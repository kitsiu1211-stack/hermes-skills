# 推送式会议事件（替代轮询）

> 配置日期：2026-07-26
> 状态：✅ 代码就绪，⚡ 等待 Gateway 重启生效

## 核心变化

从**轮询拉取**转向**推送接收**：

```
旧：Agent 每 5-10s 调 lark-cli vc +meeting-events → 拉字幕/聊天
新：飞书平台推送到 Gateway WebSocket → 实时转发给 Agent
```

## 事件流转

```
飞书会议事件
  → msg-frontier WebSocket 推送
  → Hermes Gateway FeishuAdapter 接收
  → feishu_meeting_events.py 解析
  → MessageEvent 注入 Agent 上下文
  → Agent 处理（纪要/回复/待办）
```

## 代码结构

### adapter.py 新增

**WebSocket 订阅**（3 个事件）：
```python
.register_p2_customized_event("vc.bot.meeting_invited_v1", self._on_meeting_invited_event)
.register_p2_customized_event("vc.bot.meeting_activity_v1", self._on_meeting_activity_event)
.register_p2_customized_event("vc.bot.meeting_ended_v1", self._on_meeting_ended_event)
```

**Webhook 处理器**（3 个 case，与 WebSocket 共享 handler）：
```python
elif event_type == "vc.bot.meeting_activity_v1":
    self._on_meeting_activity_event(data)
elif event_type == "vc.bot.meeting_ended_v1":
    self._on_meeting_ended_event(data)
```

### feishu_meeting_events.py（新模块）

| 函数 | 作用 |
|------|------|
| `handle_meeting_activity_event` | 解析活动批次 → 构建文本流 MessageEvent |
| `handle_meeting_ended_event` | 解析会议结束 → 构建「请出纪要」MessageEvent |
| `_parse_activity_item` | 单条活动 → 人读文本（字幕/聊天/进出） |
| `build_activity_prompt` | 批量活动 → Agent prompt |
| `build_meeting_ended_prompt` | 会议结束 → Agent prompt |

## 验证步骤

1. 重启 Gateway：`hermes gateway restart`
2. 检查日志确认事件订阅生效：
   ```bash
   grep 'meeting_activity\|meeting_ended\|meeting_invited' ~/.hermes/logs/gateway.log
   ```
3. 创建测试会议 → 邀请 Bot → 观察 Gateway 是否收到事件

## 待淘汰的轮询方案

推送稳定后逐步淘汰：

| 组件 | 状态 | 替代 |
|------|------|------|
| `listen_subtitles.py` | 仍在使用 | `vc.bot.meeting_activity_v1` 推送 |
| `poll_meeting_chat()` | 仍在使用 | 同上 |
| poll.sh | 仍在使用 | 同上 |
| 会议结束检测（超时 + meeting-list-active 验证） | 仍在使用 | `vc.bot.meeting_ended_v1` 推送 |

## 注意事项

- **Gateway 不能自重启**：从 Gateway 进程内无法 `hermes gateway restart`，需用户在终端手动执行
- **事件去重**：`handle_meeting_ended_event` 已内置 dedup（`vc_ended:{meeting_id}`），防止重复触发纪要
- **activity 空批次过滤**：`build_activity_prompt` 返回空字符串时跳过，不会产生空 MessageEvent
- **控制台 vs lark-cli**：Bot 级事件只能在飞书开放平台控制台配置，不能用 `lark-cli auth login --scope` 扫码授权
