# Inter-agent Contracts

Operational narration stays in the worker context that created it. The main thread receives compact deltas only.

## Explorer → Main

```text
PLANNING BRIEF
Relevant paths/symbols:
Current behavior/data flow:
Constraints/invariants:
Likely edit surface:
Verification targets:
Material uncertainty/risk:
Decision needed: NONE | <precise question>
```

## Main → Builder

```text
TASK CAPSULE
ID:
Route: MICRO | STANDARD | HEAVY
Goal:
Edit surface:
Relevant evidence / authoritative docs:
Decisions already made:
Constraints/invariants:
Acceptance criteria:
Verification expected:
Worktree/branch:
Escalate if:
Return: KNOWLEDGE DELTA only
```

## Builder → Main

```text
KNOWLEDGE DELTA
Outcome: PASS | PARTIAL | BLOCKED
Changed files:
Behavioral/contract changes:
Verification:
New facts / invalidated assumptions:
Residual risks:
Decision required: NO | YES: <one precise question>
```

## Verifier → Main

```text
VERIFICATION DELTA
STATUS: PASS | FAIL | BLOCKED
GATES:
MATERIAL_FAILURES:
SCOPE:
DECISION_REQUIRED: YES | NO
```

## Reviewer → Main

```text
REVIEW DELTA
Verdict: PASS | FIX_REQUIRED | HEAVY_REVIEW_REQUIRED
Findings:
Required fixes:
Missing verification:
Heavy-review trigger:
```

## Heavy reviewer → Main

```text
HEAVY REVIEW DELTA
Verdict: PASS | FIX_REQUIRED | DECISION_REQUIRED
Trigger class:
Findings (blocking/non-blocking, certainty, conditions):
Minimal evidence:
Impact:
Minimal remediation:
Verification after remediation:
Residual risk:
Decision required: NO | YES: <one precise question>
```

## Forbidden handoff content by default

Do not promote full terminal transcripts, full stack traces, long diffs, private chain-of-thought, repeated retry history, or complete unrelated project docs into the main thread. Link to files/commands and report only the material transition.
