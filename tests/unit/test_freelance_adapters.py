"""Unit tests for Freelance Source Adapters (Bahr, Mostaql, Khamsat).

Ensures deterministic extraction, zero network dependencies, and valid Evidence schemas.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from marketing_plugin.adapters.acquisition_router import AcquisitionMode, compute_content_hash
from marketing_plugin.adapters.bahr_adapter import BahrAdapter
from marketing_plugin.adapters.base import BaseSourceAdapter
from marketing_plugin.adapters.khamsat_adapter import KhamsatAdapter
from marketing_plugin.adapters.mostaql_adapter import MostaqlAdapter
from schemas.models import Evidence, ExtractorType

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "freelance"


class TestFreelanceAdapters(unittest.TestCase):
    """Verifies all specialized freelance adapters against static fixtures."""

    def setUp(self):
        self.bahr = BahrAdapter()
        self.mostaql = MostaqlAdapter()
        self.khamsat = KhamsatAdapter()

        # Load fixtures
        self.bahr_json_raw = (FIXTURES_DIR / "bahr_listing.json").read_text(encoding="utf-8")
        self.bahr_html_raw = (FIXTURES_DIR / "bahr_listing.html").read_text(encoding="utf-8")
        self.mostaql_html_raw = (FIXTURES_DIR / "mostaql_listing.html").read_text(encoding="utf-8")
        self.khamsat_html_raw = (FIXTURES_DIR / "khamsat_listing.html").read_text(encoding="utf-8")

    # --- Base Contract Tests ---

    def test_base_adapter_contract(self):
        """Verify BaseSourceAdapter enforces abstract methods and provides to_evidence."""
        class IncompleteAdapter(BaseSourceAdapter):
            pass

        with self.assertRaises(TypeError):
            IncompleteAdapter()  # Can't instantiate abstract class

        class MinimalAdapter(BaseSourceAdapter):
            source_key = "test_source"

            def build_search_url(self, query: str, page: int = 1) -> str:
                return f"https://example.com/search?q={query}&p={page}"

            def extract_listings(self, raw_html_or_payload: str):
                return [{"title": "Test Job", "description": "Need Python dev"}]

            def extract_detail(self, raw_html_or_payload: str):
                return {"title": "Test Job Detail"}

        adapter = MinimalAdapter()
        self.assertEqual(adapter.default_acquisition_mode, AcquisitionMode.CRAWL4AI)
        self.assertEqual(adapter.source_key, "test_source")
        self.assertEqual(adapter.build_search_url("ai", 2), "https://example.com/search?q=ai&p=2")

        # Test to_evidence
        record = {"title": "Test Job", "description": "Need Python dev", "budget": "$100"}
        evi = adapter.to_evidence(record, url="https://example.com/job/1")
        self.assertIsInstance(evi, Evidence)
        self.assertEqual(evi.source_id, "test_source")
        self.assertEqual(evi.extractor, ExtractorType.DETERMINISTIC)
        self.assertEqual(evi.url, "https://example.com/job/1")
        self.assertEqual(evi.content_hash, compute_content_hash(evi.fact_text))
        self.assertTrue(evi.evidence_id.startswith("evi_test_source_"))

        # Test to_evidence rejection of invalid schemes and malformed URLs
        with self.assertRaises(ValueError):
            adapter.to_evidence(record, url="ftp://example.com/job/1")
        with self.assertRaises(ValueError):
            adapter.to_evidence(record, url="/relative/url")
        with self.assertRaises(ValueError):
            adapter.to_evidence(record, url="")
        with self.assertRaises(ValueError):
            adapter.to_evidence(record, url="javascript:alert(1)")

    # --- Bahr Adapter Tests ---

    def test_bahr_adapter_attributes_and_url(self):
        """Verify Bahr adapter metadata and search URL builder."""
        self.assertEqual(self.bahr.source_key, "bahr")
        self.assertEqual(self.bahr.default_acquisition_mode, AcquisitionMode.CRAWL4AI)

        url = self.bahr.build_search_url("تطوير تطبيقات", 2)
        self.assertIn("https://bahr.sa/projects?", url)
        self.assertIn("search=", url)
        self.assertIn("page=2", url)

    def test_bahr_extract_listings_json(self):
        """Verify Bahr adapter extracts structured items from Next.js JSON payload."""
        items = self.bahr.extract_listings(self.bahr_json_raw)
        self.assertEqual(len(items), 2)

        item1 = items[0]
        self.assertEqual(item1["title"], "تطوير تطبيق جوال لمتجر إلكتروني باستخدام Flutter")
        self.assertEqual(item1["budget"], "5000 - 10000 ريال")
        self.assertEqual(item1["duration"], "30 يوم")
        self.assertIn("Flutter", item1["tags"])
        self.assertIn("سلة", item1["description"])
        self.assertEqual(item1["url"], "https://bahr.sa/projects/101")

        item2 = items[1]
        self.assertIn("UI/UX", item2["title"])
        self.assertIn("Figma", item2["tags"])
        self.assertEqual(item2["url"], "https://bahr.sa/projects/102")

    def test_bahr_extract_listings_html(self):
        """Verify Bahr adapter extracts structured items from rendered HTML."""
        items = self.bahr.extract_listings(self.bahr_html_raw)
        self.assertEqual(len(items), 2)

        item1 = items[0]
        self.assertIn("أتمتة خدمة العملاء", item1["title"])
        self.assertEqual(item1["budget"], "4000 - 8000 ريال")
        self.assertEqual(item1["duration"], "20 يوم")
        self.assertIn("AI", item1["tags"])
        self.assertIn("واتساب", item1["description"])
        self.assertEqual(item1["url"], "https://bahr.sa/projects/201")

        item2 = items[1]
        self.assertIn("Power BI", item2["title"])
        self.assertEqual(item2["url"], "https://bahr.sa/projects/202")

    def test_bahr_extract_detail(self):
        """Verify Bahr adapter detail extraction from JSON and HTML."""
        detail_json = json.dumps({
            "project": {
                "id": 999,
                "title": "نظام ذكاء اصطناعي للتحليلات",
                "budget": "15000 ريال",
                "duration": "45 يوم",
                "tags": ["AI", "Python"],
                "description": "مشروع بناء نظام ذكاء اصطناعي",
                "url": "https://bahr.sa/projects/999",
            }
        })
        detail = self.bahr.extract_detail(detail_json)
        self.assertEqual(detail["title"], "نظام ذكاء اصطناعي للتحليلات")
        self.assertEqual(detail["budget"], "15000 ريال")
        self.assertEqual(detail["url"], "https://bahr.sa/projects/999")

        detail_html = """
        <html><body>
          <h1 class="project-title">تطوير منصة B2B</h1>
          <span class="project-budget">20000 ريال</span>
          <span class="project-duration">60 يوم</span>
          <div class="tags"><span class="tag">Django</span></div>
          <div class="project-description">تفاصيل المنصة...</div>
          <link rel="canonical" href="https://bahr.sa/projects/888">
        </body></html>
        """
        detail_h = self.bahr.extract_detail(detail_html)
        self.assertEqual(detail_h["title"], "تطوير منصة B2B")
        self.assertEqual(detail_h["budget"], "20000 ريال")
        self.assertEqual(detail_h["duration"], "60 يوم")
        self.assertEqual(detail_h["url"], "https://bahr.sa/projects/888")

    def test_bahr_to_evidence(self):
        """Verify Bahr to_evidence generates valid Evidence with deterministic hash."""
        items = self.bahr.extract_listings(self.bahr_json_raw)
        evi = self.bahr.to_evidence(items[0], url=items[0]["url"])

        self.assertIsInstance(evi, Evidence)
        self.assertEqual(evi.source_id, "bahr")
        self.assertEqual(evi.extractor, ExtractorType.DETERMINISTIC)
        self.assertEqual(evi.url, "https://bahr.sa/projects/101")
        self.assertTrue(len(evi.content_hash) == 64)
        self.assertEqual(evi.content_hash, compute_content_hash(evi.fact_text))
        self.assertIn("Flutter", evi.fact_text)

    # --- Mostaql Adapter Tests ---

    def test_mostaql_adapter_attributes_and_url(self):
        """Verify Mostaql adapter metadata and search URL builder."""
        self.assertEqual(self.mostaql.source_key, "mostaql")
        self.assertEqual(self.mostaql.default_acquisition_mode, AcquisitionMode.CRAWL4AI)

        url = self.mostaql.build_search_url("ذكاء اصطناعي", 3)
        self.assertIn("https://mostaql.com/projects?", url)
        self.assertIn("keyword=", url)
        self.assertIn("page=3", url)

    def test_mostaql_extract_listings(self):
        """Verify Mostaql adapter extracts structured items from HTML fixture."""
        items = self.mostaql.extract_listings(self.mostaql_html_raw)
        self.assertEqual(len(items), 2)

        item1 = items[0]
        self.assertEqual(item1["title"], "أتمتة عمليات التسويق عبر WhatsApp وربطها مع CRM")
        self.assertEqual(item1["budget"], "$250 - $500")
        self.assertEqual(item1["duration"], "10 أيام")
        self.assertIn("Python", item1["tags"])
        self.assertIn("CRM", item1["description"])
        self.assertEqual(item1["url"], "https://mostaql.com/project/892341-marketing-automation-whatsapp")

        item2 = items[1]
        self.assertIn("لوحة تحكم ذكاء اصطناعي", item2["title"])
        self.assertEqual(item2["budget"], "$500 - $1000")
        self.assertEqual(item2["duration"], "20 يوماً")
        self.assertIn("FastAPI", item2["tags"])
        self.assertEqual(item2["url"], "https://mostaql.com/project/892342-ai-dashboard-marketing")

    def test_mostaql_extract_detail(self):
        """Verify Mostaql adapter extracts project detail from HTML."""
        detail_html = """
        <html><body>
          <h1 class="project__title">ربط نظام CRM مع منصة سلة</h1>
          <span class="project__budget">$1000 - $2500</span>
          <span class="project__duration">15 يوماً</span>
          <div class="project__tags">
            <a class="badge" href="#">API</a>
            <a class="badge" href="#">PHP</a>
          </div>
          <div class="project__description">
            نحتاج لربط متجرنا مع CRM خارجي...
          </div>
          <link rel="canonical" href="https://mostaql.com/project/9999-crm-salla">
        </body></html>
        """
        detail = self.mostaql.extract_detail(detail_html)
        self.assertEqual(detail["title"], "ربط نظام CRM مع منصة سلة")
        self.assertEqual(detail["budget"], "$1000 - $2500")
        self.assertEqual(detail["duration"], "15 يوماً")
        self.assertIn("API", detail["tags"])
        self.assertIn("CRM خارجي", detail["description"])
        self.assertEqual(detail["url"], "https://mostaql.com/project/9999-crm-salla")

    def test_mostaql_to_evidence(self):
        """Verify Mostaql to_evidence produces compliant Evidence object."""
        items = self.mostaql.extract_listings(self.mostaql_html_raw)
        evi = self.mostaql.to_evidence(items[0], url=items[0]["url"])

        self.assertIsInstance(evi, Evidence)
        self.assertEqual(evi.source_id, "mostaql")
        self.assertEqual(evi.extractor, ExtractorType.DETERMINISTIC)
        self.assertEqual(evi.url, "https://mostaql.com/project/892341-marketing-automation-whatsapp")
        self.assertTrue(len(evi.content_hash) == 64)
        self.assertEqual(evi.content_hash, compute_content_hash(evi.fact_text))
        self.assertIn("WhatsApp", evi.fact_text)

    # --- Khamsat Adapter Tests ---

    def test_khamsat_adapter_attributes_and_url(self):
        """Verify Khamsat adapter metadata and search URL builder."""
        self.assertEqual(self.khamsat.source_key, "khamsat")
        self.assertEqual(self.khamsat.default_acquisition_mode, AcquisitionMode.CRAWL4AI)

        url = self.khamsat.build_search_url("سيو", 1)
        self.assertIn("https://khamsat.com/community/requests?", url)
        self.assertIn("keyword=", url)
        self.assertIn("page=1", url)

    def test_khamsat_extract_listings(self):
        """Verify Khamsat adapter extracts community requests from HTML fixture."""
        items = self.khamsat.extract_listings(self.khamsat_html_raw)
        self.assertEqual(len(items), 2)

        item1 = items[0]
        self.assertIn("تحسين محركات البحث SEO", item1["title"])
        self.assertEqual(item1["author"], "ahmed_marketer")
        self.assertIn("دروب شيبينغ", item1["description"])
        self.assertEqual(item1["url"], "https://khamsat.com/community/requests/654321-seo-expert-saudi")

        item2 = items[1]
        self.assertIn("كاتب محتوى تقني", item2["title"])
        self.assertEqual(item2["author"], "sara_tech")
        self.assertIn("التحول الرقمي", item2["description"])
        self.assertEqual(item2["url"], "https://khamsat.com/community/requests/654322-content-writer-arabic")

    def test_khamsat_extract_detail(self):
        """Verify Khamsat adapter extracts request detail from HTML."""
        detail_html = """
        <html><body>
          <h1 class="title">طلب برمجة بوت تيليجرام تفاعلي</h1>
          <a class="author-name" href="/user/omar_coder">omar_coder</a>
          <div class="details-body">
            أحتاج بوت تيليجرام يقوم بالرد على استفسارات المشتركين وتوجيههم للدفع.
          </div>
          <link rel="canonical" href="https://khamsat.com/community/requests/7777-telegram-bot">
        </body></html>
        """
        detail = self.khamsat.extract_detail(detail_html)
        self.assertEqual(detail["title"], "طلب برمجة بوت تيليجرام تفاعلي")
        self.assertEqual(detail["author"], "omar_coder")
        self.assertIn("تيليجرام", detail["description"])
        self.assertEqual(detail["url"], "https://khamsat.com/community/requests/7777-telegram-bot")

    def test_khamsat_to_evidence(self):
        """Verify Khamsat to_evidence produces compliant Evidence object."""
        items = self.khamsat.extract_listings(self.khamsat_html_raw)
        evi = self.khamsat.to_evidence(items[0], url=items[0]["url"])

        self.assertIsInstance(evi, Evidence)
        self.assertEqual(evi.source_id, "khamsat")
        self.assertEqual(evi.extractor, ExtractorType.DETERMINISTIC)
        self.assertEqual(evi.url, "https://khamsat.com/community/requests/654321-seo-expert-saudi")
        self.assertTrue(len(evi.content_hash) == 64)
        self.assertEqual(evi.content_hash, compute_content_hash(evi.fact_text))
        self.assertIn("Author: ahmed_marketer", evi.fact_text)

    # --- Robustness & Edge Cases ---

    def test_empty_or_malformed_input(self):
        """Verify adapters safely return empty collections for empty or invalid inputs."""
        for adapter in (self.bahr, self.mostaql, self.khamsat):
            self.assertEqual(adapter.extract_listings(""), [])
            self.assertEqual(adapter.extract_listings("   "), [])
            self.assertEqual(adapter.extract_listings("<html><body>No listings here</body></html>"), [])
            self.assertEqual(adapter.extract_detail(""), {})
            self.assertEqual(adapter.extract_detail("   "), {})

    def test_url_validation_and_domain_isolation(self):
        """Verify adapters enforce expected platform domain in to_evidence and listing parsing."""
        record = {"title": "Test Listing", "budget": "1000"}

        # Valid domain URLs succeed
        evi_bahr = self.bahr.to_evidence(record, url="https://bahr.sa/projects/123")
        self.assertEqual(evi_bahr.url, "https://bahr.sa/projects/123")

        evi_mostaql = self.mostaql.to_evidence(record, url="https://mostaql.com/project/456")
        self.assertEqual(evi_mostaql.url, "https://mostaql.com/project/456")

        evi_khamsat = self.khamsat.to_evidence(record, url="https://khamsat.com/community/requests/789")
        self.assertEqual(evi_khamsat.url, "https://khamsat.com/community/requests/789")

        # Mismatched domain raises ValueError
        with self.assertRaises(ValueError):
            self.bahr.to_evidence(record, url="https://malicious.com/projects/123")

        with self.assertRaises(ValueError):
            self.mostaql.to_evidence(record, url="https://phishing.org/project/456")

        with self.assertRaises(ValueError):
            self.khamsat.to_evidence(record, url="https://attacker.net/community/requests/789")
