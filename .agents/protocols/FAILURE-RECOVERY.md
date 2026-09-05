# Failure Recovery Protocol

## Builder failure
After initial implementation + 2 substantial repair attempts:
- stop mutation;
- return Knowledge Delta with failure evidence;
- Orchestrator classifies missing evidence / wrong assumption / oversized capsule / environment blocker / upstream incompatibility / user decision;
- re-slice or reframe before spawning a clean Builder session.

## Reviewer rejection
At most 2 bounded review-driven repair cycles. If the same class of finding recurs, Orchestrator must reassess the capsule/architecture instead of cycling.

## Explorer failure
No repeated same-question exploration. Return what is known, what cannot be established, and the exact capability experiment or user decision required.

## Verifier blocked
Never modify code from Verifier. Report environment/capability blocker and let Orchestrator decide whether the check is mandatory, substitutable, or deferred.

## Agent hang / runaway
Use `/agents` or `manage_subagents` to inspect/kill a stuck worker. Check custom-agent tool names against official documented names before retrying. Do not recursively spawn replacements.
