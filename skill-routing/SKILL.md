---
name: skill-routing
description: Skill路由引擎：8 Zone匹配架构，收到消息先匹配Zone只加载命中技能
user_invocable: false
version: "1.0.0"
---

# Skill 路由引擎

收到用户消息后，先匹配 Zone，只加载命中 Zone 的 skill。永不全量遍历。

## Zone 匹配规则

| 触发词 | Zone | 加载的 skill |
|--------|------|-------------|
| 旁听/入会/会议/纪要 | 1 | feishu-meeting-listen, meeting-audit, meeting-minutes, lark-vc, lark-vc-agent, lark-minutes, lark-note, meeting-followup-material |
| 客户/销售/方案/续约/C360 | 2 | c360-cli, sales-playbook, renewal-proposal, client-handover-checklist, customer-research, workshop-interest-activation, opportunity-cross-analysis, manager-ai-onboarding, output-style-xiaoguanjia |
| 发链接/文章/分析/看看/公众号 | 3 | 文章分析, ljg-rank, ljg-learn, ljg-plain, ljg-card, ljg-qa, human-writing, explain-like-village-elder, deep-grill, grill-with-docs, diverge-converge, knowledge-capture |
| lark-cli/飞书API/卡片/文档/多维 | 4 | lark-cli, lark-doc, lark-im, feishu-api, feishu-card-send, feishu-group-chat, beautiful-feishu-whiteboard, hermes-feishu-gateway, lark-shared, lark-apps, miaoda-deploy |
| Obsidian/记忆/回顾/Ebbinghaus/技能同步 | 5 | obsidian, ebbinghaus-review, memory-compress, memory-management, daily-session-summary, weekly-deep-read, skill-hub, 双周Skill同步, ai-industry-brief |
| Agent群/协作/Aime/代理 | 6 | agent-group-collab, aime-query, multi-agent-orchestration, trae-loop-engineering |
| 咖啡/地图/附近/X | 7 | my-coffee, find-nearby, xitter |

## Zone 8

Zone 8 包含所有不加载的 skill。除非用户点名，永远不碰。完整列表见 Obsidian `AI场景/Skill路由表.md`。

## Token 优化

当前 243 个 skill，每轮系统 prompt 注入 ~5554 tokens。Zone 路由在同 profile 内省 ~15%（减少 skill_view 全文加载）。拆 profile 到 40 个 skill 时省 84%。

## 执行规则

1. 收到消息 → 提取触发词 → 匹配 Zone
2. 只加载命中 Zone 的 skill 全文（skill_view）
3. 同一 Zone 内按使用频率排序加载
4. 用户显式点名某个 skill → 直接加载，不管 Zone
