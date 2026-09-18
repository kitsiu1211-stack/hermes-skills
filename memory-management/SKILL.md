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

## 主动遗忘设计（敢忘）

> 2026-09-08 用户把 Today.ai 文章的「敢忘」概念落到了 memory 机制设计上：敢忘 ≠ 删除无效信息，敢忘 = 主动设计遗忘。现有「满了才压缩」是被动遗忘；敢忘要求**写入时定保质期、小遗忘日常化、季度把记忆亮给用户审、北极星 = 记忆改变决策的次数**。
> 四动作完整框架 + 用户的原话推理链 + 「敢忘手术」待办状态：`references/proactive-forgetting-design.md`

## 清理工作流

1. 导出当前内容，逐条标注 `[stated]` / `[inferred]` / `[observed]`
2. 删除所有非 `[stated]` 条目
3. 过程/技巧 → 放进对应 skill（不是 memory）
4. 合并重复
5. 目标：6-10 条、<50% 容量

### 🚨 批量 remove 陷阱：系统提示词里的 memory 快照会过期

memory 条目在会话中会被别的任务改动（新增/改写，比如顺手写了 model.routing 或改了 Obsidian 条目），系统提示词注入的快照可能已旧。批量 remove 时 old_text 照抄旧快照 → 一个不匹配整批失败（batch 是 all-or-nothing，所有 add/remove 全部不生效）。

- remove 的 old_text 用「短唯一子串」（如 `[stated]` 前缀 + 前几个字，或一条专属名词），别用会随内容漂移的整句。
- 失败时错误信息会返回 `current_entries`（当前真实条目列表），直接拿它重建 operations 再提交，别对着旧快照瞎猜。
- 压缩后不必追加「压缩时间戳」条目去浪费刚腾出的空间——使用率本身（<80%）就是防重复的闸。
