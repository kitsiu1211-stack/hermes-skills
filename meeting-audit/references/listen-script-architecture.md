# listen_subtitles.py 架构与演进

## 核心能力

旁听飞书会议，不入会，用户身份轮询字幕。会后自动保存字幕、写收件箱、bot 通知出纪要。

## 关键设计决策

### API 返回值模式 (v3)

`get_events()` 返回 `(events, error)` 元组:

| 返回 | events | error | 含义 |
|------|--------|-------|------|
| 正常 | `[...]` | `None` | 有事件数据 |
| 空返回 | `[]` | `None` | API 超时/无事件 |
| API 错误 | `None` | "智能体不可入会" | 会议未开开关 |

主循环先检查 error——有错误立即退出，不再空转轮询。

### 会议结束检测 (v2)

**旧逻辑（v1）**：连续 4 轮 API 返回空事件 → 判会议结束。
**问题**：`lark-cli vc +meeting-events` 45s 超时也返回空，跟真结束无法区分。两次误杀 CodeM 培训。

**新逻辑（v2）**：连续空返回 → 调 `meeting_still_active()` 验证（`+meeting-list-active` 检查 meeting_id 是否还在列表中）。
- 会议还在 → 打日志 `[API 静默 N 轮，会议仍在进行]`，继续轮询
- 会议不在了 → 进入"等待最后字幕"模式，多等 12 轮确保收尾字幕不丢
- 保守策略：`meeting_still_active()` 异常时返回 True（不误杀）

### 增量保存

每收到新字幕立即写盘（`save_progress()`），crash 不丢数据。异常捕获也触发保存。

### JSON 容错

`get_events()` 中对 `json.JSONDecodeError` 做了 try/except 保护，API 返回非 JSON 时返回空列表而非崩溃。

### 多会议并行

用户同时参加多个会议时，脚本默认取第一个活跃会议。第二个会议需显式传 meeting_id：
```bash
python3.11 listen_subtitles.py <meeting_id>
```

## 会后的三项产出

1. 字幕文件 → `~/.hermes/meeting_transcripts/<meeting_id>.txt`
2. 收件箱条目 → `~/.hermes/meeting_inbox.json`
3. Bot 消息 → Home 频道 "纪要请求: 会议「xxx」已结束"

## 配置项

| 配置 | 值 | 说明 |
|------|-----|------|
| API 超时 | 45s | `get_events()` 中 `subprocess.run(timeout=45)` |
| 轮询间隔 | 5s | `POLL_SEC = 5` |
| 结束前确认轮数 | 4 | 连续空返回后触发 `meeting_still_active()` 检查 |
| 结束后等待轮数 | 12 | 确认结束后多等几轮确保收尾字幕 |
| Home Chat | `oc_e2f79ec1614a1efe1ebcd7c679bb45a8` | 纪要请求发送目标 |
