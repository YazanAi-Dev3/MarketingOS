#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def check(cond,msg,errors):
    if not cond: errors.append(msg)

def run(name):
    p=subprocess.run([sys.executable,str(ROOT/"scripts"/name)],text=True,capture_output=True)
    return p.returncode,p.stdout+p.stderr

def main():
    errors=[]
    required=[
      "AGENTS.md","GEMINI.md",".agents/hooks.json",".agent-workflow/agent-control-manifest.json",
      ".agents/protocols/ROUTING.md",".agents/protocols/DRY-RUN.md","docs/13-source-acquisition-and-legacy-migration.md",
      "docs/14-antigravity-engineering-environment.md","config/acquisition-policy.example.yaml"
    ]
    for rel in required: check((ROOT/rel).exists(),f"missing {rel}",errors)
    try: manifest=json.loads((ROOT/".agent-workflow/agent-control-manifest.json").read_text(encoding="utf-8"))
    except Exception as e: errors.append(f"manifest parse: {e}"); manifest={}
    roles=manifest.get("roles",[])
    check(len(roles)==6,"manifest must define six roles",errors)
    for r in roles:
        check(r.get("model")=="gemini-3.8-flash-high",f"role {r.get('name')} model mismatch",errors)
        check(r.get("reasoning")=="high",f"role {r.get('name')} effort mismatch",errors)
    try:
        rp=json.loads((ROOT/"config/runtime-providers.json").read_text(encoding="utf-8"))
        runtime=rp["runtime_reasoning"]
        forbidden=set(rp["forbidden_runtime_providers"])
        check(runtime["preferred"]=="antigravity","runtime preferred provider must be antigravity",errors)
        check(runtime["fallback"]=="gemini_api","runtime fallback must be gemini_api",errors)
        check(runtime["paid_usage_allowed"] is False,"paid runtime usage must default false",errors)
        check({"codex","openai","chatgpt"}.issubset(forbidden),"runtime forbidden provider list incomplete",errors)
    except Exception as e: errors.append(f"runtime provider config: {e}")
    for script in ["validate_agent_definitions.py","scan_for_secrets.py"]:
        rc,out=run(script)
        if rc: errors.append(f"{script} failed:\n{out}")
    # No Codex harness or legacy workflow directory.
    check(not (ROOT/".codex").exists(),".codex must not exist in Antigravity control plane",errors)
    check(not (ROOT/".agents"/"workflow").exists(),"legacy .agents/workflow must not exist",errors)
    if errors:
        print("CONTROL PLANE FAIL")
        for e in errors: print("-",e)
        return 1
    print("PASS: Marketing OS Antigravity control plane static checks")
    return 0
if __name__ == "__main__": raise SystemExit(main())
