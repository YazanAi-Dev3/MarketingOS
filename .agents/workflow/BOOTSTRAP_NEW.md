# Greenfield Bootstrap — Antigravity

1. Place this bundle at the repository root so `AGENTS.md`, `GEMINI.md`, `.agents/`, `docs/`, `config/`, and `agent_docs/` share one root.
2. Initialize Git if needed and create the trusted `main` branch.
3. Run the static control-plane validator:
   ```bash
   python scripts/verify_control_plane.py
   ```
4. Open the project in Antigravity 2.0 / Antigravity CLI from the repository root.
5. Select the custom `orchestrator` agent.
6. Select **Gemini 3.8 Flash (High)**. In headless runs pin `--model gemini-3.8-flash-high --effort high`.
7. Run `.agents/workflow/DRY-RUN.md` once before broad autonomous engineering. This specifically checks subagent model/effort inheritance and candidate worktree review access.
8. If high-effort inheritance cannot be proven, switch to the included pinned role runner rather than accepting silent Medium effort.
9. Begin with the smallest Phase 0 unit in `docs/10-preimplementation-plan.md` (`T-08`, then `T-01`).
10. Update `agent_docs/STATE.md` after each coherent closure.

Do not reconstruct missing implementation history in a greenfield repo. Do not let bootstrap become a broad refactor.
