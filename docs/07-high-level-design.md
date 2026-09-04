# Marketing OS — High-Level Design (HLD)

> Version 1.0 · 2026-09-03 · Documentation-ready · Architecture source

## 1. Governing architecture principle

> **Customize Hermes; do not recreate it. Keep marketing domain state explicit, evidence-grounded and independent from the model/runtime.**

The architecture deliberately separates:
- **runtime/platform capability** supplied by Hermes;
- **marketing domain capability** supplied by our plugin/skills/config;
- **search/publishing infrastructure** supplied by mature OSS;
- **reasoning** supplied by Google/Antigravity;
- **human authority** for externally visible actions.

## 2. Layers/bounded contexts and dependency rules

```text
┌─────────────────────────────────────────────────────┐
│ Operator Surfaces                                   │
│ CLI / private Telegram                              │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ Hermes Runtime                                      │
│ gateway · sessions · skills · plugins · cron        │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ Marketing Domain Layer                              │
│ query planning · sources · evidence · leads ·       │
│ content · approvals · interactions · analytics      │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
               ▼                  ▼
       Data/Collection       Reasoning Adapter
  SQLite/files/SearXNG       Antigravity → Gemini API*
               │                  │
               ▼                  ▼
         Public web          Google runtime
                                  (*conditional fallback)
                       │
                       ▼
              External Action Layer
             Postiz / native channels
                       │
                  human approval
```

### Strict dependency rules

1. Hermes runtime may call marketing tools; marketing domain must not rely on conversation memory as truth (`A-011`).
2. Model outputs may propose signals/assessments but cannot mutate authority without validated tool contracts.
3. Source/evidence records exist before model-derived decisions (`A-017`).
4. Publishing adapters consume `approved` actions only.
5. Codex is outside runtime (`A-031`).
6. Country/service policy lives in config, not prompt literals.
7. Upstream Hermes changes are consumed via pinned versions and extension interfaces.

## 3. Component inventory

### 3.1 Hermes Gateway

**Responsibility:** CLI/Telegram sessions, scheduler, tool/skill execution.  
**State:** Hermes-owned sessions/memory/cron metadata.  
**Dependencies:** Hermes upstream, Telegram.  
**Contract:** dispatch authenticated operator requests and scheduled jobs.  
**Failure:** CLI remains fallback if Telegram fails.

### 3.2 Marketing Plugin

**Responsibility:** expose domain tools and enforce boundaries.  
**State:** reads/writes `marketing.db` and artifact paths.  
**Public contract examples:** `scan`, `source_evaluate`, `lead_assess`, `lead_list`, `content_ideas`, `approval_resolve`, `interaction_log`.  
**Failure:** fail closed for mutation if DB/schema validation fails.

### 3.3 Policy/Configuration Layer

Owns:
- country weights;
- language/query lexicons;
- service priorities;
- source taxonomy;
- action/autonomy policy.

Manual country weights are authoritative (`A-005`).

### 3.4 Query Planner

Turns `(intent, country, funnel, service priorities, source registry history)` into multilingual query plans. It never selects arbitrary URLs as “official sources” without classification/evaluation.

### 3.5 SearXNG Adapter

Metasearch abstraction (`A-016`) returning normalized search candidates. It is replaceable; downstream code sees a stable result contract.

### 3.6 Collector/Extractor

Fetches public pages, normalizes text/metadata, stores raw artifact/hash, and emits Evidence candidates. Browser-capable extraction is limited to public access and policy.

### 3.7 Source Registry

Stores sources and task-specific capability scores (`A-027`). It enables exploit/discover balancing (`A-030`) without freezing a URL list.

### 3.8 Entity Resolver

Creates/merges Company candidates deterministically where confidence is high; ambiguous merges require review.

### 3.9 Evidence Store

Authoritative factual layer. Evidence is immutable per content hash/version semantics. It is the anchor for reproducibility.

### 3.10 Signal/Lead Intelligence

Rules + Antigravity derive Signals and LeadAssessments. Every claimed pain/opportunity references evidence IDs.

### 3.11 Antigravity Adapter / Provider Plugin

**Preferred runtime reasoning bridge (`A-019`).**

Candidate implementation after `T-01`:
- Hermes custom model-provider plugin if the protocol mapping is clean; or
- general Hermes tool/skill adapter invoking `agy` headless for bounded reasoning tasks.

Must support:
- structured JSON/schema;
- auth persistence;
- timeout/cancellation;
- no Codex fallback;
- secret redaction;
- provider/run metadata.

### 3.12 Content Engine

Produces:
`market pattern → idea → master content → platform asset`.

Grounding comes from evidence/service priorities/outcome feedback (`A-028`).

### 3.13 Approval Service

Persisted state machine guarding external actions. Telegram/CLI are only interfaces; approval truth is in marketing DB.

### 3.14 Postiz Adapter

Consumes approved content for scheduling/publishing after `T-03`. Postiz can be absent without breaking Market Radar.

### 3.15 Conversation Intake

Captures interactions/outcomes. WhatsApp remains human-operated in V1 (`A-022`); text can be logged/analyzed manually.

## 4. Runtime modes

### Interactive
Lead inspection, manual analysis, content review, approvals.

### Scheduled
Source discovery, scans, source health, daily digest, periodic analysis. Hermes cron is preferred where adequate (`A-029`).

### Deterministic no-model
Health checks, backups, dedupe, parsing, config validation, metrics rollups.

### Model-assisted
Lead interpretation, synthesis, content strategy, reply drafts.

## 5. Primary flows

### 5.1 Regional discovery

```text
Cron/CLI
→ Query Planner
→ SearXNG
→ normalize/dedupe
→ Source Registry
→ Collector
→ Evidence
→ Signal/Lead assessment
→ persisted results
→ Telegram digest
```

Failure of one engine/source yields `partial`, not false success.

### 5.2 On-demand company analysis

```text
Founder submits URL
→ public-access validation
→ collect/extract
→ entity resolve
→ evidence persist
→ Antigravity assessment
→ schema/evidence validation
→ lead view
```

### 5.3 Approval/publishing

```text
Content draft
→ Approval(pending)
→ founder approve
→ idempotency key
→ Postiz adapter
→ publish result
→ ContentAsset(published|failed)
→ analytics/outcome link
```

No Postiz call occurs on `pending/rejected`.

### 5.4 Conversation intake

```text
WhatsApp/Telegram/other interaction
→ manual/native intake
→ log Interaction
→ classify/draft with Antigravity if requested
→ founder responds
→ outcome tag
→ lead lifecycle + M-12
```

### 5.5 Provider flow

```text
Marketing task
→ redact secrets
→ select Google path
→ Antigravity adapter
       └─ failure/unsupported → Gemini API only if T-05 enabled
→ structured output validation
→ domain-level evidence checks
→ persist result
```

## 6. Data authority map

| Entity/state | Authority | Derived/rebuildable |
|---|---|---|
| Hermes sessions/memory | Hermes | not marketing truth |
| country/service config | versioned config | reloadable |
| Source/Company/Evidence/Lead | `marketing.db` | canonical domain state |
| raw source artifact | filesystem + hash ref | refetch where possible, not guaranteed |
| Signal/Assessment | `marketing.db` append-only/versioned | re-derivable from evidence |
| approval | `marketing.db` | authoritative |
| published remote post | external platform/Postiz result + local record | reconcile |
| provider response | stored validated result/metadata | rerunnable, not assumed stable |

## 7. Cross-cutting concerns

| Concern | Single enforcement point | Prevents | Verification |
|---|---|---|---|
| secrets | pre-provider redactor | credential leakage | synthetic leak tests |
| public-source boundary | collector URL/access policy | auth bypass | negative URL/access fixtures |
| provenance | Evidence contract | unsupported claims | assessment validator |
| approval | Approval Service/action wrapper | unauthorized posting/sending | replay/state tests |
| cost | provider allowlist/cost breaker | paid fallback | config/negative tests |
| country weights | config service | silent geographic drift | config audit |
| idempotency | job/action keys | duplicates | replay tests |
| audit actor | mutation layer | unattributed changes | DB constraint/tests |

## 8. Invariants

| # | Invariant | Enforcement | Verification |
|---|---|---|---|
| I-01 | Codex never runs marketer inference | provider allowlist | grep/config test |
| I-02 | external action needs approval | action wrapper | integration test |
| I-03 | every material lead claim cites existing evidence | assessment validator | golden set |
| I-04 | agent cannot mutate country weights | config write permissions/tool absence | negative test |
| I-05 | secrets never enter model payload | redactor | seeded secret test |
| I-06 | Hermes memory is not marketing source-of-truth | repository/service boundaries | architecture test/review |
| I-07 | duplicate approved action cannot publish twice | idempotency key | replay test |
| I-08 | rejected/dead source is not silently treated trusted | source state filter | unit test |
| I-09 | no paid provider fallback | provider config | smoke/negative test |

## 9. Deployment view

Single VPS contains all OSS runtime services initially; Google reasoning is external. Postiz is phase-gated because its dependency footprint is larger. See OPS for capacity/deployment details.

## 10. Degradation view

| Dependency failure | Still works | Unavailable | Behavior |
|---|---|---|---|
| Antigravity | deterministic/search/history | semantic tasks | queue/report |
| Gemini fallback disabled | Antigravity-only path | fallback | no spend |
| SearXNG | existing data/manual URL | broad discovery | partial scan |
| Telegram | CLI | mobile approvals | pending queue |
| Postiz | content/approval | auto-publish | manual publish |
| one country/source | other scopes | affected coverage | degrade score/report |
| Hermes scheduler | CLI/manual run | unattended jobs | alert/repair |

## 11. Extension points

- Hermes general plugin for marketing tools.
- Hermes model-provider plugin or tool adapter for Antigravity (`T-01`).
- country profiles/lexicons as data.
- search backend adapter.
- Postiz publishing adapter.
- future authorized source connectors (`D-12`).
- future PostgreSQL (`D-05`) behind repository interfaces.
- future RAG (`D-06`) only after benchmark trigger.

## 12. Traceability index

| Component | Detailed spec | Governing decisions | Tests/guards |
|---|---|---|---|
| Query Planner | TS §9 | A-004,A-005,A-015,A-030 | query fixtures |
| Source Registry | TS §1/9 | A-027 | score/state tests |
| Evidence Store | TS §1/3 | A-017 | provenance tests |
| Antigravity Adapter | TS provider sections | A-018,A-019,A-020,A-031 | T-01 + schema/security tests |
| Approval Service | TS §6 | A-007,A-026 | state/replay tests |
| Postiz Adapter | TS external action flow | A-021 | T-03/T-07 |
| Conversation Intake | TS entities/flows | A-022 | interaction fixtures |

## Appendix — Architecture review checklist

- [ ] Hermes core remains unmodified unless ADR.
- [ ] Component names match TS.
- [ ] source-of-truth ownership is singular.
- [ ] every external action goes through Approval Service.
- [ ] provider config cannot select Codex.
- [ ] dynamic sources are bounded by country/intent/taxonomy.
- [ ] evidence and signal layers remain distinct.
- [ ] degraded dependencies have explicit behavior.
