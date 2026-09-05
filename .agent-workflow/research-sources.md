# Antigravity Research Sources — reverified 2026-09-05

## Official primary sources

- Custom agents / subagents: https://antigravity.google/docs/subagents
- CLI background tasks & subagents: https://antigravity.google/docs/cli/subagents/
- `/agents` discovery/monitoring: https://antigravity.google/docs/cli/commands/agents/
- Skills / progressive disclosure: https://antigravity.google/docs/skills/
- Workspace Rules: https://antigravity.google/docs/rules-workflows/
- Hooks schema and tool names: https://antigravity.google/docs/hooks
- Permissions: https://antigravity.google/docs/permissions/
- CLI permissions: https://antigravity.google/docs/cli/permissions
- Headless CLI: https://antigravity.google/docs/cli/headless/
- Antigravity 2.0 feature deep dive: https://antigravity.google/blog/google-io-2026-feature-deep-dive

## Community signals reviewed

Community evidence is used only to identify failure modes worth guarding or testing. It does not supersede official documentation.

- Parallel subagent quota-pressure report (2026-06-30):
  https://www.reddit.com/r/google_antigravity/comments/1ujy5gc/antigravitys_parallel_subagent_architecture_is/
- Antigravity 2.12.0 community release discussion (2026-09-03):
  https://www.reddit.com/r/google_antigravity/comments/1w637hk/antigravity_20_release_v2120/
- Context-management discussion emphasizing bounded context/handoffs (2026-03-13):
  https://www.reddit.com/r/google_antigravity/comments/1rsfx0y/context_management_in_antigravity_gravity/
- Antigravity CLI 1.1.22–1.1.25 release discussion, including Gemini 3.8 Flash/custom-agent inheritance changes (2026-09-03):
  https://www.reddit.com/r/google_antigravity/comments/1w63694/antigravity_cli_release_v1122_v1123/

## Research discipline

- Reverify official sources before material Antigravity upgrades.
- Treat model catalogs, quotas, and tier entitlements as volatile.
- Treat user reports as `COMMUNITY_SIGNAL`, never `UPSTREAM_FACT`.
- Preserve local capability checks for behaviors that official schemas do not fully prove in the user's installed release (especially effective effort inheritance and exact worktree review access).
