#!/usr/bin/env python3
"""Validate a generated agent-control manifest and selected filesystem invariants.

This validator is intentionally platform-neutral. Platform-specific syntax checks
must be added/run separately and reported truthfully.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

READ_ONLY_ARCHETYPES = {"EXPLORER", "REVIEWER", "VERIFIER", "HEAVY_REVIEWER", "DOMAIN_AUDITOR", "DOC_AUDITOR"}
WRITE_WORDS = {"write", "workspace-write", "mutate", "trusted-write", "repository-write"}


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def contains_write_permission(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        low = value.lower()
        return any(w in low for w in WRITE_WORDS)
    if isinstance(value, list):
        return any(contains_write_permission(v) for v in value)
    if isinstance(value, dict):
        return any(contains_write_permission(v) for v in value.values())
    return False


def load_manifest(root: Path) -> tuple[Path, dict]:
    candidates = [
        root / ".agent-workflow" / "agent-control-manifest.json",
        root / "agent-control-manifest.json",
    ]
    for p in candidates:
        if p.exists():
            return p, json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("agent-control-manifest.json not found")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="Generated project/control-plane root")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest_path, m = load_manifest(root)
    except Exception as e:
        print(f"FAIL: {e}")
        return 2

    required_top = ["schema_version", "project", "platform", "authority", "trust", "roles", "routes", "verification", "repair_budgets", "guards", "durable_state", "unresolved"]
    for key in required_top:
        if key not in m:
            fail(errors, f"manifest missing top-level key: {key}")

    roles = m.get("roles") or []
    names: list[str] = []
    archetype_by_name: dict[str, str] = {}
    for i, role in enumerate(roles):
        if not isinstance(role, dict):
            fail(errors, f"roles[{i}] is not an object")
            continue
        name = role.get("name") or role.get("id")
        archetype = str(role.get("archetype") or "").upper()
        if not name:
            fail(errors, f"roles[{i}] has no name/id")
            continue
        if name in names:
            fail(errors, f"duplicate role name: {name}")
        names.append(name)
        archetype_by_name[name] = archetype
        if archetype in READ_ONLY_ARCHETYPES and contains_write_permission(role.get("permissions")):
            fail(errors, f"read-only archetype {archetype} ({name}) appears write-capable")
        if archetype == "BUILDER" and not role.get("edit_boundary") and not role.get("permissions"):
            warnings.append(f"builder {name} has no explicit edit boundary/permissions")
        if not role.get("output_contract"):
            warnings.append(f"role {name} has no explicit output_contract")

    known_roles = set(names) | {"ORCHESTRATOR", "MAIN"}
    for i, route in enumerate(m.get("routes") or []):
        if not isinstance(route, dict):
            fail(errors, f"routes[{i}] is not an object")
            continue
        seq = route.get("sequence") or route.get("flow") or role_seq(route)
        if isinstance(seq, list):
            for ref in seq:
                if not isinstance(ref, str):
                    continue
                clean = ref.replace("optional ", "").replace("conditional ", "").strip()
                # Archetype labels are allowed when the renderer resolves them later.
                if clean and clean not in known_roles and clean.upper() not in {"EXPLORER","BUILDER","REVIEWER","VERIFIER","HEAVY_REVIEWER","INTEGRATOR","ORCHESTRATOR"}:
                    warnings.append(f"route {route.get('name') or route.get('id') or i} references unresolved role/archetype: {ref}")
        if not route.get("entry_conditions") and not route.get("entry"):
            warnings.append(f"route {route.get('name') or route.get('id') or i} lacks entry conditions")

    budgets = m.get("repair_budgets") or {}
    for key, value in budgets.items():
        if not isinstance(value, int) or value < 0:
            fail(errors, f"repair budget {key} must be a finite non-negative integer")
        elif value > 10:
            warnings.append(f"repair budget {key}={value} is unusually high; verify anti-runaway intent")

    for i, guard in enumerate(m.get("guards") or []):
        if not isinstance(guard, dict):
            fail(errors, f"guards[{i}] is not an object")
            continue
        if not guard.get("source_invariant"):
            fail(errors, f"guard[{i}] has no source_invariant")
        blocking = guard.get("blocking") is True or str(guard.get("blocking", "")).lower() in {"true", "block", "blocking", "fail_closed"}
        if blocking and not guard.get("self_tests"):
            fail(errors, f"blocking guard {guard.get('name') or i} has no self_tests")
        if not guard.get("mechanical_predicate"):
            warnings.append(f"guard {guard.get('name') or i} has no mechanical_predicate")

    auth = m.get("authority") or {}
    if not auth.get("sources"):
        warnings.append("authority.sources is empty")
    if not auth.get("decision_owner"):
        warnings.append("authority.decision_owner is empty")

    trust = m.get("trust") or {}
    if trust.get("integration_mode") in (None, "", "UNRESOLVED"):
        warnings.append("trust.integration_mode unresolved")

    unresolved = m.get("unresolved") or []
    if unresolved:
        warnings.append(f"manifest has {len(unresolved)} unresolved item(s); BOOTSTRAP_READY may be false")

    print(f"Manifest: {manifest_path}")
    if errors:
        print("\nERRORS")
        for e in errors:
            print(f"- {e}")
    if warnings:
        print("\nWARNINGS")
        for w in warnings:
            print(f"- {w}")
    if errors:
        print(f"\nFAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nPASS: 0 errors, {len(warnings)} warning(s)")
    return 0


def role_seq(route: dict):
    return route.get("default_flow") or []


if __name__ == "__main__":
    raise SystemExit(main())
