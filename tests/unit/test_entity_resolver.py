"""Unit tests for EntityResolver and Identity Deduplication Engine.

Verifies canonical root domain normalization, multi-lingual name cleaning,
deterministic identity resolution against CompanyRepository, and non-destructive
merging safeguards according to docs/02-technical-design-spec.md:130.
"""
from __future__ import annotations

import unittest
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.services.entity_resolver import EntityResolver, ResolutionOutcome
from schemas.models import Company, FunnelType


class TestEntityResolver(unittest.TestCase):
    """Unit tests for EntityResolver domain normalization, name cleaning, and resolution."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed reference country profiles for foreign key constraints
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 0.35),
                   ('AE', 'United Arab Emirates', '["ar", "en"]', 0.25),
                   ('TR', 'Turkey', '["tr", "en"]', 0.10);
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.resolver = EntityResolver(self.company_repo)

    # --- 1. Domain Normalization Tests ---

    def test_normalize_domain_canonical_root(self):
        """Verify URL with path, query, fragment and www normalizes to root domain."""
        raw = "https://www.example.com/page?ref=1#section"
        self.assertEqual(self.resolver.normalize_domain(raw), "example.com")

    def test_normalize_domain_subdomain_and_port(self):
        """Verify subdomain with port normalizes to root domain."""
        raw = "m.sub.domain.sa:8080"
        self.assertEqual(self.resolver.normalize_domain(raw), "domain.sa")

    def test_normalize_domain_regional_second_level_tlds(self):
        """Verify multi-part regional ccTLDs (.com.sa, .co.ae, .com.tr, .com.qa)."""
        self.assertEqual(
            self.resolver.normalize_domain("https://blog.portal.client.com.sa/dashboard"),
            "client.com.sa",
        )
        self.assertEqual(
            self.resolver.normalize_domain("https://tech.startup.co.ae/services"),
            "startup.co.ae",
        )
        self.assertEqual(
            self.resolver.normalize_domain("https://app.yazilim.com.tr"),
            "yazilim.com.tr",
        )
        self.assertEqual(
            self.resolver.normalize_domain("https://portal.finance.com.qa/login"),
            "finance.com.qa",
        )
        self.assertEqual(
            self.resolver.normalize_domain("https://news.agency.org.sa"),
            "agency.org.sa",
        )

    def test_normalize_domain_edge_cases(self):
        """Verify localhost, ip addresses, uppercase, trailing slash, and empty values."""
        self.assertEqual(self.resolver.normalize_domain("http://localhost:8000"), "localhost")
        self.assertEqual(self.resolver.normalize_domain("192.168.1.1:9000"), "192.168.1.1")
        self.assertEqual(self.resolver.normalize_domain("HTTPS://WWW.EXAMPLE.COM/"), "example.com")
        self.assertEqual(self.resolver.normalize_domain(""), "")
        self.assertIsNone(self.resolver.normalize_domain(None))

    # --- 2. Company Name Cleaning Tests ---

    def test_normalize_company_name_arabic(self):
        """Verify Arabic alef forms, teh marbuta, harakat, and corporate prefixes/suffixes."""
        # Alef forms: أ, إ, آ -> ا; Teh marbuta: ة -> ه
        # Strip prefix 'شركة' and suffix 'ذ.م.م'
        raw = "شركة الأفق التقنية ذ.م.م"
        cleaned = self.resolver.normalize_company_name(raw)
        self.assertEqual(cleaned, "الافق التقنيه")

        # Strip prefix 'مؤسسة' and alef hamza below 'إ'
        raw2 = "مؤسسة إنجاز للبرمجيات"
        cleaned2 = self.resolver.normalize_company_name(raw2)
        self.assertEqual(cleaned2, "انجاز للبرمجيات")

        # Strip suffix 'ش.م.م' and tatweel/harakat
        raw3 = "مجموعة النَّـمَـاء ش.م.م"
        cleaned3 = self.resolver.normalize_company_name(raw3)
        self.assertEqual(cleaned3, "النماء")

    def test_normalize_company_name_english(self):
        """Verify English corporate suffixes stripping and case normalization."""
        self.assertEqual(
            self.resolver.normalize_company_name("Acme Technologies, Inc."),
            "acme technologies",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Global Logistics LLC"),
            "global logistics",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Apex Software Ltd."),
            "apex software",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Venture Co., Ltd."),
            "venture",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Horizon Corporation"),
            "horizon",
        )

    def test_normalize_company_name_turkish(self):
        """Verify Turkish corporate forms stripping and lowercase normalization."""
        self.assertEqual(
            self.resolver.normalize_company_name("Demir Yazılım A.Ş."),
            "demir yazılım",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Yıldız Bilişim Ltd. Şti."),
            "yıldız bilişim",
        )
        self.assertEqual(
            self.resolver.normalize_company_name("Anadolu Lojistik Anonim Şirketi"),
            "anadolu lojistik",
        )

    def test_normalize_company_name_edge_cases(self):
        """Verify empty names and names that consist solely of corporate legal terms."""
        self.assertEqual(self.resolver.normalize_company_name(""), "")
        self.assertEqual(self.resolver.normalize_company_name(None), "")
        # Fallback retains cleaned text
        self.assertTrue(len(self.resolver.normalize_company_name("LLC Inc.")) > 0)

    # --- 3. Identity Resolution and Deduplication Tests ---

    def test_resolve_exact_primary_domain_match(self):
        """Verify exact primary domain match returns existing company with confidence 1.0."""
        existing = Company(
            company_id="comp_existing_domain",
            canonical_name="Riyadh Tech",
            primary_domain="riyadhtech.sa",
            country_code="SA",
            city="Riyadh",
            public_contacts_json={"phone": "+966500000001"},
        )
        self.company_repo.save_company(existing)

        # Query with different name variation and full URL
        outcome = self.resolver.resolve_company(
            canonical_name="شركة تقنية الرياض المحدودة",
            country_code="SA",
            primary_domain="https://www.riyadhtech.sa/about?lang=ar",
            city="Riyadh",
            public_contacts={"email": "info@riyadhtech.sa"},
            return_details=True,
        )

        self.assertIsInstance(outcome, ResolutionOutcome)
        self.assertEqual(outcome.company.company_id, "comp_existing_domain")
        self.assertEqual(outcome.confidence, 1.0)
        self.assertFalse(outcome.is_new)
        self.assertEqual(outcome.match_type, "exact_domain")

        # Verify contacts were non-destructively enriched
        updated = self.company_repo.get_company("comp_existing_domain")
        self.assertEqual(updated.public_contacts_json.get("email"), "info@riyadhtech.sa")
        self.assertEqual(updated.public_contacts_json.get("phone"), "+966500000001")

    def test_resolve_shared_verified_contact(self):
        """Verify shared verified phone or email resolves with confidence 0.90."""
        existing = Company(
            company_id="comp_contact_match",
            canonical_name="Apex Logistics",
            country_code="SA",
            public_contacts_json={"email": "contact@apexlog.sa", "phone": "+966501112233"},
        )
        self.company_repo.save_company(existing)

        # Match by phone number
        outcome_phone = self.resolver.resolve_company(
            canonical_name="Apex Express Delivery",
            country_code="SA",
            public_contacts={"phone": "+966 50 111 2233"},
            return_details=True,
        )
        self.assertEqual(outcome_phone.company.company_id, "comp_contact_match")
        self.assertEqual(outcome_phone.confidence, 0.90)
        self.assertFalse(outcome_phone.is_new)
        self.assertEqual(outcome_phone.match_type, "verified_contact")

        # Match by email
        outcome_email = self.resolver.resolve_company(
            canonical_name="Apex Global Warehouse",
            country_code="SA",
            public_contacts={"email": "CONTACT@apexlog.sa"},
            return_details=True,
        )
        self.assertEqual(outcome_email.company.company_id, "comp_contact_match")
        self.assertEqual(outcome_email.confidence, 0.90)
        self.assertFalse(outcome_email.is_new)

    def test_resolve_exact_normalized_name_same_country(self):
        """Verify exact normalized name match within same country resolves with confidence 0.85."""
        existing = Company(
            company_id="comp_name_match",
            canonical_name="شركة الأفق للتطوير ذ.م.م",
            country_code="SA",
            city="Jeddah",
        )
        self.company_repo.save_company(existing)

        # Input name has different corporate prefix/suffix but normalizes identically
        outcome = self.resolver.resolve_company(
            canonical_name="مؤسسة الافق للتطوير",
            country_code="SA",
            city="Jeddah",
            return_details=True,
        )
        self.assertEqual(outcome.company.company_id, "comp_name_match")
        self.assertEqual(outcome.confidence, 0.85)
        self.assertFalse(outcome.is_new)
        self.assertEqual(outcome.match_type, "exact_name")

    def test_resolve_no_match_creates_new_company(self):
        """Verify ambiguous / unrecognised entity creates a new company in repository."""
        outcome = self.resolver.resolve_company(
            canonical_name="Unseen Solutions LLC",
            country_code="SA",
            primary_domain="https://unseen-solutions.sa",
            city="Dammam",
            return_details=True,
        )
        self.assertTrue(outcome.is_new)
        self.assertEqual(outcome.match_type, "created_new")
        self.assertEqual(outcome.confidence, 1.0)
        self.assertTrue(outcome.company.company_id.startswith("comp_"))

        # Verify saved in CompanyRepository
        persisted = self.company_repo.get_company(outcome.company.company_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.canonical_name, "Unseen Solutions LLC")
        self.assertEqual(persisted.primary_domain, "unseen-solutions.sa")

    # --- 4. Non-Destructive Safeguard Tests ---

    def test_non_destructive_different_country_creates_separate_entity(self):
        """Verify identical company name in a different country creates a separate entity."""
        sa_company = Company(
            company_id="comp_sa_branch",
            canonical_name="Alpha Tech",
            country_code="SA",
        )
        self.company_repo.save_company(sa_company)

        # Input has same name but country is AE
        outcome = self.resolver.resolve_company(
            canonical_name="Alpha Tech LLC",
            country_code="AE",
            return_details=True,
        )
        self.assertTrue(outcome.is_new)
        self.assertNotEqual(outcome.company.company_id, "comp_sa_branch")
        self.assertEqual(outcome.company.country_code, "AE")

        # Verify original SA company is unchanged
        sa_check = self.company_repo.get_company("comp_sa_branch")
        self.assertEqual(sa_check.country_code, "SA")

    def test_non_destructive_distinct_domains_prevent_merge(self):
        """Verify identical normalized name with distinct primary domains does NOT merge (A-017 safeguard)."""
        existing = Company(
            company_id="comp_domain_alpha",
            canonical_name="Beta Innovations",
            primary_domain="beta-innovations.com",
            country_code="SA",
        )
        self.company_repo.save_company(existing)

        # Input has same name but a completely distinct primary domain
        outcome = self.resolver.resolve_company(
            canonical_name="Beta Innovations LLC",
            country_code="SA",
            primary_domain="https://beta-innovations-group.sa",
            return_details=True,
        )
        self.assertTrue(outcome.is_new)
        self.assertNotEqual(outcome.company.company_id, "comp_domain_alpha")
        self.assertEqual(outcome.company.primary_domain, "beta-innovations-group.sa")

    def test_default_return_type_is_company(self):
        """Verify resolve_company returns Company entity by default with attributes attached."""
        company = self.resolver.resolve_company(
            canonical_name="Standard Return Enterprise",
            country_code="SA",
            primary_domain="standard-return.sa",
        )
        self.assertIsInstance(company, Company)
        self.assertTrue(hasattr(company, "_is_new"))
        self.assertTrue(hasattr(company, "_match_type"))
        self.assertTrue(company._is_new)
