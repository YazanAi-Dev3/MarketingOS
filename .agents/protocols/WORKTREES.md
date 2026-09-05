# Worktree and Integration Protocol

1. Before mutation, record `git status`, branch and repository root.
2. MICRO may mutate current workspace only when explicitly eligible, single-writer and reversible.
3. STANDARD/HEAVY Builder uses Antigravity `workspace=branch` after `AG-CC-03` proves installed-version worktree visibility semantics.
4. Record candidate branch/worktree in Knowledge Delta.
5. Reviewer/Verifier receive the candidate identity, not only a summary.
6. Human founders perform final merge to trusted `main`.
7. Never auto-push, auto-merge, `reset --hard`, destructive `clean`, delete worktrees or rewrite history.
8. If native branch/worktree behavior is not proven, use explicit Git worktrees and keep the same trust policy.
