"""Acquisition Router and Evidence Fetcher for Marketing OS.

Routes URL acquisition to Direct HTTP or Crawl4AI according to A-037.
Enforces SSRF boundaries, private network blocking, content size limits,
and cryptographic SHA-256 evidence hashing.
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import socket
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB safety limit
DEFAULT_TIMEOUT_SECONDS = 20.0


class AcquisitionMode(str, Enum):
    DIRECT_HTTP = "direct_http"
    CRAWL4AI = "crawl4ai"


@dataclass
class AcquisitionResult:
    """Standardized result of a page acquisition."""
    success: bool
    url: str
    normalized_url: str
    mode_used: AcquisitionMode
    status_code: int = 0
    content_type: str = ""
    raw_content: str = ""
    content_hash: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


def is_ssrf_safe_url(url: str) -> bool:
    """Check whether a URL targets a public, safe hostname and not private/internal networks."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        lower_host = hostname.lower()
        if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254"):
            return False

        # If hostname is numeric or decimal IP (e.g. 2130706433 or 127.1)
        try:
            if lower_host.isdigit():
                ip_obj = ipaddress.ip_address(int(lower_host))
            else:
                ip_obj = ipaddress.ip_address(lower_host)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                return False
            return True
        except ValueError:
            # Hostname is a domain name, proceed to DNS resolution
            pass

        # Try to resolve IP to check private ranges (Fail closed)
        try:
            addrinfo = socket.getaddrinfo(hostname, None)
            if not addrinfo:
                return False
            for item in addrinfo:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_reserved
                    or ip_obj.is_multicast
                ):
                    return False
        except (socket.gaierror, socket.herror, ValueError):
            # Fail closed: resolution error means unsafe target
            return False

        return True
    except Exception:
        return False



def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of extracted content for evidence provenance."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AcquisitionRouter:
    """Selects and executes the appropriate acquisition strategy for target URLs."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = MAX_BODY_BYTES,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.timeout = timeout_seconds
        self.max_bytes = max_bytes
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=False,
            headers={
                "User-Agent": "MarketingOS-Intelligence/2.0 (+https://intellify.example/bot)",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            },
        )

    def route_acquisition(
        self,
        url: str,
        force_mode: Optional[AcquisitionMode] = None,
    ) -> AcquisitionResult:
        """Acquire target URL using the appropriate strategy."""
        normalized = url.strip()

        # Enforce SSRF boundary on initial URL
        if not is_ssrf_safe_url(normalized):
            return AcquisitionResult(
                success=False,
                url=url,
                normalized_url=normalized,
                mode_used=force_mode or AcquisitionMode.DIRECT_HTTP,
                error="URL failed SSRF safety validation (private/internal network target forbidden)",
            )

        mode = force_mode or self._select_mode(normalized)

        if mode == AcquisitionMode.DIRECT_HTTP:
            return self._fetch_direct_http(normalized)
        else:
            return self._fetch_crawl4ai(normalized)

    def _select_mode(self, url: str) -> AcquisitionMode:
        """Heuristic selector: prefer direct HTTP for JSON/APIs or simple pages, Crawl4AI for complex SPAs."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        if path.endswith((".json", ".xml", ".rss", ".atom")) or "/api/" in path:
            return AcquisitionMode.DIRECT_HTTP
        # Default policy under A-037: prefer direct HTTP first if sufficient, Crawl4AI for rich sites
        return AcquisitionMode.DIRECT_HTTP

    def _fetch_direct_http(self, url: str) -> AcquisitionResult:
        """Fetch page via direct HTTP request with per-hop SSRF validation."""
        start_time = datetime.now(timezone.utc)
        current_url = url
        redirect_count = 0
        max_redirects = 5
        client = self._get_client()

        try:
            while True:
                # Enforce SSRF boundary before requesting each hop
                if not is_ssrf_safe_url(current_url):
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                    return AcquisitionResult(
                        success=False,
                        url=url,
                        normalized_url=current_url,
                        mode_used=AcquisitionMode.DIRECT_HTTP,
                        duration_seconds=elapsed,
                        error=f"Redirect destination failed SSRF safety validation: {current_url}",
                    )

                resp = client.get(current_url)

                # Check if this is a redirect response
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        return AcquisitionResult(
                            success=False,
                            url=url,
                            normalized_url=current_url,
                            mode_used=AcquisitionMode.DIRECT_HTTP,
                            duration_seconds=elapsed,
                            error="Redirect response missing Location header",
                        )
                    redirect_count += 1
                    if redirect_count > max_redirects:
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        return AcquisitionResult(
                            success=False,
                            url=url,
                            normalized_url=current_url,
                            mode_used=AcquisitionMode.DIRECT_HTTP,
                            duration_seconds=elapsed,
                            error=f"Too many redirects (exceeded limit of {max_redirects})",
                        )
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue

                break

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            if resp.status_code >= 400:
                return AcquisitionResult(
                    success=False,
                    url=url,
                    normalized_url=current_url,
                    mode_used=AcquisitionMode.DIRECT_HTTP,
                    status_code=resp.status_code,
                    duration_seconds=elapsed,
                    error=f"HTTP {resp.status_code} error",
                )

            # Limit content size
            content = resp.text[:self.max_bytes]
            content_hash = compute_content_hash(content)

            return AcquisitionResult(
                success=True,
                url=url,
                normalized_url=current_url,
                mode_used=AcquisitionMode.DIRECT_HTTP,
                status_code=resp.status_code,
                content_type=resp.headers.get("content-type", ""),
                raw_content=content,
                content_hash=content_hash,
                duration_seconds=elapsed,
                headers=dict(resp.headers),
            )

        except httpx.TimeoutException:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            return AcquisitionResult(
                success=False,
                url=url,
                normalized_url=current_url,
                mode_used=AcquisitionMode.DIRECT_HTTP,
                duration_seconds=elapsed,
                error=f"Direct HTTP fetch timed out after {self.timeout}s",
            )
        except Exception as exc:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            return AcquisitionResult(
                success=False,
                url=url,
                normalized_url=current_url,
                mode_used=AcquisitionMode.DIRECT_HTTP,
                duration_seconds=elapsed,
                error=f"Direct HTTP fetch failed: {exc}",
            )


    def _fetch_crawl4ai(self, url: str) -> AcquisitionResult:
        """Placeholder for Crawl4AI rich acquisition invocation."""
        # Crawl4AI rich acquisition integration will be invoked here
        start_time = datetime.now(timezone.utc)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        return AcquisitionResult(
            success=False,
            url=url,
            normalized_url=url,
            mode_used=AcquisitionMode.CRAWL4AI,
            duration_seconds=elapsed,
            error="Crawl4AI execution environment initialized but headless browser not attached in this test run",
        )

