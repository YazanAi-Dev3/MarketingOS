"""Unit tests for Content Engine, Content Repository, and Domain Tool.

Verifies:
- ContentRepository CRUD, querying, and FK constraints
- Grounded idea generation across service profiles (A-028, M-06)
- Platform-tailored copy drafting (LinkedIn, X/Twitter, Instagram, Telegram)
- Strict human approval gating and permission checks (A-007, I-02)
- Secret sanitization and untrusted prompt isolation (A-018, I-05)
- Hermes domain tool `generate_content` integration
"""
import unittest

from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.content_repo import ContentRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.services.content_engine import ContentEngine
from marketing_plugin.tools.domain_tools import generate_content
from schemas.models import (
    ApprovalDecision,
    ContentAsset,
    ContentAssetStatus,
    ContentIdea,
    ContentIdeaObjective,
    Evidence,
    ExtractorType,
    FunnelType,
)


class TestContentEngine(unittest.TestCase):
    """Unit test suite for ContentEngine and ContentRepository."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        # Seed service profiles
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'Enterprise AI Automation'),
                   ('software_systems', 'secondary', '["b2b"]', 'Custom Software Systems'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Academic Mentoring');
        """)
        # Seed a source
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('src_test_01', 'linkedin.com', '["SA"]', 'social', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.content_repo = ContentRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.engine = ContentEngine(
            db=self.db,
            content_repo=self.content_repo,
            approval_repo=self.approval_repo,
            evidence_repo=self.evidence_repo,
        )

    def test_repository_idea_crud_and_filtering(self):
        """Tests ContentRepository idea creation, retrieval, and filtering."""
        idea = ContentIdea(
            content_idea_id="idea_repo_01",
            funnel=FunnelType.B2B,
            market_scope=["SA", "AE"],
            service_key="ai_automation",
            source_signal_ids=["ev_101", "ev_102"],
            topic="Automating Logistics in Riyadh",
            objective=ContentIdeaObjective.DEMAND_CAPTURE,
            score=0.92,
            status="proposed",
        )
        self.content_repo.save_idea(idea)

        fetched = self.content_repo.get_idea("idea_repo_01")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.topic, "Automating Logistics in Riyadh")
        self.assertEqual(fetched.market_scope, ["SA", "AE"])
        self.assertEqual(fetched.source_signal_ids, ["ev_101", "ev_102"])
        self.assertEqual(fetched.objective, ContentIdeaObjective.DEMAND_CAPTURE)

        # Filter by service_key
        ideas_ai = self.content_repo.list_ideas(service_key="ai_automation")
        self.assertEqual(len(ideas_ai), 1)

        ideas_academic = self.content_repo.list_ideas(service_key="academic_mentoring")
        self.assertEqual(len(ideas_academic), 0)

    def test_repository_asset_crud_and_status_update(self):
        """Tests ContentRepository asset creation, listing, and status modification."""
        idea = ContentIdea(
            content_idea_id="idea_repo_02",
            funnel=FunnelType.B2B,
            market_scope=["SA"],
            service_key="ai_automation",
            source_signal_ids=["ev_201"],
            topic="Event-Driven Workflows",
            objective=ContentIdeaObjective.CASE_STYLE,
            score=0.88,
        )
        self.content_repo.save_idea(idea)

        asset = ContentAsset(
            content_asset_id="asset_repo_01",
            idea_id="idea_repo_02",
            master_content="Master narrative for event-driven workflows",
            platform="linkedin",
            format="long_form_post",
            body="Post body for LinkedIn",
            media_brief="Architecture diagram",
            cta="DM for blueprint",
            status=ContentAssetStatus.AWAITING_APPROVAL,
            version=1,
        )
        self.content_repo.save_asset(asset)

        fetched = self.content_repo.get_asset("asset_repo_01")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.platform, "linkedin")
        self.assertEqual(fetched.status, ContentAssetStatus.AWAITING_APPROVAL)

        # Update status
        updated = self.content_repo.update_asset_status("asset_repo_01", ContentAssetStatus.APPROVED)
        self.assertTrue(updated)
        fetched_after = self.content_repo.get_asset("asset_repo_01")
        self.assertEqual(fetched_after.status, ContentAssetStatus.APPROVED)

    def test_generate_ideas_deterministic_grounding(self):
        """Tests grounded idea generation for service profiles."""
        ideas = self.engine.generate_ideas(
            service_key="ai_automation",
            market_scope=["SA"],
            count=3,
            objective=ContentIdeaObjective.DEMAND_CAPTURE,
        )
        self.assertGreaterEqual(len(ideas), 1)
        idea = ideas[0]
        self.assertEqual(idea.service_key, "ai_automation")
        self.assertEqual(idea.market_scope, ["SA"])
        self.assertEqual(idea.objective, ContentIdeaObjective.DEMAND_CAPTURE)
        self.assertTrue(len(idea.source_signal_ids) > 0)

    def test_generate_ideas_with_custom_topic_and_secret_redaction(self):
        """Tests idea generation with a custom topic and verifies secret sanitization (A-018, I-05)."""
        secret_topic = "Automating Logistics with secret token bearer sk-1234567890123456789012 for Riyadh operations"
        ideas = self.engine.generate_ideas(
            service_key="software_systems",
            market_scope=["SA"],
            custom_topic=secret_topic,
        )
        self.assertEqual(len(ideas), 1)
        idea = ideas[0]
        self.assertNotIn("sk-1234567890123456789012", idea.topic)
        self.assertIn("[REDACTED_SECRET]", idea.topic)

    def test_draft_multiplatform_assets_creates_four_platforms(self):
        """Tests multi-platform draft generation across LinkedIn, Twitter, Instagram, Telegram."""
        ideas = self.engine.generate_ideas(
            service_key="ai_automation",
            market_scope=["SA"],
            count=1,
        )
        idea_id = ideas[0].content_idea_id

        assets = self.engine.draft_multiplatform_assets(
            idea_id=idea_id,
            platforms=["linkedin", "twitter", "instagram", "telegram"],
            auto_request_approval=True,
        )

        self.assertEqual(len(assets), 4)
        platforms = {a.platform for a in assets}
        self.assertEqual(platforms, {"linkedin", "twitter", "instagram", "telegram"})

        # Check platform formats
        format_by_platform = {a.platform: a.format for a in assets}
        self.assertEqual(format_by_platform["linkedin"], "long_form_post")
        self.assertEqual(format_by_platform["twitter"], "thread_or_post")
        self.assertEqual(format_by_platform["instagram"], "carousel")
        self.assertEqual(format_by_platform["telegram"], "markdown_announcement")

        # Invariant A-007, I-02: All assets must start in AWAITING_APPROVAL
        for asset in assets:
            self.assertEqual(asset.status, ContentAssetStatus.AWAITING_APPROVAL)
            self.assertIsNotNone(asset.media_brief)
            self.assertIsNotNone(asset.cta)

        # Check approval repository has 4 pending approvals
        pending_approvals = self.approval_repo.list_pending(target_type="content_asset")
        self.assertEqual(len(pending_approvals), 4)

    def test_human_approval_gate_enforcement(self):
        """Tests that unapproved assets cannot be published (Invariants A-007, I-02)."""
        ideas = self.engine.generate_ideas(service_key="ai_automation", count=1)
        assets = self.engine.draft_multiplatform_assets(
            idea_id=ideas[0].content_idea_id,
            platforms=["linkedin"],
            auto_request_approval=True,
        )
        asset = assets[0]

        # Cannot publish initially
        self.assertFalse(self.engine.can_publish_or_schedule(asset.content_asset_id))
        with self.assertRaises(PermissionError):
            self.engine.publish_asset(asset.content_asset_id)

        # Find approval request ID
        pending = self.approval_repo.list_pending(target_type="content_asset")
        target_approval = next(p for p in pending if p.target_id == asset.content_asset_id)

        # Human operator approves the request
        resolved = self.approval_repo.resolve(
            approval_id=target_approval.approval_id,
            decision=ApprovalDecision.APPROVED,
            actor_id="operator_founder",
            notes="Approved for publication after copy review",
        )
        self.assertTrue(resolved)

        # Now can publish
        self.assertTrue(self.engine.can_publish_or_schedule(asset.content_asset_id))
        published = self.engine.publish_asset(asset.content_asset_id)
        self.assertEqual(published.status, ContentAssetStatus.PUBLISHED)

    def test_content_grounding_rubric_verification(self):
        """Tests M-06 content grounding validation against evidence citations."""
        # Create evidence
        evidence = Evidence(
            evidence_id="ev_field_test_99",
            source_id="src_test_01",
            url="https://linkedin.com/post/123",
            fact_type="pain_point",
            fact_text="Customer support latency exceeds 48 hours for GCC ecommerce stores",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash99",
        )
        self.evidence_repo.save_evidence(evidence)

        ideas = self.engine.generate_ideas(
            service_key="ai_automation",
            market_scope=["SA"],
            evidence_ids=["ev_field_test_99"],
            count=1,
        )
        assets = self.engine.draft_multiplatform_assets(
            idea_id=ideas[0].content_idea_id,
            platforms=["linkedin"],
        )

        rubric_res = self.engine.verify_content_grounding(assets[0], ideas[0])
        self.assertTrue(rubric_res["passed"])
        self.assertTrue(rubric_res["dimensions"]["evidence_citation"])
        self.assertTrue(rubric_res["dimensions"]["approval_gated"])
        self.assertTrue(rubric_res["dimensions"]["secrets_isolated"])

    def test_domain_tool_generate_content(self):
        """Tests Hermes domain tool generate_content end-to-end execution."""
        res = generate_content(
            service_key="ai_automation",
            country_code="SA",
            platforms=["linkedin", "twitter"],
            objective="demand_capture",
            db=self.db,
        )

        self.assertEqual(res["status"], "success")
        self.assertIn("primary_idea", res)
        self.assertEqual(res["assets_count"], 2)
        self.assertTrue(res["approval_required"])
        self.assertIn("awaiting_approval", res["policy_notice"])


if __name__ == "__main__":
    unittest.main()
