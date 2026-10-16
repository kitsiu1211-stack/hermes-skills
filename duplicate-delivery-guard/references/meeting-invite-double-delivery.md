# 案例：同一会议邀请并发投递两个会话（2026-10-13）

## 时间线（实测）

| 时间 | 事件 |
|---|---|
| 17:09:51 | 会议「心玥landing/交接沟通群的视频会议」(400249112) 开始，host = 用户本人 |
| 17:10:09 | 新会话（fresh，上一会话因不活跃过期）Bot 入会，启动 `poll.sh` 静默旁听 |
| 17:13:31 | 会议结束（全场仅 3 分 40 秒），3 名参会人（含 Bot）全部 leave |
| ~17:17 | **另一个仍然活跃的旧会话**独立完成了全部交付：发给用户的纪要卡片（`om_x100b63eb...`）+ 跟进日程（10/14 11:00「跟进：凯莫尔→奥基 主体切换（退订重签工单）」），并顺手 `pkill -f "poll.sh 7696054407616728004"` 清掉僵尸轮询 |
| 17:17 | 新会话收到 `poll.sh` 退出通知（其实是旧会话 kill 的），差点再出一份纪要卡片 |

**结果**：新会话在执行前查了「产出物」，发现卡片和日程都已存在 → 只回了一句状态汇报，没有重复发。

## 查重的实际命令与返回

```bash
# 命中 ①：日历里已有同主题日程
$ lark-cli calendar +search-event --as user --query "退订" --start 2026-10-14 --end 2026-10-16 --json
{ "ok": true, "data": { "items": [ {
  "summary": "跟进：凯莫尔→奥基 主体切换（退订重签工单）",
  "start": {"date_time": "2026-10-14T11:00:00+08:00"} } ], "has_more": false } }

# 命中 ③：session_search 命中旧会话，其最后一条消息写明了「已经做了」清单
$ session_search(query="凯莫尔 退订重签 工单", sort="newest")
→ 命中会话 20261013_110428_9f8e7214，assistant 消息含：
  "📋 出了纪要卡片… / 📅 建了跟进日程：凯莫尔→奥基… / 🧹 顺手清掉了这个已结束会议残留的轮询进程"

# 命中 ②：卡片确实已送达私聊（注意字段名是 data.messages）
$ lark-cli im +chat-messages-list --chat-id <home> --as bot --order desc --page-size 5 --json
→ data.messages[] 里可见 17:17 的 interactive 卡片 + 一条 post 说明
```

## 教训

1. **`pgrep` 查不到进程 ≠ 没人处理过**：旧会话清理了进程，产出物（卡片、日程）仍在。
2. **`data.messages` 不是 `data.items`**：lark-cli `im +chat-messages-list` 的返回结构用 `messages`，写错会静默取空 → 误判「没发过」→ 重复交付。
3. **两个会话可以在同一分钟内并行工作**（都读了同一份 `~/meeting_logs/<id>.jsonl`），所以查重必须紧接交付，窗口越短越好。
4. **正确交付 = 状态汇报而不是静默**：说清「会议已结束 + 核心结论 + 已出过纪要/日程，不重复发」，用户才知道闭环了。
5. 附带发现（属于 `feishu-meeting-listen` 领域，该技能为用户自有、curator 不可写）：`~/meeting_logs/<id>.jsonl` 的**行序不是时间序**（poll.sh 每轮 `--page-all` 追加，同轮内句子顺序随机），读字幕前必须先按 `time` 排序并做 `sentence_id` 去重，否则对话是乱的。
