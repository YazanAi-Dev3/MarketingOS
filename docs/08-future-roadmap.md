# Marketing OS — Future Roadmap

> Version 2.0 · 2026-09-05 · Purpose: analyzed deferrals, not a feature wish list

## 1. Why this document exists

V1 is intentionally narrow: obtain useful market intelligence, create grounded content, capture conversations and operate safely with existing resources. Future ideas return only when a measurable trigger justifies their complexity.

## 2. Deferral taxonomy

| Item | Class | Value | Why not now | Cheap/current substitute | Activation trigger | Dependencies |
|---|---|---|---|---|---|---|
| `D-01` WhatsApp API automation | cost/platform | faster conversation automation | zero-cost/compliance uncertain | Business App + manual logging | approved zero-cost path + sufficient volume | T-04 |
| `D-02` autonomous posting | maturity/risk | lower operator effort | quality not calibrated | approval required | M-06/M-07 performance + explicit promotion | content feedback |
| `D-03` autonomous outreach | risk | higher throughput | account/brand risk | draft + human send | proven reply quality + founder decision | M-07/M-12 |
| `D-04` web dashboard | need | richer UX | no current need | Telegram + CLI | founders cannot operate efficiently | workflow evidence |
| `D-05` PostgreSQL | scale | concurrency/analytics | SQLite sufficient | SQLite | measured locking/scale/analytics pain | M-09 |
| `D-06` vector DB/RAG | need | semantic retrieval | corpus too small/structured | direct files + SQLite/FTS | retrieval benchmark failure | corpus growth |
| `D-07` fine RBAC | organization | delegated access | two admins only | allowlist + actor_id | team/external operators added | auth design |
| `D-08` Workspace automation | need | automate Gmail/Drive/Sheets | core acquisition first | manual/targeted export | repetitive friction measured | authorized connectors |
| `D-09` Chatwoot inbox | scale | omnichannel ops | inbound low | native channels | conversations hard to track | inbound volume |
| `D-10` LangGraph/workflow engine | complexity | durable branches | Hermes likely enough | explicit job states + cron | pause/resume/recovery complexity | workflow evidence |
| `D-11` CRM/marketing suite | scale | lifecycle campaigns | premature | internal DB + Telegram | lead lifecycle bottleneck | volume |
| `D-12` private source connectors | access | unique intelligence | legal/technical variability | manual import | source proves high yield + official connector | authorization |
| `D-13` auto geographic weights | optimization | adaptive allocation | founders want manual control | suggestions only | sufficient outcome data + explicit permission | M-12 |
| `D-14` learned ranking models | ML/data | potentially better ranking | no labels | rules + LLM-assisted | labeled corpus beats baseline in benchmark | outcomes |
| `D-15` multi-node deployment | scale | capacity/reliability | unnecessary complexity | one VPS | T-06/metrics prove bottleneck | budget/ops |

## 3. Blocked items

`D-01` depends on WhatsApp platform economics/permissions.  
`D-12` depends on a specific authorized source.  
`D-15` depends on actual resource saturation, not theoretical scale.

## 4. Deferred by need/cost

Do not buy or deploy CRM/automation/search/AI products merely because they are common marketing tooling. Current design must prove where the bottleneck actually is.

## 5. Deferred by business/organizational maturity

Autonomy, RBAC and omnichannel tooling become useful only after the startup has repeatable volume and more operators.

## 6. Deferred by scale

PostgreSQL, vector retrieval, learned rankers and multi-node architecture are all scale responses. They must not become prerequisites for getting the first useful leads/content cycle running.

## 7. Explicit negative goals / rejected futures

| Item | Why intentionally rejected | Reconsider only if |
|---|---|---|
| Custom agent framework (`A-032`) | duplicates Hermes | Hermes extension model proven inadequate |
| Fixed source list (`A-033`) | stale/non-dynamic | only as local seed/allowlist, never primary strategy |
| unbounded web search (`A-034`) | low precision/cost | never as governing mode |
| day-one full autonomy (`A-035`) | unsafe/unvalidated | controlled promotion via M-07 |
| paid SaaS now (`A-036`) | violates budget | explicit budget policy superseded |
| Codex marketer runtime (`A-031`) | reserved for engineering | explicit founder decision superseding A-031 |

## 8. Suggested post-launch order

1. Close feedback loop and calibrate `M-01`,`M-02`,`M-06`,`M-12`.
2. Add high-value Google Workspace automations only where repetitive work exists.
3. Consider WhatsApp/omnichannel integration if inbound grows.
4. Promote narrowly proven actions to autonomy, one action class at a time.
5. Upgrade storage/search/workflow architecture only when measurements trigger it.
6. Consider learned ranking after a meaningful labeled outcome dataset exists.

## 9. Rule for adding a new idea

```text
Idea:
Business value:
Why not now:
Current substitute:
Activation trigger:
Dependencies:
What must not be prematurely built:
```

## v2 roadmap delta

- Specialized adapters beyond the first validated Mostaql/Khamsat/Bahr set are **earned**, not prebuilt. `M-14` determines when recurring source value justifies maintenance.
- Legacy Clients Hunter UI/runtime migration is explicitly not on the roadmap; only useful capabilities/fixtures migrate.
- If generic Crawl4AI acquisition proves sufficient for a high-value source, no custom adapter is required merely for architectural symmetry.

