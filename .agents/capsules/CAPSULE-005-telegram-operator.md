# CAPSULE-005 — Telegram Operator Bot & Interactive Approvals

Route: STANDARD (Operator Interface & Approval State Machine Gate)
Risk trigger: Operator Authorization Boundary (A-026 allowlist enforcement & negative auth verification)
Candidate workspace: candidate/capsule-005-telegram-operator

## 1. Outcome
A production-ready Telegram operator service (`TelegramOperatorService`) providing the daily control and approval surface for Marketing OS founders per A-013. It enforces strict admin allowlists (A-026), formats regional market digests and lead cards, handles interactive inline button callbacks for human approvals (`request_approval` / A-007, I-02), guarantees idempotent resolution with `actor_id` audit tracking, and executes safe control commands (`/status`, `/leads`, `/pending`, `/approve`, `/reject`).

## 2. Acceptance behavior
1. **Strict Admin Allowlist Authorization (A-026):**
   - Configurable list of allowed Telegram user IDs and chat IDs.
   - `is_authorized(user_id, chat_id)` strictly validates callers. Unauthorized users are blocked from executing commands or submitting approval callbacks.
   - Negative authentication tests pass, proving non-allowlisted callers cannot mutate state.
2. **Interactive Approval Cards & Callbacks (A-007, I-02):**
   - Generates formatted approval cards in Arabic/English detailing action type, target type/ID, company info, fit score, and operator notes.
   - Attaches Telegram inline keyboard buttons:
     - `Approve / موافقة` (`appr:<id>:approved`)
     - `Reject / رفض` (`appr:<id>:rejected`)
     - `Rewrite / طلب تعديل` (`appr:<id>:rewrite_requested`)
   - Handles callback queries, verifies authorization, and resolves approval in `ApprovalRepository` with `actor_id` and timestamp.
3. **Idempotent Resolution:**
   - Double-clicking or repeated callback execution on an already-resolved approval returns a notification that the request was already handled by `actor_id`, without corrupting or re-mutating state.
4. **Digest & Inspection Commands:**
   - `/status`: Returns system counts (total companies, leads by status, pending approvals count, and search runs).
   - `/leads [country]`: Returns top qualified leads with clear priority buckets, fit scores, and contact availability.
   - `/pending`: Returns list of pending approvals with interactive inline buttons.
   - `/approve <id>` and `/reject <id>`: Text command alternatives for terminal/CLI parity.
5. **Separation of Concerns (A-011):**
   - Does not store domain state in Telegram session memory; all queries and mutations interact directly with `Database` and `marketing_plugin/repositories/`.
   - Never exposes raw secrets, API keys, or database passwords in Telegram messages.
6. **Verification Suite:**
   - Unit tests covering authorization, negative auth, formatting, command routing, callback parsing, and idempotency.
   - Integration tests covering end-to-end flow: lead qualification -> `request_approval` -> Telegram notification card -> callback resolution -> DB persistence.
   - 100% test pass rate across the full repository test suite (>=100 passing tests).

## 3. Authority / Invariants
- `A-007`: Research, extraction, and internal reporting run automatically; public publishing and outreach require human approval initially.
- `A-011`: Hermes session state and marketing domain state are separate authorities.
- `A-013`: CLI is the engineering/operator interface; private Telegram is the daily control/approval surface.
- `A-026`: Both founders are administrators in V1; every mutation/approval stores `actor_id`.
- `I-02`: Publishing/sending cannot occur without persisted approval.

## 4. Known evidence
- `marketing_plugin/repositories/approval_repo.py`: Implements `create_request`, `get_approval`, `resolve`.
- `marketing_plugin/repositories/lead_repo.py`: Implements `list_leads`, `get_lead`, `get_latest_assessment`.
- `marketing_plugin/repositories/company_repo.py`: Implements `get_company`, `count_companies`.
- `marketing_plugin/tools/domain_tools.py`: Implements `request_approval`, `assess_lead`, `list_leads`.
- `schemas/models.py`: Defines `Approval`, `ApprovalDecision`, `Lead`, `Company`.

## 5. Edit surface
- `marketing_plugin/services/telegram_operator.py` (New: operator service and callback handler)
- `marketing_plugin/services/__init__.py` (Export `TelegramOperatorService`)
- `tests/unit/test_telegram_operator.py` (New: unit and negative auth tests)
- `tests/integration/test_telegram_approval_workflow.py` (New: integration test)
- `agent_docs/STATE.md` (Update state upon completion)

## 6. Forbidden surface
- `migrations/001_initial_schema.sql` (Frozen schema)
- `config/country-priorities.yaml` (Frozen configuration)
- External Telegram network calls in unit tests (Must use hermetic mocks / simulated payloads)
- Web UI or dashboard code (D-04 explicitly defers web UI in favor of Telegram + CLI)

## 7. Implementation constraints
- Zero incremental cost (`A-020`).
- No external paid Telegram libraries; use pure Python dataclasses / dict payloads compatible with Telegram Bot API and Hermes Telegram gateway.
- Hermetic test suite requiring zero network connectivity.

## 8. Verification
- `pytest tests/unit/test_telegram_operator.py`
- `pytest tests/integration/test_telegram_approval_workflow.py`
- `pytest` (Full suite must pass 100%)

## 9. Documentation / state delta
- Update `agent_docs/STATE.md` recording `CAPSULE-005` completion and transition to Phase 2 Content Engine.

## 10. Stop / escalation conditions
- Missing Telegram API field contracts required by Hermes gateway.
- Inability to verify negative authentication without live bot.
- Repair budget exceeded (max 2 substantial repairs).
