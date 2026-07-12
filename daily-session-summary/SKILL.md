---
name: daily-session-summary
description: Generate a daily digest of Hermes conversations — key decisions, conclusions, and action items. Triggered by cron job at 21:00 daily.
category: productivity
---

# Daily Session Summary

Generate a daily digest of Hermes conversations — key decisions, conclusions, and action items.

## Trigger
Cron job at 21:00 daily, or invoked on-demand.

## Workflow

### 1. Find today's sessions
Use `session_search()` (no args = browse mode) to get the most recent sessions. Filter to sessions whose `when` field is today's date. Relevant sessions are those with source `feishu` involving the user.

### 2. Extract content from each session
For each relevant session found:
- Use `session_search(session_id="...", around_message_id=<match_message_id>)` to scroll through the conversation
- Focus on the user's messages and your substantive responses
- Skip trivial exchanges ("好的", "收到", status updates)

### 3. Identify key points
From the conversation content, extract:
- **Decisions made**: "决定做X", "选择Y方案", "不用Z"
- **Conclusions reached**: bug根因, 分析结论, 讨论结果
- **Actions started/completed**: 创建了skill, 部署了cron, 修复了bug
- **Ideas worth noting**: 用户提出的新想法、新方向

### 4. Generate the summary card
Format as a Feishu interactive card (see template below). Keep it concise — 3-5 bullet points per section max.

### 5. Send to user
Use `feishu-cli exec im.v1.message.create`:

```bash
feishu-cli exec im.v1.message.create --params '{
  "params": {"receive_id_type": "open_id"},
  "data": {
    "receive_id": "ou_dc055b0b5b0b5db2b1af5e79c0536db6",
    "msg_type": "interactive",
    "content": "<card_json_string>"
  }
}'
```

Use `json.dumps(card, ensure_ascii=False)` to serialize the card JSON, then embed it in the `content` field.

## Card Template

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "📋 今日工作摘要"},
    "template": "indigo"
  },
  "elements": [
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**{{DATE}}**"}
    },
    {"tag": "hr"},
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**🔑 关键决策**\n{{DECISIONS}}"}
    },
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**💡 重要结论**\n{{CONCLUSIONS}}"}
    },
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**⚡ 今日行动**\n{{ACTIONS}}"}
    },
    {"tag": "hr"},
    {
      "tag": "note",
      "elements": [{"tag": "plain_text", "content": "每日 21:00 自动生成 · Hermes Session Summary"}]
    }
  ]
}
```

If no substantive conversations happened today, send a brief note:
> 📋 今日工作摘要 — {{DATE}}  
> 今天没有实质性的工作对话，安静的一天。

## Pitfalls
- session_search browse mode returns sessions sorted by recency; filter by `when` date before processing
- The card JSON must be properly escaped via `json.dumps(card, ensure_ascii=False)` before embedding in `--params`
- Don't include every tiny interaction — only substantive discussions matter
- If session content is very long, sample key excerpts rather than trying to read everything
- Use `feishu-cli exec im.v1.message.create` (NOT MCP tools) for sending cards

## 质检：Generator → Evaluator（强制）

本 Skill 产出每日摘要卡片，**必须经过 Evaluator 独立评分后才能交付**。

| 维度 | 阈值 | 检查要点 |
|------|------|---------|
| **关键决策覆盖** | ≥7 | 是否覆盖了当天所有实质性对话？有无遗漏重要决策？ |
| **待办可操作性** | ≥7 | 待办事项是否具体可执行？还是「跟进XX」式空泛？ |
| **简洁度** | ≥7 | 卡片是否精炼？有无冗余信息或无意义的交互记录？ |

Generator→Evaluator→全部≥7交付/修正重评（最多3轮）。禁止自评。
