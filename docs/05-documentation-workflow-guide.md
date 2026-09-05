# Marketing OS — Documentation & Living Workflow Guide

> Version 2.0 · 2026-09-05 · Purpose: keep design intent stable while code and upstream tools evolve

## 1. Governing principle

> **Document stable intent, boundaries and decisions manually; derive fast-changing implementation detail from code/config/tests.**

### Documentation layers by volatility

| Layer | Content | Volatility | Correct source | Update trigger |
|---|---|---|---|---|
| Decision | scope, cost, autonomy, provider policy | Low | REG + ADRs | decision changes |
| Architecture | components, authority, invariants | Medium | HLD/TS | architecture contract changes |
| Operations | topology, security, recovery | Medium | OPS + deploy config | deployment/security change |
| Runtime configuration | countries, priorities, provider IDs | High | versioned YAML/config | config change |
| Schema/API implementation | tables, CLI args, tool schemas | High | code/migrations/generated docs | code change |
| External provider facts | quotas, flags, platform behavior | High | PROVIDERS with verification date | re-verification/upgrade |

## 2. Document decision table

| Artifact | When | Source of truth | Owner | Notes |
|---|---|---|---|---|
| `00-document-index.md` | navigation/release | docs suite | founders | update when suite status changes |
| `01-project-checkpoint.md` | explain why | confirmed decisions | founders | narrative, not LLD |
| `02-technical-design-spec.md` | implementation contract | design snapshot | engineering | update with domain contract changes |
| `04-operations-deployment-security.md` | production changes | deployment/security design | engineering/operator | same PR as ops change |
| `06-coordination-master-register.md` | always | **governing status registry** | founders/engineering | no silent decision mutation |
| `07-high-level-design.md` | architecture review | architecture | engineering | component/boundary change |
| `08-future-roadmap.md` | deferred ideas | D-items | founders | trigger-based |
| `09-final-design-review.md` | audit checkpoints | actual audit | reviewer | generated last |
| `10-preimplementation-plan.md` | implementation kickoff | T/M/phase ordering | engineering | retire/replace after phase kickoff |
| `11-ai-coding-agent-setup.md` | Antigravity engineering setup | build policy | engineering | all roles Gemini 3.8 Flash High |
| `12-model-provider-guide.md` | runtime provider facts | dated external verification | engineering/operator | volatile facts expire |
| ADR | irreversible implementation-era decision | ADR file | decision owner | only on trigger |

## 3. Low-level design policy

Do **not** maintain long hand-written LLD for every class. The following are implementation sources:
- Python types/dataclasses/Pydantic models;
- SQLite migrations;
- tool/CLI schemas;
- JSON Schemas for Antigravity structured output;
- tests/fixtures;
- Docker/Compose manifests.

Write manual LLD only when a cross-component contract is expensive to infer or has non-obvious invariants.

## 4. Recommended `docs/` structure

```text
docs/
├── 00-document-index.md
├── 01-project-checkpoint.md
├── 02-technical-design-spec.md
├── 04-operations-deployment-security.md
├── 05-documentation-workflow-guide.md
├── 06-coordination-master-register.md
├── 07-high-level-design.md
├── 08-future-roadmap.md
├── 09-final-design-review.md
├── 10-preimplementation-plan.md
├── 11-ai-coding-agent-setup.md
├── 12-model-provider-guide.md
└── adr/
```

README at repo root points first to IDX and REG.

## 5. ADRs

### 5.1 Trigger

Create an ADR when at least one is true:
- modifying Hermes core instead of extension surface;
- changing the authoritative marketing store;
- introducing paid/runtime provider;
- changing approval/autonomy policy;
- changing public/private collection boundary;
- adding a workflow framework or distributed architecture;
- adopting a dependency whose removal would require material redesign;
- superseding a confirmed `A-###`.

### 5.2 Template

Use the skill's ADR template with:
`Context → Decision → Options → Consequences → Verification → Supersedes/affects`.

### 5.3 Initial candidates

No ADR exists yet because implementation has not begun. Likely first ADR only if `T-01` reveals that Antigravity integration requires a non-trivial provider/plugin architecture choice.

## 6. Living documentation workflow

### Same-change update rule

A code/config change that alters a documented contract must update the owning document **in the same change**.

Examples:
- Country weight CLI changes → TS + config example.
- Approval semantics change → TS + HLD + OPS.
- Provider path changes → PROVIDERS + REG and ADR if durable.
- New deferred feature → ROAD + REG.

### Executable documentation/config

Prefer:
- JSON Schema for model outputs;
- validated YAML for country/service config;
- generated CLI `--help`;
- migrations;
- contract tests.

### CI/document health checks

Run:
- project tests/lint/type checks;
- schema/config validation;
- secret scan;
- documentation suite validator;
- link/reference check for internal filenames;
- grep/guard ensuring rejected runtime concepts (e.g. Codex provider) do not appear as current scope.

### Pull-request checklist

- [ ] Does this change alter an `A/M/T/D` item?
- [ ] Is an ADR trigger met?
- [ ] Did domain source-of-truth move?
- [ ] Does external action permission change?
- [ ] Does provider/cost policy change?
- [ ] Were docs updated in the same change?
- [ ] Are new secrets/config excluded from Git?
- [ ] Were relevant fixtures/smokes run?

### End-of-phase review

At each phase exit:
1. close investigations/calibrations actually measured;
2. update REG;
3. re-run suite validator;
4. audit current-vs-deferred scope;
5. record material finding in REVIEW or create new review version.

## 7. HLD ownership/content

HLD owns component boundaries, dependencies, authority, flows, degradation and invariants. It must not duplicate exact schemas from TS.

## 8. NFR handling

No separate NFR artifact in V1. Security, reliability, observability, cost and recovery are integrated into TS/HLD/OPS. Create a separate NFR only if contractual/service-level requirements emerge.

## 9. Architecture/code review timing

- Before Phase 0 exit: adapter/runtime review.
- Before Phase 1 exit: data/evidence/source review.
- Before Phase 4: external publishing/security review.
- Before any autonomy promotion: dedicated review against `M-07`.

## 10. Implementation-plan documentation

`10-preimplementation-plan.md` is kickoff guidance, not a perpetual backlog. After implementation starts, actual task tracking belongs in the engineering workflow; ROAD continues to own intentional deferrals.

## 11. Governing shortcut

> If a fact changes with every refactor, keep it in code/tests/config. If changing it changes **why the system is safe/correct/useful**, keep it in documentation and decision history.
