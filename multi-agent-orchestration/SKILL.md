---
name: multi-agent-orchestration
description: Hermes 作为主 Orchestrator，按任务类型分拆并 delegate 给 Codex/Claude Code 等外部 Agent 并行执行，最后合并结果。
category: autonomous-ai-agents
---

# 多 Agent 编排：Hermes Orchestrator 模式

## ⚡ 核心原则：确定性路由优先（MS Conductor 思路）

**已知的工作流模式 → 走确定性 YAML 路由；未知的任务 → 才用 LLM 动态决策。**

受 Microsoft Conductor（2026.5 开源）启发：对于已知结构的任务，确定性路由 = 零 token 消耗、更快、更可预测。

路由规则定义在 `references/routing.yaml`，编排时必须**先查表**，无匹配再走 LLM。

## 核心模式

```
用户 → Hermes（主脑，在飞书）
         ├── 第一步：查 routing.yaml 确定性匹配
         │    └── 命中 → 直接按预定义链执行（零决策 token）
         └── 未命中 → LLM 动态路由
              /    |    \
           Codex  Claude  Search Agent ...
              \    |    /
           Hermes 收结果 → 合并 → 发回用户
```

## 何时用

- 用户说「帮我查 X 市场，顺便让 Codex 搭个看板」
- 用户说「写个小红书文案，同时让 Codex 出配图」
- 任何需要「不同能力组合」的复合任务

## 执行流程

### 0. 确定性路由检查（必须第一步！）

**加载 `references/routing.yaml`，逐一匹配 trigger_keywords。命中最多的优先。**

匹配成功后 → 直接按预定义的 stages 链执行，跳过 LLM 路由决策：
- `research_pipeline` → three-stage-pipeline: Search(flash) → Analyst(pro) → QA(pro)
- `code_task` → 直接 delegate 给 claude-code 或 codex CLI
- `feishu_card` → Hermes 自己按模板生成
- `knowledge_capture` → knowledge-capture 技能
- `group_bot_routing` → @mention 对应 bot

**仅在 routing.yaml 无匹配时**，才进入 Phase 1 LLM 动态路由。

### 1. 分拆任务（Hermes 自己做，仅当无确定性匹配时）

识别子任务的能力类型：
- **代码/开发** → Codex CLI 或 Claude Code CLI
- **调研/搜索** → delegate_task 给 Search Agent，或自己做
- **数据/分析** → delegate_task 给 Analyst Agent

### 2. Codex/Claude Code 的启动方式

```bash
# 先建 git repo（Codex 需要）
mkdir -p /tmp/project && cd /tmp/project && git init && git commit --allow-empty -m "init"

# Codex 后台跑
codex exec --full-auto "task description" &
# 或用 terminal(background=true, pty=true, notify_on_complete=true)

# Claude Code 打印模式（推荐，不交互）
claude -p "task" --max-turns 10

# Claude Code tmux 模式（需要多轮交互时）
tmux new-session -d -s work && tmux send-keys -t work 'claude' Enter
```

### 3. 并行执行

所有子任务同时启动，不等：

```
terminal(background=true): codex exec "搭看板"
delegate_task: 调研市场数据
```

### 4. 合并结果

等所有子任务结束后，Hermes 做数据对齐和整合：
- 调研数据灌入 Codex 的看板
- 调研结果 + 配图打包

## 飞书群内 Bot Agent（新）

除了 Codex/Claude 等子进程 Agent，飞书群里还有**常驻 Bot Agent**：

```yaml
Agent协作群 (oc_219a613c13292855c2dc4b80e59dfd6e):
  - Hermes（主 Orchestrator）
  - 马斯克（Aily 智能伙伴）
  - Aime 个人助理
  - N8N 机器人
```

### 路由规则

**⚠️ 新规则：先查 `references/routing.yaml`，无匹配再走此表。**

用户告诉 Hermes 一件事 → Hermes 先查 YAML 路由表 → 命中则直接执行预定义链 → 未命中才按此表 LLM 分析：

| 任务类型 | 路由 |
|---------|------|
| 代码/开发 | delegate_task → Codex/Claude（子进程） |
| 深度调研 | three-stage-pipeline（子 Agent） |
| 群内 bot 擅长的任务 | @mention 对应 bot，收集回复 |
| 通用/未分配 | Hermes 自己处理 |

### 与群内 Bot 协作

1. 需要 @mention bot 才能触发（post 格式 at 标签，需要 open_id）
2. **⚠️ Bot 必须配置角色 system_prompt**：无角色限定的 bot 会把全部任务都做了（见 `feishu-group-chat` 技能「Bot 角色身份：System Prompt 注入」）
3. 收到回复后 Hermes 负责判断质量、整理合并
4. 群内 bot 能力注册在 `feishu-group-chat` 技能的 `references/agents.yaml`

## 已验证的组合

| 组合 | 效果 |
|------|------|
| Hermes 调研 + Codex 搭看板 | ✅ 并行 ~6min，看板 + 数据完整 |
| Hermes 写文案 + Codex 出图 | ✅ 文案完成，图需 API key |
| Hermes 分析任务 + delegate_task 调研 | ✅ 工作流稳定 |
| Hermes 编排 → 群内 bot @mention | 🔧 刚建立，待验证 |

## CEO Agent 4-Step SOP（核心工作流）

用户将 Hermes 定位为「CEO Agent」——不是被动等指令，而是主动接管完整的 agent 协作链路：

```
Step 1: 接收任务 → 分析类型，匹配路由表
Step 2: 派发 → 群里 @ 对应 agent，附清晰指令
Step 3: 收结果 → agent 回复后，做质量判断、去噪、补漏
Step 4: 整理交付 → 按用户偏好（卡片优先、去 AI 味、有数据支撑）重新组织
```

**关键纪律**：
- 不把原始 agent 回复直接转发给用户——必须经过 Step 3 质量判断
- 如果 agent 回复质量不够或信息不全，先追问补全再交付
- 交付格式遵循用户偏好（见 memory: 飞书卡片规则，去 AI 味）

## Agent 工厂：按需创建虚拟 Agent

飞书开放平台没有公开 REST API 来程序化创建新 bot/app。替代方案——在 Hermes 基础设施上创建「虚拟 Agent」：

1. **定义 Agent 配置**：Role、Soul、Skills（写入 agents.yaml）
2. **分配群内身份**：以现有 Hermes app 为载体，通过不同 display_name 和回复风格模拟独立 agent
3. **路由触发**：用户 @ 该 agent 时，heartbeat 或网关捕获，Hermes 以该 agent 的身份回复
4. **协作**：虚拟 agent 可与群内其他真实 agent（Aime、马斯克）平等协作

详见 `feishu-group-chat` 技能 → `references/agent-factory.md`

## 注意事项

1. Codex 需要 git repo，用 `mktemp -d && git init` 创建
2. Codex 默认沙箱模式无网络，图生需 `--yolo` + API key
3. Claude Code 优先用 `-p` 打印模式（无交互，不需要 tmux）
4. 并行任务各自独立工作目录，避免冲突
5. 合并阶段 Hermes 负责数据校验和对齐
6. CEO Agent 模式下，Hermes 不是「等指令的工具」，而是「主动判断+分派+质量把关的中间层」
