---
name: feishu-bot-media-delivery
description: Feishu bot media needs @mention; verify GitHub deliveries.
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

## 关联

- Bot 路由表/群成员、@铁律、轮询回复：`agent-group-collab`（用户自建，需 `hermes curator adopt` 后才可自动维护）
- 飞书群聊多 Agent 管理（bot 注册、教学 @mention）：`feishu-group-chat`（用户自建，同上）
