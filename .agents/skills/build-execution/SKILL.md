---
name: build-execution
description: Executes one approved Task Capsule as a production-quality bounded implementation with focused verification, finite repair, and structured handoff. Use for Builder mutation work after architecture and acceptance criteria are fixed.
---
# Build Execution Skill

## Procedure

1. Confirm candidate workspace and clean/known Git state.
2. Read capsule plus only the directly owning code/docs.
3. Inspect existing implementation before editing.
4. Implement the smallest coherent production-complete change.
5. Add/update focused tests or executable checks.
6. Run narrow checks first; repair candidate-caused failures within budget.
7. Update durable docs/state when required.
8. Return Knowledge Delta; never merge to main.

## Anti-patterns

Stop instead of:
- replacing an accepted architecture because it is inconvenient;
- broad refactoring adjacent modules;
- adding future-scale infrastructure without a current requirement;
- hiding failures by weakening tests;
- copying legacy code wholesale without validating dependencies/contracts;
- using an LLM for deterministic parsing that a stable schema can solve.

## Failure budget

Initial build + two substantial repair/debug cycles. If exhausted, preserve evidence and return BLOCKED/SCOPE_EXPANDED. The next move belongs to Orchestrator, preferably a smaller corrected capsule or clean new Builder session.
