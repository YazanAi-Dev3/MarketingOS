# CAPSULE-006 — Content Engine & Multi-Platform Drafting

Route: STANDARD (Content Synthesis & Platform Adaptation)
Risk trigger: External Publishing Boundary (A-007, I-02 - Content must remain in DRAFT / AWAITING_APPROVAL with human gatekeeper approval)
Candidate workspace: candidate/capsule-006-content-engine

## 1. Outcome
A production-ready content generation engine (`ContentEngine`) and persistent repository (`ContentRepository`) that synthesizes grounded marketing ideas from collected market evidence (A-028) and drafts tailored, high-converting copy across multiple platforms (LinkedIn, X/Twitter, Instagram, Telegram) while strictly enforcing human approval gates (A-007, I-02) and anti-hallucination evidence citations (M-06, I-05).

## 2. Acceptance behavior
1. **Persistent Content Repository (`ContentRepository`):**
   - Implements CRUD and querying for `ContentIdea` and `ContentAsset` entities in SQLite (`content_ideas` and `content_assets` tables).
   - Foreign key integrity, status progression (`DRAFT` -> `AWAITING_APPROVAL` -> `APPROVED`/`REJECTED`), and version tracking.
2. **Evidence-Grounded Idea Generation (A-028, M-06):**
   - Synthesizes market signals, evidence pain points, and active service profiles (`ai_automation`, `software_systems`, `academic_mentoring`).
   - Categorizes ideas by strategic objective: `demand_capture`, `education`, `trust`, `case_style`, `direct_offer`.
   - Links ideas back to source evidence IDs (`source_signal_ids`).
3. **Multi-Platform Adaptation:**
   - Generates distinct, platform-tailored drafts:
     - **LinkedIn**: Thought-leadership problem breakdown, technical architecture approach, business impact, professional CTA.
     - **X / Twitter**: Punchy attention hook, concise technical breakdown, engaging thread/post format, crisp CTA.
     - **Instagram**: Visual carousel structure with slide-by-slide brief, visual hook, and caption with hashtags.
     - **Telegram**: Formatted Markdown update for technical/founder audience with direct action link.
4. **Human Approval Enforcement (A-007, I-02):**
   - Assets are created in `AWAITING_APPROVAL` (or `DRAFT`) status.
   - Automatically registers a human approval request via `ApprovalRepository` (`action_type="publish_content"`, `target_type="content_asset"`).
   - No asset can transition to `SCHEDULED` or `PUBLISHED` without an approved record in SQLite.
5. **Prompt Injection & Secret Sanitization (A-018, I-05):**
   - All input texts pass through `SecretRedactor` prior to model synthesis.
   - Prompts strictly frame raw web evidence as untrusted data.
6. **Hermes Domain Tool Integration:**
   - Exposes `generate_content` tool in `marketing_plugin/tools/domain_tools.py`.
7. **Verification Suite:**
   - Unit tests covering repository operations, idea generation, multi-platform formatting, secret scrubbing, and approval integration.
   - Integration tests covering end-to-end flow: evidence -> idea -> multi-platform assets -> approval request -> Telegram operator card preview.
   - 100% test pass rate across the full repository test suite (>=110 passing tests).

## 3. Authority / Invariants
- `A-007`: Research, extraction, storage, analysis run automatically; public publishing and outreach require human approval initially.
- `A-018`: Prompt context is scrubbed of secrets/credentials before reasoning.
- `A-019`: Runtime reasoning is Google-only: Antigravity preferred; Gemini API fallback. Codex/OpenAI rejected (A-031).
- `A-028`: Content is generated from market evidence, service priorities and feedback, then adapted per platform.
- `I-02`: Publishing/sending cannot occur without persisted approval.
- `M-06`: Content quality rubric (relevance, evidence citations, brand tone, zero hallucinated claims).

## 4. Known evidence
- `schemas/models.py`: Defines `ContentIdea`, `ContentAsset`, `ContentIdeaObjective`, `ContentAssetStatus`.
- `migrations/001_initial_schema.sql`: Tables `content_ideas` (13) and `content_assets` (14).
- `marketing_plugin/adapters/antigravity_adapter.py`: Implements headless reasoning with schema enforcement.
- `marketing_plugin/repositories/approval_repo.py`: Approval state machine.
- `marketing_plugin/repositories/evidence_repo.py`: Market evidence queries.
- `tests/fixtures/evaluation_seeds.py`: `CONTENT_GROUNDING_RUBRIC`.

## 5. Edit surface
- `marketing_plugin/repositories/content_repo.py` (New: repository for ideas and assets)
- `marketing_plugin/repositories/__init__.py` (Export `ContentRepository`)
- `marketing_plugin/services/content_engine.py` (New: content generation and multi-platform drafting service)
- `marketing_plugin/services/__init__.py` (Export `ContentEngine`)
- `marketing_plugin/tools/domain_tools.py` (Add `generate_content` tool)
- `tests/unit/test_content_engine.py` (New: unit tests)
- `tests/integration/test_content_generation_pipeline.py` (New: integration test)
- `agent_docs/STATE.md` (Update state upon completion)

## 6. Forbidden surface
- `migrations/001_initial_schema.sql` (Frozen schema)
- `config/country-priorities.yaml` (Frozen configuration)
- External social media network calls (Instagram API / Postiz live publish) without approval mock
- Silent unapproved publishing or automated posting (`A-007`, `I-02`)

## 7. Implementation constraints
- Zero incremental spend (`A-020`).
- No external paid NLP/generation dependencies.
- Deterministic fallback when Antigravity model is unavailable or in mock test mode.

## 8. Verification
- `pytest tests/unit/test_content_engine.py`
- `pytest tests/integration/test_content_generation_pipeline.py`
- `pytest` (Full suite must pass 100%)

## 9. Documentation / state delta
- Update `agent_docs/STATE.md` recording `CAPSULE-006` completion and transition to Postiz/social scheduling spike.

## 10. Stop / escalation conditions
- Missing fields in content database schema.
- Unapproved automated posting without human approval record.
- Repair budget exceeded (max 2 substantial repairs).
