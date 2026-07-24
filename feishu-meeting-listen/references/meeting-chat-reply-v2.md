# 会中聊天 @浪子 文字回复（2026-07-21 最终版）

## 架构：纯 lark-cli，零 AI 管线

用户明确要求（2026-07-21）：
> **「不用生成语音回复 直接在对话框里回复就好了」**
> **「为什么要豆包理解，你不能调用 lark cli 的能力直接回复么？」**

→ 不走豆包、不走 LLM、不走 TTS。纯 lark-cli 接收→发送。

## 实现

### 1. 数据源：`vc +meeting-events` chat_received

```bash
lark-cli vc +meeting-events --as bot --meeting-id <id> --page-all --page-size 100
```

- 标准会议 ✅ 个人会议 ✅ 都支持 chat_received
- 已在会议 214916822（GTM 宣贯）和 556362268（个人会议）验证

### 2. 检测逻辑：main.py poll_meeting_chat()

```python
async def poll_meeting_chat(lark, meeting_id, doubao, stop_event):
    """3秒轮询，seen_ids 去重，message_type=1 文本，含"浪子"触发"""
    # 检测到触发 → lark.meeting_message_send(meeting_id, reply)
```

### 3. 发送：lark_cli.py meeting_message_send()

```python
def meeting_message_send(self, meeting_id: str, text: str) -> dict:
    return _run([
        "vc", "+meeting-message-send",
        "--as", "user",  # 🚨 必须 --as user，bot 需 app 级 scope
        "--meeting-id", meeting_id,
        "--msg-type", "text",
        "--text", text,
    ])
```

### 4. 权限：`vc:meeting.message:write`

- user 授权：`lark-cli auth login --scope "vc:meeting.message:write" --no-wait --json` + 扫码
- bot 需要开发者在控制台申请（user 更简单）

## 触发词

- 当前：`"浪子"` 硬编码在 `poll_meeting_chat()` 中
- 回复格式：`f"收到，{sender}。{content}"`（模板化，非 LLM）

## 已知限制

| 限制 | 说明 |
|------|------|
| 回复纯文本 | 不支持 markdown / 富文本 |
| 单条发送 | 每次触发一条，无流式 |
| 身份混用 | `--as user` 发送 → 聊天框显示为用户身份，非 bot |
| 无上下文 | 不携带历史对话，纯单轮 |

## 诊断日志

`poll_meeting_chat()` 关键日志：
- `[chat] poll #N total_events=X new_chats=Y` — 每轮统计
- `[chat] event detail sender=X items_count=Y` — 每条事件
- `[chat] item detail sender=X msg_type=Y content=...` — 每条消息详情
- `[chat] triggered by X content=...` — 触发检测
- `[chat] replying to meeting reply=...` — 准备发送
- `[chat] reply sent` / `[chat] send failed error=...` — 发送结果

⚠️ ByteView raw msg 日志（每秒 10+ 条）会淹没 chat 日志——用 `grep 'chat\|trigger'` 单独搜索
