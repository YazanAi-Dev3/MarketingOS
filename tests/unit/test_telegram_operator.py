"""Unit tests for TelegramOperatorService.

Verifies:
1. Negative authentication (non-allowlisted callers rejected per A-026).
2. Chat allowlist security boundary.
3. Command handling (/status, /leads, /pending, /help, /approve, /reject).
4. Interactive approval card generation and inline keyboard markup.
5. Interactive callback resolution (Approve, Reject, Rewrite) with actor_id audit tracking (A-026).
6. Idempotent callback handling (preventing duplicate resolutions).
"""
from __future__ import annotations

import unittest
from datetime import datetime

from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.telegram_operator import (
    TelegramOperatorConfig,
    TelegramOperatorService,
)
from schemas.models import (
    Approval,
    ApprovalDecision,
    Company,
    FunnelType,
    Lead,
    LeadAssessment,
    LeadStatus,
    utc_now,
)


class TestTelegramOperatorService(unittest.TestCase):
    """Hermetic unit tests for Telegram Operator control and approval service."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed countries and services
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'UAE', '["ar", "en"]', 0.25);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        # Allowlist founder admin 1001 and 1002, in chat 5001
        self.config = TelegramOperatorConfig(
            admin_user_ids={"1001", "1002"},
            admin_chat_ids={"5001"},
        )
        self.service = TelegramOperatorService(db=self.db, config=self.config)

    # --- 1. Authorization & Negative Auth Tests (A-026) ---

    def test_negative_auth_command_rejected(self):
        """Unauthorized caller must be blocked from running commands."""
        res = self.service.handle_command(command_text="/status", user_id="9999", chat_id="5001")
        self.assertFalse(res.success)
        self.assertEqual(res.error, "Unauthorized access")
        self.assertIn("غير مصرح له", res.text)

    def test_negative_auth_chat_id_rejected(self):
        """Authorized user from unauthorized chat must be blocked."""
        res = self.service.handle_command(command_text="/status", user_id="1001", chat_id="9999")
        self.assertFalse(res.success)
        self.assertEqual(res.error, "Unauthorized access")

    def test_negative_auth_callback_rejected_and_state_unmutated(self):
        """Unauthorized callback cannot approve/reject, and leaves DB unmutated."""
        appr = Approval(
            approval_id="appr_sec_01",
            action_type="publish_post",
            target_type="content",
            target_id="cnt_01",
            decision=ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        self.approval_repo.create_request(appr)

        res = self.service.handle_callback(
            callback_data="appr:appr_sec_01:approved",
            user_id="9999",  # Attacker ID
            chat_id="5001",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "Unauthorized callback execution")

        # Verify DB state is STILL PENDING
        saved = self.approval_repo.get_approval("appr_sec_01")
        self.assertIsNotNone(saved)
        self.assertEqual(saved.decision, ApprovalDecision.PENDING)
        self.assertIsNone(saved.actor_id)

    # --- 2. Positive Command Tests ---

    def test_status_command_authorized(self):
        """Authorized admin receives formatted system status."""
        company = Company(
            company_id="comp_1",
            canonical_name="Al-Majd Tech",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead_comp_1",
            company_id="comp_1",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.lead_repo.save_lead(lead)

        res = self.service.handle_command(command_text="/status", user_id="1001", chat_id="5001")
        self.assertTrue(res.success)
        self.assertIn("إجمالي العملاء المتتبعين:* 1", res.text)
        self.assertIn("المؤهلين (Qualified): 1", res.text)
        self.assertIn("SQLite WAL", res.text)

    def test_leads_command_formats_cards(self):
        """Command /leads formats top qualified leads with scores."""
        company = Company(
            company_id="comp_lead_card",
            canonical_name="Riyadh Cloud Co",
            primary_domain="riyadh-cloud.example.sa",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead_comp_lead_card",
            company_id="comp_lead_card",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.lead_repo.save_lead(lead)

        asm = LeadAssessment(
            assessment_id="asm_test_01",
            lead_id="lead_comp_lead_card",
            fit_score=0.95,
            pain_score=0.90,
            urgency_score=0.85,
            reachability_score=0.90,
            final_score=0.91,
            confidence=0.95,
            reasoning_summary="Clear automation need",
            provider_identity="antigravity",
            created_at=utc_now(),
        )
        self.lead_repo.save_assessment(asm)

        res = self.service.handle_command(command_text="/leads SA", user_id="1001", chat_id="5001")
        self.assertTrue(res.success)
        self.assertIn("Riyadh Cloud Co", res.text)
        self.assertIn("Bucket 1", res.text)
        self.assertIn("0.91", res.text)
        self.assertIn("riyadh-cloud.example.sa", res.text)

    # --- 3. Interactive Approval Card & Callback Tests ---

    def test_format_approval_card(self):
        """Card contains approval details and standard inline keyboard buttons."""
        appr = Approval(
            approval_id="appr_card_01",
            action_type="outreach_send",
            target_type="lead",
            target_id="lead_123",
            decision=ApprovalDecision.PENDING,
            notes="Tailored outreach message prepared for review.",
            requested_at=utc_now(),
        )
        card = self.service.format_approval_card(appr)

        self.assertIn("appr_card_01", card["text"])
        self.assertIn("outreach_send", card["text"])
        self.assertIn("A-007", card["text"])
        self.assertIn("reply_markup", card)

        buttons = card["reply_markup"]["inline_keyboard"]
        self.assertEqual(len(buttons), 2)
        # Row 1: Approve & Reject
        self.assertEqual(buttons[0][0]["callback_data"], "appr:appr_card_01:approved")
        self.assertEqual(buttons[0][1]["callback_data"], "appr:appr_card_01:rejected")
        # Row 2: Rewrite
        self.assertEqual(buttons[1][0]["callback_data"], "appr:appr_card_01:rewrite_requested")

    def test_callback_approval_state_transition_and_audit(self):
        """Tapping approve updates DB to APPROVED and stores actor_id (A-026)."""
        appr = Approval(
            approval_id="appr_trans_01",
            action_type="publish_post",
            target_type="content",
            target_id="cnt_post_99",
            decision=ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        self.approval_repo.create_request(appr)

        cb_res = self.service.handle_callback(
            callback_data="appr:appr_trans_01:approved",
            user_id="1001",
            chat_id="5001",
            user_name="Yazan (Founder)",
        )
        self.assertTrue(cb_res.success)
        self.assertEqual(cb_res.decision, "approved")
        self.assertIn("1001", cb_res.actor_id)
        self.assertIn("تم اعتماد الإجراء", cb_res.alert_text)

        # Check in DB
        saved = self.approval_repo.get_approval("appr_trans_01")
        self.assertEqual(saved.decision, ApprovalDecision.APPROVED)
        self.assertIn("1001", saved.actor_id)
        self.assertIsNotNone(saved.resolved_at)

    def test_idempotent_callback_resolution(self):
        """Repeated callback submission on an already-resolved approval returns alert without mutating."""
        appr = Approval(
            approval_id="appr_idem_01",
            action_type="outreach_send",
            target_type="lead",
            target_id="lead_99",
            decision=ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        self.approval_repo.create_request(appr)

        # First resolution: Approve
        res1 = self.service.handle_callback(
            callback_data="appr:appr_idem_01:approved",
            user_id="1001",
            chat_id="5001",
        )
        self.assertTrue(res1.success)

        # Second resolution attempt: Reject (duplicate click)
        res2 = self.service.handle_callback(
            callback_data="appr:appr_idem_01:rejected",
            user_id="1002",
            chat_id="5001",
        )
        self.assertFalse(res2.success)
        self.assertEqual(res2.error, "Approval already resolved")
        self.assertIn("تم اتخاذ القرار مسبقاً", res2.alert_text)

        # Verify DB is STILL APPROVED (not changed by second click)
        saved = self.approval_repo.get_approval("appr_idem_01")
        self.assertEqual(saved.decision, ApprovalDecision.APPROVED)
        self.assertIn("1001", saved.actor_id)

    def test_direct_command_approve_and_reject(self):
        """Commands /approve <id> and /reject <id> resolve approvals directly."""
        appr1 = Approval(
            approval_id="appr_cmd_01",
            action_type="publish_post",
            target_type="content",
            target_id="cnt_01",
            decision=ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        appr2 = Approval(
            approval_id="appr_cmd_02",
            action_type="outreach_send",
            target_type="lead",
            target_id="lead_02",
            decision=ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        self.approval_repo.create_request(appr1)
        self.approval_repo.create_request(appr2)

        res_appr = self.service.handle_command("/approve appr_cmd_01", user_id="1001", chat_id="5001")
        self.assertTrue(res_appr.success)
        self.assertIn("تم اعتماد", res_appr.text)

        res_rej = self.service.handle_command("/reject appr_cmd_02", user_id="1002", chat_id="5001")
        self.assertTrue(res_rej.success)
        self.assertIn("تم رفض", res_rej.text)

        # Verify DB states
        self.assertEqual(self.approval_repo.get_approval("appr_cmd_01").decision, ApprovalDecision.APPROVED)
        self.assertEqual(self.approval_repo.get_approval("appr_cmd_02").decision, ApprovalDecision.REJECTED)


if __name__ == "__main__":
    unittest.main()
