# First-use Antigravity Dry Run

This bundle is statically validated, but the following checks require the **installed Antigravity release and your signed-in Google AI Pro account**. Run them before broad autonomous engineering.

## AG-CC-01 — Agent discovery + exact main model

1. Run `agy agents` or open `/agents`.
2. Confirm these workspace agents are discovered: `orchestrator`, `explorer`, `builder`, `verifier`, `reviewer`, `heavy-reviewer`.
3. Run a pinned headless smoke:

```bash
agy -p "Return exactly AG-OK" --agent orchestrator --model gemini-3.8-flash-high --effort high --output-format json
```

Expected: success, exact model slug accepted, no silent fallback.

## AG-CC-02 — Subagent high-effort inheritance (BLOCKING for native mode)

Start Main explicitly on **Gemini 3.8 Flash High** and ask:

> Invoke the explorer only. Read `agent_docs/PROJECT.md` and return its first heading. No edits.

Inspect the subagent detail/metadata/logs exposed by your installed release. Confirm the Explorer is actually running Gemini 3.8 Flash **High**, not Medium.

- If confirmed: native-subagent mode is approved.
- If the installed release does not expose enough evidence or uses Medium: mark native mode `UNPROVEN` and use `scripts/run_antigravity_role.py` for pinned role execution until inheritance can be proven.

Never silently downgrade the user's requested effort.

## AG-CC-03 — Native branch worktree + reviewer visibility

Ask Main to issue a throwaway MICRO/STANDARD smoke capsule that creates `.agent-workflow/smoke/builder-write.txt` containing `ok`, with Builder invoked using `workspace=branch`.

Expected:
- Builder writes only in its candidate worktree.
- `main` remains unchanged.
- Main can identify the candidate worktree/branch.
- Independent Reviewer can inspect the **actual candidate state** without receiving Builder reasoning history.

If Reviewer cannot access the candidate worktree directly, test the fallback review packet: actual `git diff` + changed-file snapshots + capsule + verification evidence.

Delete/reject the smoke candidate after the test.

## AG-CC-04 — Role permission separation

- Explorer: must not edit.
- Reviewer and Heavy Reviewer: must not edit.
- Verifier: may run only named gates and must not repair.
- Builder: may write only inside the assigned capsule/worktree.

## AG-CC-05 — Heavy routing without execution

Ask Main:

> If a task changes Telegram founder authorization and Antigravity credential handling, which route and gates apply? Do not implement and do not spawn Heavy Reviewer merely to answer.

Expected: `HEAVY`, baseline Reviewer, then Heavy Reviewer only when the trigger remains relevant.

## Record results

Update `.agent-workflow/capability-checks.md` with:
- Antigravity 2.0 / CLI version;
- agent discovery;
- exact main model/effort;
- subagent model/effort evidence;
- branch-worktree behavior;
- reviewer candidate visibility;
- any tool/frontmatter warning.
