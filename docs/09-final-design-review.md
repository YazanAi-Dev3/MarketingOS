# Marketing OS — Final Design Review

> Version 1.0 · 2026-09-03 · Audit scope: documentation snapshot v1.0 · Generated after cross-document audit

## 1. Audit scope and cumulative result

تمت مراجعة حزمة التصميم الخاصة بـMarketing OS باعتبارها **تصميماً قبل التنفيذ** لوكيل تسويق داخلي مبني على Hermes، وليس مراجعة لكود إنتاج غير موجود بعد.

شمل التدقيق:
- تطابق scope بين CP/TS/HLD/OPS/ROAD/PREP؛
- تطابق مصدر الحقيقة والـdata ownership؛
- عدم تسرب Codex إلى runtime بعد قرار الرفض؛
- اتساق Antigravity/Gemini provider policy؛
- اتساق source intelligence والسياسات الجغرافية؛
- external-action approval boundaries؛
- IDs (`A/M/T/D/R`) والإحالات بينها؛
- حالة الوثائق المختارة/المستبعدة؛
- الفصل بين documentation-ready وimplementation-ready.

**النتيجة التراكمية:** الحزمة Documentation-ready. لا توجد فجوة user-owned مفتوحة. التنفيذ غير جاهز بالكامل حتى إغلاق التحقيقات blocking المناسبة، وعلى رأسها `T-08` و`T-01`.

## 2. Material issues found in this audit

### R-01 · Codex could leak into product runtime

**Detected:** نسخة تصميم سابقة حاولت استخدام Codex/ChatGPT OAuth كحل سهل لتشغيل Hermes، وهو يخالف قرار المؤسس بأن Codex مخصص للبناء فقط.

**Why it matters:** يربط workload التسويقي بحصة أداة البناء ويخالف ownership المقصود للstack.

**Repair:** تثبيت `A-019` Google-only runtime، وإضافة `A-031` كرفض صريح لـCodex runtime؛ تحديث CP/TS/HLD/OPS/AGENT/PROVIDERS/PREP.

**Propagation verified:** البحث النصي لا يجد Codex كـcurrent provider/fallback؛ كل ذكر runtime له هو نفي/guard/rejected decision.

**Status:** CLOSED.

### R-02 · Hermes + Antigravity was at risk of being documented as already integrated

**Detected:** وجود `agy` headless لا يثبت تلقائياً أن Antigravity يحقق Hermes model-provider semantics.

**Why it matters:** لو وثق كحقيقة، قد يبدأ التنفيذ فوق contract غير موجود.

**Repair:** تحويله إلى `T-01` blocking investigation، مع مسارين extension-first: model-provider plugin أو general tool/skill adapter. لا تعديل Hermes core بدون ADR.

**Propagation verified:** PROVIDERS/PREP/HLD/TS جميعها تذكر التكامل كمسار مطلوب إثباته، لا كقدرة جاهزة.

**Status:** CLOSED.

### R-03 · Gemini API fallback could contradict zero-cost policy

**Detected:** قبول Gemini API كـfallback لا يعني أن Google AI Pro يضمن API usage مجانية/مشمولة.

**Why it matters:** قد ينشأ spend غير مقصود رغم `A-020`.

**Repair:** `T-05` يتحقق من المسار والحصة/الكلفة الفعلية؛ fallback disabled إذا لم يحقق zero-incremental-cost. لا paid auto-fallback.

**Propagation verified:** CP/TS/OPS/PREP/PROVIDERS/HLD متفقة.

**Status:** CLOSED.

### R-04 · Postiz was at risk of becoming a hard MVP dependency

**Detected:** المنتج مفتوح المصدر ومناسب، لكن self-hosting والحسابات/OAuth وInstagram behavior تتغير حسب النسخة والحساب.

**Why it matters:** قد يتوقف MVP كله على publishing stack أثقل من Market Radar.

**Repair:** Postiz preferred publishing layer فقط بعد `T-03`,`T-06`,`T-07`; manual publish/direct Telegram يبقي V1 قابلاً للاستخدام.

**Propagation verified:** HLD/OPS/PREP/ROAD متفقة.

**Status:** CLOSED.

## 3. Automated/structural checks actually run

| Check | Command/method | Result |
|---|---|---|
| Skill suite validator — pre-review | `validate_suite.py docs --state .doc-engine/generation-plan.json` | Only expected failure: REVIEW not yet generated |
| Registry reference audit | regex scan of all docs against REG definitions | 76 referenced identifiers, 0 undefined |
| Selected-document audit | generation plan vs files | only REVIEW missing before final generation |
| Internal markdown reference audit | filename scan | only REVIEW references missing before final generation |
| Codex runtime audit | grep for Codex provider/runtime/fallback patterns | no positive/current Codex runtime path; occurrences are explicit rejection/guards |
| T-02 semantic audit | grep + manual inspection | T-02 consistently means SearXNG regional benchmark |
| Architecture ownership review | manual CP/TS/HLD/OPS comparison | Hermes state ≠ marketing DB; authority consistent |
| Scope/deferred review | manual CP/HLD/ROAD/PREP comparison | deferred items do not appear as V1 requirements except as phase-gated substitutes |

A final validator run is executed after this file is written; its result is recorded in `.doc-engine/audit-report.json` and package README.

## 4. Remaining calibrations / investigations / deferred items

### Investigations

- `T-08` — pin Hermes release/interfaces. **Before first implementation branch.**
- `T-01` — prove Hermes ↔ Antigravity runtime path. **Key runtime blocker.**
- `T-02` — benchmark SearXNG regional/localized discovery. **Before scheduled regional scans.**
- `T-05` — conditional Gemini API fallback if T-01 is insufficient.
- `T-06` — current VPS capacity for selected co-located stack.
- `T-03`,`T-07` — Postiz/Instagram publishing, blocking Phase 4 only.
- `T-04` — optional WhatsApp integration, not V1 blocker.

### Calibrations

`M-01` through `M-13` remain intentionally open where values must be measured rather than invented. The most immediate are:
- `M-03` country weights;
- `M-11` query lexicons;
- `M-08` crawl/timeouts;
- `M-01` lead scoring after founder-labeled fixtures.

### Deferred

`D-01` through `D-15` have explicit trigger/substitute definitions in ROAD/REG. None must be implemented to claim V1 design completion.

## 5. Design state

### Complete enough now

- product identity/scope;
- dual funnels;
- service/geographic policy;
- dynamic source architecture;
- data model/authority;
- evidence/provenance model;
- human approval/autonomy boundary;
- Hermes reuse-first strategy;
- CLI/Telegram operator surfaces;
- Google-only runtime policy;
- zero-cost circuit breaker;
- phased publishing/WhatsApp behavior.

### Design at its phase

- country numeric weights;
- source/lead thresholds;
- exact query engine/lexicon mix;
- crawl/resource budgets;
- model/effort routing;
- content cadence;
- backup RPO/RTO;
- social publishing credentials/version.

These are correctly represented as `M-##` or `T-##`, not fake constants.

### Before first production code

Strict minimum:
1. close `T-08`;
2. run `T-01` before coding against a provider assumption;
3. establish secret/model-payload guard and provider allowlist;
4. define clean migration/test DB baseline.

Phase 1 additionally needs `T-02` before broad scheduled search.

### Must not be deferred inside implementation

- `A-031` runtime provider prohibition;
- evidence lineage;
- secret redaction;
- public-source access boundary;
- approval + idempotency;
- authoritative marketing store separation;
- paid usage circuit breaker.

## 6. Repeated failure/consistency patterns

1. **Convenient integration ≠ approved architecture.** Existing subscriptions can tempt the design toward a provider that violates workload ownership.
2. **Document external capability as investigation until the exact deployed contract is proven.**
3. **Do not turn optional OSS components into MVP blockers.**
4. **Keep model/provider uncertainty outside domain contracts.** Evidence, approvals and data schemas remain stable whichever Google path wins.
5. **Avoid false numeric precision.** Country/search/lead/content thresholds are measurements.

## 7. Verdict

### Documentation-ready: **YES**

Evidence:
- user-owned product/authority decisions are closed;
- selected docs are substantive and derived from one frozen ledger;
- unknowns are classified as investigation/calibration/deferral;
- rejected decisions are explicit;
- no unresolved contradiction is known;
- cross-document IDs/ownership/scope are consistent.

### Implementation-ready: **NO**

Primary blockers:
- `T-08` Hermes pin/extension smoke;
- `T-01` Antigravity integration contract;
- phase-specific investigations before their features are relied upon (`T-02`, later `T-03/T-06/T-07`);
- `M-03` must be set before production regional scheduling.

The design is intentionally ready to guide implementation **without pretending that external integration facts have already been proven**.
