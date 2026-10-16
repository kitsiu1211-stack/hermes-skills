# 聊天/会议证据检索链（做「事实还原」时用）

场景：用户问「某某在会上提了什么问题」「某同事为什么情绪这么大」「客户发的评估表是什么」——
需要把**群聊 / 一对一私聊 / 会中聊天框 / 会议字幕**里的原始证据挖出来，而不是凭印象作答。

结论：`im +messages-search` 这条最直觉的路**经常走不通**，用下面的替代链（全部只需现有权限）。

## 0. 不要卡在 messages-search

```bash
lark-cli im +messages-search --as user --query "疆海" --start "2026-10-07T00:00:00+08:00"
# → {"ok": false, "error": {"subtype": "missing_scope", "message": "missing required scope(s): search:message"}}
```

`search:message` 未授权，且要用户点设备码才能开。**不要因此判断「翻不到记录」**，也不要为了一个即时问题去弹授权打扰用户——
直接走下面的两步替代链。

## 1. 找会话：`im +chat-search`

```bash
lark-cli im +chat-search --query "<客户名 / 同事名>" --as user
```

返回 `data.chats[]`，每条含 `chat_id`、`name`、`external`（true = 外部群/客户群）、`owner_id`、`create_time`。
外对客场景一眼就能认出客户群（例：`疆海-飞书项目测试群`、`疆海 x 飞书 AI 效率先锋大赛作战室`）。

搜人用：
```bash
lark-cli contact +search-user --query "陈佳永" --as user
# 是 +search-user，没有 +user-search（写错报 unknown subcommand "…+user-search"）
# 返回 open_id + p2p_chat_id + department；外部客户查不到是正常的，别反复试
```

## 2. 读消息：`im +chat-messages-list`

```bash
# 群聊
lark-cli im +chat-messages-list --as user --chat-id oc_xxx \
  --page-size 40 --order desc --start "2026-10-14T00:00:00+08:00"
# 一对一（--user-id 传对方 open_id）
lark-cli im +chat-messages-list --as user --user-id ou_xxx --page-size 40 --order desc
```

- 返回结构是 **`data.messages[]`**（不是 `data.items`），字段：`sender.name`、`create_time`、`content`、`msg_type`、`message_id`
- `--order desc` + `--start <当天 00:00+08:00>` 最适合「今天这场会期间大家说了什么」
- 🚨 **`--page-size` 过大实测返回 0 条**（`--page-size 80` 空、`--page-size 40` 正常返回 40 条，同一会话）→ 拿到 0 条**先缩 page-size 重试**，再考虑 `--page-token` 翻页。别把「空返回」当成「没有记录」
- 想按人筛选再靠 Python 过滤 `sender.name`，成本远低于反复调 API

## 3. 会中聊天框 ↔ 同步群

会议开始后，会中聊天框与关联群打通，群里会出现系统消息：

> `Meeting has started. New messages will be synced in the group chat and in-meeting chat.`

两条路产出完全不同：

| 路径 | 能拿到什么 | 拿不到什么 |
|---|---|---|
| `vc +meeting-events --meeting-id <长id> --page-all --as user` → `chat_received_items` | 表情/短文本（实测整场仅 4 条 `OK`，`message_type: 3`、`message_id` 为空） | 图片、文件、长文本 |
| `im +chat-messages-list --chat-id <同步群>` | 带 `message_id` 的 `image` / `post` 消息（客户贴的评估表、需求清单、文档链接） | 字幕（那部分仍看会议 JSONL） |

**所以「客户在会上发了张表」要去同步群里取，不要指望 vc 事件。**

## 4. 下载聊天里的图片再读成文字

```bash
lark-cli im +messages-resources-download --as user \
  --message-id "om_xxx" --file-key "img_v3_xxx" --type image --output ./shared.png
```

- `file-key` 在消息 `content` 里（形如 `img_v3_0216f_...`）；`msg_type` 为 `image` / `post` 时优先看
- 下载后**必须用 vision 读成文字**：客户发的评估表/评分表读出来才有分析价值（本次读出的是一张「Jira 基准功能」评估表：18 项功能 + 权重 + 得分率，直接成了回答「对方提了什么问题」的主干）。只写「对方发了张图」等于没看
- 图片常是**局部截图**（右侧列被裁掉），读的时候注明「可见部分」，不要脑补被裁掉的内容

## 5. 拿到证据后怎么用（避免误读）

- **私聊吐槽 ≠ 会上发言**：内部同事在私聊里说的狠话（「我想跟他们干起来了」）和他会上对着麦克风说的（克制、提议会后书面应答）**是两件事**，交付时分别标注，别混成「他在会上发飙」
- **时间戳对齐**：把私聊消息时间与会中字幕时间对齐，就能指出「他这句火气对应的是 17:16–17:17 那段追问」——这种因果对齐才是用户真正想看的
- **范围铁律**：用户点名「现在这场会议」时就**只查这场**（会议 JSONL + 该场同步群 + 相关私聊当日消息），不要顺手扩散到别的群、别的客户、历史会话。范围错了会被当场纠正
