# 音频转录（本地 Whisper）

本地转录短音频（≤30s）的首选方案。

## 命令

```bash
# 1. 转为 16kHz mp3
ffmpeg -y -i <input.ogg|m4a|aac> -ar 16000 -ac 1 -b:a 32k /tmp/audio_asr.mp3

# 2. 转录（base 模型最快，5s 音频 10s 完成）
~/.hermes/hermes-agent/venv/bin/whisper /tmp/audio_asr.mp3 \
  --model base --language Chinese --output_format txt --output_dir /tmp

# 3. 读结果
cat /tmp/audio_asr.txt
```

## 模型选择

| 模型 | 速度 | 准确度 | 适用 |
|------|------|--------|------|
| tiny | 极快 | 低（中文易出错） | 英文短片段 |
| **base** | 快（~2x 实时） | 中等 | **中文首选** |
| small | 慢（~10x 实时） | 较好 | 超时可跳过 |

## 注意事项

- whisper 在 `~/.hermes/hermes-agent/venv/bin/whisper`
- 仅 CPU 推理，无 GPU 加速
- 30s 以上音频建议走 DashScope Paraformer 异步 API（本 session 遇到上传失败，待排查）
