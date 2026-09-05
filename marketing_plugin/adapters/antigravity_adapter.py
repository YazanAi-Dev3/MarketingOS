"""Antigravity CLI Reasoning Adapter for Marketing OS.

Wraps headless Google Antigravity CLI (`agy.exe`) to provide
deterministic, structured reasoning (Gemini 3.8 Flash High)
without runtime OpenAI/Codex dependencies, enforcing policy A-019/A-031.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default search paths for agy executable on Windows/Linux
DEFAULT_AGY_PATHS = [
    Path(os.path.expandvars(r"%USERPROFILE%\.gemini\bin\agy.exe")),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\agy.exe")),
    Path(os.path.expanduser("~/.gemini/bin/agy")),
    Path("/usr/local/bin/agy"),
]

DEFAULT_MODEL = "gemini-3.8-flash-high"
DEFAULT_EFFORT = "high"


@dataclass
class ReasoningResult:
    """Structured result returned by Antigravity reasoning execution."""
    success: bool
    text: str = ""
    structured_data: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    conversation_id: str = ""
    error: Optional[str] = None
    raw_output: str = ""


from marketing_plugin.policies.redactor import redact_secrets

MAX_CLI_PROMPT_CHARS = 24_000


class AntigravityAdapter:
    """Manages headless execution of official Google Antigravity CLI."""

    def __init__(
        self,
        executable_path: Optional[Path] = None,
        default_model: str = DEFAULT_MODEL,
        default_effort: str = DEFAULT_EFFORT,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.executable_path = executable_path or self._discover_executable()
        self.default_model = default_model
        self.default_effort = default_effort
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _discover_executable() -> Path:
        """Find the agy executable on the current system."""
        # 1. Check system PATH
        path_which = shutil.which("agy") or shutil.which("agy.exe")
        if path_which:
            return Path(path_which)

        # 2. Check default locations
        for candidate in DEFAULT_AGY_PATHS:
            if candidate.is_file():
                return candidate

        raise FileNotFoundError(
            "Google Antigravity CLI (agy/agy.exe) not found on PATH or default locations. "
            "Please install or provide explicit executable_path."
        )

    def reason(
        self,
        prompt: str,
        json_schema: Optional[Dict[str, Any] | Path | str] = None,
        model: Optional[str] = None,
        effort: Optional[str] = None,
        agent: Optional[str] = None,
        cwd: Optional[Path] = None,
    ) -> ReasoningResult:
        """Execute a prompt headless through Antigravity CLI with safety boundaries."""
        target_model = model or self.default_model
        target_effort = effort or self.default_effort

        # Invariant I-05: Redact all secrets before passing to model
        safe_prompt = redact_secrets(prompt)

        # Protect against Windows CreateProcess 32KB command line limit
        if len(safe_prompt) > MAX_CLI_PROMPT_CHARS:
            logger.warning(
                "Prompt length %d exceeds safe Windows command line buffer; truncating to %d",
                len(safe_prompt),
                MAX_CLI_PROMPT_CHARS,
            )
            safe_prompt = safe_prompt[:MAX_CLI_PROMPT_CHARS] + "\n[Content truncated for length]"

        cmd = [
            str(self.executable_path),
            "-p", safe_prompt,
            "--model", target_model,
            "--effort", target_effort,
            "--output-format", "json",
        ]

        if agent:
            cmd.extend(["--agent", agent])

        temp_schema_path: Optional[Path] = None
        try:
            if json_schema:
                if isinstance(json_schema, Path):
                    cmd.extend(["--json-schema", str(json_schema)])
                elif isinstance(json_schema, dict):
                    # Write schema to a temporary file
                    fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="agy_schema_")
                    temp_schema_path = Path(tmp_name)
                    with open(fd, "w", encoding="utf-8") as f:
                        json.dump(json_schema, f, ensure_ascii=False)
                    cmd.extend(["--json-schema", str(temp_schema_path)])
                elif isinstance(json_schema, str):
                    if Path(json_schema).is_file():
                        cmd.extend(["--json-schema", json_schema])
                    else:
                        # Write raw json string to file
                        fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="agy_schema_")
                        temp_schema_path = Path(tmp_name)
                        with open(fd, "w", encoding="utf-8") as f:
                            f.write(json_schema)
                        cmd.extend(["--json-schema", str(temp_schema_path)])

            start_time = time.perf_counter()
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                cwd=str(cwd) if cwd else None,
            )
            elapsed = time.perf_counter() - start_time

            if proc.returncode != 0:
                return ReasoningResult(
                    success=False,
                    duration_seconds=elapsed,
                    error=f"agy exited with code {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}",
                    raw_output=proc.stdout,
                )

            # Parse the JSON envelope
            try:
                envelope = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                return ReasoningResult(
                    success=False,
                    duration_seconds=elapsed,
                    text=proc.stdout.strip(),
                    error=f"Failed to parse agy JSON envelope: {exc}",
                    raw_output=proc.stdout,
                )

            usage = envelope.get("usage", {})
            return ReasoningResult(
                success=True,
                text=envelope.get("response", ""),
                structured_data=envelope.get("structured_output"),
                duration_seconds=envelope.get("duration_seconds", elapsed),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                thinking_tokens=usage.get("thinking_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                conversation_id=envelope.get("conversation_id", ""),
                raw_output=proc.stdout,
            )

        except subprocess.TimeoutExpired:
            return ReasoningResult(
                success=False,
                duration_seconds=self.timeout_seconds,
                error=f"Reasoning timed out after {self.timeout_seconds} seconds",
            )
        except Exception as exc:
            return ReasoningResult(
                success=False,
                error=f"Unexpected reasoning error: {exc}",
            )
        finally:
            if temp_schema_path and temp_schema_path.is_file():
                try:
                    temp_schema_path.unlink()
                except OSError:
                    pass

