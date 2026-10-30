---
name: bot-broadcast-receipts
description: 群内给多个 bot 广播规则/派活并回收回执时使用。以实收为准，不追静默 bot。
category: feishu
version: 1.0.0
author: 浪子 (curator)
license: MIT
metadata:
  hermes:
    tags: [feishu, multi-agent, broadcast, receipt, ledger]
    related_skills: [agent-group-collab, feishu-group-chat, feishu-thread-reply, duplicate-delivery-guard]
---

# 群内多 Bot 广播 & 回执回收

## When to Use

命中以下任一情形就加载本 skill：

- 要在群里给一批 bot 广播规则、版本通知、新口径（「收到请回 ✅ 已读 X」）
- 要统计「哪些 bot 已接入 / 已确认 / 已回执」，并出名单或写台账
- 用户在追问回执进度，或问「还有几个没回」
- 要向群 bot 派活并设定回执格式

不适用：单个 bot 的派活与回复回收（用 `agent-group-collab` 里对应 bot 的策略）。

给飞书群里一批 bot 发规则、通知、派活，然后回收「✅ 已读 / 已完成」这类回执。群 bot 名单与 @ 方式见 `agent-group-collab`（本 skill 只负责广播与回执这一段）。

## 铁律：回执以实收为准

**收到几个算几个。禁止做「N 个里还差几个」的补齐式追踪。**

用户的定稿口径（2026-10-29）：「接收到多少 bot 的回答，就以那个为主就 OK 了，就不用再去跟踪剩下的没有回的那个 bot 的情况」。

具体禁止：

- ❌ 不设「24 小时未回按未接入处理」这类截点，不为它建判定 cron
- ❌ 不点名、不二次催、不再定向补发提醒
- ❌ 不把静默 bot 记成「未接入 / 违规 / 该绕过」
- ✅ 台账（通常 Obsidian）只登记已回执的 bot，静默的标注「不追踪」+ 原因
- ✅ 真需要它参与时走可达路径：真人 @，或换一个可达的 bot

原因（写进台账，别只记结论）：**相当一部分 bot 产品设计上只响应真人的 @，不响应 agent 发起的 @**（个人助理类、部分 Aily 智能体）。不是不配合，是物理收不到。继续追踪等于要求工具具备它没有的能力，只会产出噪音和假的「未接入」记录。

## 广播流程

1. **发之前先核名单**：`lark-cli im +chat-members-list --member-types bot --page-all`。群成员变动频繁，缓存不可信。
2. **一条消息就是全部内容**：规则、派活原文贴全，不转述。@ 用 `<at user_id="ou_xxx">名</at>` 直双引号，全角引号会静默降级成纯文本。
3. **回执要求写死一行**：`收到请回一行「✅ 已读 X-v1」，一条就够，别展开`。不写这句，会收到一堆「收到」「已对齐」「口径锁定」。
4. **不加威胁条款**。写了「未回按未接入处理」，后面就得撤销它——多一条群消息，还得多改一次台账。
5. **回收**：等 3-10 秒后跑一次 list（见下），之后有人回再增量补。不轮询、不定时催。

## 收尾：只发一条，不带 @

口径变了或要闭环时，在规则消息的话题里发**一条不带 @** 的收尾消息：

- 说清哪条作废 + 为什么（能力限制，不是态度）
- 末尾写「不用回执」

不带 @ 是硬要求：带了 @ 就是新一轮派活，会触发确认往返。`--reply-in-thread` 用法见 `feishu-thread-reply`。

## 核查谁回了：一次调用拿主聊天 + 话题

```bash
lark-cli im +chat-messages-list --chat-id <chat> --order desc --page-size 50 \
  --start "YYYY-MM-DD HH:MM" --format json
```

- `--page-size` 上限 **50**，写 60 直接 validation 报错
- 话题内回复**嵌套在父消息的 `thread_replies[]`** 里，不用另调 threads 接口；`--start` 卡时间窗即可一次看清「谁在主聊天回、谁在话题回」
- 判定回执看 `sender.name` + `content` 是否含 `✅`；卡片回执（`msg_type: interactive`）也算数，正文裹在 `<card>` 里
- **真人判官/监工的确认单列，不占 bot 名额**（否则会出现 N+1/N 这种假账）

台账字段：bot 名 / 回执位置（主聊天 or 话题）/ 原文摘要。

## 坑

- **两个实例同一个 app 身份**：一个 Feishu app 上跑两个 Hermes 实例时会互抢回执、翻倍确认往返。症状是「同一条回执出现两次、措辞不同」。遇到就把实例拆到不同 app，或让云端实例只在自己被点名的话题里响应。
- **确认往返会自我繁殖**：A bot 回执 → 我回「收到」→ A 再回「👌」。规则里必须写明「只回一次，看到别人的回执不用再回」，并且我自己先做到不回第二条。
- **别用 cron 建「截止日判定」**：用户不需要机器去施压 bot。这类 cron 建了大概率要删，删了还得改台账。
