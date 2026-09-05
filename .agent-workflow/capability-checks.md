# Antigravity Capability Checks

Status values: `UNRUN`, `PASS`, `FAIL`, `SUPERSEDED`.

| ID | Check | Status | Blocks | Fallback |
|---|---|---|---|---|
| AG-CC-01 | Workspace discovers all six custom agents with valid tools | UNRUN | real delegated workflow | fix definitions; no blind retries |
| AG-CC-02 | Native worker inherits required Gemini 3.8 Flash High effective effort | UNRUN | native subagent mode | pinned role runner |
| AG-CC-03 | Parent/Reviewer/Verifier can inspect exact `workspace=branch` candidate | UNRUN | native STANDARD/HEAVY flow | explicit Git worktree |
| AG-CC-04 | Hooks + permissions deny secrets/destructive action and allow safe work | UNRUN locally; static tests included | trusted mutation | repair guards/settings |
| AG-CC-05 | Orchestrator stays ≤2 active subagents and workers never delegate | UNRUN | cost/control policy | stop/kill offending worker; fix prompts/tools |

Static validation of configuration is not a substitute for these installed-runtime checks.
