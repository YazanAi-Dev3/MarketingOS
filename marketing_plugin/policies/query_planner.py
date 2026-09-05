"""Regional Query Planner for Marketing OS.

Generates intent-driven, multilingual, regionalized search query plans
according to A-015 and HLD Section 3.4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from schemas.models import FunnelType, PriorityClass


@dataclass
class QueryPlan:
    """A generated multi-query search plan for a specific region and service."""
    intent: str
    country_code: str
    funnel: FunnelType
    service_key: str
    queries: List[str] = field(default_factory=list)
    language_target: str = "ar"
    categories: List[str] = field(default_factory=lambda: ["general"])


# Regional terminology lexicons
COUNTRY_LOCALIZATIONS: Dict[str, Dict[str, Any]] = {
    "SA": {
        "primary_lang": "ar",
        "cities": ["الرياض", "جدة", "الدمام", "الخبر"],
        "entity_terms": ["شركة", "مؤسسة", "منصة", "تطبيق"],
        "tender_terms": ["منافسة", "مناقصة", "طلب عروض", "مشروع أتمتة"],
        "job_terms": ["مطلوب مطور", "توظيف ذكاء اصطناعي", "مهندس بيانات"],
    },
    "AE": {
        "primary_lang": "en",
        "cities": ["Dubai", "Abu Dhabi", "Sharjah"],
        "entity_terms": ["company", "LLC", "Fintech", "logistics"],
        "tender_terms": ["RFP", "tender", "procurement", "AI integration"],
        "job_terms": ["hiring AI", "hiring automation engineer", "tech lead"],
    },
    "QA": {
        "primary_lang": "ar",
        "cities": ["الدوحة", "لوسيل"],
        "entity_terms": ["شركة", "قطر للتكنولوجيا", "لوجستيات"],
        "tender_terms": ["مناقصة", "منافسة تقنية"],
        "job_terms": ["وظائف تقنية", "مطور ذكاء اصطناعي"],
    },
    "JO": {
        "primary_lang": "ar",
        "cities": ["عمان", "إربد"],
        "entity_terms": ["شركة تقنية", "حلول برمجية", "مركز دراسات"],
        "tender_terms": ["استشارة برمجية", "عطاء"],
        "job_terms": ["مطلوب مبرمج", "استشاري تحليل بيانات"],
    },
    "SY": {
        "primary_lang": "ar",
        "cities": ["دمشق", "حلب", "اللاذقية"],
        "entity_terms": ["شركة برمجيات", "حلول دفع", "تجارة إلكترونية"],
        "tender_terms": ["طلب مشروع برمجيات", "استشارة تقنية"],
        "job_terms": ["مطلوب مبرمج بايثون", "مطور ويب"],
    },
    "TR": {
        "primary_lang": "tr",
        "cities": ["İstanbul", "Ankara", "İzmir"],
        "entity_terms": ["şirketi", "yazılım", "e-ticaret", "lojistik"],
        "tender_terms": ["ihale", "yazılım projesi", "otomasyon talebi"],
        "job_terms": ["yapay zeka uzmanı", "yazılım geliştirici"],
    },
}

SERVICE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "ai_automation": {
        "ar": [
            "أتمتة خدمة العملاء واتساب {city}",
            "حلول الذكاء الاصطناعي للأعمال {city}",
            "ربط أنظمة الشركات API أتمتة {city}",
        ],
        "en": [
            "AI workflow automation {city}",
            "WhatsApp customer support AI {city}",
            "business process automation AI {city}",
        ],
        "tr": [
            "yapay zeka iş süreçleri otomasyonu {city}",
            "müşteri hizmetleri yapay zeka botu {city}",
        ],
    },
    "software_dev": {
        "ar": [
            "تطوير منصات وتطبيقات ويب {city}",
            "شركة برمجة وتطوير أنظمة {city}",
        ],
        "en": [
            "custom software development {city}",
            "web platform development {city}",
        ],
        "tr": [
            "özel yazılım geliştirme firması {city}",
        ],
    },
    "academic_consulting": {
        "ar": [
            "استشارات برمجية وتحليل بيانات أبحاث {city}",
            "تدريب بايثون ونمذجة خوارزميات {city}",
        ],
        "en": [
            "research data pipeline consulting {city}",
            "scientific computing Python modeling {city}",
        ],
    },
}


class RegionalQueryPlanner:
    """Produces focused query plans for a country, service, and intent."""

    def plan(
        self,
        country_code: str,
        service_key: str = "ai_automation",
        intent: str = "company_discovery",
        funnel: FunnelType = FunnelType.B2B,
    ) -> QueryPlan:
        """Generate localized queries for target market."""
        code = country_code.upper()
        country_data = COUNTRY_LOCALIZATIONS.get(code, COUNTRY_LOCALIZATIONS["SA"])
        primary_lang = country_data["primary_lang"]

        service_langs = SERVICE_TEMPLATES.get(service_key, SERVICE_TEMPLATES["ai_automation"])
        templates = service_langs.get(primary_lang) or service_langs.get("en", [])

        cities = country_data.get("cities", [""])
        queries: List[str] = []

        # Generate per city and template
        for city in cities[:2]:  # Top 2 major economic hubs
            for template in templates:
                q = template.format(city=city)
                if q not in queries:
                    queries.append(q)

        return QueryPlan(
            intent=intent,
            country_code=code,
            funnel=funnel,
            service_key=service_key,
            queries=queries,
            language_target=primary_lang,
        )

