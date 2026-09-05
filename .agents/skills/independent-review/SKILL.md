---
name: independent-review
description: Performs independent semantic acceptance review of an implemented candidate against its Task Capsule and governing project contracts. Use after implementation for STANDARD work and risk-signaled MICRO work; it never repairs code.
---
# Independent Review Skill

Review actual candidate state, not Builder explanation.

Order:
1. acceptance behavior;
2. scope/edit-boundary compliance;
3. architecture and project invariants;
4. edge/failure/idempotency behavior;
5. data/evidence/provenance contracts;
6. test/verification sufficiency;
7. operational/security implications;
8. documentation/state consistency.

A finding must be actionable: severity + path/symbol + violated criterion + failure scenario + smallest correction direction.
Avoid style churn. Escalate only concrete HEAVY triggers.

Return `REVIEW DELTA` from `.agents/protocols/CONTRACTS.md`.
