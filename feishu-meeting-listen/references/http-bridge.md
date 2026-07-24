# Hermes ↔ 会议 HTTP Bridge

2026-07-21 最终架构。替代文件队列轮询（inbox/outbox 的延迟问题）。

## 架构

```
main.py 检测问题 → 写 meeting_inbox.json（标记）
                  ↓
Hermes 收到用户消息 → 读 inbox → 思考 → curl POST localhost:19876/reply
                  ↓
HTTP Server (aiohttp) → 根据 channel 分发：
  - "voice" → doubao.say_tts(reply) → 豆包 ChatTTSText TTS → ByteView 播回
  - "chat"  → lark.meeting_message_send(meeting_id, f"@{sender} {reply}")
```

## HTTP 端点

`POST http://localhost:19876/reply`

```json
{"channel": "voice|chat", "sender": "袁鑫杰", "reply": "回复内容"}
```

## 代码位置

- HTTP Server: `main.py` → `_run_http_server()` → aiohttp `web.Application()`，routes `@routes.post("/reply")`
- Bridge: `voice_agent/bridge.py` → `push_question()` 写入 `~/.hermes/meeting_inbox.json`
- 触发: `main.py` → `_ask_hermes(channel, sender, text, meeting_id)` → fire-and-forget，**不返回值**
- **关键**：`_ask_hermes` 不轮询 outbox。回复异步通过 HTTP push 到达。

## HTTP Handler 逻辑

```python
@routes.post("/reply")
async def handle_reply(request):
    data = await request.json()
    if data["channel"] == "voice":
        await doubao.say_tts(data["reply"])  # ChatTTSText(500) TTS-only
    else:
        lark.meeting_message_send(meeting_id, f"@{data['sender']} {data['reply']}")
```

## 已验证

- ✅ curl 测试通过：`curl -X POST localhost:19876/reply ...` → `{"ok": true}` → bot 发文字到会议聊天
- ✅ 语音 TTS 出豆包音频流（ChatTTSText 500 触发纯 TTS）

## 优势 vs 文件轮询

| 方案 | 延迟 | 可靠性 |
|------|------|--------|
| 文件轮询 outbox | 1-45s（poll 间隔 + 超时） | 依赖 Hermes 主动检查 |
| HTTP push | ~0ms（直接推送） | Hermes 直接 POST，无等待 |
