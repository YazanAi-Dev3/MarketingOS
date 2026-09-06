"""Integration tests for MarketScanner Pipeline.

Verifies regional query planning -> SearXNG discovery -> SSRF-safe page acquisition
-> adapter extraction (Bahr, Mostaql, Khamsat, Generic) -> entity resolution
-> SQLite persistence of Evidence, Company, and Lead records.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from marketing_plugin.adapters.acquisition_router import (
    AcquisitionMode,
    AcquisitionResult,
    compute_content_hash,
)
from marketing_plugin.adapters.searxng_adapter import SearchRunResult
from marketing_plugin.policies.query_planner import RegionalQueryPlanner
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository
from marketing_plugin.services.entity_resolver import EntityResolver
from marketing_plugin.services.market_scanner import MarketScanner, ScanRunSummary
from marketing_plugin.tools.domain_tools import scan_market
from schemas.models import LeadStatus, SearchResult

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "freelance"


class TestMarketScannerIntegration(unittest.TestCase):
    """End-to-end integration test of the Market Scanner pipeline with SQLite."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country profiles
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'United Arab Emirates', '["ar", "en"]', 0.25);
        """)
        # Seed service profiles
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Workflow Automation'),
                   ('software_dev', 'primary', '["b2b"]', 'Custom Software Development');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.source_repo = SourceRepository(self.conn)
        self.resolver = EntityResolver(self.company_repo)

        # Mock SearXNG adapter returning SSRF-safe URL
        self.mock_searxng = MagicMock()
        self.mock_searxng.search.return_value = SearchRunResult(
            success=True,
            query="test_query",
            results=[
                SearchResult(
                    search_result_id="res_001",
                    search_run_id="run_001",
                    url="https://example.com/solutions",
                    normalized_url="https://example.com/solutions",
                    title="Riyadh AI Solutions | Automation",
                    snippet="Leading enterprise AI automation in Riyadh",
                    rank=1,
                    engine_sources=["google"],
                ),
            ],
            total_results=1,
        )

        # Load sanitized fixtures
        self.html_bahr = (FIXTURES_DIR / "bahr_listing.html").read_text(encoding="utf-8")
        self.html_mostaql = (FIXTURES_DIR / "mostaql_listing.html").read_text(encoding="utf-8")
        self.html_khamsat = (FIXTURES_DIR / "khamsat_listing.html").read_text(encoding="utf-8")

        self.html_generic = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Riyadh AI Solutions - Smart Workflows</title>
            <meta name="description" content="Empowering Saudi enterprises with automated AI agents.">
        </head>
        <body>
            <h1>Riyadh AI Solutions</h1>
            <p>Contact us at info@example.com or call +966509998877.</p>
        </body>
        </html>
        """

        # Mock AcquisitionRouter
        self.mock_router = MagicMock()

        def route_side_effect(url: str, **kwargs):
            if "bahr.sa" in url:
                return AcquisitionResult(
                    success=True,
                    url=url,
                    normalized_url=url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    status_code=200,
                    raw_content=self.html_bahr,
                    content_hash=compute_content_hash(self.html_bahr),
                )
            elif "mostaql.com" in url:
                return AcquisitionResult(
                    success=True,
                    url=url,
                    normalized_url=url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    status_code=200,
                    raw_content=self.html_mostaql,
                    content_hash=compute_content_hash(self.html_mostaql),
                )
            elif "khamsat.com" in url:
                return AcquisitionResult(
                    success=True,
                    url=url,
                    normalized_url=url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    status_code=200,
                    raw_content=self.html_khamsat,
                    content_hash=compute_content_hash(self.html_khamsat),
                )
            elif "example.com" in url:
                return AcquisitionResult(
                    success=True,
                    url=url,
                    normalized_url=url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    status_code=200,
                    raw_content=self.html_generic,
                    content_hash=compute_content_hash(self.html_generic),
                )
            else:
                return AcquisitionResult(
                    success=False,
                    url=url,
                    normalized_url=url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    error="Page not found",
                )

        self.mock_router.route_acquisition.side_effect = route_side_effect

        self.scanner = MarketScanner(
            db=self.db,
            planner=RegionalQueryPlanner(),
            searxng_adapter=self.mock_searxng,
            acquisition_router=self.mock_router,
            entity_resolver=self.resolver,
            company_repo=self.company_repo,
            evidence_repo=self.evidence_repo,
            lead_repo=self.lead_repo,
            source_repo=self.source_repo,
        )

    # --- Test 1: Full Scan Pipeline Execution ---

    def test_full_market_scan_pipeline_execution(self):
        """Verify complete scanner execution creates companies, evidence, and leads."""
        summary = self.scanner.scan(
            country_code="SA",
            service_key="ai_automation",
            limit=5,
        )

        self.assertIsInstance(summary, ScanRunSummary)
        self.assertEqual(summary.country_code, "SA")
        self.assertEqual(summary.service_key, "ai_automation")
        self.assertTrue(summary.queries_executed >= 1)
        self.assertTrue(summary.discovered_urls >= 4)
        self.assertTrue(summary.acquired_pages >= 4)
        self.assertTrue(summary.created_companies >= 4)
        self.assertTrue(summary.saved_evidence >= 4)
        self.assertEqual(summary.errors, [])

        # 1. Verify Companies in SQLite
        generic_comp = self.company_repo.find_by_domain("example.com")
        self.assertIsNotNone(generic_comp)
        self.assertEqual(generic_comp.country_code, "SA")
        self.assertIn("info@example.com", generic_comp.public_contacts_json.get("email", ""))

        # 2. Verify Evidence records in SQLite
        evidence_items = self.evidence_repo.list_for_company(generic_comp.company_id)
        self.assertTrue(len(evidence_items) >= 1)
        evi = evidence_items[0]
        self.assertEqual(evi.source_id, "searxng_web")
        self.assertEqual(len(evi.content_hash), 64)  # Valid SHA-256
        self.assertIn("Riyadh AI Solutions", evi.fact_text)

        # 3. Verify Leads in SQLite with DISCOVERED status
        lead_id = f"lead_{generic_comp.company_id}"
        lead = self.lead_repo.get_lead(lead_id)
        self.assertIsNotNone(lead)
        self.assertEqual(lead.status, LeadStatus.DISCOVERED)
        self.assertEqual(lead.recommended_service_key, "ai_automation")

    # --- Test 2: Idempotent Deduplication on Second Scan ---

    def test_market_scanner_idempotent_deduplication(self):
        """Verify second scan on identical sources merges existing companies and creates zero duplicate leads."""
        summary_run1 = self.scanner.scan(
            country_code="SA",
            service_key="ai_automation",
            limit=5,
        )
        initial_created = summary_run1.created_companies
        self.assertTrue(initial_created >= 4)

        # Run scan second time
        summary_run2 = self.scanner.scan(
            country_code="SA",
            service_key="ai_automation",
            limit=5,
        )

        # Second run should merge existing companies
        self.assertEqual(summary_run2.created_companies, 0)
        self.assertTrue(summary_run2.merged_companies >= 4)

        # Check total leads count has not duplicated
        all_leads = self.lead_repo.list_leads()
        self.assertEqual(len(all_leads), initial_created)

    # --- Test 3: SSRF Protection Safeguard ---

    def test_market_scanner_ssrf_protection_safeguard(self):
        """Verify URLs pointing to loopback or metadata endpoints are blocked and logged as errors."""
        unsafe_urls = [
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8080/admin",
            "http://localhost/secret",
        ]

        summary = self.scanner.scan(
            country_code="SA",
            urls=unsafe_urls,
            include_freelance_sources=False,
        )

        self.assertEqual(summary.acquired_pages, 0)
        self.assertEqual(summary.created_companies, 0)
        self.assertEqual(summary.saved_evidence, 0)
        self.assertEqual(len(summary.errors), 3)
        self.assertTrue(all("SSRF" in err for err in summary.errors))

    # --- Test 4: Hermes Tool Integration (scan_market) ---

    def test_scan_market_tool_executes_full_scanner(self):
        """Verify scan_market tool with run_full_scanner=True executes the pipeline and returns summary."""
        tool_result = scan_market(
            country_code="SA",
            service_key="ai_automation",
            scanner=self.scanner,
            run_full_scanner=True,
            limit=5,
        )

        self.assertEqual(tool_result["status"], "success")
        self.assertEqual(tool_result["country_code"], "SA")
        self.assertEqual(tool_result["service_key"], "ai_automation")
        self.assertIn("scan_summary", tool_result)
        self.assertTrue(tool_result["created_companies"] >= 4)
        self.assertTrue(tool_result["saved_evidence"] >= 4)
        self.assertTrue(tool_result["acquired_pages"] >= 4)

    # --- Test 5: Auto-bootstrap unseeded country on fresh DB ---

    def test_market_scanner_auto_bootstraps_unseeded_country_on_fresh_db(self):
        """Verify unseeded country is auto-bootstrapped into country_profiles with configured weight on fresh DB."""
        fresh_db = Database(":memory:")
        fresh_db.connect()
        fresh_db.run_migrations()

        scanner = MarketScanner(
            db=fresh_db,
            acquisition_router=self.mock_router,
        )
        summary = scanner.scan(
            country_code="TR",
            limit=1,
            urls=["https://example.com/tr-test"],
        )

        self.assertEqual(summary.country_code, "TR")
        self.assertEqual(summary.errors, [])

        cursor = fresh_db.connect().cursor()
        cursor.execute(
            "SELECT country_code, name, manual_weight, enabled FROM country_profiles WHERE country_code = 'TR';",
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["country_code"], "TR")
        self.assertEqual(row["name"], "Turkey")
        self.assertAlmostEqual(row["manual_weight"], 0.10)
        self.assertEqual(row["enabled"], 1)

