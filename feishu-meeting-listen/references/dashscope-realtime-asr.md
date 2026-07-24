# DashScope 实时语音识别 (ASR) 接入指南

> Qwen-Audio-3.0-Realtime 未上线期间的过渡方案。通过 DashScope Paraformer 实时 ASR + Qwen-Plus 文本分析实现会议实时监听。

## 已验证状态（2026-07-15）

- ✅ WebSocket 连接：`wss://dashscope.aliyuncs.com/api-ws/v1/inference`
- ✅ 模型：`paraformer-realtime-v2`
- ✅ API Key：百炼 `sk-ws-*` 格式的 WebSocket Key（同时验证了 REST `/compatible-mode/v1/chat/completions` 的 `qwen-plus` 可用）
- ✅ task-started / task-finished 生命周期正常
- ✅ 音频推流通道打通
- ❌ **Qwen-Audio-3.0-Realtime 未上线**：所有模型名被 `/api-ws/v1/realtime` 端点（Omni 架构）映射到不存在的部署 `qwen-omni-turbo-realtime-2025-03-26`；百炼帮助文档 404

## WebSocket 协议

### 端点

```
wss://dashscope.aliyuncs.com/api-ws/v1/inference
```

### 认证

```python
header={"Authorization": f"Bearer {API_KEY}"}
```

### 启动任务 (run-task)

```json
{
    "header": {
        "action": "run-task",
        "task_id": "<uuid>",
        "streaming": "duplex"
    },
    "payload": {
        "task_group": "audio",
        "task": "asr",
        "function": "recognition",
        "model": "paraformer-realtime-v2",
        "parameters": {
            "format": "pcm",
            "sample_rate": 16000,
            "enable_intermediate_result": true,
            "enable_punctuation": true
        },
        "input": {}
    }
}
```

**关键**：`payload.input` 字段必须存在（即使是空对象 `{}`），否则返回 "Missing required parameter 'payload.input'!"。

### 发送音频

任务启动后（收到 `task-started` 事件），通过同一个 WebSocket 连接发送二进制 PCM 数据：

```python
ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY)
```

- 格式：16-bit signed int, little-endian, 单声道
- 采样率：16000 Hz
- 块大小：3200 字节（200ms）

### 结束任务 (finish-task)

```json
{
    "header": {
        "action": "finish-task",
        "task_id": "<uuid>",
        "streaming": "duplex"
    },
    "payload": {
        "input": {}
    }
}
```

### 服务端事件

| 事件 | 说明 |
|---|---|
| `task-started` | 任务创建成功，可开始推送音频 |
| `task-failed` | 任务失败，`header.error_code` + `header.error_message` |
| `result-generated` | 转写结果，`payload.output.sentence.text` + `sentence_end` |
| `task-finished` | 任务完成 |

### 转写结果结构

```json
{
    "header": {"event": "result-generated", "task_id": "xxx"},
    "payload": {
        "output": {
            "sentence": {
                "text": "今天来讨论方案",
                "sentence_end": false,
                "begin_time": 170,
                "end_time": 920,
                "words": [
                    {"text": "今天", "begin_time": 170, "end_time": 295}
                ]
            }
        }
    }
}
```

- `sentence_end: true` 表示完整句子结束
- 同一句子可能多次推送（修正/补全），用 `text` 字段去重

## 可用模型

| 模型 | 说明 | 推荐 |
|---|---|---|
| `paraformer-realtime-v2` | 通用实时 ASR | ✅ 首选 |
| `paraformer-realtime-v1` | 旧版 | 兼容 |
| `fun-asr-realtime` | 更新版 ASR | 备选 |
| `qwen3-asr-flash-realtime` | Qwen3 ASR | 备选 |

## 音频路由设置

### macOS BlackHole + 多输出设备

1. **安装 BlackHole**：`brew install blackhole-2ch`（需 sudo，需重启）
2. **创建多输出设备**：
   - 打开「音频 MIDI 设置」(Audio MIDI Setup)
   - 左下角 + → 创建多输出设备
   - 勾选 BlackHole 2ch + MacBook Air 扬声器
   - 右键 → 将此设备用于声音输出
3. **或在系统设置中切换**：声音 → 输出 → 多输出设备

### 验证音频路由

```bash
# 查看 BlackHole 输入设备
system_profiler SPAudioDataType | grep -A8 "BlackHole"

# 列出可录音设备
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if 'BlackHole' in info['name']:
        print(f'{info[\"name\"]} index={i} input={info[\"maxInputChannels\"]}')
p.terminate()
"
```

## 完整脚本

脚本位于 `scripts/meeting_realtime.py`，包含完整的：音频采集 → ASR 转写 → 千问分析 → C360 查询 链路。

```bash
cd ~/.hermes/skills/feishu/feishu-meeting-listen
python3 scripts/meeting_realtime.py
```

### 脚本架构

```
BlackHole → PyAudio (采集线程)
              ↓
         audio_queue
              ↓
    DashScope ASR WebSocket (audio_pusher 线程)
              ↓
         transcript_queue
              ↓
    主循环：每 5s 分析累积文本
              ↓
    Qwen-Plus (文本分析)
              ↓
    lark-c360 (客户查询)
```

### 分析配置

- 模型：`qwen-plus` (REST API)
- 分析间隔：5 秒
- C360 查询冷却：同一客户 30 秒内不重复
- 分析输出：客户名、关键话题、行动项、情绪、是否需要 C360 查询

## 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| WebSocket 连接成功但 task-failed: ModelNotFound | 用了 `realtime` 端点而非 `inference` 端点 | 改用 `wss://dashscope.aliyuncs.com/api-ws/v1/inference` |
| "Missing required parameter 'payload.input'" | run-task 缺少 `input` 字段 | 添加 `"input": {}` |
| "Missing required parameter 'header'" | 缺少 header | 添加包含 action/task_id/streaming 的 header |
| BlackHole 找不到 | 未重启 | 安装后必须重启 Mac |
| stream.read() 阻塞 | 音频没有路由到 BlackHole | 检查多输出设备是否正确配置 |
| NO_VALID_AUDIO_ERROR | 没有发送音频或音频全为静音 | 确认系统音频正在路由到 BlackHole |
