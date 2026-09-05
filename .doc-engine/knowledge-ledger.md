# Marketing OS — Frozen Knowledge Ledger

> Snapshot: 2026-09-03 · Version 1.0 · Source: project conversation + user decisions + current official external verification where noted.

## Project identity
- `CONFIRMED` — Internal marketing/sales intelligence and content system for a small startup serving technology clients and technical/academic customers.
- `CONFIRMED` — Target geographies: Saudi Arabia, UAE, Qatar, Syria, Bahrain, Oman, Jordan, Lebanon, Turkey.
- `CONFIRMED` — Existing paid resources: VPS, Google AI Pro/Antigravity, Codex. No new paid service/subscription should be required.
- `CONFIRMED` — The active engineering harness is Antigravity-native. Codex is outside this control plane and is forbidden from runtime marketing operations.

## Confirmed decisions
- `A-001` Internal-tool identity; working name “Marketing OS”.
- `A-002` MVP = Market Radar + Content Engine + Conversation Intake.
- `A-003` Separate B2B and academic funnels over one shared platform.
- `A-004` All nine target countries supported from V1.
- `A-005` Geographic allocation is manually weighted via config/CLI; the system may recommend but never mutate weights autonomously.
- `A-006` Service priority order: AI services → technical/academic services → general software systems.
- `A-007` Graduated autonomy: research/analysis/storage automatic; externally visible actions require human approval initially.
- `A-008` Academic services are limited to legitimate learning, mentoring, review, debugging, implementation support, and similar assistance; no deceptive submission of assessed work as the student's own.
- `A-009` Hermes is the base agent product/runtime; avoid core modifications when Skills/Plugins/configuration suffice.
- `A-010` Reuse mature OSS components before custom implementation.
- `A-011` Hermes session/memory storage is separate from marketing domain data.
- `A-012` MVP marketing data uses SQLite plus filesystem raw artifacts; PostgreSQL is deferred.
- `A-013` MVP operator interfaces = CLI + private Telegram control surface.
- `A-014` Automated acquisition uses public sources accessible without bypassing authentication/protection; private sources require manual or authorized integration.
- `A-015` Sources are discovered dynamically through taxonomy + country profiles + search intent + a learned Source Registry; no fixed URL list.
- `A-016` Self-hosted SearXNG is the preferred metasearch backend.
- `A-017` Every material signal/lead assessment must preserve evidence and provenance.
- `A-018` Broad-context policy: send large relevant context to Antigravity when useful; always remove passwords, API keys, tokens, credentials/secrets, and content whose disclosure is prohibited.
- `A-019` Runtime model policy: Antigravity/Google only. Antigravity Headless CLI preferred; Gemini API is fallback. Codex is prohibited from runtime inference.
- `A-020` Zero incremental-cost boundary remains governing: no paid SaaS or paid API usage without an explicit future superseding decision; Gemini API fallback must stay within free/existing allowance unless this constraint changes.
- `A-021` Postiz self-hosted is the preferred social publishing/scheduling layer after smoke verification.
- `A-022` WhatsApp is a human conversion channel in V1; no WhatsApp API dependency is required for MVP acceptance.
- `A-023` Technical success criteria are separated from commercial outcome; first paying client is the primary business outcome, not the sole software acceptance test.
- `A-024` No vector DB/RAG architecture is required in MVP; use direct files/structured data/FTS until scale proves need.
- `A-025` No web dashboard in MVP; terminal and Telegram are sufficient.
- `A-026` Both founders are admins in V1; mutating actions record `actor_id`.
- `A-027` Source quality is task-specific/multidimensional, not a single global reputation score.
- `A-028` Content strategy is derived from market signals, service priorities, interaction feedback, and platform adaptation rather than generic caption generation.
- `A-029` Scheduled work uses Hermes scheduling/runtime primitives where adequate; external user-facing actions retain approval gates.
- `A-030` Search combines exploitation of known high-yield sources with controlled open discovery; exact allocation is calibrated.
- `A-031` `REJECTED` — Codex as runtime/model provider for the marketer.
- `A-032` `REJECTED` — Rebuilding a custom agent framework instead of customizing Hermes.
- `A-033` `REJECTED` — Fixed source URL lists as the primary discovery strategy.
- `A-034` `REJECTED` — Unbounded “search the web” behavior without geography/source-intent controls.
- `A-035` `REJECTED` — Fully autonomous cold outreach/public posting from day one.
- `A-036` `REJECTED` — New paid CRM/automation/social SaaS under the current cost constraint.

## Calibrations
- `M-01` Lead score weights and qualification thresholds.
- `M-02` Source capability scores and trust/degradation thresholds.
- `M-03` Manual geographic weights for the nine countries.
- `M-04` Exploit-versus-discover search allocation.
- `M-05` Mapping service priority classes into actual search/content/lead-routing weights.
- `M-06` Content quality/approval rubric and publication cadence.
- `M-07` Evidence required before promoting any external action from approval-required to automatic.
- `M-08` Crawl frequency, concurrency, page budgets, timeouts and per-job limits.
- `M-09` Data retention/storage budget on the VPS.
- `M-10` Antigravity model/effort routing for quality/latency/quota efficiency.
- `M-11` Country/sector query lexicons and language mix.
- `M-12` Business KPI baselines: qualified leads, replies, conversations, meetings, conversions.
- `M-13` Backup cadence, practical RPO/RTO and restore-test frequency.

## Investigations
- `T-01` Blocking: prove a stable Hermes ↔ Antigravity Headless integration path without using Codex; verify structured output, auth persistence, failures, concurrency and capability boundaries.
- `T-02` Blocking for regional discovery: benchmark SearXNG result quality/localization across representative Arabic/English/Turkish/French queries and target countries.
- `T-03` Blocking for automatic social publishing: self-host Postiz and prove real Instagram + Telegram publish/schedule operations using owned accounts.
- `T-04` Non-blocking: verify any official WhatsApp zero-incremental-cost integration path; manual WhatsApp remains the V1 substitute.
- `T-05` Conditional fallback: verify selected Gemini API model, free-tier/zero-spend eligibility, structured output/tool support, data policy and Hermes adapter path if `T-01` fails.
- `T-06` Blocking before all services share one VPS: capacity smoke test for Hermes + SearXNG + Postiz stack and storage growth.
- `T-07` Before Instagram automation: verify account/app permissions and provider credential prerequisites with the actual company account.
- `T-08` Before implementation lock: pin a Hermes version and verify plugin/skill interfaces used by the design.

## Deferred
- `D-01` WhatsApp API automation — trigger: proven compliant zero/approved-cost path plus enough inbound volume.
- `D-02` Autonomous public posting — trigger: calibrated quality and low edit/rejection rate.
- `D-03` Autonomous outbound outreach — trigger: proven message quality, account safety and explicit promotion decision.
- `D-04` Web dashboard — trigger: Telegram/CLI become operationally insufficient.
- `D-05` PostgreSQL migration — trigger: concurrency/volume/analytics exceed SQLite comfort or multiple services need stronger transactional access.
- `D-06` Vector DB/RAG — trigger: direct/FTS retrieval fails measurable knowledge-retrieval evaluation.
- `D-07` Fine-grained RBAC — trigger: team expands beyond the two founders or external operators are added.
- `D-08` Full Google Workspace automation — trigger: recurring manual Gmail/Drive/Sheets workflows create measurable friction.
- `D-09` Omnichannel inbox such as Chatwoot — trigger: inbound volume becomes difficult to manage in native channels.
- `D-10` LangGraph/durable workflow framework — trigger: branching/pause-resume/recovery complexity outgrows Hermes-native orchestration.
- `D-11` Marketing automation suite/CRM — trigger: lead volume, lifecycle automation and campaigns exceed the internal store/operator flow.
- `D-12` Private/authenticated source connectors — trigger: a specific source proves high-value and an authorized stable integration exists.
- `D-13` Automatic geographic reweighting — trigger: enough conversion data exists and founders explicitly allow automatic mutation.
- `D-14` Learned lead/source ranking models — trigger: enough labeled outcomes exist to beat calibrated deterministic/model-assisted scoring.
- `D-15` Multi-node/distributed deployment — trigger: single-VPS resource limits are proven bottlenecks.


## v2 additions — 2026-09-05
- A-037: Crawl4AI primary rich acquisition; direct HTTP/API when sufficient.
- A-038: Clients Hunter donor/selective migration.
- A-039: Mostaql/Khamsat/Bahr specialized adapter candidates gated by T-09.
- A-040: legacy raw credentials/archive/database quarantine; sanitized fixtures only.
- A-041: source adapter promotion requires measured value (M-14).
- A-042: SearXNG discovery is separate from authoritative acquisition.
- A-043: engineering agents fixed to Gemini 3.8 Flash High/High; only Orchestrator delegates, max 2 active subagents.
- T-09: current-site adapter revalidation.
- M-14: adapter promotion calibration.
- R-05: legacy credential/noise migration risk controlled.
