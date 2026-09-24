"""Unit tests for ConversationIntakeService.

Verifies:
1. Secret sanitization on inbound messages (A-018, I-05).
2. Deterministic academic integrity violation detection and rejection (A-008).
3. B2B entity extraction, lead association, and priority scoring.
4. Legitimate academic mentoring classification (A-003).
5. Safe actor tagging and approval registration (A-007, I-02, A-022).
6. Multi-touch message ingestion for the same company/lead.
"""
from __future__ import annotations

import json
import unittest

from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.conversation_intake import (
    ConversationIntakeService,
    IntakeOutcome,
)
from schemas.models import (
    ActorType,
    ApprovalDecision,
    FunnelType,
    InteractionDirection,
    LeadStatus,
)


class TestConversationIntakeService(unittest.TestCase):
    """Hermetic unit tests for conversation intake and inbound lead qualification."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed countries and services for FK reference
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'UAE', '["ar", "en"]', 0.25);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Academic Mentoring');
        """)
        self.conn.commit()

        self.interaction_repo = InteractionRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.company_repo = CompanyRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        self.service = ConversationIntakeService(
            db=self.db,
            interaction_repo=self.interaction_repo,
            lead_repo=self.lead_repo,
            company_repo=self.company_repo,
            approval_repo=self.approval_repo,
        )

    def test_secret_sanitization_inbound_message(self):
        """Sensitive credentials in inbound messages must be redacted per I-05 / A-018."""
        secret_msg = "مرحبا، هذا مفتاح الربط sk-live-1234567890abcdef1234567890abcdef ونريد ربط النظام"
        outcome = self.service.ingest_message(
            channel="whatsapp",
            external_party_ref="+966512345678",
            message_text=secret_msg,
            company_name="Security Corp",
        )

        self.assertTrue(outcome.success)
        self.assertFalse(outcome.is_academic_violation)

        # Inspect persisted inbound interaction
        inbound = self.interaction_repo.get_interaction(outcome.interaction_id)
        self.assertIsNotNone(inbound)
        self.assertNotIn("sk-live-1234567890abcdef1234567890abcdef", inbound.content_summary)
        self.assertIn("[REDACTED_SECRET]", inbound.content_summary)

        # Inspect approval notes
        approval = self.approval_repo.get_approval(outcome.approval_id)
        self.assertIsNotNone(approval)
        self.assertNotIn("sk-live-1234567890abcdef1234567890abcdef", approval.notes)

    def test_academic_violation_deterministic_rejection(self):
        """Cheating or ghostwriting requests must be rejected immediately per A-008."""
        cheating_inquiries = [
            "أحتاج حل امتحان الرياضيات غداً نيابة عني بمقابل",
            "مطلوب حل كويز وإرسال الإجابات فوراً",
            "أريد شخص يكتب لي رسالة ماجستير بالكامل بدون أي تدخل مني",
            "Please take my exam for me next week",
            "Can you write my dissertation for money?",
        ]

        for idx, text in enumerate(cheating_inquiries):
            outcome = self.service.ingest_message(
                channel="telegram",
                external_party_ref=f"@cheater_{idx}",
                message_text=text,
            )

            self.assertTrue(outcome.success)
            self.assertTrue(outcome.is_academic_violation)
            self.assertEqual(outcome.funnel, "academic")
            self.assertEqual(outcome.intent, "academic_violation")
            self.assertEqual(outcome.status, "rejected_academic_violation")
            self.assertIsNone(outcome.approval_id)
            self.assertIn("النزاهة الأكاديمية", outcome.suggested_reply)

            # Lead must be marked REJECTED in database
            lead = self.lead_repo.get_lead(outcome.lead_id)
            self.assertIsNotNone(lead)
            self.assertEqual(lead.status, LeadStatus.REJECTED)
            self.assertEqual(lead.next_action, "rejected_academic_violation")

            # Interaction must be logged with academic_violation tag
            interaction = self.interaction_repo.get_interaction(outcome.interaction_id)
            self.assertEqual(interaction.outcome_tag, "academic_violation")
            self.assertEqual(interaction.direction, InteractionDirection.INBOUND)
            self.assertEqual(interaction.actor, ActorType.EXTERNAL)

    def test_b2b_inquiry_intake_and_approval_flow(self):
        """B2B inquiries must be classified, qualified, and queued for approval."""
        msg = "السلام عليكم، نحن شركة استشارات لوجستية ونحتاج أتمتة عمليات الفوترة وتتبع الشحنات مع نظام ERP"
        outcome = self.service.ingest_message(
            channel="whatsapp",
            external_party_ref="+966551234567",
            message_text=msg,
            sender_name="Ahmed Al-Otaibi",
            company_name="Logistics Pro KSA",
            country_code="SA",
            auto_request_approval=True,
        )

        self.assertTrue(outcome.success)
        self.assertFalse(outcome.is_academic_violation)
        self.assertEqual(outcome.channel, "whatsapp")
        self.assertEqual(outcome.funnel, "b2b")
        self.assertEqual(outcome.intent, "b2b_inquiry")
        self.assertEqual(outcome.status, "pending_approval")
        self.assertIsNotNone(outcome.approval_id)

        # Verify lead state
        lead = self.lead_repo.get_lead(outcome.lead_id)
        self.assertEqual(lead.status, LeadStatus.QUALIFIED)
        self.assertEqual(lead.priority_bucket, 1)
        self.assertEqual(lead.recommended_service_key, "ai_automation")

        # Verify company
        comp = self.company_repo.get_company(outcome.company_id)
        self.assertIn("Logistics Pro KSA", comp.canonical_name)
        self.assertEqual(comp.country_code, "SA")

        # Verify draft reply interaction (actor=agent_draft)
        interactions = self.interaction_repo.list_interactions(lead_id=lead.lead_id)
        self.assertEqual(len(interactions), 2)  # Inbound + Outbound draft

        outbound_draft = [i for i in interactions if i.direction == InteractionDirection.OUTBOUND][0]
        self.assertEqual(outbound_draft.actor, ActorType.AGENT_DRAFT)
        self.assertEqual(outbound_draft.outcome_tag, "pending_approval")
        self.assertIn("IntelliFY", outbound_draft.content_summary)

        # Verify pending approval request
        approval = self.approval_repo.get_approval(outcome.approval_id)
        self.assertEqual(approval.action_type, "outreach_reply")
        self.assertEqual(approval.decision, ApprovalDecision.PENDING)
        self.assertEqual(approval.target_id, outbound_draft.interaction_id)

    def test_legitimate_academic_mentoring_inquiry(self):
        """Legitimate academic mentoring must be classified as academic without violation."""
        msg = "السلام عليكم، أحتاج جلسات استشارية لتوجيهي في منهجية البحث وتطبيق التحليل الإحصائي لرسالة الماجستير"
        outcome = self.service.ingest_message(
            channel="email",
            external_party_ref="student@kau.edu.sa",
            message_text=msg,
            sender_name="Mona",
            country_code="SA",
        )

        self.assertTrue(outcome.success)
        self.assertFalse(outcome.is_academic_violation)
        self.assertEqual(outcome.funnel, "academic")
        self.assertEqual(outcome.intent, "academic_mentoring")
        self.assertEqual(outcome.status, "pending_approval")
        self.assertIn("التوجيه الأكاديمي والاستشارات المنهجية", outcome.suggested_reply)

        lead = self.lead_repo.get_lead(outcome.lead_id)
        self.assertEqual(lead.funnel, FunnelType.ACADEMIC)
        self.assertEqual(lead.status, LeadStatus.QUALIFIED)
        self.assertEqual(lead.recommended_service_key, "academic_mentoring")

    def test_multi_touch_conversation_deduplication(self):
        """Repeated messages from same contact attach to existing company and lead."""
        contact = "+966599887766"
        cname = "Alpha Tech"

        res1 = self.service.ingest_message(
            channel="whatsapp",
            external_party_ref=contact,
            message_text="رسالة أولى: هل تقدمون خدمات تطوير البرمجيات؟",
            company_name=cname,
        )
        self.assertTrue(res1.success)

        res2 = self.service.ingest_message(
            channel="whatsapp",
            external_party_ref=contact,
            message_text="رسالة ثانية: نود الاستفسار عن التكلفة التقديرية للأتمتة",
            company_name=cname,
        )
        self.assertTrue(res2.success)

        # Both outcomes must point to the SAME company and lead
        self.assertEqual(res1.company_id, res2.company_id)
        self.assertEqual(res1.lead_id, res2.lead_id)

        # Database must have 4 interactions (2 inbound, 2 draft outbound)
        interactions = self.interaction_repo.list_interactions(lead_id=res1.lead_id)
        self.assertEqual(len(interactions), 4)


if __name__ == "__main__":
    unittest.main()
