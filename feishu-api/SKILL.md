---
name: feishu-api
description: Feishu/Lark Open Platform API operations — bitable CRUD, docx editing, auth/permission management, and tooling (feishu-cli). Covers the full lifecycle from permission setup through API calls to troubleshooting.
category: devops
---

# Feishu Open Platform API

Unified guide for Feishu/Lark Open Platform API automation. Covers bitable (多维表格), docx documents, and the shared auth/permission/tooling layer.

## Trigger

When the user wants to:
- Read/write Feishu bitable data programmatically
- Read, edit, create, or format Feishu docx/wiki/slides/sheets/markdown documents
- Debug Feishu API permission issues
- Set up Feishu API access (scopes, tokens, auth)
- Create Feishu bots/apps programmatically (QR device-code flow)
- Set up Hermes profiles with independent Feishu bots for multi-agent teams
- Fetch external articles (WeChat, Medium, web) and summarize as Feishu cards → see `references/article-fetching.md`
- **Any Feishu operation — always check lark-cli first, never use browser**

## lark-cli Domain Quick Reference

**23 个域覆盖飞书全量操作。操作飞书前先查这里，不要用 browser。**

| Domain | Key Capabilities |
|--------|-----------------|
| `im` | 发消息（text/markdown/post/**interactive卡片**/file/image/video/audio）、群管理、消息搜索/回复 |
| `docs` | 读文档（`+fetch --doc-format markdown`）、创建、历史版本、图片操作 |
| `wiki` | 空间/节点管理、移动、复制、`+node-get` 取 obj_token |
| `base` | 多维表格：表/字段/记录/视图/仪表盘/form/workflow/权限 |
| `sheets` | 电子表格：单元格读写/样式/搜索替换/合并 |
| `slides` | 演示文稿：创建/截图/替换页面 |
| `markdown` | 原生 Markdown：增删改查/patch/diff |
| `drive` | 云盘：文件增删改、上传下载导出导入、权限/评论 |
| `calendar` | 日程、忙闲、会议室查找/预订、智能时段推荐 |
| `vc` | 视频会议：活跃列表、入离会、**会议事件(字幕/弹幕)**、会中消息 |
| `task` | 任务增删改、分配、评论、提醒 |
| `approval` | 审批实例/任务：搜索/创建/审批/驳回/转交 |
| `okr` | OKR 周期/目标/关键结果/进度 |
| `attendance` | 考勤记录查询 |
| `contact` | 用户信息查询/搜索 |
| `mail` | 邮件草稿/发送/转发/回执 |
| `minutes` | 妙记详情/摘要/待办/字幕/转写 |
| `note` | 会议笔记详情 + 转写 |
| `mindnotes` | 思维笔记节点 |
| `whiteboard` | 白板查询/更新 |
| `apps` | 妙搭应用：创建/部署/发布/自动化触发器 |
| `event` | 实时事件流消费 |
| `api` | 裸 HTTP 逃生舱 |
| `schema` | 查看 API 参数/权限 |
| `skills` | 读 CLI 内置领域指南 |

**🚨 铁律：飞书文档/网页一律用 lark-cli，禁止 browser。**
- 读文档：`lark-cli docs +fetch --doc <url或token> --doc-format markdown`
- 读 wiki：先用 `wiki +node-get --node-token <url> --jq '.data.obj_token'` 取 token，再用 docs +fetch
- 会议事件：`lark-cli vc +meeting-events --as user --meeting-id <id> --page-all`

## Auth & Permissions (Shared)

### Tooling

**CLI 唯一入口。** `@larksuite/cli`（二进制 `lark-cli`, v1.0.68+, 字节跳动官方维护）覆盖全部飞书 API。**所有飞书操作统一走 CLI**——不使用 MCP 工具、不使用浏览器、不使用直接 HTTP 调用。唯一例外：文件上传（multipart form-data）需要原始 HTTP。

**安装/更新：**
```bash
npm install -g @larksuite/cli@latest   # 官方 CLI
```

**⚠️ 已废弃的工具（请勿使用）：**
- `@lixiaolin94/feishu-cli`（第三方，已删除）
- `lark-cli@0.1.0`（sxsboat 第三方，已删除）
- `feishu-cli` npm 包（提供 `feishu` 二进制，仅扫码登录，已删除）

**MCP 迁移到 CLI：** Feishu MCP 已通过 `hermes mcp remove feishu` 彻底移除。

| Tool | Purpose | Config |
|------|---------|--------|
| `lark-cli` | 全部飞书 API 操作（消息、文档、多维表格、日历、任务、白板等） | `~/.lark-cli/config.yaml` (app `cli_a964fd626078dcbc`) |

**lark-cli key commands:**
```bash
lark-cli auth status                              # check auth
lark-cli im +messages-send --chat-id oc_xxx --text "..."  # send message
lark-cli im +chat-list --page-size 10             # list chats
lark-cli im +messages-send --help                 # inspect all send options
lark-cli schema im.messages.create                # inspect API params (raw API)
lark-cli api GET /open-apis/im/v1/chats           # raw API fallback
lark-cli <domain> --help                          # browse commands per domain
```

**Domain conventions:** Prefer `+shortcut` commands over raw API. Each domain (`im`, `base`, `docs`, `drive`, `mail`, etc.) has its own set of typed commands. Use `lark-cli <domain> --help` to explore. Use `lark-cli api GET|POST <path>` as raw escape hatch only when no shortcut/typed command covers the operation.

**Note: `@larksuite/cli` v1.0.68 does NOT have an `exec` subcommand.** Any code examples referencing `lark-cli exec ...` or `feishu-cli exec ...` are from the deprecated third-party CLI and will fail. Use `+shortcuts` instead.

### lark-cli Auth Login (UAT)

```bash
lark-cli auth login --recommend              # 设备码授权（推荐）
lark-cli auth login --scope "scope1 scope2"  # 指定 scope
lark-cli auth status                         # 检查授权状态
```

**已授权状态（2026.7.10）：** 用户身份（袁鑫杰）+ Bot 身份均已就绪，无需重新授权。

**移动端授权（正确方案）：** 用户不在电脑旁时，用两步非交互式流程：

```bash
# Step 1: 获取授权 URL + state
feishu-cli auth login --print-url
# → {"auth_url": "https://accounts.feishu.cn/...", "state": "abc123"}

# Step 2: 用户手机打开 auth_url 授权，浏览器跳转到 127.0.0.1:9768/callback?code=xxx&state=yyy（失败页面）
#         用户复制地址栏完整 URL 发回来

# Step 3: 用回调 URL 换 token（无需启动本地服务器！）
feishu-cli auth callback "<回调URL>" --state "<state_from_step_1>"
```

**⚠️ 不要用 `--manual` 模式做非交互授权。** `--manual` 期望 stdin 交互输入，在 background/PTY 下直接退出。`auth callback` 是唯一的非交互路径——把回调 URL 作为 CLI 参数传入，无需服务器、无需阻塞。

---

## File Upload & Send (IM)

When sending files to Feishu users (e.g., .tar.gz, .zip, .pdf), the Feishu IM API requires a two-step flow:

### Step 1: Upload file to get `file_key`

```python
import urllib.request, json

# Get tenant access token
token = get_tenant_token()

# Multipart upload
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
with open(file_path, 'rb') as f:
    file_data = f.read()

body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file_type"\r\n\r\n'
    f'stream\r\n'
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file_name"\r\n\r\n'
    f'{os.path.basename(file_path)}\r\n'
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(file_path)}"\r\n'
    f'Content-Type: application/octet-stream\r\n\r\n'
).encode() + file_data + f'\r\n--{boundary}--\r\n'.encode()

req = urllib.request.Request(
    'https://open.larkoffice.com/open-apis/im/v1/files',
    data=body,
    headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Authorization': f'Bearer {token}'
    }
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
    file_key = result['data']['file_key']
```

### Step 2: Send as file message

```bash
lark-cli api im.v1.message.create --params '{
  "params": {"receive_id_type": "chat_id"},
  "data": {
    "receive_id": "<chat_id>",
    "msg_type": "file",
    "content": "{\"file_key\": \"<file_key>\"}"
  }
}'
```

**Note**: File upload (multipart form-data) is the one case where CLI can't help — must use raw HTTP. Everything else goes through `lark-cli api`.

---

## Message Sending

All message types through `lark-cli im +messages-send`. The shortcut command handles JSON wrapping, content-type inference, and scoping better than raw API calls.

### Available flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--text "..."` | Plain text (auto-wraps as JSON) | `--text "Hello"` |
| `--markdown '...'` | Markdown → post format (auto-wraps; images auto-resolved) | `--markdown '**Bold** text'` |
| `--content '...' --msg-type interactive` | Interactive card JSON | See below |
| `--chat-id oc_xxx` | Send to a group chat | Use this for group delivery |
| `--user-id ou_xxx` | Send to a user's Home channel | Use `--as bot` for bot delivery |
| `--as bot` / `--as user` | Identity for sending | Bot needs `im:message`; user needs `im:message.send_as_user` |

### Text Message

```bash
# Bot sends text to a group
lark-cli im +messages-send --as bot --chat-id oc_xxx --text "Hello everyone"

# Bot sends text to a user's Home channel
lark-cli im +messages-send --as bot --user-id ou_xxx --text "Hello"
```

### Markdown Message (preferred for structured content)

```bash
# Bot sends rich markdown to user's Home channel
lark-cli im +messages-send --as bot --user-id ou_xxx --markdown '**🔮 标题**

**段落一：** 内容

---

**段落二：** 更多内容
'
```

The CLI auto-wraps markdown as a `post` message type. This is the simplest path for rich formatted messages. Supports:
- `**bold**` `*italic*` `~~strikethrough~~`
- `[links](url)` 
- Lists, tables, code blocks
- Image URLs auto-displayed

### Interactive Card

```bash
# Build the card JSON in a file or inline, then send
lark-cli im +messages-send --as bot --user-id ou_xxx \
  --content '{"config":{"wide_screen_mode":true},"header":{"title":{"tag":"plain_text","content":"标题"},"template":"indigo"},"elements":[{"tag":"div","text":{"tag":"lark_md","content":"**内容**"}}]}' \
  --msg-type interactive
```

**Card JSON structure:**

```python
card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": "标题"},
        "template": "blue"  # blue|turquoise|green|yellow|red|purple|indigo|gray|default
    },
    "elements": [
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": "**内容**"}},
        {"tag": "note", "elements": [{"tag": "plain_text", "content": "来源"}]}
    ]
}
```

**⚠️ Reliable pattern: write card JSON to temp file first, then use `--content`.** For complex cards, build the JSON in a `write_file` call to a temp file, then pipe it:

```bash
lark-cli im +messages-send --as bot --user-id ou_xxx \
  --content "$(cat /tmp/card.json)" \
  --msg-type interactive
```

The `--content` value with `--msg-type interactive` must be the **full card JSON as a single string** (not nested inside a `content` wrapper — the CLI handles wrapping).

**Markdown shortcut (preferred for most use cases):** Instead of building an interactive card, use `--markdown` for rich formatting. It produces a `post`-type message (not an interactive card), but carries bold/italics/links/code blocks/headers/tables/horizontal rules. Only fall back to `--msg-type interactive` when you need buttons, header theming (`template` colors), or `note` footers.

**Card rules (phone-first):** Header concise, info segmented with bold/dividers/indentation. Split into multiple cards if too long (max ~30KB). Prefer 1 card, at most 2. No cloud doc fallback.

### File Message

```bash
lark-cli im +messages-send --as bot --chat-id <chat_id> \
  --file <file_key> \
  --msg-type file
```

File upload (multipart) requires raw HTTP — see File Upload & Send section above.

### Thread Reply

When `HERMES_SESSION_THREAD_ID` env var exists, use reply API via `+messages-reply`:

```bash
lark-cli im +messages-reply \
  --as bot \
  --message-id <root_message_id> \
  --content '{"elements":[...]}' \
  --msg-type interactive
```

Or for markdown reply:

```bash
lark-cli im +messages-reply \
  --as bot \
  --message-id <root_message_id> \
  --markdown 'Reply content'
```

**⚠️ Pitfall**: Reply API needs `message_id` (om_ prefix), NOT `thread_id` (omt_ prefix). Use `lark-cli im +chat-messages-list --chat-id <chat_id>` to find the root message and extract its `message_id`.

### Monitoring Threads for Bot Responses

When you @mention another bot in a group chat, its response often arrives as a **Thread reply** under your message — NOT as a new message in the main chat timeline. Always check both the main chat AND the Thread when waiting for a bot response.

**Your sent message carries a `thread_id` field** (omt_ prefix) — poll it directly using `+threads-messages-list`:

```bash
# List messages in a thread by om_ message ID or omt_ thread ID
lark-cli im +threads-messages-list --as bot \
  --thread-id <om_xxx_or_omt_xxx> \
  --page-size 20
```

The Thread will contain your original message plus any replies. Filter by `sender.id` to find the target bot's response.

---

## Skill Hub (妙搭)

**两个 Skill Hub，更新方式不同：**

| App ID | 名称 | 更新方式 |
|--------|------|---------|
| `app_179xr3ds4q0` | Hermes Agent Skill Hub | ✅ 可程序化更新 |
| `app_4k5x4btce2wuf` | Business Skill Hub | ❌ 仅手动（需浏览器妙搭后台） |

### Hermes Agent Skill Hub (`app_179xr3ds4q0`) — 更新流程

**⚠️ 不要走浏览器妙搭后台（magic.solutionsuite.cn 需要飞书 SSO 登录，agent 无法通过）。直接用 CLI 发布。**

```bash
# 1. 编辑源文件
#    /tmp/skillhub/index.html
#    技能数据在 categories[] 数组里，每个 skill: { cn, code, icon, desc, exUser, exAgent }
#    记得更新：分类计数、hero dot 总数、copyAll toast 文案

# 2. 发布
cd /tmp && lark-cli apps +html-publish --app-id app_179xr3ds4q0 --path ./skillhub --as user --json
# → {"ok": true, "data": {"url": "https://bytedance.aiforce.cloud/app/app_179xr3ds4q0"}}
```

**更新 Skill Hub 时别忘了同步更新 GitHub README 和 count。**

完整参考：`references/skill-hub-api.md`

**Feishu operations**: 统一使用 `lark-cli api` 调用飞书 API。不再使用 MCP 工具。

### Permission Scopes

All Feishu API operations require explicit permission scopes granted in the app console. The critical gotcha: **after granting scopes in the console, you MUST click 「发布」 (Publish/Create Version)** — unchecked scopes only live in draft until published. This is the #1 cause of "I added the permission but it still doesn't work."

For a complete permission scope reference and authorization URL builder, see `references/permission-scopes.md`.

### Token Types

| Token | How to Get | Used For |
|-------|-----------|----------|
| **TAT** (tenant_access_token) | Auto-generated from app_id/app_secret in `~/.feishu-cli/config.yaml` | Reading documents, writing blocks, converting markdown, bitable CRUD |
| **UAT** (user_access_token) | `feishu-cli auth login` (opens browser for OAuth) | `builtin import`, `builtin search` |

UAT must be explicitly authorized — run `feishu-cli auth login` on the desktop. The callback goes to `http://127.0.0.1:9768/callback`, so the user must be at their machine.

### Common Pitfalls (All Feishu APIs)

| Issue | Fix |
|-------|-----|
| `lark-cli api` 返回 99992402 `field validation failed` | 参数结构错误。`exec` 需要 `{"params": {query参数}, "data": {body}, "path": {路径参数}}`。用 `--dry-run` 验证 |
| `feishu_doc_read` 返回 error | 该工具仅在飞书评论线程上下文生效。用 `lark-cli api docx.v1.document.rawContent` 替代 |
| Permission 99991672 | Missing scope. Grant in app console → 权限管理 → 应用身份权限 → add scope → **发布** |
| `open_id cross app` (99992361) | Each Feishu app assigns a **different open_id** to the same user. When app A creates a group and tries to add user X, it must use user X's open_id **as seen by app A** — the open_id from app B's namespace will fail with code 99992361. Fix: use `contact/v3/users/batch_get_id` with the creating app's token to look up the user by email/phone, getting the correct open_id for that app. |
| `feishu-cli auth login` 报「重定向URL有误」(错误码 20029) | 已废弃。现在统一使用 `lark-cli auth login --recommend`（设备码授权），无需配置回调 URL。 |
| `lark-cli` UAT 过期 | 使用 `lark-cli auth login --recommend` 重新授权（设备码流程，无需回调 URL） |
| `lark-cli` UAT 过期 | 使用 `lark-cli auth login --recommend` 重新授权（设备码流程，无需回调 URL） |
| Wiki access denied despite permissions | Known Feishu issue — wiki permissions may not propagate for tenant tokens. **Workaround (no extra scopes needed):** `feishu-cli docx document rawContent --document-id <wiki_token>` — wiki nodes expose content through the docx endpoint even when wiki API permissions are missing. |
| Wiki 评论无法直接用 wiki token 读取（`drive.v1.fileComment.list` 返回 `1069307: not exist`） | Wiki token（如 `RTMrwsWKKiTTsMk5KgscpaYznQy`）不是真正的文档 token。两步解决：(1) `wiki.v2.space.getNode` 获取 `obj_token` 和 `obj_type`；(2) 用 `obj_token` + `file_type=<obj_type>` 调 `drive.v1.fileComment.list`。详见下方「Wiki 文档评论读取」。 |
| Bot 发消息 230013 `Bot has NO availability` | 目标用户不在 bot 的「可用范围」内 | (1) 开放平台加用户入可用范围并发布；(2) 改用 `im:message.send_as_user` scope + `--as user` 以用户身份发送 |
| `lark-cli drive +download --output` 绝对路径报错 | CLI 安全限制，`--output` 只接受相对路径 | 先 `cd /tmp` 再 `--output ./file.pdf` |
| `lark-cli im +messages-send --as user` 缺 scope | 用户身份发消息需要 `im:message.send_as_user`（与 bot 用的 `im:message` 不同） | `lark-cli auth login --scope "im:message.send_as_user"` |
| `im/v1/images/{key}` 返回 234008 `The app is not the resource sender` | 飞书限制：只有发图的 App 才能下载自己发的图片。收到其他 bot 发的图片时，API 无法下载——图片内容只能由用户在客户端查看。 |
| `im/v1/images/{key}` 返回 234001 `Invalid request param` | 消息中的图片/文件**不能通过 images 端点下载**。正确方式：使用消息资源端点 `GET /open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=image`。步骤：(1) 先通过 message list 获取 message_id 和 image_key；(2) 再调用资源端点下载文件内容。详见 `references/image-download.md`。 |
| Bot @mention 后没在群里看到回复 | 很多 bot 会在你的消息下创建 **Thread（话题）** 回复，而不是在主聊天时间线发送。去原始消息的 `thread_id` 里查（`container_id_type: "thread"`），不要只轮询主聊天。 |
| `--content` for doc create is raw string | Pass markdown text directly: `--content "## Title"`, NOT JSON. |
| `execute_code` 卡片发送报 SyntaxError (smart quotes) | `execute_code` sandbox 对中文引号（`""` `''`）解析严格。卡片内容字符串中移除所有中文引号，改用纯文本表达。必须保留时用 `\u201c` / `\u201d` Unicode 转义。 |

---

## App Creation & Registration (QR Device-Code Flow)

Create Feishu enterprise internal apps (bots) programmatically — used for Hermes profile multi-agent setups where each profile needs its own Feishu bot.

**Full API reference:** `references/qr-app-registration.md`

### Quick Start (Single Bot)

```python
import json, urllib.request, time
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

ACCOUNTS_URL = "https://accounts.feishu.cn"
REG_PATH = "/oauth/v1/app/registration"

def post_reg(body):
    url = f"{ACCOUNTS_URL}{REG_PATH}"
    data = urlencode(body).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        return json.loads(exc.read())

# 1. Start registration → present QR URL to user
res = post_reg({"action": "begin", "archetype": "PersonalAgent", "auth_method": "client_secret", "request_user_info": "open_id"})
print(f"QR: {res['verification_uri_complete']}&from=hermes&tp=hermes")

# 2. Wait for user to scan, then poll
cred = None
deadline = time.monotonic() + 120
while time.monotonic() < deadline and not cred:
    res = post_reg({"action": "poll", "device_code": res["device_code"]})
    if "app_id" in res:
        cred = {"app_id": res["app_id"], "app_secret": res["app_secret"]}
    elif res.get("error") == "access_denied":
        break
    time.sleep(5)

# 3. Write to Hermes profile .env
# Replace FEISHU_APP_ID and FEISHU_APP_SECRET lines
```

### Multi-Bot Bulk Creation

When creating multiple bots (e.g., for pm, marketing, designer, data profiles):

1. Run all `begin` calls first to get fresh device codes
2. Present all QR links to the user at once
3. Poll all device codes **in parallel** (round-robin, one loop) — NOT sequentially
4. Write credentials to each profile's .env as they come in

Sequential polling is the #1 cause of timeout failures — by the time the Nth bot is polled, its device code has likely expired.

### No "List Apps" API

There is **no public Feishu API** to list all apps under a tenant. Save `app_id` + `app_secret` immediately after registration — they cannot be retrieved later via API. The only fallback is the Open Platform console at https://open.feishu.cn/app (requires browser login).

---

## Group Chat Operations

Creating and managing Feishu group chats with multiple bots. Full recipe with code in `references/group-chat-operations.md`.

### Permission Scopes Required

| Operation | Required Scopes |
|-----------|----------------|
| Create a group chat | `im:chat` or `im:chat:create` |
| Add members to a group | `im:chat` or `im:chat.members:write_only` |
| Look up user by email/phone | `contact:user.id:readonly` |

⚠️ After granting scopes, **publish a new version** of the app for them to take effect.

### Creating a Group with Multiple Bots

```python
# POST /open-apis/im/v1/chats?user_id_type=open_id
payload = {
    "name": "Group Name",
    "chat_type": "private",
    "bot_id_list": ["cli_xxx", "cli_yyy"],  # app_ids, NOT open_ids
    "user_id_list": []  # optional; see cross-app pitfall below
}
```

**⚠️ `bot_id_list` is UNRELIABLE.** In multiple tests (2026-06-17), `chat.create` succeeded but the member list was **empty** — bots listed in `bot_id_list` were NOT actually added. Always verify with a `GET /chats/{chat_id}/members` call after creation. When `bot_id_list` fails to add bots, the fallback approaches are listed below in "Workarounds when bot_id_list fails".

**Key points:**
- `bot_id_list` takes **app_ids** (cli_ prefix), NOT bot open_ids — but don't rely on it
- `membership_approval: "no_approval_required"` lets members add others freely

### Adding Members (Cross-App open_id Pitfall)

The #1 gotcha when adding users to a group: each Feishu app assigns a **different open_id** to the same user. When app A creates a group and tries to add user X, it must use X's open_id **as seen by app A**.

```python
# ❌ WRONG: using open_id from app B's namespace with app A's token
add_members(token_from_app_A, user_open_ids=["ou_xxx_from_app_B"])  # → 99992361

# ✅ CORRECT: look up user by email using the creating app's token
url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id"
data = json.dumps({"emails": ["user@example.com"]}).encode()
# ... gets the correct open_id for this specific app
```

When you can't look up (missing `contact:user.id:readonly` scope), fallback: create the group with bots only, set `membership_approval: "no_approval_required"`, and have the user join manually.

### Workarounds When `bot_id_list` Fails

When bots aren't added during group creation, you have these options:

1. **meJoin (public groups only)** — Each bot calls `PATCH /im/v1/chats/{chat_id}/members/me_join`. **Only works for public groups** (`chat_type: "public"`); returns `232008: chat is not public` for private groups. Requires `im:chat.members:write_only` scope.

2. **Add members by open_id** — The group-creating bot adds each bot by open_id via `POST /im/v1/chats/{chat_id}/members`. Requires the bot's open_id **as seen by the creating app**. Since bots **cannot look up other bots** via `contact/v3/users/batch_get_id` (contact API only returns users within the app's contacts scope, and bots are excluded), this only works when you already know the correct cross-app open_ids.

3. **Manual group creation** — When API routes are exhausted, create the group in the Feishu client UI and add bots by searching their display names. This is the most reliable path for private multi-bot groups when bots lack permission scopes.

### Joining Existing Groups (API Limitation)

**There is no Feishu Open API endpoint for a bot to join an existing group chat.** Once a group exists without your bot, you cannot programmatically join it. The only ways in are:

1. **Interactive card button** — send a card with a join button. If the button doesn't work, search the group name in the Feishu client.
2. **Manual addition** — an existing member adds the bot via the Feishu client UI.

**Do not waste time trying `chatMembers.get`, `message_list`, or any other API** — they all return `230002: Bot/User can NOT be out of the chat`.

### Error Codes (Group Chat Operations)

| Error Code | Meaning | Fix |
|-----------|---------|-----|
| 99992361 `open_id cross app` | open_id from different app's namespace | Use `batch_get_id` with the correct app's token |
| 99991672 `Access denied` | Missing scope | Grant scope in developer console → **Publish new version** |
| 232008 `chat is not public` | `meJoin` only works for public groups | Set `chat_type: "public"` or add via `chatMembers.create` |
| 230002 `Bot/User can NOT be out of the chat` | Bot not a member | No API to join; use manual methods |
| 99992351 `id not exist` | Wrong ID type (e.g., app_id used as open_id) | Use correct open_id for the target app |

---

## Bitable CRUD Operations

### Approach: Unified via `base` domain

使用 `lark-cli` 的 `base` domain 命令操作多维表格。不再使用 MCP 工具或直接 HTTP 请求。

```bash
# 列出所有表
lark-cli base table list --app-token <app_token>

# 列出字段
lark-cli base field list --app-token <app_token> --table-id <table_id>

# 搜索记录（支持分页和过滤）
lark-cli base record search --app-token <app_token> --table-id <table_id> \
  --field-names '["字段1", "字段2"]' --page-size 500

# 创建记录
lark-cli base record create --app-token <app_token> --table-id <table_id> \
  --fields '{"字段名": "值"}'

# 更新记录
lark-cli base record update --app-token <app_token> --table-id <table_id> \
  --record-id <record_id> \
  --fields '{"字段名": "新值"}'
```

需要快速交互或 domain 没覆盖到的场景，可用 raw API 通道：
```bash
lark-cli api GET /open-apis/bitable/v1/apps/<app_token>/tables
```

### Bitable Pitfalls

1. **Field types vary**: URL fields return as `{"link": "...", "text": "..."}` dicts, not plain strings. Single-select fields return plain strings. Check structure before use.
2. **Pagination**: `page_size` max is 500. Most `base` commands support `--page-all` for auto-pagination.

---

## Docx Documents

For reading, editing, creating, and formatting Feishu docx documents via `lark-cli docs` commands.

### Reading a Document

```bash
lark-cli docs +fetch --doc <doc_id> --as user --json
```

Returns `data.document.content` as docx XML. For quick content inspection, pipe through `jq` or Python. The CLI may also offer format options — check `lark-cli docs +fetch --help`.

### Reading Wiki Document Comments

Wiki 文档的评论不能直接用 wiki node token（如 URL 中的 `RTMrwsWKKiTTsMk5KgscpaYznQy`）调用 `drive.v1.fileComment.list`——会返回 `1069307: not exist`。需要两步解析：

**Step 1: 解析 wiki node 获取实际文档 token**

```bash
lark-cli api wiki.v2.space.getNode --params '{"params": {"token": "<wiki_token>"}}'
```

从返回中取 `data.node.obj_token`（真正的文档 token）和 `data.node.obj_type`（如 `docx`）。

**Step 2: 用实际文档 token 读取评论**

```bash
lark-cli api drive.v1.fileComment.list --params '{
  "path": {"file_token": "<obj_token>"},
  "params": {"file_type": "<obj_type>", "page_size": 50}
}'
```

返回的 `items` 包含每条评论及其 `reply_list.replies`（回复线程）。`quote` 字段是被评论引用的文档原文。`is_whole` 区分全文评论 vs 局部评论。

**⚠️** `page_token` 在翻到尾页时不会消失——始终返回最后一页的 token。判断是否翻完应看返回条数是否 < `page_size`，而不是依赖 `has_more` 字段（不可靠）。

### Creating a New Document (from Markdown)

The simplest path: create a doc with markdown content in one call. The CLI converts markdown to docx blocks internally.

```bash
lark-cli docs +create \
  --title "Document Title" \
  --doc-format markdown \
  --content "@./relative/path/to/file.md" \
  --as user \
  --json
```

Key flags:
- `--doc-format markdown` — treat `--content` as markdown (default is `xml`)
- `--content` — supports `@file` syntax to read from a file, OR `-` to read from stdin, OR inline string
- **`@file` requires a relative path within the current directory** — `cd` to the file's directory first, or use `./path`
- Absolute paths are rejected with `--file must be a relative path within the current directory`
- `--as user` — create as user identity (needs UAT); `--as bot` also supported
- Returns `data.document.document_id` and `data.document.url`

**Inline markdown (short content):**
```bash
lark-cli docs +create --title "Title" --doc-format markdown --content "## Heading\n\nBody" --as user --json
```

### Updating a Document

```bash
lark-cli docs +update \
  --doc <doc_id_or_url> \
  --command append \
  --doc-format markdown \
  --content "## New Section\n\nContent..." \
  --as user \
  --json
```

Available commands: `append`, `overwrite`, `str_replace` (with `--pattern`), `block_insert_after`, `block_delete`. Check `lark-cli docs +update --help` for all options.

### Bulk Document Fix

When a docx has multiple structural issues, export → fix → re-create:

1. **Export**: `lark-cli docs +fetch --doc <id> --as user --json` → extract `data.document.content`
2. **Fix**: Python script to repair structure
3. **Re-create**: `lark-cli docs +create --title "Title" --doc-format markdown --content "@./fixed.md" --as user --json`

See `references/bulk-fix-patterns.md` for concrete fix recipes.

### Docx Pitfalls

| Issue | Fix |
|-------|-----|
| `docs +create --content @file` 报 `invalid file path` | `@file` 必须是当前目录下的**相对路径**。先 `cd` 到文件所在目录，或用 `./filename`。不接受绝对路径。 |
| Markdown import 不支持表格 | `+create --doc-format markdown` 自动转换表格为 docx table blocks——已验证可行。 |
| 文档 URL 格式 | `https://bytedance.larkoffice.com/docx/<doc_id>` — 用于 `+update --doc` 或 `+fetch --doc` |

---

## References

- `references/card-send-template.py` — Minimal working Python template for sending interactive cards via feishu-cli (copy into execute_code)
- `references/image-download.md` — 飞书消息中图片/文件下载：正确端点（messages/{id}/resources/{key}）、完整 curl 配方、与 images 端点的区别
- `references/bulk-fix-patterns.md` — Concrete Python fix recipes for docx repair sessions
- `references/qr-app-registration.md` — Feishu QR device-code app registration API: flow, pitfalls, parallel polling, and .env wiring
- `references/skill-hub-api.md` — Two 妙搭 Skill Hubs (Business + Hermes Agent): app IDs, `lark-cli apps +html-publish` publishing, source file location, API endpoints
- `references/article-fetching.md` — WeChat/外部文章抓取：browser_console + #js_content，Medium jina.ai 代理，通用网站 snapshot/console
- `references/article-analysis-pipeline.md` — 公众号文章分析完整流水线：抓取 → ljg-rank + ljg-learn → Hermes Context → 飞书卡片
- `references/manual-block-construction.md` — 手动构建 docx block 的 Python 模板：当 convert 输出不可控或包含表格时的可靠替代方案
