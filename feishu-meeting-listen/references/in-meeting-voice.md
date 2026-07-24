# In-Meeting Voice Integration

2026-07-21 实现。会中语音回复链路。

## 架构

```
ByteView 收音频 → 豆包 WebSocket (ASR)
  → receive_audio() yield str (ASR 文字)
  → DeepSeek API 生成回复
  → macOS say → ffmpeg → 16kHz mono PCM
  → byteview.send_audio() 分块发送
```

## 环境变量

```
# DeepSeek API Key — 语音回复生成
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# DashScope API Key — 百炼 WebSocket ASR (sk-ws-* 格式)
DASHSCOPE_API_KEY=sk-your-dashscope-api-key-here
```

## 关键文件

- `scripts/meeting_realtime.py` — 主实时语音流程
- `scripts/test_asr.py` — ASR 测试
- `scripts/test_full.py` — 端到端测试
- `config/.env` — 环境变量配置

## 参考

- `dashscope-realtime-asr.md` — 百炼 WebSocket ASR 详细文档
- `deepseek-voice-pipeline.md` — DeepSeek + TTS 语音回复链路
- `doubao-tts-research.md` — 豆包 TTS 调研
- `realtime-voice-debug.md` — 实时语音调试记录
