# Marketing OS — Antigravity Complete Engineering Package v2.1

A self-contained pre-implementation package for the Hermes-based Marketing OS. It combines current project documentation, a hardened Google Antigravity multi-agent engineering control plane, deterministic safety hooks, least-privilege setup guidance, regional source-acquisition architecture, and a selective migration plan for the legacy Clients Hunter codebase.

Required engineering model policy: Gemini 3.8 Flash High + High effort for every custom engineering role. See `README_AR.md` and `docs/14-antigravity-engineering-environment.md` for setup and rationale.

## Validation status

Static package validation passes with zero agent-definition warnings, hook self-tests pass, secret/quarantine scan passes, the documentation suite passes, and the workflow-engine validator reports zero errors. Native Antigravity behavior remains intentionally gated by the local `AG-CC-01..05` dry run; product implementation then begins with `T-08` followed by `T-01`.

## Windows note: hooks and datacloud_telemetry

- Project hook handlers intentionally live in `.agents/scripts/` because commands in `.agents/hooks.json` resolve from the customization context.
- If the global `googlecloudtools.datacloud_telemetry` plugin raises `MODULE_NOT_FOUND` with a duplicated/quoted Windows path, disable that plugin from **Antigravity > Settings > Customizations / Plugins**, restart Antigravity, then run the hook self-tests.
