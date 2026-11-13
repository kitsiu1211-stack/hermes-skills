---
name: feishu-card-send
description: Send structured content as Feishu interactive cards via bot — correct <font> syntax, column_set layout, note footer
category: feishu
---

# 飞书卡片发送

表格、对比、结构化信息 → 飞书卡片。纯文本回复 → Hermes 直接输出。所有定时任务输出、会议纪要、C360 客户画像必须用卡片。

## 触发

输出包含表格、对比、多段结构化信息时自动触发。

---

## 飞书卡片文本格式

### 推荐：`tag: lark_md`（简洁，支持 Markdown）

```json
{"tag": "div", "text": {"tag": "lark_md", "content": "**加粗**内容\n\n换行段落"}}
```

✅ 支持 **加粗**、`\n` 换行、emoji
❌ 不支持 `<font>` 标签、表格、`##` 标题

### 旧版：`tag: markdown`（需 `<font>` 标签）

以下语法在飞书卡片中不支持：

| 错误 | 正确 |
|------|------|
| **加粗** | `<font weight=bold>文字</font>` |
| `## 标题` | `<font size=24 weight=bold>标题</font>` |
| 表格 | 纯文本空格对齐 或 `column_set` |
| `---` 分割线 | `{"tag": "hr"}` 独立元素 |

**选择**：内容型卡片用 `lark_md`（少写标签），数据看板用 `markdown`+`<font>`（更精细控制）

## 完整卡片 JSON 骨架

🚨 **`column_set` 必须加 `"background_style": "default"`** — 不加是裸数字，加了才是灰底圆角卡片框。

```json
{
  "config": { "wide_screen_mode": true },
  "header": {
    "template": "blue",
    "title": { "tag": "plain_text", "content": "📌 标题 | 一句话摘要" }
  },
  "elements": [
    {
      "tag": "column_set",
      "flex_mode": "none",
      "background_style": "default",
      "columns": [
        {
          "tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
          "elements": [{ "tag": "markdown", "content": "<font size=24 weight=bold>数值</font>\n<font size=14 color=orange>状态标签</font>\n<font size=12 color=grey>单位说明</font>" }]
        }
      ]
    },
    { "tag": "hr" },
    { "tag": "markdown", "content": "<font size=16 weight=bold>小节标题</font>\n\n正文内容..." },
    { "tag": "hr" },
    { "tag": "note", "elements": [{ "tag": "plain_text", "content": "数据截至 YYYY-MM-DD HH:mm，来源：XXX" }] }
  ]
}
```

## `<font>` 标签速查

| 属性 | 写法 | 建议值 |
|------|------|------|
| 大字号标题 | `<font size=24 weight=bold>` | 20-28 |
| 小节标题 | `<font size=16 weight=bold>` | 16 |
| 加粗 | `<font weight=bold>` | - |
| 颜色 | `<font color=red>` | red/green/blue/grey/orange |
| 正常大小 | `<font size=14>` | 14 |

## 颜色约定

| 场景 | 颜色 |
|------|------|
| 上涨 / 好消息 / 达成 | `blue` 或 `green` |
| 下跌 / 风险 / 警告 | `red` |
| 高危 / 紧急 | `red` + `🚨` |
| 中性状态 | `grey` |
| 需关注 | `orange` |

## 顶部统计卡片（4 列 `column_set`）

🚨 **必须加 `"background_style": "default"` 在 `column_set` 上**，不加就是一排裸数字，加了才是四个灰底圆角卡片框。

```json
{
  "tag": "column_set",
  "flex_mode": "none",
  "background_style": "default",
  "columns": [
    {
      "tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
      "elements": [{ "tag": "markdown", "content": "<font size=24 weight=bold>12+</font>\n<font size=14 color=orange>需补记录</font>\n<font size=12 color=grey>一号位建联</font>" }]
    },
    { "... 3 more columns ..." }
  ]
}
```

每列 3 行：大数字 → 状态/涨跌 → 单位标注。手机端一屏四列。

## 定时任务/核验类汇报卡片（用户明确要求）

cron 任务的最终回复不要甩一整段文字。固定骨架：

1. 顶部 3 列 `column_set` 放最硬的数字（通过 N 项 / 失败 N 项 / 关键异常数），颜色 green/red/orange
2. 分节 `hr` + 小节标题：✅ 通过的 / ❌ 没通过的 / 🔍 关键发现 / ⚖️ 一句话判断 / 🎯 下周硬指标
3. 每节 1-3 条加粗要点，一条一行，不写长句
4. 结尾单独一节放「等你一句话」的待决策项，其余细节进 note
5. **禁止搬原文**：不写 message_id、omt_ 话题 ID、毫秒时间戳、receipts.log 字段名——这些搬到卡里等于没做摘要

## 反模式（禁止）

| 错误 | 为什么 | 后果 |
|------|------|------|
| 顶部数字用表格 | 扫读慢，视觉重量不够 | 用户懒得看 |
| 整段文字无小节标题 | 找不到焦点 | 信息密度塌方 |
| 涨跌塞在长句里 | 要单独成行+箭头/颜色 | 找不到关键数字 |
| 没 `note` 底部 | 专业度归零 | 像临时拼的 |
| **`column_set` 不加 `background_style`** | 四个裸数字，不是卡片框 | 排版塌了 |
| 用 `##` / `**` / 表格在 markdown 里 | 飞书不支持 | 卡片渲染错乱 |
| **`<font color='red'>` 用了引号** | 飞书卡片 markdown 不认属性引号 | 颜色失效，卡片可能发送失败 |
| **`note` 元素里用了 `<a>` 标签** | `note` 的 `elements` 只支持 `plain_text`，URL 用纯文本 | 卡片发送报 230099 parse card json err |

## 发送命令

```bash
lark-cli im +messages-send \
  --as bot \
  --msg-type interactive \
  --chat-id "<chat_id>" \
  --content '<JSON>'
```

## 铁律

1. `--msg-type interactive` + `--as bot`
2. **JSON 必须用 Python `json.dumps()` 构建**，禁止 bash 变量拼接。bash 中换行符会被写成字面量导致卡片显示原始转义符。正确做法：python3.11 内直接写多行字符串 + json.dumps()。
3. `header.title` 用 `tag: plain_text`
4. `elements[].text` 用 `tag: lark_md`（已验证可用 + `<font>` 标签。不要用 `##` / `**` / 表格语法。
5. column_set 必加 background_style default
6. 底部必须有 `tag: note` 标注数据来源和时间
7. 默认发到 Home `oc_e2f79ec1614a1efe1ebcd7c679bb45a8`
8. `im:message.send_as_user` 不可用，只用 bot

## chat_id 速查

- Home: `oc_e2f79ec1614a1efe1ebcd7c679bb45a8`
- Agent群: `oc_219a613c13292855c2dc4b80e59dfd6e`
