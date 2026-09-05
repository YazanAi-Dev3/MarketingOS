# Marketing OS Engineering Operating Contract

Configure this workspace rule as **Always On** in Antigravity.

- Use the project-specific `orchestrator` as the primary engineering agent.
- Required engineering model policy: **Gemini 3.8 Flash High, High effort**. Do not silently downgrade. Follow `AG-CC-02` and the pinned runner fallback if inheritance cannot be proven.
- The Orchestrator is the only delegating role. Worker agents do not spawn other agents. Operational delegation depth is 1.
- Maximum active subagents: 2. Do not create agent swarms, invoke `/teamwork-preview`, or use `/boost` as routine workflow.
- Route all work as CHAT, MICRO, STANDARD, or HEAVY according to `.agents/protocols/ROUTING.md`.
- STANDARD and HEAVY mutation work uses an isolated branch/worktree. Human founders perform final merge to trusted `main`.
- Builder has finite repair budget: initial implementation + 2 substantial repairs. Reviewer-driven repair cycles: 2. Repeated identical exploration: 0.
- Read the smallest authoritative context needed. Use Task Capsules for delegated work and structured deltas for handoff. Do not rely on chat history as durable project state.
- When a durable product/architecture/operations contract changes, update the owning documentation and `agent_docs/STATE.md` in the same coherent change.
