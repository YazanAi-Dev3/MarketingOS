# STATE — Marketing OS

Current phase: **PHASE 0 — PRE-IMPLEMENTATION FOUNDATION & SPIKES (AG-CC-01..05 CLOSED)**.

Documentation: updated for Crawl4AI acquisition and Clients Hunter selective migration.
Engineering harness: Antigravity-native control plane verified locally (AG-CC-01..05 closed).
Foundational scaffolding: `marketing_plugin/`, `schemas/`, `migrations/`, `tests/` packages initialized.

Capability checks status:
- AG-CC-01 (Discovery): CLOSED.
- AG-CC-02 (Model & Effort Inheritance): CLOSED (verified via native subagent execution trace and thinking output).
- AG-CC-03 (Candidate Worktree Flow): CLOSED (verified via branch worktree isolation and clean main branch).
- AG-CC-04 (Permissions / Hooks): CLOSED (verified via `test_hooks.py` and active PreToolUse guard).
- AG-CC-05 (Delegation Limits): CLOSED (verified via Orchestrator delegation policy and subagent lifecycle management).

Spikes status:
- T-08 (Pin Hermes & Extension Interfaces): CLOSED (Hermes v0.21.0 upstream 63279301 confirmed; plugin, skill, and model-provider contracts mapped).
- T-01 (Hermes ↔ Antigravity Runtime Path): CLOSED (Antigravity CLI 1.1.27 headless execution, Gemini 3.8 Flash High reasoning, structured JSON output, thinking token accounting verified; `AntigravityAdapter` implemented with unit tests).
- T-02 (SearXNG Localization & Regional Query Benchmark): CLOSED (`SearXNGAdapter` with URL normalization/tracking stripping, `RegionalQueryPlanner` covering GCC/Levant/Turkey, and `AcquisitionRouter` with strict SSRF private-network protection and SHA-256 evidence hashing implemented and tested).
- T-09 (Freelance Source Adapters Revalidation): CLOSED (Bahr revalidated at `bahr.sa` Next.js SPA; Mostaql and Khamsat revalidated under Crawl4AI rich acquisition mode due to AWS ALB/WAF boundaries).

Foundation milestones completed:
- Domain schemas: Pydantic models for all 16 core domain entities in `schemas/models.py` (including `AgentRun` and `ActorType`/`outcome_tag` on `Interaction`).
- SQLite storage & migrations: `migrations/001_initial_schema.sql` (17 tables including `schema_migrations`, WAL mode, foreign keys, indexes, pre-migration `.bak` snapshots, busy_timeout=5000ms) and `database.py` automated migration runner.
- Domain repositories: 7 repositories in `marketing_plugin/repositories/` (`AgentRunRepository`, `SourceRepository`, `CompanyRepository`, `EvidenceRepository`, `LeadRepository`, `ApprovalRepository`, `Database`) with explicit transaction commits and WAL multi-connection persistence.
- Deterministic secret redactor: `marketing_plugin/policies/redactor.py` scrubbing API keys, bearer tokens, private keys, AWS keys, and URL passwords before reasoning payloads or storage (Invariant I-05).
- Acquisition & Search layer: `SearXNGAdapter`, `RegionalQueryPlanner`, and `AcquisitionRouter` with per-hop redirect SSRF validation (max 5 hops), DNS fail-closed checks, integer/decimal loopback IP blocking, and SHA-256 evidence hashing.
- Freelance Source Adapters: `BaseSourceAdapter` (`marketing_plugin/adapters/base.py`) and specialized adapters for Bahr (`bahr_adapter.py`, `bahr.sa`), Mostaql (`mostaql_adapter.py`, `mostaql.com`), and Khamsat (`khamsat_adapter.py`, `khamsat.com`) producing validated `Evidence` models with SHA-256 content hashes and deterministic extraction.
- Hermes Domain Tools: `marketing_plugin/tools/domain_tools.py` implementing `scan_market`, `assess_lead`, `list_leads`, and `request_approval` (Invariant A-007) and registered in `marketing_plugin/__init__.py`.
- Antigravity CLI Adapter: Safe reasoning execution with automatic secret redaction, 24KB prompt truncation protecting Windows buffer limits, and `--dangerously-skip-permissions` omitted.
- Synthetic & Freelance test fixtures: 12 synthetic fixtures in `tests/fixtures/` and 4 static freelance fixtures in `tests/fixtures/freelance/` (Bahr Next.js JSON/HTML, Mostaql HTML, Khamsat HTML).
- Test suite & control plane: Comprehensive unit and integration test suite passing cleanly (59 passed in ~1.6s, 100% pass rate), static control plane checks, hook self-tests, and secret scans all passing.
- Test suite & control plane: Comprehensive unit and integration test suite passing cleanly (62 passed in ~1.3s, 100% pass rate), static control plane checks, hook self-tests, and secret scans all passing.
- CAPSULE-002 & T-09 External Gates: Independent verification (`verifier`) and acceptance review (`reviewer`) PASSED with zero findings; Heavy Risk Review (`heavy-reviewer`) PASSED (Low residual risk). All repairs (01: qualification truth & dynamic source lookup, 02: deterministic rowid tie-breaker) verified.
- GitHub repository & Merge: Fast-forward merged `candidate/t09-freelance-adapters` into `main` and pushed to `https://github.com/YazanAi-Dev3/MarketingOS` (tracked on `origin/main`).
- CAPSULE-003 (Phase 1 Scanner Pipeline & Entity Deduplication): COMPLETED, merged to `main`, and pushed to public GitHub repository (`https://github.com/YazanAi-Dev3/MarketingOS`).
- CAPSULE-004 (Lead Scoring & AI Qualification Engine): COMPLETED, merged to `main`, and pushed to public GitHub repository (`https://github.com/YazanAi-Dev3/MarketingOS`).
- CAPSULE-005 (Telegram Operator Bot & Interactive Approvals): COMPLETED, merged to `main`, and pushed to public GitHub repository (`https://github.com/YazanAi-Dev3/MarketingOS`).
- CAPSULE-006 (Content Engine & Multi-Platform Drafting): COMPLETED, merged to `main`, and pushed to public GitHub repository (`https://github.com/YazanAi-Dev3/MarketingOS`).
- CAPSULE-007 (Social Publishing Scheduler & Postiz Adapter): COMPLETED on candidate branch `candidate/capsule-007-publishing-scheduler`.
  - `PostizAdapter` (`marketing_plugin/adapters/postiz_adapter.py`): Self-hosted Postiz REST client (A-021) with health checks, channel listing, post scheduling, secret sanitization (A-018, I-05), and hermetic mock mode.
  - `PublishingService` (`marketing_plugin/services/publishing_service.py`): Orchestrates publication of approved content assets, enforcing strict human approval check against SQLite (A-007, I-02), direct Telegram broadcasting, Postiz dispatch, and graceful manual export fallback when Postiz is offline (R-04).
  - Hermes Domain Tool: `publish_content` added to `marketing_plugin/tools/domain_tools.py` and exported in package root `marketing_plugin`.
  - Comprehensive Verification Suite: `tests/unit/test_postiz_adapter.py` (7 tests), `tests/unit/test_publishing_service.py` (6 tests), and `tests/integration/test_publishing_pipeline.py` (3 tests) covering approval gate security, direct Telegram, Postiz automated dispatch, and offline manual export fallback.
  - Full test suite: 132 tests passing cleanly (100% pass rate in ~2.0s).

Next immediate steps (Phase 3):
1. Conversation Intake & Inbound DM Qualification (Telegram / WhatsApp / Email inbound lead capture, intent recognition, entity extraction, and lead pipeline ingestion).
2. Outbound outreach generation & human approval dispatch.

