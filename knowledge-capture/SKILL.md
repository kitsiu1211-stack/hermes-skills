---
name: knowledge-capture
label: 知识捕获统一入口
description: >
  统一的知识捕获入口，只在用户明确要求持久化时触发（非自动）。
  强制执行 Generator → Evaluator 质检流水线（三维度评分，<70% 禁止写入）。
  双轨存储：外部输入 → AI思考知识图谱（Compiled Truth + Timeline），
  原创感悟 → 成长图谱（体系篇+功能篇）。
---

# Knowledge Capture — 知识捕获统一入口

> 版本: v1.0.4 | 基于 彦祖 & 马斯克 v1.0.3 设计 | 适配 Hermes Agent

## ⚡ 触发条件（最高优先级 — 2026.5.31 用户纠正）

**本 Skill 只在用户明确要求持久化知识时才激活。文章链接本身不是触发信号。**

| 用户行为 | 处理方式 |
|----------|---------|
| 分享公众号文章 / 链接（无其他指令） | ❌ **不触发** — 直接总结内容，发飞书卡片 |
| 说「写入」「记下来」「保存」「存一下」 | ✅ 触发完整流水线 |
| 说「写进Obsidian」「写入Obsidian」「存到Obsidian」 | ✅ 触发 — 路由到知识图谱 → 走 Obsidian 直写路径（跳过 Generator/Evaluator） |
| 说「帮我写进思考文档」 | ✅ 触发 — 路由到成长图谱 |
| 链接 +「提炼存起来」 | ✅ 触发 — 路由到知识图谱 |

**判断原则：** 文章链接本身不是触发信号——它是信息输入，不是存储指令。用户没说关键词 = 不触发。即使发了十篇文章也只做总结卡片，不走流水线。

## 核心价值

| 能力 | 说明 |
|------|------|
| **统一入口** | 一个指令处理所有知识捕获，自动路由，无需用户选择目标 |
| **双轨存储** | 外部学习 → 知识图谱（G-Brain），原创思考 → 成长图谱（日记式） |
| **独立质检** | Generator 生成 + Evaluator 独立脚本质检，评分 ≥85% 放行，<70% 打回 |
| **复习就绪** | 知识图谱格式兼容艾宾浩斯复习系统（ebbinghaus-review） |

---

## ⚠️ 强制执行规则（不可跳过）

```
Step 1: Router 识别路由 → Step 2: Generator 生成 → Step 3: Evaluator 质检 → Step 4: 双轨写入
                                                              ↑                           ↑
                                                              └─── 禁止直接跳过 ──────────┘
```

**🚫 禁止行为：**
1. ❌ 跳过 Evaluator 直接写入
2. ❌ 自己充当 Evaluator（必须调用 `python scripts/evaluator.py`）
3. ❌ Evaluator 评分 <70% 时写入（最多重试 3 次修正）
4. ❌ 忽略「格式错误」「空章节」等严重问题

---

## Step 1: Router 内容识别（LLM 执行）

**路由决策表：**

| 特征 | 信号词 | 目标 | 格式 |
|------|--------|------|------|
| 含 URL / 分享链接 | `http` | 知识图谱 | Compiled Truth + Timeline |
| 文章/播客/书/会议/笔记/摘录 | `文章、播客、书、会议、读了、听了、看了、笔记、摘录` | 知识图谱 | Compiled Truth + Timeline |
| 原创感悟/思考/复盘 | `我觉得、感悟、复盘、思考、想法、灵感、突然想到` | 成长图谱 | 体系篇 + 功能篇 |
| 今天/最近/刚才的思考 | `今天、最近、刚才` | 成长图谱 | 体系篇 + 功能篇 |
| **两侧分数相等** | — | **询问用户** | — |

**判断逻辑：** 统计两侧信号词命中数量，得分高的一方决定路由。平局则 `clarify()` 询问用户。

---

## Step 2: Generator 生成

**执行命令：**
```bash
cd ~/.hermes/skills/knowledge-capture && python scripts/generator.py \
  --input "{LLM提炼的结构化内容}" \
  --route "{growth_graph | knowledge_graph}" \
  --title "{清洁标题}" \
  --source "{清洁来源名}" \
  --url "{可选来源URL}" \
  --tags "{手动标签，逗号分隔}" \
  --output /tmp/generator_output.json
```

**重要**：`--input` 不应是原始用户输入，而是 LLM 提炼后的结构化摘要。`--title` 和 `--source` 用于传入清洁元数据。

---

## Step 3: Evaluator 独立质检（强制）

**执行命令：**
```bash
cd ~/.hermes/skills/knowledge-capture && python scripts/evaluator.py \
  --input /tmp/generator_output.json
```

**三维度质检表：**

| 维度 | 检查项 | 权重 | 不合格处理 |
|------|--------|------|-----------|
| **准确性** | 路由正确、来源标注完整 | 25% | ❌ 重新路由 |
| **完整性** | 核心洞察不空、格式规范、标签完整、必填章节不空 | 50% | ❌ 补充/修正 |
| **可用性** | 内容长度合理（100-2000 字符）、无空章节、无占位符 | 25% | ⚠️ 优化表述 |

**判定规则：**
- ✅ **通过**（≥85 分）：进入 Step 4 写入
- ⚠️ **警告**（70-84 分）：根据提示优化 → 重新质检 → 通过后写入
- ❌ **打回**（<70 分）：**禁止写入**，分析报告后修正。最多重试 3 次。

---

## Step 4: 双轨写入

### 4a. 写入成长图谱（growth_graph）

**目标文档：** `TPtddJcIxozz63xykfDcadKIn7d`（Feishu docx）

**格式规范：**
```markdown
## 2026.5.31（星期日）
主题：AI落地"底线-上限"框架

### 一句话引入
> 企业AI落地的真正瓶颈不是技术，而是组织形态...

### 体系篇
**核心洞察：组织是AI落地的底线，场景是AI落地的上限**
...

### 功能篇
**ISV销售实战应用：**
...

### 一句话总结
> 底线之上，上限才高。
```

**写入规则：**
- 日期格式：`YYYY.M.D`（点分隔）+ `（星期X）`
- 新日期插入到介绍文字之后、第一个日期条目之前（倒序）
- 同日期已有内容追加到末尾
- 一次只写一个日期，多条内容合并为一个条目
- 写入后读前 50 block 验证
- 内容 > 30 block 时给出完整 Markdown 让用户手动粘贴

### 4b. 写入 AI思考知识图谱（knowledge_graph）

**目标：** Obsidian vault — `~/Documents/Obsidian Vault/concepts/`

**何时走此路径：**
- 用户说「写入Obsidian」「写进Obsidian」
- 含外部分享链接 + 存储指令（路由到知识图谱）
- 原创感悟但用户指定 Obsidian

**写入方式：** 使用 [[obsidian]] skill 直接创建 `.md` 笔记。**跳过 Generator/Evaluator 流水线**（该流水线为 Feishu docx block 格式设计，Obsidian 不需要）。

**Obsidian 笔记格式规范（遵循 [[obsidian]] skill 的 4-section 结构）：**
```markdown
# 主题N：标题

## Compiled Truth
核心洞察一段话...

> **核心公式/引用**：...

## 关键要点
- **要点一**：...
- **要点二**：...

## 关联主题
- [[主题X-xxx]] — 关联说明
- [[主题Y-yyy]] — 关联说明

## Timeline
| 日期 | 事件 |
|------|------|
| YYYY-MM-DD | ... |
```

**注意事项：**
- 主题编号：查看 `concepts/` 目录下已有最大编号，+1
- 文件名：`主题N-标题.md`（标题用中文短名，不含特殊字符）
- 关联主题：必须检查已有 notes，用 `search_files` 列出已有主题避免断链
- 写入后：`read_file` 验证内容完整
- 知识图谱内容会被 [[ebbinghaus-review]] cron job 自动纳入复习

---

## 标签体系

| 关键词 | 自动标签 |
|--------|---------|
| Agent、大模型、AI工具 | #AI #Agent |
| 客户、销售、谈判、BD | #销售 #客户成功 |
| 团队、管理、组织、领导力 | #管理 #组织 |
| 思维、认知、学习、成长 | #认知 #成长 |
| 产品、战略、市场、商业 | #商业 #产品 |
| 效率、工具、流程、自动化 | #效率 #工具 |

最多 5 个标签。

---

## ⚠️ 已知陷阱

### Generator 局限
Generator 是规则脚本。以下场景 LLM 需预提取优质输入：
- 用 `--title` 和 `--source` 传清洁元数据，避免脚本用截断文本
- LLM 先提炼 compiled_truth，放在输入开头
- LLM 预精选最重要的 5 条 key_points
- 输入用 `- ` bullet 列表，不用节标题

### Evaluator 盲区
Evaluator 只做规则检查，**不做语义质量判断**。100 分 ≠ 内容优质。LLM 必须在 Generator 之前完成内容提炼。

### 写入飞书文档的路径（优先级递减）

**不要因为 MCP 挂了就说「写不了」——先尝试 feishu-cli。**（2026.6.4 用户纠正）

| 优先级 | 方式 | 适用场景 | 前置条件 |
|--------|------|---------|---------|
| 1 | `feishu-cli docx document convert` + block 批量写入 | 知识图谱/成长图谱 docx 创建或全量替换 | 仅需 `docs:doc` scope（tenant token 即可） |
| 2 | `feishu-cli docx builtin import` | 导入 Markdown 为新文档 | `drive:drive` scope + 版本已发布 |
| 3 | MCP feishu API | 批量写入、block 操作 | 系统 tenant token 可用 |
| 4 | 保存到 `references/{date}_{slug}.md` | 以上全部不可用时的回退 | 无 |

**feishu-cli tenant token 操作要点（2026.6.5 验证）：**
- `--use-uat false` 使用 tenant access token，**不需要 OAuth 授权**
- Tenant token 获取：`curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" -H "Content-Type: application/json" -d '{"app_id":"...","app_secret":"..."}'`
- `docs:doc` scope 已开通 → 可创建/读取/写入 docx blocks（已验证 `code=0`）
- `drive:drive` scope 开通后需「创建版本 → 发布」才生效（只保存不够）
- Block 写入：POST `/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children`，每批 50 blocks
- 文档根 block_id 与 document_id 相同
- `feishu-cli docx document convert --content-type markdown --use-uat false` 转换 Markdown 为 blocks
- `feishu-cli docx document create --use-uat false` 创建空白 docx

**feishu-cli builtin import 需要 UAT + drive:drive**：`docx builtin import --markdown` 走 `drive.media.uploadAll` + `drive.importTask.create` 链路，需 `drive:drive` scope。没有时用 block 写入方案（路径1）。

### MCP Feishu 不可用
当以上路径都不可用时：保存到 `references/{date}_{slug}.md`，路径恢复后批量写入。注意：不要直接放弃——至少尝试 feishu-cli 路径。

### 知识图谱格式损坏与修复

当用户反馈 AI知识图谱 / 成长图谱 docx 格式异常（内容重复、Timeline错乱、标题缺失、末尾碎片）时，参考 [references/knowledge-graph-repair.md](references/knowledge-graph-repair.md) 的完整诊断→修复→导入流程。

### ❌ 不要用 shell `terminal()` 传多行 input 给 generator
使用 `terminal()` + `repr()` 传递 `--input` 时，换行符被转义为 `\\n`，generator 收到的是单行文本，导致 `key_points` 和 `action_items` 全部解析失败。
**正确做法：** 在 `execute_code` 中 `import generator` 直接调用 `generate_capture_output()`，输入保持原始多行文本（参考本 session 的实践）。Evaluator 同理：`import evaluator` → `KnowledgeCaptureEvaluator().evaluate(data)`。

### 标签去重
手动标签（`--tags "AI,组织"`）与自动标签（`#AI`）合并后会出现 `#AI #管理 AI 组织` 的重复。写入前用正则清理：只保留 `#` 前缀标签，按去 `#` 后的 base 去重。

### Obsidian 写入不要走 Generator/Evaluator 流水线

Generator + Evaluator 是为 Feishu docx block 格式设计的 JSON 流水线。用户说「写入Obsidian」时，直接用 [[obsidian]] skill 创建 `.md` 笔记——跳过 scripts。Obsidian 的结构（Compiled Truth + 关键要点 + 关联主题 + Timeline）与 Feishu 成长图谱格式不同，应遵循 [[obsidian]] skill 的 4-section 规范。

### Key points 混入 action items
Generator 把所有 `- ` bullet 行都当作 `key_points`，包括 `可行动项` 节标题下的 action bullet。这是 generator 的解析局限——key_points 第 5 条常是 action item 的重复。LLM 在评估 formatted_output 时需自行判断是否要手动修正。

---

## 版本历史

- **v1.0.6** (2026-06-24): 知识图谱目标从「待创建 Docx」修正为 Obsidian vault（`~/Documents/Obsidian Vault/concepts/`），新增 Obsidian 直写路径（跳过 Generator/Evaluator），补充触发词「写进Obsidian」和 Obsidian 4-section 格式规范
- **v1.0.5** (2026-06-05): 重写「写入飞书文档的路径」— tenant token (`--use-uat false`) 可直接用于 docx block 操作，不需 OAuth；block 批量写入（50/批）替代 builtin import 作为首选方案；补充 permission scope 诊断（docs:doc vs drive:drive）和发布生效机制
- **v1.0.4** (2026-06-04): 重写「写入飞书文档的路径」——加入 feishu-cli 作为优先路径，用户纠正「不要因为 MCP 挂了就说写不了」；补充 feishu-cli doc 操作要点和 OAuth 快速流程
- **v1.0.3** (2026-06-04): 新增三个陷阱——shell 传参破坏换行、标签去重、key_points 混入 action items
- **v1.0.2** (2026-05-31): 强化触发条件——文章链接不是触发信号，只在用户明确要求持久化时激活
- **v1.0.1** (2026-05-31): 修复 generator action_items 解析；强化 evaluator 检测空 action_items 和占位符；新增 pitfalls
- **v1.0.0** (2026-05-31): 初始 Hermes 版本
