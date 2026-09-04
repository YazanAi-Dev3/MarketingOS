# Routing Policy

## Decision rule

Route by mutation scope, uncertainty, blast radius, reversibility, contract/schema/security impact, verification cost, and architecture need — not by line count alone.

## CHAT

**Entry:** no repository mutation; architecture/product decision can be answered from authority, or one targeted repository fact is missing.

Flow:
`Main Orchestrator → optional Explorer → Main answer/decision`

No Builder, Reviewer, or Heavy Reviewer by default.

## MICRO

Use only when all are true:
- localized obvious edit;
- low blast radius and easy rollback;
- clear acceptance criteria;
- no architecture/public contract/schema/security/provider/external-action decision;
- no broad tracing needed.

Flow:
`Main Task Capsule → Builder → focused verification → finish`

Reviewer is conditional if a risk trigger appears or verification is weak. Direct current-branch work is allowed only when no other writer exists and the user has not required an isolated candidate.

## STANDARD

Default real engineering work.

Flow:
`optional targeted Explorer → Main Task Capsule → Builder → local checks/repair → conditional Verifier → Reviewer → bounded repair via same Builder → final review if material repair → state update → human merge`

Rules:
- isolated branch/worktree required;
- candidate is untrusted until review passes;
- human founder performs final merge;
- reviewer sees actual candidate diff/state + capsule, not builder reasoning transcript.

## HEAVY

Use when the initial scope is high-blast-radius or hard to reverse, or when one of these project triggers applies materially:

1. auth/access control, secrets, credentials, founder allowlists;
2. command execution, SSRF, prompt/tool injection, MCP/tool permissions;
3. Antigravity/Gemini runtime provider architecture or secret-redaction boundary;
4. public publishing/outreach approval, idempotency, replay or duplicate external actions;
5. destructive migration, backup/restore, SQLite integrity or irreversible data change;
6. production VPS/deployment/security topology;
7. concurrency/distributed state;
8. architecture change that is expensive to roll back or crosses Hermes core boundaries.

Flow is phased:
`targeted Explorer → Main architecture/phase plan → one coherent Task Capsule → Builder → verification → Reviewer → Heavy Reviewer if trigger remains relevant → bounded repair → re-review → checkpoint → human merge`

Do not give Heavy Reviewer the whole project. Give it the exact trigger, capsule, candidate state/diff, relevant contracts, and verification evidence.

## Builder budget exhaustion

All engineering roles use the same Gemini 3.8 Flash High model, so there is no permanent capability-escalation Builder. After the initial implementation plus 2 substantial repair attempts fail:
- Builder stops and returns BLOCKED/PARTIAL.
- Main determines whether the cause is missing evidence, wrong capsule/architecture, external blocker, or difficult implementation.
- If scope/architecture remain valid, Main may issue the same corrected or smaller bounded capsule to a **clean Builder session**.
- If the blocker implies a design/product decision, stop and escalate the decision instead of repeating implementation.

## Parallelism

Global spawned-agent cap: 2.

Allowed:
- two independent read-only evidence tasks;
- Explorer + Builder only when Explorer answers a separate question that cannot invalidate the current capsule;
- two builders only in separate worktrees with disjoint edit surfaces and explicit composition plan.

Forbidden:
- two write agents in one worktree;
- Builder and Reviewer on the same moving candidate;
- spending Heavy Review on a candidate that baseline review has already rejected.

## Repair budgets

- primary Builder substantial repair attempts after initial implementation: 2;
- reviewer-driven repair cycles: 2;
- repeated exploration of the same answered question: 0.

After budget exhaustion, escalate the **decision/risk**, not the execution history.

## Scope expansion

Return:

```text
SCOPE EXPANSION
Original task status:
New fact:
Why current capsule is insufficient:
Smallest next coherent capsule:
Decision/risk escalation needed:
```

Never silently convert a bounded task into an autonomous project.
