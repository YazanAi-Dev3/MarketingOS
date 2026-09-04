# Capability Checks — Antigravity

## Verified from current official Antigravity documentation (2026-09-04)

- Workspace custom agents are discovered under `.agents/agents/<name>/agent.md` (or `<name>.md`).
- `subagent: true` agents can be invoked by a primary agent through `invoke_subagent`.
- Custom frontmatter supports `tools`, `mainAgent`, `subagent`, `model` (`inherit|flash|pro`), `commandExecutionPolicy`, MCP servers, skills/plugins.
- Subagents start with isolated conversation context rather than parent history.
- Native subagent workspace modes include `inherit`, `branch` (isolated Git worktree), and `share`.
- Parent agents retain access to subagent workspaces; permission requests can bubble to the parent UI.
- Workspace rules live under `.agents/rules`; skills live under `.agents/skills`; `AGENTS.md` and `GEMINI.md` are parsed as workspace context.
- CLI headless runs can pin `--model gemini-3.8-flash-high` and `--effort high`; unknown model slugs fail non-zero rather than silently falling back.

## AG-CC-01 — REQUIRED_LOCAL (PASSED)
Confirmed all six custom agents exist and validate via `scripts/verify_control_plane.py` (0 errors, 0 warnings).
Headless run via pinned role-runner with `--agent explorer --model gemini-3.8-flash-high --effort high` succeeded and returned `AG-OK`.

## AG-CC-02 — BLOCKING_NATIVE_MODE (RESOLVED: FALLBACK PINNED RUNNER APPROVED)
Tested `invoke_subagent` for custom subagent `explorer`; runtime returned `subagent "explorer" not found or not allowed to be invoked`.
Native subagent high-effort inheritance is therefore **UNPROVEN / NOT PERMITTED** for custom agents in this CLI environment.
As mandated by policy, the pinned fallback runner `scripts/run_antigravity_role.py` (enforcing `--model gemini-3.8-flash-high --effort high`) is approved and operational. Tested on `explorer` reading `agent_docs/PROJECT.md` and succeeded with returncode 0.

## AG-CC-03 — BLOCKING_NATIVE_REVIEW_PATH (RESOLVED: REVIEW-PACKET FALLBACK APPROVED)
Because custom subagents are routed via the pinned role runner rather than native `invoke_subagent`, candidate review visibility uses the documented review-packet fallback in `WORKTREES.md` (`git diff` + changed-file snapshots + capsule + verification evidence) without sharing builder reasoning history.

### Recorded Environment Facts (2026-09-04)
- Antigravity CLI version: `1.1.19`
- Main Orchestrator Model: `gemini-3.8-flash-high` + `effort: high`
- Engineering Sub-role Execution: `scripts/run_antigravity_role.py` pinning `--model gemini-3.8-flash-high --effort high`
- Control-Plane Status: VERIFIED / OPERATIONAL

