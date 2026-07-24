# Hook 机制：在 LLM 之前执行确定性工作

两个生产级 Hook（2026-07-17 实现）：

## ⑥ 输出脱敏 Hook

`~/.hermes/scripts/sanitize_output.py` — 在所有 LLM 输出发送给用户前自动替换内部敏感 ID。正则匹配，100% 命中，不进 prompt，零 token。

覆盖：`ou_xxx`（用户ID）、`cli_xxx`（应用ID）、`766*`（会议ID）、`sk-/fk-`（API Key）、`t-`（Token）。

## ④ lark-cli 截断 Hook

`~/.hermes/scripts/lark_cli_wrapper.py` — 拦截所有 lark-cli 调用结果，自动截断/摘要。

- **C360 查询**：只保留 `name/ARR/阶段/跟进/CSM` 等关键字段
- **会议列表**：只保留 `title + meeting_id + meeting_no`
- **通用列表**：摘要化，最多 20 条
- **超长输出**：截断到 3000 字符

安装：`~/.hermes/scripts/hooks/lark-cli` → PATH 注入 `~/.hermes/.env`。

## 核心原理

```
Skill + Script:  输入 → [LLM] → "要调 Script 吗？" → 调或跳 → 输出 （执行权在 LLM）
Hook:            输入 → [Hook Script] → 结果 → [LLM] → 输出 （执行权在框架）

Prompt = 软约束（LLM 可能忘）
Script = 硬约束（LLM 决定什么时候调，可能跳）
Hook   = 无条件执行（在 LLM 意识外，零遗忘）
```

## Token 节省

Hook 不进 prompt，代码逻辑零 token。确定性工作（脱敏/截断/格式化/模型路由）从 LLM 剥离到框架层，LLM 只做推理。
