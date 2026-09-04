# DOCUMENTATION DELTA — Antigravity Port

**Product architecture/security/business decisions changed:** NONE.

**Engineering execution-control change:** the current engineering harness is now Google Antigravity instead of Codex. Product runtime decisions remain Google-only and `A-031` continues to reject Codex/OpenAI/ChatGPT as marketer runtime providers.

**New workflow decisions:**
- all engineering roles = Gemini 3.8 Flash High;
- native custom agents under `.agents/agents/`;
- no permanent Deep Builder;
- STANDARD/HEAVY Builder uses native `workspace=branch`;
- active subagent policy cap = 2;
- native effort inheritance requires AG-CC-02; pinned role runner is fail-closed fallback.

`docs/11-ai-coding-agent-setup.md` and document-index inventory entries were updated to reflect the current engineering harness. Other product documents retain Codex references where they describe the explicit runtime rejection/history.
