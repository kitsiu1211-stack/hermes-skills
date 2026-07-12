# 知识图谱 docx 格式修复工作流

> 适用：AI知识图谱 / 成长图谱 docx 出现结构错误时的诊断与修复流程

## 触发信号

用户说「格式有问题」「看起来不对」「内容乱了」等。

## 常见 corruption 类型

| 类型 | 表现 | 根因 |
|------|------|------|
| 内容重复 | 同一主题的 Compiled Truth 出现两次 | Agent 写入时未检查已有内容，或 merge 逻辑错误 |
| Timeline 污染 | 主题A的 Timeline 表格混入主题B的数据 | block 追加位置偏移，内容串到相邻区域 |
| 标题缺失 | 主题N 的 🎯 标题丢失，直接从 Compiled Truth 开始 | 主题被嵌入到前一个主题的 section 内 |
| 文档末尾碎片 | 残留「(已删除)」标记 + 未归类的孤立段落 | 写入失败回滚不完整 |

## 诊断流程

### Step 1: 读取全文

```bash
feishu-cli docx document rawContent --document-id <doc_token> > /tmp/kg_raw.txt
```

如果 feishu-cli 不可用，用 `mcp_feishu_docx_v1_document_rawContent`。

### Step 2: 定位主题边界

```python
import re
for m in re.finditer(r'🎯 主题(\d+)：', content):
    print(f"主题{m.group(1)} at pos {m.start()}")
```

检查：
- 主题编号是否连续（24个主题应全出现两次：导航索引 + 正文）
- 正文区的主题间距是否合理（<500 chars 的间距 = 可能是被污染或合并）

### Step 3: 逐段排查

1. **检查重复**：搜索特定主题的关键词（如「更新记录（2026.5.8）」），看是否出现两次
2. **检查 Timeline**：对比 Timeline 表格内容是否匹配当前主题
3. **检查标题**：是否每个主题都有 `🎯 主题N：` 前缀
4. **检查末尾**：文档最后 500 字符是否干净

## 修复流程

### 方案A：全文修复（推荐，适合≥3个问题）

1. 提取所有主题段落（以 `🎯 主题` 为边界）
2. 对每个主题内容执行正则修复（去重、清理污染、补标题）
3. 清理文档末尾碎片
4. 重组为干净纯文本
5. 转换为 Markdown（加 `## ` / `### ` / `**` 标记）
6. 通过 `feishu-cli docx builtin import` 导入为新版本

### 方案B：Block 级精确修复（适合1-2个小问题）

1. 用 `feishu-cli docx document-block list` 找到问题 block
2. 用 `feishu-cli docx document-block update` 修正文本
3. 用 `feishu-cli docx document-block-children delete` 删除重复 block

方案B 对 block 结构的理解要求高，且 feishu-cli 的 block 操作 API 较复杂。**通常优先选方案A。**

## Markdown 转换注意事项

从 `rawContent` 纯文本转 Markdown 时：

- `🎯 主题N：xxx` → `## 🎯 主题N：xxx`
- `Compiled Truth（当前最佳理解）` → `### Compiled Truth（当前最佳理解）`
- `关键要点` / `关联主题` / `Timeline（思考演变）` → `### 章节名`
- 日期行 `2026.5.15 | xxx` → `**2026.5.15 | xxx**`
- 表格数据保持纯文本（feishu import 会自动识别）
- `核心公式：` / `核心洞察：` 开头行 → `**核心公式：xxx**`

## 导入飞书

### 方式A：Block 批量写入（推荐，不需要 UAT）

当 `drive:drive` 权限未开通时，`builtin import` 会报 `99991672` 错误。但可以绕过导入 API，直接用 block 写入——只需要 `docs:doc` scope（tenant token 即可）。

**步骤：**

```python
import subprocess, json

# 1. 获取 tenant access token（无需 OAuth）
TAT_CMD = 'curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" ...'
tat = subprocess.run(TAT_CMD, shell=True, ...)

# 2. 创建空白文档
curl -X POST "https://open.feishu.cn/open-apis/docx/v1/documents" \
  -H "Authorization: Bearer $TAT" \
  -d '{"title":"文档标题"}'
# → 返回 document_id

# 3. 转换 Markdown 为 Blocks
feishu-cli docx document convert \
  --content-type markdown \
  --content "$(cat /tmp/kg_fixed.md)" \
  --use-uat false
# → 返回 blocks 数组

# 4. 批量写入（每次最多 50 blocks）
for batch in chunks(blocks, 50):
    curl -X POST "https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children" \
      -H "Authorization: Bearer $TAT" \
      -d '{"children": batch, "index": offset}'
```

**注意事项**：
- 文档根 block_id 等于 document_id
- Blocks 写入使用 `children` 端点，不是 `batch_create`
- 每批次 50 blocks 稳妥，避免超时
- `convert` 返回的 blocks 可直接作为 `children` 的 body

### 方式B：builtin import（需要 UAT + drive:drive 权限）

```bash
feishu-cli docx builtin import \
  --markdown "$(cat /tmp/kg_fixed.md)" \
  --file-name "AI思考知识图谱-修复版" \
  --use-uat false
```

**前置条件**：app 需开通 `drive:drive` scope。启用后必须「创建版本 → 发布」才生效（仅保存不够）。

如果 `--use-uat false` 报权限错误但 `--use-uat true` 说 UAT 未配置：
- `docs:doc` scope 已开通 → 可读可写 docx blocks → 用方式A
- `drive:drive` scope 未开通 → 无法 import → 用方式A

## 案例：2026.6.5 修复记录

**源文档**：`OGBVdDVjJohAGkxItSXcODxunjh`（AI知识图谱 docx）

**发现的7个问题**：
1. 主题8（PaperClip Skill设计）Compiled Truth 重复
2. 主题10（AI暴露度）Timeline 混入主题8数据
3. 主题9（AI Native）Timeline 混入 PaperClip 要点
4. 主题17（中美AI谈判）缺失 🎯 标题（嵌入在主题18内）
5. 主题12（AI转型与组织）重复 Timeline 标题
6. 主题22/23 合并成一行
7. 文档末尾残留「(已删除)」碎片 + AI Split 孤立段落

**修复**：全文 Python 处理 → 7个正则修复 → Markdown 转换 → 25K chars 干净版本输出到 `/tmp/knowledge_graph_fixed.md`
