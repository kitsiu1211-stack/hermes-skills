# 官方独立入会方案 — 配置与验证记录

> 2026-07-25 基于飞书官方文档 `W2Wgdi5Ifoal8uxqQNHcxNGRnMc` 完成

## 一键配置

**App ID**: `cli_a964fd626078dcbc` (Mark 42-浪子)

**配置链接**（点击自动完成权限+事件订阅）：
```
https://open.feishu.cn/page/launcher?clientID=cli_a964fd626078dcbc&addons=<base64gzip>
```

配置内容：
- 权限: `vc:meeting.bot.join:write`, `vc:meeting.meetingevent:read`
- 事件: `vc.bot.meeting_invited_v1`, `vc.bot.meeting_ended_v1`, `vc.bot.meeting_activity_v1`

## 验证结果

### ✅ Bot入会 — 正常工作
```bash
lark-cli vc +meeting-join --meeting-number 472634528 --as bot
# ok: true, meeting_id: 7666687236474538970
```
`join_type=1` 由 lark-cli 1.0.77 自动处理。

### ✅ Bot拉事件 — 新格式正常
```bash
lark-cli vc +meeting-events --as bot --meeting-id 7666687236474538970
# 返回 participant_joined 事件，新格式含 event_type + actors + payload
```

旧格式已升级——events 列表更结构化。

### ⏳ 推送事件 — 待 lark-cli 支持
`vc.bot.meeting_activity_v1` / `vc.bot.meeting_invited_v1` / `vc.bot.meeting_ended_v1` 三个事件已在控制台注册，但 lark-cli 1.0.77 的 `event list` 中未包含这些 bot 级会议事件（独立入会是早鸟灰度）。当前用 `+meeting-events --as bot` 轮询替代。

## 与旧方案的区别

| 旧方案 | 新方案 |
|--------|--------|
| `--as user` 拉事件 | `--as bot` 拉事件（权限完备） |
| 无事件订阅 | 3 个 bot 级事件已注册 |
| 轮询间隔 10s | 轮询间隔不变，但事件格式提升 |
| 入会参数缺 join_type | lark-cli 自动填 join_type=1 |
