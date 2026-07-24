# 飞书官方智能体入会方案

## 来源

用户分享的飞书文档：`VXnpdcUFWotAmexKWmUcAwA4nCe`
标题：「飞书语音 Agent 入会与豆包实时语音完整配置方案」

## 核心区别 vs 当前 BlackHole 方案

| | 当前 V4 方案 | 官方方案 |
|------|------|------|
| 入会方式 | MacBook 麦克风偷偷收音 | Bot 通过 API **真实入会** (`lark-cli vc +meeting-join`) |
| 音频下行 | 无（听系统外放） | ByteView WebSocket 双向音频 (24kHz PCM) |
| 音频上行 | BlackHole → 飞书麦克风（不可靠） | ByteView WebSocket → 会议原生音频 |
| 语音模型 | ASR + LLM + TTS 三段拼接 | 豆包端到端实时语音模型（一体） |
| 会议感知 | 会里其他人听不到 TTS | **全都能听到** |

## 架构链路

```
飞书会议真人语音
  ↓
飞书 ByteView Realtime WebSocket (24 kHz PCM s16le)
  ↓
本地 Starter (重采样 24kHz → 16kHz)
  ↓
豆包端到端实时语音模型 (16 kHz PCM）
  ↓
本地 Starter (重采样 16kHz → 24kHz)
  ↓
ByteView Realtime WebSocket → 会议中播放机器人语音
```

## 前置条件

1. **加入智能体入会体验群**（灰度）：https://go.larkoffice.com/join-chat/283k21f7-98e5-47dc-aecd-a339ed735166
2. **飞书应用权限**：
   - `vc:meeting.bot.join:write`（必需）
   - `vc:meeting.bot.realtime:write`（必需）
   - `vc:meeting.meetingevent:read`（可选，不建议申请）
3. **豆包凭证**：不是 TTS API，而是「豆包端到端实时语音大模型」的 APP ID / Access Token / Secret Key
4. **会议设置**：「智能会议权限」中勾选「允许智能体加入会议」
5. **飞书客户端 ≥ 最新版**，`lark-cli` 已升级

## 关键命令

```bash
# 入会
lark-cli vc +meeting-join --as bot --meeting-number <9位会议号>

# 获取 realtime endpoint
lark-cli api GET /open-apis/vc/v1/realtime/endpoint --as bot --params '{"meeting_id":"<meeting_id>"}'

# 离会
lark-cli vc +meeting-leave --as bot --meeting-id <meeting_id>
```

## ByteView WebSocket 协议要点

- Binary 消息，Frontier Frame 格式
- Protobuf 编码：`meeting_realtime.v1.ClientEvent` / `ServerEvent`
- 连接后先发 `session.create`，收到 `session.created` 后才能发音频
- 音频格式：`audio/pcm`, `s16le`, mono, 24000 Hz, 20-100ms 分片

## 豆包端到端实时语音 WebSocket

- 地址：`wss://openspeech.bytedance.com/api/v3/realtime/dialogue`
- Headers: `X-Api-App-ID`, `X-Api-Access-Key`（Access Token）, `X-Api-Resource-Id: volc.speech.dialog`, `X-Api-App-Key`（Secret Key）
- 音频：PCM, mono, 16000 Hz（输入）/ 24000 Hz（输出）
- 协议：自定义二进制帧（gzip+JSON payload）

## Starter 项目

路径：`/Users/bytedance/Documents/Codex_Project/feishu-voice-agent-starter/`

**2026-07-17 配置状态（✅ 全链路已跑通）**：
- ✅ 权限 `vc:meeting.bot.join:write` — 已授权
- ✅ 权限 `vc:meeting.bot.realtime:write` — 已授权（实测可用）
- ✅ 豆包凭证：APP ID `2353725770`，Access Token `oGEkgN96mlQA0XxJG4WNJwrv-SEbJwhj`，App Key `PlgvMymc7f3tQnJ6`
- ✅ 协议版本：`VersionBits.Version1`（V3 被拒）
- ✅ `--check` 通过
- ✅ 飞书应用：`cli_a964fd626078dcbc`
- ✅ 体验群：用户已加入「智能体入会体验群」

**申请 realtime 权限**：打开 https://open.feishu.cn/page/scope-apply?clientID=cli_a964fd626078dcbc&scopes=vc%3Ameeting.bot.realtime%3Awrite
## 使用方式

```bash
cd ~/Documents/Codex_Project/feishu-voice-agent-starter

# 检查配置
python3 main.py --check

# 自动检测活跃会议并入会（2026-07-17 已融合 V3 auto_detect_meeting）
# 不需要传 --meeting-no，脚本自动用 +meeting-list-active 检测
python3 main.py

# 或手动指定会议号
python3 main.py --meeting-no <9位会议号>
```

**文件清单**（14 个文件）：
- `main.py` — 主流程
- `config.yaml` — 真实凭证（不提交 git）
- `persona.md` — 人设
- `voice_agent/config.py` — 配置解析
- `voice_agent/lark_cli.py` — lark-cli 封装
- `voice_agent/byteview_protocol.py` — ByteView protobuf 协议
- `voice_agent/byteview.py` — ByteView WS 桥接
- `voice_agent/doubao_protocol.py` — 豆包二进制协议
- `voice_agent/doubao.py` — 豆包实时语音客户端
- `voice_agent/audio_utils.py` — PCM 重采样
- `voice_agent/ws_compat.py` — websockets 版本兼容
- `voice_agent/logging_utils.py` — 日志
- `voice_agent/__init__.py`

## 排障速查

| 错误 | 原因 | 解决 |
|------|------|------|
| `unknown command "+meeting-join"` | lark-cli 命令缺 `vc` 子命令前缀 | 用 `lark-cli vc +meeting-join` 而非 `lark-cli +meeting-join`。同理 `vc +meeting-leave`、`vc +meeting-events` |
| `field validation failed` (99992402) on realtime endpoint | `--params` 缺 `meeting_id` | 必须传 `--params '{"meeting_id":"<id>"}'` |
| `app_scope_not_applied` (99991672) | 缺 `vc:meeting.bot.realtime:write` 权限 | 去开发者后台申请 scope（见上方"申请 realtime 权限"链接） |
| ErrNotInGray / 20017 | 未进灰度 | 加体验群 |
| app has not applied for scope | 应用权限未申请 | 开放平台申请 + 发布 |
| user lacks permission | 数据范围不覆盖 | 配置可访问数据范围 |
| 豆包 401 | 用了错误的 Access Token | 用「服务接口认证信息」的 Access Token，非 AK/SK |
| 🚨 `unsupported protocol version 3` | `protocols.py` 版本号用了 V3 | **改回 `VersionBits.Version1`**。V3 被服务端拒绝 |
| 🚨 `invalid X-Api-App-Key` (45000001) | App Key 与服务端注册的不一致 | 检查豆包控制台「服务接口认证信息」→ Secret Key。服务端返回的 `expected:[...]` 就是正确值 |
| 🚨 `quota exceeded for types: qpm` (45000292) | 短时间内重连太多次，触发豆包 QPM 限流 | 等 30-60 秒再试。正常使用不会触发，测试时注意间隔 |
| 🚨 Bot 说话没人听到 | `main.py` 中 `say_text()`（开场白）在 forward tasks 启动之前调用 → TTS 音频回来时没人监听 WebSocket → 丢失 | **把 `say_text()` 移到 `asyncio.create_task` 之后**，并加 `await asyncio.sleep(0.2)` 确保 forward 任务已经开始监听 |
| websockets extra_headers | websockets 15 API 变更 | 用 `additional_headers` / Starter 已兼容 |

### 🚨 `lark_cli.py` Starter 代码已知 Bug（2026-07-17 已修）

子 Agent 生成的 `voice_agent/lark_cli.py` 有四处调用错误：

1. `join_meeting()` — 用了 `+meeting-join`，应为 `vc +meeting-join`
2. `leave_meeting()` — 用了 `+meeting-leave`，应为 `vc +meeting-leave`
3. `meeting_events()` — 用了 `+meeting-events`，应为 `vc +meeting-events`
4. `realtime_endpoint()` — 方法签名不接受 `meeting_id` 参数，需加参数并传 `--params '{"meeting_id":"<id>"}'`

此外 `main.py` 需从 realtime_endpoint 返回的 `data.websocket_url` 提取 WebSocket URL（返回结构：`{"ok":true,"data":{"websocket_url":"wss://...","expires_time":"..."}}`）。

### 🚨 `doubao_protocol.py` 协议格式完全错误（2026-07-17 已替换）

子 Agent 自造的 `doubao_protocol.py` 使用了完全错误的二进制帧格式：

- ❌ 自造格式：`[version:1][type:1][header_size:2][payload_size:4][header_json][payload]`
- ✅ 官方格式：`[(version<<4)|header_size:1][(type<<4)|flag:1][(serialization<<4)|compression:1][padding to 4×header_size][event:4][session_id_len:4][session_id][payload_len:4][payload]`

**修复方案**：下载官方协议库 `protocols_.py`（来自 `https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_5ec6e28945592c909158dc1e2cf9a89c.zip`），应用以下修复后替换自造协议：

1. **版本号**：**必须是 `VersionBits.Version1`，不要改！** ⚠️ 2026-07-17 实测：`Version3` 被服务端拒绝（`unsupported protocol version 3`），`Version1` 正常通过。
2. **位运算 bug（4 处）**：`==` 比较 → `&` 位运算（`WithEvent` 标志位 和 `PositiveSeq`/`NegativeSeq` 序列位）——否则服务器 `LastNoSeq | WithEvent = 6` 的消息解析失败
3. **websockets 类型引用**：删除所有 `websockets.WebSocketClientProtocol` 类型标注
4. **SAY_HELLO**：需用 `TaskRequest`（event_id=200）而非独立事件类型；`text` 放在 `req_params.text` 中

**`doubao.py` 配套修改**：
- 使用 `protocols.py` 的 `Message`/`MsgType`/`start_connection`/`start_session`/`task_request`
- `send_audio()` 用 `AudioOnlyClient` 消息类型
- `receive_audio()` 解析 `AudioOnlyServer`（type=0x0B）获取 TTS 音频
- `_raise_for_error` 检查 `msg.type == MsgType.Error`

### 🚨 豆包凭证混淆陷阱（2026-07-17 踩坑）

豆包有**三套不同的凭证体系**，不能混用：

| 凭证类型 | 端点 | 用途 | 来源 |
|---------|------|------|------|
| **TTS API Key** | `v3/tts/bidirection` | 单句 TTS | 「API Key 管理」里的 Key |
| **实时语音凭证** | `v3/realtime/dialogue` | 端到端实时语音 | 「服务接口认证信息」的 APP ID + Access Token + Secret Key |
| **通用 AK/SK** | 其他服务 | 非语音用途 | 「访问控制 → API访问密钥」 |

**绝对不要把 TTS 的 `X-Api-Key` 填进实时语音的 `X-Api-Access-Key`。** 实时语音需要三字段：`X-Api-App-ID`、`X-Api-Access-Key`（= Access Token）、`X-Api-App-Key`（= Secret Key）。控制台路径：豆包语音 → API服务中心 → 豆包端到端实时语音大模型 → 服务接口认证信息。