---
name: opportunity-cross-analysis
description: Cross-reference meeting intelligence with Base/C360 system-of-record data to produce accurate AI opportunity lists. Use when the user asks to compile, cross-check, or analyze customer opportunities across multiple CSM owners — especially after a series of盘点 meetings.
category: productivity
---

# Opportunity Cross-Analysis

## Trigger

用户要求整理、盘点、交叉分析多位 CSM 名下的 AI 商机，尤其是：
- 开了一系列盘点会（一人或多人）之后要求汇总
- 给出了 Base 多维表格链接要求对账
- 说"整理商机情况""生成分析文档"

## Core Principle

**Base 是 system of record，会议是 field intelligence。始终以 Base 为准做最终统计，会议内容作为定性补充。**

不要用手工估算替代系统数据——用户手工列的表经常漏客户或混入已购。

## Workflow

### Step 1: 收集会议情报

从以下来源提取商机线索：
- 会议旁听字幕 / 妙记
- 用户在聊天中 @ 你参与的讨论
- session_search 跨话题搜索相关盘点记录

输出一份初步的客户-商机映射表。此时**不区分已购 vs 新商机**——只是情报收集。

### Step 2: 对账 Base 数据

用户通常会给出 Base 链接（南区区域AI总表 → 每日更新-客户商机表）。

**关键字段**：`Q3 AI 商机盘点`（字段 ID: `fldxplYlHm`）

**判断规则（用户原话）**：
- `Q3 AI 商机盘点` 字段为空、`/`、或以 `无商机` 开头 → **不是新商机**
- 其他任何非空值 → **是新商机**（含 `待确认`、`刚交接`、具体金额描述）

### Step 3: 查询命令

```bash
# 分页拉取全表（limit 最大 200）
lark-cli base +record-list \
  --base-token "<token>" \
  --table-id "tblNTJtyLAeIPqN1" \
  --limit 200 \
  --offset <offset> \
  --as user
```

**输出格式**：Markdown 表格（不是 JSON）。用 Python 解析表头定位列索引。

**目标人员映射**（按 `客户所有人` 字段过滤）：
- 袁鑫杰、陈少特、叶珊珊、何月楠（Luna）、王梦迪

**踩坑**：
- 不要用 `--json` 或 `--format json`（CLI 不支持，返回空）
- 不要用 `--field-ids` 过滤（可能导致空结果）
- `--limit` 最大 200，需循环 offset 直到 `has_more=false`
- 用户字段是 JSON 字符串 `[{"id":"ou_xxx","name":"姓名"}]`，用 `json.loads()` 解析

### Step 4: 输出分类

按「已购 vs 新商机」分开：

**已购**：Base 标记 `无商机` 的客户中，那些曾经买过 AI 包的。从会议情报中提取购买路径（知识问答 / aily / 随飞书捆绑等）。

**新商机**：Base 标记非 `无商机` 的客户。按金额档分类：
- 9.9 万
- 29.7 万
- 49.5 万
- 99 万
- 待确认 / 刚交接

### Step 5: 定性分析

结合会议情报补充：
- **Solid 判断**：消耗加速 / CSM 在推 / AI 效率先锋带动的 → 高确定性
- **风险点**：顾虑豆包 / 组织问题 / 缺场景 / AB 面恐惧
- **行业差异**：大制造 vs 消费电子 vs 企业服务 vs 大消费 vs 游戏的 AI 成熟度和切入路径

### Step 6: 写入云文档

用 `lark-cli docs +create` 或 `+update --command overwrite` 生成结构化文档，包含：
1. 行业特征速览表
2. 商机金额分布
3. 各人商机明细
4. 跨行业共性发现
5. 行业差异矩阵
6. 待办行动方案

## 赢单经验蒸馏（变体：过程 → 路径打法）2026-08-26

**触发**：用户说「把 XX、XX 和我的 AI 赢单内容整理分析」「蒸馏赢单」「沉淀路径打法」。

**用户明确否定的框架**：❌ 五行业打法对照表、❌ 三档（9.9/29.7/99）方法论。这两类输出用户会直接说「不需要」。

**用户要的**：✅ 每个人的**赢单过程**（客户原状态 → 触发点 → 推动动作 → 成交 → 后续），再从过程里**沉淀出可复制的路径/打法**。

**素材来源优先级**：
1. 当天旁听的蒸馏会字幕（标题模式「蒸馏 xx AI 赢单经验」「xx AI 售卖经验蒸馏」）
2. **妙记**（用户常把蒸馏会录成妙记）——先搜妙记再断言「待补听」：
   ```bash
   lark-cli minutes +search --as user --query "蒸馏老王" --format json
   # 返回 items[].token（不是 id/topic！）+ display_info 含关键词/时长
   lark-cli minutes +detail --as user --minute-tokens "<tok1>,<tok2>" \
     --summary --todo --transcript --output-dir ./minutes
   # ⚠️ --output-dir 必须相对路径（绝对路径被拒）；逐字稿写文件，summary/todos 在 JSON
   ```
3. Base 商机明细（无蒸馏/妙记时兜底，仅客户+金额，无过程）

**过程记录格式**：按人分组，每人列出客户 + 关键过程链（谁拍板 / 什么活动推动 / 用量数据 / 什么话术生效），一条路径一句。

## Deep Grill 自审（交付前必做，2026-08-26 用户要求）

用户说「你自己 Deep grill 一下，我觉得还是差了点东西」= 上一版缺实质。交付赢单沉淀前先自审五问：

1. **新签/增购/续约区分了吗**？混在一起提炼路径是硬伤——「额度用完续充」不是赢单方法论
2. **升级信号指标给了吗**？只说「用量高」不够——要可量化触发器（消耗率×倍、激活人数、额度耗尽速度）
3. **失败模式有吗**？被拒/零消耗/卡预算/客户投诉这些反例才是防坑指南
4. **协同机制写了没**？大赛靠市场、测算靠 CSM、大单靠多人协同——资源前提不交代新人无法复制
5. **冷静期/竞品应对空白吗**？客户进 ROI 核算期、在 Codex 花 200 万——应对话术要有

输出形态从「分析报告」改成「可抄作业的手册」，发群同事直接能用。

详见 `references/win-bid-distillation.md`（5 人 27 案例盘点 + 完整命令）。

## Pitfalls

- **不要混入已购客户当新商机**。用户明确区分"本季度增购或新购"才算商机
- **不要用手工估算替代 Base 数据**。手工汇总几乎总是漏客户——Base 里的商机数往往比预估多得多
- **珊珊和梦迪的盘点会经常没旁听到**，但她们的 data 在 Base 里是完整的——先拉 Base 数据，再标注"会议未旁听"
- **先搜妙记再断言"待补听"**。用户常已录妙记（「蒸馏老王」「警官 AI 售卖经验蒸馏」即梦迪/月楠），说"待补听"会让用户纠正「不用补听，妙记就是聊完了」
- **拓竹 "已99" 不是商机**，但 Base 里可能有 9.9 万扩容包作为新商机
