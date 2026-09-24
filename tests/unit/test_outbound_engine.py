"""Unit tests for OutboundEngine service.

Verifies:
1. 3-step cadence generation (Initial Pitch, Value Case, Breakaway).
2. Channel adaptation across Email, WhatsApp, and LinkedIn.
3. Factual evidence citations in personalized outreach drafts.
4. Academic integrity guard (A-008): legitimate mentoring only, zero ghostwriting.
5. Secret scrubbing (A-018, I-05) on all company and evidence inputs.
6. Approval request creation (A-007, I-02, A-022) with actor='agent_draft'.
7. Lead lifecycle state progression (QUALIFIED -> OUTREACH_READY -> CONTACTED).
"""
from __future__ import annotations

import unittest

from marketing_plugin.policies.redactor import contains_secrets
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.services.lead_scorer import ACADEMIC_VIOLATION_PATTERNS
from marketing_plugin.services.outbound_engine import OutboundEngine
from schemas.models import (
    ActorType,
    ApprovalDecision,
    Company,
    Evidence,
    ExtractorType,
    FunnelType,
    InteractionDirection,
    Lead,
    LeadAssessment,
    LeadStatus,
    OutreachStepType,
    utc_now,
)


class TestOutboundEngine(unittest.TestCase):
    """Hermetic unit tests for OutboundEngine."""

    def setUp(self):
        self.db = Database(":memory:")
        self.conn = self.db.connect()
        self.db.run_migrations()

        # Seed country profiles, service profiles, and sources for foreign key constraints
        self.conn.execute("""
            INSERT INTO country_profiles (country_code, name, languages, manual_weight)
            VALUES ('SA', 'Saudi Arabia', '["ar"]', 1.0),
                   ('AE', 'UAE', '["ar", "en"]', 0.9);
        """)
        self.conn.execute("""
            INSERT INTO service_profiles (service_key, priority_class, allowed_funnels, offer_summary)
            VALUES ('ai_automation', 'primary', '["b2b"]', 'AI Workflow Automation'),
                   ('software_dev', 'primary', '["b2b"]', 'Custom Software Development'),
                   ('academic_mentoring', 'secondary', '["academic"]', 'Academic Mentoring');
        """)
        self.conn.execute("""
            INSERT INTO sources (source_id, domain_or_platform_key, country_scope, source_family, languages, status, access_mode)
            VALUES ('mostaql', 'mostaql.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public'),
                   ('bahr', 'bahr.sa', '["SA"]', 'freelance_platform', '["ar"]', 'trusted', 'public'),
                   ('khamsat', 'khamsat.com', '["SA", "AE"]', 'freelance_platform', '["ar"]', 'trusted', 'public');
        """)
        self.conn.commit()

        self.company_repo = CompanyRepository(self.conn)
        self.lead_repo = LeadRepository(self.conn)
        self.evidence_repo = EvidenceRepository(self.conn)
        self.interaction_repo = InteractionRepository(self.conn)
        self.approval_repo = ApprovalRepository(self.conn)

        self.engine = OutboundEngine(
            db=self.db,
            lead_repo=self.lead_repo,
            company_repo=self.company_repo,
            evidence_repo=self.evidence_repo,
            interaction_repo=self.interaction_repo,
            approval_repo=self.approval_repo,
        )

        # Seed B2B Company & Qualified Lead
        self.b2b_company = Company(
            company_id="comp_b2b_01",
            canonical_name="شركة حلول الخدمات اللوجستية المتطورة",
            primary_domain="saudi-logistics.sa",
            country_code="SA",
            city="الرياض",
            sector="الخدمات اللوجستية وسلاسل الإمداد",
            funnel=FunnelType.B2B,
            entity_confidence=1.0,
        )
        self.company_repo.save_company(self.b2b_company)

        self.b2b_lead = Lead(
            lead_id="lead_b2b_01",
            company_id="comp_b2b_01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
            priority_bucket=1,
            recommended_service_key="ai_automation",
        )
        self.lead_repo.save_lead(self.b2b_lead)

        # Evidence for B2B company
        self.evidence = Evidence(
            evidence_id="ev_b2b_01",
            company_id="comp_b2b_01",
            source_id="mostaql",
            url="https://mostaql.com/project/101",
            fact_type="job_posting",
            fact_text="طلب بناء نظام متكامل لربط فواتير المستودعات ومسارات الشحن آلياً",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_b2b_01",
            confidence=0.95,
        )
        self.evidence_repo.save_evidence(self.evidence)

        # Assessment linking evidence
        self.assessment = LeadAssessment(
            assessment_id="ass_b2b_01",
            lead_id="lead_b2b_01",
            fit_score=0.9,
            pain_score=0.85,
            urgency_score=0.8,
            reachability_score=0.75,
            final_score=0.85,
            recommended_service_key="ai_automation",
            evidence_ids=["ev_b2b_01"],
            reasoning_summary="شركة لوجستية تواجه تحديات يدوية في تتبع الشحن والفواتير.",
        )
        self.lead_repo.save_assessment(self.assessment)

    def test_generate_b2b_cadence_email(self):
        """Verifies 3-step B2B email cadence with evidence citation and approval gating."""
        plan = self.engine.generate_cadence(
            lead_id="lead_b2b_01",
            channel="email",
            auto_request_approval=True,
        )

        self.assertIsNotNone(plan.cadence_id)
        self.assertEqual(plan.lead_id, "lead_b2b_01")
        self.assertEqual(plan.company_id, "comp_b2b_01")
        self.assertEqual(plan.channel, "email")
        self.assertEqual(len(plan.messages), 3)

        # Step 1: Initial Pitch
        s1 = plan.messages[0]
        self.assertEqual(s1.step_number, 1)
        self.assertEqual(s1.step_type, OutreachStepType.INITIAL_PITCH)
        self.assertEqual(s1.delay_days, 0)
        self.assertIn("IntelliFY", s1.body)
        self.assertIn("شركة حلول الخدمات اللوجستية المتطورة", s1.body)
        self.assertIn("فواتير المستودعات ومسارات الشحن", s1.body)
        self.assertIsNotNone(s1.subject)
        self.assertIn("شركة حلول الخدمات اللوجستية المتطورة", s1.subject)

        # Step 2: Value Case
        s2 = plan.messages[1]
        self.assertEqual(s2.step_number, 2)
        self.assertEqual(s2.step_type, OutreachStepType.VALUE_CASE)
        self.assertEqual(s2.delay_days, 3)
        self.assertIn("دراسة حالة", s2.subject)
        self.assertIn("الخدمات اللوجستية", s2.body)

        # Step 3: Breakaway
        s3 = plan.messages[2]
        self.assertEqual(s3.step_number, 3)
        self.assertEqual(s3.step_type, OutreachStepType.BREAKAWAY)
        self.assertEqual(s3.delay_days, 5)
        self.assertIn("إغلاق", s3.subject)
        self.assertIn("لن أقوم بإرسال رسائل متابعة إضافية", s3.body)

        # Verify Approval Gate (A-007, I-02)
        self.assertIsNotNone(plan.approval_id)
        approval = self.approval_repo.get_approval(plan.approval_id)
        self.assertIsNotNone(approval)
        self.assertEqual(approval.action_type, "outreach_send")
        self.assertEqual(approval.target_type, "lead")
        self.assertEqual(approval.target_id, "lead_b2b_01")
        self.assertEqual(approval.decision, ApprovalDecision.PENDING)

        # Verify Lead State Progression (M-01)
        updated_lead = self.lead_repo.get_lead("lead_b2b_01")
        self.assertEqual(updated_lead.status, LeadStatus.OUTREACH_READY)
        self.assertEqual(updated_lead.next_action, "awaiting_approval")

        # Verify Draft Interactions persisted with actor=agent_draft
        interactions = self.interaction_repo.list_interactions(lead_id="lead_b2b_01")
        self.assertEqual(len(interactions), 3)
        for inter in interactions:
            self.assertEqual(inter.direction, InteractionDirection.OUTBOUND)
            self.assertEqual(inter.actor, ActorType.AGENT_DRAFT)

    def test_generate_b2b_cadence_whatsapp_and_linkedin(self):
        """Verifies channel tailoring for WhatsApp and LinkedIn."""
        # WhatsApp
        wa_plan = self.engine.generate_cadence(
            lead_id="lead_b2b_01",
            channel="whatsapp",
            auto_request_approval=False,
        )
        self.assertEqual(wa_plan.channel, "whatsapp")
        self.assertIsNone(wa_plan.messages[0].subject)  # WhatsApp has no email subject
        self.assertIn("مرحباً بك أستاذي الكريم", wa_plan.messages[0].body)
        self.assertIn("5 دقائق", wa_plan.messages[0].cta)

        # LinkedIn
        li_plan = self.engine.generate_cadence(
            lead_id="lead_b2b_01",
            channel="linkedin",
            auto_request_approval=False,
        )
        self.assertEqual(li_plan.channel, "linkedin")
        self.assertIn("تحية طيبة", li_plan.messages[0].body)
        self.assertIn("شبكتنا المهنية", li_plan.messages[2].cta)

    def test_academic_integrity_guard_preservation(self):
        """Strictly tests A-008: Academic leads receive ethical mentoring only; zero cheating."""
        acad_company = Company(
            company_id="comp_acad_01",
            canonical_name="طالب باحث دراسات عليا",
            country_code="SA",
            funnel=FunnelType.ACADEMIC,
            entity_confidence=1.0,
        )
        self.company_repo.save_company(acad_company)

        acad_lead = Lead(
            lead_id="lead_acad_01",
            company_id="comp_acad_01",
            funnel=FunnelType.ACADEMIC,
            status=LeadStatus.QUALIFIED,
            priority_bucket=2,
            recommended_service_key="academic_mentoring",
        )
        self.lead_repo.save_lead(acad_lead)

        acad_evidence = Evidence(
            evidence_id="ev_acad_01",
            company_id="comp_acad_01",
            source_id="khamsat",
            url="https://khamsat.com/service/202",
            fact_type="academic_inquiry",
            fact_text="استشارة في ضبط العينات والتحليل الإحصائي لبحث ماجستير",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_acad_01",
            confidence=0.9,
        )
        self.evidence_repo.save_evidence(acad_evidence)

        plan = self.engine.generate_cadence(lead_id="lead_acad_01", channel="email")
        self.assertEqual(len(plan.messages), 3)

        # Verify strict compliance with A-008: No cheating keywords in any message
        for msg in plan.messages:
            full_text = f"{msg.subject or ''} {msg.body} {msg.cta}"
            for violation in ACADEMIC_VIOLATION_PATTERNS:
                self.assertNotIn(
                    violation,
                    full_text,
                    f"Academic violation pattern '{violation}' found in outreach message!",
                )
            # Ensure mentions of integrity and methodology
            self.assertTrue(
                "النزاهة" in full_text or "منهجية" in full_text or "إحصائي" in full_text or "استشارة" in full_text
            )

    def test_secret_redaction_in_outreach(self):
        """Strictly tests A-018 and I-05: Secrets never enter outreach copy or logs."""
        secret_key = "AIzaSyD_TEST_SECRET_API_KEY_1234567890ABC"
        secret_company = Company(
            company_id="comp_sec_01",
            canonical_name=f"شركة السحاب التقنية key={secret_key}",
            primary_domain="cloud.sa",
            country_code="SA",
            sector="تقنية المعلومات",
            funnel=FunnelType.B2B,
            entity_confidence=1.0,
        )
        self.company_repo.save_company(secret_company)

        secret_lead = Lead(
            lead_id="lead_sec_01",
            company_id="comp_sec_01",
            funnel=FunnelType.B2B,
            status=LeadStatus.QUALIFIED,
        )
        self.lead_repo.save_lead(secret_lead)

        secret_ev = Evidence(
            evidence_id="ev_sec_01",
            company_id="comp_sec_01",
            source_id="mostaql",
            url="https://mostaql.com/p/303",
            fact_type="job_posting",
            fact_text=f"نحتاج مطور يربط النظام عبر sk-12345678901234567890abcdefgh",
            extractor=ExtractorType.DETERMINISTIC,
            content_hash="hash_sec_01",
            confidence=0.9,
        )
        self.evidence_repo.save_evidence(secret_ev)

        plan = self.engine.generate_cadence(lead_id="lead_sec_01", channel="email")

        # Verify no raw secrets leaked into messages
        for msg in plan.messages:
            self.assertNotIn(secret_key, msg.body)
            self.assertNotIn("sk-12345678901234567890abcdefgh", msg.body)
            self.assertFalse(contains_secrets(msg.body))
            if msg.subject:
                self.assertFalse(contains_secrets(msg.subject))

    def test_record_contact_attempt(self):
        """Verifies record_contact_attempt transitions lead to CONTACTED and logs interaction."""
        # Generate cadence first (lead -> OUTREACH_READY)
        self.engine.generate_cadence(lead_id="lead_b2b_01", channel="email")
        lead_before = self.lead_repo.get_lead("lead_b2b_01")
        self.assertEqual(lead_before.status, LeadStatus.OUTREACH_READY)

        # Now record contact attempt
        success = self.engine.record_contact_attempt(
            lead_id="lead_b2b_01",
            channel="email",
            actor_id="founder_admin",
            notes="Sent step 1 pitch email to CEO",
        )
        self.assertTrue(success)

        # Check lead lifecycle progression (M-01, M-12)
        lead_after = self.lead_repo.get_lead("lead_b2b_01")
        self.assertEqual(lead_after.status, LeadStatus.CONTACTED)
        self.assertEqual(lead_after.next_action, "awaiting_lead_reply")

        # Check interaction logged with actor=HUMAN
        interactions = self.interaction_repo.list_interactions(lead_id="lead_b2b_01", actor=ActorType.HUMAN)
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].outcome_tag, "contacted")
        self.assertIn("Sent step 1 pitch email to CEO", interactions[0].content_summary)

    def test_missing_lead_or_company_raises(self):
        """Verifies appropriate errors when records are missing."""
        with self.assertRaises(ValueError):
            self.engine.generate_cadence(lead_id="nonexistent_lead")

        # Lead with missing company
        from unittest.mock import patch
        orphan_lead = Lead(
            lead_id="orphan_lead",
            company_id="nonexistent_company",
            funnel=FunnelType.B2B,
        )
        with patch.object(self.lead_repo, "get_lead", return_value=orphan_lead):
            with self.assertRaises(ValueError):
                self.engine.generate_cadence(lead_id="orphan_lead")


if __name__ == "__main__":
    unittest.main()
