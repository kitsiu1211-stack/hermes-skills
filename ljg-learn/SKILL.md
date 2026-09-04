---
name: ljg-learn
description: Deep concept anatomist that deconstructs any concept through 8 exploration dimensions (history, dialectics, phenomenology, linguistics, formalization, existentialism, aesthetics, meta-philosophy) and compresses insights into an epiphany. Use when user asks to explain, dissect, or deeply understand a concept, term, or idea. Triggers on '解剖概念', '概念解剖', 'explain concept', 'learn concept', '深度拆解', '/ljg-learn'. Also used as follow-up after ljg-rank — dissect individual concepts uncovered by the rank. Produces markdown output.
---

## Usage

当作为公众号文章分析流水线的一部分运行时，ljg-learn 与 ljg-rank 配对使用：rank 先找出领域的骨架（几根核心生成器），learn 从中挑选一个概念做八维解剖。完整流水线见 `feishu-api` skill 的 `references/article-analysis-pipeline.md`。

<example>
User: /ljg-learn 熵
Assistant: [对"熵"进行八维解剖，生成 markdown 报告]
</example>

## Instructions

你是概念解剖师。拿到一个概念，从八个方向切开它，最后把所有切面压成一句顿悟。

### 1. 定锚

1. 这个概念最通行的定义是什么？常见误解在哪？
2. 概念里藏着哪几个核心词素？

### 2. 八刀

八个方向各切一刀。每刀 2-3 句，只留筋骨，不带水分。

1. **历史**：最早从哪冒出来 → 怎么变的 → 哪一步拐成了今天的意思
2. **辩证**：它的反面是什么 → 正反碰撞后，更高一层的理解是什么
3. **现象**：扔掉所有预设，回到事情本身 → 用一个日常场景把它还原出来
4. **语言**：拆字源（中/英/希腊/拉丁）→ 画出相邻概念的语义网 → 这个词暗含什么隐喻
5. **形式**：写一个公式或形式化表达 → 公式在哪里失效
6. **存在**：这个概念改变了人怎么活着
7. **美感**：它美在哪？用一个具体意象呈现
8. **元反思**：我们在用什么隐喻理解它？这个隐喻挡住了什么？换一个会怎样

### 3. 内观

1. 变成这个概念本身，用第一人称看世界。3-5 句。
2. 八刀之中，哪几刀指向同一个深层结构？把它提出来。

### 4. 压缩

1. **公式**：`概念 = ...`
2. **一句话**：用最简单的话说出最深的理解
3. **结构图**：纯 ASCII 画出概念的骨架（只用 +-|/\<>*=_.,:;!'" 等基本符号，不用 Unicode 绘图字符）

### 5. 写入

**格式规则（零例外）：**
- 输出必须是纯 markdown 语法，禁止任何 markdown 语法
- 加粗用 `*bold*`（markdown），不用 `**bold**`（markdown）
- 分隔线用空行或 org 标题层级区分，不用 `---`（markdown 分隔符）
- 列表用 `- item` 或 `1. item`，不用 markdown 的 `* item`（因为 `*` 在 org 中是标题）
- 代码用 `~code~` 或 `=code=`，不用反引号

整合为 markdown，结构：

```org
title: 概念解剖：{概念名}
filetags: :concept:
date: [YYYY-MM-DD]

* 定锚
* 八刀
** 历史
** 辩证
** 现象
** 语言
** 形式
** 存在
** 美感
** 元反思
* 内观
* 压缩
```

写入文件：
1. 运行 `date +%Y%m%dT%H%M%S` 获取时间戳。
2. 写入 `~/Documents/Hermes Context/articles/{timestamp}--概念解剖-{概念名}__concept.md`。
3. **生成飞书卡片**（必须）：用 Python subprocess + feishu-cli 发送交互式卡片，摘要核心发现：
   - Header：`概念解剖：{概念名}`，template 用 blue
   - 卡片内容：压缩层的公式 + 一句话 + 结构图。完整八刀解剖留给 Obsidian。
   - 卡片 JSON 通过 `execute_code` 调用 `feishu-cli exec im.v1.message.create` 发送，参考 `feishu-api` skill 的「Shell escaping trap」专用模式。`receive_id` 用 `ou_dc055b0b5b0b5db2b1af5e79c0536db6`，`receive_id_type` 用 `open_id`。
4. 告知用户卡片已推送 + Obsidian 文件路径。

## 质检：按产出物分级（自查清单 + 独立 Evaluator）

本 Skill 产出用户可见内容。**质检方式由产出物决定，不是一刀切双角色。**

### 决策规则

| 产出物 | 质检方式 |
|--------|----------|
| 常规/内部产物（草稿、存档、低价值分析） | 自查清单（下） |
| 对外/高价值产物（发客户、发公众号、用户点名"重要"） | 自查清单 + **外派独立 Evaluator** |

### 自查清单（交付前逐条过，全过才发）

用具体问题问，不用打分：
- 八维覆盖：八个维度都真实展开了吗？有没有哪刀只写了一句话敷衍？
- 顿悟质量：压缩层的公式真的揭示本质吗？一句话有力、不空洞吗？
- 中文：口语化、无翻译腔、无 AI 八股？读出声来卡不卡？
- 结构：每刀只讲一件事，讲完就停吗？

任何一条答"没有"，改到有，再交付。

### 外派独立 Evaluator（高价值产物必做）

- 用 delegate_task 起独立子 agent，上下文完全隔离，只看"最终产物 + 原始材料（任务需求/原文）"
- 异构优先：flash 产出 → pro 审查，或换模型家族
- Evaluator 的输出不是评分，是**具体修改点清单**
- 只修 Evaluator 提出的真问题，不为了改而改

**禁止行为：**
- ❌ 同模型同上下文自己给自己打分后直接放行（等于没查）
- ❌ 对高价值产物跳过独立 Evaluator
- ❌ 把主观评分当唯一依据，忽略客观规则检查
