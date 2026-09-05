"""Tests for Deterministic Secret Redactor (Invariant I-05)."""
import unittest

from marketing_plugin.policies.redactor import (
    REDACTED_PLACEHOLDER,
    contains_secrets,
    redact_secrets,
)


class TestSecretRedactor(unittest.TestCase):
    """Verifies that all known secret formats are redacted from model payloads."""

    def test_redact_google_api_key(self):
        # Concatenate prefix to avoid tripping static secret scanners on test fixtures
        mock_key = "AIza" + "SyD-exampleGoogleKey1234567890abc"
        text = f"Client config has google_key={mock_key} in headers"
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("AIzaSyD", redacted)
        self.assertIn(REDACTED_PLACEHOLDER, redacted)

    def test_redact_openai_secret_key(self):
        mock_key = "sk-" + "abc12345678901234567890_test_key"
        text = f"Found token: {mock_key}"
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("sk-abc", redacted)
        self.assertIn(REDACTED_PLACEHOLDER, redacted)

    def test_redact_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("eyJhbGciOi", redacted)
        self.assertIn(REDACTED_PLACEHOLDER, redacted)

    def test_redact_private_key_block(self):
        header = "-----" + "BEGIN RSA PRIVATE KEY-----"
        footer = "-----" + "END RSA PRIVATE KEY-----"
        text = (
            f"{header}\n"
            "MIIEowIBAAKCAQEA0mockKeyContentForTestingPurposeOnly123456789==\n"
            f"{footer}"
        )
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("mockKeyContent", redacted)
        self.assertIn(REDACTED_PLACEHOLDER, redacted)

    def test_redact_url_password(self):
        text = "Connecting to https://admin:super_secret_pwd_99@api.vendor.com/v1"
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("super_secret_pwd_99", redacted)
        self.assertIn(f"https://admin:{REDACTED_PLACEHOLDER}@api.vendor.com/v1", redacted)

    def test_redact_test_corpus_mock_secrets(self):
        text = "api_key=MOCK_SECRET_KEY_FOR_TESTING_PURPOSES_ONLY_XYZ99 aws_secret_key=SAMPLE_TEST_AWS_SECRET_KEY_EXCLUDED"
        self.assertTrue(contains_secrets(text))
        redacted = redact_secrets(text)
        self.assertNotIn("MOCK_SECRET_KEY", redacted)
        self.assertNotIn("SAMPLE_TEST_AWS", redacted)

    def test_clean_text_unchanged(self):
        text = "شركة المسار السريع للخدمات اللوجستية في الرياض تقدم حلول التجارة الإلكترونية."
        self.assertFalse(contains_secrets(text))
        self.assertEqual(redact_secrets(text), text)


if __name__ == "__main__":
    unittest.main()
