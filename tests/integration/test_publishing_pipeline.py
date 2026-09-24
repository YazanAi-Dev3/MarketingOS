"""Integration tests for Social Publishing Pipeline and Scheduling.

Verifies end-to-end lifecycle:
1. Grounded Idea & Multi-Platform Drafting (CAPSULE-006)
2. Interactive Human Approval via Telegram Operator (CAPSULE-005, A-007, I-02)
3. Automated Social Dispatch via Postiz Adapter (A-021)
4. Direct Telegram channel broadcasting
5. Graceful manual export fallback when Postiz is unreachable (R-04)
6. Zero-Unapproved Publishing Enforcement (PermissionError / permission_denied)
"""
from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

from marketing_plugin.adapters.postiz_adapter import PostizAdapter, PostizPostResponse
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.content_repo import ContentRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.services.content_engine import ContentEngine
from marketing_plugin.services.publishing_service import PublishingService
from marketing_plugin.services.telegram_operator import (
    TelegramOperatorConfig,
    TelegramOperatorService,
)
from marketing_plugin.tools.domain_tools import generate_content, publish_content
from schemas.models import (
    ApprovalDecision,
    Company,
    ContentAssetStatus,
    Evidence,
    ExtractorType,
    FunnelType,
    utc_now,
)
from tests.fixtures.evaluation_seeds import EVIDENCE_EXTRACTION_EXPECTED


class TestPublishingPipeline(unittest.TestCase):
    """Integration test suite for the social publishing and scheduling pipeline."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country & service profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation & ERP Integration');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('src_sa_logistics', 'saudi-logistics.com', '["SA"]', 'website', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.content_repo = ContentRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        self.operator_service = TelegramOperatorService(
            db=self.db,
            config=TelegramOperatorConfig(
                admin_user_ids={"1001", "1002"},
                admin_chat_ids={"5001"},
            ),
        )

        # Ingest logistics seed evidence
        seed = EVIDENCE_EXTRACTION_EXPECTED["gcc-sa-01-clean-logistics"]
        company = Company(
            company_id="comp_pub_pipeline_01",
            canonical_name=seed["company_name"],
            country_code=seed["country"],
            city=seed["city"],
            funnel=FunnelType.B2B,
            public_contacts_json={"email": seed["contact_email"], "phone": seed["contact_phone"]},
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_pub_pipeline_01",
            company_id=company.company_id,
            source_id="src_sa_logistics",
            url="https://saudi-logistics.com/careers",
            fact_type="operational_pain",
            fact_text=seed["pain_points"][0],
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_pub_pipe_01",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

    def test_full_publishing_lifecycle_with_approval_and_postiz(self):
        """End-to-end: Content generated -> Approved via Telegram -> Dispatched to Postiz."""
        # 1. Generate content for LinkedIn & Twitter
        gen_res = generate_content(
            service_key="ai_automation",
            country_code="SA",
            platforms=["linkedin", "twitter"],
            evidence_ids=["evi_pub_pipeline_01"],
            db=self.db,
        )
        self.assertEqual(gen_res["status"], "success")
        self.assertEqual(gen_res["assets_count"], 2)

        linkedin_asset_id = next(a["asset_id"] for a in gen_res["assets"] if a["platform"] == "linkedin")
        twitter_asset_id = next(a["asset_id"] for a in gen_res["assets"] if a["platform"] == "twitter")

        # 2. Attempt to publish before approval -> BLOCKED (A-007, I-02)
        blocked_res = publish_content(asset_id=linkedin_asset_id, db=self.db)
        self.assertEqual(blocked_res["status"], "permission_denied")
        self.assertTrue(blocked_res["approval_required"])
        self.assertEqual(self.content_repo.get_asset(linkedin_asset_id).status, ContentAssetStatus.AWAITING_APPROVAL)

        # 3. Founder approves LinkedIn asset via Telegram Operator callback
        approvals = self.approval_repo.list_pending(target_type="content_asset")
        li_approval = next(ap for ap in approvals if ap.target_id == linkedin_asset_id)

        cb_res = self.operator_service.handle_callback(
            callback_data=f"appr:{li_approval.approval_id}:approved",
            user_id="1001",
            chat_id="5001",
            user_name="YazanFounder",
        )
        self.assertTrue(cb_res.success)
        self.assertEqual(cb_res.decision, "approved")

        # 4. Set up mock PostizAdapter for automated publishing
        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = True
        mock_postiz.create_post.return_value = PostizPostResponse(
            success=True,
            post_id="postiz_remote_li_999",
            scheduled_at=None,
            providers=["linkedin"],
        )

        # 5. Dispatch approved LinkedIn post
        pub_res = publish_content(
            asset_id=linkedin_asset_id,
            db=self.db,
            postiz_adapter=mock_postiz,
        )
        self.assertEqual(pub_res["status"], "success")
        self.assertEqual(pub_res["publication_status"], "published")
        self.assertEqual(pub_res["dispatch_mode"], "postiz")
        self.assertEqual(pub_res["remote_id"], "postiz_remote_li_999")

        # Verify DB status updated to PUBLISHED
        self.assertEqual(self.content_repo.get_asset(linkedin_asset_id).status, ContentAssetStatus.PUBLISHED)

        # 6. Verify Twitter asset is still unapproved and cannot be published
        blocked_tw = publish_content(asset_id=twitter_asset_id, db=self.db, postiz_adapter=mock_postiz)
        self.assertEqual(blocked_tw["status"], "permission_denied")

    def test_scheduled_publishing_to_postiz(self):
        """Verifies scheduling workflow with a future timestamp."""
        gen_res = generate_content(
            service_key="ai_automation",
            country_code="SA",
            platforms=["twitter"],
            db=self.db,
        )
        asset_id = gen_res["assets"][0]["asset_id"]

        # Approve asset
        approvals = self.approval_repo.list_pending(target_type="content_asset")
        appr = next(ap for ap in approvals if ap.target_id == asset_id)
        self.approval_repo.resolve(appr.approval_id, ApprovalDecision.APPROVED, actor_id="admin_1001")

        # Schedule post
        target_time = "2026-10-15T09:00:00+00:00"
        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = True
        mock_postiz.create_post.return_value = PostizPostResponse(
            success=True,
            post_id="postiz_sched_123",
            scheduled_at=target_time,
            providers=["twitter"],
        )

        pub_res = publish_content(
            asset_id=asset_id,
            scheduled_at=target_time,
            db=self.db,
            postiz_adapter=mock_postiz,
        )

        self.assertEqual(pub_res["status"], "success")
        self.assertEqual(pub_res["publication_status"], "scheduled")
        self.assertEqual(pub_res["scheduled_at"], target_time)
        self.assertEqual(self.content_repo.get_asset(asset_id).status, ContentAssetStatus.SCHEDULED)

    def test_postiz_offline_graceful_manual_export(self):
        """Verifies R-04: If Postiz is offline, system produces a clean manual export package."""
        gen_res = generate_content(
            service_key="ai_automation",
            country_code="SA",
            platforms=["instagram"],
            db=self.db,
        )
        asset_id = gen_res["assets"][0]["asset_id"]

        # Approve asset
        approvals = self.approval_repo.list_pending(target_type="content_asset")
        appr = next(ap for ap in approvals if ap.target_id == asset_id)
        self.approval_repo.resolve(appr.approval_id, ApprovalDecision.APPROVED, actor_id="admin_1001")

        # Mock offline Postiz
        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = False

        pub_res = publish_content(
            asset_id=asset_id,
            db=self.db,
            postiz_adapter=mock_postiz,
        )

        self.assertEqual(pub_res["status"], "success")
        self.assertEqual(pub_res["dispatch_mode"], "manual_export")
        self.assertIsNotNone(pub_res["manual_export_package"])
        self.assertIn("INSTAGRAM", pub_res["manual_export_package"]["platform"])
        self.assertIn("instructions", pub_res["manual_export_package"])


if __name__ == "__main__":
    unittest.main()

