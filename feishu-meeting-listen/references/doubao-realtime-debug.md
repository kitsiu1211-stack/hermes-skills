# 豆包端到端实时语音：排坑速查

## 🚨 快速排障流程

遇到豆包无声按顺序查：

1. **ByteView 音频流速**：`byteview.py` 加 `log("bv", "raw msg", idx=idx, raw_len=len(message))`——不要只看每 50 条的 `fwd` 日志
2. **session_id**：`send_audio` 必须 `flag=WithEvent` + `event=TaskRequest` + `session_id`
3. **ASR 信号**：应出现 `[doubao] recv msg type=FullServerResponse event=ASRResponse payload_size=736`
4. **TTS 信号**：ASR 积够句子后 `AudioOnlyServer` → `yield tts audio`

## 最终突破：2026-07-21 session_id 修复 🎉

**累计 10+ 次测试定位到根因**：新版 `protocols.py` 的 `Message` 类中 `AudioOnlyClient` 默认 `flag=NoSeq` 不包含 `session_id`。豆包收到音频后无法关联会话，静默丢弃。

### 修复代码

```python
# ❌ 旧版（无声）
msg = Message(type=MsgType.AudioOnlyClient, flag=MsgTypeFlagBits.NoSeq)
msg.payload = audio

# ✅ 新版
msg = Message(type=MsgType.AudioOnlyClient, flag=MsgTypeFlagBits.WithEvent)
msg.event = EventType.TaskRequest
msg.session_id = self.session_id
msg.payload = audio
```

## ChatResponse 文本捕获（2026-07-21）

用于会中文字回复：`receive_audio()` 中解析 `FullServerResponse` 的 `ChatResponse` 事件 payload → 提取 JSON `result`/`text` 字段 → `self.text_responses.append(text)`。

```python
if isinstance(event, EventType) and event == EventType.ChatResponse and msg.payload:
    chat_data = json.loads(msg.payload.decode("utf-8"))
    text = chat_data.get("result", "") or chat_data.get("text", "") or ""
    if text:
        self.text_responses.append(text)
```

配合 `poll_meeting_chat()` 中 `await asyncio.sleep(3)` 后取 `doubao.text_responses` → `lark.meeting_message_send()`。

## 历史排坑

- 空会议断开 45000001：至少 1 个真人说话
- 回声打断：务必戴耳机
- 协议版本：Version1（V3 被拒）
- App Key 不匹配：看服务端 `expected:[...]`
- say_text() 不发声：端到端模型不响应 SayHello
- opening_line 走根级别 payload，非 dialog 子字段
