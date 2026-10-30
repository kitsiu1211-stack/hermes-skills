---
name: feishu-bot-media-delivery
description: Feishu bot delivery — @ mention, thread targeting, verify delivery.
version: 1.0.0
author: hermes-curator
license: MIT
category: feishu
metadata:
  tags: [feishu, bot, media, lark-cli, github, kimicode]
  related_skills: [agent-group-collab, feishu-group-chat]
---

# 飞书群 Bot 媒体投递与远程交付验收

## When to Use

给 Agent协作群里的 bot（Kimi Code、小管家等）发图片/文件（如让 Kimi Code 替换页面照片）；或远程 agent（Kimi Code 等独立沙箱环境）交付文件、需要从 GitHub 拉取验收时。

**也用于任何「飞书消息到底送达没有」的场景**：@ 了对方没反应、怀疑 @ 没生效、长答复要发进话题（thread）、同一群里有多条 thread 需要对齐、要证明自己发出的消息确实被对面 bot 收到。

## 一、媒体消息必须带 @（2026-08-18 实证）

**核心事实**：bot 的群消息接收模式是「仅接收 @ 消息」。纯媒体消息（`--image ./x.jpg` 或 `--file`）**不触发任何 bot**——事件流里根本没有未 @ 的媒体消息，bot 也常因权限策略无法用 API 反拉群消息列表（230027）。发图给 bot 正确姿势：

```bash
# 1. 上传图片拿 image_key（必须 --as bot；user 身份缺 im:resource scope 报 missing_scope）
lark-cli im images create --as bot --data '{"image_type":"message"}' --file "./照片.jpg"
# → {"image_key":"img_v3_xxx"}

# 2. 用 --markdown 发：@ + 说明 + ![alt](img_key) 内嵌图片（每条图一条消息，@ 一次）
lark-cli im +messages-send --as bot --chat-id oc_xxx --markdown \
  $'<at user_id="ou_xxx">Bot</at> 图1 说明\n\n![说明](img_v3_xxx)'
```

- 图片+文字同一条消息发，bot 收到事件后可按 message_id 下载图片继续处理
- `--markdown` 的 `![alt](img_key)` 只认已上传的 image_key，不认本地路径（`![x](./a.png)` 不会自动上传）
- 文件同理：先拿 file_key 再内嵌，或让 bot 从 GitHub 拉取

## 一·b、@ 到底有没有送达：mentions 核验 + thread 归属（2026-10-28 实证）

`ok: true`、消息出现在群里，都**不等于对方收得到**。三件事分开核。

**1. @ 标签有没有解析**

- 内联 `<at user_id="ou_xxx">名字</at>` 在 `--text` 和 `--markdown`（post）里都有效（CLI 会规范化成真 mention）；只有 interactive 卡片要换卡片原生 `<at id=ou_xxx></at>`。文档：`lark-cli skills read lark-im/references/lark-im-messages-reply.md` 的「@Mention Format」。
- **引号必须半角**。写成全角 `“ou_xxx”` 时飞书不解析，`<at>` 整段变成可见纯文本，而**消息照样发送成功、零报错**——只有对方收不到。2026-10-28 踩过，用户在群里当场指出「你这个艾特好像有问题」。
- 发完核（不要只看 `ok: true`）：

```bash
lark-cli im +messages-mget --message-ids <om_id> --as bot \
  --jq '.data.messages[0] | {mentions:[.mentions[]? | {id,name}], thread:.thread_id}'
```

- `mentions[]` 只证明标签解析正确，**不证明对方是这个群的成员**：飞书接受任何合法 open_id。**外部租户 bot 不出现在 `+chat-members-list --member-types bot` 的返回里**（2026-10-28：返回 12 个 bot，对手方不在其中），只能从消息历史里的 `sender.id` 认它。

**2. 消息落在哪个 thread**

同一个群里会同时存在多条 thread。`+messages-reply --message-id <om> --reply-in-thread` 把消息放进**那条 om 所属的 thread**，与你当前会话所在 thread 无关：

- 给对面 bot 的答复要 reply 到**它自己发的那条消息**上；reply 到别人的消息就落到另一条 thread，它看不见。
- 主站流 `+chat-messages-list` **看不到话题回复**，要用 `+threads-messages-list --thread-id omt_xxx`（也接受 `om_` ID，自动解析到所属 thread）。在 chat-messages-list 里翻不到 ≠ 没发出去。
- chat_id 用 `+chat-search --query "群名" --as bot` 拿（`im chat list` 有时返回空）。

**3. 跨 thread 就把结论就地重发一版**

别指望对方能看到另一条 thread 里的长回复。在对方所在 thread 再发一版**能独立读懂**的确认消息——多一条重复，好过对面完全没收到。重发旧答复带 `--idempotency-key`，正文首行写明「上一条漏了艾特，带上重发」。

## 二、远程 Agent 交付验收：GitHub 中转（gh api）

Kimi Code 在独立环境跑，编译产物/源码不在本机磁盘。让它 push 到 GitHub 后，用 gh CLI 验收（不要搜本地文件）：

```bash
# raw.githubusercontent.com 会 429 Too Many Requests（GitHub 限爬虫）——用 gh api 代替
gh api repos/<owner>/<repo>/contents/index.html --jq '.content' | base64 -d > /tmp/check.html

# 验收清单
gh api repos/<owner>/<repo>/commits --jq '.[0].commit.committer.date + " | " + .[0].commit.message'  # 最新 commit 时间/信息
gh api repos/<owner>/<repo>/contents/images --jq '.[].name'                                       # 资源文件是否在
grep -o 'src="[^"]*"' /tmp/check.html                                                              # HTML 引用是否齐全
grep -c '照片待补\|待补' /tmp/check.html                                                           # 占位是否还有残留

# Pages 在线预览 + 资源 HTTP 200 验证
curl -sL -o /dev/null -w "%{http_code}\n" "https://<owner>.github.io/<repo>/"
curl -sL -o /dev/null -w "%{http_code}\n" "https://<owner>.github.io/<repo>/images/xxx.jpg"
```

**验收结论标准**：commit 时间晚于素材送达时间 + 文件/图片都在 + HTTP 200 → 才算交付成功。占位残留（如 Hero 头像、未提供的场次照片）是用户没给素材，不算失败，如实汇报即可。

## 常见坑

| 问题 | 原因 | 解决 |
|------|------|------|
| 发图 bot 没反应 | 纯图片消息无 @，bot 只收 @ 消息 | 按第一节步骤：先 `images create --as bot` 拿 key，再 markdown 内嵌 @+图 |
| `images create` 报 missing_scope im:resource | user 身份未授权 | 换 `--as bot`（bot 身份无需该 scope） |
| raw.githubusercontent.com 429 | GitHub 反爬限流 | 用 `gh api repos/.../contents/<file> --jq '.content' \| base64 -d` |
| bot 说「收到替换需求但图片不在我事件流里」 | 图片消息没 @ 它 | 重新发，每条图带 `<at>`，说明放哪个位置 |
| @ 看起来发了但对方收不到，且没有任何报错 | `<at>` 里的引号是**全角** `“ou_xxx”`，飞书不解析，整段退化成纯文本 | 改半角 `"`；发完用 `+messages-mget --jq '.mentions'` 核 |
| 回给了 bot，bot 却说没收到 / 答非所问 | `--reply-in-thread` 的 thread 由 `--message-id` 决定，reply 错消息就落到另一条 thread | reply 到**对方自己发的那条** om；发完用 mget 的 `thread_id` 核 |
| 在 `+chat-messages-list` 里找不到刚发的话题回复 | 主站流不含话题内消息 | 用 `+threads-messages-list --thread-id omt_xxx`（或直接喂 om_ ID） |
| 明明 @ 了却「不在群成员列表」 | 对方是外部租户 bot，`+chat-members-list --member-types bot` 不列它 | 从消息历史 `sender.id` 取 open_id；成员列表不能当作投递前置校验 |
| `im chat list` / `+chat-list` 返回空 | bot 身份下该命令不覆盖全部群 | 用 `+chat-search --query "群名" --as bot` |

## 关联

- Bot 路由表/群成员、@铁律、轮询回复：`agent-group-collab`（用户自建，需 `hermes curator adopt` 后才可自动维护）
- 飞书群聊多 Agent 管理（bot 注册、教学 @mention）：`feishu-group-chat`（用户自建，同上）
