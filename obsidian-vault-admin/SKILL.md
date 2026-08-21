---
name: obsidian-vault-admin
description: Use when syncing Obsidian dual-vault or debugging a plugin.
platforms: [macos, linux, windows]
---

# Obsidian Vault Admin

Filesystem-first administration of Obsidian vaults: syncing the dual-vault setup and
diagnosing community plugins. Complements the bundled `obsidian` skill (which covers
note CRUD) — use THIS one for sync and plugin troubleshooting.

## When to Use

- User asks to sync the Obsidian vaults, or reports one vault is missing/out-of-date.
- A community plugin is "not working": command not found, view won't open, starry graph
  missing, or plugin settings not applying.

## Dual-vault setup

This user runs TWO vaults:

| Vault | Path | Role |
|---|---|---|
| Obsidian Vault | `~/Documents/Obsidian Vault/` | git 主库 → GitHub `obsidian-project-hub`. Primary; write here. |
| My Great Vault | `~/Documents/My Great Vault/` | cloud mirror (read by phone / other devices). |

**Every edit to the primary vault MUST be synced to the mirror.** A past session only
knew one vault and the two drifted for weeks. After writing notes, run:

```bash
rsync -a --exclude='.git' --exclude='.gitignore' --exclude='.obsidian' \
  "$HOME/Documents/Obsidian Vault/" "$HOME/Documents/My Great Vault/"
```

- `.obsidian` is intentionally excluded so the two vaults' settings/plugins don't fight.
  Consequence: **plugin config changes (e.g. Galaxy View style) do NOT auto-sync** — copy
  the specific file over manually when the user wants them matched.
- `rsync` without `--delete` preserves mirror-only files; `diff` the two trees to catch drift.

## Debugging a community plugin

Full checklist lives in `references/plugin-debugging.md`. The one-liner that matters:

**Command palette returns "未找到命令 / Command not found" for a plugin's command ⇒
the plugin is NOT loaded** (not a language mismatch, not a config problem, not a missing
file). Verify files / enable-state / config / version, then restart Obsidian (`Cmd+Q`,
not close-window) to apply any pending update and force a clean reload.

## Pitfalls

- **Separate-view confusion**: a plugin may render its OWN view, not the native feature.
  `Galaxy View` (starry 星空) ≠ Obsidian's native `关系图谱` (Graph View). If the user
  screenshots the native graph and says "还是没有", first confirm they're opening the
  plugin's view (ribbon icon / command palette), not the native one.
- **Pending update = stale plugins**: `"An update is already downloaded"` in the app
  log means an update is waiting on a restart; plugins often stop loading cleanly until
  that restart happens.
- **Read-only diagnosis first**: never tell the user to restart until you've confirmed
  files/enable/config on disk are correct — otherwise a restart hides the real cause.
