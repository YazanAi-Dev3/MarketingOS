"""Tests for SearXNG Adapter, Regional Query Planner, and Acquisition Router."""
import socket
import unittest
from unittest.mock import MagicMock, patch

from marketing_plugin.adapters.acquisition_router import (
    AcquisitionMode,
    AcquisitionRouter,
    compute_content_hash,
    is_ssrf_safe_url,
)
from marketing_plugin.adapters.searxng_adapter import (
    SearXNGAdapter,
    normalize_url,
)
from marketing_plugin.policies.query_planner import RegionalQueryPlanner
from schemas.models import FunnelType


class TestAcquisitionAndSearch(unittest.TestCase):
    """Verifies search normalization, query planning, and SSRF-safe acquisition."""

    def test_normalize_url(self):
        url = "https://example.com/products/ai-tool/?utm_source=twitter&utm_medium=cpc&fbclid=123#frag"
        norm = normalize_url(url)
        self.assertEqual(norm, "https://example.com/products/ai-tool")

        # Test trailing slash and lowercase domain
        url2 = "HTTP://EXAMPLE.COM/about/"
        self.assertEqual(normalize_url(url2), "http://example.com/about")

    def test_ssrf_filter(self):
        # Internal / Loopback addresses must be blocked
        self.assertFalse(is_ssrf_safe_url("http://localhost:8080/admin"))
        self.assertFalse(is_ssrf_safe_url("http://127.0.0.1:5000"))
        self.assertFalse(is_ssrf_safe_url("http://10.0.0.5/api"))
        self.assertFalse(is_ssrf_safe_url("http://192.168.1.10/login"))
        self.assertFalse(is_ssrf_safe_url("ftp://example.com"))

        # Public hostnames allowed
        self.assertTrue(is_ssrf_safe_url("https://example.com/public/data"))
        self.assertTrue(is_ssrf_safe_url("http://api.github.com/repos"))

    def test_content_hashing(self):
        text = "Sample evidence extracted from page"
        h1 = compute_content_hash(text)
        h2 = compute_content_hash(text)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex length

    def test_regional_query_planner(self):
        planner = RegionalQueryPlanner()

        # Saudi Arabia Plan
        sa_plan = planner.plan(country_code="SA", service_key="ai_automation", funnel=FunnelType.B2B)
        self.assertEqual(sa_plan.country_code, "SA")
        self.assertEqual(sa_plan.language_target, "ar")
        self.assertTrue(any("الرياض" in q for q in sa_plan.queries))
        self.assertTrue(any("واتساب" in q for q in sa_plan.queries))

        # UAE Plan
        ae_plan = planner.plan(country_code="AE", service_key="ai_automation", funnel=FunnelType.B2B)
        self.assertEqual(ae_plan.country_code, "AE")
        self.assertEqual(ae_plan.language_target, "en")
        self.assertTrue(any("Dubai" in q for q in ae_plan.queries))

        # Turkey Plan
        tr_plan = planner.plan(country_code="TR", service_key="ai_automation", funnel=FunnelType.B2B)
        self.assertEqual(tr_plan.country_code, "TR")
        self.assertEqual(tr_plan.language_target, "tr")
        self.assertTrue(any("İstanbul" in q for q in tr_plan.queries))

    def test_searxng_adapter_mock(self):
        mock_response = {
            "query": "أتمتة الشركات الرياض",
            "results": [
                {
                    "url": "https://example-saudi-logistics.com/about?utm_source=google",
                    "title": "شركة المسار اللوجستي",
                    "content": "نقدم خدمات الأتمتة وإدارة المستودعات في الرياض",
                    "engines": ["google", "bing"],
                }
            ],
        }

        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp

            adapter = SearXNGAdapter(base_url="http://mock-searxng:8080")
            result = adapter.search(query="أتمتة الشركات الرياض", country_code="SA")

            self.assertTrue(result.success)
            self.assertEqual(result.total_results, 1)
            first = result.results[0]
            self.assertEqual(first.normalized_url, "https://example-saudi-logistics.com/about")
            self.assertEqual(first.title, "شركة المسار اللوجستي")
            self.assertEqual(first.rank, 1)
            self.assertIn("google", first.engine_sources)

    def test_acquisition_router_blocks_ssrf(self):
        router = AcquisitionRouter()
        res = router.route_acquisition("http://127.0.0.1:8080/internal-secrets")
        self.assertFalse(res.success)
        self.assertIn("SSRF", res.error)

    def test_acquisition_router_direct_http_mock(self):
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<html><body>Clean company text</body></html>"
            mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
            mock_get.return_value = mock_resp

            router = AcquisitionRouter()
            res = router.route_acquisition("https://example.com/about")

            self.assertTrue(res.success)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mode_used, AcquisitionMode.DIRECT_HTTP)
            self.assertIn("Clean company text", res.raw_content)
            self.assertTrue(len(res.content_hash) == 64)

    def test_acquisition_router_blocks_redirect_ssrf(self):
        """Ensure HTTP redirects to cloud metadata or internal network are blocked."""
        with patch("httpx.Client.get") as mock_get:
            # First request returns 302 redirecting to AWS/cloud metadata IP
            redirect_resp = MagicMock()
            redirect_resp.status_code = 302
            redirect_resp.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
            mock_get.return_value = redirect_resp

            router = AcquisitionRouter()
            res = router.route_acquisition("https://example.com/redirect-to-metadata")

            self.assertFalse(res.success)
            self.assertIn("SSRF", res.error)

    def test_ssrf_filter_integer_and_decimal_ips(self):
        """Ensure decimal/integer encoded IP addresses targeting loopback are blocked."""
        # 2130706433 is 127.0.0.1 in decimal notation
        self.assertFalse(is_ssrf_safe_url("http://2130706433/admin"))
        # 0.0.0.0 binds to all interfaces
        self.assertFalse(is_ssrf_safe_url("http://0.0.0.0:8080"))
        # Cloud metadata IP
        self.assertFalse(is_ssrf_safe_url("http://169.254.169.254/latest/"))

    def test_ssrf_filter_dns_failure_fails_closed(self):
        """Ensure socket.gaierror or resolution failure fails closed."""
        with patch("socket.getaddrinfo", side_effect=socket.gaierror):
            self.assertFalse(is_ssrf_safe_url("https://unresolvable-domain-xyz.example.com"))


if __name__ == "__main__":
    unittest.main()


