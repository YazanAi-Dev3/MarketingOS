# Task Capsule Template

```markdown
# CAPSULE <id> — <short name>

Route: MICRO | STANDARD | HEAVY
Risk trigger: NONE | <specific trigger>
Candidate workspace: current | branch/worktree

## Outcome
<one testable end state>

## Acceptance behavior
- ...

## Authority / invariants
- `A-...` / owning docs

## Known evidence
- path/symbol/current behavior

## Edit surface
- allowed paths/modules

## Forbidden surface
- explicit non-goals/areas

## Implementation constraints
- dependencies/provider/cost/security rules

## Verification
- command/gate + expected evidence

## Documentation/state delta
- files/status items to update

## Stop conditions
- architecture unresolved
- external capability unproven
- scope expansion
- repair budget exhausted
```
