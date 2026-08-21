# Diagnosing Obsidian Community Plugins

Playbook for "the plugin is installed but not working" — e.g. its command returns
`未找到命令 / Command not found`, or its view won't open. Validated on macOS with a
dual-vault setup.

## Golden rule

**Command palette returns "未找到命令 / Command not found" for the plugin's command
⇒ the plugin is NOT loaded in the current session.** It is not a language mismatch,
not a missing config file, not a "wrong search term". When a plugin loads, it registers
its commands via `addCommand({id, name, callback})` in `onload()`; if those commands
aren't findable, `onload()` did not complete.

(If the plugin loaded and only the display language differed, one of the two names —
Chinese `打开星系视图` or English `Open Galaxy View` — would still match. Both failing
is proof of not-loaded.)

## Separate-view confusion (user-facing gotcha)

Some plugins render a **separate view**, not the native feature. `Galaxy View` (the
"星空/starry" cinematic 3D graph) is NOT Obsidian's native `关系图谱` (Graph View).
The native graph stays plain regardless of the plugin. Users will screenshot the native
graph and say "还是没有" — first check they are opening the plugin's own view
(ribbon icon or command palette), not the native graph.

## Diagnostic checklist (filesystem-first, all read-only)

Run these before asking the user to restart anything:

1. **Files present** — `ls -la <vault>/.obsidian/plugins/<id>/` should have
   `main.js`, `manifest.json`, `styles.css`, `data.json`. Compare `md5` against a
   vault where the plugin is known to work (files are usually identical).
2. **Enabled** — `<vault>/.obsidian/community-plugins.json` must list the plugin id.
3. **Config valid** — `python3 -c "import json; json.load(open('.../data.json'))"`.
   A corrupt `data.json` can make `onload()` throw before registering commands.
4. **Loaded-before evidence** — `<vault>/.obsidian/workspace.json`:
   - `left-ribbon.hiddenItems` contains `"<id>:<display name>": false` ⇒ ribbon icon
     was registered (plugin loaded at some point).
   - a leaf `"type": "<id>"` in the layout ⇒ its view was actually open.
   Presence here proves the plugin *used to* load; absence of the command *now* means
   the current session failed to load it.
5. **Version compat** — `defaults read /Applications/Obsidian.app/Contents/Info.plist
   CFBundleShortVersionString` vs `manifest.json`'s `minAppVersion`.
6. **Pending update** — grep `~/Library/Application Support/obsidian/obsidian.log` for
   `"An update is already downloaded"`. A downloaded-but-not-applied app update
   (needs a restart) is a common reason plugins end up stale/not-loaded.

## Reading the plugin's load order (minified main.js)

Grep for `onload()`, `addCommand`, `addRibbonIcon` to see registration order. Key
insight: plugins often read/validate settings **before** registering commands:

```js
onload(){ this.settings = Hr(await this.loadData()), /* ... */ this.addCommand(...) }
```

If `loadData()` throws (bad JSON) the commands never register. Note that the `Hr()`
normalizer here is a *safe* fallback mapper (type-checks each field, falls back to
defaults) — so a structurally-valid-but-wrong-value `data.json` will NOT crash it;
only truly invalid JSON or a throwing pre-step will.

## Fix that actually worked

**Full restart of Obsidian** (`Cmd+Q` to quit the app, then reopen — NOT closing the
window with the red button). A full restart applies any pending app update AND forces
every plugin to reload cleanly. This resolves "files/config/enable are all correct but
commands still not found".

After restart, verify: the ribbon icon appears at the bottom of the left sidebar, or
`Cmd+P` finds the command again.

## Key file locations (macOS)

| What | Path |
|---|---|
| Plugin files | `<vault>/.obsidian/plugins/<id>/` |
| Enabled plugins | `<vault>/.obsidian/community-plugins.json` |
| Workspace (load evidence) | `<vault>/.obsidian/workspace.json` |
| Vault registry (which vaults, open?) | `~/Library/Application Support/obsidian/obsidian.json` |
| App log (update status) | `~/Library/Application Support/obsidian/obsidian.log` |
| App version | `defaults read /Applications/Obsidian.app/Contents/Info.plist CFBundleShortVersionString` |
