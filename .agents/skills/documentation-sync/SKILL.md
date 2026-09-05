---
name: documentation-sync
description: Keeps durable project state and owning documentation synchronized with implementation decisions, resolved investigations, calibrations, and operational contracts without duplicating the entire design suite.
---
# Documentation Sync Skill

Update documentation when the implementation changes durable truth.

- `agent_docs/STATE.md`: current phase/candidate/evidence/blockers/next safe action.
- `agent_docs/DECISIONS.md`: newly accepted durable decisions only.
- `docs/06-coordination-master-register.md`: canonical status of `A-/T-/M-/R-` items.
- owning design/operations/provider document: contract details.

Do not turn chat transcripts or raw logs into documentation. Do not mark an investigation closed unless evidence exists. Keep capability checks explicit when behavior was not run on the user's actual environment.
