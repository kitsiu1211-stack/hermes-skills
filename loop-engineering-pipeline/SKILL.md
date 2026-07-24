---
name: loop-engineering-pipeline
description: |
  Matt Pocock Loop Engineering 开发专用流水线。从模糊需求到可交付代码的端到端流程。
  触发词：loop、开始 loop、loop engineering、走流水线、按流水线来。
  自动走完：setup → grill → to-spec → to-tickets → implement → handoff。
  支持 TRAE 协作模式：to-tickets 后调度 TRAE 实现 → 本地测试 → 报错喂回 → 循环到通过。
---

# Loop Engineering Pipeline

开发专用全链路流水线。模糊需求 → 可交付代码。

**上游**：日常方案孵化用 `diverge-converge`（扩散收敛法），聊出来是软件方案后切 loop。

## 流水线阶段

```
setup-matt-pocock-skills    ← 一次性：初始化项目（issue 路径、标签、CONTEXT.md）
        ↓
grill-with-docs             ← 追问需求 + 领域建模 + 写 ADR
        ↓                     ★ 每轮一问 + 置信度 + 对比表格
to-spec                     ← 讨论内容 → 结构化 PRD/规范文档
        ↓
to-tickets                  ← PRD → 拆分为 tracer-bullet tickets（含依赖关系）
        ↓
implement                   ← 逐个 ticket 实现（TDD + 代码审查）
        ↓                     或 TRAE 协作模式（见下方）
handoff                     ← 输出交接文档，可被下一个 Agent 继承
```

## 如何使用

### 方式一：完整流水线（推荐）

用户说 **「loop」** 或 **「走流水线」** 时，自动按阶段推进。每个阶段结束时暂停，让用户确认再进下一阶段。

### 方式二：单步触发

- 「grill 一下这个需求」→ 只跑追问
- 「出个 spec」→ 只跑 to-spec
- 「拆任务」→ 只跑 to-tickets
- 「实现 #3 ticket」→ 只跑 implement

### 方式三：TRAE 协作模式

当用户明确要用 TRAE 编码时（如「loop，让 TRAE 做」）：

1. **grill + to-spec + to-tickets**：照常走前三阶段，产出清晰 tickets
2. **调度 TRAE**：将 ticket 以文本形式发给 TRAE（飞书消息），要求它以文件/Gist 形式提交代码
3. **本地测试**：下载 TRAE 的代码到本地，运行测试
4. **报错喂回**：将精确错误信息发给 TRAE，让它修复
5. **循环**：重复 3-4 直到通过
6. **审查 + 交接**：通过后跑 code-review，输出 handoff

**TRAE 模式规则**：
- 一次只给 TRAE 一个 ticket（不要一次丢多个）
- 必须让 TRAE 发文件链接或代码块，不接受截图
- 本地跑完所有测试才判定通过
- 最多 5 轮循环，超过则标记为需要人工介入

## grill 阶段

由 `grill-with-docs` 驱动（diverge-converge 和 loop-engineering-pipeline 的共用追问内核）：

1. **每轮只问一个问题**——最关键的分叉
2. **带置信度**：如「建议方案 B，置信度 85%」
3. **对比表格**：两三个方案并列，优劣对比，最优标出
4. **决策台账**：记录每条决策 + 依据 + 被否决的方案 + 否决理由

## 关键原则

1. **绝不跳过阶段**：不跳过 setup/grill 直接写代码
2. **追问到底**：grill 不结束，直到没有遗留问题
3. **垂直切片**：每个 ticket 是端到端 tracer bullet
4. **红-绿循环**：implement 必须 TDD
5. **审查即完成**：code-review 通过才算 ticket done

## 项目文件结构

```
.scratch/<feature-slug>/
  issues/           ← to-tickets 产出
    01-xxx.md
    02-xxx.md
  decisions.md      ← grill 产出的决策台账
docs/
  agents/
    issue-tracker.md
    domain.md
  adr/              ← grill-with-docs 产出的 ADR
CONTEXT.md
```

## 与 diverge-converge 的分工

| | diverge-converge | loop-engineering-pipeline |
|---|---|---|
| **触发** | 扩散收敛、帮我想想、看清全貌 | loop、走流水线、开发这个 |
| **交付** | 决策手稿 | 可运行代码 |
| **场景** | 研究、商业、产品、规划 | 软件开发、bug 修复 |
| **关系** | 上游（聊出软件方案后切 loop） | 下游（只做工程实现） |
| **追问内核** | `grill-with-docs` | `grill-with-docs` |

**与 `diverge-converge` 共用 `grill-with-docs` 作为追问内核。**
