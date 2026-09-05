# Antigravity Official Capability Matrix

Verified against Google Antigravity documentation on 2026-09-05.

| Capability | Current documented behavior | Project use |
|---|---|---|
| Workspace custom agents | `.agents/agents/<name>.md` or `<name>/agent.md`; YAML frontmatter | six fixed roles |
| Planner delegation | `description` is used to decide when to delegate | descriptions are deliberately detailed |
| Tool allowlist | exact `tools` list; invalid names can hang a subagent | only documented tool names are used |
| Subagent context | starts with clean context, not parent conversation history | strict Task Capsules / deltas |
| Workspaces | `inherit`, `branch`, `share` | `branch` for STANDARD/HEAVY Builder |
| Skills | `.agents/skills/*/SKILL.md`, progressive disclosure | focused procedural knowledge |
| Rules | `.agents/rules`, max 12k chars each; activation configured per rule | three rules intended Always On |
| Hooks | `.agents/hooks.json`; PreToolUse/PostInvocation/Stop available | deterministic safety/model guards |
| Permissions | deny/ask/allow; Deny > Ask > Allow | least privilege + human confirmation |
| Monitoring | `/agents` and subagent lifecycle controls | kill runaway/stuck workers |
| Native nesting | platform supports deeper nesting | project deliberately restricts depth to 1 |
| Headless model pin | `agy --model ... --effort high` | fallback pinned role runner |

Source URLs are recorded in `research-sources.md`; reverify when upgrading Antigravity.
