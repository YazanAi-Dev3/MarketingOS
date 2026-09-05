# DECISIONS — Engineering Working Summary

This file summarizes confirmed durable decisions; canonical IDs live in `docs/06-coordination-master-register.md`.

- Hermes extension-first; do not rebuild runtime or fork core without a new accepted decision.
- Product reasoning Google-only; Codex/OpenAI runtime rejected.
- SQLite + raw artifact filesystem own marketing domain state in MVP.
- Manual country priorities; agent may recommend but not auto-change them.
- Human approval gates initial public publishing/outreach.
- SearXNG dynamic discovery + evidence-oriented page acquisition.
- Crawl4AI primary rich web acquisition; direct public API/HTTP preferred when simpler; BeautifulSoup/lxml parser utilities only.
- Clients Hunter selective architectural migration + clean reimplementation; legacy application not a dependency.
- Mostaql/Khamsat/Bahr candidate specialized adapters require current-site revalidation.
- All engineering custom roles target Gemini 3.8 Flash High + High effort; only Orchestrator delegates; max active subagents 2.
