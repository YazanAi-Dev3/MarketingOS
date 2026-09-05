# Engineering Routing Protocol

## CHAT
No repository mutation. Use current evidence; no delegation unless a single material fact is missing.

## MICRO
Small/local/reversible, narrow edit surface, no architecture/provider/secret/external-action/destructive/concurrency trigger.
Flow: Orchestrator → optional Builder → focused checks. Reviewer only if risk/uncertainty appears.
Current workspace allowed only if single-writer and explicitly safe.

## STANDARD
Meaningful implementation with bounded design and moderate blast radius.
Flow: Orchestrator → optional Explorer → Builder (`workspace=branch`) → focused verification → Reviewer → human merge.
Verifier is conditional when independent execution provides meaningful additional evidence.

## HEAVY
Any concrete high-risk trigger: auth/secrets, command/tool permissions, untrusted-web/SSRF, provider/runtime boundary, public external side effects, destructive migration, production infrastructure, concurrency/shared state, or expensive-to-reverse architecture.
Flow: Orchestrator → targeted evidence → Builder (`workspace=branch`) → named verification → Reviewer → Heavy Reviewer → human merge.

## Cost/control rules

- Maximum active subagents: 2.
- Worker delegation depth: 0; only Orchestrator delegates.
- Same-question exploration retry: 0.
- Builder repair budget: 2 substantial repairs after initial implementation.
- Reviewer-driven repair cycles: 2.
- No routine `/boost`, `/teamwork-preview`, or unbounded parallel agents.
