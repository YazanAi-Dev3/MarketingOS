#!/usr/bin/env python3
"""Prevent a premature stop while background work is still active, without creating an infinite stop loop."""
from __future__ import annotations
import json, sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return 0
    fully_idle = bool(payload.get("fullyIdle", True))
    execution_num = int(payload.get("executionNum") or 0)
    if not fully_idle and execution_num < 2:
        print(json.dumps({
            "decision": "continue",
            "reason": "Background task/subagent is still active. Reconcile or explicitly terminate it before ending the engineering turn."
        }))
    else:
        print(json.dumps({"decision": "allow"}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
