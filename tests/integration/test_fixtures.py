"""Tests for synthetic fixtures and evaluation seeds."""
import unittest

from tests.fixtures.evaluation_seeds import (
    CONTENT_GROUNDING_RUBRIC,
    ENTITY_MERGE_LABELS,
    EVIDENCE_EXTRACTION_EXPECTED,
    LEAD_PRIORITY_RANKING_LABELS,
    SOURCE_RELEVANCE_LABELS,
)
from tests.fixtures.synthetic_corpus import SYNTHETIC_CORPUS


class TestFixturesAndSeeds(unittest.TestCase):
    """Verifies synthetic corpus completeness and evaluation seed consistency."""

    def test_corpus_coverage(self):
        """Ensure all required regional clusters and edge cases exist."""
        clusters = {f["market_cluster"] for f in SYNTHETIC_CORPUS}
        self.assertIn("gcc", clusters)
        self.assertIn("levant", clusters)
        self.assertIn("turkey", clusters)
        self.assertIn("north_africa", clusters)

        # Ensure Turkey cluster has multiple fixtures per pre-implementation plan
        turkey_count = sum(1 for f in SYNTHETIC_CORPUS if f["market_cluster"] == "turkey")
        self.assertGreaterEqual(turkey_count, 2, "Turkey cluster requires at least 2 fixtures")

        # Check edge cases presence
        has_prompt_injection = any(f.get("contains_prompt_injection") for f in SYNTHETIC_CORPUS)
        has_fake_secret = any(f.get("contains_fake_secret") for f in SYNTHETIC_CORPUS)
        has_duplicate_entity = any("duplicate_entity" in f.get("tags", []) for f in SYNTHETIC_CORPUS)
        has_stale_page = any("stale_page" in f.get("tags", []) for f in SYNTHETIC_CORPUS)
        has_tender = any("procurement_tender" in f.get("tags", []) for f in SYNTHETIC_CORPUS)
        has_academic_violation = any(
            f.get("is_academic") and not f.get("academic_integrity_compliant", True)
            for f in SYNTHETIC_CORPUS
        )
        has_academic_legit = any(
            f.get("is_academic") and f.get("academic_integrity_compliant", False)
            for f in SYNTHETIC_CORPUS
        )

        self.assertTrue(has_prompt_injection, "Missing prompt injection edge case in corpus")
        self.assertTrue(has_fake_secret, "Missing fake secret edge case in corpus")
        self.assertTrue(has_duplicate_entity, "Missing duplicate entity fixture in corpus")
        self.assertTrue(has_stale_page, "Missing stale page fixture in corpus")
        self.assertTrue(has_tender, "Missing procurement tender fixture in corpus")
        self.assertTrue(has_academic_violation, "Missing academic violation edge case in corpus")
        self.assertTrue(has_academic_legit, "Missing legitimate academic case in corpus")


    def test_corpus_to_priority_mapping(self):
        """Ensure every corpus fixture has a ground-truth lead priority."""
        for fixture in SYNTHETIC_CORPUS:
            fid = fixture["fixture_id"]
            self.assertIn(fid, LEAD_PRIORITY_RANKING_LABELS)
            expected_priority = fixture["expected_lead_priority"]
            self.assertEqual(LEAD_PRIORITY_RANKING_LABELS[fid], expected_priority)

    def test_entity_merge_test_cases(self):
        """Ensure entity merge cases cover both confident merge and collision avoidance."""
        actions = {case["expected_action"] for case in ENTITY_MERGE_LABELS}
        self.assertIn("MERGE_HIGH_CONFIDENCE", actions)
        self.assertIn("NO_MERGE_AMBIGUOUS_COLLISION", actions)

    def test_content_grounding_rubric(self):
        """Ensure content grounding rubric requires evidence citation and approvals."""
        dimensions = CONTENT_GROUNDING_RUBRIC["dimensions"]
        self.assertTrue(dimensions["evidence_citation"]["mandatory"])
        self.assertTrue(dimensions["persisted_approval_required"]["mandatory"])


if __name__ == "__main__":
    unittest.main()

