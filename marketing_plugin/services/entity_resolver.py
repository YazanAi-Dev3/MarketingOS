"""Entity Resolver and Identity Deduplication Engine for Marketing OS.

Implements canonical root domain normalization, multi-lingual company name cleaning
(Arabic, English, Turkish), non-destructive identity resolution against CompanyRepository,
and deterministic confidence scoring per docs/02-technical-design-spec.md:130.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marketing_plugin.repositories.company_repo import CompanyRepository
from schemas.models import Company, FunnelType, utc_now

logger = logging.getLogger(__name__)

# Known regional and global two-part (second-level) ccTLDs
SECOND_LEVEL_TLDS: Set[str] = {
    # Saudi Arabia
    "com.sa", "org.sa", "gov.sa", "edu.sa", "net.sa", "med.sa", "pub.sa",
    # United Arab Emirates
    "co.ae", "com.ae", "net.ae", "gov.ae", "ac.ae", "org.ae",
    # Qatar
    "com.qa", "edu.qa", "gov.qa", "net.qa", "org.qa",
    # Syria
    "com.sy", "edu.sy", "gov.sy", "net.sy", "org.sy",
    # Turkey
    "com.tr", "edu.tr", "gov.tr", "org.tr", "net.tr", "biz.tr", "info.tr", "av.tr", "dr.tr", "bel.tr",
    # Bahrain
    "com.bh", "edu.bh", "gov.bh", "net.bh", "org.bh",
    # Oman
    "co.om", "com.om", "edu.om", "gov.om", "net.om", "org.om",
    # Jordan
    "com.jo", "edu.jo", "gov.jo", "net.jo", "org.jo",
    # Lebanon
    "com.lb", "edu.lb", "gov.lb", "net.lb", "org.lb",
    # United Kingdom & Commonwealth
    "co.uk", "org.uk", "gov.uk", "ac.uk", "net.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "net.nz", "org.nz",
    # Egypt
    "com.eg", "edu.eg", "gov.eg", "net.eg", "org.eg",
}


@dataclass
class ResolutionOutcome:
    """Detailed outcome of an identity resolution decision."""
    company: Company
    confidence: float
    is_new: bool
    match_type: str  # "exact_domain", "verified_contact", "exact_name", "created_new"

    @property
    def company_id(self) -> str:
        return self.company.company_id


class EntityResolver:
    """Resolves and deduplicates company entities against the repository.

    Hierarchy of identity resolution:
    1. Exact primary domain match (Confidence 1.0)
    2. Shared verified contact (email or phone) (Confidence 0.90)
    3. Exact normalized name + same country_code (Confidence 0.85)
    4. Ambiguous / no match -> creates new Company entity with entity_confidence.

    All resolution operations are non-destructive: distinct entities are preserved,
    ambiguous merges are rejected, and existing properties are enriched rather than overwritten.
    """

    def __init__(self, company_repo: CompanyRepository) -> None:
        self.company_repo = company_repo

    @staticmethod
    def normalize_domain(url_or_domain: Optional[str]) -> Optional[str]:
        """Extract canonical root domain from URL or domain string.

        Examples:
            'https://www.example.com/page?ref=1' -> 'example.com'
            'm.sub.domain.sa:8080' -> 'domain.sa'
            'https://blog.startup.com.sa/contact' -> 'startup.com.sa'
            'http://localhost:8000' -> 'localhost'
            '192.168.1.1:8080' -> '192.168.1.1'
        """
        if not url_or_domain:
            return "" if url_or_domain == "" else None

        raw = str(url_or_domain).strip()
        if not raw:
            return ""

        # Handle scheme if present
        if "://" in raw or raw.startswith("//"):
            parsed = urllib.parse.urlparse(raw)
            netloc = parsed.netloc or parsed.path.split("/")[0]
        else:
            # Treat as netloc with optional path
            parsed = urllib.parse.urlparse(f"http://{raw}")
            netloc = parsed.netloc or parsed.path.split("/")[0]

        # Strip port and credentials if present
        if "@" in netloc:
            netloc = netloc.split("@")[-1]
        if ":" in netloc:
            netloc = netloc.split(":")[0]

        host = netloc.strip().lower().rstrip(".")
        if not host:
            return ""

        # Check if IPv4 address
        parts = host.split(".")
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return host

        # Single word hostname (e.g. localhost)
        if len(parts) <= 1:
            return host

        # Two-part domain (e.g. example.com or domain.sa)
        if len(parts) == 2:
            return host

        # Three or more parts: check against known second-level TLDs
        last_two = f"{parts[-2]}.{parts[-1]}"
        if last_two in SECOND_LEVEL_TLDS:
            # Suffix has two labels, take the preceding label as well
            return f"{parts[-3]}.{last_two}"

        # Standard TLD (e.g. com, net, org, sa, ae): take last two parts
        return f"{parts[-2]}.{parts[-1]}"

    @staticmethod
    def normalize_company_name(name: Optional[str]) -> str:
        """Normalizes company name across Arabic, English, and Turkish.

        Performs:
        - Arabic: alef normalization ('أ/إ/آ/ٱ' -> 'ا'), teh marbuta ('ة' -> 'ه'),
          harakat/tatweel stripping, and stripping corporate forms ('شركة', 'مؤسسة', 'ذ.م.م', etc.).
        - English: strips corporate suffixes ('LLC', 'Inc', 'Ltd', 'Co.', 'Corp', etc.).
        - Turkish: strips Turkish corporate suffixes ('A.Ş.', 'Ltd. Şti.', 'Anonim Şirketi', etc.).
        """
        if not name:
            return ""

        text = str(name).strip()
        if not text:
            return ""

        # 1. Arabic character normalization
        # Remove harakat (tashkeel)
        text = re.sub(r"[\u064B-\u0652\u0670]", "", text)
        # Remove tatweel (kashida)
        text = re.sub(r"\u0640", "", text)
        # Alef forms to bare alef
        text = re.sub(r"[أإآٱ]", "ا", text)
        # Teh marbuta to heh
        text = re.sub(r"ة", "ه", text)

        # 2. Turkish-aware lowercasing
        text = text.replace("İ", "i").replace("I", "ı").lower()

        # 3. Strip Turkish corporate forms
        turkish_patterns = [
            r"\bltd\.?\s*şti\.?\b",
            r"\bltd\.?\s*sti\.?\b",
            r"\ba\.?ş\.?\b",
            r"\ba\.?s\.?\b",
            r"\banonim\s+şirketi\b",
            r"\blimited\s+şirketi\b",
            r"\bşirketi\b",
            r"\bsirketi\b",
        ]
        for pat in turkish_patterns:
            text = re.sub(pat, " ", text, flags=re.IGNORECASE)

        # 4. Strip English corporate forms
        english_patterns = [
            r"\bl\.?l\.?c\.?\b",
            r"\binc\.?\b",
            r"\bltd\.?\b",
            r"\bcorp\.?\b",
            r"\bcorporation\b",
            r"\bcompany\b",
            r"\blimited\b",
            r"\bplc\.?\b",
            r"\bco\.?\b",
        ]
        for pat in english_patterns:
            text = re.sub(pat, " ", text, flags=re.IGNORECASE)

        # 5. Strip Arabic corporate forms
        # Suffixes
        arabic_suffix_patterns = [
            r"\bذ\.?م\.?م\.?\b",
            r"\bش\.?م\.?م\.?\b",
            r"\bش\.?م\.?ع\.?\b",
            r"\bمساهمه\s+مقفله\b",
            r"\bمساهمه\s+عامه\b",
        ]
        for pat in arabic_suffix_patterns:
            text = re.sub(pat, " ", text)

        # Prefixes (applied after teh marbuta has been converted to 'ه')
        arabic_prefix_patterns = [
            r"^\s*شركه\s+",
            r"^\s*مؤسسه\s+",
            r"^\s*مجموعه\s+",
            r"^\s*وكاله\s+",
            r"^\s*مكتب\s+",
        ]
        for pat in arabic_prefix_patterns:
            text = re.sub(pat, "", text)

        # 6. Remove punctuation and collapse whitespace
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        cleaned = " ".join(text.split()).strip()

        # Fallback if stripping removed everything
        if not cleaned:
            fallback = re.sub(r"[^\w\s]", " ", name).strip()
            return " ".join(fallback.split()).lower()

        return cleaned

    def resolve(
        self,
        canonical_name: str,
        country_code: str,
        primary_domain: Optional[str] = None,
        city: Optional[str] = None,
        sector: Optional[str] = None,
        public_contacts: Optional[Dict[str, Any]] = None,
        public_contacts_json: Optional[Dict[str, Any]] = None,
        funnel: FunnelType = FunnelType.B2B,
        entity_confidence: Optional[float] = None,
    ) -> ResolutionOutcome:
        """Resolve identity and return comprehensive ResolutionOutcome."""
        contacts = public_contacts or public_contacts_json or {}
        country = country_code.strip().upper()
        norm_domain = self.normalize_domain(primary_domain) if primary_domain else None
        clean_input_name = self.normalize_company_name(canonical_name)

        # --- Rule 1: Exact Primary Domain Match (Confidence 1.0) ---
        if norm_domain:
            existing_by_domain = self.company_repo.find_by_domain(norm_domain)
            if existing_by_domain:
                # Merge / enrich non-destructively
                self._enrich_company(existing_by_domain, city=city, sector=sector, contacts=contacts)
                existing_by_domain.entity_confidence = 1.0
                self.company_repo.save_company(existing_by_domain)

                existing_by_domain._is_new = False
                existing_by_domain._match_type = "exact_domain"
                return ResolutionOutcome(
                    company=existing_by_domain,
                    confidence=1.0,
                    is_new=False,
                    match_type="exact_domain",
                )

        # --- Rule 2: Shared Verified Contact (Confidence 0.90) ---
        contact_match = self._find_by_contacts(contacts)
        if contact_match:
            # If both have explicit distinct primary domains, do not merge blindly
            if (
                norm_domain
                and contact_match.primary_domain
                and norm_domain != contact_match.primary_domain
            ):
                logger.info(
                    "Contact match found but distinct primary domains (%s vs %s); rejecting destructive merge.",
                    norm_domain,
                    contact_match.primary_domain,
                )
            else:
                self._enrich_company(
                    contact_match,
                    primary_domain=norm_domain,
                    city=city,
                    sector=sector,
                    contacts=contacts,
                )
                self.company_repo.save_company(contact_match)

                contact_match._is_new = False
                contact_match._match_type = "verified_contact"
                return ResolutionOutcome(
                    company=contact_match,
                    confidence=0.90,
                    is_new=False,
                    match_type="verified_contact",
                )

        # --- Rule 3: Exact Normalized Name + Same Country Code (Confidence 0.85) ---
        if clean_input_name:
            cur = self.company_repo.conn.cursor()
            cur.execute(
                "SELECT * FROM companies WHERE country_code = ? ORDER BY entity_confidence DESC;",
                (country,),
            )
            candidates = [self.company_repo._row_to_company(row) for row in cur.fetchall()]

            for cand in candidates:
                cand_clean_name = self.normalize_company_name(cand.canonical_name)
                if cand_clean_name == clean_input_name:
                    # Non-destructive check: if both have distinct primary domains, do NOT merge
                    if (
                        norm_domain
                        and cand.primary_domain
                        and norm_domain != cand.primary_domain
                    ):
                        logger.info(
                            "Name match for '%s' but distinct domains (%s vs %s); preserving distinct entities.",
                            clean_input_name,
                            norm_domain,
                            cand.primary_domain,
                        )
                        continue

                    # Confirmed match
                    self._enrich_company(
                        cand,
                        primary_domain=norm_domain,
                        city=city,
                        sector=sector,
                        contacts=contacts,
                    )
                    self.company_repo.save_company(cand)

                    cand._is_new = False
                    cand._match_type = "exact_name"
                    return ResolutionOutcome(
                        company=cand,
                        confidence=0.85,
                        is_new=False,
                        match_type="exact_name",
                    )

        # --- Rule 4: Ambiguous / No Match -> Create New Company ---
        assigned_conf = entity_confidence if entity_confidence is not None else 1.0
        new_company_id = f"comp_{uuid.uuid4().hex[:12]}"
        now = utc_now()

        new_company = Company(
            company_id=new_company_id,
            canonical_name=canonical_name.strip(),
            primary_domain=norm_domain,
            country_code=country,
            city=city.strip() if city else None,
            sector=sector.strip() if sector else None,
            public_contacts_json=contacts,
            funnel=funnel,
            entity_confidence=assigned_conf,
            created_at=now,
            updated_at=now,
        )
        self.company_repo.save_company(new_company)

        new_company._is_new = True
        new_company._match_type = "created_new"
        return ResolutionOutcome(
            company=new_company,
            confidence=assigned_conf,
            is_new=True,
            match_type="created_new",
        )

    def resolve_company(
        self,
        canonical_name: str,
        country_code: str,
        primary_domain: Optional[str] = None,
        city: Optional[str] = None,
        sector: Optional[str] = None,
        public_contacts: Optional[Dict[str, Any]] = None,
        public_contacts_json: Optional[Dict[str, Any]] = None,
        funnel: FunnelType = FunnelType.B2B,
        entity_confidence: Optional[float] = None,
        return_details: bool = False,
    ) -> Union[Company, ResolutionOutcome]:
        """Resolves company identity and returns either Company or ResolutionOutcome.

        By default returns the Company entity (existing or newly created) with
        ._is_new and ._match_type attributes set for caller convenience.
        """
        outcome = self.resolve(
            canonical_name=canonical_name,
            country_code=country_code,
            primary_domain=primary_domain,
            city=city,
            sector=sector,
            public_contacts=public_contacts,
            public_contacts_json=public_contacts_json,
            funnel=funnel,
            entity_confidence=entity_confidence,
        )
        if return_details:
            return outcome
        return outcome.company

    # --- Private Helpers ---

    def _find_by_contacts(self, contacts: Dict[str, Any]) -> Optional[Company]:
        """Search company repository for shared verified email or phone."""
        target_emails, target_phones = self._extract_contact_identifiers(contacts)
        if not target_emails and not target_phones:
            return None

        cur = self.company_repo.conn.cursor()
        cur.execute(
            "SELECT * FROM companies WHERE public_contacts_json != '{}' AND public_contacts_json IS NOT NULL;"
        )
        for row in cur.fetchall():
            cand = self.company_repo._row_to_company(row)
            cand_emails, cand_phones = self._extract_contact_identifiers(cand.public_contacts_json)

            # Check email overlap
            if target_emails.intersection(cand_emails):
                return cand
            # Check phone overlap
            if target_phones.intersection(cand_phones):
                return cand

        return None

    @staticmethod
    def _extract_contact_identifiers(contacts: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
        """Extract set of normalized emails and phones from contacts dict."""
        emails: Set[str] = set()
        phones: Set[str] = set()

        if not contacts or not isinstance(contacts, dict):
            return emails, phones

        # Check emails
        for key in ("email", "emails", "contact_email", "mail"):
            val = contacts.get(key)
            if isinstance(val, str) and "@" in val:
                clean_e = val.strip().lower()
                if len(clean_e) > 5:
                    emails.add(clean_e)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, str) and "@" in v:
                        clean_e = v.strip().lower()
                        if len(clean_e) > 5:
                            emails.add(clean_e)

        # Check phones
        for key in ("phone", "phones", "mobile", "tel", "whatsapp"):
            val = contacts.get(key)
            if isinstance(val, str):
                digits = re.sub(r"[^\d+]", "", val.strip())
                if len(digits) >= 8:
                    phones.add(digits)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, str):
                        digits = re.sub(r"[^\d+]", "", v.strip())
                        if len(digits) >= 8:
                            phones.add(digits)

        return emails, phones

    @staticmethod
    def _enrich_company(
        company: Company,
        primary_domain: Optional[str] = None,
        city: Optional[str] = None,
        sector: Optional[str] = None,
        contacts: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Non-destructively enrich missing fields on an existing company."""
        if not company.primary_domain and primary_domain:
            company.primary_domain = primary_domain
        if not company.city and city:
            company.city = city.strip()
        if not company.sector and sector:
            company.sector = sector.strip()

        if contacts and isinstance(contacts, dict):
            merged = dict(company.public_contacts_json or {})
            for k, v in contacts.items():
                if k not in merged or not merged[k]:
                    merged[k] = v
                elif isinstance(merged[k], list) and isinstance(v, list):
                    merged[k] = list(set(merged[k] + v))
            company.public_contacts_json = merged

        company.updated_at = utc_now()
