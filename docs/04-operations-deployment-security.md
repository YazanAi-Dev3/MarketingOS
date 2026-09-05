# Marketing OS — Operations, Deployment & Security

> Version 2.0 · 2026-09-05 · Documentation-ready · Operational design

## 1. Governing operational constraints

1. **Zero incremental cost (`A-020`)**: الإنتاج يجب أن يعمل فوق الـVPS وGoogle AI Pro/Antigravity الموجودين، وبرمجيات OSS. أي API مدفوعة تبقى معطلة حتى قرار superseding صريح.
2. **Hermes-first (`A-009`)**: لا fork للـcore ما دام Plugin/Skill/config يحل المشكلة.
3. **Google-only runtime reasoning (`A-019`, `A-031`)**: Antigravity أولاً، Gemini API fallback؛ Codex ليس runtime.
4. **Public-source collection (`A-014`)**: لا تجاوز authentication/CAPTCHA أو شروط منصة بقصد استخراج بيانات خاصة.
5. **Human gate (`A-007`)**: النشر، الإرسال، الأسعار والالتزامات التجارية لا تتجاوز approval policy.
6. **Evidence-first (`A-017`)**: الاستنتاج بلا evidence قابل للتتبع لا يدخل lead decision.
7. **Single VPS until disproven (`D-15`)**: لا توزيع/cluster قبل `T-06`.

## 2. Deployment topology

### 2.1 Topology

```text
                    Internet / Public Sources
                              │
                        HTTPS / Search
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Existing VPS                        │
│                                                             │
│  Hermes Gateway                                             │
│  ├─ CLI/TUI                                                 │
│  ├─ Telegram private operator surface                       │
│  ├─ Cron / scheduled jobs                                   │
│  ├─ Marketing Plugin + Skills                               │
│  └─ Antigravity Adapter / Provider Plugin  ───────┐         │
│                                                   │         │
│  SearXNG ──► Search Results                         │         │
│  marketing.db + raw artifacts                      │         │
│  Postiz (phase-gated) ──► social publishing        │         │
│                                                   │         │
└───────────────────────────────────────────────────┼─────────┘
                                                    │
                                                    ▼
                                   Google Antigravity / Gemini
                                   (no Codex runtime)
```

### 2.2 Service/process boundaries

- **Hermes Gateway**: sessions, Telegram/CLI, scheduler, tool/skill dispatch.
- **Marketing Plugin**: domain tools, policy enforcement, marketing DB access.
- **Antigravity Adapter**: serializes a bounded task contract, applies secret redaction, invokes official `agy` headless, validates output, maps errors.
- **SearXNG**: self-hosted metasearch only; not marketing source-of-truth.
- **SQLite + filesystem**: authoritative marketing domain state and raw artifacts.
- **Postiz**: optional V1 publishing component only after `T-03`,`T-06`,`T-07`.

### 2.3 Rejected deployment alternatives

- Paid workflow/SaaS stack: violates `A-020`.
- Custom web dashboard: rejected by `A-025`.
- Distributed services/microservices: deferred `D-15`.
- Running the marketer on Codex: rejected `A-031`.

### 2.4 Environment specification

Baseline: Linux VPS with Docker/Compose where upstream projects recommend it, Python environment for custom plugin/tools, persistent volumes for Hermes state, marketing data, SearXNG config, and Postiz dependencies if enabled.

Exact CPU/RAM/storage are not invented. `T-06` measures whether co-location is viable. If Postiz is too heavy, MVP remains valid with direct Telegram and manual Instagram publishing until capacity/budget changes.

## 3. Resource/capacity budget

### Memory/storage

Owned by `T-06`, `M-09`.

Measure at minimum:
- idle and peak RSS per service;
- SQLite/raw artifact growth per 100/1000 pages;
- Postiz PostgreSQL/Redis/Temporal footprint if enabled;
- Antigravity adapter concurrency effects;
- filesystem free-space floor.

### CPU

Background search/crawl jobs are rate-limited. Parsing and normalization are deterministic. Model reasoning is external to VPS except adapter overhead.

### Connections/queues

No distributed queue in MVP. Hermes cron + persisted `Job` state are sufficient. Every scheduled job must be idempotent and resumable from stored inputs/outputs.

## 4. Isolation of interactive vs background workloads

Interactive Telegram/CLI commands must not wait behind wide crawls.

Rules:
- scans use bounded concurrency (`M-08`);
- background jobs may be paused/cancelled;
- model tasks have explicit timeout;
- Postiz publishing is decoupled from discovery;
- long aggregation can run as scheduled work, not inside a Telegram request.

If resource pressure occurs, priority order is:
1. operator/approval surface;
2. persistence;
3. lead inspection;
4. scheduled intelligence;
5. publishing/analytics enrichment.

## 5. Latency budget

No false numeric SLA is declared. `M-08` measures practical targets.

### Interactive path

```text
Telegram/CLI → Hermes → local DB/tool → optional Antigravity → response
```

Required behavior:
- immediate acknowledgement for jobs that become asynchronous;
- bounded model timeout;
- no indefinite browser/search loops;
- present partial evidence if a downstream source fails.

### Mandatory timeout classes

Calibrate:
- HTTP connect/read timeout;
- search request timeout;
- page extraction timeout;
- `agy` print timeout;
- Postiz API/CLI timeout.

All retries must be bounded and use backoff for transient errors.

## 6. Threat model

| Threat | Likelihood | Impact | Asset/boundary | Defense | Verification |
|---|---|---:|---|---|---|
| Secret exfiltration to model | Medium | High | model boundary | deterministic redactor + deny patterns + no raw env dump | synthetic secret leak tests |
| Prompt injection in web content | High | High | untrusted source → tools | web text is evidence, never authority; tool allowlists; approval gates | injection fixture tests |
| SSRF/internal network probing | Medium | High | fetcher/browser | URL scheme/host policy, block loopback/private ranges where collector controls fetch | security tests |
| Unauthorized Telegram operator | Medium | High | operator surface | private bot/chat allowlist, pairing/auth from Hermes, audit actor_id | negative auth tests |
| Duplicate external action | Medium | High | publish/send | idempotency key + approval state + provider result record | replay test |
| Malicious/incorrect source | High | Medium | intelligence | provenance + multidimensional source health + corroboration/confidence | evaluation corpus |
| Account/platform suspension | Medium | High | social platforms | official OAuth/API paths only; no scraping/auth bypass; staged automation | T-03/T-07 |
| VPS compromise | Low/Med | High | all local state | least privilege, firewall, patching, SSH keys, secrets outside Git, backups | ops checklist |
| Database corruption/data loss | Low/Med | High | marketing.db | atomic backups, schema migrations, restore drill | M-13 restore test |
| Unbounded cost/API usage | Medium | High | Gemini API fallback | disabled unless zero-spend rule verified; quota/cost breaker | T-05 + config tests |

## 7. Application security

### Authentication/authorization

- CLI: OS/SSH access boundary.
- Telegram: exact founder user/chat allowlist.
- Both founders admin in V1 (`A-026`); all mutations record `actor_id`.
- Postiz admin access must not be public without strong auth/reverse proxy controls.

### Secrets

Never in Git, prompts, logs, or raw artifacts intentionally. Expected classes:
- Telegram bot token;
- SearXNG/Postiz credentials;
- Antigravity cached auth and/or Gemini API key;
- social OAuth secrets;
- SSH/private keys.

Permissions should restrict credential files to the service user. Backups containing secrets are encrypted or secrets are excluded/re-provisioned.

### Logs/privacy

Default logs store IDs, hashes, status, sizes, timing, provider identity, not full customer conversation text unless required for audit. Raw interaction content can be stored separately with explicit retention (`M-09`).

## 8. AI/model/tool/content injection risks

Hard rule: **content retrieved from the web can supply facts, never permissions or operating instructions.**

Enforcement points:
1. collector marks external content untrusted;
2. Antigravity task contract states evidence/instructions separately;
3. model tool permissions are narrow;
4. external actions require independent approval state;
5. output schema validation rejects malformed/hallucinated references;
6. every cited evidence ID must exist in DB.

Do not use `--dangerously-skip-permissions` for normal production Antigravity runs. Scoped permissions are preferred.

## 9. Cost circuit breakers and dependency resilience

### Cost breaker

- no paid provider configured by default;
- Gemini API fallback is disabled until `T-05`;
- per-job model call count/size logging;
- when Google quota/path is unavailable, queue or degrade—never silently switch to paid third party.

### Dependency breaker / graceful degradation

| Failure | Still works | Unavailable | User-visible behavior |
|---|---|---|---|
| Antigravity unavailable | DB, deterministic extraction, source search, Telegram status | semantic analysis/content drafting | job queued; operator notified |
| Gemini API fallback unavailable | same as above | fallback reasoning | no paid fallback |
| SearXNG degraded | known URLs/manual analyze, existing DB | broad discovery | mark scan partial |
| individual search engines fail | other engines | affected result diversity | lower source confidence |
| Telegram down | CLI/scheduled persistence | mobile approvals | approvals stay pending |
| Postiz down/not installed | content generation/approval | automatic scheduling | export/manual publish |
| Instagram integration fails | Telegram + content store | Instagram auto-publish | manual Instagram publish |
| SQLite locked/corrupt | read-only artifacts/backups depending state | writes | stop jobs; do not lose/duplicate actions |
| VPS resource pressure | operator/control path | background breadth | pause crawl/publishing jobs |

## 10. Backup and recovery

### Back up

- `marketing.db`;
- migration/version metadata;
- config files;
- irreplaceable raw/evidence artifacts according to `M-09`;
- Hermes project skills/plugins/config excluding regenerable vendor code;
- Postiz DB if Postiz is active.

### Rebuild

- SearXNG container/image;
- Hermes upstream pinned checkout/image;
- generated caches;
- search result cache.

### Targets

`M-13` determines practical RPO/RTO after observing change rate. Before production, at least one automated backup and one restore drill are mandatory.

## 11. Monitoring and alerting

Track:
- job success/partial/failure;
- scan yield by country/intent;
- SearXNG engine error/captcha/429 rates;
- fetch failure classes;
- evidence extraction counts;
- model call latency/status/token usage if reported;
- approval backlog;
- publish failures;
- disk space and backup age;
- SQLite errors.

Alerts should be actionable and sent to private Telegram, e.g.:
- no successful scheduled scan in expected window;
- disk below calibrated floor;
- backup stale;
- repeated Antigravity auth failure;
- Postiz publish failure after approval;
- source health collapse for a high-value source.

## 12. Deployment, rollback, migration, rebuild

### Release

1. backup DB/config;
2. pin/update version;
3. run migrations in test copy;
4. `verify.sh`;
5. smoke Hermes gateway/Telegram;
6. smoke Antigravity adapter;
7. smoke SearXNG;
8. if enabled, Postiz dry/owned-account test;
9. deploy;
10. observe one scheduled cycle.

### Rollback

Code/config rollback must not roll domain data backward blindly. Schema migrations require reversible/down path or restore plan.

### Upstream upgrades

Hermes/Postiz/SearXNG versions are pinned. Upgrade is treated as compatibility work with contract smoke tests; no rolling `latest` in production.

## 13. Pre-launch checklist

- [ ] `T-08` Hermes version/interface pinned.
- [ ] `T-01` Antigravity path passed, or `T-05` zero-cost Gemini fallback selected.
- [ ] `T-02` regional SearXNG benchmark passed for representative markets.
- [ ] `T-06` VPS capacity passed for enabled services.
- [ ] founder Telegram allowlist tested.
- [ ] country weights explicitly set.
- [ ] secret redaction tests pass.
- [ ] evidence/provenance regression tests pass.
- [ ] backup + restore drill completed.
- [ ] paid-provider paths absent/disabled.
- [ ] Postiz/Instagram tests completed only if automatic publishing is enabled.
- [ ] external actions require persisted approval.

## v2 operations/security addendum — crawling and legacy quarantine

- Crawl4AI/browser acquisition handles **untrusted external content**. Treat fetched text/HTML as data, never tool instructions. SSRF/private-network/network-budget controls become HEAVY-review requirements when network acquisition is implemented.
- Direct HTTP/API may bypass Crawl4AI only when public, stable and sufficient; it must preserve the same provenance/timeout/size policies.
- The original Clients Hunter archive is quarantined outside the new repository. Its `.env`, Firebase service-account material, raw DB and other credentials must not be copied into tracked state or model context. Rotate any still-active legacy credentials externally (`R-05`).
- Repository Hooks/secret scanner defend the engineering environment against accidental legacy credential ingestion.
- On Windows 11, do not treat Antigravity terminal sandbox policy as the only security boundary; current official docs state OS-level terminal sandbox preview is macOS/Linux with Windows support pending. Permissions, Hooks, Git worktrees and human confirmation remain required.

