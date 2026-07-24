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

7. **CLI-only architecture.** Do NOT fall back to MCP tools or direct HTTP API calls for Feishu. The `mcp_feishu_*` tools are permanently removed. CLI is the only path.

8. **`+html-publish --path` must be relative.** The path flag rejects absolute paths (`/tmp/myapp`) with `unsafe --path`. Solution: `cd /tmp && lark-cli apps +html-publish --path ./myapp`.

9. **`+access-scope-set` uses `=` for boolean flags.** `--require-login false` fails with `positional arguments are not supported`. Correct: `--require-login=false`.

10. **Apps domain auth: device flow two-step required.** `lark-cli auth login --domain apps` blocks for up to 10 minutes — use `--no-wait --json` to get the code + URL, show QR to user via `lark-cli auth qrcode`, then run `lark-cli auth login --device-code <code>` after user confirmation. Full recipe in `references/miaoda-html-publish.md`.

11. **`docs +create --content @file` requires relative path.** The `@file` syntax rejects absolute paths. Solution: `cd` to the file's directory first, then `--content "@./filename.md"`. Full recipe in `references/doc-create-markdown.md`.
