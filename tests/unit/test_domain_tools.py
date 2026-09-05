"""Unit tests for Marketing OS Domain Tools (Hermes integration).

Verifies scan_market, assess_lead, list_leads, and request_approval
under deterministic in-memory conditions with zero network dependencies.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from marketing_plugin import (
    DOMAIN_TOOLS,
    assess_lead,
    list_leads,
    request_approval,
    scan_market,
)
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from schemas.models import (
    ApprovalDecision,
    Company,
    Evidence,
    ExtractorType,
    FunnelType,
    Lead,
    LeadAssessment,
    LeadStatus,
    SearchResult,
    utc_now,
)


class TestDomainTools(unittest.TestCase):
    """Verifies all domain tools exposed to Hermes."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed reference country profiles and services
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Workflow Automation'),
                   ('software_dev', 'primary', '["b2b"]', 'Custom Software Development');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('mostaql', 'mostaql.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public'),
                   ('bahr', 'bahr.sa', '["SA"]', 'freelance_platform', '["ar"]', 'trusted', 'public'),
                   ('khamsat', 'khamsat.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

    # --- Tool Registration Tests ---

    def test_tool_registration(self):
        """Ensure all 4 domain tools are exported in DOMAIN_TOOLS and package namespace."""
        self.assertEqual(len(DOMAIN_TOOLS), 4)
        tool_names = [t.__name__ for t in DOMAIN_TOOLS]
        self.assertIn("scan_market", tool_names)
        self.assertIn("assess_lead", tool_names)
        self.assertIn("list_leads", tool_names)
        self.assertIn("request_approval", tool_names)

    # --- scan_market Tests ---

    def test_scan_market_saudi_includes_bahr_mostaql_khamsat(self):
        """Verify scan_market for Saudi Arabia includes regional query plan and all 3 freelance adapters."""
        res = scan_market(
            country_code="SA",
            query="حلول الذكاء الاصطناعي",
            service_key="ai_automation",
            db=self.db,
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["country_code"], "SA")
        self.assertEqual(res["service_key"], "ai_automation")
        self.assertTrue(len(res["planned_queries"]) >= 1)
        self.assertIn("حلول الذكاء الاصطناعي", res["planned_queries"])

        # Candidate sources for SA must include bahr, mostaql, and khamsat
        sources = {cs["source"] for cs in res["candidate_sources"]}
        self.assertIn("bahr", sources)
        self.assertIn("mostaql", sources)
        self.assertIn("khamsat", sources)

    def test_scan_market_uae_excludes_bahr(self):
        """Verify scan_market for non-Saudi country excludes Bahr (SA-only)."""
        res = scan_market(
            country_code="AE",
            query="AI Automation",
            service_key="ai_automation",
            db=self.db,
        )
        self.assertEqual(res["country_code"], "AE")
        sources = {cs["source"] for cs in res["candidate_sources"]}
        self.assertNotIn("bahr", sources)
        self.assertIn("mostaql", sources)
        self.assertIn("khamsat", sources)

    def test_scan_market_with_mocked_searxng(self):
        """Verify scan_market executes queries when SearXNG adapter is provided."""
        mock_searxng = MagicMock()
        mock_searxng.search.return_value = [
            SearchResult(
                search_result_id="sr_1",
                search_run_id="run_1",
                url="https://saudi-tech.example.com",
                normalized_url="https://saudi-tech.example.com",
                title="Saudi Tech Agency",
                snippet="Leading AI automation in Riyadh",
                rank=1,
                engine_sources=["google"],
            )
        ]

        res = scan_market(
            country_code="SA",
            query="AI agents Riyadh",
            searxng_adapter=mock_searxng,
            db=self.db,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["results_count"], 3)
        self.assertEqual(res["results"][0]["title"], "Saudi Tech Agency")
        self.assertTrue(mock_searxng.search.called)

    def test_scan_market_fallback_without_db(self):
        """Verify scan_market falls back to static candidate source list when db is None."""
        res_sa = scan_market(country_code="SA", query="Automations", db=None)
        sources_sa = {cs["source"] for cs in res_sa["candidate_sources"]}
        self.assertIn("bahr", sources_sa)
        self.assertIn("mostaql", sources_sa)
        self.assertIn("khamsat", sources_sa)

        res_ae = scan_market(country_code="AE", query="Automations", db=None)
        sources_ae = {cs["source"] for cs in res_ae["candidate_sources"]}
        self.assertNotIn("bahr", sources_ae)
        self.assertIn("mostaql", sources_ae)
        self.assertIn("khamsat", sources_ae)

    # --- assess_lead Tests ---

    def test_assess_lead_success(self):
        """Verify assess_lead generates bounded scores and keeps DISCOVERED on baseline, transitioning to QUALIFIED on model evaluation."""
        # 1. Create company
        company = Company(
            company_id="comp_101",
            canonical_name="Riyadh Logistics Solutions",
            primary_domain="riyadh-logistics.example.sa",
            country_code="SA",
            city="Riyadh",
            sector="Logistics",
            public_contacts_json={"email": "contact@riyadh-logistics.example.sa", "phone": "+966500000000"},
            funnel=FunnelType.B2B,
            entity_confidence=1.0,
        )
        self.company_repo.save_company(company)

        # 2. Attach Evidence with pain keyword
        evidence = Evidence(
            evidence_id="evi_comp_101_1",
            company_id="comp_101",
            source_id="mostaql",
            url="https://mostaql.com/project/101",
            fact_type="freelance_listing",
            fact_text="نبحث عن خبير أتمتة لربط نظام إدارة المستودعات عبر API وواتساب",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            confidence=1.0,
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        # 3. Unassisted baseline assessment: invariant docs/09-final-design-review.md:108
        # Keywords in evidence do NOT qualify lead; must remain DISCOVERED.
        res = assess_lead("comp_101", db=self.db)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["company_id"], "comp_101")
        self.assertEqual(res["lead_id"], "lead_comp_101")
        self.assertTrue(0.0 <= res["fit_score"] <= 1.0)
        self.assertEqual(res["pain_score"], 0.50)  # Baseline pain score reflecting unverified signals
        self.assertTrue(0.0 <= res["urgency_score"] <= 1.0)
        self.assertTrue(0.0 <= res["reachability_score"] <= 1.0)
        self.assertTrue(0.0 <= res["final_score"] <= 1.0)
        self.assertEqual(res["lead_status"], "discovered")

        # 4. Verify in DB: lead status is DISCOVERED and assessment snapshot exists
        lead = self.lead_repo.get_lead("lead_comp_101")
        self.assertIsNotNone(lead)
        self.assertEqual(lead.status, LeadStatus.DISCOVERED)

        asm = self.lead_repo.get_latest_assessment("lead_comp_101")
        self.assertIsNotNone(asm)
        self.assertEqual(asm.assessment_id, res["assessment_id"])
        self.assertIn("evi_comp_101_1", asm.evidence_ids)

        # 5. Model-assisted assessment transitions lead to QUALIFIED
        res_model = assess_lead(
            "comp_101",
            context={
                "model_evaluation": {
                    "qualified": True,
                    "pain_score": 0.85,
                    "confidence": 0.95,
                    "summary": "Verified logistics integration requirement matching offer profile",
                }
            },
            db=self.db,
        )
        self.assertEqual(res_model["status"], "success")
        self.assertEqual(res_model["lead_status"], "qualified")
        self.assertEqual(res_model["pain_score"], 0.85)

        # Verify DB updated to QUALIFIED
        lead_after = self.lead_repo.get_lead("lead_comp_101")
        self.assertIsNotNone(lead_after)
        self.assertEqual(lead_after.status, LeadStatus.QUALIFIED)

        # Verify new assessment snapshot created
        asm_after = self.lead_repo.get_latest_assessment("lead_comp_101")
        self.assertIsNotNone(asm_after)
        self.assertEqual(asm_after.assessment_id, res_model["assessment_id"])

    def test_assess_lead_not_found(self):
        """Verify assess_lead gracefully handles unknown company."""
        res = assess_lead("comp_unknown", db=self.db)
        self.assertEqual(res["status"], "error")
        self.assertIn("not found", res["error"])

    def test_get_latest_assessment_tie_breaker_identical_timestamps(self):
        """Verify get_latest_assessment deterministically breaks ties via rowid DESC when created_at is identical."""
        company = Company(
            company_id="comp_tie_break",
            canonical_name="Tie Break Corp",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(company)
        lead = Lead(
            lead_id="lead_tie_break",
            company_id="comp_tie_break",
            funnel=FunnelType.B2B,
            status=LeadStatus.DISCOVERED,
            priority_bucket=3,
        )
        self.lead_repo.save_lead(lead)

        same_time = utc_now()
        asm1 = LeadAssessment(
            assessment_id="asm_first",
            lead_id="lead_tie_break",
            assessment_version="1.0",
            fit_score=0.5,
            pain_score=0.5,
            urgency_score=0.5,
            reachability_score=0.5,
            final_score=0.5,
            confidence=0.5,
            recommended_service_key="ai_automation",
            evidence_ids=[],
            reasoning_summary="First snapshot",
            provider_identity="test",
            prompt_contract_version="1.0",
            created_at=same_time,
        )
        asm2 = LeadAssessment(
            assessment_id="asm_second",
            lead_id="lead_tie_break",
            assessment_version="2.0",
            fit_score=0.8,
            pain_score=0.8,
            urgency_score=0.8,
            reachability_score=0.8,
            final_score=0.8,
            confidence=0.8,
            recommended_service_key="ai_automation",
            evidence_ids=[],
            reasoning_summary="Second snapshot inserted later with identical timestamp",
            provider_identity="test",
            prompt_contract_version="1.0",
            created_at=same_time,
        )
        self.lead_repo.save_assessment(asm1)
        self.lead_repo.save_assessment(asm2)

        latest = self.lead_repo.get_latest_assessment("lead_tie_break")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.assessment_id, "asm_second")

    # --- list_leads Tests ---

    def test_list_leads_filtering_and_pagination(self):
        """Verify list_leads correctly filters by status and country code."""
        # Create 2 companies in different countries
        c1 = Company(
            company_id="comp_sa_1",
            canonical_name="Company SA",
            country_code="SA",
            funnel=FunnelType.B2B,
        )
        c2 = Company(
            company_id="comp_ae_1",
            canonical_name="Company AE",
            country_code="AE",
            funnel=FunnelType.B2B,
        )
        self.company_repo.save_company(c1)
        self.company_repo.save_company(c2)

        # Create leads
        lead_sa = Lead(
            lead_id="lead_sa",
            company_id="comp_sa_1",
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
        )
        lead_ae = Lead(
            lead_id="lead_ae",
            company_id="comp_ae_1",
            status=LeadStatus.DISCOVERED,
            priority_bucket=2,
        )
        self.lead_repo.save_lead(lead_sa)
        self.lead_repo.save_lead(lead_ae)

        # 1. List all
        all_leads = list_leads(db=self.db)
        self.assertEqual(len(all_leads), 2)

        # 2. Filter by status
        qual_leads = list_leads(status="qualified", db=self.db)
        self.assertEqual(len(qual_leads), 1)
        self.assertEqual(qual_leads[0]["lead_id"], "lead_sa")

        # 3. Filter by country code
        sa_leads = list_leads(country_code="SA", db=self.db)
        self.assertEqual(len(sa_leads), 1)
        self.assertEqual(sa_leads[0]["lead_id"], "lead_sa")

        ae_leads = list_leads(country_code="AE", db=self.db)
        self.assertEqual(len(ae_leads), 1)
        self.assertEqual(ae_leads[0]["lead_id"], "lead_ae")

        # 4. Limit parameter
        limited = list_leads(limit=1, db=self.db)
        self.assertEqual(len(limited), 1)

    # --- request_approval Tests ---

    def test_request_approval_flow(self):
        """Verify request_approval creates an approval record with pending decision."""
        res = request_approval(
            action_type="publish_post",
            target_type="content_asset",
            target_id="asset_777",
            notes="Ready for LinkedIn posting; pending marketing lead sign-off",
            db=self.db,
        )

        self.assertEqual(res["status"], "requested")
        self.assertEqual(res["action_type"], "publish_post")
        self.assertEqual(res["target_type"], "content_asset")
        self.assertEqual(res["target_id"], "asset_777")
        self.assertEqual(res["decision"], "pending")
        self.assertTrue(res["approval_id"].startswith("appr_"))

        # Verify persisted in repository
        appr = self.approval_repo.get_approval(res["approval_id"])
        self.assertIsNotNone(appr)
        self.assertEqual(appr.decision, ApprovalDecision.PENDING)
        self.assertEqual(appr.notes, "Ready for LinkedIn posting; pending marketing lead sign-off")
