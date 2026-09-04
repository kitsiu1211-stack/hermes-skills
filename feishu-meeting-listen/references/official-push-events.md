# 飞书官方智能体入会 · 独立入会（推送式事件）

> 来源：`W2Wgdi5Ifoal8uxqQNHcxNGRnMc`（飞书智能体入会 · 接入手册 对外版，2026-07-25）

## 与当前方案的核心差异

当前实现用 **轮询** `vc +meeting-events`（每10s）获取事件 → 限流（99991400）、延迟、部分会议无声。

官方 **独立入会** 采用 **推送式事件订阅**，三个事件：

| 事件 | 用途 |
|------|------|
| `vc.bot.meeting_invited_v1` | Bot 被邀请入会 → 自动响应 |
| `vc.bot.meeting_ended_v1` | 会议结束 → 即时空转 |
| `vc.bot.meeting_activity_v1` | 字幕/聊天/参会人进出/共享文档 → 实时推送，5s/100条聚合 |

## 迁移要点

1. **权限**（应用身份）：
   - `vc:meeting.bot.join:write`
   - `vc:meeting.meetingevent:read`
2. **事件订阅**：在开放平台声明上述三个事件
3. **BotJoinMeeting** 必须传 `join_type=1`
4. **语音互动**仍在小范围共创，暂不开放——ByteView 方案保留

## 排查清单补充

| 问题 | 原因 | 解决 |
|------|------|------|
| 收不到字幕/事件为空 | 事件未在开放平台声明 | 严格对齐文档字段名 |
| Bot 加入不了会 | 漏传 `join_type` | 固定填 `join_type=1` |
| 入会报「不支持的 Token 类型」 | 用了 User Token | Bot 入 / 离会只支持 Tenant Token |

## 结论

官方推送式接入是**下一代方案**——不再限流、不再漏消息。语音互动未开放前，ByteView 保留作为补充。
