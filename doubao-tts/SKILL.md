---
name: doubao-tts
description: 火山引擎豆包语音 TTS（语音合成）WebSocket 双向流式接入。使用官方二进制协议库，支持实时文本流式输入、音频流式输出。触发词：豆包TTS、火山TTS、seed-tts、语音合成、openspeech。
---

# 豆包语音 TTS WebSocket 双向流式

## 端点

```
wss://openspeech.bytedance.com/api/v3/tts/bidirection
```

## 鉴权

| 方式 | 请求头 | 说明 |
|------|--------|------|
| 新版控制台 | `X-Api-Key` + `X-Api-Resource-Id` | 推荐，从 [API Key 管理](https://console.volcengine.com/speech/new/setting/apikeys) 获取 |
| 旧版控制台 | `X-Api-App-Id` + `X-Api-Access-Key` + `X-Api-Resource-Id` | 从 [服务详情](https://console.volcengine.com/speech/service/10035) 获取 |

### Resource ID

| 值 | 模型 | 音色兼容 |
|----|------|---------|
| `seed-tts-2.0` | 豆包语音合成大模型 2.0 | 仅 2.0 音色（如 `zh_female_xiaohe_uranus_bigtts`） |
| `seed-tts-1.0` | 豆包语音合成大模型 1.0 | 仅 1.0 音色 |
| `seed-icl-2.0` | 豆包声音复刻大模型 2.0 | 复刻音色 |

## 通信协议

**不是纯 JSON WebSocket！** 使用自定义二进制帧协议，帧格式：4 字节头 + 事件 + 会话 ID + 载荷。

官方提供 `protocols_.py`（从 [文档页](https://docs.volcengine.com/docs/6561/2532486?lang=zh) 下载 zip），提供：
- `start_connection(ws)` / `finish_connection(ws)`
- `start_session(ws, payload, session_id)` / `finish_session(ws, session_id)`
- `task_request(ws, payload, session_id)`
- `receive_message(ws)` / `wait_for_event(ws, msg_type, event_type)`

### ⚠️ 协议库 Bug（必须修复）

官方 `protocols_.py` 的 `_get_writers` 和 `_get_readers` 中，`WithEvent` 标志位用了等值比较而非位运算。服务器发送音频时组合 `LastNoSeq | WithEvent`（值 6），导致 `== 4` 失配，音频消息解析失败。

**修复**（4 处改动，见 `references/protocol-fix.patch`）：
- `self.flag == MsgTypeFlagBits.WithEvent` → `self.flag & MsgTypeFlagBits.WithEvent`
- `self.flag in [PositiveSeq, NegativeSeq]` → `(self.flag & 0b11) in [PositiveSeq, NegativeSeq]`

## 关键 Payload 格式

### ✅ 正确（TaskRequest）
```json
{
  "req_params": {
    "speaker": "zh_female_xiaohe_uranus_bigtts",
    "audio_params": {"format": "mp3", "sample_rate": 24000},
    "text": "你好世界"
  }
}
```

### ❌ 错误
```json
{"text": "你好世界"}
```

**`text` 必须放在 `req_params` 里面，且 `req_params` 必须包含完整的 speaker 和 audio_params。**

## 完整流程

```
1. websockets.connect(URL, additional_headers={X-Api-Key, X-Api-Resource-Id}, max_size=10*1024*1024)
2. start_connection(ws) → wait_for_event(ConnectionStarted)
3. start_session(ws, payload, session_id) → wait_for_event(SessionStarted)
4. task_request(ws, payload, session_id) → 接收 AudioOnlyServer 音频块
5. finish_session(ws, session_id)
6. finish_connection(ws)
```

## 音色选择

**默认音色：小何 2.0**（`zh_female_xiaohe_uranus_bigtts`），自然度最高。

2.0 模型所有已测试音色（详见 [音色列表](https://www.volcengine.com/docs/6561/1257544)）：

| 音色名 | voice_type | 风格 |
|--------|-----------|------|
| **小何 2.0**（默认）| `zh_female_xiaohe_uranus_bigtts` | 通用女声 |
| 清新女声 2.0 | `zh_female_qingxinnvsheng_uranus_bigtts` | 清新自然 |
| 魅力女友 2.0 | `zh_female_meilinvyou_uranus_bigtts` | 亲切温柔 |
| Vivi 2.0 | `zh_female_vv_uranus_bigtts` | 通用女声 |
| 暖阳女声 2.0 | `zh_female_kefunvsheng_uranus_bigtts` | 客服风格 |
| 小天 2.0 | `zh_male_taocheng_uranus_bigtts` | 通用男声 |
| 云舟 2.0 | `zh_male_m191_uranus_bigtts` | 通用男声 |

## 飞书发送语音消息

语音合成后通过 lark-cli 发送到飞书：

```bash
# 1. 合成 → MP3（用 Python 脚本）
python3 synthesize.py "要说的文字" -o /tmp/tts.mp3

# 2. MP3 → Opus（飞书语音消息必须 Opus 格式）
ffmpeg -y -i /tmp/tts.mp3 -c:a libopus -b:a 16k /tmp/tts.opus

# 3. 发送（必须用相对路径，且在文件所在目录执行）
cd /tmp && lark-cli im +messages-send --as bot --chat-id <chat_id> --audio tts.opus
```

## 计费

- **试用**：20,000 字符，半年有效。在控制台点「**试用**」（不是「开通服务」）
- **正式版**：按字符计费，需账户有余额
- 「开通服务」会把试用额度覆盖为正式版，没余额会返回 `code:20000000, data:null`

## 常见错误

| 错误 | 原因 |
|------|------|
| `code:20000000, data:null` | 正式版余额为 0 或试用额度已用完 |
| `45000030 requested resource not granted` | API Key 未授权该 Resource ID |
| `55000000 resource ID mismatch` | speaker 和 resource_id 不匹配（如 2.0 speaker 配 seed-tts-1.0） |
| HTTP 401 | 鉴权 Key 类型错误（大模型 Key ≠ 语音 Key） |
| HTTP 403 | 豆包语音服务未开通 |
| `decode ws request failed` | 发送了纯文本 JSON 而非二进制协议帧 |

## 🚨 脚本集成陷阱（2026-07-17 实战排坑）

### `.env` 文件尾部注释陷阱

`.env` 解析器（`line.split("=", 1)`）会把 `=` 后整行作为值，包括 `#` 注释：

```
# ❌ 错误 — speaker 变成 "zh_female_xiaohe_uranus_bigtts  # 小何 2.0"
DOUBAO_TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts  # 小何 2.0

# ✅ 正确
DOUBAO_TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts
```

**症状**：API 返回 `55000000 resource ID mismatch` 或无音频。**排查**：`print()` `.env` 加载后的实际值，确认无注释污染。

### `asyncio.run()` 主线程阻塞

在同步主线程中调用 `asyncio.run(doubao_tts())` 会卡在 `synthesizing` 阶段。**同一 TTS 代码用子进程正常，脚本内 asyncio 阻塞。**

**修复: 子进程隔离**：

```python
result = subprocess.run([
    sys.executable, "-c", f"""
import asyncio, json, uuid
from doubao_tts_proto import MsgType, EventType, start_connection, ...
import websockets, copy as cp
async def tts():
    # ... standard flow (connect → session → task → collect)
    if audio: open("{out}", "wb").write(audio); print("OK")
asyncio.run(tts())
"""], capture_output=True, text=True, timeout=30)
if "OK" in result.stdout: subprocess.run(["afplay", out], timeout=30)
```

**原因**：主线程的 `while True` + PyAudio 回调与 `asyncio.run()` 事件循环冲突。子进程有独立解释器和事件循环，彻底隔离。
