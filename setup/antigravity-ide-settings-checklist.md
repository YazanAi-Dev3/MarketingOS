# Antigravity Workspace Setup Checklist

This is a checklist, not a settings file. UI labels may move between releases.

1. Open this repository as the workspace root so `.agents/` is discoverable.
2. Select custom main agent `orchestrator`.
3. Select **Gemini 3.8 Flash High** and **High effort** for the main session.
4. In Customizations → Rules, configure these three workspace rules as **Always On**:
   - `00-operating-contract.md`
   - `10-git-trust-and-scope.md`
   - `20-security-runtime-boundaries.md`
5. Confirm `.agents/hooks.json` is active. Run `python scripts/test_hooks.py` before trusting it.
6. Review `/permissions`; do not globally auto-approve all commands/MCP/web actions. Use scoped grants.
7. Do not make `/teamwork-preview` or `/boost` part of routine workflow. The repository uses explicit custom roles and max two active subagents.
8. Run `.agents/protocols/DRY-RUN.md` before STANDARD/HEAVY implementation.
9. On Windows, do not assume OS-level terminal sandbox enforcement is identical to macOS/Linux preview behavior; retain Permissions + Hooks as critical controls.
10. After any Antigravity upgrade, rerun agent discovery, model/effort inheritance, worktree visibility and hook tests.
