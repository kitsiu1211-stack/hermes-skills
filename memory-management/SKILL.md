---
name: memory-management
description: Maintain Hermes memory — [stated] enforcement, domain routing, privacy redlines, and cleanup workflows. Load when the user asks to reorganize or audit memory, or when memory grows stale with inferences and procedures.
category: productivity
---

# Hermes 记忆管理

遵循 Claude Fable 5 设计原则的 Hermes 记忆维护方法论。
详见 `references/fable-5-memory-excerpt.md`。

## 实测案例（2026-07-27 袁鑫杰 session）

**清理前**：41 条，2156 chars，98% 容量——过程、推断、工具技巧混杂。
**清理后**：6 条，865 chars，39% 容量——纯 `[stated]` 事实。

被踢掉的 15 条类型：
- 三次流水线 → 推断，非用户说的
- 授权模型 → 自创框架
- 旁听脚本细节 → 过程，应在 skill 不在 memory
- lark-cli 全品类覆盖 → 工具习惯
- 跨会话双向记忆 → 机制，非用户事实

## 核心铁律：只存 [stated]

**唯一写入标准**：用户亲口说过的事实。

| 可以存 | 不能存 |
|--------|--------|
| 用户说"我是 RM" | 你推断"用户管理客户" |
| 用户说"用 MiniMax 识图" | 你观察"MiniMax 比 DeepSeek 好" |
| 用户说"不要轮询" | 你总结"用户偏好手动" |
| 用户的选择 | 你提出的选项列表 |
| 用户确认的决策 | 你的推理过程 |

**禁存清单**：
- 过程/技巧（三次流水线、脚本调试路径）
- 推断（"用户喜欢 X 类型"）
- Claude 的搜索结果
- 工具使用习惯（lark-cli 参数、飞书 flag）
- 环境故障（依赖缺失、版本 Bug）
- 死链接/已过期的凭证

## 写入时机：实时，不等

- 用户说出一条事实 → 立刻存，不等对话结束
- 如果现在对话结束，那一行应该已经在 memory 里了

## 隐私红线

绝不存：种族、宗教、性取向、健康状况、住址、电话号码、PII、心理评估、MBTI。不存占位符——"有健康问题"也不行。

## 清理工作流

1. 导出当前内容，逐条标注 `[stated]` / `[inferred]` / `[observed]`
2. 删除所有非 `[stated]` 条目
3. 过程/技巧 → 放进对应 skill（不是 memory）
4. 合并重复
5. 目标：6-10 条、<50% 容量
