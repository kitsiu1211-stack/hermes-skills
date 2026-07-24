# Agent 工厂：虚拟 Agent 架构

## 背景

飞书开放平台没有公开 REST API 来程序化创建新 bot/应用。所有 app 创建需在开发者后台手动完成。但 Hermes 需要「Agent 工厂」能力——根据任务目标动态创建专业化 agent 并拉入协作群。

## 方案：虚拟 Agent

不依赖飞书平台创建新 app，在 Hermes 基础设施上模拟独立 agent。

### 架构

```
用户 @ 虚拟Agent → 群消息 → heartbeat 捕获
                              ↓
                    Hermes 识别 @ 目标
                              ↓
               加载该 Agent 的配置 (agents.yaml)
                              ↓
           ┌──────────────────┼──────────────────┐
           │ Role 定义        │ Soul/Persona     │ Skills 能力集    │
           │ (干什么的)       │ (说话风格)       │ (能调哪些工具)   │
           └──────────────────┼──────────────────┘
                              ↓
              以该 Agent 身份生成回复 → 发回群
```

### Agent 配置格式 (agents.yaml)

```yaml
agents:
  - name: "客户监控Agent"
    display_name: "客户哨兵"
    type: "virtual"          # virtual = Hermes 托管, platform = 外部平台
    role: "customer_monitor"
    persona: |
      你是客户监控专员。说话简洁、数据驱动、不带情绪。
      发现有异常第一时间报告，不做主观推测。
    capabilities:
      - "监控飞书多维表格中的客户数据变更"
      - "定时检查客户关键指标"
      - "异常检测与告警"
    routing:
      triggers: ["客户监控", "客户异常", "客户数据变更"]
    tools: ["feishu_bitable", "cronjob", "terminal"]
    cron_job_id: null         # 创建后回填
```

### 创建流程

1. **需求分析**：用户描述任务 → Hermes 判断是否需要新建 agent
2. **能力规划**：定义 Role、Soul、Skills、触发词
3. **基础设施搭建**：
   - 如果需要定时任务 → 创建 cron job
   - 如果需要数据源 → 配置飞书多维表格/webhook
   - 如果需要外部 API → 注册 MCP tool
4. **注册到群**：写入 `agents.yaml`，更新路由表
5. **测试**：用户 @ 该 agent 验证端到端

### 与平台 Agent 的区别

| | 平台 Agent (Aime/马斯克) | 虚拟 Agent |
|---|---|---|
| 创建方式 | 飞书开发者后台手动 | Hermes 配置化自动 |
| 运行载体 | 独立 app/bot | Hermes app 内部 |
| 能力边界 | 平台决定 | Hermes 工具集决定 |
| 灵活性 | 受限 | 完全可控 |
| 群内表现 | 独立 bot 身份 | 通过 Hermes 回复 |

### 已验证的限制

- 飞书 `chatMembers` API 过滤所有 bot，虚拟 agent 不会出现在成员列表
- 系统邀请消息不包含被邀请者 open_id，无法通过 API 区分不同虚拟 agent
- 虚拟 agent 的「独立身份」是通过不同的 display_name 和 persona 实现的，底层仍是 Hermes app
