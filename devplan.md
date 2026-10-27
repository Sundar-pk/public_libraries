---
name: plan
description: Turn a Jira issue plus a codebase into a grounded dev plan and an honest clarification analysis. Use for every Jira task before and while implementing.
---

# Plan: Jira + Codebase to Dev Plan and Clarification

Method: read, understand, question, implement, verify. Everything named must be something you actually inspected.

## Workflow

1. **Fetch the Jira.** Read summary, description, and every sub-task verbatim. Extract each explicit requirement as R1, R2, ... Keep exact values, formats, and worked examples from the spec; they are acceptance tests.
2. **Explore the repo.** README, file tree first, then open only the files each task touches (code and tests). Record concrete paths and functions you saw. Run the baseline test and demo commands from the README and note the result. Do not plan against files you have not opened.
3. **Classify each task** as trivial-clear, complex-clear, or complex-ambiguous. This sets depth:
   - trivial-clear: smallest possible plan; one or two files; no extras; clarification "none" or one line.
   - complex-clear: every requirement covered and traceable; edge cases from the spec included.
   - complex-ambiguous: clarification comes first; do not guess; state assumptions; plan only what is safe.
4. **Gap analysis (clarification pass).** Compare Jira vs code vs README ("not implemented" lists are strong hints). For each real gap: the question, why it matters, and the assumption you would make if forced to proceed. Look for: undefined failure behavior, boundaries and invalid input, duplicates and retries, concurrency, persistence, audit and logging (what, where, retention, access), data sources and freshness, compliance expectations, backward compatibility, configuration and thresholds, performance, scope boundaries, and missing acceptance criteria. Rank by impact. Only real gaps.
5. **Plan the change in TDD order** (red, green, refactor), then implement it if the task is clear. Then verify by running the tests and the demo.

## Output

Emit exactly two sections for each task.

### dev_plan  (per task: T1, T2, T3)
- **Task / class:** one line (trivial-clear / complex-clear / complex-ambiguous).
- **Impacted files:** concrete paths, with function or line where useful; mark new files as NEW. Only files you inspected (or will create).
- **Proposed change:** numbered steps in TDD order.
  1. RED: test file, test name, input, expected result.
  2. GREEN: minimal change (file, function, what).
  3. REFACTOR: only if needed.
- **Requirement coverage:** R1 maps to step(s)... Every requirement must map to a step.
- **Verification:** the exact commands (for example `python3 -m pytest -q` and the demo script) and the expected result. After implementing, report the actual outcome.
- **Out of scope:** what you are deliberately not doing.

### clarification  (per task)
- **Gaps:** Q1..Qn, each with **Why it matters** and **Assumption if unanswered**.
- T1: "None" (or one line). T2: only minor gaps, if any. T3: rich, ranked, sharp.
- For ambiguous tasks, do not implement the unclear parts; list what is blocked until answered.

## Self-check before answering
- Every file and function named was opened, or is marked NEW.
- No invented APIs, libraries, or config; no new third-party dependencies.
- Trivial task: no extra files, refactors, or abstractions.
- Complex-clear task: all requirements mapped to steps and tests.
- Ambiguous task: questions asked, not guessed; assumptions explicit.
- Tests and demo were actually run and results reported honestly.
- No hardcoded task values, secrets, personal data, or local paths.
