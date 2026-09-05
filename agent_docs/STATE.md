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

Foundation milestones completed:
- Domain schemas: Pydantic models for all 16 core domain entities in `schemas/models.py` (including `AgentRun` and `ActorType`/`outcome_tag` on `Interaction`).
- SQLite storage & migrations: `migrations/001_initial_schema.sql` (17 tables including `schema_migrations`, WAL mode, foreign keys, indexes, pre-migration `.bak` snapshots, busy_timeout=5000ms) and `database.py` automated migration runner.
- Domain repositories: 7 repositories in `marketing_plugin/repositories/` (`AgentRunRepository`, `SourceRepository`, `CompanyRepository`, `EvidenceRepository`, `LeadRepository`, `ApprovalRepository`, `Database`) with explicit transaction commits and WAL multi-connection persistence.
- Deterministic secret redactor: `marketing_plugin/policies/redactor.py` scrubbing API keys, bearer tokens, private keys, AWS keys, and URL passwords before reasoning payloads or storage (Invariant I-05).
- Acquisition & Search layer: `SearXNGAdapter`, `RegionalQueryPlanner`, and `AcquisitionRouter` with per-hop redirect SSRF validation (max 5 hops), DNS fail-closed checks, integer/decimal loopback IP blocking, and SHA-256 evidence hashing.
- Antigravity CLI Adapter: Safe reasoning execution with automatic secret redaction, 24KB prompt truncation protecting Windows buffer limits, and `--dangerously-skip-permissions` omitted.
- Synthetic test fixtures: 12 fixtures in `tests/fixtures/synthetic_corpus.py` and `evaluation_seeds.py` (GCC, Levant, North Africa, Turkey SaaS, stale posts, tenders, duplicate merge/split, prompt injection, academic integrity).
- Test suite & control plane: Comprehensive unit and integration test suite passing cleanly (100% pass rate), static control plane checks, hook self-tests, and secret scans all passing.

Next immediate steps:
1. Complete independent external review gate confirmation (`reviewer` + `heavy-reviewer`).
2. `T-09`: Mostaql/Khamsat/Bahr adapter verification before specialized implementation.
3. Implement Hermes plugin registration hook in `marketing_plugin/` exposing domain tools (`scan`, `lead_assess`, `lead_list`).
