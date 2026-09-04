# 飞书事件驱动入会（被 call 自动入会）

> 来源文档：`Q6nWdDKwIo8Zw4x7TLRcnXEDnYb`

## 核心链路

```
飞书推送 vc.bot.meeting_invited_v1 事件
  → Bot 调入会 API: POST /open-apis/vc/v1/bots/join (join_type=1)
  → 拿实时音频端点: GET /open-apis/vc/v1/realtime/endpoint
  → 连 ByteView WS 收发音频
```

## 与主动入会的对比

| | 主动入会 (当前) | 事件驱动入会 |
|--|---|---|
| 触发 | 用户说「旁听会议」→ Agent 轮询检测 | 飞书推送事件 → Bot 自动入会 |
| 延迟 | 手动 / 15s 轮询 | **即时** |
| 适用 | 仅标准会议（9位号） | 标准会议 + 个人通话 |
| 实现 | `lark-cli vc +meeting-join` | `/open-apis/vc/v1/bots/join` |

## 所需配置

| 类别 | 具体项 |
|-|-|
| 权限 | `vc:meeting.bot.join:write` ✅ 已授权 |
| 事件订阅 | `vc.bot.meeting_invited_v1`（被 call 入会）|
| 事件接收 | 长连接（WSClient）或 Webhook |
| 发布 | 权限/事件配好后**必须发布版本** |

## 当前状态（2026-07-26）

- ✅ 权限已授权
- ✅ 事件已在控制台添加：
  - `vc.bot.meeting_invited_v1` — 被邀请入会
  - `vc.bot.meeting_activity_v1` — 会中活动推送（5s/100条聚合）
  - `vc.bot.meeting_ended_v1` — 会议结束推送
- ✅ Hermes Gateway 已注册三个事件的 WebSocket 订阅 + webhook 处理器
- ✅ `feishu_meeting_events.py` 处理模块已就绪
- ⚠️ 需重启 Gateway 生效：`hermes gateway restart`

## Bot 级事件 vs 用户级事件

| 事件 | 级别 | 配置方式 | 消费方式 |
|------|------|---------|---------|
| `vc.bot.meeting_invited_v1` | Bot | 开放平台控制台 | Gateway WebSocket / webhook |
| `vc.bot.meeting_activity_v1` | Bot | 开放平台控制台 | Gateway WebSocket / webhook |
| `vc.bot.meeting_ended_v1` | Bot | 开放平台控制台 | Gateway WebSocket / webhook |
| `vc.meeting.participant_joined_v1` | User | 无需控制台 | `lark-cli event consume` |
| `vc.meeting.participant_ended_v1` | User | 无需控制台 | `lark-cli event consume` |

**关键区别**：Bot 级事件是**应用级推送**，在开放平台控制台配置后通过 msg-frontier WebSocket 推送；用户级事件是**参会人级事件**，可直接通过 lark-cli 本地消费。

**请求网址不一定需要**：Gateway 通过 WebSocket 长连接接收事件（不需要公网 HTTPS 端点）。仅当控制台强制要求时才需配置 webhook URL（Gateway 默认 `127.0.0.1:8765/feishu/webhook`）。

## 三种推送事件的用途

| 事件 | 替代的轮询 | 收益 |
|------|-----------|------|
| `meeting_invited_v1` | 用户说「入会」→ Agent 扫活跃会议 | 即时，Bot 被邀请瞬间自动入会 |
| `meeting_activity_v1` | `listen_subtitles.py` 每5s轮询 + `poll_meeting_chat()` 每10s轮询 | 实时推送，无延迟，无限流 |
| `meeting_ended_v1` | poll.sh 检测离会 → 等超时 | 即时通知，秒级触发纪要
