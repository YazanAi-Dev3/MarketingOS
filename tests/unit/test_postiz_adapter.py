"""Unit tests for Postiz REST API Adapter.

Verifies:
- Header and auth token formatting
- Health check verification under mock and live responses
- Integration channel listing
- Post creation, scheduling, and secret sanitization (A-018, I-05)
- Error and timeout recovery
"""
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock
import httpx

from marketing_plugin.adapters.postiz_adapter import PostizAdapter, PostizPostResponse


class TestPostizAdapter(unittest.TestCase):
    """Unit test suite for PostizAdapter."""

    def test_init_and_headers(self):
        """Verifies header construction with API key."""
        adapter = PostizAdapter(base_url="http://test-postiz:5000/", api_key="test_key_123")
        self.assertEqual(adapter.base_url, "http://test-postiz:5000")
        headers = adapter._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer test_key_123")
        self.assertEqual(headers["x-api-key"], "test_key_123")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_check_health_mock_mode(self):
        """Verifies health check in mock mode returns True immediately."""
        adapter = PostizAdapter(mock_mode=True)
        self.assertTrue(adapter.check_health())

    def test_check_health_with_client(self):
        """Verifies health check under HTTP 200 and connection error."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.get.return_value = mock_resp

        adapter = PostizAdapter(client=mock_client)
        self.assertTrue(adapter.check_health())
        mock_client.get.assert_called_with("http://localhost:5000/api/v1/health", headers=adapter._get_headers())

        # Error case
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        self.assertFalse(adapter.check_health())

    def test_list_integrations_mock_and_http(self):
        """Verifies listing connected social channels."""
        # Mock mode
        adapter_mock = PostizAdapter(mock_mode=True)
        integrations = adapter_mock.list_integrations()
        self.assertEqual(len(integrations), 3)
        providers = {i["provider"] for i in integrations}
        self.assertIn("linkedin", providers)
        self.assertIn("twitter", providers)

        # HTTP Client mode
        mock_client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "int_live_1", "provider": "linkedin", "status": "active"}
        ]
        mock_client.get.return_value = mock_resp

        adapter_http = PostizAdapter(client=mock_client)
        live_res = adapter_http.list_integrations()
        self.assertEqual(len(live_res), 1)
        self.assertEqual(live_res[0]["provider"], "linkedin")

    def test_create_post_mock_mode(self):
        """Verifies post creation in mock mode."""
        adapter = PostizAdapter(mock_mode=True)
        resp = adapter.create_post(
            content="Testing automation post in Riyadh",
            platforms=["linkedin", "twitter"],
            scheduled_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(resp.success)
        self.assertIsNotNone(resp.post_id)
        self.assertEqual(resp.providers, ["linkedin", "twitter"])
        self.assertEqual(resp.scheduled_at, "2026-10-01T12:00:00+00:00")

    def test_create_post_redacts_secrets(self):
        """Verifies that secrets are stripped prior to dispatch (Invariant I-05)."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "post_789", "status": "queued"}
        mock_client.post.return_value = mock_resp

        adapter = PostizAdapter(client=mock_client)
        dirty_content = "Deploying AI with secret sk-1234567890123456789012 to enterprise."
        resp = adapter.create_post(
            content=dirty_content,
            platforms=["linkedin"],
        )
        self.assertTrue(resp.success)

        # Verify posted payload
        called_args, called_kwargs = mock_client.post.call_args
        sent_payload = called_kwargs["json"]
        self.assertNotIn("sk-1234567890123456789012", sent_payload["content"])
        self.assertIn("[REDACTED_SECRET]", sent_payload["content"])

    def test_create_post_error_handling(self):
        """Verifies error response when Postiz API returns failure."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid provider specified"
        mock_client.post.return_value = mock_resp

        adapter = PostizAdapter(client=mock_client)
        resp = adapter.create_post(
            content="Some valid content",
            platforms=["unknown_channel"],
        )
        self.assertFalse(resp.success)
        self.assertIn("HTTP 400", resp.error_message)


if __name__ == "__main__":
    unittest.main()

