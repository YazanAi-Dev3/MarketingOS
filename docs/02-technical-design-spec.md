# Marketing OS — Technical Design Specification

> Version 2.0 · 2026-09-05 · Documentation-ready · Implementation-facing specification

## Contents

هذا المستند يحدد العقود والبيانات والحالات والـpipelines التي سيُنفذها المشروع. أسماء المكونات هنا يجب أن تطابق `07-high-level-design.md`.

## 1. Domain and data model

### 1.1 Authorities

- **Hermes State:** sessions, conversational context, agent/plugin/skill runtime metadata.
- **Marketing Domain Store (`marketing.db`):** source registry, companies, evidence, signals, leads, assessments, content, approvals, interactions, run accounting.
- **Raw Artifact Store:** fetched HTML/text/snapshots and source-response payloads needed for traceability/reprocessing.
- **Configuration Store:** country priorities, service priorities, query lexicons/policies, source taxonomy. Configuration is versioned in Git; secrets are not.

`A-011` forbids treating Hermes session memory as the authoritative marketing database.

### 1.2 Core entities

#### `CountryProfile`

```text
country_code PK
name
languages[]
enabled
manual_weight
query_lexicon_version
source_policy_version
updated_at
updated_by
```

Invariant: an enabled country cannot enter scheduled production scans until `manual_weight` is explicitly set (`M-03`).

#### `ServiceProfile`

```text
service_key PK
priority_class {primary, secondary, tertiary}
enabled
allowed_funnels[]
offer_summary
qualification_policy_version
```

Confirmed priority classes follow `A-006`; numeric operational mapping is `M-05`.

#### `Source`

```text
source_id PK
domain_or_platform_key
country_scope[]
source_family
languages[]
status {candidate, trusted, degraded, blocked, dead}
first_seen_at
last_seen_at
last_success_at
access_mode {public, authorized_connector, manual}
metadata_json
```

#### `SourceCapabilityScore`

One row per source × capability:

```text
source_id FK
capability {company_discovery, buying_signal, contact_discovery, trend_intelligence,
            content_intelligence, sector_mapping, authority}
score
sample_count
last_updated_at
score_version
```

A source has no single universal quality score (`A-027`).

#### `SearchRun`

```text
search_run_id PK
intent
country_code
service_key nullable
query_plan_json
engine_profile
config_snapshot_hash
started_at
finished_at
status
result_count
error_summary
```

#### `SearchResult`

```text
search_result_id PK
search_run_id FK
url
normalized_url
title
snippet
rank
engine_sources[]
discovered_at
```

#### `Company`

```text
company_id PK
canonical_name
primary_domain nullable
country_code
city nullable
sector nullable
public_contacts_json
funnel {b2b, academic}
entity_confidence
created_at
updated_at
```

Identity resolution uses domain first, then normalized name + contact/social evidence. Ambiguous merges require review rather than destructive merge.

#### `Evidence`

```text
evidence_id PK
company_id nullable
source_id FK
url
artifact_path nullable
observed_at
published_at nullable
fact_type
fact_text
extractor {deterministic, model_assisted, manual}
content_hash
confidence
```

`fact_text` must remain a factual observation, not a business interpretation (`A-017`).

#### `Signal`

```text
signal_id PK
company_id FK
type
summary
evidence_ids[]
confidence
model_or_rule_identity
created_at
valid_until nullable
```

Examples: hiring, expansion, weak lead handling, manual WhatsApp workflow, missing localization, new branch, procurement demand.

#### `Lead`

```text
lead_id PK
company_id FK
funnel
status {discovered, qualified, rejected, outreach_ready, contacted,
        replied, meeting, proposal, won, lost, dormant}
priority_bucket
recommended_service_key
owner nullable
next_action nullable
created_at
updated_at
```

#### `LeadAssessment`

Append-only assessment snapshot:

```text
assessment_id PK
lead_id FK
assessment_version
fit_score
pain_score
urgency_score
reachability_score
final_score
confidence
recommended_service_key
evidence_ids[]
reasoning_summary
provider_identity
prompt_contract_version
created_at
```

Old assessments are never overwritten; current view points to latest valid assessment.

#### `ContentIdea`

```text
content_idea_id PK
funnel
market_scope[]
service_key
source_signal_ids[]
topic
objective {trust, education, demand_capture, direct_offer, case_style}
score
status {proposed, selected, rejected, archived}
```

#### `ContentAsset`

```text
content_asset_id PK
idea_id FK
master_content
platform {instagram, telegram, whatsapp_manual, other}
format
body
media_brief nullable
cta
status {draft, awaiting_approval, approved, rejected, scheduled, published, failed}
version
```

#### `Approval`

```text
approval_id PK
action_type
target_type
target_id
requested_at
resolved_at nullable
actor_id nullable
decision {pending, approved, rejected, rewrite_requested}
notes nullable
```

#### `Interaction`

```text
interaction_id PK
lead_id nullable
channel
external_party_ref nullable
direction {inbound, outbound}
content_summary
raw_content_path nullable
occurred_at
actor {human, agent_draft, external}
outcome_tag nullable
```

#### `AgentRun`

```text
agent_run_id PK
task_type
provider_path
model_identity nullable
input_refs[]
input_size_estimate
output_contract_version
started_at
finished_at
status
error_class nullable
approval_required
```

## 2. Core conceptual / computational model

Marketing OS separates four semantic levels:

```text
Source → Evidence → Signal → Decision/Action
```

- **Source:** where information came from.
- **Evidence:** observable fact.
- **Signal:** interpretation relevant to business.
- **Decision/Action:** qualification, content idea, outreach recommendation.

This granularity exists so a model can be wrong about the interpretation without corrupting the underlying fact, and so decisions can be re-evaluated when scoring/prompt policies change.

## 3. Input/document/event lifecycle

### 3.1 Web discovery lifecycle

```text
query planned
→ search executed
→ URLs normalized/deduplicated
→ source candidates registered
→ fetch/extract
→ artifact hashed/stored
→ evidence extracted
→ company resolved
→ signals derived
→ lead/content evaluation
```

### 3.2 Reprocessing

Reprocessing is idempotent by `(normalized_url, content_hash, extractor_version)`. New content hash creates new evidence rather than mutating historical evidence. Derived signals/assessments include their generating version, so they can be superseded safely.

### 3.3 Source lifecycle

```text
candidate → trusted
    ↓          ↓
 blocked   degraded
    ↓          ↓
  dead ← repeated failures / explicit removal
```

A degraded source may still be queried with reduced weight. `dead` is reversible only by operator action or a successful re-validation job.

## 4. Normalization / canonicalization / validation

Order is mandatory:

1. URL canonicalization (scheme/host normalization, tracking-parameter removal where safe).
2. Text extraction/encoding normalization.
3. Country/language classification.
4. Entity normalization.
5. Contact normalization.
6. Evidence schema validation.
7. Duplicate/replay detection.
8. Store evidence.
9. Only then run expensive model interpretation.

Untrusted HTML/scripts are never executed merely to extract text. Browser automation is invoked only when static extraction fails and policy allows it.

## 5. Complex data types and rendering

Raw HTML, screenshots, media and large reports are stored as files and referenced by immutable path/hash. SQLite stores metadata and derived text, not every binary blob. Large context may be assembled for Antigravity (`A-018`) but secrets are scrubbed first.

## 6. Policy classes / authorization / disclosure / behavior taxonomy

### 6.1 Action classes

| Class | Examples | V1 behavior |
|---|---|---|
| `INTERNAL_READ` | search, read evidence, inspect DB | automatic |
| `INTERNAL_WRITE` | store evidence, score lead, draft content | automatic + audit |
| `EXTERNAL_DRAFT` | outreach draft, reply suggestion | automatic draft only |
| `EXTERNAL_PUBLISH` | publish/schedule social content | approval required |
| `EXTERNAL_SEND` | cold email/DM/message | approval required |
| `COMMERCIAL_COMMITMENT` | price/proposal/contract promise | human-only |
| `SENSITIVE_ACADEMIC` | assessed-work request | policy gate; refuse deceptive completion |

### 6.2 Authority

Both founders are admin (`A-026`). Telegram user/chat allowlist and local CLI OS access are the V1 authorization boundary.

## 7. Unitization / work-item representation

Every background operation is a `Job` concept even if implemented using Hermes scheduler primitives:

```text
job_id
type
country/service scope
config_snapshot
input_refs
status {queued, running, succeeded, partial, failed, cancelled}
started/finished
retry_count
error_class
output_refs
```

The system must never infer job completion solely from an agent message; completion requires persisted output contract validation.

## 8. Linking/alignment/coverage/relationship inference

### Company resolution

Priority of identity evidence:

1. exact normalized domain;
2. verified public contact/social link shared across records;
3. normalized legal/trading name + country/city;
4. model-assisted similarity only as a candidate merge, never an automatic destructive merge below calibrated confidence.

### Evidence coverage

A lead assessment must reference at least one evidence item for each claimed pain/opportunity. Missing support downgrades confidence or forces abstention.

## 9. Retrieval/query/selection pipeline

### 9.1 Inputs

`country priorities + service priorities + funnel + search intent + source registry history + query lexicon`.

### 9.2 Query planning

The Query Planner creates multilingual query groups according to CountryProfile. Examples are generated from taxonomy concepts rather than hard-coded websites: chamber, tender, hiring, expansion, directory, company website, public social, local business news, etc. (`A-015`).

### 9.3 Source allocation

For each intent:

```text
manual country weight
× service priority mapping
× source capability score
× freshness/health modifier
× exploration policy
```

Exact weights are calibration (`M-02`–`M-05`). The agent can propose config changes but cannot write country weights automatically (`A-005`).

### 9.4 SearXNG contract

Preferred interface: self-hosted `/search` returning JSON. Adapter must pass query, language where supported, categories/engine profile, time range when useful, and retain engine provenance. `T-02` decides the engine mix and regional quality.

## 10. Confidence, validation, rejection, or decision gates

### Evidence gate

Reject model-produced factual claim when its referenced evidence IDs do not exist or do not support the statement on inspection.

### Lead gate

Before `qualified`:

- company identity confidence acceptable;
- at least one actionable service match;
- evidence-backed pain/opportunity or strong fit;
- no policy conflict;
- score threshold from `M-01`.

### Abstention

Model output must support `insufficient_evidence=true`. It is preferable to miss a lead than fabricate a pain point.

## 11. Session/state model

Hermes session context is interaction convenience, not business truth. Every command that mutates marketing state writes to `marketing.db` and records `actor_id` or `agent_run_id`.

Telegram conversations map to founder operator sessions. Long-running jobs return a job ID and later push a result; the operator does not need to keep a chat context alive.

## 12. Classification/gating before expensive work

Before Antigravity:

1. URL/source health checks.
2. deterministic extraction.
3. duplicate detection.
4. minimum content threshold.
5. country/service relevance heuristics.
6. secret scrubber.
7. task-specific context selection.

Only shortlisted items reach model reasoning. This preserves quota without limiting useful context once a task is selected.

## 13. Router/orchestrator/dispatch paths

### Path A — Scheduled market scan

`Hermes Scheduler → Query Planner → SearXNG → Extractor → Source Registry → Evidence Store → Signal/Lead Analyzer → marketing.db → Telegram Digest`.

### Path B — Analyze one URL

`CLI/Telegram → URL validation → Extractor → Entity Resolver → Evidence → Antigravity analysis → Lead report → operator`.

### Path C — Content ideation

`Content command/schedule → recent signals + service priorities + previous outcomes → Antigravity strategist → ContentIdea rows → Telegram review`.

### Path D — Content production/publishing

`approved idea → master asset → platform adapters → approval → Postiz → publish/schedule → publication status`. `T-03` must pass first.

### Path E — Conversation intake

`founder pastes/logs message or native/manual WhatsApp interaction → interaction row → classification/draft → founder response → outcome logging`.

## 14. Prompt/request assembly and output contract

### 14.1 Context assembly order

1. task instruction/version;
2. relevant company/service/country policy;
3. full or broad evidence/context as useful (`A-018`);
4. prior outcome context if relevant;
5. explicit tool/action boundaries;
6. required JSON schema.

### 14.2 Secret scrubber

Before provider invocation, scan text/attachments/config for at minimum:

- passwords;
- API keys;
- bearer/session tokens;
- OAuth client secrets/refresh tokens;
- private keys;
- database credentials/DSNs containing secrets;
- platform access tokens;
- explicitly marked confidential-not-for-model material.

A scrub event is logged without logging the secret value.

### 14.3 Lead-analysis output

```json
{
  "company_id": "...",
  "funnel": "b2b",
  "recommended_service": "...",
  "scores": {"fit": 0, "pain": 0, "urgency": 0, "reachability": 0},
  "final_score": 0,
  "confidence": 0.0,
  "pain_points": [
    {"summary": "...", "evidence_ids": [1, 2], "confidence": 0.0}
  ],
  "next_action": "...",
  "insufficient_evidence": false
}
```

Numeric scales/thresholds are defined by `M-01`; schema semantics are stable.

### 14.4 Content-strategy output

Must include objective, audience/funnel, market scope, service, evidence/signal references, master angle, platform variants to create, CTA, and risk/claim notes.

## 15. Adaptive strategies / domain strategies

### Geography

Country profiles adapt language/query vocabulary/source-family weighting. Turkey is Turkish-first; Lebanon may include French; Gulf countries use Arabic+English; Syria can weight public social/community discovery more heavily if `M-02` proves it productive. These are policy templates, not assumptions about final source yield.

### Funnel

B2B scoring emphasizes organization fit, operational pain, expansion/hiring/procurement signals and reachability. Academic scoring emphasizes technical subject fit, legitimate assistance scope, timing and service compatibility.

## 16. Tools/internal capabilities

### Hermes built-ins/reused capabilities

- CLI/TUI/gateway/session runtime.
- Telegram messaging gateway.
- scheduler/cron.
- web extraction/browser/search capabilities as supported by pinned version.
- skills/plugins/tool registry.

Exact pinned capabilities are verified by `T-08`.

### Custom Marketing Plugin responsibilities

- config loading/validation;
- Source Registry CRUD;
- marketing.db migrations/repositories;
- entity/evidence/lead state transitions;
- SearXNG adapter/profile selection;
- Antigravity bridge;
- Postiz dispatcher;
- audit/event log;
- metrics extraction.

### Skills

- regional-source-discovery;
- lead-qualification;
- academic-funnel-policy;
- content-strategy;
- platform-adaptation;
- outreach-drafting;
- source-evaluation.

## 17. Security/content/data protection rules

1. Public web text is **untrusted data**, not instructions.
2. Web content cannot modify tool permissions, system policy or configuration.
3. Antigravity receives broad context only after secret scrubber.
4. Telegram bot/control surface is allowlisted to founder identities/chat IDs.
5. External actions require persisted approval record; prompt text cannot bypass it.
6. No crawler bypass of authentication, CAPTCHAs, private groups or access controls (`A-014`).
7. Credentials live in environment/secret files excluded from Git; never in `marketing.db` text fields.
8. Academic policy gate runs before offer/outreach generation for that funnel.
9. Every external integration has timeout and bounded retry; no infinite agent loop.

## 18. Accounts/entitlements/billing state

No product billing/tenant accounts. Operational resource state includes:

- Antigravity authenticated/healthy;
- optional Gemini API fallback enabled/disabled;
- Postiz integration connection state;
- SearXNG health;
- Telegram allowlist;
- `paid_usage_allowed=false` circuit breaker under `A-020`.

## 19. Export/import/interoperability

- CSV/JSON export for leads, sources, interactions and content.
- Manual import for private-source observations and historical leads.
- Config in YAML.
- Raw evidence referenced by portable relative paths where feasible.
- Database migrations versioned; future PostgreSQL migration must preserve IDs/provenance.

## 20. Evaluation framework

### Independent test sets/fixtures

Create synthetic/curated fixture corpus with:

- relevant and irrelevant company pages;
- duplicate companies with name variants;
- stale/contradictory evidence;
- multilingual Arabic/English/Turkish/French examples;
- prompt-injection text inside web pages;
- secrets inserted into test context to prove scrubber;
- academic legitimate vs disallowed requests;
- content claims with/without evidence.

### Metrics

- evidence precision on curated pages;
- company dedup/entity resolution accuracy;
- source relevance@k by intent/country (`M-11`);
- lead human-acceptance/ranking agreement (`M-01`);
- unsupported-claim rate (target conceptually zero; actual regression gate defined after fixture baseline);
- content approval/rewrite/rejection rates (`M-06`);
- job success/partial/failure rates;
- business KPIs (`M-12`).

### Regression gates

A release cannot knowingly increase unsupported factual claims, bypass approvals, leak fixture secrets, or break evidence references. Numeric tolerances are set after baseline rather than fabricated now.

### Human evaluation

Founders judge lead usefulness, service match, evidence sufficiency, tone, content relevance and action readiness. Store evaluation labels so later `D-14` can use them.

### Drift/performance monitoring

Monitor source yield, engine failures, provider output contract failures, approval edit distance, and source-to-qualified-lead contribution.

### Calibration procedure

All empirical thresholds are owned by `M-01`–`M-13`; do not hard-code undocumented values.

## 21. Cost/resource/observability accounting

For each external/expensive operation record:

- provider/search integration;
- run/task;
- estimated input/output size when available;
- latency;
- success/failure;
- retry count;
- quota/cost metadata if exposed;
- resulting entity/evidence/action IDs.

`paid_usage_allowed=false` is checked before any API path that may incur spend (`A-020`).

## 22. Administrative/operator surface

Planned CLI command families (names may adapt to Hermes conventions):

```text
marketing status
marketing scan --country SA --intent leads
marketing source list|inspect|recheck
marketing lead list|inspect|assess
marketing content ideas|draft|approve|reject
marketing interaction add
marketing config countries|services show|set
marketing jobs list|inspect|retry
marketing provider health
```

Telegram exposes a safe subset: status, digest, leads, inspect, generate draft, approve/reject content, job health. Raw config/secrets are never editable from Telegram in V1.

## 23. End-to-end critical flow walkthrough

### 23.1 Scheduled B2B opportunity discovery

1. Scheduler creates `SearchRun` using current country/service config snapshot.
2. Query Planner selects country by manual allocation (`M-03`) and search intent.
3. Source Registry supplies high-value known sources; discovery policy adds open SearXNG queries (`A-030`).
4. SearXNG returns candidates with engine metadata.
5. Extractor fetches publicly accessible content; failures are classified.
6. Entity Resolver maps result to source/company; raw artifact is hashed/stored.
7. Evidence Extractor creates factual rows.
8. Deterministic gates remove duplicates/weak candidates.
9. Secret scrubber sanitizes assembled context.
10. Antigravity analyzes shortlisted company evidence through `T-01`-validated path.
11. Output schema is validated; referenced evidence IDs are checked.
12. Lead/assessment is persisted.
13. Digest ranks qualified leads and sends internal Telegram notification.
14. Founder inspects evidence and requests an outreach draft.
15. Draft is generated; no external send occurs without human action (`A-007`).
16. Outcome is later logged and contributes to `M-01`,`M-02`,`M-12`.

### 23.2 Content flow

1. System aggregates recent high-value signals, frequent pains, service priorities and past interaction outcomes.
2. Antigravity proposes evidence-linked `ContentIdea` objects.
3. Founder selects an idea.
4. Content agent creates master content and platform variants, not blind copy-paste (`A-028`).
5. Founder approves/rejects/rewrite-requests.
6. Approved asset goes to Postiz only if `T-03` passed; otherwise operator receives export/manual publish instructions.
7. Publication ID/status is stored; later engagement/inquiry outcome is attached when accessible.

### 23.3 Failure example — Antigravity unavailable

- No lead/content model analysis is fabricated.
- deterministic collection/evidence storage may continue.
- pending analysis jobs remain retryable.
- if `T-05` approved and zero-spend fallback enabled, Gemini API may be used according to task routing.
- otherwise Telegram reports degraded intelligence mode and waits for Antigravity recovery.

## v2 acquisition contract — authoritative addendum

This addendum supersedes any implementation inference that page acquisition should be hand-built around BeautifulSoup/Playwright. Under `A-037/A-042`, the pipeline is:

```text
Search Intent → Query Planner → SearXNG discovery → Acquisition Router
  → direct public API/HTTP when sufficient
  → otherwise Crawl4AI for rich crawling/rendering/extraction
  → Source Adapter → normalized Evidence/provenance
```

A SearchResult is discovery metadata. Material Signal confidence cannot rely only on its snippet. `Evidence` must identify acquired/manual authoritative content and extraction method.

Clients Hunter migration obeys `A-038/A-040`: useful behavior is cleanly reconstructed inside current ownership; legacy Firebase/Firecrawl/Streamlit/runtime schemas are not compatibility targets. Mostaql/Khamsat/Bahr adapters remain disabled until their individual `T-09` revalidation. Generic sources can be promoted to specialized adapters only after `M-14` evidence.

