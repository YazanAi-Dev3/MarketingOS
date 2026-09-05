#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".agents" / "agents"
OFFICIAL_TOOLS = {
    "view_file","write_to_file","replace_file_content","multi_replace_file_content","list_dir","find_by_name",
    "grep_search","search_web","read_url_content","run_command","manage_task","schedule","list_permissions",
    "ask_permission","invoke_subagent","define_subagent","send_message","manage_subagents","ask_question","generate_image"
}
EXPECTED = {"orchestrator","explorer","builder","verifier","reviewer","heavy-reviewer"}
READ_ONLY = {"explorer","verifier","reviewer","heavy-reviewer"}
WRITE_TOOLS = {"write_to_file","replace_file_content","multi_replace_file_content"}


def frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    return yaml.safe_load(text[4:end]) or {}, text[end+5:]


def main() -> int:
    errors=[]; warnings=[]
    found={p.parent.name:p for p in AGENTS.glob("*/agent.md")}
    if set(found) != EXPECTED:
        errors.append(f"agent set mismatch: found={sorted(found)} expected={sorted(EXPECTED)}")
    for name,path in sorted(found.items()):
        try: fm, body=frontmatter(path)
        except Exception as e:
            errors.append(f"{name}: {e}"); continue
        if fm.get("name") != name: errors.append(f"{name}: frontmatter name mismatch")
        desc=str(fm.get("description") or "")
        if len(desc) < 180: errors.append(f"{name}: description too weak/short ({len(desc)} chars)")
        tools=set(fm.get("tools") or [])
        unknown=tools-OFFICIAL_TOOLS
        if unknown: errors.append(f"{name}: undocumented tool name(s): {sorted(unknown)}")
        if name in READ_ONLY and tools & WRITE_TOOLS: errors.append(f"{name}: read-only role has write tools {sorted(tools & WRITE_TOOLS)}")
        if name != "orchestrator" and ("invoke_subagent" in tools or "define_subagent" in tools):
            errors.append(f"{name}: worker delegation forbidden")
        if name == "orchestrator" and "invoke_subagent" not in tools: errors.append("orchestrator lacks invoke_subagent")
        if fm.get("model") != "inherit": errors.append(f"{name}: model must be inherit; main/pinned runner control exact model")
        if fm.get("commandExecutionPolicy") not in {"off","sandbox"}: warnings.append(f"{name}: commandExecutionPolicy={fm.get('commandExecutionPolicy')} is broader than preferred")
        if len(body.strip().splitlines()) < 18: errors.append(f"{name}: system prompt remains too terse")
    rule_files=list((ROOT/".agents"/"rules").glob("*.md"))
    if len(rule_files) != 3: errors.append(f"expected exactly 3 focused workspace rules, found {len(rule_files)}")
    for p in rule_files:
        if len(p.read_text(encoding="utf-8")) > 12000: errors.append(f"rule exceeds documented 12k character limit: {p.name}")
    if (ROOT/".agents"/"workflow").exists() or (ROOT/".agents"/"workflows").exists():
        errors.append("legacy .agents/workflow(s) directory should not exist; use skills + protocols")
    hooks=json.loads((ROOT/".agents"/"hooks.json").read_text(encoding="utf-8"))
    if not hooks: errors.append("hooks.json empty")
    print("Agent definition validation")
    for e in errors: print("ERROR:",e)
    for w in warnings: print("WARN:",w)
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)"); return 1
    print(f"PASS: 0 errors, {len(warnings)} warning(s)"); return 0

if __name__ == "__main__": raise SystemExit(main())
