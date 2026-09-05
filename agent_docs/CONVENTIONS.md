# CONVENTIONS

- Authority: current user → confirmed REG/ADR → owning docs → code/tests for implementation facts → official upstream facts → community signals.
- Route every engineering task CHAT/MICRO/STANDARD/HEAVY.
- Only Orchestrator delegates; max active subagents 2; workers never delegate.
- STANDARD/HEAVY Builder uses isolated branch/worktree; human merges main.
- Task Capsule before delegated mutation; structured deltas for handoff.
- Builder initial implementation + 2 substantial repairs max. Reviewer-driven repairs 2 max.
- Read-only agents do not repair.
- All engineering roles: Gemini 3.8 Flash High + High effort; fail closed on downgrade.
- Prefer deterministic code for collection/normalization/state and LLM reasoning for interpretation/language.
- SearXNG = discovery; direct HTTP/API = cheapest authoritative acquisition when sufficient; Crawl4AI = default rich acquisition.
- Search snippets are not authoritative evidence.
- Clients Hunter = selective donor migration, never legacy runtime wrap.
- No secrets/raw legacy credential artifacts in repository or model context.
- Update durable docs/state when durable truth changes.
