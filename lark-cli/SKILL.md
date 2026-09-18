---
name: lark-cli
description: Official Feishu/Lark CLI (@larksuite/cli) — the single unified CLI for all Feishu operations. MCP removed; third-party CLIs removed; CLI-only architecture.
category: productivity
version: 2.0.0
---

# Lark CLI (Official)

**`@larksuite/cli`** (binary: `lark-cli`) is the **official** Feishu/Lark CLI maintained by ByteDance (bytednpm). It is the ONE and ONLY tool for all Feishu API operations — messaging, documents, drive, bitable, calendar, wiki, sheets, slides, whiteboard, approvals, mail, and more.

**Architecture (2026.7.10):** Feishu MCP and all third-party CLIs (`@lixiaolin94/feishu-cli`, `lark-cli@0.1.0`, `feishu-cli`) have been removed. Everything goes through official `lark-cli` exclusively.

**Binary:** `/Users/bytedance/.npm-global/bin/lark-cli`
**Package:** `@larksuite/cli` (install: `npm install -g @larksuite/cli`)
**Update:** `npm install -g @larksuite/cli@latest`

## Auth Status

Already authenticated with both user and bot identities:
- **User:** 袁鑫杰 (ou_dc055b0b5b0b5db2b1af5e79c0536db6), full scopes
- **Bot:** ready
- **App:** cli_a964fd626078dcbc

Check: `lark-cli auth status`

## All Domains

```
im          Message and group chat management
docs        Document and content operations
drive       File, comment, permission, and upload management
base        Bitable: table, field, record, view, dashboard, workflow
calendar    Calendar, event, and attendee management
wiki        Wiki space and node management
sheets      Spreadsheet operations
slides      Create and manage presentations
whiteboard  Create and edit boards
task        Task, task list, and subtask management
mail        Email, draft, folder, and contacts management
approval    Approval instance and task management
vc          Video conference and meeting note management
minutes     Minutes content and metadata retrieval
contact     Contacts operations
okr         Lark OKR objectives, key results
```

## Common Commands

### Messaging
```bash
lark-cli im +chat-list --page-size 10          # List chats
lark-cli im +messages-send --chat-id oc_xxx --content "hello"  # Send message
lark-cli im +messages-reply --message-id om_xxx --content "reply"  # Reply
lark-cli im +messages-search --query "keyword"  # Search messages
lark-cli im +chat-messages-list --chat-id oc_xxx  # List messages in chat
```

### Documents / Drive
```bash
lark-cli docs ...     # Document operations
lark-cli drive ...    # File operations
lark-cli wiki ...     # Wiki operations
```

### Bitable
```bash
lark-cli base ...     # All bitable operations
```

### Apps (妙搭)
```bash
lark-cli apps +create ...      # Create app
lark-cli apps +html-publish ... # Publish static HTML
lark-cli apps +access-scope-set ... # Set visibility
```
Full HTML publishing recipe: see `references/miaoda-html-publish.md`
Docx creation from markdown files: see `references/doc-create-markdown.md`

**Design quality**: When building public-facing HTML pages (Skill Hub, landing pages), load `design-taste-frontend` for structure + `popular-web-designs` for visual tokens. Never design ad-hoc — the taste skill's VARIANCE/MOTION/DENSITY dials prevent default AI slop (centered hero, purple gradients, three equal cards).

### Raw API (fallback)
```bash
lark-cli api GET /open-apis/im/v1/chats
lark-cli schema im.v1.chat.list   # Inspect API params
```

## Pitfalls

1. **Only one CLI.** Do NOT install `feishu-cli`, `@lixiaolin94/feishu-cli`, or third-party `lark-cli@0.1.0`. Use ONLY `@larksuite/cli` (binary: `lark-cli`). Third-party `lark-cli@0.1.0` (sxsboat) and `@lixiaolin94/feishu-cli` are abandoned personal projects with limited scope.

2. **No MCP, no direct HTTP API.** All Feishu operations go through `lark-cli`. CLI is the integration path — smoother than MCP, no tool registration overhead, no auth drift.

3. **`im:message.send_as_user` scope is NOT available.** ByteDance has not opened this scope. Do NOT attempt to request it — the authorization page will reject it. When sending messages as user fails, use bot identity or send a link for the user to forward.

4. **Use full binary path in background processes.** `PATH` may differ in background sessions; use `/Users/bytedance/.npm-global/bin/lark-cli`.

5. **`+shortcut` commands preferred over raw API.** The `+`-prefixed commands (`+chat-list`, `+messages-send`, etc.) handle auth, pagination, and enrichment automatically. Use raw `api` commands only as fallback.

6. **Auth tokens auto-refresh.** Unlike MCP which had token expiry issues, `lark-cli` handles refresh tokens automatically. Run `lark-cli auth status` to verify.

    ⚠️ **Cron context caveat**: auto-refresh may not trigger proactively in cron sessions without recent API activity. Before any cron job that depends on `lark-cli`, run `lark-cli auth status` to check token expiry. If the access token expires within 48 hours, flag it in the output. The refresh token typically outlasts the access token by 7 days — if the refresh token is still valid, a single API call (e.g. `lark-cli im +chat-list --page-size 1`) will trigger auto-refresh.

7. **CLI-only architecture.** Do NOT fall back to MCP tools or direct HTTP API calls for Feishu. The `mcp_feishu_*` tools are permanently removed. CLI is the only path.

8. **`+html-publish --path` must be relative.** The path flag rejects absolute paths (`/tmp/myapp`) with `unsafe --path`. Solution: `cd /tmp && lark-cli apps +html-publish --path ./myapp`.

9. **`+access-scope-set` uses `=` for boolean flags.** `--require-login false` fails with `positional arguments are not supported`. Correct: `--require-login=false`.

10. **Apps domain auth: device flow two-step required.** `lark-cli auth login --domain apps` blocks for up to 10 minutes — use `--no-wait --json` to get the code + URL, show QR to user via `lark-cli auth qrcode`, then run `lark-cli auth login --device-code <code>` after user confirmation. Full recipe in `references/miaoda-html-publish.md`.

11. **`docs +create --content @file` requires relative path.** The `@file` syntax rejects absolute paths. Solution: `cd` to the file's directory first, then `--content "@./filename.md"`. Full recipe in `references/doc-create-markdown.md`.

12. **Clean up residual npm packages from old Feishu toolchains.** Migration to `@larksuite/cli` often leaves behind packages like `@m1heng-clawd/feishu`, `openclaw`, `openclaw-team-in-feishu`, `@overlink/openclaw-feishu`, `clawhub`. Run `npm list -g --depth=0` periodically and uninstall anything that isn't `@larksuite/cli` or an unrelated tool. These stale packages don't break functionality but clutter the environment and can confuse agent routing.

13. **`lark-cli update` can time out.** The built-in `lark-cli update` command shells out to npm and may hang (observed 30s+ timeout). Fallback: `npm install -g @larksuite/cli@latest` in the background with `notify_on_complete=true`. Check version: `lark-cli auth status` output includes an `_notice.update` block with current/latest versions.

14. **`auth login` does not accept `--as` flag.** The `--as user/bot` flag is for domain commands (`im`, `docs`, etc.), not for `auth login`. `auth login` authenticates the current machine's lark-cli installation globally; use `--domain all` for full scope re-auth. Use `lark-cli auth login --help` to verify flag support before attempting.

15. **`vc +meeting-join` 的 flag 是 `--meeting-number`（9 位会议号），不是 `--meeting-id`。** 传 `--meeting-id` 直接报 `unknown flag`（CLI 会提示 `did you mean --meeting-number?`）。正确写法：
    ```bash
    lark-cli vc +meeting-join --meeting-number "816630006" --as bot
    ```
    返回 `data.join_user.id` + `data.meeting.id`（长 meeting_id，供 `+meeting-events` 用）+ `meeting_no` + `topic`。注意接口分工：`vc +meeting-list-active` 给的是**长 meeting_id**，而入会要的是 **9 位 meeting_no**。
    只想要「Bot 在场但不说话」时：join 之后只跑字幕轮询，**不要**启动语音管线（main.py）——没有管线就没有 TTS，天然静音。

16. **`im +messages-send --msg-type interactive` 的卡片 JSON 必须用 Python `json.dumps()` 构建，禁止 bash 变量拼接**（bash 里换行会写成字面量、卡片渲染出原始转义符）。多张卡片（会议纪要）用一段 Python 循环发送；`tag: markdown` 的 content **不认 `**粗体**`**（会原样显示星号），在脚本入口做一次 `**x**` → `<font weight=bold>x</font>` 的正则替换，正文就能照常写 Markdown。可复制模板见 `references/interactive-card-batch.md`。
