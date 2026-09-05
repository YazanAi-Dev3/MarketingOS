# Git Trust, Scope, and Mutation Rule

Configure this workspace rule as **Always On** in Antigravity.

- Inspect `git status`, current branch, and workspace identity before mutation.
- Trusted `main` is human-integrated. Agents never auto-merge, auto-push, rewrite history, delete worktrees, or run destructive Git cleanup without explicit human approval.
- A candidate has one mutation owner at a time. Never run two Builders against one worktree.
- STANDARD/HEAVY Builder must use an isolated `branch` workspace/worktree. MICRO may use current workspace only when low-risk, reversible, and single-writer.
- Reviewer/Verifier/Heavy Reviewer inspect the actual candidate workspace. If candidate identity/access is ambiguous, they stop BLOCKED rather than inspect the wrong checkout.
- Respect the Task Capsule edit surface. Do not broaden scope to opportunistic refactors. If a broader change is materially required, stop `SCOPE_EXPANDED` and return evidence to Orchestrator.
- Never commit runtime secrets, `.env`, private keys, service-account credentials, raw credential exports, or unsanitized Clients Hunter artifacts/database.
