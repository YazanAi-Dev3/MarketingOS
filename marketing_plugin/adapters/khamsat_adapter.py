"""Khamsat Platform Adapter (khamsat.com).

Parses Crawl4AI-rendered HTML listings for community project requests from Khamsat.
Revalidated under T-09: AWS ALB/WAF returns 403 Forbidden to direct HTTP;
requires Crawl4AI rich acquisition mode with browser stealth/headers.
"""
from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List
from bs4 import BeautifulSoup

from marketing_plugin.adapters.acquisition_router import AcquisitionMode
from marketing_plugin.adapters.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://khamsat.com"


class KhamsatAdapter(BaseSourceAdapter):
    """Specialized adapter for Khamsat (khamsat.com) community requests."""

    source_key: str = "khamsat"
    default_acquisition_mode: AcquisitionMode = AcquisitionMode.CRAWL4AI
    expected_domain: str = "khamsat.com"

    def build_search_url(self, query: str, page: int = 1) -> str:
        """Construct search URL for khamsat.com community requests."""
        encoded_query = urllib.parse.quote_plus(query.strip())
        return f"{BASE_URL}/community/requests?keyword={encoded_query}&page={page}"

    def extract_listings(self, raw_html_or_payload: str) -> List[Dict[str, Any]]:
        """Extract community request listings from Crawl4AI-rendered HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return []

        soup = BeautifulSoup(raw_text, "html.parser")
        items: List[Dict[str, Any]] = []

        # Find rows/cards in community requests table or list
        candidates = soup.select(
            "tr.community-request, table.table-community tbody tr, "
            "div.community-request, div.request-item, tr.forum-topic, article"
        )

        # Fallback if specific classes are not present
        if not candidates:
            links = soup.select("a[href*='/community/requests/']")
            seen_containers = set()
            candidates = []
            for link in links:
                container = (
                    link.find_parent("tr")
                    or link.find_parent("li")
                    or link.find_parent("div", class_=lambda c: c and any(k in c for k in ("item", "row", "card")))
                    or link.find_parent("div")
                )
                if container and id(container) not in seen_containers:
                    seen_containers.add(id(container))
                    candidates.append(container)

        for el in candidates:
            link = el.select_one("a[href*='/community/requests/']")
            if not link:
                continue

            href = link.get("href", "").strip()
            url = ""
            if href:
                joined = urllib.parse.urljoin(BASE_URL, href)
                if self.validate_url(joined):
                    url = joined

            title = link.get_text(strip=True)
            if not title:
                continue

            # Author
            author_el = el.select_one("a[href*='/user/'], td.author a, .author-name, .author, .user-details a")
            author = author_el.get_text(strip=True) if author_el else ""

            # Description / excerpt
            desc_el = el.select_one(".details p, p.description, .excerpt, p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            items.append({
                "title": title,
                "author": author,
                "description": description,
                "url": url,
            })

        return items

    def extract_detail(self, raw_html_or_payload: str) -> Dict[str, Any]:
        """Extract community request detail from Khamsat HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return {}

        soup = BeautifulSoup(raw_text, "html.parser")

        title_el = soup.select_one("h1.title, h1, .page-header h1")
        title = title_el.get_text(strip=True) if title_el else ""

        author_el = soup.select_one("a[href*='/user/'], .author-name, .details-user, .user-name")
        author = author_el.get_text(strip=True) if author_el else ""

        desc_el = soup.select_one(".details-body, .content, .post-content, .card-text, article")
        description = desc_el.get_text(strip=True) if desc_el else ""

        canonical_elem = soup.find("link", rel="canonical")
        url = ""
        if canonical_elem and canonical_elem.get("href"):
            joined = urllib.parse.urljoin(BASE_URL, canonical_elem["href"].strip())
            if self.validate_url(joined):
                url = joined

        return {
            "title": title,
            "author": author,
            "description": description,
            "url": url,
        }
