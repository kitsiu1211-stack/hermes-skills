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

## 当前状态

- ✅ 权限已授权
- ❌ 事件订阅未配置（需飞书开放平台控制台操作 https://open.feishu.cn/app/cli_a964fd626078dcbc/event）
