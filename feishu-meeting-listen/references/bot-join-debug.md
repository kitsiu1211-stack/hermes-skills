# 官方 Bot 入会排坑实录（2026-07-19）

## 测试背景

5 次 Bot 入会测试，会议号 518680334 / 629602570，全链路 ByteView + 豆包均连接成功，但豆包未产出语音。

## 协议修复

### 1. `_start_session_payload` 缺字段

**问题**：payload 缺少 `model` 和 `opening_line`，导致豆包不生成开场语音。

**修复**（`voice_agent/doubao.py`）：
```python
def _start_session_payload(self) -> dict:
    payload = {
        "asr": {"extra": {"end_smooth_window_ms": 1500}},
        "tts": {
            "speaker": self.config.doubao_voice,
            "audio_config": {...},
        },
        "dialog": {
            "bot_name": self.config.bot_name,
            "system_role": self._load_persona(),
            ...
        },
    }
    if self.config.opening_line:
        payload["opening_line"] = self.config.opening_line  # 根级，非 dialog 下
    if self.config.doubao_model:
        payload["model"] = self.config.doubao_model
    return payload
```

### 2. `say_text()` 调用移除

**问题**：`main.py` 中 `say_text()` 发 `SayHello` 事件不触发端到端模型语音。opening_line 应通过 `start_session` payload 传入。

**修复**：移除 `main.py` 中的 `say_text()` 调用和 0.2s sleep，opening_line 由 session 启动时自动触发。

### 3. 音频流日志

**修复**：`forward_byteview_to_doubao` 加日志，每 50 个 chunk 打印一次，确认 ByteView → 豆包音频流通。

## 已知限制

| 限制 | 说明 |
|------|------|
| 端到端模型需真人音频 | 豆包不生成 TTS——空会议不出声，必须有真人说话 |
| barge-in 默认开启 | 真人一开口就打断 Bot |
| 回声问题 | 外放导致 Bot 自己声音漏回麦克风→被当成打断→只说一句就停。务必戴耳机 |
| 空会议报错 | 完全空的会议上行可能报 1001（`unexpected end of JSON input`） |

## 已验证的稳定链路

- ByteView WebSocket ✅
- 豆包连接 ✅
- 音频 ByteView → 豆包 ✅（每 chunk ~4800 bytes）
- 豆包 → ByteView：❌ 未产出（真人未说话时）

## 下一步

开真实会议 + 真人说话 → 验证豆包 → ByteView 方向音频流是否产出。
