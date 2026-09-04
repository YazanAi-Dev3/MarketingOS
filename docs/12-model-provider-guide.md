# Marketing OS — Model Provider Guide

> Version 1.0 · 2026-09-03 · Runtime policy: Google-only · External facts verified 2026-09-03

## 1. Current external constraints

- `A-019`: runtime reasoning is **Antigravity preferred, Gemini API fallback**.
- `A-031`: Codex is explicitly rejected as a marketer/runtime provider.
- `A-020`: no incremental paid API/SaaS spend. Gemini API fallback is enabled only when the chosen usage path remains within zero-incremental-cost allowance or the budget decision is explicitly changed.
- `A-018`: large relevant context is allowed, but secrets/credentials and prohibited data must be removed first.

These constraints are more important than model benchmark rankings.

## 2. Provider/path table

| Provider/path | Access | Role | Key current facts | Project status |
|---|---|---|---|---|
| **Google Antigravity CLI (`agy`)** | signed-in cached credentials; CLI also supports Gemini API-key mode | preferred runtime reasoning path | official headless mode supports `text`, `json`, `stream-json`, `--json-schema`, model/agent selection, timeout and programmatic sessions | preferred; `T-01` blocking integration spike |
| **Gemini API / Google AI Studio** | API key | conditional fallback | Antigravity CLI docs describe explicit Gemini provider/API-key mode; direct Hermes integration capability must be verified for chosen API path | conditional; `T-05` |
| **Codex/ChatGPT** | existing subscription | engineering only | intentionally not evaluated for runtime use | **REJECTED runtime (`A-031`)** |
| Third-party paid APIs | API billing | none | violate current budget | disabled |

## 3. Priority path: Antigravity

### Why

The startup already pays for Google AI Pro/Antigravity, quotas are intended to be exploited, and the user explicitly prefers it over coupling runtime to Codex.

### Relevant verified CLI capabilities

As of 2026-09-03, official Antigravity headless documentation shows:
- `agy -p` non-interactive runs;
- cached authentication for headless use;
- JSON and streaming JSON output;
- `--json-schema` structured output;
- conversation continuation;
- model/effort/agent selection;
- exit/error status and configurable print timeout;
- scoped permission rules.

### Hermes integration strategy (`T-01`)

Hermes officially supports:
- general plugins for tools/hooks/integrations;
- **model-provider plugins** under its provider plugin system without editing core.

Therefore investigate in this order:

1. **Model-provider plugin** if Antigravity can satisfy Hermes' inference/provider contract cleanly.
2. **General tool/skill adapter** around `agy` for specialist/bounded tasks if transparent provider semantics are not suitable.
3. If core reasoning still cannot be supported adequately, execute `T-05` for Gemini API.

Do not patch Hermes core merely to force the integration; that would require ADR and evidence that extension points are insufficient.

## 4. Gemini API fallback

Gemini API is not assumed to be “included” merely because Google AI Pro exists. `T-05` must record:
- account/API-key setup;
- exact model/path used;
- whether usage stays zero incremental cost under current account/limits;
- structured output/tool behavior;
- context limits required by our workloads;
- data policy;
- measured latency/error behavior;
- Hermes adapter/provider compatibility.

If zero-cost criteria fail, fallback remains disabled; jobs queue/degrade rather than charging silently.

## 5. Privacy/data exposure

### Allowed by project policy

Large relevant context, including:
- public web data;
- company research/evidence;
- internal service/brand documents;
- customer/lead interaction text when needed for the task.

### Hard exclusions

- passwords;
- API keys;
- OAuth access/refresh tokens;
- private keys;
- session cookies;
- credential files/stores;
- secrets embedded in logs/config;
- content the company is not permitted to disclose.

### Enforcement

A deterministic redaction layer runs before serialization. Logs record provider path, task, size/token usage when available, status and references; raw prompts are not required in routine logs.

## 6. Catalog/rate-limit volatility

Provider/model identifiers and quotas are volatile.

Required protections:
- model/provider IDs only in config;
- health/smoke command;
- bounded retries;
- explicit timeout;
- dated facts in this document;
- no paid automatic fallback;
- output schema validation independent of model;
- evaluation corpus to compare model/effort changes.

`M-10` selects model/effort routing from observed quality/latency/quota—not intuition.

## 7. Task-to-provider routing

| Task | Preferred | Fallback | Why |
|---|---|---|---|
| lead semantic assessment | Antigravity | Gemini API if T-05 enabled | evidence-heavy reasoning |
| large regional synthesis | Antigravity | Gemini API if enabled | exploit large context/quota |
| content strategy/master draft | Antigravity | Gemini API if enabled | quality/creative synthesis |
| platform rewrite | Antigravity lower effort/model per M-10 | Gemini API if enabled | cheaper/faster task class |
| deterministic extraction/dedupe | **no model** | — | should remain code |
| provider outage/quota issue | queue/defer | Gemini only if pre-enabled | zero-cost invariant |

Codex is absent from this routing table by design.

## 8. What to record per run/provider

```text
provider_path
model/agent/effort identity
runtime/client version
auth method class (never token)
verification date
task_type
input refs + size estimate
output schema version
duration
usage/token fields when reported
status/error class
fallback invoked
human quality label
evidence validation result
```

## 9. Account/setup checklist

- [ ] install/auth `agy` interactively once.
- [ ] test headless JSON + schema output.
- [ ] use scoped permissions; no blanket unsafe approval in normal production.
- [ ] close T-01 with Hermes integration.
- [ ] if needed, create Gemini API key and run T-05.
- [ ] confirm no Codex runtime provider/config.
- [ ] confirm no paid third-party provider.
- [ ] secret-redaction integration test.
- [ ] timeout/error/fallback tests.

## 10. Durable rules

1. **Google-only runtime until explicitly superseded.**
2. **Measure the exact account/path you deploy; do not infer API economics from a consumer subscription.**
3. **Provider/model changes cannot weaken domain evidence, approval or secret boundaries.**

## Verified external references — 2026-09-03

- Google Antigravity Headless mode: `https://antigravity.google/docs/cli/headless/`
- Google Antigravity CLI installation/auth and Gemini API-key mode: `https://antigravity.google/docs/cli/install/`
- Hermes Plugin system: `https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins`
- Hermes Model Provider Plugins: `https://hermes-agent.nousresearch.com/docs/developer-guide/model-provider-plugin`
