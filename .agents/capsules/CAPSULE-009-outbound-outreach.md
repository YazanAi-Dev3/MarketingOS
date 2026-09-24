# CAPSULE-009: Outbound Outreach Generation & Follow-up Cadences

## 1. Context & Governance
- **Role:** Orchestrator (formulation) / Builder (mutation) / Reviewer (acceptance)
- **Model:** Gemini 3.8 Flash High, High effort
- **Candidate Branch:** `candidate/capsule-009-outbound-outreach`
- **Governing Invariants:**
  - `A-007` & `I-02`: External outreach messages cannot be sent autonomously; all outreach proposals require human approval records in `ApprovalRepository` (`action_type="outreach_send"`, `decision="approved"`).
  - `A-008`: Academic integrity guard strictly preserved. Academic leads only receive legitimate academic mentoring proposals; no ghostwriting or cheating outreach.
  - `A-018` & `I-05`: Secrets and PII scrubbed via `redact_secrets` before drafting.
  - `A-020`: Zero incremental paid NLP costs. High-converting deterministic templates and prompt contracts with Google-only Antigravity reasoning.
  - `A-022`: WhatsApp and cold outreach remain human-operated in V1. Drafts are generated with `actor="agent_draft"` for founder approval and transmission.
  - `M-01` & `M-12`: Closed-loop lead tracking transitions lead from `QUALIFIED` -> `OUTREACH_READY` -> `CONTACTED`.

---

## 2. Core Requirements

1. **`OutboundEngine` Service (`marketing_plugin/services/outbound_engine.py`):**
   - Implements `OutboundEngine`:
     - `generate_cadence(lead_id: str, channel: str = "email", auto_request_approval: bool = True) -> OutreachCadencePlan`:
       - Loads `Lead`, `Company`, `Evidence`, and `LeadAssessment`.
       - Scrubs confidential tokens (`I-05`).
       - Formulates a 3-step cadence:
         - **Step 1: Hook & Evidence-backed Value Proposition** (cites specific company signals/pain points).
         - **Step 2: Technical Value / Case Study** (sent ~3 business days later).
         - **Step 3: Breakaway / Closing the Loop** (sent ~5 days later).
       - Saves draft outbound interactions in `InteractionRepository` (`direction="outbound"`, `actor="agent_draft"`).
       - Registers pending `Approval` in `ApprovalRepository` (`action_type="outreach_send"`, `target_type="lead"`).
       - Updates `Lead.status` to `OUTREACH_READY`.
     - `record_contact_attempt(lead_id: str, channel: str, actor_id: str, notes: Optional[str] = None) -> bool`:
       - Transitions `Lead.status` to `CONTACTED`.
       - Updates next action to `"awaiting_lead_reply"`.

2. **Telegram Operator Bot Command (`marketing_plugin/services/telegram_operator.py`):**
   - Add `/outreach <lead_id> [channel]` command.
   - Generates personalized cadence and renders Telegram card with Step 1 draft and `[Approve & Send]`, `[Reject]`, `[Rewrite]` buttons.

3. **Hermes Domain Tools (`marketing_plugin/tools/domain_tools.py`):**
   - `generate_outreach`: Domain tool for Hermes agent.
   - `record_contact_attempt`: Marks outreach as dispatched.
   - Register in `DOMAIN_TOOLS` (expanding to 10 tools).
   - Export in `marketing_plugin/__init__.py`.

4. **Verification & Quality Gates:**
   - `tests/unit/test_outbound_engine.py`: Unit tests covering cadence generation, evidence citation, B2B vs Academic tone, and approval registration.
   - `tests/integration/test_outbound_pipeline.py`: E2E pipeline tests from qualified lead to Telegram approval to `CONTACTED` status.
   - Update `tests/unit/test_domain_tools.py` to assert 10 domain tools.
   - Target: 100% pass rate across all tests (>=155 tests).

