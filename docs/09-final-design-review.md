# Marketing OS — Final Design Review

> Version 2.0 · 2026-09-05 · Audit scope: complete documentation + Antigravity engineering control plane + Clients Hunter migration decisions · Generated last

## 1. Verdict

### Documentation-ready: **YES**

The v2 package is internally coherent enough to govern implementation. Product scope, data ownership, source-acquisition architecture, legacy migration policy, provider constraints, engineering-agent topology, trust boundaries, review gates, and operating constraints are explicit.

### Static control-plane ready: **YES**

The materialized Antigravity workspace configuration passes the package validators, hook self-tests, secret/quarantine scan, agent-schema/tool-name audit, and the Project Agent Workflow Engine validator.

### Native Antigravity delegated execution ready: **CONDITIONAL**

It still requires the user's installed Antigravity release to close `AG-CC-01..05`, especially:

- `AG-CC-02`: prove effective **Gemini 3.8 Flash High / High effort** inheritance for native subagents;
- `AG-CC-03`: prove Reviewer/Verifier can inspect the exact candidate created with native `workspace=branch` semantics.

These are capability checks, not missing design decisions. The package includes fail-closed fallbacks: pinned `agy` role execution and explicit Git worktrees.

### Product implementation-ready: **NO — intentionally gated**

Before implementation relies on product-runtime assumptions, close `T-08` and `T-01`. Specialized Mostaql/Khamsat/Bahr adapters also require `T-09` revalidation.

---

## 2. Scope audited

The audit covered:

1. `docs/` design suite and the canonical Coordination Master Register;
2. `.agents/agents/` six-role Antigravity team;
3. `.agents/rules/`, `.agents/skills/`, `.agents/hooks.json`, protocols, permissions/setup guidance;
4. `agent_docs/` durable state contract;
5. runtime-provider policy and zero-incremental-cost boundary;
6. acquisition stack (`SearXNG → Acquisition Router → direct HTTP/API or Crawl4AI → Source Adapter → Evidence`);
7. Clients Hunter selective migration/quarantine policy;
8. Git/worktree trust boundaries and final human integration ownership;
9. cross-document `A/M/T/D/R` references;
10. static validation and hook negative/positive tests.

---

## 3. Governing v2 architecture confirmed

### 3.1 Engineering control plane

The active engineering harness is **Google Antigravity**, not Codex.

Roles:

```text
Orchestrator
  ├─ Explorer           (optional, read-only)
  ├─ Builder            (single bounded mutation worker)
  ├─ Verifier           (conditional independent execution evidence)
  ├─ Reviewer           (independent semantic acceptance)
  └─ Heavy Reviewer     (trigger-only deep risk gate)
```

All roles target **Gemini 3.8 Flash High + High effort** (`A-043`). Only Orchestrator owns delegation. Worker nesting is prohibited and max active subagents is two.

There is intentionally no permanent Deep Builder: with one engineering model, a second role name does not create real capability escalation. After two substantial Builder repair attempts, Orchestrator must re-scope, acquire missing evidence, or start a clean bounded Builder session.

### 3.2 Product runtime

Product reasoning remains Google-only:

- Antigravity preferred;
- Gemini API conditional fallback;
- Codex/OpenAI/ChatGPT prohibited as Marketing OS runtime providers (`A-019`, `A-031`).

Engineering Antigravity credentials/state are not automatically product-runtime credentials/state. `T-01` must prove the Hermes↔Antigravity runtime contract rather than inferring it from the existence of `agy`.

### 3.3 Source acquisition

The v2 acquisition architecture is:

```text
Country + Service Priority + Search Intent
                 ↓
             Query Planner
                 ↓
               SearXNG
                 ↓
       Candidate URL / Source
                 ↓
          Acquisition Router
          ├─ direct public API/HTTP
          └─ Crawl4AI
                 ↓
      Generic / Specialized Adapter
                 ↓
        Normalized Evidence
                 ↓
      Entity / Signal / Lead logic
```

Confirmed design consequences:

- Crawl4AI is the default rich crawling/rendering/extraction framework (`A-037`).
- BeautifulSoup/lxml may exist as bounded deterministic parsing utilities, not as a second scraping framework.
- SearXNG performs discovery; snippets are not authoritative evidence (`A-042`).
- stable public API/direct HTTP should beat browser crawling when cheaper and sufficient.
- keyword lists aid query planning but never constitute lead qualification truth.

### 3.4 Clients Hunter

Clients Hunter is a **donor codebase** (`A-038`), not runtime legacy and not reference-only material.

Migration policy:

- source-adapter concept → keep/generalize;
- Mostaql/Khamsat/Bahr knowledge → revalidate then cleanly reimplement where useful;
- shallow→deep acquisition → keep/generalize;
- URL dedup → extend into canonical source/entity/evidence identity;
- retry/backoff → preserve behavior where the new framework does not already provide it;
- keyword sets → query-planning hints only;
- Firebase/Firecrawl/Streamlit legacy runtime → discard;
- historical lead corpus → sanitize and convert into regression/evaluation fixtures.

Raw legacy `.env`, credentials, service-account material, databases and archives are quarantined (`A-040`, `R-05`).

---

## 4. Antigravity setup review

The control plane deliberately uses multiple enforcement layers rather than relying on one large prompt.

### Detailed Custom Agents

Each role has:

- a detailed planner-facing `description`;
- narrow explicit tool allowlist;
- role-specific authority boundaries;
- project invariants;
- input/output handoff contract;
- failure/stop behavior;
- role-specific Skills.

This matters because current Antigravity documentation states that the custom-agent description is used by the planner when deciding delegation and warns that invalid tool names can cause subagent execution problems.

### Rules

Only three workspace rules are used. They contain durable cross-role constraints, not every procedure. This avoids creating an oversized rule surface and leaves task procedures to focused Skills.

### Skills

Nine focused Skills provide progressive-disclosure procedures for capsules, build execution, verification, review, heavy-risk review, worktrees, acquisition, Clients Hunter migration and documentation synchronization.

### Hooks / mechanical enforcement

The package uses deterministic guards for constraints that should not depend on model compliance:

- secret/credential access denial;
- raw Clients Hunter artifact quarantine;
- forced human confirmation for merge/push/history rewrite/destructive cleanup;
- engineering-model identity fail-closed check;
- premature Stop protection while background work remains active.

The hook configuration and output contracts were rechecked against current official Antigravity hook documentation on 2026-09-05.

### Context discipline

Native subagents start from clean context. The project therefore uses bounded Task Capsules and compact deltas rather than passing long parent conversations. This is both a quality control and a quota-control mechanism.

---

## 5. Community signals considered without turning them into requirements

Current user reports were treated as operational signals only. Recurring themes include rapid quota consumption under aggressive parallel subagent use and context-heavy workflows becoming less predictable. They do not override official behavior, but they support the defensive choices already made:

- max two active subagents;
- one delegation level;
- no speculative swarm;
- no `/boost`/teamwork dependency in the normal route;
- concise Always-On rules;
- focused Skills;
- clean-context workers;
- finite repair budgets;
- local smoke tests after Antigravity upgrades.

---

## 6. Material issues found and repaired in v2 audit

### R-01 — Codex could leak into product runtime

**Status:** CLOSED.

`A-019/A-031` and mechanical runtime-provider checks keep the product Google-only.

### R-02 — Hermes + Antigravity could be described as already integrated

**Status:** CLOSED AS DESIGN RISK; `T-01` OPEN AS INVESTIGATION.

`agy` headless capability is not treated as proof of Hermes model-provider semantics.

### R-03 — Gemini API fallback could create silent spend

**Status:** CLOSED.

Fallback remains disabled unless `T-05` establishes an allowed path or founders explicitly supersede the zero-cost constraint.

### R-04 — Postiz could become an unnecessary MVP blocker

**Status:** CLOSED.

Publishing remains phase-gated; manual/direct substitutes preserve V1 usefulness.

### R-05 — Clients Hunter can leak secrets and architecture debt

**Status:** CLOSED WITH ACTIVE CONTROLS.

Raw legacy material is quarantined; only sanitized fixtures and selectively reconstructed capabilities enter the project.

### Engineering-harness stale wording

**Detected in final v2 audit:** one Checkpoint statement still described Codex as the current implementation/review agent after the project moved to an Antigravity-native engineering harness.

**Repair:** current documents now state that Antigravity custom agents are the active engineering control plane. Codex mentions remain only as historical/existing-resource context or explicit product-runtime prohibition.

**Status:** CLOSED.

---

## 7. Automated and structural checks actually executed

| Check | Result |
|---|---|
| `python scripts/verify_control_plane.py` | **PASS** |
| `python scripts/test_hooks.py` | **PASS** |
| `python scripts/scan_for_secrets.py` | **PASS** |
| `python scripts/validate_agent_definitions.py` (via control-plane validator) | **PASS** |
| Project Documentation Engine `validate_suite.py` | **PASS — no structural errors** |
| Project Agent Workflow Engine `validate_generated_control_plane.py` | **PASS — 0 errors; 1 expected warning for unresolved capability/investigation items** |
| Cross-document registry reference audit | **43 defined IDs; 39 referenced outside REG; 0 undefined references** |
| Codex harness directory audit | **PASS — no `.codex/` control plane** |
| Runtime provider allowlist/denylist audit | **PASS** |
| Raw credential/legacy artifact fingerprint scan | **PASS** |
| Hook positive/negative synthetic tests | **PASS** |

The workflow-engine warning is intentional: `AG-CC-02`, `AG-CC-03`, and `T-09` are explicitly unresolved because they require the installed runtime or current target sites. They are not documentation gaps.

---

## 8. Capability checks that cannot be honestly completed in the generation environment

| ID | Must prove on user's environment | If it fails |
|---|---|---|
| `AG-CC-01` | all six custom agents are discovered and launch | fix exact agent/frontmatter/tool mapping before work |
| `AG-CC-02` | native worker effective config remains Gemini 3.8 Flash High / High | use pinned role runner; never silently downgrade |
| `AG-CC-03` | native `workspace=branch` candidate is inspectable by parent/Verifier/Reviewer | use explicit Git worktree/candidate identity |
| `AG-CC-04` | installed Antigravity actually executes project hooks/permissions as expected | repair config before trusted mutation |
| `AG-CC-05` | Orchestrator respects ≤2 active workers and workers never delegate | terminate violating workers and fix role policy |

Static validation is not substituted for these checks.

---

## 9. Implementation blockers and phase gates

### Before first product implementation branch

1. run `AG-CC-01..05` dry run;
2. `T-08`: pin Hermes release and extension interfaces;
3. `T-01`: prove Hermes↔Antigravity product-runtime path;
4. retain provider/secret guards;
5. establish clean SQLite/evidence/provenance baseline.

### Before broad regional discovery

- `T-02`: SearXNG localized-market benchmark;
- explicit founder-controlled `M-03` country weights;
- `M-11` query lexicons.

### Before each specialized legacy-derived source adapter

- run `T-09` against the **current** public site behavior;
- use sanitized regression fixtures;
- do not trust historical selectors or search semantics from Clients Hunter.

### Before automatic publishing

- close `T-03`, `T-06`, `T-07` for the selected publishing path;
- preserve human approval and idempotency.

---

## 10. Design elements that must not be weakened during implementation

1. evidence/provenance before material lead claims;
2. search discovery separated from authoritative acquisition;
3. manual founder ownership of country weights;
4. public/authorized source boundary;
5. secret redaction before model/context transfer;
6. human approval for public/outbound actions initially;
7. Marketing DB ownership separated from Hermes conversational memory;
8. Google-only product runtime and no silent paid fallback;
9. Hermes extension-first/reuse-first policy;
10. Clients Hunter selective reconstruction rather than legacy wrapping;
11. Crawl4AI-first rich acquisition instead of rebuilding a browser stack;
12. Builder and Reviewer independence for STANDARD/HEAVY changes;
13. human final merge to trusted `main` in V1.

---

## 11. Final readiness statement

The package is **ready to be placed at the repository root and used as the governing Antigravity engineering environment**.

It is not appropriate to claim that the installed Antigravity subagent/worktree behavior or Hermes product-runtime bridge is already proven. The package is intentionally fail-closed around these unknowns and provides bounded fallback procedures.

The next correct action is **the local Antigravity dry run**, then `T-08`, then `T-01`. Only after those gates should the first real implementation capsule begin.
