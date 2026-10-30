---
name: feishu-thread-reply
label: 飞书话题回复机制
description: Hermes Gateway 对飞书话题（thread）内回复消息的技术实现方式。
---

# 飞书话题回复

## Overview

Hermes Gateway 已经完整支持飞书话题模式。当用户在话题内发送消息时，Agent 的回复会自动保持在话题内，不会跳出到主对话。

## 技术实现（已就绪，无需额外配置）

### 接收端

在 `gateway/platforms/feishu.py` 第 2168 行：

```python
source = self.build_source(
    ...
    thread_id=getattr(message, "thread_id", None) or None,
    ...
)
```

飞书 `im.message.receive_v1` 事件中的 `thread_id` 字段已经被正确读取，并传入 `source.thread_id`。

### 回复端

在 `gateway/platforms/base.py` 第 1561 行：

```python
_thread_metadata = {"thread_id": event.source.thread_id} if event.source.thread_id else None
```

`source.thread_id` 被放入 `metadata` 字典，传递给 adapter 的 `send()` 方法。

### 发送端

在 `gateway/platforms/feishu.py` 第 3241-3250 行：

```python
reply_in_thread = bool((metadata or {}).get("thread_id"))
if reply_to:
    body = self._build_reply_message_body(
        content=payload,
        msg_type=msg_type,
        reply_in_thread=reply_in_thread,
        uuid_value=str(uuid.uuid4()),
    )
    request = self._build_reply_message_request(reply_to, body)
    return await asyncio.to_thread(self._client.im.v1.message.reply, request)
```

关键点：
- `reply_in_thread=True` 时，使用 `POST /im/v1/messages/{message_id}/reply` 接口
- 飞书 Lark SDK 的 `ReplyMessageRequestBody` 中 `reply_in_thread=True` 参数在 SDK 层面控制话题上下文
- 最终使用的是飞书官方 SDK 的 `message.reply()` 方法，而非 `message.create()`

## 消息路径

```
用户话题消息 → WS event → Gateway → thread_id 解析 → source.thread_id
    → Agent 处理 → response → metadata.thread_id → feishu.send()
    → POST /im/v1/messages/{reply_to}/reply (reply_in_thread=True)
    → 飞书 → 消息出现在话题内 ✅
```

## 用 lark-cli 手动回话题（实战坑，2026-10-29 验证）

```bash
lark-cli im +messages-reply --as bot --message-id om_xxx --reply-in-thread \
  --text '<at user_id="ou_xxxx">Name</at> 正文' --idempotency-key <唯一的key>
```

- **必须 `--as bot`**：默认走 user 身份，会报 `missing required scope(s): im:message.send_as_user`。不是权限没配，换成 bot 身份即可。
- **@ 必须用直双引号**：`<at user_id="ou_xxx">Name</at>`。全角引号 `“”` 会让飞书静默降级成纯文本，消息照发但 mention 丢失（`mentions` 数组为空）。
- **发完必须 `lark-cli im +messages-mget --message-ids <新msg>` 核对 `mentions`**，看到 `('Name', 'ou_xxx')` 才算真 @。
- **`--reply-in-thread` 的坑**：只在目标消息本身属于某个 thread（有 `thread_id`）时才能留在原串。如果目标只是主聊天流里一条 `reply_to` 普通消息（无 `thread_id`），加这个参数会**新建一个话题串**（返回的 `thread_id` 是新的）。要留主聊天流就别加 `--reply-in-thread`，靠 `--message-id` 引用即可。

## 已确认正常工作的场景

- 私聊话题回复
- 群聊话题回复
- 定时任务（cron job）的话题内交付
- Agent 主动发消息到话题
