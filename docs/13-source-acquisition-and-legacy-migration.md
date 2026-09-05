# Marketing OS — Source Acquisition & Clients Hunter Migration

> Version 2.0 · 2026-09-05 · Governing acquisition addendum

## 1. Purpose

This document freezes the acquisition architecture after reviewing the legacy Clients Hunter codebase. It supersedes any earlier wording that implied BeautifulSoup/Playwright should form a custom primary scraping stack or that Clients Hunter should merely remain an external reference.

## 2. Governing decisions

- `A-037`: **Crawl4AI is the primary rich web acquisition/rendering/extraction framework.** Prefer direct public API/HTTP when it is stable, cheaper and sufficient. BeautifulSoup/lxml remain small parsing utilities, not a parallel scraping architecture.
- `A-038`: Clients Hunter is a donor codebase for **selective architectural migration + clean reimplementation**. It is neither a runtime dependency nor reference-only material.
- `A-039`: Mostaql, Khamsat and Bahr are initial candidate specialized adapters, each blocked by current-site revalidation `T-09`.
- `A-040`: raw legacy archive/database/`.env`/Firebase service-account material is quarantined and must not enter the new repository/model context. Only sanitized regression fixtures and non-secret knowledge may be migrated.
- `A-041`: a newly discovered source becomes a specialized adapter only after measured recurring value justifies the maintenance cost; threshold is calibrated under `M-14`.
- `A-042`: SearXNG discovery and page acquisition are separate responsibilities. Search snippets can locate candidates but are not authoritative evidence for material lead claims.

## 3. Acquisition architecture

```text
Country + Service Priorities
        ↓
Search Intent
        ↓
Regional Query Planner
        ↓
SearXNG
        ↓
Candidate URL / Source
        ↓
Acquisition Router
   ├── Public API / JSON / direct HTTP
   │      when stable and sufficient
   └── Crawl4AI
          for robust crawling, rendering, sessions,
          cleaning and structured extraction
        ↓
Generic Source Profile OR Specialized Adapter
        ↓
Raw Artifact + Extracted Facts
        ↓
Evidence Normalization / Provenance
        ↓
Entity Resolution → Signals → Lead/Content Intelligence
```

The system must not collapse search, acquisition and qualification into one opaque step.

## 4. Why Crawl4AI is the default rich acquisition layer

The project needs many source families across nine countries: company sites, directories, chambers, public job boards, procurement/tender pages, news, events, startup ecosystems and freelance-demand platforms. Rebuilding browser/session/JS/rendering/content-cleaning/extraction primitives source by source would recreate infrastructure already available in a mature open-source acquisition framework.

Crawl4AI is used for the **web acquisition problem**, not as the intelligence/qualification layer. Deterministic extraction is preferred for stable sources; Antigravity should not be consumed to parse fields that a stable schema can extract.

Direct HTTP/API bypasses browser work when authoritative data is already exposed cheaply and reliably. BeautifulSoup/lxml may help with tiny deterministic transforms or edge cases after acquisition, but they do not own browser lifecycle, sessions or source crawling strategy.

## 5. Source adapter contract

A specialized adapter should own only source-specific knowledge:

```text
source_key
country/language applicability
discovery/search URL or endpoint rules
pagination/current listing/detail behavior
required acquisition mode
structured extraction schema
field normalization hints
source external identity / canonical URL logic
current-site validation metadata
bounded live-smoke procedure
```

It should **not** reimplement common browser/session/retry/content storage infrastructure when the shared acquisition layer supplies it.

## 6. Generic → specialized promotion

New web sources are generic by default. A specialized adapter has maintenance cost and should be earned by evidence.

Candidate promotion signals:
- recurring qualified-lead or useful intelligence yield;
- repeated extraction failures/expense under generic processing that a stable adapter can materially reduce;
- stable source structure and public-access boundary;
- repeated use in a strategically weighted country/service segment.

`M-14` calibrates the actual threshold. Promotion is not fully automatic in V1.

## 7. Clients Hunter findings

The legacy project was useful but solved a narrower problem: collecting projects from freelance platforms using platform search + keywords. Inspection found:

- two architectural generations coexisting: an older Firebase/Streamlit/scraper path and a newer SQLModel/SQLite pipeline path;
- legacy deployment still tied to the older path;
- a strong source-specific adapter concept and shallow→deep collection idea;
- overly weak relevance logic: native platform search and keyword/title checks could admit large volumes of unrelated work;
- Firecrawl/Firebase/Streamlit dependencies that conflict with the current zero-incremental-cost and architecture goals;
- historical lead data useful as a noise/regression corpus;
- a runtime bug in the newer Bahr pipeline where `items.append(...)` can occur without initializing `items`;
- credential-bearing files present in the archive contents; they must remain quarantined and any still-active credentials should be rotated externally.

## 8. Migration inventory

| Legacy capability | Decision | New ownership |
|---|---|---|
| Source-specific adapter pattern | KEEP / GENERALIZE | `sources/adapters` concept |
| Mostaql source knowledge | CLEAN REIMPLEMENT after `T-09` | Mostaql adapter |
| Khamsat source knowledge | CLEAN REIMPLEMENT after `T-09` | Khamsat adapter |
| Bahr source knowledge | CLEAN REIMPLEMENT/FIX after `T-09` | Bahr adapter |
| shallow→deep scraping | KEEP / GENERALIZE | acquisition/enrichment stages |
| URL dedup | IMPROVE | normalized URL + source ID + entity resolution |
| retry/backoff | KEEP behavior if not supplied downstream | acquisition infrastructure |
| keyword vocabulary | KEEP as query-planning hints | regional query planner |
| keyword relevance classifier | DISCARD | deterministic filters + evidence + model qualification |
| Firecrawl | DISCARD | Crawl4AI/direct HTTP |
| Firebase | DISCARD | SQLite domain store |
| Streamlit | DISCARD | Hermes CLI/Telegram operator UX |
| old orchestration loop | DISCARD | staged Marketing OS pipeline |
| historical leads | SANITIZE / CONVERT | regression/evaluation fixtures |

## 9. Legacy regression corpus

The old data is valuable precisely because it contains noisy candidates. Build a **sanitized** fixture set that includes:
- false positives previously admitted by keyword/platform search;
- plausible true positives;
- duplicate URLs/entities;
- malformed or stale data;
- source-specific missing fields.

Expected labels can include `reject`, `needs_more_evidence`, `qualified_candidate`, plus reason codes. The raw database is not the fixture source at runtime; fixtures are exported once through a controlled sanitization step and checked into a safe test representation.

## 10. Evidence boundary

For material signals:

```text
SearchResult → acquisition → Evidence → Signal → LeadAssessment
```

`SearchResult.snippet` may influence acquisition priority, but a high-confidence signal must point to fetched/retained evidence or a clearly identified manual/authorized source. Evidence records retain URL/source, observation time, extraction method, content/artifact identity and confidence.

## 11. Security boundary

Crawled text is attacker-controlled input. Acquisition must not:
- execute page instructions;
- follow arbitrary local/private-network targets without policy;
- bypass login, CAPTCHA or access restrictions;
- ingest credentials found in local legacy files;
- treat model-readable page text as permission to invoke tools.

SSRF/network/download limits are HEAVY-review concerns when implemented.

## 12. T-09 — current-source revalidation

Before each Mostaql/Khamsat/Bahr specialized adapter:
1. verify public-access terms/boundary;
2. inspect current search/list/detail behavior;
3. determine pagination and JavaScript/session requirements;
4. identify stable fields/selectors/endpoints;
5. decide direct HTTP/API vs Crawl4AI;
6. create fixtures and one bounded live smoke;
7. record current verification date/source version assumptions.

No historical selector is accepted merely because Clients Hunter used it.

## 13. Acceptance criteria for acquisition layer

A phase is not complete because pages were downloaded. It must prove:
- reproducible normalized evidence;
- bounded failure/retry behavior;
- source/URL dedup identity;
- provenance retention;
- public-source boundary;
- representative multilingual/country discovery;
- materially lower noise than legacy keyword-based collection on the sanitized regression corpus.
