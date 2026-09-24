# CAPSULE-004 — Lead Scoring & AI Qualification Engine

Route: STANDARD (Model Reasoning & Domain Qualification Bridge)
Risk trigger: Provider Boundary (Safe Antigravity headless reasoning integration) & Academic Ethical Boundary (A-008)
Candidate workspace: candidate/capsule-004-lead-scoring

## 1. Outcome
A production-ready, AI-assisted lead scoring and qualification engine (`LeadScorer` service) integrating `AntigravityAdapter` and `assess_lead`. It executes multi-factor qualification (`M-01`), enforces strict dual-funnel isolation (`A-003`), guarantees ethical academic boundaries (`A-008`), protects against prompt injection and secret leakage (`A-018`, `I-05`), and persists append-only `LeadAssessment` snapshots with evidence provenance (`A-017`).

## 2. Acceptance behavior
1. **Multi-Factor Score Calculation (M-01):**
   - Calculates 4 dimension scores: `fit_score`, `pain_score`, `urgency_score`, `reachability_score` in [0.0, 1.0].
   - Computes weighted composite `final_score` = `round(0.30 * fit + 0.30 * pain + 0.20 * urgency + 0.20 * reachability, 2)`.
2. **AI Reasoning via AntigravityAdapter (A-019, T-01):**
   - Synthesizes company profile and all associated `Evidence` records into a sanitized prompt.
   - Enforces strict JSON Schema matching `LeadAssessment` requirements through `AntigravityAdapter.infer_json(...)`.
   - Captures `reasoning_summary`, `recommended_service_key`, `academic_integrity_passed`, `confidence`, and provider identity (`antigravity`).
3. **Dual Funnel & Academic Integrity Enforcement (A-003, A-008):**
   - B2B funnel: Evaluates technical need, automation pain, and reachability.
   - Academic funnel: Explicitly tests for legitimate technical/mentoring assistance vs. academic dishonesty (ghostwriting, exam solving, dissertation writing on behalf of student).
   - If academic violation detected: Marks `academic_integrity_passed = False`, status `REJECTED`, and priority bucket 3 (or rejected bucket), refusing qualification.
4. **Prompt Injection & Secret Safety (A-018, I-05):**
   - All text inputs from crawled evidence pass through `SecretRedactor` before sending to the model.
   - Prompt instructions isolate untrusted text and treat it strictly as data, neutralizing injection attempts.
5. **Deterministic Fallback:**
   - If `AntigravityAdapter` is unconfigured, disabled, or fails (CLI missing or timeout), falls back gracefully to a deterministic heuristic scorer without crashing.
   - Sets `provider_identity = "deterministic_fallback"` and unassisted baseline status per Invariant docs/09-final-design-review.md:108.
6. **State Persistence & Idempotency (A-017):**
   - Appends a new `LeadAssessment` record to `lead_assessments` table linking all associated `evidence_ids`.
   - Updates `Lead` record in `leads` table with updated `status` (`QUALIFIED`, `REJECTED`, or `DISCOVERED`), `priority_bucket` (1: >=0.85, 2: >=0.70, 3: <0.70), and `recommended_service_key`.
7. **Hermes Domain Tool Integration:**
   - Updates `assess_lead` domain tool in `marketing_plugin/tools/domain_tools.py` to use `LeadScorer` while retaining full backward compatibility.
8. **Verification Suite:**
   - Unit tests covering scoring logic, academic integrity checks, prompt injection resilience, and deterministic fallback.
   - Integration tests running end-to-end against `SYNTHETIC_CORPUS` and matching `LEAD_PRIORITY_RANKING_LABELS`.
   - 100% test pass rate across the full repository test suite (>=90 passing tests).

## 3. Authority / Invariants
- `A-003`: One platform, two separated funnels: B2B and technical/academic.
- `A-006` / `M-05`: Service priority: AI services first, technical/academic second, general software third.
- `A-008`: Academic funnel supports legitimate mentoring/technical assistance, never deceptive academic completion.
- `A-011`: Hermes session memory and marketing domain state are separate authorities.
- `A-017`: Every material signal and lead assessment retains source/evidence/date/confidence provenance.
- `A-018`: Prompt context is scrubbed of secrets/credentials before reasoning.
- `A-019`: Runtime reasoning is Google-only: Antigravity preferred; Gemini API fallback. Codex/OpenAI rejected (A-031).
- `M-01`: Lead scoring weights and thresholds.

## 4. Known evidence
- `marketing_plugin/adapters/antigravity_adapter.py`: Implements `AntigravityAdapter` with `infer_json`, schema enforcement, secret redaction, and Windows buffer protection.
- `marketing_plugin/repositories/lead_repo.py`: Implements `save_lead`, `get_lead`, `save_assessment`, `get_latest_assessment`.
- `marketing_plugin/repositories/evidence_repo.py`: Implements `list_for_company(company_id)`.
- `marketing_plugin/repositories/company_repo.py`: Implements `get_company(company_id)`.
- `marketing_plugin/tools/domain_tools.py`: Contains existing baseline `assess_lead`.
- `tests/fixtures/synthetic_corpus.py`: Fixed multilingual fixtures including clean B2B, hiring signals, legitimate academic, academic violations, prompt injection, and SEO spam.
- `tests/fixtures/evaluation_seeds.py`: Fixed ground truth labels `LEAD_PRIORITY_RANKING_LABELS`.

## 5. Edit surface
- `marketing_plugin/services/lead_scorer.py` (New: core scoring & qualification logic)
- `marketing_plugin/services/__init__.py` (Export `LeadScorer`)
- `marketing_plugin/tools/domain_tools.py` (Wire `LeadScorer` into `assess_lead`)
- `tests/unit/test_lead_scorer.py` (New: unit tests for `LeadScorer`)
- `tests/integration/test_lead_qualification_pipeline.py` (New: integration tests with synthetic corpus)
- `agent_docs/STATE.md` (Update state upon completion)

## 6. Forbidden surface
- `migrations/001_initial_schema.sql` (Schema is frozen; existing tables already support all required fields)
- `config/country-priorities.yaml` (Confirmed production configuration)
- External paid APIs or OpenAI/Codex dependencies (`A-019`, `A-031`, `A-020`)
- Modifying repository transaction semantics or WAL configuration

## 7. Implementation constraints
- Zero incremental cost (`A-020`).
- No shell subprocess execution other than the existing `AntigravityAdapter` headless wrapper.
- All model inputs must be validated through `SecretRedactor` (`I-05`).
- Prompts must instruct the model in both Arabic and English context.

## 8. Verification
- `pytest tests/unit/test_lead_scorer.py`
- `pytest tests/integration/test_lead_qualification_pipeline.py`
- `pytest` (Full suite must pass 100%)

## 9. Documentation / state delta
- Update `agent_docs/STATE.md` recording `CAPSULE-004` completion, test counts, and transition to Telegram operator workflow.

## 10. Stop / escalation conditions
- Upstream Antigravity CLI interface mismatch requiring breaking changes to adapter.
- Scope expansion into uncalibrated automated outreach (A-007 forbids automated outreach without approval).
- Repair budget exceeded (max 2 substantial repairs).
