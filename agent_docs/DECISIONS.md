# DECISIONS — Antigravity Agent Control Plane

## WF-AG-001 — Engineering harness
**Decision:** Google Antigravity is the active engineering harness for this project. The prior Codex control plane is superseded for execution-control purposes only; product architecture decisions remain unchanged.

## WF-AG-002 — One model for every role
**Decision:** Orchestrator, Explorer, Builder, Verifier, Reviewer, and Heavy Reviewer all use Gemini 3.8 Flash High. Main is explicitly pinned/selected to `gemini-3.8-flash-high` with `high` effort.

## WF-AG-003 — Native inheritance with fail-closed check
**Decision:** custom subagents use `model: inherit`. Native mode is approved only after local `AG-CC-02` proves High effort inheritance. If it cannot be proven, use the pinned role runner; never silently accept Medium effort.

## WF-AG-004 — No permanent Deep Builder
**Decision:** because Builder and escalation would use the same model, no permanent deep-builder role exists. After Builder's two substantial repair attempts, Main re-evaluates the capsule/evidence and either issues a smaller/corrected capsule to a clean Builder session or surfaces a blocker/decision.

## WF-AG-005 — Independent review
**Decision:** Reviewer and Heavy Reviewer remain separate clean-context agents even though they use the same model. Independence is preserved through isolated context, different prompts/toolsets, and actual candidate evidence rather than Builder narration.

## WF-AG-006 — Git trust
**Decision:** MICRO may use current workspace only when low-risk/reversible/single-writer. STANDARD/HEAVY Builder uses native `workspace=branch`. Founders own final merge to trusted `main`.

## WF-AG-007 — Concurrency
**Decision:** workflow policy caps active subagents at 2. Write concurrency requires isolated worktrees and disjoint edit surfaces. This is a policy constraint; current public Antigravity custom-agent docs do not expose a project-level numeric concurrency field equivalent to the former Codex config.

## WF-AG-008 — Repair budgets
**Decision:** Builder has initial implementation + 2 substantial repair attempts; reviewer-driven repairs have 2 cycles; repeated identical exploration after evidence is answered is 0.

## WF-AG-009 — Runtime separation
**Decision:** Antigravity may be used both for engineering and as the preferred product reasoning technology, but the sessions, permissions, credentials, and state are separate trust domains. Codex/OpenAI/ChatGPT remain forbidden product runtime providers under `A-031`.
