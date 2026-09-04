# حزمة فريق Antigravity ووركفلو Marketing OS — v1.0

هذه هي طبقة البناء والهندسة لمشروع Marketing OS بعد تحويل الـControl Plane من Codex إلى **Google Antigravity**. لا نعيد تصميم المشروع أو الـworkflow من الصفر؛ نحافظ على نفس العقود والـrouting والـworktrees والمراجعات، ونستخدم primitives الأصلية لـAntigravity.

## الفريق النهائي

جميع الأدوار تستخدم **Gemini 3.8 Flash High**:

| الدور | الاستخدام | الصلاحية |
|---|---|---|
| `orchestrator` | القرار، التقسيم، routing، التجميع | لا يدخل debug loops الروتينية |
| `explorer` | بحث دقيق داخل المشروع | Read-only |
| `builder` | التنفيذ والإصلاح المحدود | Write داخل capsule/worktree فقط |
| `verifier` | تشغيل بوابات تحقق مستقلة | لا يصلح الكود |
| `reviewer` | مراجعة مستقلة لـSTANDARD | Read-only |
| `heavy-reviewer` | مراجعة عميقة عند triggers عالية المخاطر | Read-only |

ألغيت `deep-builder` كوكيل دائم لأن كل الأدوار تستخدم النموذج نفسه. بعد محاولتي إصلاح جوهريتين فاشلتين يرجع القرار للـOrchestrator: إما capsule أصغر/مصححة أو Builder جديد بسياق نظيف أو blocker.

## نقطة مهمة جداً عن High effort

الـMain يجب أن يعمل على `gemini-3.8-flash-high` و`high`. تعريفات الـsubagents تستخدم `model: inherit` لأن frontmatter الحالي لا يحتوي حقل effort مستقل. لذلك يوجد اختبار إلزامي `AG-CC-02` للتأكد أن الـsubagents ورثت **High** فعلاً. إذا لم نستطع إثبات ذلك، لا نقبل Medium بصمت؛ نستخدم `scripts/run_antigravity_role.py` الذي يثبت `--model gemini-3.8-flash-high --effort high` لكل دور.

## أول تشغيل

1. ضع الحزمة في جذر Repository.
2. شغّل:
   ```bash
   python scripts/verify_control_plane.py
   ```
3. اقرأ `.agents/workflow/BOOTSTRAP_NEW.md`.
4. من Antigravity اختر agent باسم `orchestrator` واختر Gemini 3.8 Flash High.
5. نفّذ `.agents/workflow/DRY-RUN.md` مرة واحدة.
6. ابدأ بـ`T-08` ثم `T-01` من خطة ما قبل التنفيذ.

## Git

- MICRO البسيط فقط يمكن أن يعمل على current workspace.
- STANDARD وHEAVY: الـBuilder يُستدعى بـ`workspace=branch` ليحصل على Git worktree معزول.
- الحد التشغيلي الذي نفرضه نحن = وكيلان فرعيان نشطان كحد أقصى.
- الدمج النهائي إلى `main` يبقى بيد المؤسسين.

## Runtime المنتج

Antigravity مستخدم هنا كأداة هندسة، وهو أيضاً التقنية المفضلة لاحقاً لعقل المسوّق، لكن السياقان منفصلان. لا تنقل أسرار/صلاحيات بيئة التطوير إلى Runtime. وقرار `A-031` يبقى قائماً: Codex/OpenAI/ChatGPT ممنوعون كـruntime provider للمسوّق.
