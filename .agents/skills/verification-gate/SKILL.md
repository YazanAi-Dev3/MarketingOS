---
name: verification-gate
description: Runs independent named verification gates against a specific candidate without repairing it. Use for tests, builds, lint/type checks, migrations, smoke tests, hook negative/positive tests, or environment checks where execution evidence must be independent of the Builder.
---
# Verification Gate Skill

- Verify candidate branch/worktree identity before running commands.
- Run only named non-destructive checks.
- Preserve command, exit status, and concise material evidence.
- Classify failure: candidate-caused, pre-existing, environment blocker, capability blocker, or flaky/indeterminate.
- Do not change repository state to make verification pass.
- External live-source checks must be bounded and separated from deterministic regression tests.
- For a safety guard, test at least one allowed and one prohibited path.

Return `VERIFICATION DELTA` from `.agents/protocols/CONTRACTS.md`.
