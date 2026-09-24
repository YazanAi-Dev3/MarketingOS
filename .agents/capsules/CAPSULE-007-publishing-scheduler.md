# CAPSULE-007 — Social Publishing Scheduler & Postiz Adapter

Route: STANDARD (Publishing & Integration Dispatcher)
Risk trigger: External Publishing Boundary (A-007, I-02 - External posting side-effects, Human Approval Enforcement)
Candidate workspace: candidate/capsule-007-publishing-scheduler

## 1. Outcome
A production-ready publishing and scheduling subsystem (`PublishingService`, `PostizAdapter`) that connects approved content assets created by `ContentEngine` to social channels (via self-hosted Postiz `A-021` or direct Telegram dispatch), provides an operator manual export fallback when Postiz is offline (`R-04`), and strictly enforces that no external transmission occurs without explicit, persisted human approval (`A-007`, `I-02`).

## 2. Acceptance behavior
1. **Postiz API Adapter (`PostizAdapter`):**
   - Connects to self-hosted Postiz REST API (`base_url`, `api_key`).
   - Supports health check, listing connected channels, and creating/scheduling posts.
   - Hermetic mock mode for tests when Postiz service is offline.
2. **Publishing Service & Dispatcher (`PublishingService`):**
   - Strictly enforces human approval check against SQLite `approvals` table (`action_type="publish_content"`, `decision="approved"`).
   - Raises `PermissionError` if an asset is not approved.
   - Routes Telegram posts directly via Telegram bot or Postiz.
   - For other social channels (LinkedIn, Twitter, Instagram), dispatches to Postiz if available.
   - If Postiz is unconfigured or unreachable, generates a structured manual export package with copy-paste text and media briefs (`R-04`).
   - Transitions `ContentAsset` status to `PUBLISHED` or `SCHEDULED` in `content_assets`.
3. **Hermes Domain Tool (`publish_content`):**
   - Added to `marketing_plugin/tools/domain_tools.py` and exported in `marketing_plugin`.
4. **Comprehensive Test Suite:**
   - Unit tests for adapter, service, and approval gates.
   - Integration tests covering the full pipeline from approval to dispatch and state updates.
   - 100% test pass rate across the full test suite (>=125 tests).

## 3. Authority / Invariants
- `A-007`: Public external actions require human approval initially.
- `A-021`: Postiz self-hosted is the preferred social scheduling/publishing layer after real-account verification.
- `R-04`: Postiz must not become an unnecessary MVP blocker; maintain manual/direct fallback paths.
- `I-02`: Publishing/sending cannot occur without persisted approval.

## 4. Known evidence
- `marketing_plugin/services/content_engine.py`: Creates `ContentAsset` with status `awaiting_approval`.
- `marketing_plugin/repositories/approval_repo.py`: Tracks human approvals.
- `marketing_plugin/repositories/content_repo.py`: Stores `ContentAsset`.
- `docs/04-operations-deployment-security.md`: Pinned Postiz configuration.

## 5. Edit surface
- `marketing_plugin/adapters/postiz_adapter.py` (New: Postiz REST client)
- `marketing_plugin/services/publishing_service.py` (New: publishing dispatcher)
- `marketing_plugin/services/__init__.py` (Export `PublishingService`)
- `marketing_plugin/tools/domain_tools.py` (Add `publish_content` tool)
- `marketing_plugin/__init__.py` (Export `publish_content`)
- `tests/unit/test_postiz_adapter.py` (New)
- `tests/unit/test_publishing_service.py` (New)
- `tests/integration/test_publishing_pipeline.py` (New)
- `agent_docs/STATE.md` (Update state)

## 6. Forbidden surface
- `migrations/001_initial_schema.sql` (Frozen schema)
- `config/country-priorities.yaml` (Frozen configuration)
- External live social network calls during routine test suites.
- Dispatching any unapproved asset to external networks (`A-007`, `I-02`).

## 7. Implementation constraints
- Zero incremental cost (`A-020`).
- Hermetic tests without required network connection to live Postiz.
- Graceful degradation if Postiz is absent (`R-04`).

## 8. Verification
- `pytest tests/unit/test_postiz_adapter.py`
- `pytest tests/unit/test_publishing_service.py`
- `pytest tests/integration/test_publishing_pipeline.py`
- `pytest` (Full suite 100% pass)

## 9. Documentation / state delta
- Update `agent_docs/STATE.md` recording `CAPSULE-007` completion.

## 10. Stop / escalation conditions
- Attempt to dispatch unapproved content.
- Unhandled exceptions when Postiz is unreachable.
- Repair budget exceeded (max 2 repairs).

