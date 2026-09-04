# Marketing OS — Antigravity Engineering Agent Setup Guide

> Version 1.1 · 2026-09-04 · Engineering harness: Google Antigravity · Required engineering model: Gemini 3.8 Flash High

## 1. Governing principle

Antigravity is the active engineering harness. It also remains the preferred product reasoning technology, but engineering and product runtime are **separate trust contexts**. Product runtime still obeys `A-019/A-020/A-031`: Google-only reasoning; Codex/OpenAI/ChatGPT are not marketer runtime providers.

## 2. Project control plane

- `AGENTS.md` / `GEMINI.md`: short always-loaded authority router.
- `.agents/agents/`: six project-specific roles.
- `.agents/skills/`: Task Capsule, worktree, verification, review, heavy-risk procedures.
- `.agents/workflow/`: routing, contracts, worktree policy, dry run.
- `.agent-workflow/agent-control-manifest.json`: normalized execution-control source.
- `agent_docs/`: durable project/engineering state.

## 3. Model policy

Every engineering role uses Gemini 3.8 Flash High. Main is explicitly pinned/selected to `gemini-3.8-flash-high` + `high`. Current custom-agent frontmatter exposes `model: inherit|flash|pro` but no standalone effort field, so `AG-CC-02` is a blocking capability check for native subagent mode. If High cannot be proven, use the pinned role runner instead of silent downgrade.

## 4. Role topology

Orchestrator → Explorer (optional) → Builder → Verifier (conditional) → Reviewer → Heavy Reviewer (trigger-only). No permanent Deep Builder. Human founders merge trusted `main`.

## 5. Git and permissions

MICRO may use current workspace only when low-risk and single-writer. STANDARD/HEAVY Builder uses Antigravity native `workspace=branch`. Reviewer/Heavy Reviewer stay read-only. Verifier runs named gates and never repairs. Workflow policy caps active subagents at 2.

## 6. Project invariants

Preserve Hermes extension boundary, marketing DB authority, evidence provenance, untrusted external-content handling, human approval for public side effects, zero-new-cost policy, and Google-only marketer runtime. Do not let engineering Antigravity credentials/session state become product runtime state.

## 7. Setup order

1. Install bundle at repo root.
2. Run static validator.
3. Select `orchestrator` + Gemini 3.8 Flash High.
4. Run AG-CC-01..05 dry run.
5. Pin Hermes (`T-08`).
6. Prove Hermes ↔ Antigravity runtime path (`T-01`).
7. Add regional search (`T-02`) only after the runtime path is viable.

## 8. Maintenance

Agent/rule/skill files are versioned. Secrets are not. Product docs outrank engineering workflow files for product architecture. Update this guide and the control-plane manifest when Antigravity agent schema or workspace behavior materially changes.
