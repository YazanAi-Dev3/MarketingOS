"""Mostaql Freelance Platform Adapter (mostaql.com).

Parses Crawl4AI-rendered HTML listings and project details from Mostaql.
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

BASE_URL = "https://mostaql.com"


class MostaqlAdapter(BaseSourceAdapter):
    """Specialized adapter for Mostaql (mostaql.com) freelance projects."""

    source_key: str = "mostaql"
    default_acquisition_mode: AcquisitionMode = AcquisitionMode.CRAWL4AI
    expected_domain: str = "mostaql.com"

    def build_search_url(self, query: str, page: int = 1) -> str:
        """Construct search URL for mostaql.com projects."""
        encoded_query = urllib.parse.quote_plus(query.strip())
        return f"{BASE_URL}/projects?keyword={encoded_query}&page={page}"

    def extract_listings(self, raw_html_or_payload: str) -> List[Dict[str, Any]]:
        """Extract project listings from Crawl4AI-rendered HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return []

        soup = BeautifulSoup(raw_text, "html.parser")
        items: List[Dict[str, Any]] = []

        # Find project rows/cards
        candidates = soup.select(
            "tr.project-row, div.project__card, li.project-item, div.project-item, "
            "table#projects-table tbody tr, div.card.project"
        )

        # Fallback if specific classes are not present
        if not candidates:
            links = soup.select("a[href*='/project/']")
            seen_containers = set()
            candidates = []
            for link in links:
                # Find enclosing row or div
                container = (
                    link.find_parent("tr")
                    or link.find_parent("li")
                    or link.find_parent("div", class_=lambda c: c and any(k in c for k in ("card", "item", "row")))
                    or link.find_parent("div")
                )
                if container and id(container) not in seen_containers:
                    seen_containers.add(id(container))
                    candidates.append(container)

        for el in candidates:
            # URL and Title
            link = el.select_one("a[href*='/project/']")
            if not link:
                continue
            href = link.get("href", "").strip()
            url = ""
            if href:
                joined = urllib.parse.urljoin(BASE_URL, href)
                if self.validate_url(joined):
                    url = joined

            title_el = el.select_one(".project__title, h2, h3") or link
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # Budget
            budget_el = el.select_one(".project__budget, .budget, span[class*='budget']")
            budget = budget_el.get_text(strip=True) if budget_el else ""

            # Duration
            duration_el = el.select_one(".project__duration, .duration, span[class*='duration']")
            duration = duration_el.get_text(strip=True) if duration_el else ""

            # Tags
            tag_els = el.select(".project__tags a, .project__tags span, .badge, .tag, a.label")
            tags = [t.get_text(strip=True) for t in tag_els if t.get_text(strip=True)]

            # Description
            desc_el = el.select_one(".project__brief, .project__desc, .project-desc, p.project__description, p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            items.append({
                "title": title,
                "budget": budget,
                "duration": duration,
                "tags": tags,
                "description": description,
                "url": url,
            })

        return items

    def extract_detail(self, raw_html_or_payload: str) -> Dict[str, Any]:
        """Extract project detail record from Mostaql detail HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return {}

        soup = BeautifulSoup(raw_text, "html.parser")

        title_el = soup.select_one("h1.project__title, h1, .page-header h1")
        title = title_el.get_text(strip=True) if title_el else ""

        budget_el = soup.select_one(".project__budget, .budget, span[class*='budget']")
        budget = budget_el.get_text(strip=True) if budget_el else ""

        duration_el = soup.select_one(".project__duration, .duration, span[class*='duration']")
        duration = duration_el.get_text(strip=True) if duration_el else ""

        tag_els = soup.select(".project__tags a, .project__tags span, .badge, .skills li")
        tags = [t.get_text(strip=True) for t in tag_els if t.get_text(strip=True)]

        desc_el = soup.select_one(".project__description, .project__brief, .card-body, article")
        description = desc_el.get_text(strip=True) if desc_el else ""

        canonical_elem = soup.find("link", rel="canonical")
        url = ""
        if canonical_elem and canonical_elem.get("href"):
            joined = urllib.parse.urljoin(BASE_URL, canonical_elem["href"].strip())
            if self.validate_url(joined):
                url = joined

        return {
            "title": title,
            "budget": budget,
            "duration": duration,
            "tags": tags,
            "description": description,
            "url": url,
        }
