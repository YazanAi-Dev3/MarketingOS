"""Tests for Antigravity CLI Reasoning Adapter."""
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from marketing_plugin.adapters.antigravity_adapter import (
    AntigravityAdapter,
    ReasoningResult,
)


class TestAntigravityAdapter(unittest.TestCase):
    """Unit and smoke tests for AntigravityAdapter."""

    def test_executable_discovery(self):
        """Ensure agy executable is located on the host system."""
        adapter = AntigravityAdapter()
        self.assertTrue(adapter.executable_path.is_file())
        self.assertIn("agy", adapter.executable_path.name.lower())

    def test_reason_parse_json_envelope(self):
        """Test parsing a valid agy json output envelope."""
        mock_output = {
            "conversation_id": "test-conv-123",
            "status": "SUCCESS",
            "response": "Analysis complete",
            "duration_seconds": 1.25,
            "structured_output": {
                "lead_priority": 1,
                "status": "qualified"
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "thinking_tokens": 25,
                "total_tokens": 150
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps(mock_output)
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            adapter = AntigravityAdapter(executable_path=Path("dummy/agy.exe"))
            result = adapter.reason(
                prompt="Assess lead",
                json_schema={"type": "object"}
            )

            self.assertTrue(result.success)
            self.assertEqual(result.conversation_id, "test-conv-123")
            self.assertEqual(result.text, "Analysis complete")
            self.assertEqual(result.structured_data, {"lead_priority": 1, "status": "qualified"})
            self.assertEqual(result.input_tokens, 100)
            self.assertEqual(result.output_tokens, 50)
            self.assertEqual(result.thinking_tokens, 25)
            self.assertEqual(result.total_tokens, 150)
            self.assertEqual(result.duration_seconds, 1.25)
            self.assertIsNone(result.error)

    def test_reason_nonzero_exit_code(self):
        """Test error handling when agy returns non-zero code."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 2
            mock_proc.stdout = ""
            mock_proc.stderr = "Model not available"
            mock_run.return_value = mock_proc

            adapter = AntigravityAdapter(executable_path=Path("dummy/agy.exe"))
            result = adapter.reason(prompt="Hello")

            self.assertFalse(result.success)
            self.assertIn("exited with code 2", result.error)
            self.assertIn("Model not available", result.error)

    def test_reason_redacts_secrets_in_prompt(self):
        """Ensure cleartext secrets in prompts are sanitized before agy execution (Invariant I-05)."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({"status": "SUCCESS", "response": "Done"})
            mock_run.return_value = mock_proc

            adapter = AntigravityAdapter(executable_path=Path("dummy/agy.exe"))
            prompt_with_secret = (
                "Review this client data: api_key=MOCK_SECRET_KEY_FOR_TESTING_PURPOSES_ONLY_XYZ99 "
                "and password: https://user:super_secret_pw123@internal.example.com"
            )
            adapter.reason(prompt=prompt_with_secret)

            # Inspect the command arguments sent to subprocess.run
            called_cmd = mock_run.call_args[0][0]
            cmd_str = " ".join(called_cmd)

            self.assertNotIn("MOCK_SECRET_KEY_FOR_TESTING_PURPOSES_ONLY_XYZ99", cmd_str)
            self.assertNotIn("super_secret_pw123", cmd_str)
            self.assertIn("[REDACTED_SECRET]", cmd_str)

    def test_reason_truncates_oversized_prompts(self):
        """Ensure prompts exceeding 24,000 chars are safely truncated to avoid WinError 206."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({"status": "SUCCESS", "response": "Done"})
            mock_run.return_value = mock_proc

            adapter = AntigravityAdapter(executable_path=Path("dummy/agy.exe"))
            huge_prompt = "A" * 50_000
            adapter.reason(prompt=huge_prompt)

            called_cmd = mock_run.call_args[0][0]
            # Prompt is the element right after "-p"
            prompt_idx = called_cmd.index("-p") + 1
            executed_prompt = called_cmd[prompt_idx]

            self.assertLessEqual(len(executed_prompt), 25_000)
            self.assertIn("[Content truncated for length]", executed_prompt)

    def test_reason_omits_dangerously_skip_permissions(self):
        """Ensure --dangerously-skip-permissions is never passed in model reasoning mode."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({"status": "SUCCESS", "response": "Done"})
            mock_run.return_value = mock_proc

            adapter = AntigravityAdapter(executable_path=Path("dummy/agy.exe"))
            adapter.reason(prompt="Hello safe reasoning")

            called_cmd = mock_run.call_args[0][0]
            self.assertNotIn("--dangerously-skip-permissions", called_cmd)


if __name__ == "__main__":
    unittest.main()


