# CONVENTIONS

## Verified now

Static control-plane verification:
```bash
python scripts/verify_control_plane.py
```
This validates the normalized manifest, Antigravity custom-agent frontmatter/tool names, required workspace files, role separation, repair budgets, exact model-pin fallback scripts, and Google-only product runtime provider guard.

## Required Antigravity local smoke

Run `.agents/workflow/DRY-RUN.md` after installation. Native subagent mode is not considered fully proven until AG-CC-02 (High-effort inheritance) and AG-CC-03 (candidate worktree review access) pass.

## Not yet verified / do not invent

The product repository is greenfield. `./scripts/verify.sh` is a design target, not yet a verified executable command. Add actual setup/test/lint/type/schema/eval commands only after they exist and have been run.

## Git

- `main` trusted; final merges human-controlled in V1.
- STANDARD/HEAVY Builder uses Antigravity `workspace=branch`.
- No concurrent writers in one worktree.
- At most two active subagents by workflow policy.

## Sensitive data

Never commit or intentionally pass passwords, API keys, OAuth credentials, private keys, bot tokens, session cookies, SSH keys, or equivalent secrets. Engineering Antigravity session credentials are not product runtime credentials.

## Engineering style

Prefer adapting mature OSS/upstream extension contracts over rebuilding infrastructure. Keep custom code narrow around Marketing OS domain logic and integrations.
