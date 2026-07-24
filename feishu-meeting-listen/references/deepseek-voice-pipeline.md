# DeepSeek + macOS TTS 语音回复链路

2026-07-21 实现。统一两条回复链路（弹幕 + 语音）均走 DeepSeek 生成回复，区别仅在于输出方式。

## 架构

```
会中弹幕「浪子」
  → poll_meeting_chat() 检测 chat_received 事件
  → DeepSeek API 生成回复
  → lark-cli vc +meeting-message-send --as bot 发回聊天

会中语音
  → ByteView 收音频 → 豆包 WebSocket (仅 ASR)
  → receive_audio() yield str (ASR 文字)
  → forward_doubao_to_byteview() 接收 ASR 文字
  → DeepSeek API 生成回复
  → _text_to_pcm() macOS say → ffmpeg → 16kHz mono PCM
  → byteview.send_audio() 分块发送 (4800B/块, 0.02s 间隔)
```

## 关键实现

### `receive_audio()` 签名变更

```python
# 旧：仅 yield bytes (TTS 音频)
async def receive_audio(self) -> AsyncIterator[bytes]:

# 新：yield str (ASR 文字) + bytes (豆包 TTS，丢弃)
async def receive_audio(self) -> AsyncIterator[bytes | str]:
```

### `forward_doubao_to_byteview()` 新逻辑

```python
async for msg in doubao.receive_audio():
    if isinstance(msg, bytes):
        # 豆包自己的 TTS → 丢弃
        pass
    elif isinstance(msg, str) and msg.strip():
        # ASR 文字 → DeepSeek → macOS say → ByteView
        reply = await _deepseek_chat(msg)
        pcm = _text_to_pcm(reply)
        for i in range(0, len(pcm), 4800):
            await byteview.send_audio(pcm[i:i+4800])
            await asyncio.sleep(0.02)
```

### macOS say → PCM

```python
def _text_to_pcm(text: str) -> bytes:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        aiff = os.path.join(td, "out.aiff")
        pcm = os.path.join(td, "out.pcm")
        subprocess.run(["say", "-o", aiff, text], check=True, timeout=15)
        subprocess.run([
            "ffmpeg", "-y", "-i", aiff, "-f", "s16le",
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", pcm,
        ], check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return Path(pcm).read_bytes()
```

## 防死循环

弹幕链路中 bot 自己的回复也会触发新的 `chat_received` 事件，需双保险：

```python
last_reply_time = 0  # 10 秒 cooldown
if sender == "浪子":
    continue  # 跳过自己的消息
if now - last_reply_time < 10:
    continue  # cooldown
```

## 所需权限

- `vc:meeting.message:write` — bot app scope，在飞书开放平台控制台申请
- DeepSeek API Key — 通过 `DEEPSEEK_API_KEY` 环境变量传入 (from `~/.hermes/.env`)

## 语音延迟

- DeepSeek API: ~1-2 秒
- macOS say + ffmpeg: ~2-4 秒
- 总计: ~3-6 秒延迟（可接受范围）
