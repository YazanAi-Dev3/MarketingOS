"""Market Scanner Pipeline for Marketing OS.

Orchestrates regional query planning, SearXNG discovery, SSRF-safe page acquisition,
source-adapter extraction, entity resolution, and SQLite persistence for Evidence,
Company, and Lead records.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import yaml

from marketing_plugin.adapters.acquisition_router import (
    AcquisitionRouter,
    compute_content_hash,
    is_ssrf_safe_url,
)
from marketing_plugin.adapters.bahr_adapter import BahrAdapter
from marketing_plugin.adapters.khamsat_adapter import KhamsatAdapter
from marketing_plugin.adapters.mostaql_adapter import MostaqlAdapter
from marketing_plugin.adapters.searxng_adapter import SearXNGAdapter
from marketing_plugin.policies.query_planner import RegionalQueryPlanner
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository
from marketing_plugin.services.entity_resolver import EntityResolver
from schemas.models import (
    AccessMode,
    Evidence,
    ExtractorType,
    FunnelType,
    Lead,
    LeadStatus,
    PriorityClass,
    Source,
    SourceStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "country-priorities.yaml"


@dataclass
class ScanRunSummary:
    """Structured outcome of a market scan execution."""
    country_code: str
    service_key: str
    queries_executed: int = 0
    discovered_urls: int = 0
    acquired_pages: int = 0
    created_companies: int = 0
    merged_companies: int = 0
    saved_evidence: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketScanner:
    """Orchestrates regional source discovery and lead ingestion pipeline."""

    def __init__(
        self,
        db: Optional[Database] = None,
        planner: Optional[RegionalQueryPlanner] = None,
        searxng_adapter: Optional[SearXNGAdapter] = None,
        acquisition_router: Optional[AcquisitionRouter] = None,
        entity_resolver: Optional[EntityResolver] = None,
        company_repo: Optional[CompanyRepository] = None,
        evidence_repo: Optional[EvidenceRepository] = None,
        lead_repo: Optional[LeadRepository] = None,
        source_repo: Optional[SourceRepository] = None,
        config_path: Optional[Path] = None,
        ssrf_validator: Optional[Any] = None,
    ) -> None:
        if db is not None:
            self.db = db
            conn = self.db.connect()
        else:
            self.db = Database("data/marketing.db")
            conn = self.db.connect()

        self.company_repo = company_repo or CompanyRepository(conn)
        self.evidence_repo = evidence_repo or EvidenceRepository(conn)
        self.lead_repo = lead_repo or LeadRepository(conn)
        self.source_repo = source_repo or SourceRepository(conn)

        self.entity_resolver = entity_resolver or EntityResolver(self.company_repo)
        self.planner = planner or RegionalQueryPlanner()
        self.searxng_adapter = searxng_adapter
        self.acquisition_router = acquisition_router or AcquisitionRouter()
        self.ssrf_validator = ssrf_validator or is_ssrf_safe_url
        self.config_path = config_path or DEFAULT_CONFIG_PATH

        # Specialized platform adapters
        self.bahr_adapter = BahrAdapter()
        self.mostaql_adapter = MostaqlAdapter()
        self.khamsat_adapter = KhamsatAdapter()

    def scan(
        self,
        country_code: str,
        service_key: Optional[str] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        urls: Optional[List[str]] = None,
        include_freelance_sources: bool = True,
    ) -> ScanRunSummary:
        """Executes a regional market scan pipeline and persists discovered evidence and leads."""
        code = country_code.strip().upper()
        active_service = service_key or "ai_automation"
        summary = ScanRunSummary(country_code=code, service_key=active_service)

        # 1. Ensure foreign key dependencies in SQLite are satisfied
        self._bootstrap_database_prerequisites(code, active_service)

        # 2. Query planning
        plan = self.planner.generate_plan(
            country_code=code,
            service_key=active_service,
            intent="market_scan",
        )

        planned_queries: List[str] = []
        if query:
            planned_queries.append(query)
        for q in plan.queries:
            if q not in planned_queries:
                planned_queries.append(q)

        if limit and limit > 0:
            active_queries = planned_queries[:limit]
        else:
            active_queries = planned_queries

        # 3. Discovery
        discovered_targets: List[Dict[str, Any]] = []

        # If explicit URLs are supplied (e.g. for targeted tests or manual scan runs)
        if urls:
            for u in urls:
                discovered_targets.append({
                    "url": u,
                    "title": "",
                    "snippet": "",
                    "source": "explicit",
                })
        else:
            # Execute SearXNG metasearch if configured
            if self.searxng_adapter is not None:
                for q in active_queries:
                    summary.queries_executed += 1
                    try:
                        search_res = self.searxng_adapter.search(query=q, country_code=code)
                        items = (
                            search_res.results
                            if hasattr(search_res, "results")
                            else list(search_res)
                        )
                        for it in items:
                            url = getattr(it, "url", None) or (
                                it.get("url") if isinstance(it, dict) else None
                            )
                            if url and not any(d["url"] == url for d in discovered_targets):
                                title = getattr(it, "title", "") or (
                                    it.get("title", "") if isinstance(it, dict) else ""
                                )
                                snippet = getattr(it, "snippet", "") or (
                                    it.get("snippet", "") if isinstance(it, dict) else ""
                                )
                                discovered_targets.append({
                                    "url": url,
                                    "title": title,
                                    "snippet": snippet,
                                    "source": "searxng",
                                })
                    except Exception as exc:
                        summary.errors.append(f"SearXNG error for '{q}': {exc}")

            # Collect regional freelance candidate discovery URLs
            if include_freelance_sources:
                search_term = query or (planned_queries[0] if planned_queries else active_service)
                # Bahr is Saudi-focused
                if code in ("SA", "KSA"):
                    bahr_url = self.bahr_adapter.build_search_url(search_term)
                    if not any(d["url"] == bahr_url for d in discovered_targets):
                        discovered_targets.append({
                            "url": bahr_url,
                            "title": "Bahr Project Search",
                            "snippet": "",
                            "source": "bahr",
                        })

                mostaql_url = self.mostaql_adapter.build_search_url(search_term)
                if not any(d["url"] == mostaql_url for d in discovered_targets):
                    discovered_targets.append({
                        "url": mostaql_url,
                        "title": "Mostaql Project Search",
                        "snippet": "",
                        "source": "mostaql",
                    })

                khamsat_url = self.khamsat_adapter.build_search_url(search_term)
                if not any(d["url"] == khamsat_url for d in discovered_targets):
                    discovered_targets.append({
                        "url": khamsat_url,
                        "title": "Khamsat Services Search",
                        "snippet": "",
                        "source": "khamsat",
                    })

        summary.discovered_urls = len(discovered_targets)

        # Apply limit to discovery processing if specified
        if limit and limit > 0 and len(discovered_targets) > limit:
            discovered_targets = discovered_targets[:limit]

        # 4. Acquisition & Extraction Loop
        for item in discovered_targets:
            target_url = item["url"]

            # SSRF validation check
            if not self.ssrf_validator(target_url):
                summary.errors.append(f"SSRF safety check failed: {target_url}")
                continue

            # Fetch page content
            try:
                acq_result = self.acquisition_router.route_acquisition(target_url)
            except Exception as exc:
                summary.errors.append(f"Acquisition exception for {target_url}: {exc}")
                continue

            if not acq_result.success:
                summary.errors.append(
                    f"Acquisition failed for {target_url}: {acq_result.error or 'Unknown error'}"
                )
                continue

            summary.acquired_pages += 1
            raw_html = acq_result.raw_content

            # Route to platform adapters or generic extractor
            parsed = urllib.parse.urlparse(target_url)
            netloc = parsed.netloc.lower()

            extracted_entities: List[Dict[str, Any]] = []

            if "bahr.sa" in netloc:
                source_id = "bahr"
                listings = self.bahr_adapter.extract_listings(raw_html)
                if not listings:
                    detail = self.bahr_adapter.extract_detail(raw_html)
                    if detail.get("title"):
                        listings = [detail]
                for rec in listings:
                    name = (
                        rec.get("author")
                        or rec.get("client")
                        or (f"Bahr - {rec.get('title', '')[:35]}" if rec.get("title") else "Bahr Client")
                    )
                    extracted_entities.append({
                        "canonical_name": name,
                        "primary_domain": None,
                        "source_id": source_id,
                        "url": rec.get("url") or target_url,
                        "fact_type": "freelance_listing",
                        "raw_record": rec,
                    })

            elif "mostaql.com" in netloc:
                source_id = "mostaql"
                listings = self.mostaql_adapter.extract_listings(raw_html)
                if not listings:
                    detail = self.mostaql_adapter.extract_detail(raw_html)
                    if detail.get("title"):
                        listings = [detail]
                for rec in listings:
                    name = (
                        rec.get("author")
                        or (f"Mostaql - {rec.get('title', '')[:35]}" if rec.get("title") else "Mostaql Client")
                    )
                    extracted_entities.append({
                        "canonical_name": name,
                        "primary_domain": None,
                        "source_id": source_id,
                        "url": rec.get("url") or target_url,
                        "fact_type": "freelance_listing",
                        "raw_record": rec,
                    })

            elif "khamsat.com" in netloc:
                source_id = "khamsat"
                listings = self.khamsat_adapter.extract_listings(raw_html)
                if not listings:
                    detail = self.khamsat_adapter.extract_detail(raw_html)
                    if detail.get("title"):
                        listings = [detail]
                for rec in listings:
                    name = (
                        rec.get("seller")
                        or rec.get("author")
                        or (f"Khamsat - {rec.get('title', '')[:35]}" if rec.get("title") else "Khamsat Seller")
                    )
                    extracted_entities.append({
                        "canonical_name": name,
                        "primary_domain": None,
                        "source_id": source_id,
                        "url": rec.get("url") or target_url,
                        "fact_type": "freelance_listing",
                        "raw_record": rec,
                    })

            else:
                # Generic web page extraction
                source_id = "searxng_web"
                generic_info = self._extract_generic_page(
                    url=target_url,
                    html=raw_html,
                    default_title=item.get("title", ""),
                )
                extracted_entities.append({
                    "canonical_name": generic_info["canonical_name"],
                    "primary_domain": generic_info["primary_domain"],
                    "city": generic_info.get("city"),
                    "public_contacts": generic_info.get("public_contacts"),
                    "source_id": source_id,
                    "url": target_url,
                    "fact_type": "web_page",
                    "raw_record": generic_info,
                })

            # 5. Entity Resolution and Storage
            for ent in extracted_entities:
                try:
                    # Resolve or create company
                    resolution = self.entity_resolver.resolve(
                        canonical_name=ent["canonical_name"],
                        country_code=code,
                        primary_domain=ent.get("primary_domain"),
                        city=ent.get("city"),
                        public_contacts=ent.get("public_contacts"),
                    )
                    resolved_company = resolution.company

                    if resolution.is_new:
                        summary.created_companies += 1
                    else:
                        summary.merged_companies += 1

                    # Save evidence
                    fact_text = self._build_fact_text(ent["raw_record"])
                    content_hash = compute_content_hash(fact_text)
                    evidence_id = f"evi_{ent['source_id']}_{content_hash[:16]}"
                    evidence = Evidence(
                        evidence_id=evidence_id,
                        company_id=resolved_company.company_id,
                        source_id=ent["source_id"],
                        url=ent["url"],
                        fact_type=ent["fact_type"],
                        fact_text=fact_text,
                        extractor=ExtractorType.DETERMINISTIC,
                        content_hash=content_hash,
                        confidence=1.0,
                        observed_at=utc_now(),
                    )
                    self.evidence_repo.save_evidence(evidence)
                    summary.saved_evidence += 1

                    # Save / ensure Lead exists in DISCOVERED status
                    lead_id = f"lead_{resolved_company.company_id}"
                    existing_lead = self.lead_repo.get_lead(lead_id)
                    if not existing_lead:
                        new_lead = Lead(
                            lead_id=lead_id,
                            company_id=resolved_company.company_id,
                            funnel=FunnelType.B2B,
                            status=LeadStatus.DISCOVERED,
                            priority_bucket=3,
                            recommended_service_key=active_service,
                            created_at=utc_now(),
                            updated_at=utc_now(),
                        )
                        self.lead_repo.save_lead(new_lead)
                except Exception as exc:
                    summary.errors.append(f"Storage error for {target_url}: {exc}")

        return summary

    # --- Internal Helpers ---

    def _bootstrap_database_prerequisites(self, country_code: str, service_key: str) -> None:
        """Ensures SQLite foreign key constraints (country, service, sources) are met."""
        conn = self.company_repo.conn

        # 1. Country profile
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM country_profiles WHERE country_code = ?;", (country_code,))
        if not cur.fetchone():
            weight = 1.0
            name = country_code
            langs = ["ar"]
            # Attempt to read weight from configuration file
            if self.config_path and Path(self.config_path).is_file():
                try:
                    cfg = yaml.safe_load(Path(self.config_path).read_text(encoding="utf-8"))
                    c_data = cfg.get("countries", {}).get(country_code, {})
                    if c_data.get("weight") is not None:
                        weight = float(c_data["weight"])
                    if c_data.get("name"):
                        name = c_data["name"]
                    if c_data.get("languages"):
                        langs = c_data["languages"]
                except Exception as exc:
                    logger.debug("Failed reading country-priorities config: %s", exc)

            conn.execute(
                """
                INSERT INTO country_profiles (country_code, name, languages, manual_weight, enabled)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(country_code) DO NOTHING;
                """,
                (country_code, name, json.dumps(langs), weight),
            )
            conn.commit()

        # 2. Service profile
        cur.execute("SELECT 1 FROM service_profiles WHERE service_key = ?;", (service_key,))
        if not cur.fetchone():
            conn.execute(
                """
                INSERT INTO service_profiles (service_key, priority_class, enabled, allowed_funnels, offer_summary)
                VALUES (?, 'primary', 1, '["b2b"]', ?)
                ON CONFLICT(service_key) DO NOTHING;
                """,
                (service_key, f"Service profile for {service_key}"),
            )
            conn.commit()

        # 3. Sources registry
        standard_sources = [
            ("searxng_web", "searxng", "search_engine"),
            ("bahr", "bahr.sa", "freelance_platform"),
            ("mostaql", "mostaql.com", "freelance_platform"),
            ("khamsat", "khamsat.com", "freelance_platform"),
        ]
        for s_id, domain, family in standard_sources:
            if not self.source_repo.get_source(s_id):
                src = Source(
                    source_id=s_id,
                    domain_or_platform_key=domain,
                    country_scope=["ALL"],
                    source_family=family,
                    languages=["ar", "en"],
                    status=SourceStatus.TRUSTED,
                    access_mode=AccessMode.PUBLIC,
                )
                self.source_repo.save_source(src)

    def _extract_generic_page(
        self,
        url: str,
        html: str,
        default_title: str = "",
    ) -> Dict[str, Any]:
        """Deterministic HTML parsing for generic company pages."""
        soup = BeautifulSoup(html, "html.parser")

        # Title extraction
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        elif default_title:
            title = default_title.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # Meta description
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()

        # Domain
        domain = EntityResolver.normalize_domain(url)

        # Derive clean canonical name
        canonical_name = ""
        if title:
            for sep in (" | ", " - ", " – ", " — ", " : "):
                if sep in title:
                    parts = [p.strip() for p in title.split(sep) if p.strip()]
                    if parts:
                        canonical_name = parts[0]
                    break
            if not canonical_name:
                canonical_name = title

        if not canonical_name and domain:
            canonical_name = domain.split(".")[0].capitalize()
        if not canonical_name:
            canonical_name = "Unknown Enterprise"

        # Regex email extraction
        emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)))
        valid_emails = [
            e for e in emails
            if not e.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css")
            )
        ]

        # Regex phone extraction
        raw_phones = list(set(re.findall(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", html
        )))
        valid_phones = [
            p.strip() for p in raw_phones if len(re.sub(r"\D", "", p)) >= 8
        ][:5]

        contacts: Dict[str, Any] = {}
        if valid_emails:
            contacts["email"] = valid_emails[0]
            contacts["emails"] = valid_emails[:3]
        if valid_phones:
            contacts["phone"] = valid_phones[0]
            contacts["phones"] = valid_phones[:3]

        return {
            "title": title,
            "description": meta_desc,
            "canonical_name": canonical_name,
            "primary_domain": domain,
            "public_contacts": contacts,
        }

    def _build_fact_text(self, raw_record: Dict[str, Any]) -> str:
        """Constructs factual text for immutable Evidence record (A-017)."""
        text_parts: List[str] = []
        if raw_record.get("title"):
            text_parts.append(f"Title: {raw_record['title']}")
        if raw_record.get("canonical_name"):
            text_parts.append(f"Company: {raw_record['canonical_name']}")
        if raw_record.get("primary_domain"):
            text_parts.append(f"Domain: {raw_record['primary_domain']}")
        if raw_record.get("description"):
            text_parts.append(f"Description: {raw_record['description']}")
        if raw_record.get("budget"):
            text_parts.append(f"Budget: {raw_record['budget']}")
        if raw_record.get("duration"):
            text_parts.append(f"Duration: {raw_record['duration']}")
        if raw_record.get("tags"):
            tags = raw_record["tags"]
            if isinstance(tags, list):
                text_parts.append(f"Tags: {', '.join(tags)}")
            else:
                text_parts.append(f"Tags: {tags}")
        if raw_record.get("public_contacts"):
            text_parts.append(
                f"Contacts: {json.dumps(raw_record['public_contacts'], ensure_ascii=False)}"
            )

        return "\n".join(text_parts) if text_parts else json.dumps(raw_record, ensure_ascii=False)
