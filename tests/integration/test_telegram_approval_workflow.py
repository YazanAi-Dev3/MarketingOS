"""Integration tests for Telegram Operator and Approval Workflow.

Verifies end-to-end integration:
1. Market lead qualification via LeadScorer
2. Generation of human approval request (request_approval / A-007)
3. Telegram operator notification card and inline keyboard rendering
4. Negative authorization enforcement (unauthorized attacker blocked / A-026)
5. Interactive callback execution by authorized founder
6. Audit trail persistence (actor_id, resolved_at) and idempotency
7. Operational status reflection in Telegram digest
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from marketing_plugin import request_approval
from marketing_plugin.adapters.antigravity_adapter import AntigravityAdapter, ReasoningResult
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.lead_scorer import LeadScorer
from marketing_plugin.services.telegram_operator import (
    TelegramOperatorConfig,
    TelegramOperatorService,
)
from schemas.models import (
    ApprovalDecision,
    Company,
    Evidence,
    ExtractorType,
    FunnelType,
    LeadStatus,
    utc_now,
)


class TestTelegramApprovalWorkflow(unittest.TestCase):
    """Integration test suite for the complete operator approval lifecycle."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country and service profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('company_website', 'company.com', '["ALL"]', 'website', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        self.operator_service = TelegramOperatorService(
            db=self.db,
            config=TelegramOperatorConfig(
                admin_user_ids={"1001", "1002"},
                admin_chat_ids={"5001"},
            ),
        )

    def test_complete_lead_qualification_to_telegram_approval_lifecycle(self):
        """Full lifecycle: Lead -> Scored -> Approval Requested -> Telegram Card -> Callback -> DB Verified."""
        # Step 1: Create company and evidence
        company = Company(
            company_id="comp_workflow_01",
            canonical_name="Dar Al-Riyadh Automation",
            primary_domain="dar-riyadh.example.sa",
            country_code="SA",
            funnel=FunnelType.B2B,
            public_contacts_json={"email": "contact@dar-riyadh.example.sa"},
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_wf_01",
            company_id="comp_workflow_01",
            source_id="company_website",
            url="https://dar-riyadh.example.sa",
            fact_type="operational_pain",
            fact_text="Seeking AI partner to automate enterprise invoice reconciliation and CRM intake.",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_wf_01",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        # Step 2: Score company with LeadScorer using mock AI adapter
        mock_adapter = MagicMock(spec=AntigravityAdapter)
        mock_adapter.reason.return_value = ReasoningResult(
            success=True,
            structured_data={
                "fit_score": 0.95,
                "pain_score": 0.90,
                "urgency_score": 0.85,
                "reachability_score": 0.95,
                "decision": "qualified",
                "academic_integrity_passed": True,
                "recommended_service_key": "ai_automation",
                "reasoning_summary": "Enterprise client with immediate financial invoice automation pain.",
                "confidence": 0.95,
            },
        )
        scorer = LeadScorer(db=self.db, adapter=mock_adapter, enable_model=True)
        score_res = scorer.score_company("comp_workflow_01")

        self.assertTrue(score_res.success)
        self.assertEqual(score_res.status, LeadStatus.QUALIFIED)
        self.assertEqual(score_res.priority_bucket, 1)

        # Step 3: Request human approval for outreach (Invariant A-007)
        appr_data = request_approval(
            action_type="outreach_send",
            target_type="lead",
            target_id=score_res.lead_id,
            notes="Personalized cold proposal draft for invoice reconciliation automation.",
            db=self.db,
        )
        approval_id = appr_data["approval_id"]
        self.assertEqual(appr_data["decision"], "pending")

        # Step 4: Render Telegram Approval Card
        appr_obj = self.approval_repo.get_approval(approval_id)
        card = self.operator_service.format_approval_card(appr_obj)
        self.assertIn(approval_id, card["text"])
        self.assertIn("outreach_send", card["text"])
        self.assertIn("A-007", card["text"])

        # Step 5: Unauthorized attacker attempts to approve -> Blocked (A-026)
        bad_cb = self.operator_service.handle_callback(
            callback_data=f"appr:{approval_id}:approved",
            user_id="6666",  # Unauthorized attacker
            chat_id="5001",
        )
        self.assertFalse(bad_cb.success)
        self.assertEqual(bad_cb.error, "Unauthorized callback execution")

        # Verify DB still PENDING
        self.assertEqual(self.approval_repo.get_approval(approval_id).decision, ApprovalDecision.PENDING)

        # Step 6: Authorized founder approves via Telegram inline button
        good_cb = self.operator_service.handle_callback(
            callback_data=f"appr:{approval_id}:approved",
            user_id="1001",  # Authorized founder
            chat_id="5001",
            user_name="Yazan",
        )
        self.assertTrue(good_cb.success)
        self.assertEqual(good_cb.decision, "approved")
        self.assertIn("1001", good_cb.actor_id)
        self.assertIn("تم اعتماد الإجراء بنجاح", good_cb.alert_text)

        # Step 7: Verify DB state mutated and audit logged (A-026, I-02)
        final_appr = self.approval_repo.get_approval(approval_id)
        self.assertEqual(final_appr.decision, ApprovalDecision.APPROVED)
        self.assertIn("1001", final_appr.actor_id)
        self.assertIsNotNone(final_appr.resolved_at)

        # Step 8: Idempotency check: Repeated click returns notice without mutating
        repeat_cb = self.operator_service.handle_callback(
            callback_data=f"appr:{approval_id}:rejected",  # Tries to flip decision
            user_id="1002",
            chat_id="5001",
        )
        self.assertFalse(repeat_cb.success)
        self.assertEqual(repeat_cb.error, "Approval already resolved")
        self.assertIn("تم اتخاذ القرار مسبقاً", repeat_cb.alert_text)

        # Confirm DB still APPROVED
        self.assertEqual(self.approval_repo.get_approval(approval_id).decision, ApprovalDecision.APPROVED)

        # Step 9: Verify Telegram /status shows 0 pending approvals
        status_res = self.operator_service.handle_command("/status", user_id="1001", chat_id="5001")
        self.assertTrue(status_res.success)
        self.assertIn("طلبات الاعتماد المعلقة:* 0", status_res.text)
        self.assertIn("المؤهلين (Qualified): 1", status_res.text)


if __name__ == "__main__":
    unittest.main()
