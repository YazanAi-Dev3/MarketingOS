# Marketing OS — Antigravity Agent Control Plane v1.0

Project-specific engineering team/workflow for building Marketing OS with Google Antigravity. Product/runtime documents are included; the engineering control plane is separate from the marketer's runtime state and credentials.

## Team

All six roles use **Gemini 3.8 Flash High**:

| Role | Purpose | Mutation |
|---|---|---|
| `orchestrator` | decisions, routing, decomposition, synthesis | durable control state only by default |
| `explorer` | targeted repository evidence | no |
| `builder` | bounded implementation and local repair | yes, capsule/worktree only |
| `verifier` | named independent gates | no repairs |
| `reviewer` | independent correctness/semantic gate | no |
| `heavy-reviewer` | trigger-scoped deep risk review | no |

There is no permanent Deep Builder. Builder budget exhaustion returns control to Main for re-scope or a clean Builder session.

## Model enforcement

Main must be selected/launched as `gemini-3.8-flash-high` with `high` effort. Custom subagents use `model: inherit`. Because current custom-agent frontmatter has no separate effort field, `AG-CC-02` must prove High inheritance locally. If unproven, use `scripts/run_antigravity_role.py`, which pins the exact model and effort for a role run.

## First use

1. Copy/unpack into repository root.
2. Run `python scripts/verify_control_plane.py`.
3. Read `.agents/workflow/BOOTSTRAP_NEW.md`.
4. Select `orchestrator` and Gemini 3.8 Flash High.
5. Run `.agents/workflow/DRY-RUN.md`.
6. Start with `T-08`, then `T-01`.

Human founders keep final merge authority. STANDARD/HEAVY Builders use native Antigravity `workspace=branch`.
