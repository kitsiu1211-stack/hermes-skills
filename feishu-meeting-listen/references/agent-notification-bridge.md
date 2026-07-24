# Agent 会议通知桥接

> ❌ **已废弃**（2026-07-16）。每 5 分钟的 cron job（`07ec40e98dc9`）已删除。
> 
> **废弃原因**：poll-v5 launchd 守护进程已 24 小时自动检测会议 + DM 通知 + C360 告警，cron job 的「检测到进行中会议」通知属于纯噪音。用户反馈：「没有有效信息不用发我，你自己内部跑就好了」。
> 
> **保留此文档**：C360 查询逻辑和过滤规则仍然有效，可在其他场景复用。

## 问题

poll-v5 通过 launchd 后台运行，检测到会议后：
- ✅ 写入日志文件
- ✅ 发送 DM 通知到用户飞书
- ❌ **不通知 Agent** — Agent 不知道有会议

用户期望：Agent 主动检测并汇报会议，不需要手动提醒。

## 解决方案：Hermes Cron Job

设置一个每 5 分钟执行的 Hermes 定时任务来做桥接。

### 关键配置

- `schedule`: `1,6,11,16,21,26,31,36,41,46,51,56 * * * *`（**不是** `every 5m`——后者在整点/半点边界漏检，见下方「已知陷阱」第一条）
- `deliver`: `origin` (通知原会话)
- `enabled_toolsets`: `["terminal"]`
- 无需 `model` override — 继承主会话模型

### 状态文件

两个 JSON 文件实现去重和跨会议连续性：

**1. `~/.hermes/cron/meeting_state.json`** — 会议级去重
```json
{
  "meeting_id": {
    "title": "会议标题",
    "cid": "客户C360 ID",
    "status": "ongoing|ended",
    "first_seen": "ISO时间"
  }
}
```
- 新会议 → 执行分析 + 通知 → 写入 `status=ongoing`
- 已在 ongoing → **静默跳过**（不再重复通知）
- 会议结束（不在活跃列表但 state=ongoing）→ 发送"会议已结束" → 更新为 ended
- 清理：删除 7 天前的 ended 记录

**2. `~/.hermes/cron/client_context.json`** — 客户级上下文（跨会议累积）
```json
{
  "cid": {
    "name": "客户名",
    "last_meeting": "ISO时间",
    "last_meeting_title": "上次会议主题",
    "last_topics": "上次讨论要点",
    "last_contacts": ["张三/CTO", "李四/采购"],
    "known_tenants": ["Fxxx"],
    "known_companies": ["子公司名"],
    "notes": "关键背景"
  }
}
```
- 同客户第二次开会 → 自动输出"上次回顾"板块（时间、主题、对接人、讨论要点）
- 每次会后更新该客户的上下文
- 保留最近 50 个客户

### 任务 Prompt（完整版）

```
会议检测通知（去重 + 过滤噪音 + 客户连续性）。核心理念：不 dump 全量，只推送可行动增量；同客户多次会议保持上下文衔接。

## 状态文件
1. ~/.hermes/cron/meeting_state.json — 会议级去重
2. ~/.hermes/cron/client_context.json — 客户级上下文（跨会议累积）

## 执行步骤

### 1. 获取活跃会议
lark-cli vc +meeting-list-active --as user
无活跃会议 → 检查 meeting_state 中 ongoing 项是否结束 → 发送"会议已结束"并更新状态 → 结束。

### 2. 去重
活跃会议已在 meeting_state 中 status=ongoing → 静默跳过。

### 3. 新会议 → 提取客户 + 查 C360
从会议标题提取客户名。用关键词搜索：
lark-c360 search all --keyword "<客户名>" --limit 5 --json
从结果中提取 account ID（entity_id，格式 001xx...）。

### 4. 获取跟进记录（不限 7 天，取最近一条）
lark-c360 follow_up +recent --account-id <account_id> --limit 3 --json
有结果 → 标注日期和内容摘要。7 天内标注 🟢"近期"，超过标注 📅 实际日期。
无结果 → 标注 "无近期跟进记录"。

### 5. 获取联系人
lark-c360 contact list --filter-json '{"relation":"AND","children":[{"field":"account_id","operator":"EQ","value":["<account_id>"]}]}' --limit 10 --json
列出关键联系人（姓名 + 角色/职位）。

### 6. C360 数据过滤（search all 结果）

✅ 可行动（输出）：
- 🔴 非 Closed Lost 的商机（新购/增购/扩张），标注产品+ARR+阶段
- 🔴 30 天内到期续约
- 🟡 90 天内到期续约
- 🟡 进行中的工单（status=服务中/处理中）

❌ 噪音（跳过）：
- Closed Lost 商机
- 90 天后的续约
- 已完成的工单/续约
- 已归档的历史协议

### 7. 🔗 连续性上下文
查 client_context.json，同客户之前有会议 → 输出：
- 上次会议时间、主题
- 上次关键讨论话题
- 上次对接人
→ 作为"上次回顾"板块

### 8. 过滤后无内容 → 静默，不发通知

### 9. 输出格式（飞书卡片，只输出有内容的板块）
🔗 上次回顾（如有）
📝 最近跟进
👤 关键联系人
📊 可行动事项
  🔴 紧急（30天内）
  🟡 关注（季度内）
📋 客户概览（首次会议时输出基本信息）

### 10. 写入状态 + 清理
- meeting_state: 新会议 → ongoing
- client_context: 更新该客户 last_meeting、last_topics、last_contacts
- 清理：meeting_state 删 7 天前 ended；client_context 保留最近 50 个客户
```

### 关键 C360 CLI 命令速查

| 用途 | 命令 |
|------|------|
| 全量搜索客户 | `lark-c360 search all --keyword "<客户名>" --limit 5 --json` |
| 最近跟进记录 | `lark-c360 follow_up +recent --account-id <id> --limit 3 --json` |
| 联系人列表 | `lark-c360 contact list --filter-json '{"relation":"AND","children":[{"field":"account_id","operator":"EQ","value":["<id>"]}]}' --limit 10 --json` |
| 客户详情 | `lark-c360 account +profile --id <id> --json` |
| 客户服务工单 | `lark-c360 account +cases --id <id> --json` |
| 客户使用数据 | `lark-c360 account +usage --id <id> --json` |

### 用户过滤偏好（铁律）

1. **Closed Lost 商机 → 完全不提**。用户原话：「丢单的就不需要再发了」
2. **续约时效过滤**：30 天内 = 🔴 紧急、90 天内 = 🟡 关注、超过 → 不提
3. **跟进记录不限 7 天**：取最近一条，无论多久。用户原话：「如果 7 天内没有，我会抓取最近的一次」
4. **跨会议连续性**：同客户开会必须回顾上次内容 + 对接人。用户原话：「不要每次搞到那个客户会好像都是全新的，缺乏专业性」
5. **过滤后无内容 → 不发通知**：不要为发而发

### 工具集

只需 `terminal` toolset — 只跑 shell 命令。

## 验证

```bash
# 检查 cron 任务
hermes cron list | grep meeting

# 手动触发
hermes cron run <job_id>

# 检查状态文件
cat ~/.hermes/cron/meeting_state.json
cat ~/.hermes/cron/client_context.json
```

## 与 poll-v5 的关系

```
poll-v5 (launchd)              cron job (Hermes)
     │                               │
     ├─ 10s 轮询活跃会议              ├─ 5m 轮询活跃会议
     ├─ 检测入会 → DM 通知用户        ├─ 检测到会议 → 通知 Agent
     ├─ 实时字幕 → C360 告警          ├─ 查 C360 → 汇报给用户
     └─ 写入日志                       ├─ 去重（同会不重复报）
                                       ├─ C360 过滤（跳过噪音）
                                       ├─ 跨会议上下文（client_context）
                                       └─ 无内容时完全静默
```

两者互补，不冲突。poll-v5 做实时监听和告警，cron job 做 Agent 级别的周期性检测、过滤后的可行动简报、以及跨会议客户上下文衔接。

## 已知陷阱

- ⚠️ **整点边界竞争（:00 漏检，2026-07-16 实锤）**：会议在 11:00 开始时，`every 5m` 的 cron 恰好也在 11:00:08 执行——飞书 VC API 可能尚未返回该会议，导致 cron 输出 `[SILENT]`，用户直到下一次 cron（5 分钟后）才被通知。**修复**：将 schedule 从 `every 5m` 改为 `1,6,11,16,21,26,31,36,41,46,51,56 * * * *`。这个模式：① 错开所有整点/半点（:00/:30）和五分钟整边界（:05/:10/:15...）；② 每轮比整点慢 1 分钟，给 API 留出刷新窗口；③ 仍然保证 5 分钟内的检测频率。
- **search all 关键词太宽 → size exceed limit**：用更精确的关键词（如"福建电子信息集团"而非"福建省电子信息"），或减小 `--limit`
- **account +profile 只返回 id + name**：需要更多字段用 `search all` 获取完整数据
- **follow_up +recent 可能为空**：正常，标注"无近期跟进记录"即可，不要编造
