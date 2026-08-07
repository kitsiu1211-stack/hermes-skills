# DataFlow-Harness 架构参考

**来源**: 北大 PKU, arXiv 2607.16617, 2026-07-18

## 核心问题: NL2Pipeline Gap

Agent 生成一次性脚本 ≠ 可持久化、可编辑、可复用的平台产物。

## 四层架构 → SkillHub 映射

```
用户自然语言 → DataFlow-WebUI（对话+可视化画布）
                    ↕
              MCP Tools Layer（读状态→增量改→校验→提交）
                    ↕
            Data Pipeline Backend（权威数据源）
                    ↕
            DataFlow-Skills（程序知识，不直接改状态）
```

| Harness 层 | SkillHub 对应 |
|-----------|--------------|
| DataFlow-Skills | SKILL.md — 提供程序知识给 Agent |
| MCP Tools Layer | lark-cli + skill_validator + skill_mutate — 操作约束层 |
| Pipeline Backend | 文件系统 + skill_graph.json — 权威数据源 |
| WebUI | HTML 中枢页 + 飞书对话 — 双模界面 |

## 实验结果

| 对比 | 端到端通过率 | 成本 | 延迟 |
|------|------------|------|------|
| DataFlow-Harness | 93.3% | 基准 | 基准 |
| Vanilla Claude Code | - | +262% | +100% |
| Context-Aware Claude Code | +0.9pp | +74% | - |

## SkillHub 已借鉴的实现

1. **校验层** (`skill_validator.py`): 操作前校验 YAML frontmatter、必填字段、引用完整性
2. **增量突变** (`skill_mutate.py`): 类型化操作 (update_field/add_tag/add_related)，不碰全文
3. **依赖图** (`skill_graph.py`): 解析所有 Skill 的引用关系，删除前检查断裂
4. **双模同步**: Obsidian Markdown + HTML 中枢页 — 同一份数据两个视图
