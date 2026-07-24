# TRAE 开发协作工作流

TRAE ASSISITANT 是桌面悬浮窗项目的开发 agent。与普通 bot 不同，TRAE 的交互涉及代码审查和迭代反馈。

## 发送消息

与其他 bot 相同，用 post 格式 @mention：

```bash
lark-cli im +messages-send --as bot \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --msg-type post \
  --content '{"zh_cn":{"title":"","content":[[{"tag":"at","user_id":"ou_1d0748623c4f90fd2f4a92b6a6734b45"},{"tag":"text","text":" <问题>"}]]}}'
```

## 获取回复

TRAE 回复为 `interactive` 卡片类型（`msg_type: "interactive"`），内容裹在 `<card>` XML 标签内。**不会用 at 回复**，必须主动轮询：

```bash
lark-cli im +chat-messages-list --as bot --chat-id oc_219a613c13292855c2dc4b80e59dfd6e --page-size 10 --order desc --json
```

从 `messages[]` 中找到 TRAE（`sender.id: "cli_aad9a703c7399ce0"`）的回复。

## 编排者角色

用户要求 Hermes 做**核心编排 Agent**，调度 TRAE 等专业 Agent 完成任务。角色分工：

- **Hermes（编排者）**：给需求、接收交付物、本地测试验证、给精确反馈
- **TRAE（编码者）**：写代码、修改、截图效果

不要越俎代庖——任务是帮 TRAE 把活干好，不是替 TRAE 写代码。

## 🚨 代码交付问题

**TRAE 会把代码拆成多段卡片消息发送**（如 10 个 fragment），拼接时缩进全乱、方法边界断裂，无法直接运行。

### 解决方案

**永远不要让 TRAE 用文本发代码。** 要求它：
1. 上传文件到群聊（`--file` 附件）
2. 或发 Gist / Pastebin 链接

```bash
# 示例：要求 TRAE 以文件形式发代码
lark-cli im +messages-send --as bot \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --msg-type post \
  --content '{"zh_cn":{"title":"","content":[[{"tag":"at","user_id":"ou_1d0748623c4f90fd2f4a92b6a6734b45"},{"tag":"text","text":" 把 app.py 以文件形式上传到群聊，不要发文本——上次拆成10段拼接后缩进全乱。"}]]}}'
```

如果已经收到碎片代码且 TRAE 无法重发，用 `chat-messages-list` 查 `resources/download` 字段下载附件。

## 反馈原则

当 TRAE 交付代码/截图时，反馈要求：

1. **具体**——不说"做得好"或"太差了"，说"数据没加载，API 请求没通，检查 endpoint"
2. **可操作**——每条反馈对应一个可修改的点
3. **先跑起来再改**——用户哲学：ship fast, iterate。不要等完美的最终版，能跑就先跑，边跑边改
4. **主动测试**——拿到代码就本地跑一遍，用自己的测试结果反馈，而不是转发 TRAE 的输出。有报错就把终端输出原样贴给 TRAE，不要转述

## 典型节奏

```
@TRAE 发需求 / 反馈（含精确报错原文）
  → 几秒后 chat-messages-list 查回复
  → TRAE 回复卡片（interactive），内容在 <card> XML 内
  → TRAE 交付代码文件 → 下载到本地
  → 本地跑一遍 → 把终端报错原样贴给 TRAE
  → TRAE 修改 → 再查 → 再测试
```

## lark-cli 输出解析注意

`chat-messages-list` 的 JSON 输出第一行可能是 warning（如 `reactions_partial_failed`），解析前跳过第一行：

```python
lines = output.split('\n')
data = json.loads('\n'.join(lines[1:]))
```
