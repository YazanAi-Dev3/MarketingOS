# Marketing OS — حزمة Antigravity الهندسية الكاملة v2.1

هذه الحزمة هي **بيئة المشروع الكاملة قبل بدء التنفيذ**: وثائق Marketing OS، فريق الوكلاء، Rules، Skills، Hooks، Permissions أمثلة، بروتوكولات Git/worktrees، durable state، إعدادات المصادر، وسياسة ترحيل Clients Hunter.

## ما تغير عن v1؟

أعيد بناء تعريفات الوكلاء لتكون قوية ومفصلة بدل prompts قصيرة. تم تصميمها وفق primitives الحالية في Antigravity: الوصف التفصيلي للتفويض، tool allowlists موثقة، سياق مستقل للـsubagents، branch worktrees، Skills progressive-disclosure، Rules قليلة Always-On، Hooks deterministic، وPermissions least-privilege.

التشكيلة:

`orchestrator → explorer(optional) → builder → verifier(conditional) → reviewer → heavy-reviewer(trigger only)`

كل الأدوار تستهدف **Gemini 3.8 Flash High + High effort**. الـOrchestrator وحده يفوض، والحد الأقصى وكيلان فرعيان نشطان. لا يوجد Deep Builder دائم لأن النموذج واحد؛ بعد فشل Builder مرتين يعيد Orchestrator تقسيم المهمة أو يبدأ Builder جديداً بسياق نظيف.

## قبل أول مهمة حقيقية

1. ضع الحزمة في جذر Repository المشروع.
2. افتح Antigravity واختر `orchestrator`.
3. اختر Gemini 3.8 Flash High + High effort.
4. اجعل ملفات `.agents/rules/` الثلاثة **Always On**.
5. راجع `setup/antigravity-ide-settings-checklist.md`.
6. شغّل:

```bash
python scripts/verify_control_plane.py
python scripts/test_hooks.py
python scripts/scan_for_secrets.py
```

7. نفّذ `.agents/protocols/DRY-RUN.md` لإغلاق `AG-CC-01..05` على جهازك.

## أهم قرار جديد في acquisition

البنية المعتمدة:

`Query Planner → SearXNG → Acquisition Router → direct HTTP/API أو Crawl4AI → Source Adapter → Evidence`

Crawl4AI هو المحرك الأساسي للـrich crawling/rendering/extraction. BeautifulSoup/lxml أدوات parsing صغيرة عند الحاجة وليست framework scraping منافساً. Clients Hunter لا يُشغّل داخل النظام الجديد؛ نأخذ منه السلوك/المعرفة المفيدة وننظف أو نعيد بناء الأجزاء المناسبة داخل architecture الجديدة.

## أين أبدأ القراءة؟

- `docs/00-document-index.md`
- `docs/06-coordination-master-register.md`
- `docs/13-source-acquisition-and-legacy-migration.md`
- `docs/14-antigravity-engineering-environment.md`
- `.agents/protocols/SESSION-START.md`

لا تبدأ ببناء adapters لمستقل/خمسات/بحر قبل `T-09`، ولا تبدأ Marketing logic قبل إغلاق blockers المبكرة في `docs/10-preimplementation-plan.md`.

## حالة التحقق النهائية للحزمة

تمت مراجعة الحزمة بعد إنشاء `09-final-design-review.md` كآخر وثيقة تصميم، وكانت النتائج:

- `scripts/validate_agent_definitions.py`: **PASS — 0 errors, 0 warnings**.
- `scripts/verify_control_plane.py`: **PASS**.
- `scripts/test_hooks.py`: **PASS**.
- `scripts/scan_for_secrets.py`: **PASS**.
- Project Documentation Engine validator: **PASS — no structural errors**.
- Project Agent Workflow Engine validator: **PASS — 0 errors** مع warning مقصود لأن بعض capability/investigation gates لا يمكن إثباتها إلا على جهازك (`AG-CC-02`, `AG-CC-03`, `T-09`).
- تدقيق معرفات `A/M/T/D/R`: **0 undefined references**.

تم أثناء التدقيق أيضاً إصلاح حالة YAML كانت قد تجعل `commandExecutionPolicy: off` تُفسر Boolean بدلاً من string؛ أصبحت الآن مكتوبة صراحةً `commandExecutionPolicy: "off"` لدى الوكلاء read-only.

**الحزمة جاهزة للوضع في جذر Repository، لكن أول تشغيل يجب أن يبدأ بالـDRY-RUN المحلي قبل أي Task حقيقية.**

## ملاحظة Windows: Hooks و datacloud_telemetry

- ملفات Hooks التنفيذية الخاصة بالمشروع موجودة عمداً داخل `.agents/scripts/` لأن أوامر `.agents/hooks.json` تُحل من سياق مجلد التخصيص. لا تنقلها إلى جذر المشروع فقط.
- إذا أدى plugin عالمي باسم `googlecloudtools.datacloud_telemetry` إلى `MODULE_NOT_FOUND` ومسار Windows مكرر/مقتبس، عطّل الـplugin من **Antigravity > Settings > Customizations / Plugins** ثم أعد تشغيل Antigravity. لا تحذف مجلده يدوياً كحل دائم.
- بعد إصلاح/تعطيل plugin العالمي شغّل `python scripts/test_hooks.py` ثم جرّب `view_file` و`run_command` من جلسة جديدة.
