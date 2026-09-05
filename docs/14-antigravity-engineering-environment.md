# Marketing OS — Antigravity Engineering Environment v2

> Version 2.0 · 2026-09-05 · Control-plane design based on current Google Antigravity documentation and bounded community operational signals

## 1. Objective

The engineering harness must compensate for a model/harness combination that may be less reliable when instructions are underspecified or context grows. The solution is not a giant system prompt or more agents. The design combines:

- strong custom-agent role definitions;
- clean-context delegation;
- focused progressive-disclosure Skills;
- only three concise Always-On workspace Rules;
- deterministic Hooks and Permissions for critical boundaries;
- bounded Task Capsules and structured handoffs;
- branch/worktree isolation;
- independent review;
- finite repair/parallelism budgets;
- local capability checks after Antigravity upgrades.

## 2. Current official platform facts used

Reviewed against Antigravity 2.0 documentation visible on 2026-09-05 (docs showed Antigravity v2.12.2 and CLI v1.1.25).

Official behavior relied on:
- workspace custom agents at `.agents/agents/<name>.md` or `<name>/agent.md`;
- YAML frontmatter with `name`, detailed `description`, exact tool list, main/subagent flags, model tier, command policy, skills/plugins;
- `description` is used by the planner to decide delegation;
- official warning that misspelled/unmapped tool names may hang a subagent;
- subagents start with clean context rather than inheriting parent conversation history;
- subagent workspaces can be `inherit`, `branch` (isolated Git worktree), or `share`;
- Skills live under `.agents/skills`, are discovered by description and loaded progressively;
- workspace Rules live under `.agents/rules`, with 12,000-character per-rule limit and configurable activation mode;
- Hooks live in `.agents/hooks.json` and can gate PreToolUse, inspect PostInvocation, and influence Stop;
- Permissions use deny/ask/allow with `Deny > Ask > Allow` precedence;
- `/agents` allows monitoring/termination of subagents;
- headless CLI can pin `--model` and `--effort high`.

Primary references are recorded in `.agent-workflow/research-sources.md`.

## 3. Community observations and how they are used

Current user discussions were reviewed only for practical failure modes, not authority. Recurring reports mention rule adherence degrading in long contexts and high quota use from aggressive subagent parallelism. The project response is defensive:

- do not keep all process detail Always-On;
- do not create deep agent trees;
- keep worker prompts role-specific and explicit;
- make security/integration prohibitions mechanical where possible;
- cap concurrency at 2;
- use clean Task Capsules rather than carrying giant parent histories;
- rerun local smoke tests after platform upgrades.

## 4. Role topology

```text
                      ORCHESTRATOR
               decision / routing / state
                         │
          ┌──────────────┼──────────────┐
          │              │              │
      EXPLORER        BUILDER        VERIFIER
      read-only       mutation       read/execute
                         │
                         ▼
                      REVIEWER
                 independent read-only
                         │
                  concrete trigger only
                         ▼
                 HEAVY REVIEWER
               exceptional-risk read-only
```

All roles target **Gemini 3.8 Flash High + High effort**. There is no permanent Deep Builder because a same-model role does not create genuine capability escalation. After repair exhaustion, Orchestrator changes the information/capsule, not merely the label.

## 5. Why role descriptions are long

Antigravity explicitly uses custom-agent `description` to decide when a task should be delegated. Therefore each description states:
- domain;
- when the role should be used;
- when it should not;
- mutation/read boundary;
- expected handoff.

The Markdown body then defines full operating behavior. Short one-line role definitions were rejected for v2 because ambiguous delegation is expensive and brittle.

## 6. Tool allowlists

Only official documented tool names are used. Workers do not get delegation tools. Read-only agents do not get write tools. Orchestrator alone gets `invoke_subagent` and management capabilities.

`validate_agent_definitions.py` rejects unknown configured tool names because current official docs warn that invalid names can hang a subagent.

## 7. Context architecture

Antigravity subagents start with clean context. The workflow exploits this deliberately:

- Orchestrator retains high-level decision state.
- Explorer receives one evidence question.
- Builder receives a Task Capsule, not the full conversation.
- Reviewer receives authoritative capsule + actual candidate + verification evidence, not Builder reasoning.
- Heavy Reviewer receives only the trigger-specific risk context.

This improves independence and controls quota/context pollution.

## 8. Rules vs Skills vs Hooks

### Always-On Rules
Only three:
1. operating contract;
2. Git trust/scope;
3. security/runtime boundaries.

They contain invariants that must remain visible every turn and each is well below the documented rule-size limit.

### Skills
Procedures are Skills: Task Capsule, build execution, verification, review, heavy-risk review, worktree protocol, documentation sync, source acquisition, Clients Hunter migration. Antigravity discovers skills by description and loads full content only when relevant.

### Hooks
Critical enforcement is not left to model memory:
- credential/raw-legacy access is denied;
- destructive/integrating Git commands force human confirmation;
- observable wrong model identity terminates the trajectory;
- premature stop with active background work is corrected once.

### Permissions
Use deny/ask/allow as the outer platform boundary. Do not use `--dangerously-skip-permissions` for normal project work. Provide only scoped low-risk allows; unconfigured sensitive operations should remain Ask.

## 9. Windows note

The user develops on Windows 11. Current official Antigravity documentation states terminal sandboxing is preview on macOS/Linux and coming to Windows. Therefore `commandExecutionPolicy: sandbox` expresses the desired role policy but **must not be treated as the sole OS security boundary on Windows**. Permissions, Hooks, Git isolation and human confirmation remain mandatory.

## 10. Model/effort policy

Main is explicitly launched on `gemini-3.8-flash-high` with High effort. Custom-agent frontmatter currently exposes model tier/inherit, but not a separate documented effort field. Therefore:

- native workers use `model: inherit`;
- `AG-CC-02` must prove effective model/effort behavior on the installed release;
- if not proven, `scripts/run_antigravity_role.py` pins `--model gemini-3.8-flash-high --effort high` in a separate role run;
- silent downgrade is forbidden.

The PostInvocation model hook can verify the observable `modelName`; it cannot prove a hidden effort parameter independently, so capability evidence remains necessary.

## 11. Parallelism and nesting

Antigravity supports multiple concurrent subagents and deeper nesting, but the project intentionally restricts:
- max active subagents: 2;
- only Orchestrator may delegate;
- worker nesting depth: 0;
- mutation writers are serialized unless separate worktrees and genuine independence are proven.

This is a cost/reliability choice, not a platform limitation.

## 12. Worktree trust model

STANDARD/HEAVY Builder is invoked with `workspace=branch` after `AG-CC-03` proves installed-version behavior. Independent gates inspect the actual candidate. Human founders merge trusted `main`.

If native candidate visibility is unreliable, use explicit Git worktrees rather than weakening independent review.

## 13. Route economics

- CHAT: no agent multiplication.
- MICRO: smallest possible mutation path; review only when signaled.
- STANDARD: one Builder + independent Reviewer, optional evidence/verifier.
- HEAVY: baseline review + one trigger-specific Heavy Reviewer.

No routine `/boost` or `/teamwork-preview`; those are tools for exceptional user-directed experiments, not project defaults.

## 14. Repair policy

- Builder: initial implementation + two substantial repairs.
- Reviewer-driven repair cycles: two.
- same-question exploration retry: zero.

After exhaustion, change the hypothesis, capsule or evidence. Repeating the same model with the same context is not escalation.

## 15. Required local dry run

The static package cannot prove installed runtime semantics. Complete `AG-CC-01..05` from `.agents/protocols/DRY-RUN.md`, especially effort inheritance and worktree candidate access, before relying on native STANDARD/HEAVY orchestration.

## 16. Upgrade discipline

When Antigravity materially updates custom agents, tools, rules, hooks, permissions, model identifiers, effort handling or worktrees:
1. reread official capability docs;
2. run static validator;
3. rerun AG-CC-01..05;
4. only then update this document and manifest.
