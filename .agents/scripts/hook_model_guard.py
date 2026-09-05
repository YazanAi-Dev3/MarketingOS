#!/usr/bin/env python3
"""Antigravity PostInvocation guard for required engineering model identity.
Effort is additionally gated by AG-CC-02 because current hook metadata exposes modelName, not a separate effort field.
"""
from __future__ import annotations
import json, re, sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(json.dumps({
            "injectSteps": [{"ephemeralMessage": f"MODEL_GUARD_PARSE_FAILURE: {exc}"}],
            "terminationBehavior": "terminate"
        }))
        return 0

    raw = str(payload.get("modelName") or "").strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")

    # Current target is Gemini 3.8 Flash High. Accept canonical/friendly variants only.
    okay = bool(re.search(r"gemini.*3[-.]?8.*flash.*high", normalized))
    if not okay:
        print(json.dumps({
            "injectSteps": [{
                "ephemeralMessage": (
                    "MODEL_POLICY_VIOLATION: Marketing OS engineering roles require Gemini 3.8 Flash High. "
                    f"Observed modelName={raw!r}. Terminating rather than silently downgrading. "
                    "If the installed Antigravity release reports a different canonical identifier for the same model, "
                    "update this guard only after AG-CC-02 proves the mapping."
                )
            }],
            "terminationBehavior": "terminate"
        }, ensure_ascii=False))
    else:
        print(json.dumps({"injectSteps": [], "terminationBehavior": ""}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
