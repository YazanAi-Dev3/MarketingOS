# Clients Hunter Migration Inventory

| Legacy capability | Decision | New destination / rule |
|---|---|---|
| source-specific adapter pattern | KEEP / GENERALIZE | source adapter layer |
| Mostaql parsing/search knowledge | CLEAN REIMPLEMENT after T-09 | specialized adapter candidate |
| Khamsat parsing/search knowledge | CLEAN REIMPLEMENT after T-09 | specialized adapter candidate |
| Bahr parsing/search knowledge | CLEAN REIMPLEMENT + fix after T-09 | specialized adapter candidate |
| shallow → deep acquisition | KEEP / GENERALIZE | acquisition pipeline |
| URL deduplication | IMPROVE | normalized URL + source ID + entity resolution |
| retry/backoff | KEEP behavior when needed | common acquisition infrastructure |
| keyword lists | REUSE as query hints only | query planner |
| keyword/title relevance classifier | DISCARD | evidence + deterministic filters + Antigravity qualification |
| Firecrawl | DISCARD | Crawl4AI/direct HTTP |
| Firebase | DISCARD | SQLite domain store |
| Streamlit | DISCARD | Hermes CLI/Telegram |
| historical lead data | SANITIZE + CONVERT | regression/evaluation fixtures |
| old orchestrator loop | DISCARD architecture | new staged acquisition/intelligence pipeline |
