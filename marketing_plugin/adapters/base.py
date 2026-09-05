"""Base Source Adapter for Marketing OS Web Acquisition.

Defines the contract for specialized source adapters according to A-037/A-039.
"""
from __future__ import annotations

import json
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from marketing_plugin.adapters.acquisition_router import (
    AcquisitionMode,
    compute_content_hash,
)
from schemas.models import Evidence, ExtractorType, utc_now


class BaseSourceAdapter(ABC):
    """Abstract base class for all specialized source adapters."""

    source_key: str = "base"
    default_acquisition_mode: AcquisitionMode = AcquisitionMode.CRAWL4AI
    expected_domain: Optional[str] = None

    @abstractmethod
    def build_search_url(self, query: str, page: int = 1) -> str:
        """Construct the search URL for this source platform."""
        raise NotImplementedError

    @abstractmethod
    def extract_listings(self, raw_html_or_payload: str) -> List[Dict[str, Any]]:
        """Extract listing items from search result or directory page."""
        raise NotImplementedError

    @abstractmethod
    def extract_detail(self, raw_html_or_payload: str) -> Dict[str, Any]:
        """Extract full detail record from a single item page or payload."""
        raise NotImplementedError

    def validate_url(self, url: str) -> bool:
        """Validate that a URL has a valid http/https scheme and matches expected domain if set."""
        if not url or not isinstance(url, str):
            return False
        url_clean = url.strip()
        if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
            return False
        parsed = urllib.parse.urlparse(url_clean)
        if not parsed.netloc:
            return False
        if self.expected_domain:
            netloc = parsed.netloc.lower()
            expected = self.expected_domain.lower()
            if netloc != expected and not netloc.endswith("." + expected):
                return False
        return True

    def to_evidence(
        self,
        raw_record: Dict[str, Any],
        url: str,
        company_id: Optional[str] = None,
        fact_type: str = "freelance_listing",
    ) -> Evidence:
        """Convert an extracted record into a standardized Evidence model."""
        if not url or not isinstance(url, str):
            raise ValueError(f"Invalid URL: '{url}' must be a non-empty string")

        url_clean = url.strip()
        if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
            raise ValueError(
                f"Invalid URL scheme in '{url}': must start with http:// or https://"
            )

        parsed = urllib.parse.urlparse(url_clean)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL format in '{url}': missing network location/host")

        if self.expected_domain:
            netloc = parsed.netloc.lower()
            expected = self.expected_domain.lower()
            if netloc != expected and not netloc.endswith("." + expected):
                raise ValueError(
                    f"URL domain '{netloc}' does not match expected platform domain '{expected}'"
                )

        text_parts: List[str] = []
        if raw_record.get("title"):
            text_parts.append(f"Title: {raw_record['title']}")
        if raw_record.get("budget"):
            text_parts.append(f"Budget: {raw_record['budget']}")
        if raw_record.get("duration"):
            text_parts.append(f"Duration: {raw_record['duration']}")
        if raw_record.get("author"):
            text_parts.append(f"Author: {raw_record['author']}")
        if raw_record.get("tags"):
            tags = raw_record["tags"]
            if isinstance(tags, list):
                text_parts.append(f"Tags: {', '.join(tags)}")
            else:
                text_parts.append(f"Tags: {tags}")
        if raw_record.get("description"):
            text_parts.append(f"Description: {raw_record['description']}")

        fact_text = "\n".join(text_parts) if text_parts else json.dumps(raw_record, ensure_ascii=False)
        content_hash = compute_content_hash(fact_text)
        evidence_id = f"evi_{self.source_key}_{content_hash[:16]}"

        return Evidence(
            evidence_id=evidence_id,
            company_id=company_id,
            source_id=self.source_key,
            url=url_clean,
            fact_type=fact_type,
            fact_text=fact_text,
            extractor=ExtractorType.DETERMINISTIC,
            content_hash=content_hash,
            confidence=1.0,
            observed_at=utc_now(),
        )
