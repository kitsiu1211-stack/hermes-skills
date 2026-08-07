# 会议纪要卡片模板

生成飞书 interactive 卡片时使用此 JSON 结构。

## 发送命令

```bash
lark-cli im +messages-send --as bot \
  --chat-id oc_e2f79ec1614a1efe1ebcd7c679bb45a8 \
  --msg-type interactive \
  --content '<JSON here>'
```

## 模板

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "📋 客户名 · 会议纪要"},
    "template": "green"
  },
  "elements": [
    {"tag": "div", "text": {"tag": "lark_md", "content": "**🕐 X 分钟**（HH:MM–HH:MM）| 👥 发言人列表"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**一、客户 AI 场景**\n**✅ 已实现**\n• 场景描述...\n• 链路：...\n\n**🔮 待实现**\n1. 需求描述...\n2. ..."}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**二、会议分析**\n类型：**产品沟通/售前方案/服务沟通**｜下一步：✅/❌ ..."}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "**三、C360**\n📦 商机：...｜📝 最近跟进：..."}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "🤖 Hermes自动生成 | {meeting_id}"}}
  ]
}
```

## 注意事项

- 内容超过 3000 字符时分两张卡，第二张续接
- C360 无数据时写"未查到"，不硬编
- 所有 `lark_md` 内容支持基本 Markdown（加粗、列表、链接）
- 标签（`#已落地` `#规划中`）放在场景描述前，不混入内容
