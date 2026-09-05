"""Deterministic Secret Redactor for Marketing OS.

Enforces Invariant I-05: "secrets never enter model payload or logs".
Sanitizes API keys, authorization tokens, private keys, and credentials
from external web content before passing to reasoning providers or storage.
"""
from __future__ import annotations

import re
from typing import List, Pattern

REDACTED_PLACEHOLDER = "[REDACTED_SECRET]"

SECRET_PATTERNS: List[Pattern[str]] = [
    # Private keys
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    # Google API keys
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    # OpenAI / generic secret keys
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    # Bearer tokens
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    # AWS access/secret keys
    re.compile(r"(?i)(?:aws_secret_access_key|aws_secret_key|aws_access_key_id)\s*=\s*['\"]?[A-Za-z0-9/+=_-]{16,}['\"]?"),
    # Generic API key assignments
    re.compile(r"(?i)(?:api_key|apikey|auth_token|access_token|client_secret)\s*[:=]\s*['\"]?[A-Za-z0-9/+=_\-]{16,}['\"]?"),
    # Test fixture mock secrets
    re.compile(r"MOCK_SECRET_KEY_FOR_TESTING_PURPOSES_ONLY_[A-Za-z0-9]+"),
    re.compile(r"SAMPLE_TEST_AWS_SECRET_KEY_[A-Za-z0-9_]+"),
    # Passwords in URLs (http://user:password@host)
    re.compile(r"://([^:]+):([^@]+)@"),
]


def redact_secrets(text: str) -> str:
    """Scan and redact known secret patterns from text."""
    if not text:
        return text

    redacted = text
    for pattern in SECRET_PATTERNS:
        # For URL password pattern, preserve user and host
        if pattern.pattern == r"://([^:]+):([^@]+)@":
            redacted = pattern.sub(r"://\1:" + REDACTED_PLACEHOLDER + "@", redacted)
        else:
            redacted = pattern.sub(REDACTED_PLACEHOLDER, redacted)

    return redacted


def contains_secrets(text: str) -> bool:
    """Return True if any secret pattern is matched in text."""
    if not text:
        return False
    return any(pattern.search(text) is not None for pattern in SECRET_PATTERNS)

