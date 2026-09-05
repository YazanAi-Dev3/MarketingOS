---
name: task-capsule
description: Creates and validates bounded engineering Task Capsules before implementation. Use whenever work is delegated to a Builder or when scope, acceptance behavior, edit boundaries, verification, or stop conditions must be made explicit.
---
# Task Capsule Skill

A Task Capsule is the contract between Orchestrator and a mutation worker. It prevents context loss and scope drift.

## Minimum capsule

Include:

1. **Capsule ID / route** — MICRO, STANDARD, or HEAVY.
2. **Outcome** — one testable end state, not an activity.
3. **Acceptance behavior** — externally or contract-observable behavior that proves completion.
4. **Authority/invariants** — governing `A-/T-/M-/R-` items and owning docs.
5. **Known evidence** — precise paths/symbols/current behavior; classify uncertainty.
6. **Edit surface** — allowed modules/files/categories.
7. **Forbidden surface** — areas that must not change.
8. **Candidate workspace** — current workspace only if eligible MICRO; otherwise branch/worktree.
9. **Verification plan** — named commands/gates or explicit bounded discovery plan.
10. **Documentation/state delta** — files to update if the implementation closes or changes durable truth.
11. **Stop/escalation conditions** — architecture uncertainty, missing external capability, scope expansion, repair budget exhaustion.

## Capsule quality decision tree

- Can acceptance behavior be stated? If no → investigate/clarify, do not build.
- Is architecture already decided? If no and material → Orchestrator decides/researches first.
- Is edit surface bounded? If no → explore until bounded.
- Is external/upstream behavior assumed? If yes → add capability check or authoritative evidence.
- Is the task high-risk? If yes → HEAVY route and explicit trigger.

## Template

Use `.agents/protocols/TASK-CAPSULE.md`. Do not copy whole documentation files into the capsule; cite paths/sections and provide only decision-relevant context.
