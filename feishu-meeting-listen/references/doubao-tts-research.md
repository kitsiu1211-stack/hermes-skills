# 豆包双向流式 TTS 调研

日期：2026-07-16，更新：2026-07-17（协议验证 + API Key 排查）

## 目标场景

在飞书会议中实现双向语音对话（类似豆包 Chatbot 的全双工体验）：
- 用户说话时 bot 实时识别（ASR）
- Bot 理解后生成回复（LLM）
- Bot 通过语音在会议中发声（TTS）
- 用户可以随时打断 bot（全双工）

## 豆包 TTS 模型选择

| 模型 | X-Api-Resource-Id | 定位 |
|------|-------------------|------|
| 语音合成 2.0 | `seed-tts-2.0` | 最新版，音质最好，支持语音指令 |
| 声音复刻 2.0 | `seed-icl-2.0` | 声音复刻，使用克隆音色 |

> **⚠️ 注意**：新版 API 的 `X-Api-Resource-Id` 只接受 `seed-tts-2.0` 和 `seed-icl-2.0`。旧文档中提到的 `seed-tts-1.0` / `seed-tts-1.0-concurr` 在 WebSocket 双向流式 V3 接口中不再作为 resource_id 使用（会返回 403）。

## API 端点

```
wss://openspeech.bytedance.com/api/v3/tts/bidirection
```

## 鉴权

```
X-Api-Key: <火山引擎豆包语音 API Key>
X-Api-Resource-Id: seed-tts-2.0
X-Api-Connect-Id: <UUID>（可选，用于追踪连接）
```

**⚠️ 豆包语音 vs 豆包大模型 Key 不互通**：
- 豆包大模型（ARK）的 Key 在语音接口返回 **HTTP 401**
- 豆包语音的 Key 在语音接口返回 **HTTP 403**（Key 有效但需开通服务）
- Bearer token 鉴权不适用（返回 400）
- 语音 Key 获取地址：`https://console.volcengine.com/speech/new/setting/apikeys?projectName=default`

## WebSocket 协议（正确的事件名）

### 客户端 → 服务端

| EventType | 说明 | 关键参数 |
|-----------|------|---------|
| `StartConnection` | 建立 WebSocket 连接 | 无 |
| `StartSession` | 创建合成会话 | `session_id`, `req_params.speaker`, `req_params.audio_params` |
| `TaskRequest` | 发送待合成文本 | `session_id`, `text` |
| `CancelSession` | 取消当前会话 | `session_id` |
| `FinishSession` | 结束当前会话 | `session_id` |
| `FinishConnection` | 断开 WebSocket 连接 | 无 |

### StartSession 请求体

```json
{
  "EventType": "StartSession",
  "session_id": "<UUID>",
  "req_params": {
    "speaker": "zh_female_qingxin",
    "audio_params": {
      "format": "pcm",
      "sample_rate": 24000
    }
  }
}
```

- `format`：流式场景推荐 `pcm`（非 `mp3`）
- `speaker`：从[音色列表](https://www.volcengine.com/docs/6561/1257544)获取

### 服务端 → 客户端

| EventType | 说明 |
|-----------|------|
| `ConnectionStarted` | 建连成功 |
| `SessionStarted` | 会话开始 |
| `TTSSentenceStart` | 开始合成音频 |
| `TTSResponse` | 音频数据（`payload.audio` 为 base64） |
| `TTSSentenceEnd` | 音频合成结束 |
| `TTSSubtitle` | 字级别时间戳（需开启 `enable_subtitle`） |
| `SessionFinished` | 会话结束（含 `payload.usage.text_words` 计费字数） |
| `ConnectionFinished` | 连接结束 |
| `SessionCanceled` | 会话取消 |
| `ConnectionFailed` | 建连失败 |
| `SessionFailed` | 会话失败 |

## 关键特性

- **双向 WebSocket**：流式输入文本 + 流式输出音频
- **支持打断**：发送 `CancelSession` 立即停止当前合成
- **链接复用**：一个 WebSocket 连接支持多次对话 session（顺序执行，不并发）
- **自动切句**：不需要手动切句/攒句，直接把 LLM 流式输出丢进去

## 完整双工链路架构

```
会议音频 → BlackHole → Paraformer ASR (DashScope, 实时)
                           ↓
                      LLM (DeepSeek V4, 流式输出)
                           ↓
                      豆包 TTS (流式合成, seed-tts-2.0)
                           ↓
                      BlackHole → 会议麦克风
                           ↓
               ASR 检测到用户说话 → 打断 TTS (CancelSession)
```

## 依赖

- 火山引擎 API Key（**豆包语音**产品，非豆包大模型 ARK）
- BlackHole 虚拟音频驱动（已安装）
- Multi-Output Device 音频路由（待配置）
- Paraformer-realtime-v2（已接入，DashScope）

## 重要澄清：语音合成大模型 ≠ 端到端实时语音大模型

这两个是火山引擎文档里并列的同级分类，但本质完全不同，容易混淆：

| 维度 | 语音合成大模型（TTS） | 端到端实时语音大模型 |
|------|----------------------|---------------------|
| **输入** | 文本 | 音频（人声） |
| **输出** | 音频 | 音频（AI 回复） |
| **核心能力** | 文字 → 语音（朗读） | 听懂 → 思考 → 说话（完整对话闭环） |
| **类比** | 朗读引擎 | GPT-4o Advanced Voice Mode |
| **接入方式** | WebSocket / HTTP API | Android SDK / iOS SDK |
| **适合本场景** | ✅ 是（LLM 已做理解，只需嘴巴） | ❌ 否（无服务端 API，且与 LLM 冲突） |

**为什么只用语音合成 TTS**：我们的架构是 ASR → LLM(DeepSeek) → TTS，LLM 已经负责「理解+生成」，只需要 TTS 把文字念出来。端到端模型自带理解和生成能力，反而与 DeepSeek 重复，且只有移动端 SDK，无法在 macOS Python 脚本中调用。

## API Key 故障排查速查表

| 现象 | HTTP 状态码 | 原因 | 解决 |
|------|-----------|------|------|
| 豆包大模型 Key 调语音 | **401** | Key 类型不匹配（ARK ≠ Speech） | 去豆包语音控制台单独获取 Key |
| 语音 Key 但未开通服务 | **403** | Key 有效但账号未激活语音服务 | 去 `console.volcengine.com/speech` 开通 |
| Bearer token 鉴权 | **400** | 协议不匹配，语音不用 Bearer | 改用 `X-Api-Key` header |
| 旧版 App-Id+Access-Key | **401** | Key 不是旧版格式 | 用新版 `X-Api-Key` 方式 |
| seed-tts-1.0 作 resource_id | **403** | V3 接口不接受 1.0 | 改用 `seed-tts-2.0` |

## 文档链接

- WebSocket 双向流式 TTS（语音合成大模型 API 列表页）：`https://www.volcengine.com/docs/6561/1329505`
- 豆包语音 API Key 管理：`https://console.volcengine.com/speech/new/setting/apikeys?projectName=default`
- 豆包语音服务开通：`https://console.volcengine.com/speech/`

## 测试脚本

`scripts/test_doubao_tts.py` — 可复用的 API 连通性测试脚本。修改 `API_KEY` 后直接运行，验证鉴权、建连、合成全链路。

## 进度

- [x] 获取豆包语音 API Key（已拿到，待开通服务）
- [x] 验证 WebSocket 协议（EventType 格式确认，见测试脚本 `scripts/test_doubao_tts.py`）
- [ ] 开通豆包语音服务（用户侧操作，console.volcengine.com/speech）
- [ ] 配置 Multi-Output Device 音频路由
- [ ] 实现完整的 TTS 客户端（含打断逻辑）
