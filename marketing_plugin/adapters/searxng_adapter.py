"""SearXNG Metasearch Adapter for Marketing OS.

Provides metasearch discovery abstraction according to A-016 and A-042.
Normalizes search results into SearchResult schemas, strips tracking params,
and handles network failures gracefully.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from schemas.models import SearchResult

logger = logging.getLogger(__name__)

DEFAULT_SEARXNG_URL = "http://localhost:8080"
DEFAULT_TIMEOUT_SECONDS = 15.0

# Country code to SearXNG language/locale mapping
COUNTRY_LOCALE_MAP: Dict[str, str] = {
    "SA": "ar-SA",
    "AE": "ar-AE",
    "QA": "ar-QA",
    "BH": "ar-BH",
    "OM": "ar-OM",
    "KW": "ar-KW",
    "SY": "ar-SY",
    "JO": "ar-JO",
    "LB": "ar-LB",
    "TR": "tr-TR",
}

# Tracking parameters to strip during URL normalization
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "yclid", "_ga", "_hsenc", "_hsmi"
}


@dataclass
class SearchRunResult:
    """Outcome of a SearXNG discovery run."""
    success: bool
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total_results: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


def normalize_url(raw_url: str) -> str:
    """Normalize URL by stripping tracking parameters, normalizing schemes, and removing redundant slashes."""
    try:
        parsed = urllib.parse.urlparse(raw_url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        # Strip default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Filter query params
        query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        cleaned_params = [
            (k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urllib.parse.urlencode(cleaned_params)

        # Normalize path
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        return urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception:
        return raw_url.strip()


class SearXNGAdapter:
    """Interacts with self-hosted or remote SearXNG metasearch instance."""

    def __init__(
        self,
        base_url: str = DEFAULT_SEARXNG_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def search(
        self,
        query: str,
        country_code: Optional[str] = None,
        language: Optional[str] = None,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        page: int = 1,
        search_run_id: str = "ad-hoc-run",
    ) -> SearchRunResult:
        """Execute a metasearch query against SearXNG returning normalized results."""
        endpoint = f"{self.base_url}/search"
        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": page,
        }

        # Localize search if country specified
        if language:
            params["language"] = language
        elif country_code and country_code.upper() in COUNTRY_LOCALE_MAP:
            params["language"] = COUNTRY_LOCALE_MAP[country_code.upper()]

        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)

        start_time = datetime.now(timezone.utc)

        try:
            client = self._get_client()
            resp = client.get(endpoint, params=params)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            if resp.status_code != 200:
                return SearchRunResult(
                    success=False,
                    query=query,
                    duration_seconds=elapsed,
                    error=f"SearXNG returned HTTP {resp.status_code}: {resp.text[:300]}",
                )

            data = resp.json()
            raw_results = data.get("results", [])
            normalized_results: List[SearchResult] = []

            for rank, item in enumerate(raw_results, start=1):
                url = item.get("url", "")
                if not url:
                    continue
                norm_url = normalize_url(url)
                title = item.get("title", "").strip()
                snippet = item.get("content", "").strip()
                engine_sources = item.get("engines", [])
                if isinstance(engine_sources, str):
                    engine_sources = [engine_sources]

                sr = SearchResult(
                    search_result_id=f"{search_run_id}-{rank:03d}",
                    search_run_id=search_run_id,
                    url=url,
                    normalized_url=norm_url,
                    title=title,
                    snippet=snippet,
                    rank=rank,
                    engine_sources=engine_sources,
                    discovered_at=datetime.now(timezone.utc),
                )
                normalized_results.append(sr)

            return SearchRunResult(
                success=True,
                query=query,
                results=normalized_results,
                total_results=len(normalized_results),
                duration_seconds=elapsed,
                raw_response=data,
            )

        except httpx.TimeoutException:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            return SearchRunResult(
                success=False,
                query=query,
                duration_seconds=elapsed,
                error=f"SearXNG search timed out after {self.timeout}s",
            )
        except Exception as exc:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            return SearchRunResult(
                success=False,
                query=query,
                duration_seconds=elapsed,
                error=f"SearXNG search failed: {exc}",
            )

