"""Integration tests for Conversation Intake Pipeline and Telegram Approval Workflow.

Verifies end-to-end integration:
1. Inbound WhatsApp message -> Entity & Lead Creation -> Inbound & Draft Interactions -> Approval Gate.
2. Telegram Operator inspection and interactive approval callback resolution (A-007, I-02, A-022, A-026).
3. Academic Integrity violation end-to-end isolation (A-008).
4. Multi-channel ingestion across WhatsApp, Telegram, Email, and Web.
"""
from __future__ import annotations

import json
import unittest

from marketing_plugin import ingest_interaction, list_interactions
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.telegram_operator import (
    TelegramOperatorConfig,
    TelegramOperatorService,
)
from schemas.models import (
    ActorType,
    ApprovalDecision,
    FunnelType,
    InteractionDirection,
    LeadStatus,
)


class TestConversationIntakePipeline(unittest.TestCase):
    """Hermetic end-to-end integration tests for conversation intake and founder approval workflow."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed countries and service profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'UAE', '["ar", "en"]', 0.25),
                   ('EG', 'Egypt', '["ar"]', 0.15);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation Systems'),
                   ('software_systems', 'primary', '["b2b"]', 'Custom Software Development'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Legitimate Academic Mentoring');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.interaction_repo = InteractionRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        self.config = TelegramOperatorConfig(
            admin_user_ids={"777001"},
            admin_chat_ids={"999001"},
        )
        self.operator = TelegramOperatorService(db=self.db, config=self.config)

    def test_e2e_whatsapp_inbound_to_telegram_approval(self):
        """Full pipeline: Inbound WhatsApp -> Qualified Lead -> Approval Queue -> Telegram Founder Approval."""
        # 1. Inbound WhatsApp message arrives
        raw_msg = (
            "السلام عليكم، نحن شركة اليمامة للتجارة في الرياض. "
            "نرغب في أتمتة نظام معالجة الطلبات وإصدار الفواتير وربطه بـ CRM."
        )
        ingest_res = ingest_interaction(
            channel="whatsapp",
            sender_ref="+966509988776",
            message=raw_msg,
            company_name="Alyamama Trading",
            country_code="SA",
            auto_request_approval=True,
            db=self.db,
        )

        self.assertEqual(ingest_res["status"], "success")
        self.assertEqual(ingest_res["channel"], "whatsapp")
        self.assertEqual(ingest_res["funnel"], "b2b")
        self.assertEqual(ingest_res["intent"], "b2b_inquiry")
        self.assertFalse(ingest_res["is_academic_violation"])

        lead_id = ingest_res["lead_id"]
        approval_id = ingest_res["approval_id"]
        self.assertIsNotNone(lead_id)
        self.assertIsNotNone(approval_id)

        # 2. Verify database records
        lead = self.lead_repo.get_lead(lead_id)
        self.assertEqual(lead.status, LeadStatus.QUALIFIED)
        self.assertEqual(lead.priority_bucket, 1)

        interactions = list_interactions(lead_id=lead_id, db=self.db)
        self.assertEqual(len(interactions), 2)

        # Inbound interaction
        inbound = next(i for i in interactions if i["direction"] == "inbound")
        self.assertEqual(inbound["actor"], "external")
        self.assertEqual(inbound["channel"], "whatsapp")

        # Draft outbound interaction (actor=agent_draft per A-022)
        draft = next(i for i in interactions if i["direction"] == "outbound")
        self.assertEqual(draft["actor"], "agent_draft")
        self.assertEqual(draft["outcome_tag"], "pending_approval")

        # 3. Founder inspects approval request via Telegram /pending
        pending_res = self.operator.handle_command("/pending", user_id="777001", chat_id="999001")
        self.assertTrue(pending_res.success)
        self.assertIn(approval_id, pending_res.text)
        self.assertIsNotNone(pending_res.reply_markup)

        # 4. Founder clicks "Approve" button
        callback_data = f"appr:{approval_id}:approved"
        cb_res = self.operator.handle_callback(
            callback_data=callback_data,
            user_id="777001",
            chat_id="999001",
            user_name="Founder Khaled",
        )

        self.assertTrue(cb_res.success)
        self.assertEqual(cb_res.decision, "approved")
        self.assertIn("Founder Khaled", cb_res.actor_id)

        # 5. Verify database approval status
        updated_appr = self.approval_repo.get_approval(approval_id)
        self.assertEqual(updated_appr.decision, ApprovalDecision.APPROVED)
        self.assertIn("Founder Khaled", updated_appr.actor_id)

    def test_e2e_academic_violation_rejection(self):
        """Full pipeline: Cheating inquiry -> Instant Rejection -> Zero Approval Queue (A-008)."""
        cheating_msg = "أريد حل واجبات وكتابة أطروحة كاملة نيابة عني بدون علم الجامعة بمقابل مالي"
        ingest_res = ingest_interaction(
            channel="whatsapp",
            sender_ref="+966555443322",
            message=cheating_msg,
            country_code="SA",
            db=self.db,
        )

        self.assertEqual(ingest_res["status"], "success")
        self.assertTrue(ingest_res["is_academic_violation"])
        self.assertEqual(ingest_res["intake_status"], "rejected_academic_violation")
        self.assertIsNone(ingest_res["approval_id"])

        # Lead in DB must be REJECTED
        lead = self.lead_repo.get_lead(ingest_res["lead_id"])
        self.assertEqual(lead.status, LeadStatus.REJECTED)
        self.assertEqual(lead.next_action, "rejected_academic_violation")

        # No approvals pending
        pending = self.approval_repo.list_pending()
        self.assertEqual(len(pending), 0)

    def test_multi_channel_ingestion_and_filtering(self):
        """Verifies ingestion and querying across Email, Web, WhatsApp, and Telegram."""
        channels = [
            ("whatsapp", "+966501112233", "نحتاج حلول أتمتة للأعمال"),
            ("telegram", "@tech_director", "نود استشارة حول ربط الأنظمة"),
            ("email", "info@enterprise.sa", "طلب عرض أسعار لأنظمة الذكاء الاصطناعي"),
            ("web", "visitor_web_uuid_99", "استفسار بخصوص خدمات البرمجة المخصصة"),
        ]

        lead_ids = []
        for ch, sender, text in channels:
            res = ingest_interaction(
                channel=ch,
                sender_ref=sender,
                message=text,
                country_code="SA",
                db=self.db,
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["channel"], ch)
            lead_ids.append(res["lead_id"])

        # Check channel filtering in list_interactions
        wa_interactions = list_interactions(channel="whatsapp", db=self.db)
        self.assertGreaterEqual(len(wa_interactions), 1)
        self.assertTrue(all(i["channel"] == "whatsapp" for i in wa_interactions))

        email_interactions = list_interactions(channel="email", db=self.db)
        self.assertGreaterEqual(len(email_interactions), 1)
        self.assertTrue(all(i["channel"] == "email" for i in email_interactions))

        web_interactions = list_interactions(channel="web", db=self.db)
        self.assertGreaterEqual(len(web_interactions), 1)
        self.assertTrue(all(i["channel"] == "web" for i in web_interactions))


if __name__ == "__main__":
    unittest.main()
