---
name: worktree-protocol
description: Enforces isolated Git branch/worktree ownership, single-writer behavior, candidate identity, review access, and human final integration for STANDARD and HEAVY engineering work.
---
# Worktree Protocol Skill

## Rules

- Trusted `main` remains human-integrated.
- STANDARD/HEAVY Builder: invoke with `workspace=branch` when native behavior passes local capability checks.
- One mutation owner per candidate.
- Record branch/worktree identity in every Knowledge Delta.
- Verifier/Reviewer receive the candidate identity and must prove they inspect it.
- No automatic merge/push/rebase/history rewrite/worktree deletion.
- If native cross-agent worktree visibility differs from documented behavior on the installed version, stop and use an explicit local Git worktree workflow rather than guessing.

## Completion

A candidate is review-ready, not integrated. Human decides final merge after required gates pass.
