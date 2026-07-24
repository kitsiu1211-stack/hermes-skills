---
name: handoff
description: 生成交接文档，让下一个 Agent/人无缝接手当前工作。触发：流水线 handoff 阶段。
---

# Handoff

将当前工作打包为交接文档，让下一个 Agent 或人类可以无缝继续。

## 何时触发

- implement 阶段结束后
- 用户说「交接」「handoff」
- 流水线 handoff 阶段

## 流程

### 1. 收集上下文

提取当前工作状态：
- 完成了什么（已解决的 tickets、合并的 PR）
- 还有什么没做（剩余 tickets、已知问题）
- 关键文件路径
- 运行方式（命令、环境变量、依赖）

### 2. 去重

不要重复已在其他产物中的内容（PRD、ADR、issues、commits）。引用路径或 URL 即可。

### 3. 脱敏

移除敏感信息（API key、密码、个人身份信息）。

### 4. 格式

```markdown
# Handoff: <项目/功能名>

**日期**: YYYY-MM-DD

## 完成了什么
- 已完成清单

## 还有什么没做
- 待办清单（含优先级）

## 关键文件
- `path/to/file` — 说明

## 如何运行
```bash
# 命令
```

## 已知问题
- 问题描述和临时方案

## 下一个 Agent 应该知道的
- 关键上下文
```

### 5. 发布

写入 `docs/handoffs/<date>-<feature>.md`。

可选：如果用户需要，用 `cronjob` 创建一个定时继续的任务。
