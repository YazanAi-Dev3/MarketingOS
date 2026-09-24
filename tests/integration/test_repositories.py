"""Integration tests for Marketing OS SQLite Database and Repositories."""
import unittest
from datetime import datetime

from marketing_plugin.repositories.agent_run_repo import AgentRunRepository
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.content_repo import ContentRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository
from schemas.models import (
    AccessMode,
    ActorType,
    AgentRun,
    Approval,
    ApprovalDecision,
    Company,
    ContentAsset,
    ContentAssetStatus,
    ContentIdea,
    ContentIdeaObjective,
    Evidence,
    ExtractorType,
    FunnelType,
    Interaction,
    InteractionDirection,
    Lead,
    LeadAssessment,
    LeadStatus,
    Source,
    SourceStatus,
)



class TestRepositories(unittest.TestCase):
    """Verifies schema migrations and all domain repositories."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        applied = self.db.run_migrations()
        self.assertIn(1, applied)

        # Seed country profiles needed for FKs
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        # Seed service profile
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'Enterprise AI Automation');
        """)
        self.conn.commit()

        self.source_repo = SourceRepository(self.conn)
        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)
        self.agent_run_repo = AgentRunRepository(self.conn)
        self.content_repo = ContentRepository(self.conn)


    def tearDown(self):
        self.db.close()

    def test_source_lifecycle(self):
        source = Source(
            source_id="src-001",
            domain_or_platform_key="riyadh-chamber.org.sa",
            country_scope=["SA"],
            source_family="chamber_association",
            languages=["ar"],
            status=SourceStatus.TRUSTED,
            access_mode=AccessMode.PUBLIC,
            metadata_json={"official": True},
        )
        self.source_repo.save_source(source)

        fetched = self.source_repo.get_source("src-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.domain_or_platform_key, "riyadh-chamber.org.sa")
        self.assertEqual(fetched.status, SourceStatus.TRUSTED)

        # Test capability score update
        self.source_repo.set_capability_score("src-001", "company_discovery", 0.92)
        scores = self.source_repo.get_capability_scores("src-001")
        self.assertEqual(scores.get("company_discovery"), 0.92)

    def test_company_lifecycle(self):
        company = Company(
            company_id="comp-001",
            canonical_name="شركة المسار السريع",
            primary_domain="example-saudi-logistics.com",
            country_code="SA",
            city="الرياض",
            sector="Logistics",
            public_contacts_json={"email": "info@example-saudi-logistics.com"},
            funnel=FunnelType.B2B,
            entity_confidence=1.0,
        )
        self.company_repo.save_company(company)

        by_id = self.company_repo.get_company("comp-001")
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id.canonical_name, "شركة المسار السريع")

        by_domain = self.company_repo.find_by_domain("example-saudi-logistics.com")
        self.assertIsNotNone(by_domain)
        self.assertEqual(by_domain.company_id, "comp-001")

        by_name = self.company_repo.find_by_name("المسار")
        self.assertEqual(len(by_name), 1)

    def test_evidence_lifecycle(self):
        # Create prerequisite source
        source = Source(
            source_id="src-web-01",
            domain_or_platform_key="example-saudi-logistics.com",
            country_scope=["SA"],
            source_family="company_website",
            languages=["ar"],
            status=SourceStatus.CANDIDATE,
            access_mode=AccessMode.PUBLIC,
        )
        self.source_repo.save_source(source)

        evidence = Evidence(
            evidence_id="ev-001",
            source_id="src-web-01",
            url="https://example-saudi-logistics.com/about",
            fact_type="operational_pain",
            fact_text="Seeking WhatsApp customer support automation",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="sha256_mock_hash_12345",
            confidence=0.98,
        )
        self.evidence_repo.save_evidence(evidence)

        fetched = self.evidence_repo.get_evidence("ev-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.fact_type, "operational_pain")

        by_hash = self.evidence_repo.find_by_hash("sha256_mock_hash_12345")
        self.assertIsNotNone(by_hash)
        self.assertEqual(by_hash.evidence_id, "ev-001")

    def test_lead_and_assessment(self):
        # Prerequisites
        company = Company(
            company_id="comp-lead-01",
            canonical_name="Apex FinTech",
            primary_domain="apexfin.ae",
            country_code="AE",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead-001",
            company_id="comp-lead-01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
        )
        self.lead_repo.save_lead(lead)

        fetched_lead = self.lead_repo.get_lead("lead-001")
        self.assertIsNotNone(fetched_lead)
        self.assertEqual(fetched_lead.priority_bucket, 1)

        # Append assessments
        ass1 = LeadAssessment(
            assessment_id="ass-001",
            lead_id="lead-001",
            fit_score=0.9,
            pain_score=0.85,
            urgency_score=0.8,
            final_score=0.85,
            confidence=0.95,
            recommended_service_key="ai_automation",
            reasoning_summary="High fit expansion signal in DIFC",
        )
        self.lead_repo.save_assessment(ass1)

        latest = self.lead_repo.get_latest_assessment("lead-001")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.assessment_id, "ass-001")
        self.assertEqual(latest.final_score, 0.85)

    def test_approval_state_machine(self):
        approval = Approval(
            approval_id="appr-001",
            action_type="publish_post",
            target_type="content_asset",
            target_id="asset-999",
            decision=ApprovalDecision.PENDING,
        )
        self.approval_repo.create_request(approval)

        pending = self.approval_repo.list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].approval_id, "appr-001")

        # Resolve approval
        ok = self.approval_repo.resolve(
            approval_id="appr-001",
            decision=ApprovalDecision.APPROVED,
            actor_id="operator-founder",
            notes="Reviewed and approved copy",
        )
        self.assertTrue(ok)

        # Verify no longer pending
        pending_after = self.approval_repo.list_pending()
        self.assertEqual(len(pending_after), 0)

        # Idempotency: resolving again fails
        ok_again = self.approval_repo.resolve(
            approval_id="appr-001",
            decision=ApprovalDecision.REJECTED,
            actor_id="operator-founder",
        )
        self.assertFalse(ok_again)

    def test_agent_run_lifecycle(self):
        """Ensure AgentRun records persist and can be queried by task type."""
        run = AgentRun(
            agent_run_id="run-test-001",
            task_type="lead_assessment",
            provider_path="antigravity_cli",
            model_identity="gemini-3.8-flash-high",
            input_refs=["lead-001", "ev-001"],
            input_size_estimate=1250,
            output_contract_version="1.0",
            status="completed",
            approval_required=False,
        )
        self.agent_run_repo.save_agent_run(run)

        fetched = self.agent_run_repo.get_agent_run("run-test-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.task_type, "lead_assessment")
        self.assertEqual(fetched.model_identity, "gemini-3.8-flash-high")
        self.assertEqual(fetched.input_refs, ["lead-001", "ev-001"])
        self.assertEqual(fetched.status, "completed")

        # Query by task
        runs = self.agent_run_repo.list_by_task("lead_assessment")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].agent_run_id, "run-test-001")

    def test_evidence_list_by_hash(self):
        """Ensure all evidence items sharing the same content hash can be listed."""
        # Prerequisites: source
        source = Source(
            source_id="src-hash-01",
            domain_or_platform_key="multi-evidence.example.com",
            country_scope=["SA"],
            source_family="company_website",
            languages=["ar"],
        )
        self.source_repo.save_source(source)

        shared_hash = "sha256_shared_page_artifact_hash_abc"
        ev1 = Evidence(
            evidence_id="ev-hash-01",
            source_id="src-hash-01",
            url="https://multi-evidence.example.com/about",
            fact_type="expansion_plan",
            fact_text="Opening new branch in Riyadh",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash=shared_hash,
            confidence=0.95,
        )
        ev2 = Evidence(
            evidence_id="ev-hash-02",
            source_id="src-hash-01",
            url="https://multi-evidence.example.com/about",
            fact_type="hiring_need",
            fact_text="Hiring 5 senior AI engineers",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash=shared_hash,
            confidence=0.90,
        )
        self.evidence_repo.save_evidence(ev1)
        self.evidence_repo.save_evidence(ev2)

        results = self.evidence_repo.list_by_hash(shared_hash)
        self.assertEqual(len(results), 2)
        fact_types = {r.fact_type for r in results}
        self.assertIn("expansion_plan", fact_types)
        self.assertIn("hiring_need", fact_types)

    def test_interaction_actor_and_outcome_tag(self):
        """Ensure Interaction table accepts actor and outcome_tag fields."""
        company = Company(
            company_id="comp-inter-01",
            canonical_name="Inter Corp",
            primary_domain="intercorp.com",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)

        lead = Lead(
            lead_id="lead-001",
            company_id="comp-inter-01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
        )
        self.lead_repo.save_lead(lead)

        inter = Interaction(
            interaction_id="inter-001",
            lead_id="lead-001",
            channel="email",
            external_party_ref="ceo@example.com",
            direction=InteractionDirection.OUTBOUND,
            actor=ActorType.AGENT_DRAFT,
            content_summary="Initial personalized outreach draft",
            outcome_tag="awaiting_human_review",
        )
        sql = """
            INSERT INTO interactions (
                interaction_id, lead_id, channel, external_party_ref,
                direction, actor, content_summary, outcome_tag, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (
                inter.interaction_id,
                inter.lead_id,
                inter.channel,
                inter.external_party_ref,
                inter.direction.value,
                inter.actor.value,
                inter.content_summary,
                inter.outcome_tag,
                inter.occurred_at.isoformat(),
            ),
        )
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute("SELECT actor, outcome_tag FROM interactions WHERE interaction_id = ?;", ("inter-001",))
        row = cur.fetchone()
        self.assertEqual(row["actor"], "agent_draft")
        self.assertEqual(row["outcome_tag"], "awaiting_human_review")

    def test_multi_connection_wal_persistence(self):
        """Ensure writes on connection 1 are committed and visible on connection 2 in WAL mode."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name

        try:
            db1 = Database(tmp_db_path)
            conn1 = db1.connect()
            db1.run_migrations()

            # Seed country profile for FK constraint
            conn1.execute(
                "INSERT INTO country_profiles (country_code, name, languages) VALUES ('SA', 'Saudi Arabia', '[\"ar\"]');"
            )
            conn1.commit()

            company_repo1 = CompanyRepository(conn1)
            comp = Company(
                company_id="comp-wal-01",
                canonical_name="WAL Test Enterprise",
                primary_domain="waltest.com",
                country_code="SA",
                funnel=FunnelType.B2B,
            )
            company_repo1.save_company(comp)

            # Open completely new second connection without closing conn1
            db2 = Database(tmp_db_path)
            conn2 = db2.connect()
            company_repo2 = CompanyRepository(conn2)

            fetched_by_conn2 = company_repo2.get_company("comp-wal-01")
            self.assertIsNotNone(fetched_by_conn2)
            self.assertEqual(fetched_by_conn2.canonical_name, "WAL Test Enterprise")

            db1.close()
            db2.close()
        finally:
            for suffix in ["", "-wal", "-shm", ".bak"]:
                p = tmp_db_path + suffix
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass


    def test_content_repository_lifecycle(self):
        """Verifies ContentRepository operations for ideas and multi-platform assets."""
        idea = ContentIdea(
            content_idea_id="idea-integ-01",
            funnel=FunnelType.B2B,
            market_scope=["SA", "AE"],
            service_key="ai_automation",
            source_signal_ids=["sig-01"],
            topic="Automating Enterprise Dispatch in Riyadh",
            objective=ContentIdeaObjective.DEMAND_CAPTURE,
            score=0.91,
            status="proposed",
        )
        self.content_repo.save_idea(idea)

        fetched_idea = self.content_repo.get_idea("idea-integ-01")
        self.assertIsNotNone(fetched_idea)
        self.assertEqual(fetched_idea.topic, "Automating Enterprise Dispatch in Riyadh")
        self.assertEqual(fetched_idea.market_scope, ["SA", "AE"])

        # Add asset
        asset = ContentAsset(
            content_asset_id="asset-integ-01",
            idea_id="idea-integ-01",
            master_content="Master narrative for dispatch automation",
            platform="linkedin",
            format="long_form_post",
            body="Complete post body for testing",
            media_brief="Workflow architecture chart",
            cta="Schedule an engineering audit",
            status=ContentAssetStatus.AWAITING_APPROVAL,
            version=1,
        )
        self.content_repo.save_asset(asset)

        fetched_asset = self.content_repo.get_asset("asset-integ-01")
        self.assertIsNotNone(fetched_asset)
        self.assertEqual(fetched_asset.platform, "linkedin")
        self.assertEqual(fetched_asset.status, ContentAssetStatus.AWAITING_APPROVAL)

        # Update status
        updated = self.content_repo.update_asset_status("asset-integ-01", ContentAssetStatus.APPROVED)
        self.assertTrue(updated)
        self.assertEqual(self.content_repo.get_asset("asset-integ-01").status, ContentAssetStatus.APPROVED)

        # List assets
        assets = self.content_repo.list_assets(idea_id="idea-integ-01")
        self.assertEqual(len(assets), 1)


if __name__ == "__main__":
    unittest.main()


