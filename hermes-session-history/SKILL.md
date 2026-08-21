---
name: hermes-session-history
description: Use when querying Hermes session history (state.db SQL).
category: productivity
---

# Hermes Session History 查询

高效读取 Hermes 会话历史（session_search 工具 + state.db 直查）的两种路径及取舍。

## 触发

- 生成每日/每周工作摘要（如 daily-session-summary）
- 用户问「上次我们 X 做到哪了」「找一下 Y 那次会话」
- 跨 session 回查、调试「为什么当时做了 Z」

## 两条路径

| 路径 | 工具 | 适用 | 局限 |
|------|------|------|------|
| A | `session_search` | 快速发现、语义检索、定位到具体消息 | scroll/read 会把 tool 响应一起返回，密集会话撑爆上下文 |
| B | `sqlite3 ~/.hermes/state.db` | 批量抽取、生成摘要、只取 user+assistant 文本 | 需手写 SQL；schema 随版本可能变，先 `.schema` |

**长会话/摘要类任务首选 B**，因为 A 的 scroll 模式对多工具会话（会议旁听、网页搜索、批量文件操作）单次滚动轻松 200KB+，直接超出上下文预算。

## 路径 A：session_search 四种形态

1. **BROWSE**（无参）— 列出最近会话（id/title/source/when/message_count/preview）
2. **DISCOVERY**（`query=`）— FTS5 语义检索，去重后返回 top-N 会话（含 bookends + 命中上下文）
3. **SCROLL**（`session_id` + `around_message_id`）— 读单个会话的消息窗口，用 `messages[-1].id` / `messages[0].id` 前后翻页
4. **READ**（仅 `session_id`）— 大会话 dump 首 20 + 末 10 条

## 路径 B：state.db 直查

数据库位置：`~/.hermes/state.db`（找不到就 `find ~/.hermes -name state.db`）。查之前先看 schema 确认列名：

```bash
sqlite3 ~/.hermes/state.db ".tables"          # sessions / messages / messages_fts ...
sqlite3 ~/.hermes/state.db ".schema messages" # 列名以当前版本为准
```

### 当天会话清单（先看 message_count 判断体量）

```bash
sqlite3 ~/.hermes/state.db "SELECT id, source, title, datetime(started_at,'unixepoch','localtime') started, message_count FROM sessions WHERE started_at >= strftime('%s','2026-08-13 00:00:00','utc') ORDER BY started_at;"
```

### 单会话抽 user + 有内容的 assistant 文本（过滤 tool 响应）

```bash
sqlite3 ~/.hermes/state.db "SELECT id, role, substr(replace(content, char(10),' ⏎ '),1,400) FROM messages WHERE session_id='<session_id>' AND ((role='user') OR (role='assistant' AND content IS NOT NULL AND length(trim(content))>0)) ORDER BY id;"
```

要点：
- `role='tool'` 的消息是工具返回值，摘要任务直接排除
- `assistant` 消息若 `content` 为空只有 `tool_calls` 字段，也排除（`length(trim(content))>0`）
- `char(10)` → `⏎` 和 `substr(...,1,400)` 让每行在终端里单行可读
- `started_at` 是 Unix epoch 秒（REAL），用 `strftime('%s','<date>','utc')` 比较

## Pitfalls

- **`role_filter` 参数在 scroll 模式不真正过滤 tool 响应**：`tool_calls` 字段仍随 assistant 消息返回。别指望它给密集会话瘦身，直接上 sqlite。
- **READ 形态对大会话只给首尾**，中间内容靠 SCROLL 逐页翻，token 代价高。
- session_search 只搜 Hermes 会话库，**不是外部源当前内容的证据**——用户给了 URL/文件/线程时先查原始源。
- 会话文件（`~/.hermes/sessions/*.json`）只存旧会话快照；近期的会话都在 state.db 里。

## 关联

- `daily-session-summary` 每天 21:00 用本文的路径 B 抽当天 feishu 会话做摘要（该 skill 目前 user-owned，未 curator 托管）。
