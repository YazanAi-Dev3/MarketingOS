# Marketing OS — Antigravity Engineering Agent Setup Guide

> Version 2.0 · 2026-09-05 · Engineering harness: Google Antigravity · Required model: Gemini 3.8 Flash High / High effort

## 1. Purpose

This guide defines the engineering control plane used to build Marketing OS. It is intentionally stronger than a collection of short prompts: the environment combines detailed role definitions, clean-context delegation, focused Skills, minimal Always-On Rules, deterministic Hooks/Permissions, Git worktree isolation, bounded repair budgets and durable handoff contracts.

Product runtime and engineering harness are distinct. Antigravity is used to build the system and is also the preferred product reasoning technology, but engineering sessions/credentials are not product runtime state.

## 2. Governing model policy

`A-043` fixes all custom engineering roles to **Gemini 3.8 Flash High with High effort**.

- Main Orchestrator is selected/launched explicitly with that model/effort.
- Worker frontmatter uses `model: inherit` because current documented custom-agent frontmatter exposes model tier but no separate effort field.
- `AG-CC-02` must prove the effective inherited model/effort on the installed release.
- If unproven, use `scripts/run_antigravity_role.py`, which pins `--model gemini-3.8-flash-high --effort high`.
- The PostInvocation hook rejects an observable wrong model identity. It is not a substitute for proving hidden/effective effort.

No silent downgrade is allowed.

## 3. Platform primitives used

Current official Antigravity documentation (reviewed 2026-09-05) supports:
- workspace custom agents in `.agents/agents/`;
- detailed descriptions used by the planner for delegation;
- explicit tool allowlists and command execution policy;
- clean-context asynchronous subagents;
- `inherit` / `branch` / `share` workspaces;
- Skills in `.agents/skills/` with progressive disclosure;
- workspace Rules in `.agents/rules/`;
- Hooks in `.agents/hooks.json`;
- fine-grained deny/ask/allow Permissions;
- `/agents` monitoring/termination;
- headless `agy` model/effort pinning.

A current official warning notes that an invalid/misspelled custom-agent tool name may cause the worker to hang. `scripts/validate_agent_definitions.py` therefore checks configured tools against the documented list used by this package.

## 4. Role topology

### Orchestrator — decision plane
Owns authority resolution, route classification, architecture/risk decisions, Task Capsules, delegation, repair budget, final synthesis and durable state. It is the only role with `invoke_subagent`.

### Explorer — evidence plane
Read-only. Resolves one precise repository/upstream fact and classifies evidence as repository fact, project authority, upstream fact, community signal, hypothesis or capability check.

### Builder — mutation plane
Owns one approved capsule/candidate. Implements within the edit boundary, runs focused checks, performs at most two substantial repairs and returns Knowledge Delta. It cannot delegate or integrate to main.

### Verifier — execution evidence
Read/execute only. Runs named gates against a named candidate and classifies failures. It never repairs.

### Reviewer — independent correctness gate
Read-only. Reviews actual candidate state against capsule/contracts, not Builder narration. Requests bounded repair or a concrete Heavy trigger.

### Heavy Reviewer — exceptional risk gate
Read-only and trigger-only: secrets/auth, command/SSRF/untrusted-web boundary, provider/runtime integration, public side effects, destructive migration, production infrastructure, concurrency/shared state or high-blast-radius architecture.

There is no permanent Deep Builder. With one model family, relabeling the same model is not capability escalation. After Builder budget exhaustion, Orchestrator changes the evidence/capsule and may start a clean Builder session.

## 5. Delegation and context

Only Orchestrator delegates; worker nesting depth is zero. Max active subagents is 2.

Subagents start with clean context, so handoffs are deliberate:
- Explorer gets one evidence question.
- Builder gets a bounded Task Capsule.
- Verifier gets candidate identity + named gates.
- Reviewer gets capsule + authoritative contracts + actual candidate + verification evidence.
- Heavy Reviewer gets the exact trigger + candidate/evidence.

Do not pass the whole parent transcript “for completeness.” Durable project context belongs in docs/agent_docs and bounded handoffs.

## 6. Routing

- **CHAT:** no mutation; no agent multiplication unless one fact is missing.
- **MICRO:** local/reversible/low-risk change; current workspace only if safe single-writer; review conditional.
- **STANDARD:** branch-worktree Builder + independent Reviewer; Verifier conditional.
- **HEAVY:** branch-worktree Builder + named verification + Reviewer + trigger-specific Heavy Reviewer.

The detailed contract is `.agents/protocols/ROUTING.md`.

## 7. Worktree trust

Trusted `main` is human-integrated. STANDARD/HEAVY Builder uses Antigravity native `workspace=branch` after `AG-CC-03` proves installed behavior. Reviewer/Verifier inspect the actual candidate. If native visibility is unreliable, use explicit Git worktrees rather than weakening review.

## 8. Rules, Skills and Hooks

### Three Always-On Rules only
- `00-operating-contract.md`
- `10-git-trust-and-scope.md`
- `20-security-runtime-boundaries.md`

Set them to **Always On** in Antigravity. They contain cross-cutting invariants only.

### Focused Skills
Procedures live in Skills so Antigravity can load them progressively when relevant: Task Capsule, build execution, verification, independent review, heavy risk review, worktree protocol, documentation sync, source acquisition and Clients Hunter migration.

### Hooks
Critical safety does not rely on prompt obedience:
- PreToolUse denies direct credential-file access/writes and unsafe raw legacy ingestion; destructive/integrating Git requires human confirmation.
- PostInvocation detects observable wrong model identity and terminates instead of silently downgrading.
- Stop reconciles active background work once without creating an infinite loop.

Run `python scripts/test_hooks.py` before trusting hook behavior.

## 9. Permissions

Antigravity permissions use Deny > Ask > Allow. The supplied settings example allows only low-risk inspection/validator commands and denies obvious secret/Git paths. Other commands/web/MCP actions should remain Ask unless a scoped grant is deliberately added.

Do not use `--dangerously-skip-permissions` for routine project work.

On Windows 11, current official docs state terminal sandboxing is not yet equivalent to the macOS/Linux preview. Therefore Permissions + Hooks + worktree trust remain essential even though agent frontmatter uses `commandExecutionPolicy: sandbox`.

## 10. Repair and cost discipline

- Builder substantial repairs after initial implementation: 2.
- Reviewer-driven repair cycles: 2.
- repeated same-question exploration: 0.
- max active subagents: 2.
- `/boost` and `/teamwork-preview` are not routine project mechanisms.

The objective is not maximum agent activity; it is minimum sufficient compute for high-confidence evidence.

## 11. Project-specific engineering guardrails

Any candidate must preserve:
- Hermes extension-first boundary;
- Google-only product runtime; Codex/OpenAI/ChatGPT runtime prohibition;
- SQLite/raw artifacts as marketing domain authority in MVP;
- evidence/provenance before material lead claims;
- dynamic source intelligence with manual geographic priorities;
- SearXNG discovery separate from authoritative acquisition;
- Crawl4AI as primary rich acquisition, direct HTTP/API when sufficient;
- Clients Hunter selective migration, no legacy runtime wrap;
- `T-09` before Mostaql/Khamsat/Bahr specialized adapters;
- human approval for public external actions initially;
- zero incremental cost unless explicitly superseded.

## 12. First-run sequence

1. install package at repo root;
2. choose `orchestrator` + Gemini 3.8 Flash High + High effort;
3. set three workspace Rules Always On;
4. apply/review scoped Permissions;
5. run static validator + hook tests + secret scanner;
6. run AG-CC-01..05 dry run;
7. only then begin product task `T-08`, followed by `T-01`.

## 13. Upgrade policy

After material Antigravity upgrades, revalidate official tool names/frontmatter, agent discovery, model/effort inheritance, worktree visibility, Hooks and Permissions before resuming autonomous delegated work. Update the capability matrix and this document with measured evidence.
