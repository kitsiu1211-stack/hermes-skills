# Cron + Python 会议检测迁移（2026-07-16）

## 架构演进

```
v1-v5: bash poll-v5.sh + launchd 守护 → 5 版全失败
   ↓
LLM cron: every 1m LLM Agent → token 太高，用户否决
   ↓
v5 Python no_agent cron (272cdc68a518): every 1m Python 脚本，零 token
   ├─ 但只做 C360 推送，丢失 poll.sh 监听 + 纪要产出 → 大失败
   ↓
v6 Python no_agent cron (272cdc68a518): every 1m Python 脚本
   ├─ 所有会议启动 poll.sh 监听
   ├─ 客户会议额外 C360 推送
   └─ 标记 completed 等待纪要生成
```

## 🚨 v5→v6：丢失纪要能力的教训

用户原话：「自从脚本更新到 V5 之后，好像都没有产出会议纪要了。就是这整个升级版本简直就是个大失败。」

**根因**：迁移时只保留了 C360 推送能力，`meeting_detect.py` 完全没有启动 `poll.sh` 入会监听。

**修复**（v6）：`meeting_detect.py` 重写，核心逻辑改为双轨：
1. **所有会议** → `subprocess.Popen(poll.sh)` 后台监听 → JSONL
2. **客户会议** → 额外 C360 查询 → stdout 输出

**教训**：任何架构迁移必须对照核心能力清单（监听 + 纪要 + C360），缺一不可。

## v6 当前架构

- **脚本**：`~/.hermes/scripts/meeting_detect.py`
- **Cron**：job `272cdc68a518`，`schedule: every 1m`，`no_agent: true`，`script: meeting_detect.py`
- **状态文件**：`~/.hermes/cron/meeting_state.json`
- **监听**：`poll.sh`（由 meeting_detect.py 自动启动）
- **日志**：`~/meeting_logs/<meeting_id>.jsonl`

## meeting_state.json 字段

```json
{
  "<meeting_id>": {
    "title": "会议标题",
    "status": "new|monitoring|completed",
    "first_seen": "ISO timestamp",
    "client": "客户名或 null",
    "pid": 12345,
    "c360_pushed": false,
    "completed_at": "ISO timestamp",
    "log_size": 12345
  }
}
```

## v6 脚本逻辑

1. `lark-cli vc +meeting-list-active --as user` — 15s 超时
2. 新会议 → `start_poll(meeting_id, title)` → `subprocess.Popen(bash poll.sh ...)` 
3. 客户会议（标题匹配「客户名 x 飞书」）→ `c360_lookup()` → 输出到 stdout
4. 检查已有 poll.sh PID 是否存活 → 退出则标记 `completed`
5. 非客户会议：仅监听，不输出

## ⚠️ 待完成：纪要自动生成

v6 `meeting_detect.py` 正确标记 `completed` + 记录 `log_size`，但缺少 LLM cron 从 JSONL 生成纪要。

需要创建：
- Cron job（建议每 5 分钟，LLM enabled）
- 读取 `meeting_state.json` 中 `status=completed` 且未生成纪要的会议
- 读取 `~/meeting_logs/<id>.jsonl` → LLM 分析 → 飞书卡片
- 标记 `summarized` 防止重复

## 旧方案状态

- `poll-v5.sh` + launchd `com.yuanxinjie.meeting-monitor` — 已停止
- LLM cron（旧 8993e3619bfc）— 已删除
- 旧 meeting cron（07ec40e98dc9）— 已删除
