#!/usr/bin/env python3
"""Conservative repository secret/quarantine scanner with low false-positive patterns."""
from __future__ import annotations
import re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKIP={".git",".venv","venv","__pycache__","tests"}
BAD_BASENAMES={".env","firebase-service-account.json","service-account.json","credentials.json"}
BAD_SUFFIXES={".pem",".p12",".pfx"}
KEY_PATTERNS=[
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]
LEGACY_RAW=[re.compile(r"clients[-_ ]hunter.*\.zip$",re.I),re.compile(r"freelance_leads\.db$",re.I)]

def main():
    errors=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in SKIP for part in p.parts): continue
        rel=p.relative_to(ROOT).as_posix()
        name=p.name.lower()
        if name in BAD_BASENAMES or p.suffix.lower() in BAD_SUFFIXES:
            errors.append(f"forbidden credential-like filename: {rel}"); continue
        if any(r.search(rel) for r in LEGACY_RAW):
            errors.append(f"raw legacy artifact prohibited: {rel}"); continue
        if p.stat().st_size > 3_000_000: continue
        try: text=p.read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        for r in KEY_PATTERNS:
            if r.search(text): errors.append(f"credential fingerprint detected: {rel}"); break
    if errors:
        print("SECRET/QUARANTINE SCAN FAIL")
        for e in errors: print("-",e)
        return 1
    print("PASS: no credential fingerprints or prohibited raw legacy artifacts detected")
    return 0
if __name__ == "__main__": raise SystemExit(main())
