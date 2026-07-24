# Qwen-Audio-3.0-Realtime 接入计划与当前状态

> 2026-07-15 千问发布实时语音模型。API 验证结果：**模型尚未上线**，改用 DashScope 实时 ASR 作为过渡方案。

## 当前状态（2026-07-15）

- ❌ **Qwen-Audio-3.0-Realtime 模型未部署**：所有模型名（`qwen-audio-3.0-realtime-flash`, `qwen-omni-turbo`, `qwen3-audio-realtime` 等）在 `wss://dashscope.aliyuncs.com/api-ws/v1/realtime` 均返回 "Model not found"
- ❌ API 文档 404：`https://help.aliyun.com/zh/model-studio/qwen-audio-realtime-api` 不存在
- ✅ **Plan B 已就绪**：DashScope 实时 ASR (Paraformer-v2) + Qwen-Plus 文本分析
- ✅ 百炼 API Key 已验证（REST + WebSocket 双向通过）

## 模型能力（预期）

| 能力 | 说明 | 场景价值 |
|---|---|---|
| Agent 工具调用 | FunctionCall 标准 | 会议中听到客户名自动查 C360 |
| 双工交互 | 边说边听，可打断 | Agent 真正入会参与对话 |
| 共情对话 | 语气/节奏/情感动态调整 | 实时感知客户情绪 |
| 毫秒响应 | VoiceBench 92.5 | 交互自然不卡顿 |

## 接入架构（计划）

```
飞书会议音频 → BlackHole 环路 → Python WebSocket → Qwen-Audio-3.0-Realtime
                                              ↓
                                     FunctionCall 触发
                                              ↓
                              C360 / 样板间 / ISV / 告警
```

## 环境依赖

```bash
# 音频环路驱动（需 sudo + 重启）
brew install blackhole-2ch

# Python 依赖
pip3 install dashscope websocket-client pyaudio

# 音频路由：音频 MIDI 设置 → 创建多输出设备 → 勾选 BlackHole 2ch + 扬声器
```

## API 端点（已验证失败）

| 端点 | 状态 | 说明 |
|---|---|---|
| `wss://dashscope.aliyuncs.com/api/v1/realtime` | ❌ 404 | |
| `wss://dashscope.aliyuncs.com/api-ws/v1/realtime` | ⚠️ 连接成功但模型不存在 | Session 创建成功，model 解析为 `qwen-omni-turbo-realtime-2025-03-26` 后报 ModelNotFound |
| `wss://dashscope.aliyuncs.com/api-ws/v1/inference` | ⚠️ 连接成功但协议不匹配 | 需要 `run-task` 格式，非 OpenAI Realtime 协议 |

## 过渡方案：DashScope 实时 ASR

详见 `references/dashscope-realtime-asr.md`。

## vs 现有 poll-v5

| 维度 | poll-v5 | DashScope ASR | Qwen-Audio-3.0 |
|---|---|---|---|
| 数据源 | 文字字幕（1-3s 延迟） | 原始音频（实时） | 原始音频（实时） |
| 分析 | 关键词匹配 + bash C360 | ASR 转写 + Qwen-Plus 分析 | 端到端语义理解 |
| 客户识别 | 关键词匹配（不可靠） | 转写文本分析 | 语义理解 + 声纹 |
| 情报查询 | bash 脚本触发 | Python 分析后调用 C360 CLI | FunctionCall 自动 |
| 交互 | 被动监听 | 被动监听 | 可主动插话 |
| 情感 | 无 | Qwen-Plus 情感分析 | 语气/节奏/情感 |
| 成本 | 零 Token | ASR + LLM Token | WebSocket + Token |
| 部署 | bash 单文件 | Python + 音频环路 | Python + 音频环路 |
| 状态 | ✅ 生产 | ✅ 测试通过 | ❌ 等待上线 |
