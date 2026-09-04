# UI Skills Toolkit (ibelick/ui-skills)

## 安装位置
`~/Documents/ui-skills/` — ibelick/ui-skills ⭐6.5k GitHub

## 可用 Skill（7个）

| Skill | 用途 | 触发场景 |
|-------|------|---------|
| `ui-skills-root` | 路由入口，根据任务选子 skill | 任意 UI 任务入口 |
| `baseline-ui` | 快速去 AI slop：间距/层级/字体 | 界面需要快速清理 |
| `improve-ui` | 完整审计 → 出修复计划（最强） | 审查/重构/设计移交 |
| `create-design-md` | 从代码反向生成 DESIGN.md | 需要规范化设计文档 |
| `fixing-accessibility` | WCAG 无障碍修复 | 无障碍审计 |
| `fixing-metadata` | SEO/社交元标签修复 | 页面元数据问题 |
| `fixing-motion-performance` | 动画性能优化 | 动画卡顿/jank |

## 协同机制（Kimi Code / TRAE 用）

1. 接到 UI 任务 → 用 `npx ui-skills start` 路由到对应 skill
2. 或直接加载 `~/Documents/ui-skills/skills/<skill-name>/SKILL.md`
3. `improve-ui` 有 `agents/openai.yaml` 和 `references/plan-template.md` — 支持 sub-agent 执行

## 安装命令

```bash
cd /tmp && git clone --depth 1 https://github.com/ibelick/ui-skills.git
cp -r /tmp/ui-skills ~/Documents/ui-skills
```
