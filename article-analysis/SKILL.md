---
name: 文章分析
description: 分析用户分享的公众号推文/网页文章，纯提取核心观点，不关联外部知识，输出飞书卡片
triggers:
  - 用户发送微信公众号/网页文章链接
  - 用户说"分析一下这篇文章""总结一下"
---

# 文章分析（纯提取，不关联）

## 架构

1 Generator + 1 Evaluator

```
文章全文 → Generator（提取核心观点）→ Evaluator（校验准确性）→ 飞书卡片
```

---

## Phase 1: Generator（观点提取）

### 身份
"你正在阅读一篇文章。你的任务是客观提取作者的核心观点和关键信息，不做任何延伸。"

### 步骤
1. 获取文章全文
   - **飞书文档/知识库**：`lark-cli docs +fetch --doc <url> --doc-format markdown`（速度更快，不用 browser）
   - **微信公众号/外部网页**：`browser_navigate` + `browser_console` 提取 `#js_content`
2. 提取以下结构化信息：
   - **标题 + 来源 + 日期**
   - **核心观点**（3-5 条，每条一句话，引用原文关键表述）
   - **关键数据/案例**（如有，列出具体数字和名称）
   - **文章结构**（作者分了几部分？每部分讲什么？）
3. 输出到内部结构，不做关联

### 约束
- 不关联任何外部知识
- 不添加自己的解读
- 不对比其他文章
- 不评价观点的对错
- 如果文章是对话/圆桌形式，标注每位发言人的核心观点

---

## Phase 2: Evaluator（准确性校验）

### 身份
"你在审核一份文章摘要。你的任务是逐条核对摘要是否忠实于原文，没读过的内容不评论。"

### 评分维度（≥70% 每条）

| 维度 | 检查点 |
|------|--------|
| 忠实度 | 每条观点能否在原文找到直接出处？有没有添加原文没有的内容？ |
| 完整性 | 原文的主要段落/观点是否都覆盖了？有没有遗漏重要信息？ |
| 准确性 | 数据/人名/案例是否与原文一致？有没有记混？ |

### 处理
- 全部通过 → 输出飞书卡片
- 有误 → 修正后重新评估（最多 3 轮）
- 3 轮后仍不通过 → 标注不通过的部分，输出卡片时注明

---

## 输出格式：飞书卡片

使用 `lark-cli im +messages-send --as bot --msg-type interactive`。

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "文章标题"},
    "template": "blue"
  },
  "elements": [
    {"tag": "div", "text": {"tag": "lark_md", "content": "来源 · 日期"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "<font color='blue'>核心观点</font>\n\n1. 观点一（引用原文表述）\n2. 观点二\n..."}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "<font color='blue'>关键数据/案例</font>\n\n· 数据1\n· 案例1"}},
    {"tag": "hr"},
    {"tag": "div", "text": {"tag": "lark_md", "content": "<font color='grey'>原文链接</font>"}}
  ]
}
```

### 约束
- 飞书卡片不支持 `##`、`**`、表格，使用 `<font>` 标签
- **`<font>` 属性不能加引号**：`<font color=blue>` ✅，`<font color='blue'>` ❌（卡片会发送失败）
- 卡片内容纯分析，不含任何"与之前讨论的关联""延伸思考"等内容
- 不发原文全文，只发卡片

---

## 发送

发送到用户飞书 Home 频道（`oc_e2f79ec1614a1efe1ebcd7c679bb45a8`）。

---

## 示例

输入：用户分享 https://mp.weixin.qq.com/s/xxx
输出：飞书卡片，标题 + 来源 + 核心观点（3-5 条纯引用） + 关键数据
