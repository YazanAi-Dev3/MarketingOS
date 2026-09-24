# CAPSULE-008 — Conversation Intake & Inbound Lead Qualification

Route: STANDARD (Conversational Intake & Interaction Management)
Risk trigger: Outreach & Messaging Boundary (A-007, I-02 - External communication side-effects, A-008 Academic Integrity, A-022 Human WhatsApp Gate)
Candidate workspace: candidate/capsule-008-conversation-intake

## 1. Outcome
A production-ready conversation intake and interaction management subsystem (`ConversationIntakeService`, `InteractionRepository`) that ingests inbound inquiries across channels (WhatsApp, Telegram, Email, Web), redacts secrets (A-018, I-05), enforces strict academic integrity checks (A-008), separates B2B vs Academic funnels (A-003), associates or creates leads in SQLite, and drafts grounded response proposals that strictly require human operator approval prior to transmission (A-007, I-02, A-022).

## 2. Acceptance behavior
1. **Interaction Repository (`InteractionRepository`):**
   - Implements CRUD and querying for `Interaction` entity in SQLite (`interactions` table).
   - Foreign key to `leads.lead_id` (ON DELETE SET NULL).
   - Filtering by `lead_id`, `channel`, `actor`, `direction`.
   - Update outcome tags (`update_outcome`).
2. **Conversation Intake Service (`ConversationIntakeService`):**
   - Ingests raw text with channel and sender reference (`external_party_ref`).
   - Scrubs credentials and secrets before model synthesis or persistence (`A-018`, `I-05`).
   - Deterministic academic integrity guard: detects cheating/ghostwriting keywords (`A-008`), tags as `academic_violation`, rejects lead, and blocks promotional outreach.
   - Dual-funnel classification: routes B2B automation vs legitimate academic mentoring (`A-003`).
   - Automatically links or creates `Company` and `Lead` in SQLite.
   - Synthesizes a contextual, grounded reply proposal (`actor="agent_draft"`).
   - Registers a pending human approval request in `ApprovalRepository` (`action_type="outreach_reply"`, `target_type="interaction"`).
3. **Telegram Operator Intake Command:**
   - Adds `/intake <channel> <sender> <message>` command to `TelegramOperatorService`.
   - Renders interactive review card with reply draft and `[Approve & Send]` / `[Reject]` inline buttons.
4. **Hermes Domain Tools:**
   - Exposes `ingest_interaction` and `list_interactions` in `marketing_plugin/tools/domain_tools.py`.
   - Registers in `DOMAIN_TOOLS` (expanding to 8 total tools).
5. **Verification Suite:**
   - Unit tests covering repository operations, academic violation rejection, B2B lead association, secret redaction, and reply drafting.
   - Integration tests covering the full pipeline from raw message intake to Telegram operator preview, approval, and database status reflection.
   - 100% test pass rate across the full test suite (target >=145 tests).

## 3. Authority / Invariants
- `A-003`: Dual-funnel boundary separation: B2B services and Academic mentoring remain distinct.
- `A-007`: Public external actions and outreach require human approval initially.
- `A-008`: Strict academic integrity policy: no exam cheating, no dissertation ghostwriting.
- `A-018`: Prompt context is scrubbed of secrets/credentials before reasoning.
- `A-022`: WhatsApp is a manual/human conversion channel in V1; automated sending without approval is prohibited.
- `I-02`: Publishing/sending cannot occur without persisted approval.

## 4. Known evidence
- `migrations/001_initial_schema.sql`: Table `interactions` (lines 230-244).
- `schemas/models.py`: `Interaction`, `ActorType`, `InteractionDirection`.
- `marketing_plugin/policies/redactor.py`: Secret scrubbing.
- `marketing_plugin/services/lead_scorer.py`: Academic violation patterns.
- `tests/fixtures/evaluation_seeds.py`: Academic integrity benchmarks.

## 5. Edit surface
- `marketing_plugin/repositories/interaction_repo.py` (New: interaction repository)
- `marketing_plugin/repositories/__init__.py` (Export `InteractionRepository`)
- `marketing_plugin/services/conversation_intake.py` (New: conversation intake service)
- `marketing_plugin/services/__init__.py` (Export `ConversationIntakeService`)
- `marketing_plugin/services/telegram_operator.py` (Add `/intake` command handler)
- `marketing_plugin/tools/domain_tools.py` (Add `ingest_interaction`, `list_interactions`)
- `marketing_plugin/__init__.py` (Export new services and tools)
- `tests/unit/test_conversation_intake.py` (New)
- `tests/integration/test_conversation_intake_pipeline.py` (New)
- `tests/integration/test_repositories.py` (Add interaction repo tests)
- `tests/unit/test_domain_tools.py` (Update tool count and tests)
- `agent_docs/STATE.md` (Update state)

## 6. Forbidden surface
- `migrations/001_initial_schema.sql` (Frozen schema)
- `config/country-priorities.yaml` (Frozen configuration)
- Autonomous external message sending without human approval (`A-007`, `I-02`, `A-022`).
- Accepting academic cheating requests (`A-008`).

## 7. Implementation constraints
- Zero incremental cost (`A-020`).
- Google-only reasoning path (Antigravity preferred, deterministic fallback for fast tests).

## 8. Verification
- `pytest tests/unit/test_conversation_intake.py`
- `pytest tests/integration/test_conversation_intake_pipeline.py`
- `pytest tests/integration/test_repositories.py`
- `pytest tests/unit/test_domain_tools.py`
- `pytest` (Full suite must pass 100%)

## 9. Documentation / state delta
- Update `agent_docs/STATE.md` recording `CAPSULE-008` completion.

## 10. Stop / escalation conditions
- Failure to reject academic integrity violation.
- Autonomous message sending without human approval.
- Repair budget exceeded (max 2 repairs).

