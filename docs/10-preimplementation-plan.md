# Marketing OS — Pre-implementation Preparation Plan

> Version 2.0 · 2026-09-05 · Phase 0 preparation + Antigravity capability gates + blocking runtime spikes

## 1. Governing principle

> Resolve uncertainties that can invalidate the architecture **before** building business breadth. Start external waits early, and work locally in parallel.

## 2. Step 1 — launch external blockers

1. Pin the Hermes version to test (`T-08`).
2. Install/authenticate official Antigravity CLI on the intended VPS/operator environment.
3. Prepare a self-hosted SearXNG test instance.
4. Confirm company Telegram bot/control chat.
5. If Phase 4 is expected soon, start Meta/Postiz prerequisites in parallel (`T-03`,`T-07`), but do not block Market Radar on them.
6. Create a Gemini API key only for `T-05` if needed; do not enable billing/paid fallback silently.

## 3. Short critical investigations

| T-ID | Question | Timebox | Needs | Decision unlocked | Blocking phase |
|---|---|---|---|---|---|
| `T-08` | Which Hermes version/plugin/skill interfaces are pinned? | short | upstream docs/release | stable base | before code |
| `T-01` | Can Hermes use Antigravity reliably without Codex? | ≤ half day initial spike | Hermes + `agy` | runtime adapter/provider architecture | Phase 0 |
| `T-02` | Does SearXNG produce useful localized results in target markets? | 1 focused benchmark session + iteration | representative queries | regional search config | Phase 1 |
| `T-05` | If T-01 fails, can Gemini API provide a zero-incremental-cost fallback with needed contracts? | short | AI Studio/API docs/account | fallback path | conditional Phase 0 |
| `T-06` | Can one VPS run enabled services safely? | smoke/load | real VPS | topology | before co-location |
| `T-03` | Can self-host Postiz schedule/publish to owned Telegram+Instagram? | phase-gated | Postiz + accounts | automatic publishing | Phase 4 |
| `T-07` | Are Instagram account/app permissions sufficient? | phase-gated | real account | Instagram publishing | Phase 4 |

### T-01 experiment design

Try in this order:

**Path A — Hermes model-provider plugin**  
Use Hermes documented provider-plugin extension if Antigravity can be mapped cleanly. No Hermes core patch.

**Path B — general tool/skill adapter**  
Hermes calls a controlled wrapper around `agy -p --output-format json --json-schema ...`. This can cover specialist reasoning even if not a transparent agent-loop provider.

Verify:
- cached auth works non-interactively;
- structured output matches schema;
- stdout/stderr separation;
- timeout/non-zero status handling;
- conversation/session semantics if needed;
- concurrent jobs do not corrupt auth/session;
- scoped permissions;
- large input behavior;
- no Codex invocation anywhere.

**Pass criterion:** one realistic lead-analysis job and one content-synthesis job execute end-to-end through Hermes with persisted run metadata and validated output.

If neither path supports core agent-loop needs, run `T-05`.

## 4. Synthetic fixture / test corpus

Create a small fixed corpus before broad crawling.

### Required content

- 2–3 company/source examples per representative market cluster:
  - Arabic GCC;
  - Syria/Levant Arabic;
  - Turkey Turkish/English;
  - Lebanon mixed language.
- clean company website;
- duplicate company from two sources;
- stale page;
- job listing as expansion signal;
- tender/procurement signal;
- misleading/SEO spam source;
- page containing prompt injection text;
- page containing fake API key/secret pattern;
- ambiguous company-name collision;
- academic lead that is legitimate;
- academic request that crosses integrity boundary.

### Seed evaluation sets

1. source relevance labels;
2. evidence extraction expected facts;
3. entity merge/no-merge labels;
4. lead priority ranking labels;
5. content grounding/relevance rubric.

This corpus is deliberately small and fixed so provider/prompt/config changes can be regression-tested.

## 5. Repository setup

```text
marketing-os/
├── docs/
├── config/
├── marketing_plugin/
│   ├── tools/
│   ├── policies/
│   ├── repositories/
│   └── adapters/
├── skills/
├── schemas/
├── migrations/
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── eval/
├── scripts/
├── data/              # gitignored runtime state
└── deploy/
```

### `.gitignore` / secret exclusion smoke

Seed a fake secret into a local ignored fixture and verify:
- Git status does not include runtime data/credentials;
- secret scanner fails if a secret is moved into tracked path;
- model redactor removes seeded secrets.

### Initial ADRs

None automatically. Create ADR only if `T-01` produces a durable architecture choice beyond the already confirmed extension-first policy.

## 6. Environment/service verification

Prove one real operation through each enabled dependency:

- Hermes starts with pinned version.
- CLI session works.
- Telegram private message reaches correct Hermes profile.
- cron executes one no-agent deterministic job and one controlled agent job.
- marketing plugin reads/writes test SQLite.
- SearXNG returns JSON.
- Antigravity returns schema-constrained JSON via chosen wrapper.
- backup/restore test DB.
- Postiz only when Phase 4 prerequisites start.

## 7. Final review and kickoff

Before Phase 1 implementation:
- close `T-08`;
- close `T-01` or choose `T-05` fallback;
- update PROVIDERS/HLD/REG with measured result;
- rerun documentation validator;
- freeze first implementation contracts.

## 8. Ready-to-start checklist

- [ ] no Codex runtime config exists.
- [ ] Hermes pinned.
- [ ] Antigravity path proven or fallback verified.
- [ ] country-priority config validates and has explicit values for enabled production countries.
- [ ] source taxonomy fixture loads.
- [ ] schema migrations run on clean DB.
- [ ] evidence provenance fixture passes.
- [ ] approval state machine fixture passes.
- [ ] secret redaction fixture passes.
- [ ] Telegram allowlist passes.
- [ ] SearXNG benchmark plan exists/starts.

## 9. What NOT to do during preparation

- build dashboard;
- scrape authenticated LinkedIn/private groups;
- integrate paid CRM;
- tune a complex lead score before labeled examples;
- deploy LangGraph/vector DB/PostgreSQL “for future scale”;
- fork Hermes;
- wire Codex as inference fallback;
- automate outbound/public posting before approval path exists.

## 10. Risks and fallbacks

| Risk | Likelihood | Impact | Fallback | Owner |
|---|---|---:|---|---|
| `agy` cannot serve Hermes agent-loop semantics | Medium | High | tool/specialist adapter; then T-05 Gemini API | engineering |
| Gemini API free path insufficient | Medium | High | narrow Antigravity-only tasks; queue/defer; explicit budget decision later | founders |
| SearXNG localization weak in a market | Medium | Medium | tune engines/language/query lexicon; source-specific adapters for proven public sources | engineering |
| VPS cannot host Postiz stack | Medium | Medium | manual Instagram + direct Telegram; Postiz later/separate | founders |
| upstream Hermes interface changes | Medium | Medium | pin version; adapter tests; upgrade deliberately | engineering |
| social OAuth approval slow | Medium | Medium | content generation/approval still ships; manual publish | founders |

## 11. Priority if time collapses

1. `T-08 + T-01`: without stable Hermes/Google runtime path, architecture is unproven.
2. SQLite/evidence/provenance contracts: correctness foundation.
3. SearXNG + regional query benchmark: acquisition foundation.
4. Telegram operator/approval flow: usable MVP surface.
5. Lead intelligence on fixed fixtures before broad content/publishing.

## v2 preimplementation delta

### Engineering harness gate before product code
Run `AG-CC-01..05` from `.agents/protocols/DRY-RUN.md`: agent discovery, Gemini 3.8 Flash High/High inheritance, native branch-worktree review visibility, hooks/permissions, and delegation-limit behavior. Use pinned role runner / explicit Git worktree fallback if native semantics are unproven.

### Acquisition preparation
After `T-08/T-01` and before specialized freelance-source code:
- establish Crawl4AI as the primary rich acquisition dependency and define the acquisition router contract;
- keep direct public API/HTTP as the cheaper route when sufficient;
- run `T-02` for SearXNG regional discovery;
- run `T-09` separately for Mostaql, Khamsat and Bahr before enabling each adapter;
- create sanitized legacy regression fixtures that include known noisy Clients Hunter candidates;
- never import raw legacy archive/database/credentials into the repo.

