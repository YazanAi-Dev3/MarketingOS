"""Integration tests for Outbound Outreach Pipeline in Marketing OS.

Tests the full closed-loop workflow:
1. Qualified lead with evidence in SQLite.
2. generate_outreach domain tool synthesizes 3-touch cadence.
3. Draft interactions saved with actor='agent_draft' (A-022).
4. Pending approval registered in ApprovalRepository (A-007, I-02).
5. Lead transitions from QUALIFIED -> OUTREACH_READY (M-01).
6. TelegramOperatorService renders interactive approval card.
7. Human founder approves via callback.
8. Lead transitions to CONTACTED with next_action='awaiting_lead_reply' (M-12).
"""
from __future__ import annotations

import unittest

from marketing_plugin import generate_outreach, record_contact_attempt
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.telegram_operator import (
    TelegramOperatorConfig,
    TelegramOperatorService,
)
from schemas.models import (
    ActorType,
    ApprovalDecision,
    Company,
    Evidence,
    ExtractorType,
    FunnelType,
    InteractionDirection,
    Lead,
    LeadAssessment,
    LeadStatus,
    OutreachStepType,
)


class TestOutboundPipelineIntegration(unittest.TestCase):
    """End-to-end integration test of the outbound outreach cadence and approval pipeline."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed reference data
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Academic Mentoring');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('mostaql', 'mostaql.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public'),
                   ('khamsat', 'khamsat.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.interaction_repo = InteractionRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        # Setup Telegram Operator
        self.tg_config = TelegramOperatorConfig(
            admin_user_ids={"founder_1001"},
            admin_chat_ids={"chat_5001"},
        )
        self.tg_service = TelegramOperatorService(db=self.db, config=self.tg_config)

    def test_e2e_b2b_outreach_flow_to_contacted(self):
        """Tests complete B2B outreach cadence lifecycle through Telegram approval gate."""
        # 1. Company & Qualified Lead Ingestion
        company = Company(
            company_id="comp_e2e_01",
            canonical_name="شركة النخبة للحلول اللوجستية",
            primary_domain="elitelogistics.sa",
            country_code="SA",
            city="الدمام",
            sector="النقل واللوجستيات",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead_e2e_01",
            company_id="comp_e2e_01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
        )
        self.lead_repo.save_lead(lead)

        evidence = Evidence(
            evidence_id="ev_e2e_01",
            company_id="comp_e2e_01",
            source_id="mostaql",
            url="https://mostaql.com/p/999",
            fact_type="rfp",
            fact_text="مشروع لتطوير خوارزمية ذكية لجدولة شاحنات التوزيع وتتبع الفواتير",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_e2e_01",
            confidence=0.98,
        )
        self.evidence_repo.save_evidence(evidence)

        # 2. Invoke generate_outreach domain tool
        outreach_res = generate_outreach(
            lead_id="lead_e2e_01",
            channel="email",
            auto_request_approval=True,
            db=self.db,
        )

        self.assertEqual(outreach_res["status"], "success")
        self.assertEqual(outreach_res["message_count"], 3)
        self.assertIsNotNone(outreach_res["approval_id"])

        # Check lead moved to OUTREACH_READY
        lead_ready = self.lead_repo.get_lead("lead_e2e_01")
        self.assertEqual(lead_ready.status, LeadStatus.OUTREACH_READY)
        self.assertEqual(lead_ready.next_action, "awaiting_approval")

        # Check interactions recorded with agent_draft
        drafts = self.interaction_repo.list_interactions(lead_id="lead_e2e_01", actor=ActorType.AGENT_DRAFT)
        self.assertEqual(len(drafts), 3)

        # 3. Founder inspects via Telegram operator command
        cmd_res = self.tg_service.handle_command(
            "/outreach lead_e2e_01 email",
            user_id="founder_1001",
            chat_id="chat_5001",
        )
        self.assertTrue(cmd_res.success)
        self.assertIn("شركة النخبة للحلول اللوجستية", cmd_res.text)
        self.assertIn("EMAIL", cmd_res.text)
        self.assertIsNotNone(cmd_res.reply_markup)

        # 4. Founder clicks [Approve]
        approval_id = outreach_res["approval_id"]
        cb_res = self.tg_service.handle_callback(
            f"appr:{approval_id}:approved",
            user_id="founder_1001",
            chat_id="chat_5001",
        )
        self.assertTrue(cb_res.success)
        self.assertEqual(cb_res.decision, "approved")

        # 5. Check Approval is resolved
        approval = self.approval_repo.get_approval(approval_id)
        self.assertEqual(approval.decision, ApprovalDecision.APPROVED)
        self.assertIsNotNone(approval.resolved_at)

        # 6. Check Lead progressed to CONTACTED (M-01, M-12)
        lead_contacted = self.lead_repo.get_lead("lead_e2e_01")
        self.assertEqual(lead_contacted.status, LeadStatus.CONTACTED)
        self.assertEqual(lead_contacted.next_action, "awaiting_lead_reply")

    def test_e2e_whatsapp_manual_dispatch_flow(self):
        """Tests manual dispatch via WhatsApp and recording contact attempt."""
        company = Company(
            company_id="comp_wa_01",
            canonical_name="مؤسسة الابتكار الرقمي",
            primary_domain="innovate.sa",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead_wa_01",
            company_id="comp_wa_01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
        )
        self.lead_repo.save_lead(lead)

        # Generate WhatsApp cadence
        plan = generate_outreach(
            lead_id="lead_wa_01",
            channel="whatsapp",
            auto_request_approval=True,
            db=self.db,
        )
        self.assertEqual(plan["status"], "success")

        # Founder sends message manually via WhatsApp, then logs contact attempt
        contact_res = record_contact_attempt(
            lead_id="lead_wa_01",
            channel="whatsapp",
            actor_id="founder_yazan",
            notes="Sent step 1 hook to business owner via WhatsApp",
            db=self.db,
        )
        self.assertEqual(contact_res["status"], "success")
        self.assertTrue(contact_res["updated"])

        # Check lead is CONTACTED
        lead_updated = self.lead_repo.get_lead("lead_wa_01")
        self.assertEqual(lead_updated.status, LeadStatus.CONTACTED)
        self.assertEqual(lead_updated.next_action, "awaiting_lead_reply")


if __name__ == "__main__":
    unittest.main()
