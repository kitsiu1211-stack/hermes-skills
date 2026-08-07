---
name: meeting-audit
description: 飞书会议能力全集 — 静默旁听字幕/聊天，或入会语音对话（ByteView + 豆包实时语音）。Agent 按需选择静默或发言模式。
category: productivity
version: 1.0.0
---

# 飞书会议旁听（Meeting Audit）

通过 lark-cli 以用户身份旁听飞书会议，实时获取字幕、聊天、参会人动态。适合会议纪要、实时问答、背后支援型 Agent。

---

## 🚨 Agent 执行指令（必读，违反即为 Bug）

### ⚠️ 旁听触发机制说明

**飞书不会因为你拉 Agent 进会议就主动推送事件**。Agent 是纯消息驱动的——只有用户发消息，Agent 才会动。拉入会议这件事本身不会变成一条消息触达 Agent。

因此：**用户拉 Agent 进会 ≠ Agent 自动开始旁听。** 用户必须在聊天中明确告知（「开始旁听」「我开会了」「监听会议 XXX」），Agent 才能启动 cronjob 轮询。

不要在不知道有会议的情况下假装在旁听。如果用户说「会议结束了，监听到什么？」但 Agent 并未被通知开始旁听（无 cronjob 运行中），应如实告知未旁听，并建议下次提前通知或设常驻 cronjob。

## 旁听执行

- 脚本：`listen_subtitles.py`（见 `references/listen-script-architecture.md`）
- lark-cli 全面替代 browser：见 `references/lark-cli-guide.md`
- 跨 RM AI 商机盘点：见 `references/ai-quota-review-methodology.md`
- 旁听脚本架构与演进：见 `references/listen-script-architecture.md`

### 执行步骤

1. **查活跃会议**：`lark-cli vc +meeting-list-active --as user --jq '[.data.meetings[] | {title: .meeting_title, no: .meeting_no}]'`
2. **启动旁听**：`cd ~/Documents/Codex_Project/feishu-voice-agent-starter && python3.11 listen_subtitles.py`
3. **多会议并行**：第二个会需传 meeting_id：`python3.11 listen_subtitles.py <meeting_id>`
4. **脚本自动处理**：不入会轮询 → 增量保存 → 会结束自动出纪要
5. **无需 cronjob**——脚本内建 `meeting_still_active()` 双重验证（API超时不误判），`notify_on_complete=true` 通知 Agent

### 触发机制（用户偏好）

**手动触发，非自动检测。** 用户通过发"旁听会议""监听会议"到聊天来通知 Agent 开始旁听。

原因：飞书不会推送会议事件给 Agent，Agent 是纯消息驱动的。用户拉 Agent 入会 ≠ Agent 感知到入会。只有用户主动发消息（"监听会议"），Agent 才能启动轮询。

### 为什么是 cronjob

`execute_code` 里的 `while True` 循环会在用户发新消息时被中断。只有 cronjob 能保证持续轮询到会议结束。

---

## 前置条件

- 飞书客户端 ≥ 7.68
- lark-cli ≥ v1.0.55（`npm install -g @larksuite/cli@latest`）
- 用户 UAT 已授权 scope `vc:meeting.meetingevent:read`（`lark-cli auth login`）
- **灰度资格**：需加入早鸟体验群
- 每场会议由 owner 在安全设置中开启「允许智能体入会」（找不到先开 AI 总结）

**⚠️ Token 分离**：`lark-cli` 和 `feishu-cli` 的 UAT token 是独立存储的。会议旁听用 lark-cli，会后发消息用 feishu-cli。需要分别检查 `lark-cli auth status` 和 `feishu-cli auth status`，按需单独授权。

**⚠️ 文档搜索权限**：会后在飞书知识库搜材料需要额外 scope `search:docs:read`，与会议旁听 scope 不共享。首次使用需单独授权：`lark-cli auth login --scope "search:docs:read" --no-wait --recommend --json`。

## 核心命令

> 旁听脚本 `listen_subtitles.py` 的完整架构与演进历史见 `references/listen-script-architecture.md`。

### 0. Bot 加入会议

```bash
lark-cli vc +meeting-join --meeting-number <9位会议号> --as bot --json
```

⚠️ **必传 `join_type=1`**（lark-cli `+meeting-join` 已内置该参数，无需手动传）。返回 `data.meeting.id`（长 ID，用于后续事件拉取）和 `data.meeting.meeting_no`。

**注意**：Bot 加入 ≠ 用户本人在会中。拉事件仍需要用户在会中（`--as user`）。Bot 入/离会只支持 Tenant Token。

## 🆕 官方推送式独立入会（2026-07-25）

飞书官方文档提供了**推送式**独立入会方案，对比旧有的轮询式方案有显著优势。

### 能力层级

| 能力 | 事件接收方式 | 开通方式 |
|------|------------|---------|
| **旁听模式** | 轮询 `ListMeetingEvents`（`--as user`） | 全量开放 |
| **独立入会** | 🆕 推送订阅 `vc.bot.meeting_activity_v1` | 早鸟灰度 |
| **语音互动** | 同上 | 小范围共创（申请表单） |

### 独立入会的推送事件

旧方案轮询 `+meeting-events` 有三大痛点：10s 间隔易限流、正式会议常返回空、间隔之间漏消息。

官方方案通过**事件订阅**实现推送（不用轮询）：

| 事件 | 用途 |
|------|------|
| `vc.bot.meeting_invited_v1` | Bot 被邀请入会 → 可自动 join |
| `vc.bot.meeting_ended_v1` | 会议结束 → 准确感知，不依赖轮询检测 |
| `vc.bot.meeting_activity_v1` | 字幕/聊天/参会人变化/共享文档 → 5s/100条聚合推送 |

### 前置条件

- 飞书应用开启「机器人」能力
- 权限：`vc:meeting.bot.join:write` + `vc:meeting.meetingevent:read`（均应用身份）
- 事件订阅：在开发者后台声明上述 3 个事件
- 飞书客户端 ≥ 7.68，lark-cli ≥ v1.0.55
- 会议开启「允许智能体入会」

### 事件订阅配置链接

一键生成配置链接（Node.js）：

```js
import { gzipSync } from 'node:zlib';
const payload = {
  scopes: { tenant: ["vc:meeting.bot.join:write", "vc:meeting.meetingevent:read"] },
  events: { items: { tenant: ["vc.bot.meeting_invited_v1", "vc.bot.meeting_ended_v1", "vc.bot.meeting_activity_v1"] } }
};
const encoded = gzipSync(JSON.stringify(payload)).toString("base64").replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
console.log(`https://open.feishu.cn/page/launcher?clientID=${appId}&addons=${encoded}`);
```

### 外层包装结构（独立入会专属）

推送事件的 `vc.bot.meeting_activity_v1` 外层包裹：

```json
{
  "meeting_activity_items": [{
    "meeting": { "id": "xxx", "meeting_no": "123456789", "topic": "周会" },
    "activity_event_type": "transcript_received",
    "transcript_received_items": [...]
  }]
}
```

按 `activity_event_type` 读对应数组：`transcript_received_items` | `chat_received_items` | `participant_joined_items` | `participant_left_items` | `magic_share_started_items`

### 接入流程

```
用户发起会议 + 开「允许智能体入会」
    ↓
飞书推送 vc.bot.meeting_invited_v1 事件（响铃）
    ↓
Agent 收到事件，调用 BotJoinMeeting 入会 → 获得 meeting_id
    ↓
开始接收 vc.bot.meeting_activity_v1 实时事件（无需轮询！）
    ↓
会议结束收到 vc.bot.meeting_ended_v1，或主动 BotLeaveMeeting 离会
```

### 对比：轮询 vs 推送

| | 旧方案（轮询） | 官方方案（推送） |
|--|-------------|-------------|
| 字幕延迟 | 3-10s | ≤5s（5s/100条聚合） |
| 限流风险 | 99991400 | 无 |
| 正式会议 | 常返回空 | 稳定推送 |
| 会议结束感知 | 轮询检测（滞后） | 实时事件 |
| Bot 被邀请 | 无感知 | 自动推送 |
| 共享文档 | 不支持 | `magic_share_started` |

### 1. 查询用户当前活跃会议

```bash
lark-cli vc +meeting-list-active --as user
```

返回 `data.meetings[]`，每项含 `meeting_id`, `meeting_no`, `meeting_title`。多个会议时让用户选一个。

### 2. 拉取会中事件

```bash
lark-cli vc +meeting-events --as user --meeting-id <meeting_id> --page-all
```

或增量拉取（用上次返回的 `page_token`）：

```bash
lark-cli vc +meeting-events --as user --meeting-id <meeting_id> --page-token <token>
```

**注意**：UAT 场景无实时推送，需要轮询拉取（建议间隔 3-5 秒）。

## 事件结构

每个事件有两层：外层是事件元信息，内层 `payload` 是实际数据。

```json
{
  "event_id": "abc5aa10-8b43-44e0-8133-33289578d9fa:0",
  "event_time": "2026-07-04T21:25:33+08:00",
  "event_type": "participant_joined",
  "payload": {
    "activity_event_type": "participant_joined",
    "meeting": { "id": "7658508485941136604", "topic": "...", ... },
    "participant_joined_items": [...]
  }
}
```

**访问路径**：`event["payload"]["activity_event_type"]` → 判断类型 → `event["payload"]["xxx_items"]` → 取数据。

### `transcript_received` — 字幕

`payload.transcript_received_items[]`：

```json
{
  "speaker": {"id": "xxx", "user_name": "张三", "user_type": 1, "user_role": 0},
  "text": "今天来讨论一下这个方案",
  "language": "zh_cn",
  "start_time_ms": "2026-07-04T21:26:33+08:00",
  "end_time_ms": "2026-07-04T21:26:34+08:00",
  "sentence_id": "1783171611815416209"
}
```

- `language` 使用下划线：`zh_cn`（非 `zh-CN`）
- `speaker.user_role`: 0=普通发言者, 2=主持人
- `user_type` 可能为声纹检测类型（100/101/102），需兼容

### `chat_received` — 会中聊天

`payload.chat_received_items[]`：

```json
{
  "operator": {"id": "xxx", "user_name": "张三"},
  "message_id": "om_xxx",
  "message_type": 1,
  "content": "大家好",
  "send_time": "1716699030000"
}
```

`message_type`：1=文本，2=系统，3=表情，4=加密。

### `participant_joined` — 参会人进入

`payload.participant_joined_items[]`：

```json
{
  "participant": {"id": "xxx", "user_name": "张三", "user_type": 1, "user_role": 2},
  "join_time": "2026-07-04T21:25:33+08:00"
}
```

`user_role`：2=主持人，1=普通参会人。

### `participant_left` — 参会人离开

`payload.participant_left_items[]`：

```json
{
  "participant": {"id": "xxx", "user_name": "张三"},
  "leave_reason": 1,
  "leave_time": "1716700000000"
}
```

`leave_reason`：1=主动离会，2=会议结束，3=被踢出。

## 事件处理参考（供 cronjob agent 使用）

Cronjob agent 直接调用 `poll.py` 脚本获取增量事件，无需自己实现轮询逻辑：

```bash
python3 ~/.hermes/skills/productivity/meeting-audit/scripts/poll.py <meeting_id>
```

**输出 JSON 结构：**
```json
{
  "events": [
    {
      "event_id": "abc:0",
      "items": [
        {"type": "transcript", "speaker": "张三", "text": "今天讨论方案"},
        {"type": "chat",     "sender": "李四", "content": "发了个文件"},
        {"type": "joined",   "name": "王五", "role": "主持人"},
        {"type": "left",     "name": "赵六", "reason": "主动离会", "reason_code": 1}
      ]
    }
  ],
  "meeting_ended": true  // true = 检测到会议结束
}
```

无新事件时返回 `{"events":[],"meeting_ended":false}`。

**Cronjob agent 逻辑：**
1. 运行 `poll.py <meeting_id>` 获取 JSON
2. `events` 为空 → 静默退出（不发消息）
3. `events` 非空 → 格式化为卡片发给用户
4. `meeting_ended: true` → 发「会议已结束」卡片 + `cronjob remove <自己>`

`poll.py` 自动维护状态文件 `~/.hermes/meeting_state/<meeting_id>.json`，确保不重复汇报。

## 排查清单

| 问题 | 原因 | 解决 |
|------|------|------|
| 拉事件报 120002 `switch disabled` | 会议未开「允许智能体入会」，或开关开了但对已有会议不生效 | **脚本立即退出**，打印 `[无法旁听] 智能体不可入会 (错误 120002)`，不再空转轮询。原因告知用户后可开新会重试 |
| 拉事件报 120003 `user is not in the meeting` | 用户已离会/会议已结束 | poll.py v1.0.1+ 已处理：返回 `meeting_ended: true`。**不要再手动调 `+meeting-events`**——poll.py 内部会优雅降级 |
| 拉事件报无权限 | 用户不在会，或 UAT 过期 | `lark-cli auth login --no-wait --recommend --json` 重新授权 |
| meeting_id 用错 | 用了 9 位会议号 | 用 `+meeting-list-active` 查到的长 ID |
| 拿不到实时字幕 | 旁听模式无推送 | 正常，需轮询调 `+meeting-events` |
| 字幕提取为空 | 用了旧字段名 `transcript_items` | **已修正**：正确字段是 `transcript_received_items` |
| `--as user` 报 unknown flag | lark-cli 版本过老 | `npm install -g @larksuite/cli@latest` |
| `+meeting-leave` 报 121104 `meeting status unexpected` | 会议已结束（用户离开后会议自动终止） | 直接加入新会议即可，无需先离开旧会议 |
| 连续多个会议邀请 | 用户在同一会话中多次发起会议 | 直接 `+meeting-join` 新会议号，无需先离开上一个（上一个大概率已结束） |
| **把案例当客户** | 从字幕内容推断客户名（如听到"拓竹"就以为客户是拓竹） | **铁律：客户名以会议标题为准，不从字幕内容推断。** 会议标题不写客户名就按标题出纪要，不要自作主张猜客户。案例引用 ≠ 客户身份 |
| **ByteView 无音频流** | 会议未启用实时音频；或 Bot 入会后启动 Agent 太快 | 先 `sleep 3` 等 Bot 就绪再启动。5 秒内无 `raw msg` → 降级到字幕旁听+聊天框文字。个人通话（标题含「通话」）Bot 无法入会。 |
| **API超时误判会议结束** | `+meeting-events` API调用超时返回空，脚本累加到4轮判结束 | **已修复**：listen_subtitles.py 新增 `meeting_still_active()` 双重验证——连续空返回后先调 `+meeting-list-active` 确认会议是否真的不在活跃列表。会议还在则继续轮询（日志：[API 静默 N 轮，会议仍在进行]），真正不在了才判结束。最多等 12 轮确保收尾字幕不丢 |

## Agent 入会语音对话（ByteView + 豆包实时语音）

当用户需要 Agent **在会中发言**（非静默旁听）时，使用 ByteView 实时音频桥接 + 豆包端到端语音方案：

### 架构

```
用户说话 → 飞书会议音频 → ByteView WebSocket → 豆包 ASR → Hermes 思考 → 豆包 TTS → ByteView WebSocket → 会议扬声器
```

**不走系统音频设备（非 BlackHole）**——全程通过 WebSocket 数字桥接，延迟更低、更稳定。

详细指南见 `references/voice-agent-guide.md`。

### 启动命令

```bash
cd ~/Documents/Codex_Project/feishu-voice-agent-starter

# 1. Bot 入会
lark-cli vc +meeting-join --meeting-number <9位会议号> --as bot

# 2. ⚠️ 等 3 秒再启动 Agent（Bot 入会到 ByteView 就绪有延迟，不等会导致无音频流）
sleep 3

# 3. 启动语音管线
python3.11 main.py --config config.yaml --meeting-no <9位会议号> --keep-in-meeting --poll-events
```

前置条件：
- `config.yaml` 已配置豆包凭证（`doubao_app_id`, `doubao_api_key`, `doubao_app_key`）
- Python 依赖：`pyyaml`, `websockets`
- ⚠️ 个人通话（标题含「XXX和XXX的通话」）Bot 无法入会，`+meeting-join` 返回 `ok: false`

### 音频可用性检测（启动后 5 秒内必须验证）

**🚨 关键**：ByteView 实时音频不是所有会议都支持。启动后立即检查日志：

```
# ✅ 正常 — 有 raw msg 流量
[bv] raw msg idx=1 raw_len=5354

# ❌ 无音频 — 5 秒内没有 raw msg → 降级方案
```

**降级方案**：无音频流时，Kill 语音 Agent，切到字幕旁听 + 会议聊天框文字回复：
1. `echo '[]' > /tmp/subtitle_inbox.json && python3.11 listen_subtitles.py`
2. 用户说话 → Agent 看到字幕 → 通过 `lark-cli vc +meeting-message-send` 在会议聊天框回复

### 卡顿修复：去掉分片延迟

**🔧 根因**：`voice_agent/byteview.py` 的 `send_audio()` 将 TTS 音频按 4800 字节分片后每片 `asyncio.sleep()` 延迟发送，句子中间产生真空期导致卡顿。

**🔧 最终修复**：保留分片（ByteView 协议要求 4800 字节帧），但**去掉 delay**——连续快速发出，WebSocket 自行处理流控。

```python
# ✅ 修复后 — 分片但不延迟，连续发送
async def send_audio(self, audio: bytes) -> None:
    if self.ws is None:
        raise MissingRealtimeEndpoint("ByteView WebSocket is not connected")
    if not self.session_id:
        raise MissingRealtimeEndpoint("ByteView session is not created")
    for chunk in split_pcm_s16le(audio):
        _, frame = build_audio_upstream_append_frame(self.session_id, chunk)
        await self.ws.send(frame)
```

**试错的坑**：
- ❌ 尝试改 sleep 采样率（48k→16k 或反过来）→ 无效果
- ❌ 尝试增大分片到 19200 字节 → ByteView 服务端静默丢弃，完全无声
- ❌ 整段发不拆 → 同上
- ✅ 分片 4800 + 无延迟 → 流畅

**豆包 TTS 实际参数**：24kHz s16le mono（doubao.py 第 177 行 `"sample_rate": 24000`），非 16kHz。

### 配置参考

```yaml
# config.yaml 关键字段
doubao_app_id: "2353725770"
doubao_api_key: "<key>"
doubao_app_key: "<key>"
doubao_voice: "zh_female_vv_jupiter_bigtts"
doubao_model: "1.2.1.1"
```

## 持久化轮询（唯一方案）

`execute_code` 中的 `while True` 循环在用户发新消息时会被中断 → **不可靠**。只有 cronjob 能保证持续轮询到会议结束。

### Cronjob 自动停止逻辑

会议结束时（`participant_left` 事件 `leave_reason == 2` 或 `+meeting-list-active` 查不到会议），cronjob agent 应：

1. 发「🔴 会议已结束」卡片给用户
2. 提取会上用户的「会后给 XX 发 YY」指令，告知会后会处理
3. **删除自己**：`cronjob remove <自己的 job_id>`（从 cronjob list 中获取）

## 会后跟进

用户在会议中自布置的任务（如「会后给 XX 发材料」），Agent 应在检测到会议结束后自动执行。

### 能力矩阵

| 场景 | 能力 | 实现 |
|------|:---:|------|
| **2a** 会后把材料发给用户 | ✅ | `feishu-cli exec im.v1.message.create` 发 DM |
| **2b** 直接发给会中提到的人 | ✅ | 同上，target 改为对方的 open_id/chat_id |
| **2c** 在知识库找材料 → 发给客户 | ✅ | `lark-cli docs +search` → 找到文件 → IM 发送 |
| 关联 CRM 信息 | ✅ | C360 CLI（`lark-cli c360`），下次会议结合旁听内容使用 |
| 内部协调（拉群、发消息） | 保留 | 有场景时启用 |

### 2c 文档搜索

在飞书文档/Wiki 中搜索材料，找到后直接发给客户：

```bash
# 搜索飞书文档（需 search:docs:read scope）
lark-cli docs +search --query "飞连" --page-size 10 --as user
```

**⚠️ 文档搜索需要独立的 scope `search:docs:read`**，与会议旁听的 `vc:meeting.meetingevent:read` 不共享。首次使用需重新授权：

```bash
lark-cli auth login --scope "search:docs:read" --no-wait --recommend --json
# → 获取 verification_url → 发给用户扫授权 → 用 device_code 完成
```

### 会后执行清单

会议结束时（`leave_reason == 2` 表示会议结束），Agent 应：
1. 回顾捕获的字幕，提取用户的「会后给XX发YY」类指令
2. **不要生成会议纪要**——飞书会议已自动生成
3. 对于需要材料的：按材料类型走不同路径（见下方）
4. 所有发完后，给用户一个简要汇总卡片

**材料获取路径：**

| 材料类型 | 获取方式 |
|------|------|
| ISV 产品材料（飞连/帆软/北森等） | Agent协作群 @ISV助手 → 查线程回复 → 发链接给用户 |
| 飞书实践/案例/方案（行业最佳实践、客户案例、应用场景等） | Agent协作群 **@样板间小管家** → 查线程回复 → 发链接给用户。🚨 **禁止自己搜 docs**——样板间是案例弹药库，专业对口，比自己搜更准、更快 |
| 其他非 ISV 材料 | `lark-cli docs +search` 搜飞书文档 → 发链接给用户（仅当样板间也覆盖不到时使用） |
| 本地文件 | 直接发链接，**不下载不上传** |

> **核心原则**：直接发链接，不要下载后再上传。节省 token、提升效率。能 @ 专业 Agent 就不要自己搜。

## 会后行动工作流

### ISV 材料获取

当用户在会议上提出 ISV 相关需求（材料、案例、话术），会后去 **Agent 协作群**（chat_id: `oc_219a613c13292855c2dc4b80e59dfd6e`）@南区 ISV 业务助手（app_id: `cli_aaa06c74f1f89bcb`），助手已集成：

- **合作商材料**：各 ISV 产品的对客介绍、解决方案
- **客户案例**：已成交客户清单、行业案例
- **对客话术**：面向客户的沟通话术、产品推荐话术

**@ISV助手后收回复的关键步骤：**

ISV 助手会回复但无法 @ Bot。需要在发消息后监听线程：

1. 用 `feishu-cli exec im.v1.message.create` 发 **post 消息**（必须带 at 元素，纯文本 @ 不触发）
2. 从返回的 `message_id` 拉取群消息找到 `thread_id`
3. 等待 5-10 秒
4. `lark-cli im +threads-messages-list --as user --thread <thread_id> --page-size 50` 拉取线程回复（⚠️ 不支持 `--page-all`，用 `--page-size`）
5. 卡片中的链接可能藏在按钮里（文本不可见），需结合 `lark-cli docs +search` 补全链接
6. 拿到后**直接发链接给用户**，不下载不上传

发消息代码模板：
```python
import json, subprocess

FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"
content = json.dumps({
    "zh_cn": {
        "title": "ISV 材料请求",
        "content": [[
            {"tag": "at", "user_id": "ou_abdda0c6cd5e362bca041cb3dbd88f86"},
            {"tag": "text", "text": " 客户需要XX的最新对客材料，麻烦发一下，谢谢！"}
        ]]
    }
}, ensure_ascii=False)

payload = json.dumps({
    "params": {"receive_id_type": "chat_id"},
    "data": {"receive_id": "oc_219a613c13292855c2dc4b80e59dfd6e", "msg_type": "post", "content": content}
})
subprocess.run([FEISHU_CLI, "exec", "im.v1.message.create", "--params", payload], timeout=15)
```

> ISV 关键词：北森、飞连、帆软、PLM、鲸采云、分贝通、易点易动、汇联易、参数领航、新核云、黑湖、纷享销客等属于飞书 ISV 生态产品。

### 飞书实践/案例材料获取

当用户在会议上提到「飞书最佳实践」「行业案例」「XX客户怎么用飞书」等需求时，会后去 **Agent 协作群** @大湾区样板间专项小管家（open_id: `ou_459dac1c298c48d280a3ea3260aac80e`），小管家已集成：

- **📚 案例弹药库**：各行业客户案例、飞书应用场景
- **🏠 样板间专项**：样板间建设方案、最佳实践
- **🌟 许愿助理**：按需生成定制化方案

🚨 **禁止自己用 `lark-cli docs +search` 搜飞书实践材料**——样板间小管家是专业案例弹药库，比自己搜索更精准、更权威。只有在样板间也覆盖不到时才考虑自己搜。

@样板间小管家流程与 @ISV 助手相同（见上方 ISV 材料获取的 post 消息模板，替换 open_id 和文案即可）。

### 🎯 材料筛选整理（🚨 核心步骤，不做就是搬运工）

**从专业 Agent（ISV 助手 / 样板间小管家）拿到材料后，禁止直接转发。必须先筛选再交付。**

Agent 给的材料往往是「大而全」的，但客户需求是具体的。Agent 已旁听了整场会议，清楚客户说了什么、痛点是什么、行业是什么、规模多大——这些都是筛选的依据。

**🚨 三条铁律（违反即为 Bug）：**

1. **无链接不发**：案例/材料必须附带可访问的文档链接。没链接的条目（如「高驰 COROS — 待挖掘」只有名字没有文档）直接丢弃，不能让客户看到一个名字却看不到内容。
2. **不自行加料**：只交付用户明确要求的内容。用户没提到的类别（如竞品对比、钉钉对比等），哪怕样板间也一并给了，一律不放入交付卡片。
3. **精选 1-3 条**：从 N 条中只保留最匹配的，每条标注匹配理由。其余丢掉——「多总比少好」是搬运工思维。

**筛选框架（三步走）：**

1. **回顾会议上下文**：客户是谁？什么行业？什么规模？会上提到了什么具体需求/痛点？
2. **逐条匹配**：拿到的每条材料，问自己：这个案例/方案跟这个客户有关吗？场景匹配吗？规模可比吗？
3. **精选 1-3 条**：只保留最匹配的材料，标注为什么选它（一句话匹配理由），其余丢掉

**输出格式（发给用户时）：**

```
📌 客户需求：[一句话回顾会上提到的需求]
🎯 筛选结果（从 N 条中精选 M 条）：

1. [材料名称] → 为什么匹配：[理由]
2. [材料名称] → 为什么匹配：[理由]

❌ 未选用：[简要说明哪些没用以及为什么]
```

**反面案例（搬运工行为）：**
- 直接转发 ISV 助手/样板间小管家的整张卡片
- 把所有案例都列出来让用户自己选
- 不做任何裁剪，觉得「多总比少好」

**正面案例（思考后交付）：**
- 客户是消费电子出海品牌，提到供应链管理痛点 → 从样板间给的 6 个案例中只选传音（供应链协同）和安克（审批提效），跳过星纪魅族（售后 VOC）和矽力杰（HR招聘）
- 客户问鲸采云材料，但会上只提了 SRM 采购，没提固定资产 → 只发 SRM 方案，易点易动只附带提及

### C360 + 业务计算器（增购报价）

当用户在会议中提及客户增购/升级席位的需求时：

1. **会后查 C360**：`lark-c360 search all --keyword "客户名"` → 拿到 entity_id
2. **查订单项**：通过 raw API 查 order_item，筛选目标产品的增购记录：
   ```bash
   lark-c360 api --method POST --path /anchor/api/entity/order_item/list \
     --data '{"filter":{"relation":"AND","children":[{"field":"account_id","operator":"EQ","value":"<entity_id>"}]},"fields":["actual_unit_price","quantity","start_date","end_date","product","purchase_type"],"limit":50}' --json
   ```
   - 响应中字段直接在 item 顶层（非 `field_values` 包裹）
   - `purchase_type` 的 `display_value` 是 JSON 字符串：`{"label":"增购",...}`
   - 按 `start_date` 倒序取最新记录
3. **算剩余天数**：最新记录的 `end_date` 减去今天
4. **代入计算器**：
   ```bash
   curl -s -X POST 'https://bytedance.aiforce.cloud/app/app_4k4ex0bzsderh/openapi/calculator/calculate' \
     -H 'Authorization: Bearer OokzHETWqITNmSpEokF16moXN_eomkNlXp7iQLx1_Xs' \
     -d '{"purchaseType":"addon","unitPrice":"<price>","quantity":<N>,"effectiveDate":"<today>","expiryDate":"<end>"}'
   ```
   - `addon` 公式：单价 × 席位 × (剩余天数/365)
   - `upgrade` 公式：(升级价 - 原价) × 席位 × (剩余天数/365)
   - `unitPrice` 以用户确认为准，C360 中的 `actual_unit_price` 可能不等于标价

## 会后分析与周报

每场会议结束后，Agent 需要沉淀分析结果。每周五汇总当周所有会议，生成周报。

### 单场会议结束后的即时分析

会议结束时，从字幕中提取以下结构化信息并持久化到 `~/.hermes/meeting_analysis/`：

```json
{
  "meeting_id": "...",
  "date": "2026-07-05",
  "topic": "...",
  "attendees": ["用户", "客户A", "客户B"],
  "customer_name": "客户公司名（如有）",
  "industry": "消费电子/金融/...（推断）",
  "demands": [
    {"category": "ISV", "detail": "需要帆软 BI 方案", "source": "客户发言", "agent_covered": true, "agent": "南区 ISV 业务助手"},
    {"category": "定价/增购", "detail": "询价 500 席位增购", "source": "客户发言", "agent_covered": true, "agent": "C360 + 业务计算器"},
    {"category": "行业案例", "detail": "消费电子如何用飞书做研发协同", "source": "客户发言", "agent_covered": true, "agent": "样板间小管家"}
  ],
  "uncovered_demands": [],
  "raw_transcripts": ["..."]
}
```

**需求分类标准：**

| 类别 | 说明 | 举例 |
|------|------|------|
| ISV | 第三方产品需求 | 帆软、北森、飞连、PLM |
| 行业案例 | 客户想看同类公司怎么用飞书 | 「安克是怎么用的」 |
| AI/功能 | 飞书自身 AI 或功能需求 | 知识问答、智能纪要 |
| 定价/增购 | 报价、续约、席位增减 | 「再加 500 个席位多少钱」 |
| 安全/合规 | TRO、数据安全、GDPR | 「出海 TRO 怎么防」 |
| 技术对接 | API、集成、定制开发 | 「能不能对接我们的 ERP」 |
| 其他 | 不属以上类别 | — |

### 每周五周报生成

**触发**：每周五（cronjob 定时触发或用户手动要求）

**数据来源**：`~/.hermes/meeting_analysis/` 下当周所有 JSON 文件

**周报必须覆盖的分析维度：**

#### a. 客户需求分类

按上述 7 个类别统计，给出每类的：
- 提及次数
- 涉及客户数
- 典型例子（1-2 个）

#### b. 需求频率分析

按频率排序，标注高频词：

```
🔥 高频（≥3 次）：AI/功能 — 5 个客户提及知识库问答
⚠️ 中频（1-2 次）：ISV、定价
💤 低频（0 次）：安全/合规
```

#### c. Agent 覆盖率评估

| 需求类别 | 总次数 | Agent 覆盖 | 覆盖率 | 对应 Agent |
|----------|--------|-----------|--------|-----------|
| ISV | 5 | 5 | 100% | 南区 ISV 业务助手 |
| 行业案例 | 3 | 3 | 100% | 样板间小管家 |
| 定价/增购 | 2 | 2 | 100% | C360 + 计算器 |
| AI/功能 | 4 | 0 | **0%** | ❌ 无 |

#### d. 举例说明（正面案例）

每类 Agent 覆盖的需求，举一个真实例子：
```
✅ ISV 需求 — 客户提到帆软 → 会后自动 @ISV 助手获取材料 → 筛选后发给用户
✅ 行业案例 — 客户问消费电子实践 → @样板间小管家获取案例弹药库 → 精选匹配案例
```

#### e. 挖掘与优化 ████████ 核心输出

**e1. 新需求缺口识别**：标注 `agent_covered: false` 的需求，判断是否需要新建 Agent：
```
⚠️ 缺口：AI/功能类需求出现 4 次（知识问答、智能纪要自定义）
→ 建议：是否需要引入「AI 方案 Agent」覆盖此类需求？
```

**e2. Agent 生态补充计划**：基于缺口分析，给用户建议：
- 现有 Agent 能否通过扩展能力覆盖（如 ISV 助手能否兼答飞书功能）？
- 需要新建什么 Agent？优先级排序
- 是否有外部 Agent 可引入（如 Kimi）？

**e3. 知识整理**：从当周字幕中提取可复用的知识片段：
- 客户对某功能的准确定义/比喻（可用于后续话术）
- 竞品对比中客户说到的飞书优势/劣势
- 新的行业场景描述

**e4. 案例沉淀**：当周出现的、可纳入样板间弹药库的新案例：
```
客户 X：消费电子出海，用飞书多维表格管理供应链，替代了 XXX 系统
→ 建议纳入样板间「消费电子-供应链协同」案例
```

**e5. 深层需求挖掘（从字里行间分析）**：
- 客户**明确说了**但当前没方案覆盖的
- 客户**没明说**但从上下文能推断的（如反复问价格 → 预算敏感；追问安全细节 → 可能去年出过事）
- 多个客户**交叉出现的潜在趋势**（如连续 3 场客户都提了同一个功能但飞书没有）

### 周报输出格式

用户期望的最终输出是一份结构化的飞书卡片/消息：

```markdown
# 📊 本周会议分析周报（MM/DD - MM/DD）

## 一、需求概览
本周共旁听 N 场会议，涉及 M 个客户，捕获 X 条需求。

## 二、需求分类与频率
🔥 高频：...
⚠️ 中频：...
💤 低频：...

## 三、Agent 覆盖率
总覆盖率：XX%
⚠️ 以下需求无 Agent 覆盖：[列表]

## 四、典型案例
✅ [案例1]
✅ [案例2]

## 五、挖掘与建议
🆕 新需求：[值得关注的新需求]
🤖 Agent 缺口：[需要新建/补充什么 Agent]
📚 可沉淀案例：[可纳入样板间的案例]
🔍 深层洞察：[字里行间发现的趋势/信号]
```

## 需求分析方法论（参考池）

以下框架已识别但**尚未采用**。用户要求先跑一周实际数据，再根据数据特征决定选用哪个：

| 框架 | 适用场景 | 参考价值 |
|------|----------|----------|
| **JTBD**（Jobs to be Done） | 分析客户"雇佣"飞书的底层任务 | 适合从功能需求挖掘到任务层 |
| **BANT / MEDDIC** | 销售资格框架（预算/决策人/需求/时间线） | 适合判断客户成熟度和优先级 |
| **Kano 模型** | 区分基本需求/期望需求/兴奋需求 | 适合洞察哪些需求超出预期 |
| **The Mom Test** | 从对话中提取真实需求、过滤客套话 | 适合提升字幕分析的深度 |

**使用原则**：数据分析优先，框架适配在后。不要用框架套数据，让数据选出最合适的框架。

## Agent 协作群管理

Agent 协作群（chat_id: `oc_219a613c13292855c2dc4b80e59dfd6e`）中已知 Agent：

| Agent | app_id | open_id | 能力 | 状态 |
|------|------|------|------|:--:|
| Mark 42-浪子 | `cli_a964fd626078dcbc` | — | Hermes（本 Agent），Orchestrator | ✅ |
| 南区 ISV 业务助手 | `cli_aaa06c74f1f89bcb` | `ou_abdda0c6cd5e362bca041cb3dbd88f86` | ISV 材料/案例/话术 | ✅ |
| 大湾区样板间专项小管家 | `cli_a96aefe4aff85cef` | `ou_459dac1c298c48d280a3ea3260aac80e` | 📚 案例弹药库 + 🏠 样板间专项 + 🌟 许愿助理 | ✅ |
| 马斯克 | `cli_a934e54959f99bd8` | `ou_ec816541777287f722b0896287c4486a` | 客户名单/合作产品/合同状态 | ✅ |
| Aime 个人助理 | `cli_9a31b280a1f3d101` | `ou_b33d3f6e144a9730db025d288c81212c` | 业绩/日历/bitable（10min 心跳） | ✅ |
| TC 交付数字员工 | `cli_a96d9040ddb8dccb` | `ou_c9cd24728752004e848f099d2b448d29` | 迁移（企微/钉钉/Confluence/语雀/Google Drive）+ 集成（SSO/API/审批连接器/主数据同步） | ✅ |

**新 Agent 加入**：用户会主动告知。收到通知后执行：
1. `lark-cli im +chat-members-list --as user --chat-id oc_219... --member-types bot --page-all` 找到新 bot
2. 发 post 消息 @ 它，做自我介绍并询问能力
3. 读回复（在线程或直接消息中），记录能力并汇报给用户
4. **不要设置 cron 轮询**——新 Agent 加入频率低且不规律，轮询浪费资源

## 客户端识别

### 客户名单

会议字幕中出现的发言人，通过以下方式区分客户方 vs 飞书方：

1. **客户端名单**：`~/.hermes/data/client_list.json`（包含 25 家南区客户的公司名 + 别名）
2. **马斯克 Agent**：可通过 @ 马斯克获取最新客户名单、合作产品、合同状态
3. **C360 验证**：单个客户 entity_id 可通过 `lark-c360 account +profile --id <id>` 获取，其 `owner_id.display_value` 可确认归属

> 匹配逻辑：字幕中 `speaker.user_name` 包含名单中任一公司名或别名 → 判定为客户方

### C360 过滤的坑

**`owner_id` 字段的 filter 在 `account list` API 中不生效**——无论传入什么 value，返回的都是全量（60万+）结果，过滤完全被忽略。

**解决方案**：
- 批量验证客户 → 用 `lark-c360 account list --keyword "客户名"` 逐个 keyword 搜索（已验证可靠）
- 单个客户详情 → 用 `lark-cli c360 account +profile --id <entity_id> --field owner_id`
- 不要浪费时间在 owner_id filter 上——已确认是 API 层面问题

- **不支持**：实时推送；在会上发声
- 用户必须本人在会中
- 每场会议需 owner 单独开启开关
- **字节未开放 `im:message.send_as_user`**：Bot 无法以用户身份发消息给其他人。当 Bot 发消息报 230013（收件人不在可用范围）时，不要把材料发给用户自己、让用户转发，不要尝试授权此 scope（已验证授权页被拒）
- ISV 助手卡片中的链接可能藏在按钮里不可见 → 用 `lark-cli docs +search` 按材料名称补全链接
