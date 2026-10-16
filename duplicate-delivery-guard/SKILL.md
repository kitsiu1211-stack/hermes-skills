---
name: duplicate-delivery-guard
description: Use when an event may hit 2+ agent sessions; dedup first.
category: productivity
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    tags: [dedup, idempotency, multi-session, feishu, meetings]
    related_skills: [feishu-meeting-listen, meeting-audit, hermes-feishu-gateway]
---

# 重复交付防护（Duplicate Delivery Guard）

## When to Use（何时使用）

任何**外部触发的事件**到达时，先假设「它可能已经触达过另一个会话/进程」：

| 触发源 | 重复机制 |
|---|---|
| 飞书会议邀请（`vc.bot.meeting_invited_v1` / IM 邀请卡） | 同一场会**并发投递到所有活跃会话**——旧会话（未过期）+ 新会话各收到一份 |
| cron 任务 | 多 profile / 手动 `action=run` 叠加定时触发 |
| Webhook / 群 @ | 平台重试、多个 bot 同时被 @ |
| 长后台任务 | 上一轮 kill 不彻底 → 僵尸进程继续产出 |

**核心风险**：每个会话都以为「我是唯一执行者」，于是各跑一遍全流程 → 用户收到重复卡片、日历里出现重复日程、群里出现重复评论。用户对这种噪音最反感。

## 铁律：交付前查「已产出物」，不是查进程

进程可能已被兄弟会话顺手清理掉（僵尸清理、`pkill`），但**产出物是持久的**——所以查产出物，不要只查 `pgrep`。

**三处查重（命中任意一处即停）**：

```bash
# ① 日历：有没有同主题的「跟进：…」日程
lark-cli calendar +search-event --as user \
  --query "<客户名/事项关键词>" --start <今天> --end <今天+5天> --json

# ② 私聊/群：卡片是不是已经发出去了
lark-cli im +chat-messages-list --chat-id <home_chat_id> \
  --as bot --order desc --page-size 5 --json
#    ⚠️ 返回字段是 data.messages（不是 data.items）；猜错字段会误判成"没发过"→ 重复发

# ③ 会话库：近期会话有没有处理过这件事
session_search(query="<客户名/事项关键词>", sort="newest")
```

**命中后的正确交付**（不要沉默，也不要重跑）：

> 会议已结束（xx:xx–xx:xx，N 分钟）。纪要卡片 + 跟进日程已在 <时间> 出过，**我不重复发**。
> 核心结论：<一句话>。

即：一句状态汇报 + 核心结论 + 明确说出「不重复发」。既避免噪音，也让用户知道事情闭环了。

## 判断细节

- **不要用 `pgrep poll.sh` 作为唯一依据**：僵尸进程常被兄弟会话清掉 → 你以为没人在跑，其实产出早已交付。
- **不要假设「旧会话过期了就没产出」**：实测旧会话在过期前已完成全部交付，新会话只是收到了同一邀请。
- **两个会话可能时间上重叠几十秒**（同时入会、同时读同一份日志）——查重与交付之间窗口要尽量短：先查再发。
- **只在无产出时才跑全流程**；无产出时按该领域的标准流程走。
- 领域细节不属于本 skill：会议入会/纪要流程见用户自有技能 `feishu-meeting-listen`（要让它可被自动维护，先 `hermes curator adopt feishu-meeting-listen`）。

## 案例

- `references/meeting-invite-double-delivery.md` — 2026-10-13 实测：同一会议邀请并发投递两个会话，A 已出卡片+跟进日程，B 差点重复；含命令与时间线。
- 2026-10-14 再次实测（更隐蔽的变体）：新会话只收到「第二场会议邀请」，看起来是干净的新任务，但**兄弟会话正在并行处理同一场会**——它 18:51 还顺手 `kill` 掉了新会话的 `poll.sh`（新会话因此收到 SIGTERM 通知，极易误判为自己出错）。实际查重三处全部命中：日历已有 3 条「跟进：疆海…」、Home 群 18:52 已发 3 张纪要卡片、`session_search("疆海")` 命中兄弟会话。**只看进程/只看 SIGTERM 会得出完全相反的结论**：进程消失 ≠ 任务失败，可能是交付完成后被清理。查重永远以产出物（日历 / 群消息 / 会话库）为准。
