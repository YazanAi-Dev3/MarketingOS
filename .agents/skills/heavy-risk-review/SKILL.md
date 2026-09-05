---
name: heavy-risk-review
description: Performs trigger-specific deep risk review for secrets/auth, command or untrusted-web boundaries, provider integrations, public side effects, destructive migrations, production infrastructure, concurrency/shared state, or expensive-to-reverse architecture. Use only when a concrete HEAVY trigger exists.
---
# Heavy Risk Review Skill

Do not repeat ordinary review. Build the threat/failure model for the assigned trigger.

Check as applicable:
- attacker-controlled inputs and trust boundaries;
- secret lifecycle and leakage surfaces;
- privilege/permission minimization;
- timeout, cancellation, retry, replay/idempotency;
- transactional/partial-failure behavior;
- rollback/restore path;
- concurrency/shared-state races;
- provider identity/schema/auth boundaries;
- public external action approval and auditability;
- SSRF/private-network/download/executable-content exposure for crawling;
- irreversible architecture and migration path.

Separate confirmed finding from conditional risk. Community anecdotes may justify a capability test, not a blocking factual claim by themselves.
