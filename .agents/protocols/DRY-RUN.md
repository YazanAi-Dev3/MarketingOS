# First-Run Antigravity Dry Run

This package is statically validated, but the following behaviors must be proven on the user's installed Antigravity version.

## AG-CC-01 — Discovery
Open the repository and confirm `orchestrator`, `explorer`, `builder`, `verifier`, `reviewer`, `heavy-reviewer` are discovered. If a custom agent hangs at launch, inspect exact frontmatter tool names first.

## AG-CC-02 — Model + effort inheritance (BLOCKING for native subagents)
Launch `orchestrator` explicitly on Gemini 3.8 Flash High + High effort. Ask it to invoke `explorer` on a harmless read-only repository question. Inspect Antigravity model/usage/session metadata and prove the worker did not silently run a weaker effective configuration.

If High effort inheritance cannot be proven, use:

```bash
python scripts/run_antigravity_role.py explorer "<prompt>"
```

The runner pins `--model gemini-3.8-flash-high --effort high`. Do not silently downgrade.

## AG-CC-03 — Candidate worktree visibility (BLOCKING before STANDARD/HEAVY native flow)
Have Orchestrator invoke Builder using `workspace=branch` for a harmless fixture edit. Confirm:
- a distinct branch/worktree is created;
- parent can identify/access it;
- Reviewer/Verifier can inspect the exact candidate without mutation;
- trusted main remains unchanged;
- cleanup is understood and not automatic-destructive.

## AG-CC-04 — Permissions/hooks
Run `python scripts/test_hooks.py`. In Antigravity, verify a safe file edit is allowed, `.env`/credential write is denied, and a destructive Git command forces human confirmation.

## AG-CC-05 — Delegation limits
Ask Orchestrator for a STANDARD dry task. Confirm it uses no nested worker delegation and never exceeds two active subagents. Use `/agents` to inspect/kill if necessary.

## Passing state
Native control plane is `MATERIALIZATION_READY` only when AG-CC-01..05 are evidenced locally. Until then the package remains policy-valid but capability-gated.
