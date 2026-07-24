---
name: implement
description: 基于 spec/tickets 实现功能——TDD 驱动，自动类型检查 + 代码审查。触发：流水线 implement 阶段。
---

# Implement

实现 tickets 中描述的工作。按依赖顺序逐个实现。

## 何时触发

- to-tickets 阶段结束后
- 用户说「实现 #3」「做这个 ticket」
- 流水线 implement 阶段

## 流程

### 1. 选择下一个 ticket

按依赖顺序取**第一个未被阻塞的 ticket**。

### 2. TDD 实现

加载 `tdd` skill，严格执行红-绿循环：

1. **确认测试接缝**（参考 PRD 中的测试决策）
2. **红**：写一个失败测试
3. **绿**：写最少代码让测试通过
4. 重复直到 ticket 完成

期间持续运行：
- 类型检查（每次改动后）
- 单个测试文件（每次实现后）
- 完整测试套件（ticket 完成后一次性跑）

### 3. 代码审查

加载 `code-review` skill，对变更做双轴审查。

### 4. 提交

提交变更到当前分支，commit message 包含 ticket 引用。

### 5. 下一个

回到步骤 1，取下一个未被阻塞的 ticket。直到全部完成。

## 关键原则

- **一 ticket 一上下文**：不要在一个窗口里做多个 ticket
- **红必须在绿之前**：不跳过测试
- **最小实现**：不要预判未来需求
- **审查即完成**：审查通过才算 ticket done
