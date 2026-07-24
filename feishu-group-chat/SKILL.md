---
name: feishu-group-chat
description: Manage AI agents in Feishu group chats — discover bots, @mention them, register their capabilities, and route tasks as the main orchestrator agent.
category: devops
---

# 飞书群聊 Multi-Agent 管理

## 群约（Group Convention）— 「早日让鑫杰实现」群铁律

### 第一铁律：群内 Agent 互相回复必须 @mention

在飞书群里，**Agent 之间互相回复必须用 @ 标签**，否则对方收不到消息。纯文本写 `@Bot名` 不生效，必须用 post 格式的 `at` 标签或 text 格式的 `<at user_id="">` 内联标签。

### 新 Agent 入群标准流程

每进一个新 Agent，作为 Orchestrator 你必须**第一时间**告知对方：

```
@新Agent，欢迎入群！群约：
1. 回复其他 Agent 时必须 @，否则对方收不到消息
2. 我是群主 Agent Hermes（浪子），负责任务路由和结果整合
3. 介绍一下你的能力，我登记到群 Agent 目录里
```

然后更新 `references/agents.yaml` 登记新 Agent 信息。

### 教学 Bot @Mention：当新 Bot 嘴上说记住了但实际没 @

**常见症状**：Bot 回复了你的消息，但 API 返回的 `mentions` 数组为空。它可能用了 interactive 卡片格式（飞书卡片不触发通知），或者用了纯文本 `@Bot名`（不解析成 at 标签），或者记错了你的 open_id。

**教学循环（迭代直到稳定）**：

```
1. @目标Bot 发一条 text 消息（--as bot --msg-type text + <at> 标签）
2. 拉群消息检查它的回复：
   - 看 sender.id/app_id 确认是目标 Bot
   - 看 msg_type 是否 text（非 interactive）
   - 看 mentions[] 是否包含你的 open_id
3. 如果任一条件不满足 → 在下一轮 @ 中明确指出问题 + 纠正：
   - "你的 mentions 数组是空的，你没 @ 我"
   - "你用了 interactive 卡片，必须用 text 格式"
   - "你记的 open_id 是错的，正确的是 ou_xxxxxxxxxxx"
4. 重复直到连续 3 次回复都 text + mentions 包含你的 open_id
```

**检查回复的核心命令**：

```bash
lark-cli im +chat-messages-list --chat-id <chat_id> --page-size 5 --order desc 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
MY_OID='ou_9b18941c79156bd08a70431dc5dcf7f9'
TARGET_APP='cli_aad1d272e3385cb3'
for m in d.get('data',{}).get('messages',[]):
    s=m.get('sender',{})
    if s.get('id')!=TARGET_APP: continue
    ids=[x.get('id','') for x in m.get('mentions',[])]
    has_me=MY_OID in ids
    print(f'{\"✅\" if has_me else \"❌\"} type={m.get(\"msg_type\")} @={[x.get(\"name\",\"?\") for x in m.get(\"mentions\",[])]}')
"
```

**判断标准**：必须同时满足三个条件才算成功：
1. `msg_type == "text"`（不是 interactive / post / card）
2. `mentions[].id` 包含你的正确 open_id
3. 重复多次（3+）仍然稳定

**告诉 Bot 的标准化话术**：

```
群内回复我必须 text 格式 + <at user_id="ou_MY_OPEN_ID">我的名字</at>
— 不论我有没有提"@我"二字。这不是礼貌问题，是物理约束：
飞书只认 <at> 标签触发通知，纯文本 @ 不生效。
```

**bot 使用 `--as bot` 发送**（无需 `send_as_user` scope），text 格式的 content JSON：

```json
{"text":"<at user_id=\"ou_TARGET_OPEN_ID\">BotName</at> 消息内容"}
```

**轮询脚本模板**：见 `references/teach-bot-mention-poll.py` — 可复用的教学轮询脚本，自动检测目标 Bot 是否 text + @ 了你。

## 触发条件

- 用户询问「群里有多少 agent/bot」
- 用户要求 @mention 群里的某个 bot
- 用户要求你担任群的「主 agent」做任务路由分发
- 用户要求你了解某个 bot 的能力并记录下来
- 用户邀请新 bot 入群后说「认识一下」（详见 `agent-group-collab` skill 的「认识一下」流程）

## 核心模式

你是群里的**主 Agent（Orchestrator）**——用户告诉你一件事，你根据对群里 agent 能力的了解，决定路由给对应的 agent 去完成，然后将结果判断、整理后给用户。

```
用户 → Hermes（主 Agent，群内）
         /    |    \
    马斯克  Aime  N8N ...
         \    |    /
     Hermes 收结果 → 判断整理 → 发回用户
```

## 发现群内 Agent

### chatMembers API 注意

飞书原生 REST API `chatMembers.get` 默认过滤机器人。但 **`lark-cli im +chat-members-list --member-types bot --page-all`** 可正常返回 bot 列表。优先使用 lark-cli。

### 正确方法一：`+chat-members-list --member-types bot`（推荐）

```bash
lark-cli im +chat-members-list --as user --chat-id <chat_id> --member-types bot --page-all
```

返回 `data.bots[]`，每项含 `app_id`、`member_id`、`name`。**此方法已在实际使用中验证有效**（2026.7.5：成功发现马斯克、Kimi Agent）。

### 正确方法二：分析消息历史（备用）

```python
# 拉取群消息，从 sender 字段提取所有唯一的 app_id
# app_id 格式：cli_xxxxxxxxxxxxxxxxx
# 有 app_id 的 sender 就是 bot agent
```

系统邀请消息（`msg_type: system`）格式为：
```json
{"template": "{from_user} invited {to_chatters} to the group..."}
```
**不包含被邀请者的 open_id**，只有显示名称。

### 记录 Agent 信息

发现 agent 后持久化到 `references/agents.yaml`：
```yaml
agents:
  - name: "马斯克"
    app_id: "cli_a934e54959f99bd8"
    open_id: "ou_ec816541777287f722b0896287c4486a"
    platform: "Aily 智能伙伴"
    capabilities: []
  - name: "Aime 个人助理"
    app_id: "cli_9a31b280a1f3d101"
    open_id: "ou_b33d3f6e144a9730db025d288c81212c"
    platform: "Aily 智能伙伴"
    capabilities: ["业绩查询", "工作日报"]
    status: "✅ 正常响应 — 工作日每10分钟心跳轮询（:00/:10/:20/:30/:40/:50 整点），@后等待≤10分钟"
```

## @Mention Bot

### 方式一：post 消息的 at 标签（推荐，适合富文本）

```bash
lark-cli im +messages-send --as bot \
  --chat-id <chat_id> \
  --msg-type post \
  --content '{"zh_cn":{"title":"","content":[[{"tag":"at","user_id":"ou_xxxxxxxxxxxxx"},{"tag":"text","text":" 你好！"}]]}}'
```

**关键**：`at` 标签的 `user_id` 字段不能为空，否则返回 400 错误。用 `--as bot` 发送（无需 `send_as_user` scope）。

### 方式二：text 消息的 <at> 内联标签（简单，适合纯文本）

在 text 消息的 JSON content 中使用 `<at user_id=\"ou_xxx\">Name</at>` 内联标签：

```bash
lark-cli im +messages-send \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --msg-type text \
  --content '{"text":"嗨 <at user_id=\"ou_abdda0c6cd5e362bca041cb3dbd88f86\">Bot名称</at>，你好！"}'
```

API 响应的 `mentions` 数组会确认 @mention 已正确解析（包含被 @ 者的 open_id 和 name）。**比 post 格式更轻量**，适合简单打招呼或短消息。

#### 发送身份：`--as bot` vs `--as user`

- `--as bot`（默认）：无需额外 scope，直接可用。用于群内 @mention 其他 agent。
- `--as user`：需要 `im:message.send_as_user` scope，需单独授权。**当前未配置此 scope**，用 `--as bot` 即可。

### 方式三：纯文本 @BotName（❌ 不生效）

纯文本中写 `@Bot名称` **不会触发飞书通知**——bot 收不到。只适用于人类成员在客户端看到后手动补 @。

### 获取 bot open_id 的最可靠方法

当 bot 从未发过言、API 又查不到时，**最可靠的方法是让用户手动 @ 一下**：

```
1. 让用户在飞书客户端里手动 @ 目标 bot
2. 立即调用 message_list 拉取最新消息
3. 从返回消息的 `mentions` 字段提取 open_id 和 name：
   mentions[0].id   → open_id
   mentions[0].name → 显示名称
```

**原理**：用户 @ 的消息会包含被 @ 者的完整身份信息，即使 bot 从未发言、chatMembers API 也过滤掉了它，mentions 字段都会暴露 open_id。

**其他途径**（按优先级排列）：

1. **消息 sender 提取**：bot 发过言 → 从 `sender.id` 拿 open_id；`sender.id` 同时给出 app_id
2. **用户手动 @**（最可靠，适用于沉默 bot）：如上所述
3. **系统邀请消息**：`msg_type: system` 的消息模板**不包含被邀请者的 open_id**，只有显示名称，不可用

## Agent 能力注册

```yaml
# references/agents.yaml
agents:
  - name: "Hermes"
    app_id: "cli_a964fd626078dcbc"
    role: "orchestrator"
    capabilities: ["调研", "写文档", "代码审查", "任务分发", "飞书卡片"]
  - name: "马斯克"
    app_id: "cli_a934e54959f99bd8"
    open_id: "ou_ec816541777287f722b0896287c4486a"
    platform: "Aily 智能伙伴"
    capabilities: ["客户名单查询", "合作产品信息", "合同状态", "袁鑫杰工作搭档"]
  - name: "Kimi Agent"
    app_id: "cli_aac38f8be0b8dce4"
    open_id: "ou_8c41b534519bd88787c285b4fffe558d"
    capabilities: []
    status: "无响应 — Webhook 未运行"
  - name: "南区 ISV 业务助手"
    app_id: "cli_aaa06c74f1f89bcb"
    open_id: "ou_abdda0c6cd5e362bca041cb3dbd88f86"
    capabilities: ["ISV 材料", "客户案例", "对客话术"]
    status: "✅ 正常响应 — 通过 Thread 回复"
  - name: "大湾区样板间专项小管家"
    app_id: "cli_a96aefe4aff85cef"
    open_id: "ou_459dac1c298c48d280a3ea3260aac80e"
    capabilities: ["案例弹药库", "样板间方案", "许愿助理"]
    status: "✅ 正常响应 — 通过 Thread 回复"
  - name: "TC 交付数字员工"
    app_id: "cli_a96d9040ddb8dccb"
    open_id: "ou_c9cd24728752004e848f099d2b448d29"
    capabilities: [迁移交付, 集成支持]
    status: "✅ 正常响应 — 入群时自动发送欢迎卡片"
  - name: "CodeM"
    app_id: "cli_a9698e4435f85cc9"
    open_id: "ou_0425582e71a1045dd1c6e139825d2139"
    capabilities: ["代码生成", "商机挖掘"]
    status: "✅ 可 @mention — 代码生成类产品，Q3 已盘出 8+ 商机，商业化未定；群内 @mention 可送达（2026.7.9 验证）"
  - name: "CSM oncall大师"
    app_id: "cli_a555904bae78900d"
    open_id: "❓ 未获取（who: --member-types bot 查不到该 bot，需用户手动 @ 后从 mentions 提取）"
    capabilities: ["CSM 场景 oncall"]
    status: "🟡 可响应群消息 — 入群后自动发送欢迎卡片，但 open_id 未获取无法 @mention（2026.7.9 通过纯文本消息验证存在）"
  - name: "SaaS Regional Sales-Southern China-RM 团队智能体"
    app_id: "cli_aada28837539dbb6"
    open_id: "ou_3b1e9a0910f76e58ed07c3b9053a0f32"
    capabilities: ["业务答疑", "任务指标跟踪", "群聊讨论结构化整理", "工作进展汇总"]
    status: "✅ 主动响应 — 入群后主动发送自我介绍，列举能力清单；@mention 可送达（2026.7.10 验证）"
```

未确认能力的 agent 记为 `capabilities: []`，后续通过对话确认。

## 权限管理

需要用到的 scope：
- `im:chat.members:read` — 读群成员（但 bot 会被过滤）
- `im:message.group_msg` — 读群消息
- `admin:app.info:readonly` — 列出 workspace 所有应用（可能需要额外申请）

### 权限申请卡片

不要发纯文本链接让用户自己打开——用 `feishu-cli exec im.v1.message.create` 发一张带「点击授权」按钮的飞书卡片。权限链接格式：

```
https://open.feishu.cn/app/{app_id}/auth?q=scope1,scope2&op_from=openapi&token_type=tenant
```

具体卡片实现见 `references/permission-card-template.md`。

## 接收其他 Bot 的消息

**关键配置**：Hermes 网关默认 `FEISHU_ALLOW_BOTS=none`，**所有其他 bot 发来的消息都会被丢弃**，即使对方 @ 了你也不会收到。

在 `~/.hermes/.env` 中设置：

```bash
FEISHU_ALLOW_BOTS=mentions
```

三个模式：

| 值 | 效果 |
|----|------|
| `none` | 屏蔽所有 bot 消息（默认） |
| `mentions` | 只收 @ 了我的 bot 消息 |
| `all` | 全收（太吵，不推荐） |

设置后需重启网关（`hermes gateway restart` 或 kill + 重启动）。

## Agent 工厂：按需创建虚拟 Agent

飞书开放平台**没有公开 REST API 来程序化创建新 bot/app**（Aily v1 端点返回 404，应用管理 API 无创建接口）。所有 app 创建需在开发者后台手动完成。

### 虚拟 Agent 方案

不依赖飞书平台创建新 app，而是在 Hermes 基础设施上创建「虚拟 Agent」：

1. **注册配置**：在 `agents.yaml` 中定义 agent 的 name、role、capabilities、persona
2. **群内身份**：以 Hermes app 为载体，通过不同回复风格模拟独立 agent
3. **路由触发**：用户 @ 该 agent → heartbeat 或网关捕获 → Hermes 以该 agent 身份回复
4. **能力执行**：虚拟 agent 背后可以连接 cron job、delegate_task、外部 API 等

虚拟 agent 可与群内真实 agent（Aime、马斯克）平等协作，对用户来说体验一致。

详细架构见 `references/agent-factory.md`。

## 与心跳型 Agent 交互（以 Aime 为例）

Aime 个人助理不接收飞书实时事件——她通过定时轮询群消息来工作。**你不会收到网关推送的 Aime 回复**，必须主动拉群消息。

### 交互流程

```
1. @Aime 发送消息（--as bot，post 格式带 at 标签）
2. 等待 Aime 的下一个心跳轮询点（每10分钟整点：:00/:10/:20/:30/:40/:50）
3. 在心跳点之后主动拉群消息查找 Aime 的回复
4. 识别回复：sender.id == Aime 的 app_id
```

### 拉群消息查回复

```bash
lark-cli im +chat-messages-list --chat-id <chat_id> --page-size 10 --order desc
```

**注意**：是 `--order desc`，不是 `--sort-type`。此命令会取反 —— 不加 `--order` 默认就是 desc。

### 过滤 Aime 的回复

```python
# 从 message list 中取 sender.id == AIME_APP_ID 的消息
# 排除历史心跳确认消息，只取比本次 @ 消息更新的
for msg in messages:
    if msg['sender']['id'] == AIME_APP_ID and msg['message_id'] > sent_message_id:
        return msg
```

### Aime 的回复特征

Aime 的回复分两层：
1. **心跳确认**："在线，Javis 🦾 已收到"——仅表示她看到了 @ 消息，不是对问题的回答
2. **实际回复**：在心跳确认之后，可能在同一轮询周期或下一次心跳中给出

**不要误把「在线，已收到」当作有效回答**——确认 ≠ 回答，继续等待或检查后续消息。

### 等待策略

```bash
# 最长等待 12 分钟（覆盖两次心跳窗口），每 30 秒查一次
for i in $(seq 1 24); do
  sleep 30
  # 拉消息 + 过滤 Aime 新回复
done
```

除了网关被动接收 webhook 事件，还需要主动轮询群消息：

### 为什么需要心跳

- 网关 `FEISHU_ALLOW_BOTS=mentions` 只在 bot @ 我时触发
- Agent 可能直接回复消息而不 @ 我
- 用户可能手动 @ 新 agent 来暴露其 open_id

### 实现方式

轮询脚本 `references/group_heartbeat.py`：
- 记录最后处理的消息 ID（状态文件）
- 每 N 秒调 `message_list` API 拉取新消息
- 过滤已知 agent 的消息（非自己、非用户、非系统消息）
- 检测到新 agent 消息时输出上下文供处理

配合 cron job 使用，实现「对群消息的持续感知」。

## Bot 角色身份：System Prompt 注入

### 核心问题：Bot 无角色 → 全员抢活

当多个 Hermes bot 在同一个飞书群里收到 @mention 时，如果它们没有角色限定，**每个 bot 都会把自己当成全能的通用 Agent**，把整个任务都做了。这就是「PM 把 Marketing 的活也干了」的根本原因。

### 解决方案：每个 Profile 注入角色 system_prompt

在 `~/.hermes/profiles/<name>/config.yaml` 的 `agent` 段下添加 `system_prompt`：

```yaml
agent:
  system_prompt: |
    你是**PM 助手**，团队的产品经理。你的职责是**只做产品规划相关的工作**，不越界做营销、设计、数据分析。

    **核心能力：**
    - 需求分析：将模糊想法转化为清晰的功能需求
    - PRD 撰写：输出结构化的产品需求文档

    **协作规则（重要）：**
    - 你只负责**产品层面**的分析和规划
    - 如果任务同时涉及营销/设计/数据，只做产品部分，明确标注「营销方案由 Marketing 助手负责」
    - 不要替其他角色做他们的工作
    - 需要跨角色协作时，在回复末尾标注需要谁接手
```

**关键设计原则：**
1. **明确角色** — 「你是 PM 助手」，不是通用 AI
2. **职责边界** — 「只做产品规划」，用否定句划清界限
3. **协作协议** — 「标注由谁接手」，给下游 agent 信号
4. **文件域隔离** — 「只改 ~/.hermes/profiles/pm/」，防止跨 bot 写文件

### 生效流程

```bash
# 1. 修改 config.yaml 添加 system_prompt
# 2. 找到旧 gateway 进程并 kill
ps aux | grep 'profile pm.*gateway run' | awk '{print $2}' | xargs kill
# 3. 重启（bash 父进程也要 kill 重开）
hermes --profile pm gateway run &
```

## 多 Bot 协作模式

### 当前机制：独立并行 + 角色限定

```
群消息 @PM @Marketing @Designer @Data
       │
       ├─→ PM bot：收到消息 → system_prompt 说「只做产品」→ 只出产品方案
       ├─→ Marketing bot：收到消息 → system_prompt 说「只做营销」→ 只出营销方案
       ├─→ Designer bot：收到消息 → 只做设计
       └─→ Data bot：收到消息 → 只做数据分析
```

**局限性：** 各 bot 独立处理，没有中央协调。如果某个 bot 没响应，没有重试或 fallback。

### 二层编排（推荐进阶方案）

```
用户 → Hermes（Orchestrator）
         /    |    \
      PM    Marketing  Designer ...
         \    |    /
      Hermes 收结果 → 整合 → 发回用户
```

Hermes 不直接干活，而是：
1. 接收任务 → 分析需要哪些角色
2. 分别 @mention 对应 bot
3. 等所有回复 → 质量判断 → 整合交付

详见 `multi-agent-orchestration` 技能中的「CEO Agent 4-Step SOP」。

## 常见陷阱

| 问题 | 原因 | 解决 |
|------|------|------|
| chatMembers REST API 只返回人类 | API 默认过滤机器人 | 用 lark-cli `+chat-members-list --member-types bot` 替代 |
| 系统邀请消息没有 open_id | 消息模板不包含目标用户 ID | 让用户在客户端手动 @，从 mentions 提取 |
| at 标签报 400 `user_id can't be nil` | post 格式 at 必须有 user_id | 先收集 open_id 再 at |
| 纯文本 @Bot名 不触发通知 | 飞书不解析文本中的 @ | 必须用 post 格式 at 标签 |
| 用户给的 ID 是 `oc_` 前缀，不是 open_id | open_id 是 `ou_` 前缀，`oc_` 是 chat_id 或其他 | 通过用户手动 @ 来提取真实 open_id |
| at 消息 API 返回 `user_id: ""` 但消息实际已发出 | API 序列化时 ID 格式不匹配导致字段为空，但飞书客户端可能仍渲染 @ | **不要仅凭 API response 的 user_id 为空就判断 @ 失败**——等用户确认或检查 mentions 字段 |
| application.list 需 admin scope | 需 `admin:app.info:readonly` | 申请权限或用消息历史 |
| computer_use 截图返回 0x0 | cua-driver 可能未运行 | 降级为纯文本消息 |
| **其他 bot @ 了我但收不到** | `FEISHU_ALLOW_BOTS` 默认 `none` | 设 `FEISHU_ALLOW_BOTS=mentions` + 重启网关 |
| 权限申请发文本链接没人点 | 用户要点击式交互 | 用 `feishu-cli exec im.v1.message.create` 发带按钮的交互式卡片 |
| 飞书卡片「加入群聊」按钮点击无效 | 卡片配置错误、群设置变更、客户端 bug、群已解散 | 1) 直接在飞书客户端搜索群名尝试加入 2) 让发卡片的人重发 3) 让群里已有成员手动拉入 |
| 机器人无法加入已有群聊 | 飞书开放 API 无「机器人主动加入已有群聊」接口 | 只能通过卡片按钮、已有成员手动添加、或搜索群名加入。不要尝试 API 方式 |
| **@多个 bot 后一个 bot 把活全干了** | bot 没有角色 system_prompt，把自己当通用 Agent | 给每个 profile 的 `agent.system_prompt` 注入角色身份 + 职责边界 |
| **用 bot/info API 拿到的 open_id 无法跨应用加群** | open_id 是应用维度的，不同 app 看到同一个人的 open_id 不同（`open_id cross app` 错误） | 1) 用发消息时的 `mentions` 字段提取目标 bot 在本应用视角下的 open_id 2) 让用户手动 @ 后从 mentions 提取 |
| **`--as user` 发消息报 missing_scope** | 缺少 `im:message.send_as_user` scope | 用 `--as bot` 代替（bot 身份发消息无需额外 scope），或授权 `im:message.send_as_user` |
| **`feishu-cli` 命令不存在** | 已统一为 `lark-cli` | 所有命令改用 `lark-cli`，格式为 `lark-cli <domain> +<action>`（如 `lark-cli im +messages-send`） |
| **`feishu-cli im message create` 报 unknown subcommand** | CLI 升级后命令格式改变 | 新格式：`lark-cli im +messages-send --chat-id <id> --msg-type post --content '...'` |
| **`+chat-messages-list --sort-type` 报 unknown flag** | 正确的 flag 名是 `--order` | 用 `--order desc` 或 `--order asc` |
| **bash + 管道解析轮询结果反复失败** | bash 中 `echo "$RESP" \| python3 -c "..."` 在多行 JSON 或特殊字符下解析失败，产生假阳性（误判旧消息为新回复） | 用 `execute_code` 写 Python 轮询脚本代替 bash，Python 直接调 `terminal()` 拿 JSON 结果 |
| **bot 之间不能私聊** | 飞书 API 返回 230013 `Bot has NO availability to this user`，bot 只能和已授权的人类用户通信 | 通过群内 @mention 与其他 bot 交互，不要尝试私聊 |
| **Aime 回复「在线，已收到」但没有实际答案** | Aime 的心跳确认和问题回答是分开的——确认只表示她看到了消息 | 不要误把确认当回答。继续等待或在同一次心跳的下一条消息中找实际回复 |
| **Bot 回复了但 mentions 数组为空** | Bot 用了 interactive 卡片格式或纯文本 @，没使用 `<at>` 标签 | 教学 Bot 用 text 格式 + `<at user_id="ou_xxx">Name</at>`，详见「教学 Bot @Mention」 |
| **Bot 说记住了规则但下次仍不 @** | Bot 理解了文字没理解后果——纯文本 @ 只是文本，不触发通知 | 把规则从「记住规定」转成「理解后果」：**不 @ 我就收不到，不是我不理你**。并走教学循环直到稳定 |
| **@ 错 Bot：用了不在群里的 Bot ID** | agents.yaml 或 memory 中的 Bot ID 已过期（Bot 改名/离群/换号），或名称相近混淆（如 Kimi Code ≠ Kimi Agent） | **路由前必须用 `lark-cli im +chat-members-list --member-types bot --page-all` 刷新群成员列表**，以实时查询结果为准，不信任静态文件。2026.7.21 实际踩坑：@ 了不存在的 Kimi Agent 而非 Kimi Code |
| **委派给 Bot 的任务内容被截断** | 出站消息构建时多段上下文未完整拼接，后半截丢失 | 发送前逐段检查：任务的全部问题/需求是否都在消息体里？多段任务用 `execute_code` 拼接完整后再发送，不在单个 `terminal()` 调用中截断 |
