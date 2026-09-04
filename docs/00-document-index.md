# Marketing OS — Document Index

> Version 1.0 · 2026-09-03 · Documentation-ready / not yet implementation-ready

## 1. Project in one paragraph

Marketing OS هو وكيل تسويق ومبيعات داخلي لشركة ناشئة تقنية صغيرة، مبني بتخصيص **Hermes Agent** بدلاً من إنشاء agent runtime جديد. يدعم السعودية والإمارات وقطر وسوريا والبحرين وعُمان والأردن ولبنان وتركيا، ويفصل مساري B2B والخدمات الأكاديمية التقنية. V1 يجمع Market Radar + Content Engine + Conversation Intake، ويعتمد Dynamic Regional Source Intelligence عبر SearXNG وSource Registry، مع Evidence/Provenance إلزامي. التشغيل اليومي عبر CLI وTelegram، والنشر عبر Postiz بعد التحقق. Reasoning التشغيلي Google-only: Antigravity أولاً وGemini API fallback؛ Codex للبناء والصيانة فقط. قيد الميزانية الحاكم هو عدم إضافة تكلفة تشغيلية جديدة دون قرار صريح.

## 2. Selected document suite

| ID | Document | Answers | Status | Why included/omitted |
|---|---|---|---|---|
| IDX | `00-document-index.md` | أين أبدأ؟ وما حالة الحزمة؟ | Current | mandatory |
| CP | `01-project-checkpoint.md` | لماذا هذا التصميم؟ | Current | primary narrative |
| TS | `02-technical-design-spec.md` | ماذا ننفذ بالضبط؟ | Current | implementation contract |
| OPS | `04-operations-deployment-security.md` | كيف نشغله ونحميه ونعيده؟ | Current | operated system |
| DOC | `05-documentation-workflow-guide.md` | كيف تبقى الوثائق حية؟ | Current | long-lived project |
| REG | `06-coordination-master-register.md` | ما القرار الحالي لكل موضوع؟ | **Governing** | canonical registry |
| HLD | `07-high-level-design.md` | ما المكونات والحدود والتدفقات؟ | Current | architecture |
| ROAD | `08-future-roadmap.md` | ما المؤجل ومتى يعود؟ | Current | explicit deferrals |
| REVIEW | `09-final-design-review.md` | هل الحزمة متسقة وجاهزة؟ | Current | generated last |
| PREP | `10-preimplementation-plan.md` | ماذا نفعل قبل الكود؟ | Current | uncertainty-first kickoff |
| AGENT | `11-ai-coding-agent-setup.md` | كيف يستخدم Antigravity للبناء بأمان؟ | Current | Antigravity engineering harness; Codex runtime rejected |
| PROVIDERS | `12-model-provider-guide.md` | كيف يعمل Antigravity/Gemini؟ | Current; dated | volatile provider facts |
| BM | — | monetization of this tool | Omitted | tool internal, not sold |
| NFR | — | separate NFR artifact | Omitted | integrated into TS/HLD/OPS |
| ADR | `docs/adr/` | implementation-era durable decisions | Not yet | no trigger before implementation |

## 3. Who reads what

| Situation/role | Read in this order | Why |
|---|---|---|
| Founder reviewing product | IDX → CP → REG → ROAD | scope/why/decisions/future |
| Engineer starting implementation | IDX → REG → PREP → HLD → TS → OPS | current truth then implementation |
| Antigravity/coding agent | AGENT → REG → owning doc | build rules and current decisions |
| Runtime/provider work | PROVIDERS → PREP T-01/T-05 → HLD/TS | volatile facts + contract |
| Search/source work | TS → config examples → HLD | source intelligence details |
| Publishing work | TS approvals → OPS → T-03/T-07 | external action safety |
| Architecture review | HLD → TS → OPS → REG | boundaries/contracts/operations/status |

## 4. Governing decisions / invariants

- `A-009`: Hermes is the base; extension-first.
- `A-015`: dynamic regional source intelligence; not a fixed URL list.
- `A-017`: evidence/provenance before material lead claims.
- `A-019`: runtime reasoning Google-only.
- `A-020`: zero incremental cost unless superseded.
- `A-007`: external public actions require human approval initially.
- `A-031`: **Codex runtime is rejected.**
- `I-01`/HLD: product provider allowlist must not contain Codex.
- `I-02`: publishing/sending cannot occur without persisted approval.
- `I-04`: agent may recommend but cannot mutate country weights.

## 5. Reference metrics / numbers

No unsupported target numbers are frozen.

Current numeric-like configuration is intentionally calibrated:
- `M-03` country weights;
- `M-01` lead thresholds;
- `M-02` source capability thresholds;
- `M-04` exploit/discover ratio;
- `M-06` content cadence/rubric;
- `M-08` crawl/timeouts/budgets;
- `M-13` backup targets.

Nine countries and three service-priority classes are confirmed product scope, not performance assumptions.

## 6. Immediate actions and blockers

### Before implementation

1. `T-08`: pin Hermes and extension interfaces.
2. `T-01`: prove Hermes ↔ Antigravity path without Codex.
3. If T-01 cannot support required runtime semantics, `T-05`: verify Gemini API fallback under cost/provider constraints.
4. Establish secret/config guards.

### Before Regional Source Intelligence exit

- `T-02`: SearXNG localization benchmark.
- `M-03`,`M-11`: actual country weights/query lexicons.

### Before automatic social publishing

- `T-03`, `T-06`, `T-07`.

## 7. Things that must not be deferred

- secret redaction before model calls;
- evidence lineage;
- public-source collection boundary;
- approval enforcement/idempotency;
- separation of Hermes memory and marketing DB;
- Codex runtime prohibition;
- no silent paid fallback.

## 8. Governing build rules

1. Reuse before rebuild.
2. Config over hard-coded country/source policy.
3. Deterministic code for collection/normalization/state; model for reasoning/language.
4. Every external dependency has degraded behavior.
5. Pin upstream versions.
6. No web UI until trigger.
7. Same-change documentation updates.

## 9. Field/external facts still requiring verification

- exact Hermes/Antigravity integration contract (`T-01`);
- Gemini fallback economics/capability if needed (`T-05`);
- target-market search result quality (`T-02`);
- actual VPS capacity (`T-06`);
- real Postiz/Instagram/Telegram publishing setup (`T-03`,`T-07`);
- optional WhatsApp official zero-cost path (`T-04`).

## 10. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-03 | First documentation-ready design snapshot after user decision rounds; Google-only runtime and Codex runtime rejection incorporated. |
