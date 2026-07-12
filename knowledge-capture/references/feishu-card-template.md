# 飞书卡片模板（知识捕获用）

当 MCP Feishu 不可用、无法写入知识图谱文档时，用此模板构造飞书卡片发送知识捕获摘要。

## 知识图谱卡片

```json
{
  "header": {
    "title": {"tag": "plain_text", "content": "📥 知识捕获：{标题}"},
    "template": "blue"
  },
  "elements": [
    {"tag": "div", "text": {"tag": "lark_md", "content": "**来源**：{来源} · {作者}\n**日期**：{日期} | **路由**：AI思考知识图谱\n**质检**：✅ 通过（{分数}/100）"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**Compiled Truth**\n> {compiled_truth}"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**关键要点**\n{key_points_bullets}"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**可行动项**\n{action_items}"}},
    {"tag": "hr"},
    {"tag": "note", "elements": [{"tag": "plain_text", "content": "{tags}"}]}
  ]
}
```

## 关键规则

- 卡片标题 ≤ 20 字
- key_points 最多 5 条，用 `• ` 开头
- 每条内容精简，手机屏幕不滚动超过 2 屏
- 如有 URL，在来源行附上
- 占位文本检查：禁止「（未提取到」「（待补充」等字眼出现在最终卡片中
