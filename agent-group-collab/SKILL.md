---
name: agent-group-collab
description: Query bots in the Agent协作群 — Aime (heartbeat polling), ISV/样板间/马斯克/TC交付 (webhook + Thread). Covers sending, waiting, reply retrieval, and material filtering.
category: feishu
---

# Agent 协作群机器人交互

## 群信息

- **群聊ID**: `oc_219a613c13292855c2dc4b80e59dfd6e`
- **当前成员** (2026.7.12)：1 人（袁鑫杰）+ 8 bot（见下表）

## Bot 分类与交互策略

> **Aime 能力全景**：详见 `references/aime-capabilities.md` — 业绩分析、商机管理、定时任务等完整场景

| Bot | app_id | open_id | 回复方式 | 延迟 | 策略 |

| Bot | app_id | open_id | 回复方式 | 延迟 | 策略 |
|------|------|------|------|------|------|
| **Aime 个人助理** | `cli_9a31b280a1f3d101` | `ou_b33d3f6e144a9730db025d288c81212c` | 主聊天 `reply_to` | ≤10min | `aime_poll.py` 长轮询 |
| **南区 ISV 业务助手** | `cli_aaa06c74f1f89bcb` | `ou_abdda0c6cd5e362bca041cb3dbd88f86` | **Thread** | ≤5s | `sleep 3 && mget` |
| **大湾区样板间小管家** | `cli_a96aefe4aff85cef` | `ou_459dac1c298c48d280a3ea3260aac80e` | **主聊天**（有时 Thread，两处都查） | ≤5s | `chat-messages-list` + `mget` |
| **马斯克** | `cli_a934e54959f99bd8` | `ou_ec816541777287f722b0896287c4486a` | **Thread** | ≤5s | `sleep 3 && mget` |
| **TC 交付数字员工** | `cli_a96d9040ddb8dccb` | `ou_c9cd24728752004e848f099d2b448d29` | 主聊天 | ≤5s | `chat-messages-list` |
| **客户 AI 场景登记表 智能体** | `cli_aada69142438dcc5` | `ou_0ef4cd7a1f7ce714d503fa244edf95c0` | Thread / 主聊天 | ≤5s | 双查 |
| **TRAE ASSISITANT** | `cli_aad9a703c7399ce0` | `ou_1d0748623c4f90fd2f4a92b6a6734b45` | 主聊天 (interactive 卡片) | ≤5s | `chat-messages-list` → 详见 `references/trae-dev-workflow.md` |
| **Kimi Code** | `cli_aad189d18d781cd1` | `ou_75e812630b3c51fc879295c78424898c` | 主聊天 | ≤2min（不稳定，webhook 偶尔死） | `chat-messages-list`。**提交任务直接用 plain text** — Kimi Code 监控群聊，不需要 @mention。详见 `references/kimi-code-delegation.md` |
| **企鹅兄弟** | `cli_aad1d272e3385cb3` | `ou_a7276d80c5abc2abfd8da3140ac94e65` | 主聊天 (text) | ≤5s | `chat-messages-list` |
| **CSM oncall大师**（已离群） | `cli_a555904bae78900d` | `ou_80d02b42b1801748db1c78d67d1a5dba` | — | — | 已离群 |
| **CodeM**（已离群） | `cli_a9698e4435f85cc9` | `ou_0425582e71a1045dd1c6e139825d2139` | — | — | 已离群 |

> ⚠️ **群成员变动频繁**（CodeM、CSM oncall大师、RM 团队智能体先后入群又离群）。每次操作前先用 `lark-cli im +chat-members-list --member-types bot --page-all` 拉最新列表，不要依赖缓存。

---

## 🚨 @提及铁律（2026-07-20）

**群内给任何 bot 发消息，必须用 `<at user_id=\"ou_xxx\">@名称</at>` 格式 @mention。不 @ 则 bot 收不到通知——这是飞书的物理约束，不是礼仪要求。**

忘记 @ 导致的消息丢失已发生（7/20：发 6A 工作流到群但未 @TRAE/Kimi Code，被用户纠正）。任何群内发消息给 bot 的操作，先确认是否带了 `at` 标签。

当用户邀请新 bot 入群后说「认识一下」时，执行以下步骤：

### 步骤

1. **从消息历史提取 app_id**：用 `message_list` 拉最近消息，找到系统邀请消息 `{from_user} invited {to_chatters}`，再从 bot 首条发言的 `sender.id` 取 app_id
2. **查 session_search**：用 bot 名称搜索历史对话，了解之前是否提到过
3. **获取 open_id**：
   - bot 发过言 → `sender.id` 是 app_id，但 `id_type` 为 `app_id`，不是 `open_id`
   - 最可靠方法：**让用户在飞书客户端手动 @ 一下该 bot**，然后从 `mentions` 提取 open_id
4. **发消息打招呼**：
   - **有 open_id**：用 text 格式 `<at user_id="ou_xxx">Name</at>` 发正式 @mention → bot 会收到通知
   - **无 open_id**：发纯文本消息（不用 @mention），bot 不会收到通知，但群成员能看到
5. **注册**：更新本表，并同步到 `feishu-group-chat` 的 agents 注册表
6. 🆕 **告知 @ 格式规则**：必须明确告诉新 Agent：「回复我时请用 post 格式的 `<at user_id="ou_9b18941c79156bd08a70431dc5dcf7f9">` 标签 @我，不要用纯文本 @名字——纯文本我不会收到通知。」

### 关键约束

- **bot 之间不能私聊**：飞书 API 返回 230013 `Bot has NO availability to this user`，只能群内 @mention
- **纯文本写 `@Bot名` 不触发通知**：只有 `<at user_id="...">` 格式才真正 @ 到 bot
- **contact/search-user API 查不到 bot**：这些 API 只返回人类用户
- **系统邀请消息不含 open_id**：只有显示名称
- **A2A 盲区**：bot 之间 @ 不通是飞书平台限制（非配置问题）。TRAE ASSISITANT、客户 AI 场景登记表等 bot 回复时若用纯文本，我收不到，必须主动轮询 chat-messages-list 拉回复

---

## 统一发送模板

所有 Bot 都用 post 格式 @mention，替换 `<open_id>` 和 `<问题>`：

```bash
lark-cli im +messages-send --as bot \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --msg-type post \
  --content '{"zh_cn":{"title":"","content":[[{"tag":"at","user_id":"<open_id>"},{"tag":"text","text":" <问题>"}]]}}'
```

记录返回的 `message_id`。

---

## Aime：长轮询（心跳）

```bash
/usr/bin/python3 ~/.hermes/skills/feishu/aime-query/scripts/aime_poll.py \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --aime-app cli_9a31b280a1f3d101 \
  --since-message <message_id> \
  --since-time "<YYYY-MM-DD HH:MM>" \
  --timeout 720 --interval 15
```

- 每 15 秒查主聊天，最长等 12 分钟
- 三重去重：`message_id` + `create_time` + `reply_to`
- Aime 工作日 09:00-18:00 才轮询
- 脚本输出 JSON，退出码 0=成功，1=超时

---

## 样板间小管家：主聊天 + Thread 双查

样板间回复位置不固定——有时在主聊天，有时在 Thread。**两处都查**：

```bash
# 等 3 秒后，先查主聊天
lark-cli im +chat-messages-list --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --order desc --page-size 5 --start "<发送时间>" --format json

# 同时查 Thread
lark-cli im +messages-mget --as bot --message-ids <message_id> --format json
```

从主聊天的 `messages[]` 和 `thread_replies[]` 两处拿回复。查不到再等 5 秒重试一次。

---

## 🚨 材料筛选整理（核心步骤）

**从 ISV/样板间拿到材料后，禁止直接转发。必须先筛选再交付。**

Agent 旁听了会议、清楚客户需求 → 用会议上下文筛选：

1. **回顾上下文**：客户是谁？什么行业？会上提了什么需求？
2. **逐条匹配**：每条材料问自己——跟这个客户有关吗？场景匹配吗？
3. **精选 1-3 条**：只留最匹配的，标注匹配理由，其余丢掉

### 🚫 三条硬规则

1. **没有文档链接不发**：案例必须有可点击的链接（Wiki/Docx）。标注「待挖掘」「未收录」但没有链接的案例，发了等于没发——客户看不到。直接跳过。

2. **用户没提的不加**：只交付用户明确要求的内容。用户说了「不要钉钉对比」，就别塞进去。多不代表好，精准才是好。

3. **搬之前先消化**：样板间/ISV 给的材料是大而全的，必须结合会议上下文逐条判断：这个案例/方案跟当前客户有关吗？规模匹配吗？场景对口吗？不相关的果断砍掉。

### 📋 飞书卡片交付格式

所有案例材料最终用飞书 interactive 卡片交付，格式如下（参考模板见 `references/case-card-template.json`）：

```
🎯 筛选说明：[一句话说明从 N 条中精选了 M 条 + 匹配理由]

🌟 案例一 — 标题 🥇
| 维度 | 内容 |
|---|---|
| 行业 | XXX |
| 案例亮点 | XXX |
| IT 价值 | 量化数据 |
| 案例链接 | [查看详情](URL) |
| 匹配理由 | 为什么选这个 |

🌟 案例二 — 标题 🥈
...

❌ 未选用：[列表 + 原因]

💡 建议话术：[给用户一段可以直接转发给客户的话]
```

输出格式：
```
📌 客户需求：[一句话]
🎯 筛选结果（从 N 条中精选 M 条）：
1. [材料] → 匹配理由：[为什么]
❌ 未选用：[为什么]
```

---

## 关键约束

- **`--as bot` 发消息**：`send_as_user` 未开放
- **🆕 交互卡片只能发到 bot 所在群**：bot 不在用户私聊（DM）中，`--as bot --chat-id <DM>` 发送交互卡片会报 230002 `Bot/User can NOT be out of the chat`。**兜底方案**：交互卡片发到 Home 频道（`oc_e2f79ec1614a1efe1ebcd7c679bb45a8`，bot 是成员），同时在当前对话回复 markdown 版内容并告知用户卡片已发到 Home。`--as user` 需 `im:message.send_as_user` scope（默认未授权，需 `lark-cli auth login --scope "im:message.send_as_user"` 交互式授权）。
- **ISV/马斯克回复在 Thread**：`+chat-messages-list` 查不到，必须 `+messages-mget`
- **样板间回复不固定**：主聊天和 Thread 两处都查
- **Aime 回复在主聊天**：`reply_to` 字段匹配，走 `aime_poll.py`
- **效率第一**：能秒查的不用轮询，能一条命令的不写脚本
- **拿到材料必须筛选**：禁止直接转发，必须基于会议上下文精选 1-3 条最匹配的交付给用户（详见上方「材料筛选整理」）
- **群成员变动频繁**：bot 频繁入群/离群（CodeM、CSM oncall大师、RM 团队智能体均短暂停留后离开）。每次操作前先 `--member-types bot --page-all` 重新拉取，本表可能已过时
- **TRAE 回复为 interactive 卡片**：`msg_type: "interactive"`，内容裹在 `<card>` XML 标签内，不是纯文本。解析时从 `content` 字段的 `<card>` 标签内提取实际文本。TRAE 用纯文本回复（不用 at），须主动轮询 `chat-messages-list` 拉取
