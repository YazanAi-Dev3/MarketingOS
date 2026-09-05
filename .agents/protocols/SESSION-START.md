# Session Start Protocol

1. Select workspace agent `orchestrator`.
2. Confirm main model is Gemini 3.8 Flash High with High effort.
3. Confirm the three workspace rules are configured **Always On**.
4. Read `agent_docs/STATE.md` and only the owning docs for the current request.
5. Run `python scripts/verify_control_plane.py` after control-plane changes.
6. Before first real implementation, complete capability checks in `.agent-workflow/capability-checks.md`.
7. For a new substantial task, have Orchestrator classify route and produce/issue a capsule; do not directly start with Builder.
