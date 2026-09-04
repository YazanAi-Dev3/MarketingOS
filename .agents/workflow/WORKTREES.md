# Git and Worktree Policy — Antigravity

## Trust model

- `main` is trusted integration history.
- STANDARD/HEAVY Builder output is an **untrusted candidate** until independent review passes.
- A worktree isolates mutation; it does not certify correctness.
- Founders perform final merge in V1. No agent auto-merges.

## Native Antigravity workspace policy

Antigravity subagents can be invoked with workspace modes `inherit`, `branch`, or `share`.

- `MICRO`: Builder may use `workspace=inherit` only when the change is localized, reversible, low-risk, and no second writer exists. If uncertain, use `branch`.
- `STANDARD`: Builder **must** use `workspace=branch` so Antigravity creates an isolated Git worktree.
- `HEAVY`: Builder **must** use `workspace=branch`; keep the candidate stable during verification/review.
- Never run two write-capable agents in one worktree.
- Parallel writers are allowed only in separate worktrees with disjoint edit surfaces and an explicit composition plan.

## Reviewer access to candidate state

Preferred: Reviewer/Verifier inspect the candidate worktree path or candidate diff supplied by Main, without receiving Builder narration.

Because peer-subagent worktree visibility can vary by installed release, `AG-CC-03` in `DRY-RUN.md` must verify that an independent Reviewer can read the Builder candidate. If not, use the documented fallback: Main exports the actual candidate diff plus changed-file snapshots and named verification evidence into a review capsule. Do not weaken reviewer independence by forwarding Builder reasoning history.

## Cleanup

Antigravity cleans temporary worktrees when a subagent is killed, but do not terminate/clean a reviewed candidate until founders confirm merge or rejection. Record candidate identity in the KNOWLEDGE DELTA.
