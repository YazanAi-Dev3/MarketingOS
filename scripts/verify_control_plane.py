#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]
def err(x): errors.append(x)
def warn(x): warnings.append(x)
def load_json(p):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e: err(f"cannot parse JSON {p.relative_to(ROOT)}: {e}"); return {}

def frontmatter(p: Path):
    s=p.read_text(encoding="utf-8")
    if not s.startswith("---\n"): err(f"{p.relative_to(ROOT)} missing YAML frontmatter"); return "",{}
    try: head,body=s[4:].split("\n---\n",1)
    except ValueError: err(f"{p.relative_to(ROOT)} unclosed YAML frontmatter"); return "",{}
    data={}; current=None
    for raw in head.splitlines():
        if re.match(r"^\s+-\s+",raw) and current:
            data.setdefault(current,[]).append(raw.split("-",1)[1].strip()); continue
        m=re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$",raw)
        if not m: continue
        k,v=m.groups(); current=k
        if v=="": data[k]=[]
        elif v.lower() in {"true","false"}: data[k]=v.lower()=="true"
        else: data[k]=v.strip('"\'')
    return body,data

def verify_provider(obj,label):
    rr=obj.get("runtime_reasoning",{})
    if rr.get("preferred")!="antigravity": err(f"{label}: preferred must be antigravity")
    if rr.get("fallback")!="gemini_api": err(f"{label}: fallback must be gemini_api")
    if rr.get("paid_usage_allowed") is not False: err(f"{label}: paid_usage_allowed must be false")
    forbidden={str(x).lower() for x in obj.get("forbidden_runtime_providers",[])}
    enabled=[rr.get("preferred"), rr.get("fallback") if rr.get("fallback_enabled") else None]
    for x in enabled:
        if x and str(x).lower() in forbidden: err(f"{label}: forbidden runtime provider enabled: {x}")

m=load_json(ROOT/".agent-workflow/agent-control-manifest.json")
for k in ["schema_version","project","platform","authority","trust","roles","routes","verification","repair_budgets","guards","durable_state","unresolved"]:
    if k not in m: err(f"manifest missing {k}")
plat=m.get("platform",{})
if plat.get("name")!="antigravity": err("manifest platform must be antigravity")
if plat.get("engineering_model")!="gemini-3.8-flash-high": err("engineering model pin wrong")
if plat.get("engineering_effort")!="high": err("engineering effort must be high")
if plat.get("max_active_subagents_policy")!=2: err("active subagent policy cap must be 2")

expected={
 "orchestrator":{"main":True,"sub":False,"policy":"sandbox","tools":{"view_file","grep_search","replace_file_content","run_command","manage_task","invoke_subagent"}},
 "explorer":{"main":False,"sub":True,"policy":"off","tools":{"view_file","grep_search"}},
 "builder":{"main":False,"sub":True,"policy":"auto","tools":{"view_file","grep_search","replace_file_content","run_command","manage_task"}},
 "verifier":{"main":False,"sub":True,"policy":"auto","tools":{"view_file","grep_search","run_command"}},
 "reviewer":{"main":False,"sub":True,"policy":"off","tools":{"view_file","grep_search"}},
 "heavy-reviewer":{"main":False,"sub":True,"policy":"off","tools":{"view_file","grep_search"}},
}
approved_tools=set().union(*(x["tools"] for x in expected.values()))
for name,cfg in expected.items():
    p=ROOT/".agents/agents"/name/"agent.md"
    if not p.exists(): err(f"missing custom agent {name}"); continue
    body,d=frontmatter(p)
    if d.get("name")!=name: err(f"{name}: frontmatter name mismatch")
    if d.get("mainAgent") is not cfg["main"]: err(f"{name}: mainAgent wrong")
    if d.get("subagent") is not cfg["sub"]: err(f"{name}: subagent wrong")
    if d.get("model")!="inherit": err(f"{name}: model must be inherit")
    if d.get("commandExecutionPolicy")!=cfg["policy"]: err(f"{name}: commandExecutionPolicy wrong")
    tools=set(d.get("tools",[]))
    if tools!=cfg["tools"]: err(f"{name}: toolset mismatch {sorted(tools)}")
    if not tools <= approved_tools: err(f"{name}: unknown tool")
    if not body.strip(): err(f"{name}: empty system prompt")
if (ROOT/".agents/agents/deep-builder").exists() or (ROOT/".agents/agents/deep_builder").exists(): err("permanent deep-builder must not exist")
if (ROOT/".codex").exists(): err(".codex adapter must be absent from Antigravity bundle")

roles=m.get("roles",[])
if {r.get("name") for r in roles} != set(expected): err("manifest roles must exactly match six Antigravity roles")
for r in roles:
    if r.get("model")!="gemini-3.8-flash-high" or r.get("reasoning")!="high": err(f"manifest role {r.get('name')} not pinned conceptually to 3.8 Flash High")
    if str(r.get("archetype","")).upper() in {"EXPLORER","VERIFIER","REVIEWER","HEAVY_REVIEWER"} and "write" in str(r.get("permissions","")).lower(): err(f"read-only role appears write-capable: {r.get('name')}")

for k,v in (m.get("repair_budgets") or {}).items():
    if not isinstance(v,int) or v<0: err(f"invalid repair budget {k}={v!r}")
if "deep_builder_repair_attempts" in (m.get("repair_budgets") or {}): err("deep_builder budget must be removed")

required=["AGENTS.md","GEMINI.md",".agents/workflow/ROUTING.md",".agents/workflow/CONTRACTS.md",".agents/workflow/TASK-CAPSULE.md",".agents/workflow/WORKTREES.md",".agents/workflow/DRY-RUN.md","agent_docs/PROJECT.md","agent_docs/CONVENTIONS.md","agent_docs/DECISIONS.md","agent_docs/STATE.md","scripts/run_antigravity_role.py","scripts/run_antigravity_role.ps1"]
for rel in required:
    if not (ROOT/rel).exists(): err(f"missing required file: {rel}")

runner=(ROOT/"scripts/run_antigravity_role.py").read_text(encoding="utf-8") if (ROOT/"scripts/run_antigravity_role.py").exists() else ""
for needle in ["gemini-3.8-flash-high","EFFORT = \"high\"","--agent","--model","--effort"]:
    if needle not in runner: err(f"pinned role runner missing {needle}")

policy=load_json(ROOT/"config/runtime-providers.json"); verify_provider(policy,"runtime provider policy")
# Negative fixture must be detected by local logic.
bad={"runtime_reasoning":{"preferred":"codex","fallback":"gemini_api","fallback_enabled":False,"paid_usage_allowed":False},"forbidden_runtime_providers":["codex","openai","chatgpt"]}
local=[]
if bad["runtime_reasoning"]["preferred"]!="antigravity": local.append(1)
if bad["runtime_reasoning"]["preferred"] in bad["forbidden_runtime_providers"]: local.append(1)
if len(local)<2: err("provider negative self-test failed")

# Control-plane wording checks.
ag=(ROOT/"AGENTS.md").read_text(encoding="utf-8")
if "Gemini 3.8 Flash High" not in ag: err("AGENTS missing required engineering model")
if "At most **2 active subagents**" not in ag: err("AGENTS missing concurrency policy")
if "no permanent deep-builder" not in ag.lower(): err("AGENTS missing no-deep-builder rule")

print(f"Root: {ROOT}")
if errors:
    print("\nERRORS"); [print("-",x) for x in errors]
if warnings:
    print("\nWARNINGS"); [print("-",x) for x in warnings]
if errors:
    print(f"\nFAIL: {len(errors)} error(s), {len(warnings)} warning(s)"); sys.exit(1)
print(f"\nPASS: 0 errors, {len(warnings)} warning(s)")
