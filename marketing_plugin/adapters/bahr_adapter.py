"""Bahr Freelance Platform Adapter (bahr.sa).

Handles Next.js App Router SPA / API extraction for Saudi freelance platform Bahr.
Revalidated under T-09: bahr.910ths.sa is dead; active platform is bahr.sa.
Requires Crawl4AI rich acquisition mode for live dynamic SPA rendering.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from marketing_plugin.adapters.acquisition_router import AcquisitionMode
from marketing_plugin.adapters.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://bahr.sa"


class BahrAdapter(BaseSourceAdapter):
    """Specialized adapter for Bahr (bahr.sa) freelance projects."""

    source_key: str = "bahr"
    default_acquisition_mode: AcquisitionMode = AcquisitionMode.CRAWL4AI
    expected_domain: str = "bahr.sa"

    def build_search_url(self, query: str, page: int = 1) -> str:
        """Construct the search URL for bahr.sa projects."""
        encoded_query = urllib.parse.quote_plus(query.strip())
        return f"{BASE_URL}/projects?search={encoded_query}&page={page}"

    def extract_listings(self, raw_html_or_payload: str) -> List[Dict[str, Any]]:
        """Extract project listings from either Next.js JSON payload or rendered HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return []

        # 1. Try parsing as direct JSON payload (e.g. Next.js API route or Server Component payload)
        if (raw_text.startswith("{") and raw_text.endswith("}")) or (
            raw_text.startswith("[") and raw_text.endswith("]")
        ):
            try:
                data = json.loads(raw_text)
                return self._parse_json_listings(data)
            except json.JSONDecodeError:
                pass

        # 2. Parse as HTML
        soup = BeautifulSoup(raw_text, "html.parser")

        # Check for embedded __NEXT_DATA__
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                next_json = json.loads(next_data_tag.string)
                results = self._parse_json_listings(next_json)
                if results:
                    return results
            except json.JSONDecodeError:
                pass

        # Parse DOM elements
        return self._parse_html_listings(soup)

    def extract_detail(self, raw_html_or_payload: str) -> Dict[str, Any]:
        """Extract project detail record from either JSON payload or detail HTML."""
        raw_text = raw_html_or_payload.strip()
        if not raw_text:
            return {}

        # 1. Try parsing as JSON
        if (raw_text.startswith("{") and raw_text.endswith("}")):
            try:
                data = json.loads(raw_text)
                return self._parse_json_detail(data)
            except json.JSONDecodeError:
                pass

        # 2. Parse as HTML
        soup = BeautifulSoup(raw_text, "html.parser")

        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                next_json = json.loads(next_data_tag.string)
                item = self._parse_json_detail(next_json)
                if item.get("title"):
                    return item
            except json.JSONDecodeError:
                pass

        return self._parse_html_detail(soup)

    # --- Private Helpers ---

    def _parse_json_listings(self, data: Any) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        raw_list: List[Dict[str, Any]] = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            # Probe common Next.js / API payload keys
            for key in ("projects", "items", "results", "data"):
                if key in data and isinstance(data[key], list):
                    raw_list = data[key]
                    break
            if not raw_list:
                # Check Next.js pageProps directly or under props
                page_props = data.get("pageProps") or data.get("props", {}).get("pageProps", {})
                if isinstance(page_props, dict):
                    for key in ("projects", "items", "results", "data"):
                        if key in page_props and isinstance(page_props[key], list):
                            raw_list = page_props[key]
                            break

        for item in raw_list:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue

            budget = str(item.get("budget") or item.get("price") or item.get("expected_budget") or "").strip()
            duration = str(item.get("duration") or item.get("execution_period") or item.get("period") or "").strip()

            raw_tags = item.get("tags") or item.get("skills") or []
            if isinstance(raw_tags, str):
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(t).strip() for t in raw_tags if str(t).strip()]
            else:
                tags = []

            description = str(item.get("description") or item.get("summary") or item.get("details") or "").strip()

            url = str(item.get("url") or "").strip()
            if not url and item.get("id"):
                url = f"{BASE_URL}/projects/{item['id']}"
            elif url and not (url.startswith("http://") or url.startswith("https://")):
                url = urllib.parse.urljoin(BASE_URL, url)
            if not self.validate_url(url):
                url = f"{BASE_URL}/projects/{item['id']}" if item.get("id") else ""

            items.append({
                "title": title,
                "budget": budget,
                "duration": duration,
                "tags": tags,
                "description": description,
                "url": url,
            })

        return items

    def _parse_html_listings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        # Look for cards or project articles
        cards = soup.select(
            "div.project-card, article.project, div[data-testid='project-card'], "
            ".project-item, .card.project, article"
        )

        # Fallback: if no dedicated cards matched, look for container elements around /projects/ links
        if not cards:
            project_links = soup.select("a[href*='/projects/']")
            seen_containers = set()
            cards = []
            for link in project_links:
                container = link.find_parent("div", class_=lambda c: c and "card" in c) or link.find_parent("div")
                if container and id(container) not in seen_containers:
                    seen_containers.add(id(container))
                    cards.append(container)

        for card in cards:
            link_elem = card.select_one("a[href*='/projects/']") or card.find("a")
            url = ""
            if link_elem and link_elem.get("href"):
                joined = urllib.parse.urljoin(BASE_URL, link_elem["href"].strip())
                if self.validate_url(joined):
                    url = joined

            title_elem = (
                card.select_one("h2, h3, h4, .project-title, .title")
                or link_elem
            )
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                continue

            budget_elem = card.select_one(".project-budget, .budget, span[class*='budget']")
            budget = budget_elem.get_text(strip=True) if budget_elem else ""

            duration_elem = card.select_one(".project-duration, .duration, span[class*='duration']")
            duration = duration_elem.get_text(strip=True) if duration_elem else ""

            tag_elems = card.select(".tag, .badge, .skill, .tags span, span[class*='tag']")
            tags = [t.get_text(strip=True) for t in tag_elems if t.get_text(strip=True)]

            desc_elem = card.select_one(".project-description, .description, p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            items.append({
                "title": title,
                "budget": budget,
                "duration": duration,
                "tags": tags,
                "description": description,
                "url": url,
            })

        return items

    def _parse_json_detail(self, data: Dict[str, Any]) -> Dict[str, Any]:
        item = data
        if "project" in data and isinstance(data["project"], dict):
            item = data["project"]
        elif "data" in data and isinstance(data["data"], dict):
            item = data["data"]

        title = str(item.get("title") or "").strip()
        budget = str(item.get("budget") or item.get("price") or "").strip()
        duration = str(item.get("duration") or item.get("period") or "").strip()
        raw_tags = item.get("tags") or item.get("skills") or []
        tags = [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
        description = str(item.get("description") or item.get("details") or "").strip()
        url = str(item.get("url") or "").strip()
        if not url and "id" in item:
            url = f"{BASE_URL}/projects/{item['id']}"
        elif url and not (url.startswith("http://") or url.startswith("https://")):
            url = urllib.parse.urljoin(BASE_URL, url)
        if not self.validate_url(url):
            url = f"{BASE_URL}/projects/{item['id']}" if "id" in item else ""

        return {
            "title": title,
            "budget": budget,
            "duration": duration,
            "tags": tags,
            "description": description,
            "url": url,
        }

    def _parse_html_detail(self, soup: BeautifulSoup) -> Dict[str, Any]:
        title_elem = soup.select_one("h1, .project-title, .title")
        title = title_elem.get_text(strip=True) if title_elem else ""

        budget_elem = soup.select_one(".project-budget, .budget, span[class*='budget']")
        budget = budget_elem.get_text(strip=True) if budget_elem else ""

        duration_elem = soup.select_one(".project-duration, .duration, span[class*='duration']")
        duration = duration_elem.get_text(strip=True) if duration_elem else ""

        tag_elems = soup.select(".tag, .badge, .skill, .tags span, .skills li")
        tags = [t.get_text(strip=True) for t in tag_elems if t.get_text(strip=True)]

        desc_elem = soup.select_one(".project-description, .description, article p, .project-details")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

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
