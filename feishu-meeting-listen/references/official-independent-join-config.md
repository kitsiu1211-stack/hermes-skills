# 飞书官方「独立入会」配置（2026-07-27 已验证）

来源：[飞书智能体入会 · 接入手册](https://bytedance.larkoffice.com/docx/W2Wgdi5Ifoal8uxqQNHcxNGRnMc)

## 配置状态

✅ 已完成一键配置（2026-07-27，Revision 67）

- App ID: `cli_a964fd626078dcbc`
- 权限: `vc:meeting.bot.join:write` + `vc:meeting.meetingevent:read`
- 事件订阅: `vc.bot.meeting_invited_v1` + `vc.bot.meeting_ended_v1` + `vc.bot.meeting_activity_v1`

## 一键配置链接生成

```javascript
const { gzipSync } = require('zlib');
const payload = {
  scopes: { tenant: ['vc:meeting.bot.join:write', 'vc:meeting.meetingevent:read'] },
  events: { items: { tenant: ['vc.bot.meeting_invited_v1', 'vc.bot.meeting_ended_v1', 'vc.bot.meeting_activity_v1'] } }
};
const encoded = gzipSync(JSON.stringify(payload))
  .toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const appId = 'cli_a964fd626078dcbc';
const url = 'https://open.feishu.cn/page/launcher?clientID=' + appId + '&addons=' + encoded;
```

## 已验证通过

1. **入会**: `lark-cli vc +meeting-join --as bot` → `join_type=1` 由 cli 1.0.77 内置处理
2. **事件轮询**: `lark-cli vc +meeting-events --as bot` 正常工作
3. **事件格式**: 升级为 `event_type` + `actors` + `payload` 结构

```json
{
  "event_id": "384b62d4-288e-...",
  "event_type": "participant_joined",
  "event_time": "2026-07-26T16:05:49Z",
  "actors": [{"id": "...", "name": "袁鑫杰", "participant_type": "human", "role": "host"}],
  "payload": {"activity_event_type": "participant_joined", ...}
}
```

## 当前限制

- `lark-cli event consume vc.bot.meeting_activity_v1` 暂不可用（独立入会早鸟灰度，event key 未进 lark-cli）
- 暂时用 `+meeting-events --as bot`（10s 轮询）
- 语音互动尚在「小范围共创」，需提交申请表单
