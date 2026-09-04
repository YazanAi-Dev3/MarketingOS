#!/usr/bin/env python3
"""Run a Marketing OS Antigravity role with the exact required model/effort.

Fallback for cases where native custom-subagent effort inheritance cannot be
proven. This is an engineering harness utility, not product runtime.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ALLOWED = {"orchestrator","explorer","builder","verifier","reviewer","heavy-reviewer"}
MODEL = "gemini-3.8-flash-high"
EFFORT = "high"

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=sorted(ALLOWED))
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt")
    g.add_argument("--prompt-file")
    ap.add_argument("--output-format", choices=["text","json","stream-json"], default="json")
    ap.add_argument("--timeout", default="10m")
    args=ap.parse_args()
    prompt=args.prompt if args.prompt is not None else Path(args.prompt_file).read_text(encoding="utf-8")
    cmd=["agy","-p",prompt,"--agent",args.agent,"--model",MODEL,"--effort",EFFORT,"--output-format",args.output_format,"--print-timeout",args.timeout]
    proc=subprocess.run(cmd)
    return proc.returncode
if __name__ == "__main__": raise SystemExit(main())
