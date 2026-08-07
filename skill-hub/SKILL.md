---
name: skill-hub
description: Maintain the Hermes Skills Hub — a static HTML showcase deployed on Miaoda (妙搭). Add/update skill cards, manage rendering logic, fix counts, and publish. ALSO acts as the Skill Guard — always run validation before any skill_manage operation.
category: feishu
---

# Skill Hub 维护 + Skill Guard（校验层）

## ⛔ Skill Guard 铁律（最高优先级）

**每次 skill_manage 操作前，必须跑校验层：**

```bash
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_validator.py preflight <action> <skill_name>
```

| 操作 | 校验内容 |
|------|---------|
| `create` | 名字不重复、格式合法 |
| `patch/edit` | Skill 存在 |
| `delete` | Skill 存在、无其他 Skill 引用断裂 |

**校验不通过 → 拒绝操作，告诉用户原因。**

操作完成后可追加全量校验：
```bash
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_validator.py check <skill_name>
```

操作完成后同步依赖图：
```bash
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_graph.py build
```

## 常用查询

```bash
# 这个 Skill 依赖谁 / 被谁依赖
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_graph.py deps <name>

# 删除影响分析
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_graph.py impact <name>

# 基于标签推荐关联
python3.11 ~/.hermes/skills/skill-hub/scripts/skill_graph.py suggest <name>
```

## 参考

- `references/dataflow-harness-architecture.md` — 北大 DataFlow-Harness 论文：校验层+增量突变+依赖图的设计来源，93.3% 通过率
- `scripts/skill_validator.py` — 校验脚本（pre-flight check）
- `scripts/skill_mutate.py` — 类型化增量突变脚本（改单个字段，不碰全文）
- `scripts/skill_graph.py` — 依赖图（205 Skills, 67 出度, 63 入度）

## 触发条件

- 任何 `skill_manage` 操作前自动触发 Skill Guard
- 用户说「更新 Skill Hub」「把 XX 加到 Skill Hub 上」

## 核心资产

| 项目 | 值 |
|------|-----|
| **app_id** | `app_179xr3ds4q0` |
| **HTML 源文件** | `/tmp/skillhub/index.html` |
| **发布 URL** | `https://bytedance.feishuapp.com/app/app_179xr3ds4q0` |
| **类型** | `html` 静态应用 |

## 添加新 Skill 卡片

1. 读取 `/tmp/skillhub/index.html`
2. 在对应 category 的 `skills` 数组末尾添加一条完整的 skill 对象：
   ```js
   { cn:"中文名", code:"skill-name", icon:"lucide-icon", desc:"一句话描述", exUser:"用户说", exAgent:"Agent 回" }
   ```
3. **完整字段表**（JSX 对象，所有值用单引号）：

   | 字段 | 必填 | 说明 | 渲染位置 |
   |------|------|------|---------|
   | `cn` | ✅ | 技能中文名称 | `name-cn` span |
   | `code` | ✅ | kebab-case 英文代码名 | `name-code` span（灰色衬线） |
   | `icon` | ✅ | [Lucide 图标名](https://lucide.dev/icons) | 卡片左侧 48px 图标 |
   | `desc` | ✅ | 一句话描述 | 卡片正文 |
   | `exUser` | ✅ | 示例对话中「用户说」 | 展开面板上半蓝色气泡 |
   | `exAgent` | ✅ | 示例对话中「Agent 回」 | 展开面板下半白色气泡 |
   | `github` | ❌ | `"owner/repo"` | 自动渲染 GitHub 跳转按钮 |
   | `quality` | ❌ | `false` 可隐藏 Gen→Eval 徽章 | 默认显示；设为 `false` 不渲染 |

   - **`quality` 字段什么时候用**：纯词典/查表类 skill（如 `ljg-rank`、`animation-vocabulary`）没有 Generator→Evaluator 架构，设为 `false` 以避免误导。其他 skill 默认保留徽章。
   - **`github` 字段效果**：在 `card-actions` 区渲染一个 GitHub Octicon 按钮，链接到 `https://github.com/owner/repo`。

4. 更新三处计数：
   - `.hero-badge` 文本：`"N 个精选 Skill"` 中的 N
   - `.hero-sub` 段落文本中出现的数字（如 `"70 枚 Skill 覆盖分析..."`）
   - `.cat-nav` 中对应分类的 `.pill-count` 文本（如 `<span class="pill-count">20</span>`）

5. **批量添加（10+ skill）**：不要逐条追加——直接替换整个 `skills: [` 数组。先分类（cognitive/dev/tools），同类 skill 按逻辑顺序排列，旧的保留顺序，新的追加在后面。更新完 arrays 后统一更新所有计数。

   **批量工作流**：读取所有目标 SKILL.md → 对每个提取 name/description/分类 → 每个 skill 写一条 JS 对象 → 确认 icon 可用（`grep -il 'lucide-'` 可验证）→ 一次性替换 categories 数组 → 更新计数 → 验证页面。

## 发布

```bash
cd /tmp/skillhub && lark-cli apps +html-publish --app-id app_179xr3ds4q0 --path ./index.html --as user
```

**⚠️ 常见坑**：`--path` 必须是相对于当前工作目录的路径，不接受绝对路径。报 `unsafe --path` 时先 `cd` 到文件所在目录，再用 `--path ./index.html`。

成功返回 `data.url` 就是新的发布链接。

## 渲染细节（JS 模板）

### 分类结构

```js
const categories = [
  {
    id: "cognitive", icon: "brain", label: "思考方式",
    title: "让 Agent 像你一样思考",
    desc: "分类描述文字",
    skills: [ /* skill objects */ ]
  },
  // ... dev, tools
];
```

每个分类有自身的 id、lucide 图标、label、section title、description 和 skills 数组。

### scroll-triggered fade-in

所有 skill card 在页面加载后有渐入动画：`opacity 0 → 1` + `translateY(24px → 0)`，每个 card 按索引叠加 0.04s delay。用 `IntersectionObserver` 触发。这部分在 `renderAll()` 下方的 `setTimeout` 块中，不要改动。

### 展开面板

每个 card 的「查看示例」按钮通过 `toggleExample(i)` 切换 `example-panel.open` class，控制 `max-height: 0 ↔ 500px` 的手风琴动画。每个 skill 的示例对话显示为 user（白色）和 agent（蓝色）两个气泡。

## 已有分类结构

| 分类 | id | 图标 |
|------|-----|------|
| 思考方式 | `cognitive` | `brain` |
| 开发方法 | `dev` | `code-2` |
| 工具效率 | `tools` | `wand-2` |
