# Bash 轮询 → Hermes Cron 迁移记录

## 时间线

| 日期 | 版本 | 方案 | 结果 |
|------|------|------|------|
| 7.4 | v1-v3 | `poll.sh` 手动启动 | 稳定（纯旁听），但需手动触发 |
| 7.10-7.15 | v4-v5 | `poll-v5.sh` + launchd 守护 | 多次故障：竞争条件、API超时、多实例并发 |
| 7.16 上午 | v5 fix | 回退 v4 逻辑 + 加 perl alarm | 54分钟 API 超时导致漏检 |
| **7.16 下午** | **cron** | **Hermes cron `8993e3619bfc`** | **生产运行中** |

## 根因分析

bash `while sleep 10` 轮询循环的三个致命缺陷：

1. **单线程阻塞**：任何一步卡住（API 超时、网络抖动），整个循环停顿
2. **无状态**：进程重启后不知道之前检测过哪些会议
3. **无感知**：进程崩溃/冻结，Agent 和用户都不知道

## Cron 架构

```yaml
job_id: 8993e3619bfc
schedule: every 1m
toolsets: [terminal]
state_file: ~/.hermes/cron/meeting_state.json
```

### 状态文件格式

```json
{
  "7661849741337250776": {
    "title": "和汪航交流",
    "status": "ended",
    "first_seen": "2026-07-16T14:46:11+08:00",
    "last_event_ts": "2026-07-16T14:47:00+08:00"
  }
}
```

### 执行流程

```
每分钟触发
  ↓
lark-cli vc +meeting-list-active
  ↓
对比 meeting_state.json
  ├─ 新会议 → bot入会 → 拉事件 → C360 → 飞书卡片通知
  ├─ 进行中 → 拉新事件 → 有实质内容才通知
  └─ 已结束 → 标记 ended → 发送结束通知
```

### 关键原则

- 只推有实质内容的更新
- 同一会议同一客户不重复推送
- API 超时静默跳过，下分钟重试
- 非工作时段（0-7点）静默

## 旧方案清理清单

- [x] `launchctl unload com.yuanxinjie.meeting-monitor.plist`
- [x] `pkill -f poll-v5.sh`
- [x] 移除旧 cron job `07ec40e98dc9`
- [x] 初始化 `meeting_state.json` = `{}`
- [x] 验证 cron `8993e3619bfc` 运行正常
