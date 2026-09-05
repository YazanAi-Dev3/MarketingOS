# Marketing OS — Engineering Authority Router

This repository uses **Google Antigravity custom agents** as its engineering control plane. The primary agent is `.agents/agents/orchestrator/agent.md`.

## Start here

1. Read `agent_docs/STATE.md`.
2. Use `docs/00-document-index.md` to load only the owning project documents.
3. Apply the three `.agents/rules/*.md` workspace rules as **Always On**.
4. Route work with `.agents/protocols/ROUTING.md`.
5. Delegate mutation only through bounded Task Capsules.

## Non-negotiable engineering policy

- All engineering roles target **Gemini 3.8 Flash High + High effort**. No silent downgrade.
- Only Orchestrator delegates. Workers do not spawn workers. Max active subagents = 2.
- STANDARD/HEAVY mutations occur in isolated branch/worktrees; final merge to `main` is human.
- Builder repair budget = 2 substantial repairs; reviewer-driven repair cycles = 2; repeated same-question exploration = 0.
- Read-only roles never repair.
- Do not rely on long chat history as project memory; use Task Capsules and durable `agent_docs`.

## Product/runtime invariants

- Hermes is the product base; extend before forking.
- Marketing runtime reasoning is Google-only: Antigravity preferred, Gemini API fallback if needed and allowed. Codex/OpenAI/ChatGPT are prohibited product-runtime providers.
- Marketing domain state is independent from Hermes conversational memory.
- SearXNG discovers; page acquisition establishes evidence.
- Crawl4AI is the primary rich web acquisition/rendering/extraction engine; direct HTTP/API is preferred when cheaper/sufficient.
- Clients Hunter is a donor codebase for selective migration, not a runtime dependency.
- Raw legacy secrets/archive/database are quarantined.
- Public external actions require human approval initially.

Critical deterministic protections live in `.agents/hooks.json` and Antigravity Permissions; prompts are not the only security boundary.
