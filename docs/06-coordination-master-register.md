# Marketing OS — Coordination Master Register

> Version 1.0 · 2026-09-03 · Single coordination source of truth

## Identifier system

| Prefix | Meaning | Lifecycle |
|---|---|---|
| `A-###` | Product/architecture/operational decision | Confirmed, rejected, or superseded; never silently rewritten |
| `M-##` | Calibration | Method + acceptance criterion now; measured value later |
| `T-##` | Investigation/spike | Time-boxed verification that unlocks implementation |
| `D-##` | Explicit deferral | Reason + current substitute + activation trigger |
| `R-##` | Review finding | Created by audit; repaired or kept open |
| `ADR-####` | Durable implementation-era architecture record | Created only after ADR trigger |

## Documents

| ID | File | Applicability | Status | Version |
|---|---|---|---|---|
| IDX | `00-document-index.md` | Always | Current | 1.0 |
| CP | `01-project-checkpoint.md` | Core | Current | 1.0 |
| TS | `02-technical-design-spec.md` | Technical system | Current | 1.0 |
| OPS | `04-operations-deployment-security.md` | Operated system | Current | 1.0 |
| DOC | `05-documentation-workflow-guide.md` | Long-lived software | Current | 1.0 |
| REG | `06-coordination-master-register.md` | Always | **Governing registry** | 1.0 |
| HLD | `07-high-level-design.md` | Technical system | Current | 1.0 |
| ROAD | `08-future-roadmap.md` | Deferred scope exists | Current | 1.0 |
| REVIEW | `09-final-design-review.md` | Always, generated last | Current | 1.0 |
| PREP | `10-preimplementation-plan.md` | Before implementation | Current | 1.0 |
| AGENT | `11-ai-coding-agent-setup.md` | Antigravity used for engineering; Codex remains runtime-rejected | Current | 1.1 |
| PROVIDERS | `12-model-provider-guide.md` | External model/provider use | Current, volatile facts dated | 1.0 |
| BM | — | Monetized tool economics | Omitted: tool is internal; startup GTM constraints live in CP/TS | — |
| NFR | — | Separate contractual NFR artifact | Omitted: NFRs integrated into HLD/OPS/TS | — |
| ADR | `adr/` | Triggered after implementation starts | Not yet applicable | — |

## 1. Confirmed decisions

### 1.1 Product, scope and market

| ID | Decision | Status | Owning doc |
|---|---|---|---|
| `A-001` | Build an internal founder-operated “Marketing OS”, not a customer-facing SaaS product. | CONFIRMED | CP |
| `A-002` | MVP includes Market Radar, Content Engine, and Conversation Intake. | CONFIRMED | CP/TS |
| `A-003` | One platform, two separated funnels: B2B and technical/academic. | CONFIRMED | CP/TS |
| `A-004` | V1 supports Saudi Arabia, UAE, Qatar, Syria, Bahrain, Oman, Jordan, Lebanon and Turkey. | CONFIRMED | CP/TS |
| `A-005` | Geographic search allocation is manually configured via file/CLI; agent suggestions cannot mutate weights automatically. | CONFIRMED | TS |
| `A-006` | Service priority: AI services first, technical/academic services second, general software systems third. | CONFIRMED | CP/TS |
| `A-008` | Academic funnel supports legitimate mentoring/technical assistance, not deceptive completion of assessed work for submission as the student's own. | CONFIRMED | CP/OPS |
| `A-023` | Technical system success is measured separately from the business outcome; first paying client remains the primary business objective. | CONFIRMED | CP/TS |

### 1.2 Runtime, autonomy and interaction

| ID | Decision | Status | Owning doc |
|---|---|---|---|
| `A-007` | Research, extraction, storage, analysis and internal reporting may run automatically; public publishing and outreach require human approval initially. | CONFIRMED | TS/OPS |
| `A-009` | Hermes is the base agent/runtime product. Prefer skills/plugins/config over core modifications. | CONFIRMED | HLD/TS |
| `A-010` | Reuse mature OSS components before custom-building equivalent infrastructure. | CONFIRMED | HLD |
| `A-013` | CLI is the engineering/operator interface; private Telegram is the daily control/approval surface. | CONFIRMED | HLD/TS |
| `A-019` | Runtime reasoning is Google-only: Antigravity preferred; Gemini API fallback. Codex is not a runtime provider. | CONFIRMED | PROVIDERS/TS |
| `A-021` | Postiz self-hosted is the preferred social scheduling/publishing layer after real-account verification. | CONFIRMED | HLD/OPS |
| `A-022` | WhatsApp is a manual/human conversion channel in V1; API automation is not an MVP dependency. | CONFIRMED | CP/TS |
| `A-025` | No web dashboard in MVP. | CONFIRMED | CP/HLD |
| `A-026` | Both founders are administrators in V1; every mutation/approval stores `actor_id`. | CONFIRMED | OPS/TS |
| `A-029` | Scheduled/background operations use Hermes-native scheduling where adequate; externally visible actions retain approval gates. | CONFIRMED | HLD/OPS |

### 1.3 Data, search and intelligence

| ID | Decision | Status | Owning doc |
|---|---|---|---|
| `A-011` | Hermes session/memory state and marketing domain state are separate authorities. | CONFIRMED | HLD/TS |
| `A-012` | Marketing domain state uses SQLite plus filesystem raw artifacts in MVP. | CONFIRMED | TS/OPS |
| `A-014` | Automated collection uses public sources only unless an authenticated source has an explicit authorized connector. | CONFIRMED | TS/OPS |
| `A-015` | Source discovery is dynamic using source taxonomy, country profiles, search intent, source registry and feedback. | CONFIRMED | TS/HLD |
| `A-016` | SearXNG self-hosted is the preferred search backend. | CONFIRMED | HLD/PROVIDERS |
| `A-017` | Every material signal and lead assessment retains source/evidence/date/confidence provenance. | CONFIRMED | TS |
| `A-018` | Large context may be sent to Antigravity when useful; secrets/credentials and prohibited data are removed first. | CONFIRMED | TS/OPS/PROVIDERS |
| `A-020` | Current budget boundary is zero incremental software/API spend; paid usage requires a later explicit superseding decision. | CONFIRMED | CP/OPS/PROVIDERS |
| `A-024` | No vector DB/RAG in MVP; use direct structured retrieval/files/FTS until measurable need appears. | CONFIRMED | TS/HLD |
| `A-027` | Source quality is multidimensional by task (discovery, buying signal, trend, contact, etc.), not one global score. | CONFIRMED | TS |
| `A-028` | Content is generated from market evidence, service priorities and feedback, then adapted per platform. | CONFIRMED | TS |
| `A-030` | Search blends known-source exploitation with controlled open discovery; ratio is calibrated rather than hard-coded as doctrine. | CONFIRMED | TS |

### 1.4 Rejected decisions

| ID | Decision | Status | Reason |
|---|---|---|---|
| `A-031` | Use Codex as marketing runtime/model provider. | REJECTED | Codex is reserved for building/maintenance and must not consume marketing runtime workload. |
| `A-032` | Rebuild an agent framework from scratch. | REJECTED | Hermes already provides gateway, sessions, skills, plugins, tools and scheduling. |
| `A-033` | Maintain a fixed URL list as the primary source strategy. | REJECTED | Becomes stale and cannot adapt by geography/intent. |
| `A-034` | Let the agent “search the web” without source/geography/search-intent controls. | REJECTED | Low precision, poor reproducibility, wasted quota. |
| `A-035` | Enable fully autonomous posting/outreach immediately. | REJECTED | Uncalibrated external-action risk and brand/account safety. |
| `A-036` | Add paid CRM, marketing automation or social SaaS now. | REJECTED | Violates current zero-incremental-cost constraint. |

## 2. Design-at-phase / deferred decisions

| ID | Item | Reason | Trigger/phase | Cheap substitute |
|---|---|---|---|---|
| `D-01` | WhatsApp API automation | Potential cost/platform constraints | Authorized stable path + sufficient volume | WhatsApp Business App + human handling + manual logging |
| `D-02` | Autonomous public posting | Quality/risk not yet calibrated | `M-06`,`M-07` prove safe performance | Human approve/rewrite/reject |
| `D-03` | Autonomous outbound outreach | Account/brand risk | Proven reply quality + explicit founder promotion decision | Draft-only + human send |
| `D-04` | Web dashboard | UX is not MVP priority | Telegram/CLI become insufficient | Telegram + CLI |
| `D-05` | PostgreSQL | Premature operational complexity | SQLite limits observed | SQLite |
| `D-06` | Vector DB/RAG | No proven retrieval need | FTS/direct retrieval fails evaluation | Files + SQLite + FTS |
| `D-07` | Fine-grained RBAC | Only two founders | Team/external operator expansion | Two-admin allowlist + audit IDs |
| `D-08` | Full Google Workspace automation | Core acquisition system should land first | Repetitive Gmail/Drive/Sheets friction | Manual use/export + targeted connectors later |
| `D-09` | Chatwoot/omnichannel inbox | Inbound volume currently low | Native channels become hard to manage | Telegram + native channel apps |
| `D-10` | LangGraph/durable workflow framework | Hermes-native flow likely sufficient for V1 | Pause/resume/branching/recovery complexity grows | Hermes tools/scheduler + explicit states |
| `D-11` | Full CRM/marketing automation suite | No volume justification | Internal lifecycle becomes operational bottleneck | Marketing SQLite + Telegram |
| `D-12` | Private/authenticated source connectors | Platform-specific risk/cost | High-value source + authorized stable connector | Manual import |
| `D-13` | Automatic geographic reweighting | Founders want manual control | Enough outcome data + explicit policy change | Agent recommendations only |
| `D-14` | Learned ranking models | No labeled conversion corpus | Sufficient outcome labels + benchmark win | Rules + LLM-assisted scoring |
| `D-15` | Multi-node deployment | Single VPS first | `T-06`/runtime metrics prove saturation | One VPS |

## 3. Calibration register

| ID | What is calibrated | Method | Acceptance criterion | Phase | Status |
|---|---|---|---|---|---|
| `M-01` | Lead scoring weights/thresholds | Label founder-reviewed sample; compare score ordering to human priority and later outcomes | High-priority bucket shows materially higher acceptance/response than lower buckets; threshold remains editable | Phase 2–5 | OPEN |
| `M-02` | Source capability scores | Track yield, freshness, extraction success and qualified-lead contribution per capability | High-weight sources consistently outperform low-weight sources for that task | Phase 1–5 | OPEN |
| `M-03` | Country weights | Founders set values in config/CLI based on access and strategy; log effective scan allocation | Every enabled country has an explicit positive weight before production scans | Before Phase 1 production schedule | OPEN |
| `M-04` | Exploit/discover ratio | Compare new-source yield vs trusted-source lead yield over several runs | Discovery remains large enough to find useful new sources without materially reducing qualified-lead throughput | Phase 1–5 | OPEN |
| `M-05` | Service-priority operational weights | Start from confirmed ordinal classes; adjust using desired business focus and lead yield | AI remains dominant unless founders explicitly change class/weights | Phase 1 | OPEN |
| `M-06` | Content quality and cadence | Founder rubric: relevance, evidence, brand fit, edit distance, inquiries | Publication cadence chosen only after approval quality is stable; no fixed vanity target | Phase 4–5 | OPEN |
| `M-07` | Autonomy promotion gates | Measure approval/rewrite/rejection/error rates per action type | External action remains approval-required until founders explicitly promote it based on evidence | Post-MVP | OPEN |
| `M-08` | Crawl/job budgets | Benchmark fetch latency, failures, quota and VPS load | Jobs finish predictably without starving interactive Telegram/agent work | Phase 1/OPS | OPEN |
| `M-09` | Retention/storage | Measure daily raw/processed growth; classify rebuildable vs authoritative data | Retention fits VPS with backup headroom; no source-of-truth data silently evicted | Phase 1/OPS | OPEN |
| `M-10` | Antigravity model/effort routing | Evaluate quality, latency and subscription quota use on representative tasks | Use the cheapest/fastest model class that meets task-specific evaluation gates | Phase 2 | OPEN |
| `M-11` | Country/sector query lexicons | Evaluate multilingual queries against manually judged relevant results | Each active country/sector has a query set that consistently returns usable local sources/signals | Phase 1–2 | OPEN |
| `M-12` | Business KPI baselines | Track weekly funnel events from first real runs | Baseline exists before optimization; optimize for qualified conversations/wins, not views alone | Phase 5 | OPEN |
| `M-13` | Backup/RPO/RTO | Run restore drill and measure recovery duration/data loss window | Practical target selected from measured restore; documented before production reliance | OPS before routine operation | OPEN |

## 4. Investigation register

| ID | Question | Timebox | Method | Unlocks | Blocking phase | Status/result |
|---|---|---|---|---|---|---|
| `T-01` | Can Hermes use Antigravity reliably as its reasoning backend without Codex? | ≤ half day | Pin Hermes; implement/minimize adapter or tool bridge around official `agy` headless; test JSON, auth, errors, concurrency, cancellation | Runtime provider architecture | Phase 0 — before runtime-dependent implementation | OPEN — BLOCKING |
| `T-02` | Is SearXNG sufficiently good for regional/multilingual discovery? | ≤ half day | Representative queries across SA/AE/SY/TR plus sample others; compare engines/languages/precision | Search backend/engine profile | Before Phase 1 scheduled production scans | OPEN — BLOCKING |
| `T-03` | Does self-hosted Postiz reliably publish/schedule to owned Instagram and Telegram accounts in the selected version? | ≤ half day after credentials | Deploy pinned version; publish test image/text/reel-compatible asset where supported; verify schedule + API/CLI path | Automated social publishing | Before Phase 4 | OPEN — BLOCKING FOR PUBLISHING ONLY |
| `T-04` | Is there an official zero-incremental-cost WhatsApp integration worth adding? | ≤ 2 hours research/test | Verify current Meta path/pricing/limits; no bypasses | Optional WhatsApp automation | Not blocking V1 | OPEN |
| `T-05` | If `T-01` fails, can Gemini API be a zero-spend Google-only fallback compatible with Hermes? | ≤ half day | Verify current free tier/model, data policy, structured outputs/tools, provider adapter | AI fallback | Conditional Phase 0 fallback before runtime-dependent implementation | OPEN |
| `T-06` | Can the current VPS run the selected stack safely? | ≤ half day | Deploy representative containers/processes; measure RAM/CPU/disk/IO under crawl + agent + Postiz activity | Single-VPS topology | Before Phase 4 co-location; earlier if VPS is small | OPEN — BLOCKING FOR FINAL TOPOLOGY |
| `T-07` | Are Instagram/Meta account/app permissions ready for automation? | ≤ 2 hours after access | Validate professional account, app credentials, scopes and callback requirements | Postiz Instagram integration | Before Phase 4 | OPEN |
| `T-08` | Which Hermes release should be pinned and are required extension points stable? | ≤ 2 hours | Install candidate stable release; run plugin/skill/gateway smoke tests | Reproducible implementation baseline | Before first implementation branch | OPEN |

## 5. Review findings

| ID | Severity | Issue | Repair | Status |
|---|---|---|---|---|
| `R-01` | HIGH | Early design risked treating Codex as a possible runtime provider, contradicting founder intent. | Runtime provider policy rewritten: Google-only; explicit `A-031` rejection added and propagated to TS/HLD/AGENT/PROVIDERS. | CLOSED |
| `R-02` | HIGH | “Hermes + Antigravity” could be stated as if already natively integrated. | Converted integration fact into blocking `T-01`; current docs distinguish official Antigravity headless capability from unproven Hermes adapter. | CLOSED |
| `R-03` | NORMAL | Zero-cost constraint could conflict with Gemini API fallback. | `A-020` states no paid usage; `T-05` must verify a zero-spend fallback or leave it disabled. | CLOSED |
| `R-04` | NORMAL | Postiz was previously treated as guaranteed publishing infrastructure despite version/account variability. | Made real-account smoke test `T-03` a publishing-phase blocker and retained manual/direct fallback paths. | CLOSED |

## 6. Sessions/milestones / design rounds

1. Business problem and zero-cost stack established.
2. Hermes selected as base product; reuse-first architecture confirmed.
3. MVP scope, dual funnels, autonomy and ethical academic boundary confirmed.
4. Dynamic regional source strategy and manual country weights confirmed.
5. Data/interaction/publishing decisions confirmed.
6. Runtime-provider correction: Antigravity/Google only; Codex explicitly excluded from marketer runtime.
7. Documentation suite generated and cross-audited.

## 7. Ongoing rules

- Core Hermes code is modified only when extension points cannot satisfy a confirmed requirement and an ADR is created.
- No new paid dependency is introduced without an explicit superseding decision to `A-020`.
- Web content is untrusted data, never executable instruction.
- Every important model conclusion links to evidence IDs.
- Country and service priorities are configuration, not code constants.
- Agent recommendations may suggest configuration changes but cannot self-approve them.
- Codex can modify the repository; Codex cannot be configured as the marketer's runtime reasoning provider.

## 8. Current readiness

### Documentation-ready
**YES.** No user-owned blocker remains open; unresolved external facts are classified as `T-##`, and empirical thresholds as `M-##`.

### Implementation-ready
**NO.** At minimum `T-08` and the Phase-appropriate blocking investigations must be closed before relying on their respective components. `T-01` is the key blocker for the intended Hermes+Antigravity runtime.

### Immediate next actions
1. Close `T-08` and pin Hermes.
2. Run `T-01` before implementing marketing intelligence around a presumed provider contract.
3. Run `T-02`, then build country profiles/source registry around the verified search behavior.
4. Complete `M-03` by entering founder-chosen country weights.

### Must-not-defer items
- Secret/context scrubber before any broad-context model invocation.
- Evidence/provenance contract before lead scoring.
- Telegram admin allowlist before exposing control commands.
- Database migration/backup smoke test before routine operation.
