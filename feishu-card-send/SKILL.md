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

## 🚨 飞书卡片 markdown 的正确写法

`tag: markdown` 元素**不是标准 Markdown**。以下语法在飞书卡片中不支持：

| 错误 | 正确 |
|------|------|
| `## 标题` | `<font size=24 weight=bold>标题</font>` |
| `**加粗**` | `<font weight=bold>文字</font>` |
| `\|--\|--\|` 表格 | 纯文本空格对齐 或 `column_set` |
| `---` 分割线 | `{"tag": "hr"}` 独立元素 |

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
2. `header.title` 用 `tag: plain_text`
3. `elements[].text` 用 `tag: lark_md`（已验证可用）+ `<font>` 标签。`tag: markdown` 也可用但 `lark_md` 对 `<font>` 兼容更好。**不要用 `##` / `**` / 表格语法**。
4. `column_set` 必加 `"background_style": "default"`
5. 底部必须有 `tag: note` 标注数据来源和时间
6. 默认发到 Home `oc_e2f79ec1614a1efe1ebcd7c679bb45a8`
7. `im:message.send_as_user` 不可用，只用 bot

## chat_id 速查

- Home: `oc_e2f79ec1614a1efe1ebcd7c679bb45a8`
- Agent群: `oc_219a613c13292855c2dc4b80e59dfd6e`
