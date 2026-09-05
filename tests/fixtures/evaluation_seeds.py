"""Evaluation seed benchmarks and ground truth labels for Marketing OS.

Contains labeled benchmark sets for:
1. Source relevance classification
2. Evidence extraction expected entities
3. Entity merge / collision resolution
4. Lead priority ranking
5. Content grounding and hallucination check rubric
"""
from __future__ import annotations

from typing import Any, Dict, List

# 1. Source relevance evaluation labels
SOURCE_RELEVANCE_LABELS: Dict[str, str] = {
    "official_registry": "AUTHORITATIVE_DISCOVERY",
    "chamber_association": "SECTOR_MAPPING",
    "procurement_tenders": "HIGH_VALUE_BUYING_SIGNAL",
    "jobs_careers": "EXPANSION_SIGNAL",
    "business_directory": "CONTACT_DISCOVERY",
    "company_website": "PRIMARY_EVIDENCE",
    "business_news": "TREND_INTELLIGENCE",
    "public_social": "OPPORTUNITY_SIGNAL",
    "seo_spam": "REJECT_DEGRADED",
}

# 2. Evidence extraction expected facts per fixture
EVIDENCE_EXTRACTION_EXPECTED: Dict[str, Dict[str, Any]] = {
    "gcc-sa-01-clean-logistics": {
        "company_name": "شركة المسار السريع للخدمات اللوجستية",
        "city": "الرياض",
        "country": "SA",
        "pain_points": ["ضغط هائل في الرد على استفسارات تتبع الشحنات عبر الواتساب وخدمة العملاء"],
        "service_need": "أتمتة خدمة العملاء والربط مع نظام WMS",
        "contact_email": "operations@example-saudi-logistics.com",
        "contact_phone": "+966112345678",
    },
    "gcc-ae-02-hiring-fintech": {
        "company_name": "Apex Financial Technologies",
        "zone": "DIFC",
        "city": "Dubai",
        "country": "AE",
        "signal": "Hiring Head of AI Integration & Marketing Analytics",
        "initiatives": ["automated customer intake workflows", "lead scoring", "automated compliance reporting"],
        "budget_timeline": "Q4",
        "contact_email": "partnerships@apexfin.ae",
    },
    "levant-jo-01-academic-legitimate": {
        "institution": "مركز دراسات المياه والبيئة",
        "city": "عمان",
        "country": "JO",
        "task_type": "استشارة برمجية وتدريب على بايثون ونمذجة بيانات الأقمار الصناعية",
        "is_ethical": True,
    },
}

# 3. Entity merge / deduplication test cases
ENTITY_MERGE_LABELS: List[Dict[str, Any]] = [
    {
        "case_id": "clean_match_same_domain",
        "entity_a": {"name": "المسار السريع", "domain": "example-saudi-logistics.com", "country": "SA"},
        "entity_b": {"name": "شركة المسار السريع للخدمات اللوجستية", "domain": "example-saudi-logistics.com", "country": "SA"},
        "expected_action": "MERGE_HIGH_CONFIDENCE",
    },
    {
        "case_id": "ambiguous_name_different_countries",
        "entity_a": {"name": "Horizon Tech", "country": "SA", "phone": "+9661234567"},
        "entity_b": {"name": "Horizon Tech", "country": "LB", "phone": "+961123456"},
        "expected_action": "NO_MERGE_AMBIGUOUS_COLLISION",
    },
    {
        "case_id": "same_company_different_sources",
        "entity_a": {"name": "Apex Financial Tech", "domain": "apexfin.ae", "registry_cr": "DIFC-8891"},
        "entity_b": {"name": "Apex FinTech UAE", "domain": "apexfin.ae", "registry_cr": "DIFC-8891"},
        "expected_action": "MERGE_HIGH_CONFIDENCE",
    },
]

# 4. Lead priority ranking expectations
LEAD_PRIORITY_RANKING_LABELS: Dict[str, int] = {
    "gcc-sa-01-clean-logistics": 1,        # Urgent specific AI automation pain with contact
    "gcc-ae-02-hiring-fintech": 1,         # Expansion hiring with explicit budget and contact
    "levant-jo-01-academic-legitimate": 2, # Legitimate technical consulting with funding
    "security-edge-02-fake-secrets": 3,    # Valid company but needs secret sanitization
    "levant-sy-02-academic-violation": 5,  # Academic integrity violation -> Rejected
    "security-edge-01-prompt-injection": 5,# Prompt injection attempt -> Quarantined
    "spam-edge-01-seo-directory": 5,       # SEO spam -> Filtered
    "turkey-tr-01-clean-saas": 1,          # Clean B2B SaaS in Turkey with integration need
    "gcc-sa-01-dup-directory": 1,          # Directory listing matching clean logistics company
    "levant-jo-02-stale-hiring": 4,        # Archived/closed job posting -> Stale/Dormant
    "gcc-qa-02-tender-procurement": 1,     # High-value public procurement tender in Doha
    "north-africa-eg-01-clean-logistics": 1,# Clean B2B automation pain in Cairo, Egypt
}


# 5. Content grounding and anti-hallucination rubric
CONTENT_GROUNDING_RUBRIC: Dict[str, Any] = {
    "version": "1.0",
    "dimensions": {
        "evidence_citation": {
            "description": "Every specific market claim, customer quote, or pain point must cite a valid evidence ID.",
            "mandatory": True,
        },
        "brand_boundary": {
            "description": "Content must strictly reflect verified company capabilities in AI/automation without exaggerating SLA.",
            "mandatory": True,
        },
        "untrusted_content_isolation": {
            "description": "External scraped text must never bleed injection commands or prompt instructions into generated copy.",
            "mandatory": True,
        },
        "persisted_approval_required": {
            "description": "Content assets must not be queued for social publishing without explicit persisted human approval.",
            "mandatory": True,
        },
    },
}

