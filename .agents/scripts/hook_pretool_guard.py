#!/usr/bin/env python3
"""Antigravity PreToolUse safety guard for Marketing OS.
Reads official hook JSON from stdin and returns decision JSON on stdout.
"""
from __future__ import annotations
import json, os, re, sys

SECRET_PATH_PATTERNS = [
    r"(^|[\\/])\.env($|[.\\/])",
    r"(^|[\\/])[^\\/]*(service[-_ ]?account|credentials?|private[-_ ]?key)[^\\/]*\.(json|pem|key|p12|pfx)$",
    r"(^|[\\/])id_(rsa|ed25519)(\.pub)?$",
]
RAW_LEGACY_PATTERNS = [
    r"clients[-_ ]hunter.*\.zip$",
    r"freelance_leads\.db$",
    r"clients[-_ ]hunter.*\.(db|sqlite|sqlite3)$",
]
DESTRUCTIVE_COMMANDS = [
    r"\bgit\s+push\b", r"\bgit\s+merge\b", r"\bgit\s+rebase\b",
    r"\bgit\s+reset\s+--hard\b", r"\bgit\s+clean\b",
    r"\bgit\s+branch\s+-[dD]\b", r"\bgit\s+worktree\s+remove\b",
    r"\brm\s+-[^\n]*r[^\n]*f\b", r"\bsudo\b",
]
SECRET_READ_COMMANDS = [
    r"\b(cat|type|more|less|head|tail|grep|rg|findstr|copy|cp)\b[^\n]*(\.env|service[-_ ]?account|credentials?|private[-_ ]?key|id_rsa|id_ed25519)",
]


def emit(decision: str, reason: str = "") -> None:
    print(json.dumps({"decision": decision, "reason": reason}, ensure_ascii=False))


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def matches_any(text: str, patterns) -> bool:
    t = text.replace("\\", "/")
    return any(re.search(p, t, re.I) for p in patterns)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        emit("deny", f"Safety hook could not parse input: {exc}")
        return 0

    call = payload.get("toolCall") or {}
    name = str(call.get("name") or "")
    args = call.get("args") or {}
    values = list(strings(args))
    joined = "\n".join(values)

    # Direct file reads/writes to credential-like files are denied, not merely prompted.
    if name in {"view_file", "write_to_file", "replace_file_content", "multi_replace_file_content"}:
        if any(matches_any(v, SECRET_PATH_PATTERNS) for v in values):
            emit("deny", "Marketing OS policy forbids agent access to credential/secret files. Use sanitized configuration examples only.")
            return 0
        if name != "view_file" and any(matches_any(v, RAW_LEGACY_PATTERNS) for v in values):
            emit("deny", "Raw Clients Hunter archives/databases are quarantined and may not be copied into tracked project state.")
            return 0

    if name == "run_command":
        if matches_any(joined, SECRET_READ_COMMANDS):
            emit("deny", "Command appears to read/copy credential material. Secret contents must not enter agent context.")
            return 0
        if any(re.search(p, joined, re.I) for p in DESTRUCTIVE_COMMANDS):
            emit("force_ask", "Destructive/integrating Git or privileged filesystem command requires explicit human approval.")
            return 0
        # Prevent common direct attempts to ingest quarantined raw legacy assets.
        if matches_any(joined, RAW_LEGACY_PATTERNS) and re.search(r"\b(cp|copy|move|mv|tar|unzip|7z|python)\b", joined, re.I):
            emit("force_ask", "Raw legacy artifact handling requires explicit human approval and a sanitization plan.")
            return 0

    emit("allow", "Marketing OS pre-tool safety checks passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
