#!/usr/bin/env python3
"""Pinned fallback runner for project custom roles when native subagent effort inheritance is not proven."""
from __future__ import annotations
import argparse, subprocess, sys

ROLES = {"orchestrator", "explorer", "builder", "verifier", "reviewer", "heavy-reviewer"}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=sorted(ROLES))
    ap.add_argument("prompt")
    ap.add_argument("--output-format", default="text", choices=["text", "json", "stream-json"])
    args = ap.parse_args()
    cmd = [
        "agy", "--agent", args.role,
        "--model", "gemini-3.8-flash-high",
        "--effort", "high",
        "--output-format", args.output_format,
        "-p", args.prompt,
    ]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
