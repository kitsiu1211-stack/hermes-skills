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
🚨 **主路径：state.db 直查（2026-08-28 修复，根治连续漏报）**。browse 模式只返回最近 10 个会话，遇到当天有大会话（会议旁听/长文分析 100+ 消息）或 cron 会话挤占时会把当天 feishu 会话挤出列表 → 误判"无实质对话"→ 静默漏报（08-24/25/26 连续 3 天翻车，当天分别有 124/80/368 消息的实质会话）。

```bash
sqlite3 ~/.hermes/state.db "SELECT id, source, title, datetime(started_at,'unixepoch','localtime') started, message_count FROM sessions WHERE started_at >= strftime('%s','<今天日期> 00:00:00','utc') AND source != 'cron' AND source != 'subagent' ORDER BY started_at;"
```

- 用 `message_count` 判断体量，对 message_count > 200 的大会话用 sqlite 抽取而非 scroll（防上下文爆炸）：
```bash
sqlite3 ~/.hermes/state.db "SELECT id, role, substr(replace(content, char(10),' ⏎ '),1,400) FROM messages WHERE session_id='<session_id>' AND ((role='user') OR (role='assistant' AND content IS NOT NULL AND length(trim(content))>0)) ORDER BY id;"
```
- 回退路径：`session_search()` browse 模式兜底，但 **SQL 查出有会话而 browse 显示为空时，以 SQL 为准**，禁止直接判"安静的一天"。

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
Use `lark-cli im +messages-send` with bot identity. User identity (`--as user`) requires `im:message.send_as_user` scope which may not be available, especially in cron context.

🚨 **Cron 模式防重复铁律（2026-08-19 修复）**：
1. **先评分、后发送**：卡片必须等 Evaluator 全部维度 ≥7 通过后，才允许发送。禁止先发卡片再跑评分（会导致初版+修订版两张卡片都发出去）。
2. **发送后最终响应必须输出 `[SILENT]`**：cron 会自动投递 agent 的最终响应。若你已经用 lark-cli 发出卡片，最终响应必须只写 `[SILENT]`，否则用户会同时收到卡片 + cron 自动投递的文本，造成重复。
3. **二选一**：要么发卡片 + `[SILENT]`，要么不发卡片、直接把摘要文本作为最终响应让 cron 投递。禁止两者都做。

```bash
# Step 1: Build card JSON to a file (avoids shell backtick-escaping bugs)
python3 /tmp/build_card.py > /tmp/card.json

# Step 2: Send via lark-cli
lark-cli im +messages-send \
  --as bot \
  --user-id ou_dc055b0b5b0b5db2b1af5e79c0536db6 \
  --msg-type interactive \
  --content "$(cat /tmp/card.json)"
```

**Important**: Write the card-builder Python script to a file first via `write_file()`, then run it via `terminal()`. Do NOT embed Python inline via `python3 -c "..."` when the code contains backtick characters — bash interprets backticks as command substitution, silently corrupting markdown code spans. Use unicode escapes (`\u0060`) if inline Python is unavoidable.

The binary on this system is `lark-cli` (not `feishu-cli`). The `+messages-send` shortcut handles the call correctly.

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
- The card JSON must be properly serialized via `json.dumps(card, ensure_ascii=False)` — then passed as the `--content` argument to `lark-cli`
- Don't include every tiny interaction — only substantive discussions matter
- If session content is very long, sample key excerpts rather than trying to read everything
- **Cron mode blocks `execute_code`**: In cron jobs, `execute_code` is blocked. Write Python scripts to files with `write_file()` and run them via `terminal()` instead
- **Shell backtick escaping**: Never embed Python inline via `python3 -c "..."` when the code contains backtick characters (common in markdown code spans like `skill-name`). Bash interprets backticks as command substitution, breaking the script. Use `write_file()` to a temp script, or escape backticks as `\u0060`
- Use `lark-cli im +messages-send --as bot` (NOT `feishu-cli exec` or `--as user`) for sending cards. Bot identity works without additional scopes
- `lark-cli` (not `feishu-cli`) is the binary on this system

## 质检：Generator → Evaluator（强制）

本 Skill 产出每日摘要卡片，**必须经过 Evaluator 独立评分后才能交付**。

| 维度 | 阈值 | 检查要点 |
|------|------|---------|
| **关键决策覆盖** | ≥7 | 是否覆盖了当天所有实质性对话？有无遗漏重要决策？ |
| **待办可操作性** | ≥7 | 待办事项是否具体可执行？还是「跟进XX」式空泛？ |
| **简洁度** | ≥7 | 卡片是否精炼？有无冗余信息或无意义的交互记录？ |

Generator→Evaluator→全部≥7交付/修正重评（最多3轮）。禁止自评。
