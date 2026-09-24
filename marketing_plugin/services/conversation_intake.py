"""Conversation Intake and Inbound Qualification Service for Marketing OS.

Implements inbound conversational capture across WhatsApp (A-022), Telegram,
Email, and Web inquiries. Enforces strict academic integrity filtering (A-008),
secret scrubbing (A-018, I-05), entity & lead resolution, intent & dual-funnel
classification (A-003), and high-converting reply draft generation guarded by
human operator approval (A-007, I-02).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from marketing_plugin.adapters.antigravity_adapter import AntigravityAdapter
from marketing_plugin.policies.redactor import redact_secrets
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.entity_resolver import EntityResolver
from marketing_plugin.services.lead_scorer import ACADEMIC_VIOLATION_PATTERNS
from schemas.models import (
    ActorType,
    Approval,
    ApprovalDecision,
    FunnelType,
    Interaction,
    InteractionDirection,
    Lead,
    LeadStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

# Academic mentoring intent keywords (ethical inquiries)
ACADEMIC_MENTORING_KEYWORDS = [
    "ماجستير",
    "دكتوراه",
    "أطروحة",
    "اطروحة",
    "بحث علمي",
    "دراسة استطلاعية",
    "تحليل إحصائي",
    "spss",
    "توجيه أكاديمي",
    "منهجية البحث",
    "استشارة بحثية",
    "academic",
    "mentoring",
    "thesis consulting",
    "research methodology",
]

# B2B enterprise automation keywords
B2B_KEYWORDS = [
    "أتمتة",
    "نظام",
    "تطبيق",
    "برمجة",
    "موقع",
    "crm",
    "erp",
    "ذكاء اصطناعي",
    "ai",
    "dashboard",
    "لوحة تحكم",
    "سيرفر",
    "api",
    "شات بوت",
    "chatbot",
    "ربط",
    "حلول تقنية",
    "متجر",
    "automation",
    "integration",
    "software",
    "فواتير",
    "مبيعات",
    "مخزون",
    "wms",
]

ETHICAL_ACADEMIC_REJECTION_NOTICE = (
    "نعتذر منك، تلتزم IntelliFY بأعلى معايير النزاهة الأكاديمية (A-008) "
    "ولا تقدم خدمات حل الامتحانات أو كتابة الأطروحات والأبحاث نيابة عن الطلاب. "
    "خدماتنا محصورة فقط في الاستشارات المنهجية والتحليل الإحصائي والتوجيه الأكاديمي المشروع."
)


@dataclass
class IntakeOutcome:
    """Outcome of processing an inbound conversation message."""
    success: bool
    interaction_id: str
    lead_id: Optional[str]
    company_id: Optional[str]
    channel: str
    funnel: str  # "b2b" or "academic"
    intent: str  # "b2b_inquiry", "academic_mentoring", "academic_violation", "general_inquiry"
    is_academic_violation: bool
    suggested_reply: Optional[str] = None
    approval_id: Optional[str] = None
    status: str = "received"  # "pending_approval", "rejected_academic_violation", "draft_ready"
    reasoning: Optional[str] = None


class ConversationIntakeService:
    """Manages intake, safety checks, lead resolution, and draft reply generation."""

    def __init__(
        self,
        db: Optional[Database] = None,
        interaction_repo: Optional[InteractionRepository] = None,
        lead_repo: Optional[LeadRepository] = None,
        company_repo: Optional[CompanyRepository] = None,
        approval_repo: Optional[ApprovalRepository] = None,
        entity_resolver: Optional[EntityResolver] = None,
        antigravity_adapter: Optional[AntigravityAdapter] = None,
        enable_model_reasoning: bool = False,
    ) -> None:
        self.db = db or Database("data/marketing.db")
        conn = self.db.connect()

        self.interaction_repo = interaction_repo or InteractionRepository(conn)
        self.lead_repo = lead_repo or LeadRepository(conn)
        self.company_repo = company_repo or CompanyRepository(conn)
        self.approval_repo = approval_repo or ApprovalRepository(conn)
        self.entity_resolver = entity_resolver or EntityResolver(self.company_repo)
        self.antigravity_adapter = antigravity_adapter
        self.enable_model_reasoning = enable_model_reasoning

    def ingest_message(
        self,
        channel: str,
        external_party_ref: str,
        message_text: str,
        country_code: Optional[str] = None,
        sender_name: Optional[str] = None,
        company_name: Optional[str] = None,
        auto_request_approval: bool = True,
    ) -> IntakeOutcome:
        """Processes an inbound message across channels with safety and approval gates.

        Args:
            channel: Inbound channel (e.g. 'whatsapp', 'telegram', 'email', 'web').
            external_party_ref: External identifier (phone number, handle, email).
            message_text: Raw inbound message body.
            country_code: Regional country code ISO (default: 'SA').
            sender_name: Optional sender display name.
            company_name: Optional explicit company name.
            auto_request_approval: Whether to register an outreach reply approval.
        """
        ch = channel.lower().strip()
        sender_ref = external_party_ref.strip()
        cc = (country_code or "SA").strip().upper()

        # Step 1: Secret Scrubbing (A-018, I-05)
        sanitized_text = redact_secrets(message_text.strip())
        sanitized_sender = redact_secrets(sender_ref)

        # Step 2: Strict Academic Integrity Guard (A-008)
        if self._is_academic_violation(message_text) or self._is_academic_violation(sanitized_text):
            logger.warning(
                "Academic integrity violation detected from %s on channel %s",
                sanitized_sender,
                ch,
            )
            return self._handle_academic_violation(
                channel=ch,
                sender_ref=sanitized_sender,
                sanitized_text=sanitized_text,
                country_code=cc,
                sender_name=sender_name,
                company_name=company_name,
            )

        # Step 3: Intent & Funnel Classification (A-003)
        funnel, intent, service_key = self._classify_intent(sanitized_text)

        # Step 4: Entity & Lead Resolution
        company, lead = self._resolve_entity_and_lead(
            channel=ch,
            sender_ref=sanitized_sender,
            country_code=cc,
            sender_name=sender_name,
            company_name=company_name,
            funnel=funnel,
            service_key=service_key,
            intent=intent,
        )

        # Step 5: Save Inbound Interaction
        inbound_interaction_id = f"intk_{uuid.uuid4().hex[:12]}"
        inbound_interaction = Interaction(
            interaction_id=inbound_interaction_id,
            lead_id=lead.lead_id,
            channel=ch,
            external_party_ref=sanitized_sender,
            direction=InteractionDirection.INBOUND,
            actor=ActorType.EXTERNAL,
            content_summary=sanitized_text,
            outcome_tag=intent,
            occurred_at=utc_now(),
        )
        self.interaction_repo.save_interaction(inbound_interaction)

        # Step 6: Generate High-Converting Reply Draft (actor='agent_draft')
        draft_reply = self._generate_reply_draft(
            intent=intent,
            funnel=funnel,
            sanitized_text=sanitized_text,
            company_name=company.canonical_name,
        )

        draft_interaction_id = f"intk_{uuid.uuid4().hex[:12]}"
        draft_interaction = Interaction(
            interaction_id=draft_interaction_id,
            lead_id=lead.lead_id,
            channel=ch,
            external_party_ref=sanitized_sender,
            direction=InteractionDirection.OUTBOUND,
            actor=ActorType.AGENT_DRAFT,
            content_summary=draft_reply,
            outcome_tag="pending_approval",
            occurred_at=utc_now(),
        )
        self.interaction_repo.save_interaction(draft_interaction)

        # Step 7: Human Approval Gate (A-007, I-02, A-022)
        approval_id: Optional[str] = None
        status = "draft_ready"

        if auto_request_approval:
            approval_id = f"appr_{uuid.uuid4().hex[:12]}"
            notes_payload = {
                "channel": ch,
                "external_party_ref": sanitized_sender,
                "draft_reply": draft_reply,
                "draft_interaction_id": draft_interaction_id,
                "inbound_interaction_id": inbound_interaction_id,
                "lead_id": lead.lead_id,
                "company_id": company.company_id,
                "company_name": company.canonical_name,
                "funnel": funnel.value,
                "intent": intent,
            }
            approval = Approval(
                approval_id=approval_id,
                action_type="outreach_reply",
                target_type="interaction",
                target_id=draft_interaction_id,
                decision=ApprovalDecision.PENDING,
                notes=json.dumps(notes_payload, ensure_ascii=False),
                requested_at=utc_now(),
            )
            self.approval_repo.create_request(approval)
            status = "pending_approval"

        return IntakeOutcome(
            success=True,
            interaction_id=inbound_interaction_id,
            lead_id=lead.lead_id,
            company_id=company.company_id,
            channel=ch,
            funnel=funnel.value,
            intent=intent,
            is_academic_violation=False,
            suggested_reply=draft_reply,
            approval_id=approval_id,
            status=status,
            reasoning=(
                f"Inbound {ch} message classified as {intent} (funnel: {funnel.value}). "
                f"Entity resolved to '{company.canonical_name}'. "
                f"Reply draft recorded with actor='agent_draft' and queued for founder approval."
            ),
        )

    # --- Internal Helpers ---

    def _is_academic_violation(self, text: str) -> bool:
        """Deterministic safety check against cheating/ghostwriting keywords per A-008."""
        lower_text = text.lower()
        for pattern in ACADEMIC_VIOLATION_PATTERNS:
            if pattern.lower() in lower_text:
                return True
        return False

    def _handle_academic_violation(
        self,
        channel: str,
        sender_ref: str,
        sanitized_text: str,
        country_code: str,
        sender_name: Optional[str],
        company_name: Optional[str],
    ) -> IntakeOutcome:
        """Enforces deterministic rejection and logs violation per A-008."""
        # Resolve company identity for audit tracking
        company, lead = self._resolve_entity_and_lead(
            channel=channel,
            sender_ref=sender_ref,
            country_code=country_code,
            sender_name=sender_name,
            company_name=company_name,
            funnel=FunnelType.ACADEMIC,
            service_key=None,
            intent="academic_violation",
        )

        # Mark lead as rejected immediately
        lead.status = LeadStatus.REJECTED
        lead.funnel = FunnelType.ACADEMIC
        lead.next_action = "rejected_academic_violation"
        lead.priority_bucket = 3
        self.lead_repo.save_lead(lead)

        # Log inbound interaction with violation tag
        interaction_id = f"intk_{uuid.uuid4().hex[:12]}"
        interaction = Interaction(
            interaction_id=interaction_id,
            lead_id=lead.lead_id,
            channel=channel,
            external_party_ref=sender_ref,
            direction=InteractionDirection.INBOUND,
            actor=ActorType.EXTERNAL,
            content_summary=sanitized_text,
            outcome_tag="academic_violation",
            occurred_at=utc_now(),
        )
        self.interaction_repo.save_interaction(interaction)

        return IntakeOutcome(
            success=True,
            interaction_id=interaction_id,
            lead_id=lead.lead_id,
            company_id=company.company_id,
            channel=channel,
            funnel=FunnelType.ACADEMIC.value,
            intent="academic_violation",
            is_academic_violation=True,
            suggested_reply=ETHICAL_ACADEMIC_REJECTION_NOTICE,
            approval_id=None,
            status="rejected_academic_violation",
            reasoning="Academic integrity violation detected (A-008). Lead automatically rejected without outreach approval.",
        )

    def _classify_intent(self, text: str) -> tuple[FunnelType, str, str]:
        """Classifies text into FunnelType, intent string, and default service key."""
        lower = text.lower()

        # Check for legitimate academic mentoring
        for kw in ACADEMIC_MENTORING_KEYWORDS:
            if kw.lower() in lower:
                return FunnelType.ACADEMIC, "academic_mentoring", "academic_mentoring"

        # Check for B2B inquiry
        for kw in B2B_KEYWORDS:
            if kw.lower() in lower:
                return FunnelType.B2B, "b2b_inquiry", "ai_automation"

        # Default general inquiry
        return FunnelType.B2B, "general_inquiry", "general_consulting"

    def _resolve_entity_and_lead(
        self,
        channel: str,
        sender_ref: str,
        country_code: str,
        sender_name: Optional[str],
        company_name: Optional[str],
        funnel: FunnelType,
        service_key: Optional[str],
        intent: str,
    ) -> tuple[Any, Lead]:
        """Resolves company entity and gets or creates the associated Lead."""
        # 1. Determine canonical name
        if company_name and company_name.strip():
            cname = company_name.strip()
        elif sender_name and sender_name.strip():
            cname = f"{sender_name.strip()} ({channel.capitalize()})"
        else:
            cname = f"{channel.capitalize()} Lead ({sender_ref})"

        # 2. Extract domain or contact points
        primary_domain = None
        contacts: Dict[str, Any] = {channel: sender_ref}

        if "@" in sender_ref and "." in sender_ref.split("@")[-1]:
            primary_domain = sender_ref.split("@")[-1].strip().lower()
            contacts["email"] = sender_ref
        elif any(c.isdigit() for c in sender_ref):
            contacts["phone"] = sender_ref

        # 3. Resolve Company via EntityResolver
        resolution = self.entity_resolver.resolve(
            canonical_name=cname,
            country_code=country_code,
            primary_domain=primary_domain,
            public_contacts=contacts,
            funnel=funnel,
        )
        company = resolution.company

        # 4. Resolve or create Lead
        lead = self.lead_repo.get_lead_by_company(company.company_id)

        # Validate service_key against service_profiles FK
        valid_service_key = None
        if service_key:
            try:
                cur = self.db.connect().cursor()
                cur.execute("SELECT 1 FROM service_profiles WHERE service_key = ?;", (service_key,))
                if cur.fetchone():
                    valid_service_key = service_key
            except Exception:
                pass

        if not lead:
            lead_id = f"lead_{uuid.uuid4().hex[:12]}"
            priority = 1 if intent == "b2b_inquiry" else 2
            initial_status = (
                LeadStatus.REJECTED if intent == "academic_violation" else LeadStatus.QUALIFIED
            )
            lead = Lead(
                lead_id=lead_id,
                company_id=company.company_id,
                funnel=funnel,
                status=initial_status,
                priority_bucket=priority,
                recommended_service_key=valid_service_key,
                next_action="awaiting_founder_reply_approval",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.lead_repo.save_lead(lead)
        else:
            # If lead was discovered or previous violation was cleaned
            if lead.status == LeadStatus.DISCOVERED and intent != "academic_violation":
                lead.status = LeadStatus.QUALIFIED
                lead.funnel = funnel
                lead.recommended_service_key = valid_service_key or lead.recommended_service_key
                lead.next_action = "awaiting_founder_reply_approval"
                lead.priority_bucket = 1 if intent == "b2b_inquiry" else lead.priority_bucket
                self.lead_repo.save_lead(lead)

        return company, lead

    def _generate_reply_draft(
        self,
        intent: str,
        funnel: FunnelType,
        sanitized_text: str,
        company_name: str,
    ) -> str:
        """Synthesizes high-converting reply draft adhering to Google-only and zero-paid rules."""
        if intent == "academic_mentoring" or funnel == FunnelType.ACADEMIC:
            return (
                "أهلاً بك! شكراً لتواصلك مع IntelliFY. "
                "نقدم خدمات التوجيه الأكاديمي والاستشارات المنهجية والتحليل الإحصائي المتقدم "
                "لمساعدة الباحثين والطلاب على إنجاز أبحاثهم بأنفسهم وفق أعلى معايير الجودة والنزاهة العلمية. "
                "يسعدنا الاطلاع على ملخص فكرة بحثك أو استفسارك المنهجي لتحديد الدعم الأنسب. ما هو التخصص ومجال الدراسة؟"
            )

        if intent == "b2b_inquiry":
            return (
                "أهلاً بك! شكراً لتواصلك مع IntelliFY. "
                "نحن متخصصون في أتمتة الأنظمة وبناء الحلول الذكية المخصصة للشركات لرفع كفاءة العمليات وزيادة المبيعات. "
                "يسعدنا ترتيب مكالمة استكشافية سريعة لمدة 15 دقيقة لمناقشة متطلباتكم وتوضيح كيف يمكننا تقديم حل متكامل يناسب احتياجكم. "
                "ما هو الوقت الأنسب لكم لمكالمة سريعة هذا الأسبوع؟"
            )

        # General inquiry fallback
        return (
            "أهلاً ومرحباً بك في IntelliFY! "
            "نسعد بتواصلك، ونحن جاهزون لمساعدتك سواء في تطوير الحلول التقنية وأتمتة الأعمال للشركات أو في الاستشارات المنهجية. "
            "كيف يمكننا خدمتك اليوم؟"
        )
