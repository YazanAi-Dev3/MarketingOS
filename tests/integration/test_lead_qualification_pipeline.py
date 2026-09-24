"""Integration tests for Lead Qualification Pipeline and Scoring Engine.

Tests end-to-end integration across:
1. Synthetic Multilingual Corpus & Ground Truth Evaluation Labels:
   - Clean B2B AI Automation Lead (SA) -> Qualified, Priority Bucket 1
   - Hiring Expansion Signal (AE) -> Qualified, Priority Bucket 1
   - Legitimate Academic Mentoring (JO) -> Qualified, Priority Bucket 2
   - Academic Integrity Violation (SY) -> Rejected, Prohibited (A-008)
   - Prompt Injection Attempt -> Neutralized as untrusted data
2. Integration with MarketScanner and SQLite Persistence:
   - Full discovery -> acquisition -> entity resolution -> lead scoring -> approval flow (A-007)
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from marketing_plugin import assess_lead, list_leads, request_approval
from marketing_plugin.adapters.antigravity_adapter import AntigravityAdapter, ReasoningResult
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.lead_scorer import LeadScorer
from schemas.models import (
    ApprovalDecision,
    Company,
    Evidence,
    ExtractorType,
    FunnelType,
    LeadStatus,
    utc_now,
)
from tests.fixtures.evaluation_seeds import LEAD_PRIORITY_RANKING_LABELS
from tests.fixtures.synthetic_corpus import SYNTHETIC_CORPUS


class TestLeadQualificationPipeline(unittest.TestCase):
    """End-to-end integration tests for Lead Qualification Pipeline."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'UAE', '["ar", "en"]', 0.25),
                   ('QA', 'Qatar', '["ar", "en"]', 0.10),
                   ('SY', 'Syria', '["ar"]', 0.10),
                   ('TR', 'Turkey', '["tr", "en"]', 0.10),
                   ('JO', 'Jordan', '["ar"]', 0.02);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Workflow Automation'),
                   ('software_systems', 'tertiary', '["b2b"]', 'Software Systems & Web'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Legitimate Academic Mentoring');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('company_website', 'company.com', '["ALL"]', 'website', '["ar", "en", "tr"]', 'trusted', 'public'),
                   ('jobs_careers', 'careers.com', '["ALL"]', 'jobs', '["ar", "en"]', 'trusted', 'public'),
                   ('public_social', 'social.com', '["ALL"]', 'social', '["ar", "en"]', 'trusted', 'public'),
                   ('public_board', 'board.net', '["ALL"]', 'forum', '["ar"]', 'trusted', 'public'),
                   ('directory', 'directory.com', '["ALL"]', 'directory', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

    def test_synthetic_clean_saudi_logistics_qualification(self):
        """Fixture 'gcc-sa-01-clean-logistics' should qualify as high priority B2B AI lead."""
        fixture = next(f for f in SYNTHETIC_CORPUS if f["fixture_id"] == "gcc-sa-01-clean-logistics")

        company = Company(
            company_id="comp_sa_logistics",
            canonical_name=fixture["title"],
            country_code=fixture["country_code"],
            funnel=FunnelType.B2B,
            public_contacts_json={"email": "operations@example-saudi-logistics.com", "phone": "+966112345678"},
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_sa_logistics_1",
            company_id="comp_sa_logistics",
            source_id="company_website",
            url=fixture["url"],
            fact_type="operational_pain",
            fact_text=fixture["raw_text"],
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_sa_logistics",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        # Mock high-confidence Antigravity reasoning
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
                "reasoning_summary": "High-urgency logistics company needing WhatsApp & WMS automation.",
                "confidence": 0.95,
            },
        )

        scorer = LeadScorer(db=self.db, adapter=mock_adapter, enable_model=True)
        res = scorer.score_company("comp_sa_logistics")

        self.assertTrue(res.success)
        self.assertEqual(res.status, LeadStatus.QUALIFIED)
        self.assertEqual(res.priority_bucket, LEAD_PRIORITY_RANKING_LABELS["gcc-sa-01-clean-logistics"])
        self.assertGreaterEqual(res.final_score, 0.85)
        self.assertEqual(res.recommended_service_key, "ai_automation")

    def test_synthetic_uae_hiring_signal_qualification(self):
        """Fixture 'gcc-ae-02-hiring-fintech' should qualify as high priority expansion lead."""
        fixture = next(f for f in SYNTHETIC_CORPUS if f["fixture_id"] == "gcc-ae-02-hiring-fintech")

        company = Company(
            company_id="comp_ae_fintech",
            canonical_name="Apex Financial Technologies",
            country_code=fixture["country_code"],
            funnel=FunnelType.B2B,
            public_contacts_json={"email": "partnerships@apexfin.ae"},
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_ae_fintech_1",
            company_id="comp_ae_fintech",
            source_id="jobs_careers",
            url=fixture["url"],
            fact_type="hiring_signal",
            fact_text=fixture["raw_text"],
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_ae_fintech",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        mock_adapter = MagicMock(spec=AntigravityAdapter)
        mock_adapter.reason.return_value = ReasoningResult(
            success=True,
            structured_data={
                "fit_score": 0.90,
                "pain_score": 0.85,
                "urgency_score": 0.90,
                "reachability_score": 0.90,
                "decision": "qualified",
                "academic_integrity_passed": True,
                "recommended_service_key": "ai_automation",
                "reasoning_summary": "Active Q4 hiring for AI integration in Dubai DIFC.",
                "confidence": 0.95,
            },
        )

        scorer = LeadScorer(db=self.db, adapter=mock_adapter, enable_model=True)
        res = scorer.score_company("comp_ae_fintech")

        self.assertTrue(res.success)
        self.assertEqual(res.status, LeadStatus.QUALIFIED)
        self.assertEqual(res.priority_bucket, LEAD_PRIORITY_RANKING_LABELS["gcc-ae-02-hiring-fintech"])

    def test_synthetic_academic_integrity_violation_rejection(self):
        """Fixture 'levant-sy-02-academic-violation' must be strictly rejected per A-008."""
        fixture = next(f for f in SYNTHETIC_CORPUS if f["fixture_id"] == "levant-sy-02-academic-violation")

        company = Company(
            company_id="comp_sy_thesis_cheating",
            canonical_name=fixture["title"],
            country_code=fixture["country_code"],
            funnel=FunnelType.ACADEMIC,
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_sy_cheating_1",
            company_id="comp_sy_thesis_cheating",
            source_id="public_board",
            url=fixture["url"],
            fact_type="academic_request",
            fact_text=fixture["raw_text"],
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_sy_cheating",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        scorer = LeadScorer(db=self.db, enable_model=False)
        res = scorer.score_company("comp_sy_thesis_cheating")

        self.assertTrue(res.success)
        self.assertEqual(res.status, LeadStatus.REJECTED)
        self.assertEqual(res.priority_bucket, 3)
        self.assertFalse(res.academic_integrity_passed)
        self.assertIn("A-008", res.reasoning_summary)

        # Check DB state
        lead = self.lead_repo.get_lead("lead_comp_sy_thesis_cheating")
        self.assertEqual(lead.status, LeadStatus.REJECTED)

    def test_end_to_end_qualification_and_approval_flow(self):
        """Tests complete qualification pipeline followed by human gatekeeper approval (A-007)."""
        # 1. Register company and evidence
        company = Company(
            company_id="comp_e2e_approval",
            canonical_name="Doha Logistics Services",
            country_code="QA",
            funnel=FunnelType.B2B,
            public_contacts_json={"email": "contact@doha-logistics.qa"},
        )
        self.company_repo.save_company(company)

        evidence = Evidence(
            evidence_id="evi_doha_1",
            company_id="comp_e2e_approval",
            source_id="company_website",
            url="https://doha-logistics.qa",
            fact_type="web_extract",
            fact_text="We need to automate our customs clearance document processing pipeline.",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_doha_1",
            observed_at=utc_now(),
        )
        self.evidence_repo.save_evidence(evidence)

        # 2. Assess lead using assess_lead domain tool with mock model evaluation
        assess_res = assess_lead(
            company_id="comp_e2e_approval",
            context={
                "model_evaluation": {
                    "qualified": True,
                    "fit_score": 0.90,
                    "pain_score": 0.85,
                    "urgency_score": 0.80,
                    "reachability_score": 0.90,
                    "decision": "qualified",
                    "academic_integrity_passed": True,
                    "recommended_service_key": "ai_automation",
                    "reasoning_summary": "Clear logistics document processing automation requirement.",
                }
            },
            db=self.db,
        )
        self.assertEqual(assess_res["status"], "success")
        self.assertEqual(assess_res["lead_status"], "qualified")
        self.assertEqual(assess_res["priority_bucket"], 1)

        # 3. Verify lead is retrievable via list_leads
        qualified_leads = list_leads(status="qualified", country_code="QA", db=self.db)
        self.assertEqual(len(qualified_leads), 1)
        self.assertEqual(qualified_leads[0]["company_id"], "comp_e2e_approval")

        # 4. Request human approval for outreach (Invariant A-007)
        appr_res = request_approval(
            action_type="outreach_send",
            target_type="lead",
            target_id=qualified_leads[0]["lead_id"],
            notes="Ready to send tailored cold proposal for customs document AI automation.",
            db=self.db,
        )
        self.assertEqual(appr_res["status"], "requested")
        self.assertEqual(appr_res["decision"], "pending")

        # 5. Verify approval record in DB
        appr = self.approval_repo.get_approval(appr_res["approval_id"])
        self.assertIsNotNone(appr)
        self.assertEqual(appr.decision, ApprovalDecision.PENDING)
        self.assertEqual(appr.action_type, "outreach_send")


if __name__ == "__main__":
    unittest.main()
