# Windows Hook Troubleshooting

## 1. Project hook path

Workspace hook commands are defined in `.agents/hooks.json`. Their executable handlers live in `.agents/scripts/` and are referenced as `python ./scripts/<hook>.py`. This layout mirrors Antigravity's customization-directory hook examples.

If an older v2.0 workspace reports `.agents\scripts\hook_pretool_guard.py` missing, copy these files from root `scripts/` into `.agents/scripts/`:

- `hook_pretool_guard.py`
- `hook_model_guard.py`
- `hook_stop_guard.py`

Do not replace them with empty stubs; doing so silently disables the safety policy.

## 2. Google datacloud telemetry plugin bug on Windows

A current Windows bug can construct a duplicated path containing embedded quotes for `telemetry_hook_bundle.js`, causing every PreToolUse action to fail. Disable `googlecloudtools.datacloud_telemetry` through Antigravity's plugin/customization manager until Google ships a working version for your installation. Deleting the plugin directory is not a reliable fix because managed plugins can be restored.

After disabling it, restart Antigravity and confirm the broken hook no longer appears in the active hooks list.

## 3. Verify

From the repository root:

```powershell
python scripts/test_hooks.py
python scripts/verify_control_plane.py
```

Then start a fresh Antigravity conversation and verify:

1. A normal `view_file` succeeds.
2. Reading `.env` is denied.
3. A harmless `run_command` succeeds.
4. A destructive Git command requests explicit approval.
