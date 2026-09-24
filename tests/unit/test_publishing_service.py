"""Unit tests for PublishingService.

Verifies:
- Invariant A-007, I-02: PermissionError on unapproved asset dispatch
- Direct Telegram dispatch
- Postiz automated dispatch when healthy
- Graceful manual export fallback when Postiz is offline (R-04)
- Scheduling datetime preservation and failure handling
"""
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

from marketing_plugin.adapters.postiz_adapter import PostizAdapter, PostizPostResponse
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.content_repo import ContentRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.services.publishing_service import PublishingService
from schemas.models import (
    Approval,
    ApprovalDecision,
    ContentAsset,
    ContentAssetStatus,
    ContentIdea,
    ContentIdeaObjective,
    FunnelType,
    utc_now,
)


class TestPublishingService(unittest.TestCase):
    """Unit test suite for PublishingService."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country & service profile
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Automation');
        """)
        self.conn.commit()

        self.content_repo = ContentRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        # Seed base idea
        self.idea = ContentIdea(
            content_idea_id="idea_pub_01",
            funnel=FunnelType.B2B,
            market_scope=["SA"],
            service_key="ai_automation",
            source_signal_ids=["sig_01"],
            topic="Logistics Automation in Riyadh",
            objective=ContentIdeaObjective.DEMAND_CAPTURE,
        )
        self.content_repo.save_idea(self.idea)

    def _create_asset_and_approval(self, platform: str, approved: bool = False) -> str:
        asset_id = f"asset_{platform}_01"
        asset = ContentAsset(
            content_asset_id=asset_id,
            idea_id="idea_pub_01",
            master_content="Master content for automation",
            platform=platform,
            format="long_form_post" if platform == "linkedin" else "post",
            body=f"Formatted body for {platform}",
            media_brief="Architecture diagram",
            cta="DM for blueprint",
            status=ContentAssetStatus.AWAITING_APPROVAL,
            version=1,
        )
        self.content_repo.save_asset(asset)

        approval_id = f"appr_{platform}_01"
        approval = Approval(
            approval_id=approval_id,
            action_type="publish_content",
            target_type="content_asset",
            target_id=asset_id,
            decision=ApprovalDecision.APPROVED if approved else ApprovalDecision.PENDING,
            requested_at=utc_now(),
        )
        self.approval_repo.create_request(approval)
        return asset_id

    def test_unapproved_asset_raises_permission_error(self):
        """Verifies Invariants A-007, I-02: dispatch without approval raises PermissionError."""
        asset_id = self._create_asset_and_approval("linkedin", approved=False)
        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
        )

        self.assertFalse(service.is_asset_approved(asset_id))
        with self.assertRaises(PermissionError):
            service.dispatch_asset(asset_id)

    def test_approved_asset_dispatches_telegram_direct(self):
        """Verifies Telegram posts dispatch directly."""
        asset_id = self._create_asset_and_approval("telegram", approved=True)
        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
        )

        res = service.dispatch_asset(asset_id)
        self.assertTrue(res.success)
        self.assertEqual(res.platform, "telegram")
        self.assertEqual(res.dispatch_mode, "telegram_direct")
        self.assertEqual(res.status, "published")

        # Verify DB updated
        asset_in_db = self.content_repo.get_asset(asset_id)
        self.assertEqual(asset_in_db.status, ContentAssetStatus.PUBLISHED)

    def test_approved_asset_dispatches_postiz_when_healthy(self):
        """Verifies social dispatch to Postiz when adapter is healthy."""
        asset_id = self._create_asset_and_approval("linkedin", approved=True)

        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = True
        mock_postiz.create_post.return_value = PostizPostResponse(
            success=True,
            post_id="postiz_remote_123",
            scheduled_at=None,
            providers=["linkedin"],
        )

        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
            postiz_adapter=mock_postiz,
        )

        res = service.dispatch_asset(asset_id)
        self.assertTrue(res.success)
        self.assertEqual(res.dispatch_mode, "postiz")
        self.assertEqual(res.remote_id, "postiz_remote_123")
        self.assertEqual(res.status, "published")

        mock_postiz.create_post.assert_called_once()
        asset_in_db = self.content_repo.get_asset(asset_id)
        self.assertEqual(asset_in_db.status, ContentAssetStatus.PUBLISHED)

    def test_approved_asset_falls_back_to_manual_export_when_postiz_offline(self):
        """Verifies decision R-04: graceful manual export fallback when Postiz is offline."""
        asset_id = self._create_asset_and_approval("instagram", approved=True)

        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = False  # Postiz is offline

        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
            postiz_adapter=mock_postiz,
        )

        res = service.dispatch_asset(asset_id)
        self.assertTrue(res.success)
        self.assertEqual(res.dispatch_mode, "manual_export")
        self.assertIsNotNone(res.manual_export_package)
        self.assertIn("INSTAGRAM", res.manual_export_package["platform"])
        self.assertIn("Architecture diagram", res.manual_export_package["media_brief"])
        self.assertIn("Copy the body text", res.manual_export_package["instructions"])

    def test_scheduling_preservation(self):
        """Verifies scheduled_at is preserved in dispatch result."""
        asset_id = self._create_asset_and_approval("twitter", approved=True)
        target_time = datetime(2026, 10, 5, 14, 30, tzinfo=timezone.utc)

        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = True
        mock_postiz.create_post.return_value = PostizPostResponse(
            success=True,
            post_id="postiz_scheduled_99",
            scheduled_at=target_time.isoformat(),
            providers=["twitter"],
        )

        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
            postiz_adapter=mock_postiz,
        )

        res = service.dispatch_asset(asset_id, scheduled_at=target_time)
        self.assertTrue(res.success)
        self.assertEqual(res.status, "scheduled")
        self.assertEqual(res.scheduled_at, target_time.isoformat())

        asset_in_db = self.content_repo.get_asset(asset_id)
        self.assertEqual(asset_in_db.status, ContentAssetStatus.SCHEDULED)

    def test_postiz_failure_marks_asset_as_failed(self):
        """Verifies that an API failure from Postiz transitions asset status to FAILED."""
        asset_id = self._create_asset_and_approval("linkedin", approved=True)

        mock_postiz = MagicMock(spec=PostizAdapter)
        mock_postiz.check_health.return_value = True
        mock_postiz.create_post.return_value = PostizPostResponse(
            success=False,
            error_message="API Token Expired",
        )

        service = PublishingService(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
            postiz_adapter=mock_postiz,
        )

        res = service.dispatch_asset(asset_id)
        self.assertFalse(res.success)
        self.assertEqual(res.status, "failed")
        self.assertIn("API Token Expired", res.error)

        asset_in_db = self.content_repo.get_asset(asset_id)
        self.assertEqual(asset_in_db.status, ContentAssetStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
