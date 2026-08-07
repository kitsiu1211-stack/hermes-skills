---
name: memory-compress
description: OptMem 四层金字塔压缩——定期将 memory.md 中的重复/过时/低权威条目压缩为高层规则。触发：memory 使用率 > 80% 或用户说"压缩记忆"。
category: productivity
---

# Memory Compress

## 触发

- memory.md 使用率超过 80%
- 用户说"压缩记忆""整理记忆""记忆太多了"
- 每月一次定期执行

## 四层金字塔

```
L3 行为规则 ← 精炼，永久保留
L2 压缩摘要 ← 合并合并再合并
L1 结构事实 ← 去重去冗余
L0 原始日志 ← Hermes session 自动覆盖，不管理
```

## 压缩流程

### Step 1: 读当前 memory + self-improvement

```
memory 工具 → 读现有条目
read_file ~/.hermes/memories/self-improvement.md → 读 E/C/I/S
```

### Step 2: 五级分类

每一当前 memory 入口标注层级和目标操作：

| 层级 | 条件 | 操作 |
|------|------|------|
| L3 | 行为约束/铁律，已写入 self-improvement I 表 | 并入一条总结 → 从 memory 移除原始 |
| L2 | 领域知识/客户反馈 | 合并同类 → 压缩为一条 |
| L1 | 用户档案/偏好/环境 | 去重 + 去冗余描述 |
| L0 | 单次事件/临时状态 | 从 memory 移除 |

### Step 3: 压缩执行

把用户档案、偏好、环境信息整合为 3-5 个压缩入口。行为规则如有冲动自我 improvement 的 I 表中的，归入一个汇总入口。

目标：压缩后使用率 < 60%。

## 压缩原则

1. **内容不丢失**：只合并和精简，不删除用户陈述中的事实。
2. **权威性排序**：[stated] > [observed] > [inferred]。
3. **冲突双保留**：旧事实被更新时不覆盖，使用记忆`替换`操作保留原记录线索。

## 防重复规则

压缩后记录压缩时间戳。除非使用率再次超过 80%，否则不重复压缩。
