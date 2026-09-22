"""
multi_model_fintech_agent.py

REFERENCE IMPLEMENTATION — Loan Underwriting Copilot
A multi-model LangGraph pipeline that routes each step of a loan pre-screening
workflow to the internal LLM best suited for it:

    Intake (Mistral)  ->  Risk Analysis (Qwen)  ->  Compliance Check (GPT-OSS)  ->  Decision
                                  |
                                  +-- if risk_score > 70 --> Manual Review --> Decision

This is the file you walk through live in the 15-minute code section.
It runs standalone with `python multi_model_fintech_agent.py`.

By default it runs in MOCK MODE (USE_MOCK_LLM=true) so the demo works even
without network access to the internal gateway — flip the env var to false
once you've confirmed the real endpoints are reachable from the room.
"""

import json
import os
import re
from typing import List, Optional, TypedDict
from typing_extensions import Annotated
import operator

import requests
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

# ---------------------------------------------------------------------------
# 1. INTERNAL LLM GATEWAY CONFIG  (see slide 10 — "Our Internal LLM Gateway")
#    Every model speaks the same OpenAI-compatible /v1/chat/completions
#    schema. Only base_url, model name, and api_key differ per model.
# ---------------------------------------------------------------------------
MODEL_ENDPOINTS = {
    "mistral": {
        "base_url": os.environ.get("MISTRAL_BASE_URL", "https://internal-llm-gw/mistral/v1"),
        "model": os.environ.get("MISTRAL_MODEL", "mistral-large-internal"),
        "api_key": os.environ.get("MISTRAL_API_KEY", "dummy-key"),
    },
    "qwen": {
        "base_url": os.environ.get("QWEN_BASE_URL", "https://internal-llm-gw/qwen/v1"),
        "model": os.environ.get("QWEN_MODEL", "qwen2.5-72b-internal"),
        "api_key": os.environ.get("QWEN_API_KEY", "dummy-key"),
    },
    "gpt-oss": {
        "base_url": os.environ.get("GPT_OSS_BASE_URL", "https://internal-llm-gw/gpt-oss/v1"),
        "model": os.environ.get("GPT_OSS_MODEL", "gpt-oss-120b-internal"),
        "api_key": os.environ.get("GPT_OSS_API_KEY", "dummy-key"),
    },
}

# Set to "false" once you've confirmed the internal gateway is reachable.
USE_MOCK_LLM = os.environ.get("USE_MOCK_LLM", "true").lower() == "true"


def call_internal_llm(endpoint_key: str, system_prompt: str, user_prompt: str,
                       *, temperature: float = 0.0, max_tokens: int = 800) -> str:
    """POST an OpenAI-compatible chat completion request to one of our
    internal model endpoints and return the raw text of the response.

    This is the ONE function every specialist node calls. Swapping which
    model backs a node is a one-line change: pass a different endpoint_key.
    """
    if USE_MOCK_LLM:
        return _mock_response(endpoint_key)

    cfg = MODEL_ENDPOINTS[endpoint_key]
    url = f"{cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _safe_json(raw_text: str) -> dict:
    """Model output is occasionally wrapped in ```json fences or has stray
    text around it — strip that before parsing."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _mock_response(endpoint_key: str) -> str:
    """Canned responses so the workshop demo works with no network access.
    Swap USE_MOCK_LLM to false to hit the real internal gateway."""
    if endpoint_key == "mistral":
        return json.dumps({
            "applicant_name": "Priya Sharma",
            "requested_amount": 45000,
            "monthly_income": 6200,
            "monthly_debt": 1100,
            "purpose": "Expand small retail business (inventory)",
            "transaction_summary": "Steady deposits, no gambling or crypto activity",
        })
    if endpoint_key == "qwen":
        return json.dumps({
            "risk_score": 42,
            "rationale": "Stable income, debt-to-income ratio well within acceptable range",
        })
    if endpoint_key == "gpt-oss":
        return json.dumps({"compliant": True, "violations": []})
    return "{}"


# ---------------------------------------------------------------------------
# 2. SHARED STATE  (see slide 5 — "State" primitive)
# ---------------------------------------------------------------------------
class LoanState(TypedDict):
    application_text: str
    extracted: Optional[dict]
    risk_score: Optional[float]
    risk_rationale: Optional[str]
    compliance_result: Optional[dict]
    decision: Optional[str]
    # Annotated + operator.add means every node's trace entries are appended,
    # not overwritten — a running audit log across all hops.
    trace: Annotated[List[str], operator.add]


RISK_THRESHOLD = 70

# ---------------------------------------------------------------------------
# 3. SPECIALIST NODES — each backed by a different internal model
# ---------------------------------------------------------------------------

INTAKE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a loan intake specialist. Extract structured fields from the raw "
     "application text. Respond ONLY with compact JSON in this exact shape: "
     '{{"applicant_name": str, "requested_amount": number, "monthly_income": number, '
     '"monthly_debt": number, "purpose": str, "transaction_summary": str}}'),
    ("user", "{application_text}"),
])


def intake_node(state: LoanState) -> dict:
    """Fast, cheap field extraction — Mistral is plenty for this."""
    messages = INTAKE_PROMPT.format_messages(application_text=state["application_text"])
    raw = call_internal_llm("mistral", messages[0].content, messages[1].content)
    extracted = _safe_json(raw)
    return {
        "extracted": extracted,
        "trace": [f"[intake/mistral] extracted fields: {list(extracted.keys())}"],
    }


RISK_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a credit risk analyst. Given applicant financials, assess risk. "
     "Respond ONLY with JSON: "
     '{{"risk_score": <integer 0-100, higher = riskier>, "rationale": <one sentence>}}'),
    ("user", "Applicant data: {extracted}"),
])


def risk_node(state: LoanState) -> dict:
    """Multi-step reasoning over financials — Qwen's strength."""
    messages = RISK_PROMPT.format_messages(extracted=json.dumps(state["extracted"]))
    raw = call_internal_llm("qwen", messages[0].content, messages[1].content)
    result = _safe_json(raw)
    return {
        "risk_score": result.get("risk_score", 50),
        "risk_rationale": result.get("rationale", ""),
        "trace": [f"[risk/qwen] risk_score={result.get('risk_score')} — {result.get('rationale')}"],
    }


COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a lending compliance officer. Check the application against these "
     "policy rules: (1) requested_amount must be <= 5x monthly_income, "
     "(2) purpose must not be for restricted use (gambling, crypto speculation), "
     "(3) monthly_debt must not exceed 45% of monthly_income. "
     'Respond ONLY with JSON: {{"compliant": true|false, "violations": [str, ...]}}'),
    ("user", "Applicant data: {extracted}\nRisk score: {risk_score}"),
])


def compliance_node(state: LoanState) -> dict:
    """Highest cost-of-being-wrong step — reserved for the largest model."""
    messages = COMPLIANCE_PROMPT.format_messages(
        extracted=json.dumps(state["extracted"]), risk_score=state["risk_score"]
    )
    raw = call_internal_llm("gpt-oss", messages[0].content, messages[1].content)
    result = _safe_json(raw)
    return {
        "compliance_result": result,
        "trace": [f"[compliance/gpt-oss] compliant={result.get('compliant')} violations={result.get('violations')}"],
    }


def manual_review_node(state: LoanState) -> dict:
    """No LLM call — a pure routing stub for the high-risk branch.
    This is the node the WORKSHOP task extends with a fraud-detection agent."""
    return {
        "decision": "MANUAL_REVIEW",
        "trace": [f"[manual_review] risk_score={state['risk_score']} exceeded threshold "
                  f"({RISK_THRESHOLD}) — routed to a human underwriter"],
    }


def decision_node(state: LoanState) -> dict:
    """Final aggregation step — deliberately rule-based, not an LLM call.
    Not every node in a multi-model graph needs to be a model at all."""
    if state.get("decision") == "MANUAL_REVIEW":
        return {"trace": ["[decision] MANUAL_REVIEW confirmed — awaiting human underwriter"]}

    compliance = state.get("compliance_result") or {}
    if not compliance.get("compliant", True):
        decision = "REJECT"
        reason = f"Policy violation(s): {compliance.get('violations')}"
    else:
        decision = "APPROVE"
        reason = state.get("risk_rationale", "risk within policy threshold")

    return {"decision": decision, "trace": [f"[decision] {decision} — {reason}"]}


# ---------------------------------------------------------------------------
# 4. CONDITIONAL EDGE — the branching logic (see slide 12)
# ---------------------------------------------------------------------------
def route_after_risk(state: LoanState) -> str:
    if (state.get("risk_score") or 0) > RISK_THRESHOLD:
        return "manual_review"
    return "compliance"


# ---------------------------------------------------------------------------
# 5. WIRE THE GRAPH
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(LoanState)

    graph.add_node("intake", intake_node)
    graph.add_node("risk", risk_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("manual_review", manual_review_node)
    graph.add_node("decision", decision_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "risk")
    graph.add_conditional_edges(
        "risk", route_after_risk,
        {"manual_review": "manual_review", "compliance": "compliance"},
    )
    graph.add_edge("compliance", "decision")
    graph.add_edge("manual_review", "decision")
    graph.add_edge("decision", END)

    return graph.compile()


app = build_graph()


# ---------------------------------------------------------------------------
# 6. RUN & TRACE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_application = """
    Applicant: Priya Sharma
    Requested loan amount: $45,000
    Stated purpose: Expand small retail business (inventory)
    Monthly income: $6,200
    Existing monthly debt payments: $1,100
    Recent transaction history: steady deposits, no gambling/crypto activity
    """

    result = app.invoke({"application_text": sample_application, "trace": []})

    print("\n--- TRACE (per-hop audit log) ---")
    for line in result["trace"]:
        print(line)

    print("\n--- FINAL STATE ---")
    print(json.dumps({k: v for k, v in result.items() if k != "trace"}, indent=2))
