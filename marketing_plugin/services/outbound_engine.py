"""Outbound Outreach Generation and Cadence Sequencing Service for Marketing OS.

Implements evidence-grounded outreach synthesis (A-028, M-06), 3-step cadence sequencing
(Initial Pitch, Value Case, Breakaway), strict academic integrity compliance (A-008),
secret scrubbing (A-018, I-05), multi-channel support (Email, WhatsApp, LinkedIn),
and mandatory human approval gates (A-007, I-02, A-022) with lead lifecycle state progression (M-01, M-12).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from marketing_plugin.adapters.antigravity_adapter import AntigravityAdapter
from marketing_plugin.policies.redactor import redact_secrets
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from schemas.models import (
    ActorType,
    Approval,
    ApprovalDecision,
    FunnelType,
    Interaction,
    InteractionDirection,
    Lead,
    LeadStatus,
    OutreachCadencePlan,
    OutreachMessage,
    OutreachStepType,
    utc_now,
)

logger = logging.getLogger(__name__)


class OutboundEngine:
    """Core outbound outreach synthesis and multi-step cadence orchestration service."""

    def __init__(
        self,
        db: Optional[Database] = None,
        lead_repo: Optional[LeadRepository] = None,
        company_repo: Optional[CompanyRepository] = None,
        evidence_repo: Optional[EvidenceRepository] = None,
        interaction_repo: Optional[InteractionRepository] = None,
        approval_repo: Optional[ApprovalRepository] = None,
        adapter: Optional[AntigravityAdapter] = None,
        enable_model: bool = False,
    ) -> None:
        self.db = db
        if db is not None:
            conn = db.connect()
            self.lead_repo = lead_repo or LeadRepository(conn)
            self.company_repo = company_repo or CompanyRepository(conn)
            self.evidence_repo = evidence_repo or EvidenceRepository(conn)
            self.interaction_repo = interaction_repo or InteractionRepository(conn)
            self.approval_repo = approval_repo or ApprovalRepository(conn)
        else:
            self.lead_repo = lead_repo  # type: ignore[assignment]
            self.company_repo = company_repo  # type: ignore[assignment]
            self.evidence_repo = evidence_repo  # type: ignore[assignment]
            self.interaction_repo = interaction_repo  # type: ignore[assignment]
            self.approval_repo = approval_repo  # type: ignore[assignment]

        self.adapter = adapter
        self.enable_model = enable_model

    def generate_cadence(
        self,
        lead_id: str,
        channel: str = "email",
        auto_request_approval: bool = True,
    ) -> OutreachCadencePlan:
        """Generates a personalized, evidence-grounded 3-touch follow-up cadence for a lead.

        Enforces:
        - Secret scrubbing (A-018, I-05)
        - Academic integrity policy (A-008)
        - Human approval gate (A-007, I-02, A-022)
        - Lead lifecycle state updates (M-01, M-12)

        Args:
            lead_id: Target lead identifier.
            channel: Outreach channel ('email', 'whatsapp', 'linkedin').
            auto_request_approval: Whether to create a pending approval request.

        Returns:
            OutreachCadencePlan containing the 3 messages and approval reference.
        """
        if not self.lead_repo or not self.company_repo:
            raise RuntimeError("LeadRepository and CompanyRepository are required.")

        lead = self.lead_repo.get_lead(lead_id)
        if lead is None:
            raise ValueError(f"Lead with id '{lead_id}' not found.")

        company = self.company_repo.get_company(lead.company_id)
        if company is None:
            raise ValueError(f"Company '{lead.company_id}' not found for lead '{lead_id}'.")

        ch = channel.lower().strip()
        if ch not in ("email", "whatsapp", "linkedin"):
            ch = "email"

        # 1. Evidence gathering
        evidences = []
        assessment = self.lead_repo.get_latest_assessment(lead_id)
        if assessment and assessment.evidence_ids and self.evidence_repo:
            for eid in assessment.evidence_ids:
                ev = self.evidence_repo.get_evidence(eid)
                if ev:
                    evidences.append(ev)
        if not evidences and self.evidence_repo:
            evidences = self.evidence_repo.list_for_company(company.company_id)

        # 2. Secret Redaction (A-018, I-05)
        safe_company_name = redact_secrets(company.canonical_name)
        safe_sector = redact_secrets(company.sector or "التقنية والأعمال")
        evidence_snippets = [redact_secrets(ev.fact_text) for ev in evidences if ev.fact_text]

        if evidence_snippets:
            primary_evidence = evidence_snippets[0]
        else:
            primary_evidence = f"مبادرات التحول الرقمي وتطوير الحلول البرمجية في قطاع {safe_sector}"

        # 3. Tone & Cadence Synthesis (B2B vs Academic per A-008)
        if lead.funnel == FunnelType.ACADEMIC:
            messages = self._build_academic_cadence(
                company_name=safe_company_name,
                primary_evidence=primary_evidence,
                channel=ch,
            )
        else:
            messages = self._build_b2b_cadence(
                company_name=safe_company_name,
                sector=safe_sector,
                primary_evidence=primary_evidence,
                channel=ch,
            )

        cadence_id = f"cad_{uuid.uuid4().hex[:12]}"
        plan = OutreachCadencePlan(
            cadence_id=cadence_id,
            lead_id=lead.lead_id,
            company_id=company.company_id,
            channel=ch,
            messages=messages,
            created_at=utc_now(),
        )

        # 4. Save Draft Interactions (actor='agent_draft')
        if self.interaction_repo:
            for msg in messages:
                int_id = f"int_out_{uuid.uuid4().hex[:12]}"
                interaction = Interaction(
                    interaction_id=int_id,
                    lead_id=lead.lead_id,
                    channel=ch,
                    external_party_ref=safe_company_name,
                    direction=InteractionDirection.OUTBOUND,
                    actor=ActorType.AGENT_DRAFT,
                    content_summary=f"[{ch.upper()}] الخطوة {msg.step_number} ({msg.step_type.value}): {msg.subject or msg.cta[:40]}",
                    outcome_tag=f"cadence_step_{msg.step_number}",
                    raw_content_path=msg.body,
                    occurred_at=utc_now(),
                )
                self.interaction_repo.save_interaction(interaction)

        # 5. Human Approval Gate (A-007, I-02, A-022) & Status Progression
        if auto_request_approval and self.approval_repo:
            approval_id = f"appr_out_{uuid.uuid4().hex[:12]}"
            approval = Approval(
                approval_id=approval_id,
                action_type="outreach_send",
                target_type="lead",
                target_id=lead.lead_id,
                decision=ApprovalDecision.PENDING,
                notes=f"مسودة حملة تواصل {ch.upper()} لشركة {safe_company_name} (3 خطوات تواصل)",
                requested_at=utc_now(),
            )
            self.approval_repo.create_request(approval)
            plan.approval_id = approval_id

            # Transition lead status to OUTREACH_READY (M-01)
            lead.status = LeadStatus.OUTREACH_READY
            lead.next_action = "awaiting_approval"
            lead.updated_at = utc_now()
            self.lead_repo.save_lead(lead)

        return plan

    def record_contact_attempt(
        self,
        lead_id: str,
        channel: str,
        actor_id: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Records that an outreach touchpoint was sent, advancing lead to CONTACTED.

        Enforces:
        - Lead lifecycle state progression (M-01, M-12): OUTREACH_READY -> CONTACTED.
        - Next action updated to 'awaiting_lead_reply'.
        - Real dispatch logged in InteractionRepository with actor=HUMAN.

        Args:
            lead_id: Lead identifier.
            channel: Delivery channel used.
            actor_id: Human operator / founder identifier who dispatched.
            notes: Optional execution details or notes.

        Returns:
            True if status was transitioned, False otherwise.
        """
        if not self.lead_repo:
            return False

        lead = self.lead_repo.get_lead(lead_id)
        if lead is None:
            logger.warning("Attempted to record contact attempt for missing lead %s", lead_id)
            return False

        lead.status = LeadStatus.CONTACTED
        lead.next_action = "awaiting_lead_reply"
        lead.updated_at = utc_now()
        self.lead_repo.save_lead(lead)

        if self.interaction_repo:
            int_id = f"int_out_{uuid.uuid4().hex[:12]}"
            ch = channel.lower().strip()
            interaction = Interaction(
                interaction_id=int_id,
                lead_id=lead.lead_id,
                channel=ch,
                external_party_ref=lead.company_id,
                direction=InteractionDirection.OUTBOUND,
                actor=ActorType.HUMAN,
                content_summary=notes or f"تم تنفيذ التواصل المباشر عبر {ch.upper()} بواسطة {actor_id}",
                outcome_tag="contacted",
                occurred_at=utc_now(),
            )
            self.interaction_repo.save_interaction(interaction)

        return True

    # --- Cadence Builders ---

    def _build_b2b_cadence(
        self,
        company_name: str,
        sector: str,
        primary_evidence: str,
        channel: str,
    ) -> List[OutreachMessage]:
        """Synthesizes high-converting, evidence-grounded B2B follow-up sequence."""
        if channel == "whatsapp":
            step1 = OutreachMessage(
                step_number=1,
                step_type=OutreachStepType.INITIAL_PITCH,
                channel=channel,
                subject=None,
                body=(
                    f"مرحباً بك أستاذي الكريم، معكم فريق IntelliFY لأتمتة وتطوير الأنظمة.\n\n"
                    f"لفت انتباهنا مؤخراً اهتمامكم في {company_name} بموضوع: ({primary_evidence}).\n"
                    f"نحن متخصصون في بناء برمجيات وأتمتة مسارات العمل لقطاع {sector} بهدف خفض التكاليف التشغيلية بنسبة تتجاوز 40%.\n\n"
                    f"هل يناسبكم اتصال هاتفي سريع لمدة 5 دقائق لاستعراض نموذج أولي مقترح لـ {company_name}؟"
                ),
                cta="هل يناسبك اتصال سريع لمدة 5 دقائق هذا الأسبوع؟",
                delay_days=0,
            )
            step2 = OutreachMessage(
                step_number=2,
                step_type=OutreachStepType.VALUE_CASE,
                channel=channel,
                subject=None,
                body=(
                    f"السلام عليكم أستاذنا، متابعة سريعة لرسالتنا السابقة حول أتمتة العمليات في {company_name}.\n\n"
                    f"أحببت مشاركة نتيجة حققناها مؤخراً مع شركة مشابهة في قطاع {sector}:\n"
                    f"• تقليص زمن إنجاز المعاملات بنسبة 65% عبر نظام سير عمل ذكي.\n"
                    f"• تكامل فوري وسلس مع الأنظمة الحالية دون انقطاع تشغيلي.\n\n"
                    f"إذا أحببتم، يمكننا مشاركة مخطط المعمارية التقنية المناسب لنظامكم."
                ),
                cta="يسعدنا إرسال دراسة الحالة والمخطط الفني إذا ناسبكم.",
                delay_days=3,
            )
            step3 = OutreachMessage(
                step_number=3,
                step_type=OutreachStepType.BREAKAWAY,
                channel=channel,
                subject=None,
                body=(
                    f"أهلاً بكم مجدداً، أقدّر انشغالكم بالمهام التشغيلية في {company_name}.\n\n"
                    f"لن أقوم بإزعاجكم بمزيد من الرسائل المتتابعة. إذا كان تطوير حلول الأتمتة والذكاء الاصطناعي ضمن أولوياتكم القادمة، فنحن جاهزون دائماً للتعاون.\n\n"
                    f"تمنياتنا لكم ولفريقكم الكريم بدوام التوفيق والنجاح."
                ),
                cta="باب التواصل مفتوح دائماً متى ما كانت الأتمتة ضمن أولوياتكم.",
                delay_days=5,
            )
        elif channel == "linkedin":
            step1 = OutreachMessage(
                step_number=1,
                step_type=OutreachStepType.INITIAL_PITCH,
                channel=channel,
                subject=f"تطوير وأتمتة العمليات التقنية لـ {company_name}",
                body=(
                    f"تحية طيبة،\n\n"
                    f"تابعت باهتمام نشاط {company_name} وتوجهكم نحو ({primary_evidence}).\n"
                    f"في IntelliFY، نساعد المنشآت الرائدة في قطاع {sector} على بناء وتطوير حلول الأتمتة وهندسة البرمجيات التي ترفع الكفاءة التشغيلية بصورة فورية.\n\n"
                    f"يسعدني مشاركة فكرة أولية حول كيفية تطبيق هذه الحلول لديكم."
                ),
                cta="هل يناسبكم تبادل نقاش قصير عبر الرسائل أو مكالمة سريعة؟",
                delay_days=0,
            )
            step2 = OutreachMessage(
                step_number=2,
                step_type=OutreachStepType.VALUE_CASE,
                channel=channel,
                subject=f"دراسة حالة في قطاع {sector}: عوائد الأتمتة",
                body=(
                    f"مرحباً مجدداً،\n\n"
                    f"استكمالاً لتواصلي السابق، قمنا مؤخراً بتطوير بنية تكامل برمجية لشركة تعمل في قطاع {sector}، حيث نجح الفريق في تسريع وتيرة المعالجة بـ 3 أضعاف مع ضمان استقرار وأمان البيانات الكامل.\n\n"
                    f"يسعدني تزويدكم بتفاصيل التجربة والمخطط المعماري المقترح."
                ),
                cta="أخبرني إن كنت ترغب في الاطلاع على ملخص الحالة الفنية.",
                delay_days=3,
            )
            step3 = OutreachMessage(
                step_number=3,
                step_type=OutreachStepType.BREAKAWAY,
                channel=channel,
                subject="إغلاق حلقة التواصل — IntelliFY",
                body=(
                    f"تحياتي، أعلم تماماً مدى انشغال جدولكم القيادي في {company_name}.\n\n"
                    f"سأكتفي بهذا القدر من المتابعة لعدم إشغال وقتكم. سأكون سعيداً بإعادة فتح النقاش متى ما أصبحت مبادرات الأتمتة والتحول التقني على جدول أعمالكم.\n\n"
                    f"دمتم بكل خير ونجاح."
                ),
                cta="يسعدني بقاء قنوات الاتصال مفتوحة في شبكتنا المهنية.",
                delay_days=5,
            )
        else:  # email (default)
            step1 = OutreachMessage(
                step_number=1,
                step_type=OutreachStepType.INITIAL_PITCH,
                channel=channel,
                subject=f"فرصة تعاون تقني وأتمتة مسارات العمل لـ {company_name}",
                body=(
                    f"السادة الكرام في {company_name}،\n\n"
                    f"تحية طيبة وبعد،،\n\n"
                    f"لفت انتباهنا مؤخراً اهتمامكم وسعيكم الملحوظ في مجال ({primary_evidence}).\n"
                    f"نحن في شركة IntelliFY نتخصص في تصميم وتطوير الأنظمة البرمجية وحلول الأتمتة الذكية لقطاع {sector}، حيث نساعد المنشآت على تحويل التحديات التشغيلية إلى مسارات رقمية موثوقة وعالية الأداء.\n\n"
                    f"نود اقتراح نموذج عمل تقني مبدئي ومخصص لاحتياجات {company_name} يسهم في رفع الإنتاجية وتقليل التكاليف التشغيلية."
                ),
                cta="هل يناسبكم اجتماع افتراضي سريع (15 دقيقة) خلال هذا الأسبوع لاستعراض النموذج المبدئي؟",
                delay_days=0,
            )
            step2 = OutreachMessage(
                step_number=2,
                step_type=OutreachStepType.VALUE_CASE,
                channel=channel,
                subject=f"دراسة حالة فنية: كيف حققنا وفراً بنسبة 40% في قطاع {sector}",
                body=(
                    f"السادة في {company_name}،\n\n"
                    f"السلام عليكم ورحمة الله وبركاته،\n\n"
                    f"متابعةً لرسالتي السابقة بخصوص حلول الأتمتة الرقمية؛ أردت مشاركتكم نموذجاً واقعياً لمشروع أنجزناه مؤخراً في قطاع {sector}:\n\n"
                    f"1. التحدي: تشتت البيانات بين الأنظمة وبطء في العمليات اليدوية.\n"
                    f"2. الحل التقني: منصة مركزية ذكية مع ربط تكاملي كامل عبر واجهات برمجة التطبيقات (APIs).\n"
                    f"3. العائد الفعلي: تقليص زمن الإنجاز بنسبة 65%، وتحقيق عائد استثماري خلال 60 يوماً فقط.\n\n"
                    f"نحن على ثقة بأن تطبيق نموذج مماثل في {company_name} سيحقق نتائج ملموسة."
                ),
                cta="هل ترغبون في إرسال المستند التعريفي ودراسة الحالة الكاملة للاطلاع عليها؟",
                delay_days=3,
            )
            step3 = OutreachMessage(
                step_number=3,
                step_type=OutreachStepType.BREAKAWAY,
                channel=channel,
                subject=f"إغلاق المتابعة المؤقتة — نتمنى لـ {company_name} مزيداً من التوفيق",
                body=(
                    f"السادة الأفاضل في {company_name}،\n\n"
                    f"تحية تقدير واحترام،\n\n"
                    f"أعلم تماماً كثافة الأولويات والمشاغل لديكم، ولذلك لن أقوم بإرسال رسائل متابعة إضافية حرصاً على وقتكم الثمين.\n\n"
                    f"في حال أصبحت أتمتة العمليات البرمجية وبناء الحلول الذكية أولوية لـ {company_name} في الفترات القادمة، يسعدنا دوماً تواصلكم معنا عبر هذا البريد أو عبر موقعنا الإلكتروني.\n\n"
                    f"مع خالص تمنياتنا لكم ولفريق عملكم بالتوفيق والريادة."
                ),
                cta="يسعدنا دائماً تقديم الاستشارة التقنية متى ما رأيتم الوقت مناسباً.",
                delay_days=5,
            )

        return [step1, step2, step3]

    def _build_academic_cadence(
        self,
        company_name: str,
        primary_evidence: str,
        channel: str,
    ) -> List[OutreachMessage]:
        """Synthesizes ethical, academic-integrity compliant mentoring sequence (A-008).

        STRICT INVARIANT: No ghostwriting, no exam cheating, no writing thesis on behalf.
        Only legitimate academic consultation, methodology mentorship, and statistical guidance.
        """
        step1 = OutreachMessage(
            step_number=1,
            step_type=OutreachStepType.INITIAL_PITCH,
            channel=channel,
            subject=f"استشارة منهجية وبحثية: دعم الدراسات العليا في مجال ({company_name})",
            body=(
                f"الأستاذ والباحث الفاضل،\n\n"
                f"تحية طيبة وبعد،،\n\n"
                f"اطلعنا على اهتمامكم البحثي المتميز في سياق ({primary_evidence}).\n"
                f"نقدم في IntelliFY خدمات التوجيه والإرشاد الأكاديمي المنهجي، حيث نساعد الباحثين وطلاب الدراسات العليا في:\n"
                f"• بناء وتدقيق خطط البحث والمنهجيات العلمية وفق المعايير المحكمة.\n"
                f"• الإرشاد في التحليل الإحصائي المتقدم وبرمجة النماذج البحثية (Python / R / SPSS).\n"
                f"• مراجعة سلامة التصميم التجريبي وضمان معايير النزاهة العلمية وقابلية التكرار (Reproducibility).\n\n"
                f"نلتزم بأعلى معايير النزاهة الأكاديمية الصارمة لتمكين الباحث من إتقان أطروحته بنفسه واجتياز المناقشة باقتدار."
            ),
            cta="هل ترغب في جلسة استشارية أولية (15 دقيقة) لمناقشة منهجية البحث وخطة التحليل؟",
            delay_days=0,
        )
        step2 = OutreachMessage(
            step_number=2,
            step_type=OutreachStepType.VALUE_CASE,
            channel=channel,
            subject="نموذج توجيه بحثي ناجح: إعداد النماذج الإحصائية للنشر العلمي",
            body=(
                f"أهلاً بكم مجدداً،\n\n"
                f"متابعةً لاستشارتنا حول الأبحاث الأكاديمية؛ نود مشاركتكم تجربة باحث استرشد بخدماتنا التوجيهية في بناء نموذج إحصائي متقدم، حيث تمكن من:\n"
                f"1. إتقان التحليل الإحصائي والدفاع عن نتائجه بثقة كاملة أمام لجنة التحكيم.\n"
                f"2. ضبط منهجية جمع البيانات وتحقيق الدقة العلمية المطلوبة للنشر في المجلات المصنفة.\n"
                f"3. الاعتماد الكامل على الفهم الذاتي الخالي من أي إخلال بأخلاقيات البحث العلمي.\n\n"
                f"يسعدنا تزويدكم بدليلنا الإرشادي حول أفضل الممارسات في إعداد المنهجيات العلمية."
            ),
            cta="يسعدنا إرسال الدليل الإرشادي المنهجي إذا ناسبكم.",
            delay_days=3,
        )
        step3 = OutreachMessage(
            step_number=3,
            step_type=OutreachStepType.BREAKAWAY,
            channel=channel,
            subject="إغلاق المتابعة الأكاديمية — تمنياتنا لكم بمسيرة بحثية موفقة",
            body=(
                f"الباحث الكريم،\n\n"
                f"تقديراً لانشغالكم بمراحل البحث والتحصيل العلمي، لن نقوم بإرسال متابعات لاحقة عبر هذه القناة.\n\n"
                f"إذا احتجتم في أي مرحلة قادمة إلى استشارة منهجية أو تدقيق إحصائي احترافي يثري عملكم البحثي المستقل، فنحن في خدمتكم دوماً.\n\n"
                f"نسأل الله لكم التوفيق الدائم ونيل أعلى المراتب العلمية."
            ),
            cta="أبواب الاستشارة المنهجية مفتوحة لكم في أي وقت خلال رحلتكم الأكاديمية.",
            delay_days=5,
        )
        return [step1, step2, step3]
