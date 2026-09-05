---
name: clients-hunter-migration
description: Migrates useful capabilities from the legacy Clients Hunter donor codebase into the new Marketing OS architecture by evidence-based KEEP/IMPROVE/CLEAN_REIMPLEMENT/DISCARD decisions. Use when implementing Mostaql, Khamsat, Bahr, legacy lead regression fixtures, dedup, retry, or shallow-to-deep acquisition behavior.
---
# Clients Hunter Selective Migration Skill

Clients Hunter is **not** an application dependency. Its raw archive/database/credentials are not copied into production.

## Migration method

For each capability:
1. Identify user/business behavior worth preserving.
2. Inspect legacy implementation and dependency assumptions.
3. Revalidate any external-site behavior against the current public site (`T-09`).
4. Classify:
   - `KEEP_BEHAVIOR`
   - `IMPROVE`
   - `CLEAN_REIMPLEMENT`
   - `DISCARD`
5. Map it into current Marketing OS ownership.
6. Add focused fixture/regression evidence.

## Default inventory

- Source adapter concept → KEEP/GENERALIZE.
- Mostaql/Khamsat/Bahr source knowledge → CLEAN_REIMPLEMENT after current-site validation.
- Shallow→deep acquisition → KEEP/GENERALIZE.
- URL dedup → IMPROVE into canonical URL/source/entity identity.
- Retry/backoff → KEEP behavior only where lower layer does not already solve it.
- Keyword lists → REUSE as query-planning hints; DISCARD as relevance/qualification classifier.
- Firebase → DISCARD.
- Firecrawl dependency → DISCARD; use new acquisition architecture.
- Streamlit UI → DISCARD from MVP.
- Historical lead records → sanitize and convert to regression/evaluation fixtures.

## Security quarantine

Never read/copy/commit actual secrets for migration. Do not place the raw legacy `.env`, Firebase service-account JSON,
archive, or unsanitized database under tracked project paths. If a legacy credential may still be active, flag rotation to the human owner.
