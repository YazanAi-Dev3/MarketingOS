"""Postiz REST API Adapter for Marketing OS.

Implements social publishing and scheduling integration with self-hosted Postiz (A-021).
Provides health checks, integration channel listing, post creation, and scheduled post dispatch.
Gracefully handles offline/unreachable conditions (R-04) and supports hermetic mock mode.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from marketing_plugin.policies.redactor import redact_secrets

logger = logging.getLogger(__name__)

DEFAULT_POSTIZ_URL = "http://localhost:5000"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass
class PostizPostResponse:
    """Response returned from Postiz post creation/scheduling."""
    success: bool
    post_id: Optional[str] = None
    scheduled_at: Optional[str] = None
    providers: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class PostizAdapter:
    """HTTP Client adapter for Postiz open-source social scheduling API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
        mock_mode: bool = False,
    ) -> None:
        self.base_url = (base_url or DEFAULT_POSTIZ_URL).rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = client
        self.mock_mode = mock_mode

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-api-key"] = self.api_key
        return headers

    def check_health(self) -> bool:
        """Verifies if the Postiz service is reachable and responding."""
        if self.mock_mode:
            return True

        url = f"{self.base_url}/api/v1/health"
        try:
            client = self._client or httpx.Client(timeout=self.timeout)
            try:
                resp = client.get(url, headers=self._get_headers())
                return resp.status_code in (200, 204)
            finally:
                if self._client is None:
                    client.close()
        except Exception as exc:
            logger.debug(f"Postiz health check failed: {exc}")
            return False

    def list_integrations(self) -> List[Dict[str, Any]]:
        """Lists connected social media accounts/integrations configured in Postiz."""
        if self.mock_mode:
            return [
                {"id": "int_li_01", "provider": "linkedin", "name": "Company LinkedIn", "status": "connected"},
                {"id": "int_tw_01", "provider": "twitter", "name": "@MarketingOS_AI", "status": "connected"},
                {"id": "int_tg_01", "provider": "telegram", "name": "Marketing OS Channel", "status": "connected"},
            ]

        url = f"{self.base_url}/api/v1/integrations"
        try:
            client = self._client or httpx.Client(timeout=self.timeout)
            try:
                resp = client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("integrations", [])
                logger.warning(f"Failed to list Postiz integrations: HTTP {resp.status_code}")
                return []
            finally:
                if self._client is None:
                    client.close()
        except Exception as exc:
            logger.warning(f"Error fetching Postiz integrations: {exc}")
            return []

    def create_post(
        self,
        content: str,
        platforms: List[str],
        scheduled_at: Optional[datetime] = None,
        media_urls: Optional[List[str]] = None,
    ) -> PostizPostResponse:
        """Creates or schedules a post across specified social media platforms."""
        clean_content = redact_secrets(content)
        normalized_platforms = [p.lower().strip() for p in platforms]

        if self.mock_mode:
            scheduled_iso = scheduled_at.isoformat() if scheduled_at else None
            return PostizPostResponse(
                success=True,
                post_id=f"postiz_mock_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                scheduled_at=scheduled_iso,
                providers=normalized_platforms,
                raw_response={"status": "mock_created", "platforms": normalized_platforms},
            )

        payload: Dict[str, Any] = {
            "content": clean_content,
            "providers": normalized_platforms,
        }
        if scheduled_at is not None:
            payload["scheduledAt"] = scheduled_at.isoformat()
        if media_urls:
            payload["media"] = media_urls

        url = f"{self.base_url}/api/v1/posts"
        try:
            client = self._client or httpx.Client(timeout=self.timeout)
            try:
                resp = client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PostizPostResponse(
                        success=True,
                        post_id=data.get("id") or data.get("post_id"),
                        scheduled_at=data.get("scheduledAt"),
                        providers=normalized_platforms,
                        raw_response=data,
                    )
                err_msg = f"Postiz returned HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(err_msg)
                return PostizPostResponse(
                    success=False,
                    providers=normalized_platforms,
                    error_message=err_msg,
                )
            finally:
                if self._client is None:
                    client.close()
        except Exception as exc:
            err_msg = f"Network exception communicating with Postiz: {exc}"
            logger.error(err_msg)
            return PostizPostResponse(
                success=False,
                providers=normalized_platforms,
                error_message=err_msg,
            )
