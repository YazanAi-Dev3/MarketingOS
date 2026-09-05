# Hooks and Permissions Plan

Antigravity hooks enforce what prompts should not be trusted to remember under long context.

- **PreToolUse:** deny credential file access/writes and unsafe raw Clients Hunter ingestion; force human confirmation for integrating/destructive Git and privileged filesystem commands.
- **PostInvocation:** verify the observable model identity matches the required Gemini 3.8 Flash High policy. Effective reasoning effort remains an installed-runtime capability check because hooks expose `modelName`, not an independent effort field.
- **Stop:** if background work is still active, continue once so the Orchestrator reconciles or terminates it; then allow stop to avoid a loop.

The global permission example in `setup/antigravity-cli-settings.example.json` uses Deny for secret/Git paths, explicit Allow only for low-risk read-only commands, and leaves unconfigured commands/web/MCP at Antigravity's secure Ask defaults.
