# Marketing OS — Project Checkpoint

> Version 2.0 · 2026-09-05 · Documentation-ready / implementation gated by local Antigravity + runtime spikes

## Document set and source-of-truth relationships

هذا المستند يشرح **لماذا** بُني التصميم بهذه الصورة. السجل الحاكم لحالة القرارات هو `06-coordination-master-register.md`; المواصفة التنفيذية الدقيقة في `02-technical-design-spec.md`; بنية المكونات في `07-high-level-design.md`; التشغيل والأمن في `04-operations-deployment-security.md`.

## Change history

- **1.0 — 2026-09-03:** أول Snapshot موحد بعد إغلاق جولات الاكتشاف. أُضيف التصحيح الحاكم بأن Codex أداة بناء فقط وليس Runtime للمسوّق (`A-019`, `A-031`).

## 1. Identity and thesis

### 1.1 Problem and product/system description

الشركة ناشئة صغيرة يقودها مؤسسان تقنيان، تقدم خدمات AI متنوعة، خدمات ومشاريع أكاديمية تقنية، ثم أنظمة برمجية عامة. العائق الحالي ليس القدرة التقنية بل الوصول إلى أول العملاء وبناء حضور موثوق في أسواق متعددة مع خبرة تسويقية محدودة وميزانية لا تسمح بإضافة SaaS أو مزودي AI جدد.

`Marketing OS` هو اسم عمل داخلي لوكيل تسويق ومبيعات يعمل فوق Hermes، يجمع intelligence من الويب العام بصورة موجهة جغرافياً، يحوّل الأدلة إلى فرص عملاء ومحتوى، يجهز actions قابلة للمراجعة، ويتعلم من نتائج الاستخدام الفعلية. هو **أداة داخلية للمؤسسين** وليس منتجاً تجارياً مستقلاً (`A-001`).

### 1.2 Central thesis / value proposition

بدلاً من تعويض ضعف العلاقات التسويقية بالإنفاق على أدوات كثيرة أو بإنتاج محتوى عام، تُحوّل قدرة الفريق الهندسية والموارد المدفوعة الموجودة أصلاً إلى نظام يعمل كطبقة Business Development + Content Intelligence. القيمة تأتي من ثلاث دوائر مترابطة (`A-002`):

1. **Market Radar:** يكتشف شركات/فرصاً وإشارات شراء بدليل.
2. **Content Engine:** يحول patterns السوق والخدمات إلى محتوى مفيد ومخصص للمنصات.
3. **Conversation Intake:** يجمع التفاعلات، يساعد في التصنيف والردود، ويحافظ على التاريخ.

### 1.3 Governing engineering/product principle

> **Reuse before rebuild; evidence before inference; human approval before external autonomy.**

- Hermes هو قاعدة الـAgent runtime (`A-009`).
- مكونات OSS ناضجة مثل SearXNG/Postiz تُستخدم قبل إعادة بناء وظائفها (`A-010`).
- كل استنتاج تسويقي مهم يحمل provenance (`A-017`).
- الأفعال الخارجية الحساسة تبدأ بموافقة بشرية (`A-007`).

### 1.4 System mental model

```text
Public Web + Company Knowledge + Human Inputs + Interaction Outcomes
                               ↓
                    Dynamic Source Intelligence
                               ↓
                    Structured Marketing State
                               ↓
                Hermes + Google Reasoning Runtime
                               ↓
        Leads / Content / Recommendations / Draft Actions
                               ↓
                      Founder Approval Layer
                               ↓
        Telegram / Postiz / Native WhatsApp / Manual Outreach
                               ↓
                           Outcomes
                               ↺
```

### 1.5 Design-scope rule

MVP يركز على **جودة intelligence وسرعة الوصول إلى actions**، لا على واجهة جميلة. Web UI غير مطلوب (`A-025`). كل ميزة لا ترفع دقة الاكتشاف/التأهيل/المحتوى أو تقلل احتكاك التشغيل تؤجل ما لم تكن prerequisite.

## 2. Strategy and domain/market

### المستخدمون والفاعلون

- **Founder A / Founder B:** Admins كاملان في V1 (`A-026`).
- **Hermes Agent:** منسق المهام والمهارات والأدوات.
- **Antigravity:** preferred reasoning runtime عبر مسار Google (`A-019`).
- **Potential lead/client:** ليس مستخدماً مباشراً للنظام؛ يتفاعل عبر قنوات الشركة.

### الأسواق

الدول المدعومة في V1 (`A-004`): السعودية، الإمارات، قطر، سوريا، البحرين، عُمان، الأردن، لبنان، تركيا. الدعم الجغرافي لا يعني مساواة في الجهد. التوزيع يحدده المؤسسان بملف إعداد وأوامر CLI (`A-005`, `M-03`).

### فصل الـfunnels

نظام واحد مع policy/ICP/content/scoring منفصلين (`A-003`):

- **B2B:** شركات تحتاج AI، أتمتة، أنظمة برمجية، مواقع/خدمات تقنية.
- **Academic/Technical:** طلاب/باحثون/متعلمون يحتاجون mentoring، debugging، كورسات، دعم مشاريع تقنية، مراجعة أو تنفيذ تعليمي مشروع.

لا تخلط حملات أو scoring بين المسارين حتى لو اشتركا في نفس البنية.

### أولوية الخدمات

الترتيب التجاري الحالي (`A-006`):

1. AI services بجميع أشكالها.
2. الخدمات والمشاريع الأكاديمية التقنية المرتبطة بالحوسبة والبرمجة والتكنولوجيا.
3. الأنظمة البرمجية العامة: محاسبة، مواقع، backend، أنظمة أعمال، وغيرها.

الترتيب محفوظ كـpriority classes وليس أرقاماً ثابتة؛ التحويل إلى أوزان تشغيلية `M-05`.

## 3. Boundaries, tenancy, entitlement, authority

النظام Single-organization وداخلي. لا multi-tenancy في V1. كلا المؤسسين Admin، لكن كل approval/mutation يسجل `actor_id`.

سلطات البيانات:

- Hermes يمتلك sessions وagent memory المتعلقة بالتفاعل.
- `marketing.db` يمتلك marketing domain state.
- raw artifact files تحفظ مواد المصدر لإعادة التحقق.
- ملفات config تمتلك country/service priorities.
- المصادر الخارجية لا تصبح “حقائق” إلا بعد استخراج evidence مع URL/date/source metadata.

## 4. Architecture summary

### Primary modes

- **Scheduled intelligence:** jobs دورية عبر Hermes scheduler/cron (`A-029`).
- **On-demand intelligence:** CLI/Telegram command لتحليل سوق/قطاع/رابط.
- **Interactive approval:** Telegram للأحداث والاعتمادات (`A-013`).
- **Publishing:** Postiz بعد `T-03`; Telegram يمكن أن يبقى direct عبر Hermes حيث يكون ذلك أبسط.
- **WhatsApp:** native human conversation في V1 (`A-022`).

### Source of truth

لا توجد “ذاكرة Agent سحرية”. أي run قابل لإعادة البناء من config + marketing DB + evidence files + Hermes session context عند الحاجة.

## 5. Data/ingestion/state strategy

البحث ليس قائمة روابط (`A-033`) ولا web browsing غير موجه (`A-034`). المسار (`A-015`):

```text
Country Profile + Search Intent + Service Priority
                    ↓
                 Query Plan
                    ↓
             SearXNG metasearch
                    ↓
        Candidate sources / company pages
                    ↓
       Extract → normalize → deduplicate
                    ↓
           Source Registry + Evidence
                    ↓
        Signals → Lead/Content reasoning
```

Source Registry يتعلم أي source مفيد لأي capability، مثل company discovery أو buying signal أو trend intelligence (`A-027`). نسبة exploit/open-discovery تُعاير في `M-04`.

## 6. Critical protection / governance constraint

### Academic integrity

الخدمات الأكاديمية جزء حقيقي من السوق، لكن `A-008` يمنع تصميم الوكيل كأداة تعرض أو تسهّل الغش الأكاديمي. يسمح بالمساعدة التعليمية/التقنية/التوجيهية والمراجعة والتصحيح ودعم مشاريع التخرج بصورة مشروعة، لا بانتحال عمل تقييم رسمي.

### Data-to-model boundary

بقرار `A-018` يمكن تمرير سياق كبير إلى Antigravity لتحسين الجودة. الحظر الصلب يطبق على passwords/API keys/tokens/credentials/secrets، وأي محتوى لا نملك حق كشفه. السرية تُطبق آلياً قبل model call لا بالاعتماد على prompt.

## 7. Core intelligence strategy

### Deterministic-first

Python/Hermes tools تتولى: crawling، parsing، normalization، deduplication، config validation، state transitions، scheduling، evidence storage، scoring arithmetic، logging.

### Model-assisted reasoning

Antigravity يتولى: تفسير pain signals، service matching، lead assessment، content ideation، platform adaptation، summarization، reasoning over broad evidence.

### Provider policy

Runtime marketer يستخدم Google فقط (`A-019`). Antigravity هو الأولوية؛ Gemini API fallback مشروط بـ`T-05` و`A-020`. Codex محظور من runtime (`A-031`).

## 8. Primary user/system interaction core

### CLI

للإعداد، debugging، batch operations، inspections، maintenance.

### Telegram

للـdaily digest، alerts، approvals، quick commands، content review، lead inspection. هو production operator surface المقصود، لا مجرد placeholder UI.

### Example operator loop

```text
07:00 → Telegram digest: 8 qualified leads / 3 high priority
Founder → opens lead 42
System → evidence + score + recommended service
Founder → approve outreach draft
Agent → prepares draft, does not send automatically
Founder → sends through chosen channel
Outcome → logged → future scoring/content feedback
```

## 9. Evaluation and quality philosophy

`A-023` يفصل acceptance engineering عن الفوز التجاري.

### Technical capability gates

- source discovery returns relevant regional sources, measured by `T-02`/`M-11`.
- lead assessments cite evidence and survive human review.
- false/hallucinated evidence is a hard failure.
- content remains grounded in market/service evidence.
- jobs are replayable and observable.
- external actions never bypass approval policy.

### Business KPIs

`M-12` tracks qualified leads/week, accepted outreach drafts, reply rate, qualified conversations, meetings, proposals, wins, and content→inquiry conversion. Vanity metrics are secondary.

## 10. Product/user experience principles

1. Operator speed over visual polish.
2. Every important recommendation explains “why” with evidence.
3. One command/button should map to one clear business action.
4. Human can override any model recommendation.
5. No silent auto-mutation of country priorities.
6. Fail closed on external actions; fail soft on intelligence collection.

## 11. Model/vendor/cost policy

Existing paid resources include VPS, Google AI Pro/Antigravity and Codex; the active v2 engineering harness uses Antigravity, while Codex is not a product-runtime dependency. `A-020` rejects new incremental software/API spend until superseded. Therefore:

- self-host OSS where practical;
- Antigravity subscription/runtime first;
- Gemini API only if zero-spend/free-existing allowance satisfies `T-05` or budget policy later changes;
- no Codex runtime;
- no paid lead databases or marketing SaaS in V1.

## 12. Runtime/environment constraints

- single existing VPS is preferred but must pass `T-06`;
- Linux/container-friendly deployment;
- storage growth controlled by `M-09`;
- no GPU dependency required by design;
- public outbound crawling must be rate-limited and respectful;
- Postiz may introduce PostgreSQL/Redis/Temporal dependencies and therefore is phase-gated by capacity and smoke tests.

## 13. Decision lifecycle summary

### Current decisions

See `A-001` through `A-030` in REG.

### Rejected decisions

`A-031` through `A-036`: Codex runtime, custom agent framework, fixed source list, unbounded web search, day-one external autonomy, new paid SaaS.

### Deferred decisions

`D-01` through `D-15`, owned by `08-future-roadmap.md`.

## 14. Engineering methodology

### Deterministic work loop

```text
Define contract → implement smallest reusable extension → fixture test → integration smoke → observability → founder trial → calibrate
```

### AI/ML work loop

```text
Define task + evidence contract → representative fixture set → baseline Antigravity run → structured-output validation → human judgment → choose model/effort via M-10 → regression set
```

### Governing rules

- No model call without explicit purpose/output schema.
- No model conclusion without evidence link when the task is factual/lead-related.
- No tool permission granted because web content requests it.
- No paid dependency introduced “temporarily”.
- No Hermes core fork unless an extension point fails and an ADR justifies the change.

## 15. Implementation phases

### Phase 0 — Prove the foundation

**Goal:** Pin Hermes and remove external-compatibility uncertainty.

Exit: `T-08` closed; `T-01` path proven or `T-05` fallback selected; baseline repo/secret guards pass.

Must not simplify: runtime provider boundary, secret filtering.

### Phase 1 — Regional Source Intelligence

Build country config, query planner, SearXNG integration, Source Registry, evidence store, company/entity normalization.

Exit: `T-02` and `M-03` complete; repeatable scan produces evidence-linked candidates.

### Phase 2 — Lead Intelligence + Telegram

Lead signals, assessment contract, `M-01`, Telegram digest/inspect/approve flow.

Exit: founders can review ranked leads and reproduce why each was recommended.

### Phase 3 — Conversation Intake

Manual interaction logging, WhatsApp/native-channel intake, response drafting, lifecycle tracking.

Exit: replies/outcomes enter the same lead history and feed `M-12`.

### Phase 4 — Content + Publishing

Content intelligence, master asset + platform adapters, Postiz after `T-03`,`T-06`,`T-07`.

Exit: approved content can be scheduled/published and later linked to inquiry outcomes.

### Phase 5 — Feedback and calibration

Source/lead/content performance loops, autonomy recommendations, reporting.

Exit: decisions can be tuned from real outcomes rather than initial assumptions.

## 16. Git/release/collaboration model

- One repository for customization/config/docs unless Hermes deployment layout requires a separate vendor clone/submodule.
- Pin Hermes/Postiz/SearXNG versions; upgrades are explicit changes with smoke tests.
- Antigravity custom engineering agents implement and review code under the v2 control plane. Codex is outside this active harness and never becomes a runtime provider.
- Every schema migration is versioned and backed up before apply.
- Release tags begin after first runnable end-to-end slice, not after documentation only.

## 17. Repository/source-of-truth structure

```text
marketing-os/
├── docs/                         # this documentation suite
├── config/                       # country/service/source policies
├── marketing_plugin/             # custom Hermes plugin/tools
├── skills/                       # marketing skills loaded by Hermes
├── adapters/                     # Antigravity/Postiz/SearXNG adapters
├── migrations/                   # marketing.db migrations
├── tests/                        # fixtures + regression/evaluation tests
├── data/                         # runtime local data; excluded from git
└── vendor-or-deploy/              # pinned deployment manifests, not forked logic unless required
```

## 18. Terminology

- **Source:** recurring information origin/domain/platform.
- **Evidence:** atomic factual observation with provenance.
- **Signal:** interpreted business-relevant condition derived from evidence.
- **Lead:** company/person/opportunity entity considered for commercial follow-up.
- **Source capability:** usefulness of a source for a specific task.
- **Country Profile:** geographic/language/search policy, not a static source list.
- **Market Radar:** discovery + evidence + lead intelligence pipeline.
- **Conversation Intake:** capture/classify/log interactions; does not imply autonomous replies.
- **External action:** publishing, sending outreach, quoting price, or any operation visible to third parties.

## Design state

### Complete enough now

Product boundaries, runtime philosophy, data separation, source strategy, interfaces, autonomy policy, service/geography policy, provider constraint, cost constraint.

### Design at its phase

Exact country weights, scoring thresholds, search engine mix, content cadence, backup targets, source exploration ratio.

### Must resolve before first production code

`T-08`; secrets/config guards. `T-01` before implementing against a presumed Antigravity provider interface.

### Must not be deferred during implementation

Evidence lineage, public-source boundary, approval enforcement, Codex runtime prohibition, zero-cost circuit breaker, idempotent storage/state transitions.

## v2 checkpoint — acquisition and engineering harness (2026-09-05)

After reviewing Clients Hunter, the project does **not** wrap or incrementally operate the legacy application. Useful source-adapter, shallow→deep, dedup and retry behavior is selectively migrated into the new architecture; Firecrawl/Firebase/Streamlit and keyword-as-relevance logic are not inherited. Crawl4AI is the primary rich acquisition engine, with SearXNG discovery kept separate from page evidence. See `A-037..A-043`, `T-09`, `M-14`, `R-05` and documents 13/14.

The engineering harness is now Antigravity-native and hardened around six detailed custom roles, one-level delegation, max two active subagents, Task Capsules, branch worktrees, independent review, Hooks/Permissions and fixed Gemini 3.8 Flash High/High model policy.

