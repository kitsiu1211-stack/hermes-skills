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
CLI 没封装目标能力时（如批量撤回消息、群内撤回他人消息），先按 `references/openapi-doc-mining.md` 的三级阶梯从官方文档挖规范（`llms.txt` → `llms-<module>.txt` → 单接口 URL 补 `.md`，全部 curl 可达、无需授权），确认权限/限频/路径后再 `lark-cli api` 裸调。有 `+command` 就先用 `+command`，别挖文档。

## Pitfalls

1. **Only one CLI.** Do NOT install `feishu-cli`, `@lixiaolin94/feishu-cli`, or third-party `lark-cli@0.1.0`. Use ONLY `@larksuite/cli` (binary: `lark-cli`). Third-party `lark-cli@0.1.0` (sxsboat) and `@lixiaolin94/feishu-cli` are abandoned personal projects with limited scope.

2. **No MCP, no direct HTTP API.** All Feishu operations go through `lark-cli`. CLI is the integration path — smoother than MCP, no tool registration overhead, no auth drift.

3. **`im:message.send_as_user`（以用户身份发消息）：CLI 侧不拦，授权页能否授予仍未验证（2026-10-28）。** `lark-cli auth login --scope "im:message.send_as_user" --no-wait --json` 会正常吐出 `device_code` + `verification_url`，**CLI 侧不会报错**，说明「发起这个 scope 的授权」本身可行；但历史上实测过授权页拒绝，成功与否**只能在用户完成授权后由 `--device-code` 那一步判定**。因此口径是：**可以发起、不许承诺**。对用户的话固定为「补授权后我就能以你的身份发；页面不给这个权限就走兜底」，兜底＝用户手点/转发，或 bot 身份发（bot 身份在服务台、值班号这类只认用户消息的机器人面前无效，见 pitfall 26）。
    设备码 + 二维码的完整两段式流程（含 `--scope` 变体、`auth qrcode` 用法）见 `references/auth-flow-recipe.md`。

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

17. **`docs +search` 的标题只在「关键词命中标题」时才存在——不能只靠它挑材料。** 返回结构：结果在 `data.results[]`；**`title_highlighted` / `summary_highlighted` 挂在 results 每一项的顶层**（是 `result_meta` 的兄弟键，不是它的子键），`result_meta` 里装的是 `token` / `url` / `owner_name` / `create_time` 等元数据。🚨 **别写 `.result_meta.title_highlighted`**——实测整列返回 `null`（2026-10-15 踩到：查「批量删除消息」时标题栏一片 null，换路径后立刻正常）。看到「标题全是 null」先怀疑取错路径，**不要**据此断定文档不存在或搜索坏了。可用的取法：
```bash
lark-cli docs +search --query "<关键词>" --page-size 5 | python3 -c "
import sys,json
for r in json.load(sys.stdin)['data']['results']:
    print((r.get('title_highlighted') or '').replace('<h>','').replace('</h>',''))
    print('   ',(r.get('summary_highlighted') or '')[:120])
    print('   ',r.get('result_meta',{}).get('url'))"
```
（`<h>`／`<em>` 高亮标签要 strip）。`page_token` 是一大坨可忽略。坑：**关键词只命中正文、没命中标题时，`title_highlighted` 整键缺失**，盲写解析会得到一排「无标题」条目——不要据此断定文档不存在或搜索坏了。正确姿势：先用 `summary_highlighted` 判断内容对味，再 `docs +fetch --doc <url>` 拉原文确认，确认后才写进交付物；**一个查询跑一次就够，最多换一次关键词**，别刷搜索凑标题。

18. **`contact +search-user` 没有 `--keyword` flag**（实测报 `unknown flag "--keyword"`），且需要 `--as user`——先 `lark-cli contact +search-user --help` 核对参数，别照搬别的 `+search` 命令写法。另外：**会议里出现的外部客户姓名查不到是正常的**（对方不在本方通讯录），查不到不要反复试；要识别客户主体就去 C360 `search entity --entity account` 或 grep 本地会议记录。

19. **写含中文的 Python 脚本（发卡片／解析）一律用 `python3.11`。** 实测 `/usr/bin/python3` 跑含中文的脚本报 `SyntaxError: Non-UTF-8 code starting with '\xe4' ... no encoding declared`，换 `python3.11` 直接正常。两个同源小坑：① **Python < 3.12 的 f-string 里不能出现反斜杠**——`f"{'\"ok\": true' in out}"` 会 `SyntaxError: f-string expression part cannot include a backslash`，先把字面量赋给变量再拼接；② 判定发送结果用 `'"ok": true' in out`（或 `json.loads`），别用 f-string 套引号。

20. **跟进日程（calendar）：建前必查重，状态变了用 `+update` 而不是再 `+create`。** 同一件事反复建会攒出一串重复日程（用户会来删）。

```bash
# ① 建前先查（按关键词 + 目标日期窗口）
lark-cli calendar +search-event --as user --query "快造" --start 2026-10-13 --end 2026-10-14
# ② 确实没有 → 建
lark-cli calendar +create --as user --summary "跟进：<主题>" \
  --start 2026-10-13T10:00+08:00 --end 2026-10-13T10:30+08:00 \
  --description "📹 来源会议：… / 📋 待办详情：…（Markdown 可用）"
# ③ 原待办已完成 / 变成下一步 → 改原事件，不要新建第二条
lark-cli calendar +update --as user --event-id "2178220f-…-_0" --summary "…" --description "…"
```

- 时间**必须带时区偏移** `+08:00`；`--summary` 只写主题（不含时间/地点/人名），细节全放 `--description`
- `--event-id` 形如 `<uuid>_0`（末尾是实例序号）；重复日程要带 `--apply-to single|all`
- `+update` 默认 `--notify` 给参会人发通知（只改自己的日程可忽略）
- **身份别搞混**：`calendar` / `vc` / `docs` 这类域命令用 `--as user`；只有 `im +messages-send` 发消息用 `--as bot`。授权过期时 `--as user` 全线失败，先修身份再排业务（见 `hermes-feishu-gateway` skill）。

**建完日程怎么确认（2026-10-16 实测，别再自己吓自己）：**

1. **`+create` 的返回值就是权威凭据**——`{"ok": true, ...}` 即落盘成功。**不要**紧接着用 `+search-event --query "<刚建的标题原文>"` 去验证，很可能是 0 条结果。
2. **`+search-event` 有两个实测特性**：① **索引有延迟**——刚建的事件立刻搜不到，过几分钟或换更宽的关键词才出现；② **返回条数似乎有上限**（`--page-size 30` 仍只回 10 条，同一查询早先回 17 条）。所以「搜不到」≠「没建成」。正确姿势：用**宽关键词**复核（如 `--query "跟进"` + 目标日期窗口，同时 grep 出多条 summary 一起看），或直接用 `+agenda --start <日> --end <日>` 按天点验。
3. **`+agenda` 没有 `--date` 旗标**（传了报 `unknown flag "--date"`）；按天查用 `--start` / `--end`（`--end` 默认取 start 当天结束）。
4. **`calendar +create --description @<file>` 接受绝对路径**（实测 `--description @/tmp/desc1.md` 一次通过）——**与 `docs +create --content @file` 必须相对路径（pitfall 11）相反**，别把两条规则互相套用。待办详情里带 emoji / 换行 / Markdown 时，一律写文件再 `@` 引用，不要内联。

21. **确认「这场会到底是谁的会」——查日历，不要从字幕猜。** 会议标题只写主题（如「飞书 & PLM对接」）时，字幕里出现的公司名很可能是案例引用而非客户。可靠做法是拿当天日程反查：

```bash
lark-cli calendar +search-event --as user --query "<标题关键词>" --start <今天> --end <今天+7>
```

实测命中日程「感臻｜PLM沟通」，与会议「飞书 & PLM对接」同时段（11:00–12:00）→ 直接确认客户主体。**副产品**：这类查询经常一次暴露重复预约（同一时段两条日程），顺手提醒用户清一个，用户会谢你。
铁律仍然成立：**标题和日历都没写客户名就不猜**，如实按标题出交付物。

22. **`vc +meeting-events` 的字幕 `speaker` 可能是会议室设备名，不是人名。** 会议室设备入会时，字幕里的 speaker 会是形如「上海漕河泾中心D座-F17-06🎦(8)」「康泰创新广场-12F-曼谷 Bangkok(10)」的设备名，而真人名字混在正文里（谁在投屏、谁自我介绍、谁被点名）。影响：纪要/分析里会出现「某会场的每个人都有个长名字」的假象，或者把设备名当发言人写出来。
处理：① 不要把设备名当人名写进发言归属；② 按内容推断发言人；③ 交付物末尾统一加一句「会议室设备入会，部分发言归属为设备名，人名归属或有误差」，并口头提示用户。判断信号：speaker 字符串里带楼层/房间/城市编号或结尾 `(N)` 数字。

23. **卡片 JSON 落到文件再 `--content "$(cat f)"`，比内联更省事（pitfall 16 的另一条实现路径）。** `write_file` 写 `/tmp/card1.json` 后：
```bash
lark-cli im +messages-send --chat-id <oc_…> --msg-type interactive --as bot \
  --content "$(cat /tmp/card1.json)" 2>&1 | grep -E '"ok"|message_id'
```
好处：JSON 用 write_file 写的时候自带语法校验（lint 会直接告诉你 JSON 坏了），不用再写一段 Python；多张卡片按序号命名、循环发送即可。发送后**必须**grep 出 `"ok": true` + `message_id` 才算交付成功——命令不报错 ≠ 卡片发出去了。

24. **「批量删除聊天信息」——飞书没有一键全删开关，四条路各管一段，答错就是对客户说错话。** 单条撤回＝`lark-cli im messages delete --message-id om_xxx`（**high-risk-write**：只有用户明确确认后才能加 `--yes`）；批量撤回接口（`DELETE /open-apis/im/v1/batch_messages/:bm-id`）**只能撤「批量发送消息」接口发出的消息**；客户端「多选 → 删除」只删自己视图、**删了不释放企业存储空间**；真正释放容量只有两条路——管理员后台清理 IM 文件、或发送者撤回原始消息。另两条高频约束：机器人撤他人消息必须自身是群主/管理员/创建者（群内消息 ≤1 年），撤回统一受管理员设置的撤回时限限制（超时报 `230009`）。
    完整边界表 + 接口参数 + 错误码 + **对客存储口径**（哪些算容、哪些不算、大文件走云文档链接）见 `references/im-message-recall-and-delete.md`——客户问「能不能批量删 / 删了能不能腾空间」时先读这一页，别凭印象答。

25. **群内「提问」和「派活」一样，必须 @ 目标对象——不 @ 就等于问空气（2026-10-28 用户纠正）。** 用户原话：「这个问题你是对谁说的，每次你都得 at 对应的人或者智能体。」

    不 @ 会同时触发两种失效：① **物理失效**——目标 bot 收不到（飞书只认 `<at user_id="ou_…">` 标签，纯文本 @ 不触发通知）；② **语义失效**——群里的人类和其他 bot 也看不出这句话在问谁，只能等用户来纠。

    最容易犯的形态是**选项式/澄清式提问**：把「❓ A 还是 B？1. … 2. …」这类问题渲染成群消息，但它面向当前用户、**没有 @ 字段** → 一张无主卡片，人和 bot 都不敢接。真要问某个 bot，就别用卡片式提问，直接 `--msg-type text --text '<at user_id="ou_…">名</at> 问题'`；真要问用户本人，就 @ 用户的 open_id 或明写「这条问鑫杰」。

    发出前自检一句：**如果对方只看到正文、没有上下文，他知道是在问他吗？** 不知道 → 补 @ 或改走私聊。发错了就一句认错 + 立刻重发带 @ 的版本，别逐条解释。

    同一群常有**多个 thread 并存**（能力边界对齐在一个 thread，周复盘回执固定在另一个）。跨 thread 被问起时正文必须写明落点（「回执落在 X 话题下，根消息 om_…」），否则对方在自己 thread 里刷不到，会重复催。

    相关的「这句话到底是在回谁 / 哪个群」定位命令、并行 session 撞车的排查，见 `references/chat-evidence-retrieval.md` 第 1.5 节。

26. **交互卡片的按钮，任何 bot / API 都点不了——别答应「我帮你点那个按钮」。** 卡片按钮走的是发卡应用自己的卡片回调，飞书开放平台**没有「代用户触发卡片交互」的接口**（`im` 域也没有上报 action 的写接口）。实测（2026-10-28，飞书交易支持值班号）：另一个 bot 把卡片上同样的菜单文字 `🧾 发票处理` 直接发进会话，值班号**完全没响应、没建工单群**；而用户本人手打同一条文字十余次，每次都立刻建工单群。

    **结论口径：卡片按钮 = 只认真人点击；文字等价物 = 只认用户身份发送。** 想「替用户点按钮」只有三条路：① 用户手点（然后把 bot 拉进它建出来的群/工单群）；② 以用户身份发等价文字（要 `im:message.send_as_user`，见 pitfall 3 的「可以发起、不许承诺」）；③ 在用户本人的飞书客户端里模拟点击（computer_use）——**截图返回 0×0、elements 为空时，通常是窗口最小化或屏幕锁屏，先 `list_windows` 确认，别据此断定驱动坏了**。

    回答这类问题不要只说「做不到」就收尾：给出判定理由 + 上述三条路 + 立刻能执行的那一条（发起授权 / 让用户拉群）。细节与话术见 `references/helpdesk-menu-bot-cards.md`。

27. **解析 lark-cli 的 JSON 输出前，先切到第一个 `{`。** stdout 里可能先冒一行警告（实测 `warning: reactions_partial_failed: 1 message(s) failed ([om_…])`），直接 `json.load(sys.stdin)` 会 `JSONDecodeError: Expecting value: line 1 column 1`——看着像命令挂了，其实数据完好。固定写法：

    ```bash
    lark-cli im +chat-messages-list --chat-id oc_xxx > /tmp/chat.raw 2>&1
    python3 -c "import json;raw=open('/tmp/chat.raw').read();d=json.loads(raw[raw.find('{'):])"
    ```

    两个同源坑：① `+chat-messages-list --page-size` 上限 **50**（传 60 直接 `invalid --page-size 60: must be between 1 and 50`）；② 不传 `--order` 时返回是**新到旧**，要按时间线读就 `reversed(msgs)`。
