# Final Workflow Review — Antigravity Port

## Verdict

- **POLICY_READY:** PASS
- **STATIC_MATERIALIZATION_READY:** PASS
- **NATIVE_SUBAGENT_READY:** CONDITIONAL on AG-CC-02 and AG-CC-03 local dry run
- **FALLBACK_READY:** PASS — pinned role runner can force `gemini-3.8-flash-high` + `high` for individual role executions if native inheritance is unproven.

## Topology

Six roles only: Orchestrator, Explorer, Builder, Verifier, Reviewer, Heavy Reviewer. Deep Builder was removed because the same model would provide no capability escalation; failure returns to Main for re-scope/clean Builder.

## Quality and cost

All roles intentionally use Gemini 3.8 Flash High. Cost/quota control therefore comes from route selection, compact capsules, finite repair budgets, max-two-active-subagent policy, clean-context independent review, and trigger-only Heavy Reviewer—not from model tier switching.

## Native Antigravity advantages used

- project-scoped custom agents;
- clean subagent context;
- native branch worktrees;
- scoped tools/command policies;
- skills/rules;
- CLI exact model/effort pinning.

## Residual risks

1. High effort inheritance for native subagents is not statically expressible in current custom-agent frontmatter: AG-CC-02.
2. Candidate worktree visibility to independent review roles must be proven on the installed release: AG-CC-03.
3. Numeric max-concurrency is a workflow policy, not a discovered project-scoped configuration field; Main must enforce <=2 active subagents.
4. Product-specific test/lint/type/eval commands do not exist yet.

## First execution

After local dry run, execute `T-08`, then `T-01`. Do not jump to broad marketing features.
