"""
workshop_starter.py

WORKSHOP COMPLETION TASK — Add a Fraud Detection Agent
=========================================================
Starting point: the same Loan Underwriting Copilot pipeline from
multi_model_fintech_agent.py. Everything below already runs as-is
(`python workshop_starter.py`) — your job is to fill in the 6 TODOs so
that high-risk applications get screened by a Fraud Detection agent
before they reach manual review.

TARGET GRAPH AFTER YOUR CHANGES:

    intake (Mistral) -> risk (Qwen) --[risk_score <= 70]--> compliance (GPT-OSS) -> decision
                                    \\
                                     +--[risk_score > 70]--> fraud_check (4th model)
                                                                 |
                                                    [fraud_flag] +--yes--> decision (HOLD_FOR_INVESTIGATION)
                                                                 +--no ---> manual_review -> decision

Definition of done (see slide 14):
  [ ] New node + state field compile without errors
  [ ] Conditional edge visibly triggers on a high-risk sample application
  [ ] Decision + rationale printed at the end of the run
  [ ] Bonus (optional): run compliance & fraud nodes in parallel and merge results

Search this file for "TODO" to find every spot you need to touch.
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
# 1. INTERNAL LLM GATEWAY CONFIG
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
    # -----------------------------------------------------------------
    # TODO 1: Add a 4th endpoint for the fraud detection model.
    #   If your org hasn't provisioned a separate model for this yet,
    #   it's fine to point "fraud-model" at one of the existing three
    #   (e.g. reuse "qwen"'s config) — the important part for this
    #   exercise is that fraud_check is its OWN NODE with its own
    #   prompt and its own state field, not which literal model backs it.
    #
    # "fraud-model": {
    #     "base_url": os.environ.get("FRAUD_MODEL_BASE_URL", "https://internal-llm-gw/<your-model>/v1"),
    #     "model": os.environ.get("FRAUD_MODEL_NAME", "<your-model-name>"),
    #     "api_key": os.environ.get("FRAUD_MODEL_API_KEY", "dummy-key"),
    # },
    # -----------------------------------------------------------------
}

USE_MOCK_LLM = os.environ.get("USE_MOCK_LLM", "true").lower() == "true"


def call_internal_llm(endpoint_key: str, system_prompt: str, user_prompt: str,
                       *, temperature: float = 0.0, max_tokens: int = 800) -> str:
    if USE_MOCK_LLM:
        return _mock_response(endpoint_key)

    cfg = MODEL_ENDPOINTS[endpoint_key]
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
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
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _mock_response(endpoint_key: str) -> str:
    """Canned responses for offline demo/workshop use. Add a branch here for
    your new "fraud-model" key so you can test fraud_node without live
    network access (see TODO 3)."""
    if endpoint_key == "mistral":
        return json.dumps({
            "applicant_name": "Arjun Mehta",
            "requested_amount": 38000,
            "monthly_income": 3400,
            "monthly_debt": 900,
            "purpose": "Debt consolidation",
            "transaction_summary": "Large irregular cash deposits inconsistent with stated income",
        })
    if endpoint_key == "qwen":
        # Deliberately high risk_score so your fraud_check branch triggers.
        return json.dumps({
            "risk_score": 81,
            "rationale": "Requested amount is over 11x monthly income; irregular deposit pattern",
        })
    if endpoint_key == "gpt-oss":
        return json.dumps({"compliant": True, "violations": []})
    # -----------------------------------------------------------------
    # TODO 3 (part of it lives here): add a mock branch, e.g.
    # if endpoint_key == "fraud-model":
    #     return json.dumps({
    #         "fraud_flag": True,
    #         "fraud_rationale": "Deposit pattern inconsistent with stated income; recommend hold",
    #     })
    # -----------------------------------------------------------------
    return "{}"


# ---------------------------------------------------------------------------
# 2. SHARED STATE
# ---------------------------------------------------------------------------
class LoanState(TypedDict):
    application_text: str
    extracted: Optional[dict]
    risk_score: Optional[float]
    risk_rationale: Optional[str]
    compliance_result: Optional[dict]
    decision: Optional[str]
    trace: Annotated[List[str], operator.add]
    # -----------------------------------------------------------------
    # TODO 2: add the field(s) your fraud_check node will populate, e.g.
    # fraud_flag: Optional[bool]
    # fraud_rationale: Optional[str]
    # -----------------------------------------------------------------


RISK_THRESHOLD = 70

# ---------------------------------------------------------------------------
# 3. SPECIALIST NODES  (unchanged from the reference pipeline)
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
    messages = INTAKE_PROMPT.format_messages(application_text=state["application_text"])
    raw = call_internal_llm("mistral", messages[0].content, messages[1].content)
    extracted = _safe_json(raw)
    return {"extracted": extracted,
            "trace": [f"[intake/mistral] extracted fields: {list(extracted.keys())}"]}


RISK_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a credit risk analyst. Given applicant financials, assess risk. "
     "Respond ONLY with JSON: "
     '{{"risk_score": <integer 0-100, higher = riskier>, "rationale": <one sentence>}}'),
    ("user", "Applicant data: {extracted}"),
])


def risk_node(state: LoanState) -> dict:
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
    """Kept as the fallback for high-risk applications that fraud_check
    clears — a human still reviews them, we just no longer send EVERY
    high-risk case straight to a human without a fraud screen first."""
    return {
        "decision": "MANUAL_REVIEW",
        "trace": [f"[manual_review] risk_score={state['risk_score']} — cleared fraud screen, "
                  f"routed to a human underwriter"],
    }


# -----------------------------------------------------------------------
# TODO 3: IMPLEMENT fraud_node
#
# This is the core of the exercise. Write a node function that:
#   1. Builds a prompt asking the model to look for fraud indicators —
#      e.g. mismatched stated income vs. transaction_summary, unusual
#      deposit patterns, inconsistent applicant details.
#   2. Calls call_internal_llm("fraud-model", ...) (or whichever endpoint
#      key you set up in TODO 1).
#   3. Parses the JSON result into fraud_flag (bool) and fraud_rationale (str).
#   4. Returns a state update dict, same shape as the other nodes, plus
#      a trace entry.
#
# Starter skeleton:
#
# FRAUD_PROMPT = ChatPromptTemplate.from_messages([
#     ("system",
#      "You are a fraud detection analyst. Review the applicant data for "
#      "signs of fraud: mismatched income vs. transaction history, unusual "
#      "deposit patterns, or inconsistent details. Respond ONLY with JSON: "
#      '{{"fraud_flag": true|false, "fraud_rationale": <one sentence>}}'),
#     ("user", "Applicant data: {extracted}\nRisk score: {risk_score}\nRisk rationale: {risk_rationale}"),
# ])
#
# def fraud_node(state: LoanState) -> dict:
#     messages = FRAUD_PROMPT.format_messages(
#         extracted=json.dumps(state["extracted"]),
#         risk_score=state["risk_score"],
#         risk_rationale=state["risk_rationale"],
#     )
#     raw = call_internal_llm("fraud-model", messages[0].content, messages[1].content)
#     result = _safe_json(raw)
#     return {
#         "fraud_flag": result.get("fraud_flag", False),
#         "fraud_rationale": result.get("fraud_rationale", ""),
#         "trace": [f"[fraud_check/fraud-model] fraud_flag={result.get('fraud_flag')} — {result.get('fraud_rationale')}"],
#     }
#
# -----------------------------------------------------------------------


def decision_node(state: LoanState) -> dict:
    if state.get("decision") == "MANUAL_REVIEW":
        return {"trace": ["[decision] MANUAL_REVIEW confirmed — awaiting human underwriter"]}

    # -------------------------------------------------------------
    # TODO 6: before falling through to the compliance-based logic
    # below, check state.get("fraud_flag"). If it's True, this
    # application should never reach a human queue silently — return
    # {"decision": "HOLD_FOR_INVESTIGATION", "trace": [...]} here.
    # -------------------------------------------------------------

    compliance = state.get("compliance_result") or {}
    if not compliance.get("compliant", True):
        decision = "REJECT"
        reason = f"Policy violation(s): {compliance.get('violations')}"
    else:
        decision = "APPROVE"
        reason = state.get("risk_rationale", "risk within policy threshold")

    return {"decision": decision, "trace": [f"[decision] {decision} — {reason}"]}


# ---------------------------------------------------------------------------
# 4. CONDITIONAL EDGES
# ---------------------------------------------------------------------------
def route_after_risk(state: LoanState) -> str:
    # -------------------------------------------------------------
    # TODO 4: change the high-risk branch target from "manual_review"
    # to "fraud_check" once that node exists.
    # -------------------------------------------------------------
    if (state.get("risk_score") or 0) > RISK_THRESHOLD:
        return "manual_review"  # <-- change to "fraud_check"
    return "compliance"


# -----------------------------------------------------------------------
# TODO 5: write route_after_fraud and use it in add_conditional_edges below.
#
# def route_after_fraud(state: LoanState) -> str:
#     if state.get("fraud_flag"):
#         return "decision"        # skip straight to decision -> HOLD_FOR_INVESTIGATION
#     return "manual_review"       # cleared fraud screen -> still goes to a human
# -----------------------------------------------------------------------


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
    # TODO 4 (cont.): graph.add_node("fraud_check", fraud_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "risk")
    graph.add_conditional_edges(
        "risk", route_after_risk,
        {"manual_review": "manual_review", "compliance": "compliance"},
        # TODO 4 (cont.): {"fraud_check": "fraud_check", "compliance": "compliance"},
    )
    graph.add_edge("compliance", "decision")
    graph.add_edge("manual_review", "decision")
    # TODO 5 (cont.): graph.add_conditional_edges(
    #     "fraud_check", route_after_fraud,
    #     {"decision": "decision", "manual_review": "manual_review"},
    # )
    graph.add_edge("decision", END)

    return graph.compile()


app = build_graph()


# ---------------------------------------------------------------------------
# 6. RUN & TRACE
#    This sample application is deliberately high-risk (risk_score=81 in
#    mock mode) so it exercises your new branch — don't change it until
#    your fraud_check node is wired in.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_application = """
    Applicant: Arjun Mehta
    Requested loan amount: $38,000
    Stated purpose: Debt consolidation
    Monthly income: $3,400
    Existing monthly debt payments: $900
    Recent transaction history: large irregular cash deposits inconsistent with stated income
    """

    result = app.invoke({"application_text": sample_application, "trace": []})

    print("\n--- TRACE (per-hop audit log) ---")
    for line in result["trace"]:
        print(line)

    print("\n--- FINAL STATE ---")
    print(json.dumps({k: v for k, v in result.items() if k != "trace"}, indent=2))
