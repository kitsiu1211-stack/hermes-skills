# Hermes ↔ 会议 Bot 桥接协议

## 架构原则

**一个大脑**：Hermes（DeepSeek）是唯一的推理引擎。`main.py` 只做耳朵（豆包 ASR）和嘴巴（豆包 TTS）。不要在 `main.py` 里自己调 DeepSeek——那是另一个大脑。

## 通信方式：HTTP Push（生产，2026-07-21）

**文件队列已废弃**——依赖 Hermes 主动检查，延迟 1-45s 且会超时。HTTP push 零延迟。

### Bot 侧（main.py）

- `_ask_hermes(channel, sender, text, meeting_id)` — **fire-and-forget**，写 inbox 文件仅作标记，无返回值
- `_run_http_server(lark, meeting_id, doubao, stop_event)` — aiohttp 监听 `localhost:19876/reply`
- Handler 区分 channel：voice → `doubao.say_tts(reply)`，chat → `lark.meeting_message_send(meeting_id, f"@{sender} {reply}")`

### Hermes 侧

```bash
# 收到用户消息 → 检查 inbox
cat ~/.hermes/meeting_inbox.json

# 思考后 HTTP push 回复
curl -X POST http://localhost:19876/reply \
  -H "Content-Type: application/json" \
  -d '{"channel":"chat","sender":"袁鑫杰","reply":"深圳今天阵雨，27°C"}'
```

## push_question 协议

```json
{"req_id": "abc12345", "channel": "voice|chat", "sender": "袁鑫杰", 
 "text": "今天天气如何", "meeting_id": "766...", "ts": 1753112345.0}
```

## 关键设计决策

1. **fire-and-forget**：`_ask_hermes()` 无返回值。写 inbox → 立即返回，不阻塞 poller 或 voice handler
2. **HTTP push > 文件轮询**：消除延迟、消除超时。已验证端到端（`curl → ok: true`）
3. **两条独立链路**：chat → text reply，voice → TTS reply。绝不互串
4. **`receive_audio()` 返回 `AsyncIterator[bytes | str]`**：bytes = TTS 音频（全部转发 ByteView），str = ASR 文本（走 bridge → Hermes）
