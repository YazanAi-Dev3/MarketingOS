# Community Operational Observations

These are **anecdotal signals, not governing facts**. Official Antigravity documentation remains authoritative for supported behavior. Signals were rechecked 2026-09-05.

Recurring current community themes:

- aggressive parallel/subagent-heavy work can consume quota much faster than a serial or tightly bounded workflow;
- context discipline and specialized handoff files are commonly used to keep long engineering sessions tractable;
- custom-agent/subagent behavior has changed across releases, so users frequently benefit from version-specific smoke tests rather than trusting historical behavior;
- recent releases explicitly include subagent/hook stability improvements, reinforcing the need to re-run capability checks after meaningful upgrades.

Project response:

- max two active subagents;
- worker delegation depth zero;
- no default `/boost`/broad teamwork dependency;
- detailed role definitions but only three concise Always-On Rules;
- focused progressive-disclosure Skills;
- deterministic Hooks/Permissions for critical prohibitions;
- Task Capsules and compact deltas instead of inherited long conversations;
- installed-release capability gates (`AG-CC-01..05`) before trusting native inheritance/worktree behavior.

These signals must never be converted into a product or platform contract without official evidence or a local capability test.
