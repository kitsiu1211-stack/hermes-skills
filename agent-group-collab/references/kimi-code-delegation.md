# Kimi Code 委派

## 何时用 Kimi Code

用户说「让 kimi code 搭一个」「kimi code 在群里」时，直接把需求文本发到 Agent协作群。

Kimi Code 会监控群聊并自动回复代码。

## 命令

```bash
lark-cli im +messages-send \
  --chat-id oc_219a613c13292855c2dc4b80e59dfd6e \
  --as bot \
  --text 'Kimi Code，<需求描述>'
```

## 关键注意事项

1. **不需要 @mention** — Kimi Code 监控群聊内容，直接发 plain text 即可
2. **用 `--as bot`** — user identity 缺少 `im:message.send_as_user` scope
3. **需求要完整自包含** — Kimi Code 没有上下文，题目、选项、技术要求全写进消息
4. **回复在主聊天** — 用 `lark-cli im +chat-messages-list` 轮询获取
5. **回复不稳定** — webhook 偶尔死，如果 2 分钟内没回复，重新发一次

## 需求模板

```
Kimi Code，帮我搭一个 <用途>：

<技术要求>（单HTML文件、移动端适配等）

<具体内容>（题目、选项、正确答案）

<特殊要求>（管理后台、分页等）
```

## 示例：AI 认知答题

```bash
lark-cli im +messages-send \
  --chat-id 'oc_219a613c13292855c2dc4b80e59dfd6e' \
  --as bot \
  --text 'Kimi Code，帮我搭一个 AI 认知摸底答题 H5：
单 HTML 文件，极简暗色 UI，移动端适配。6 道单选题，答完出分。管理后台 ?mode=admin 显示分布柱状图+满分名单。localStorage。

题目（✓=正确答案）：
Q1 Chatbot和Agent区别？ BAgent自主调用工具执行动作✓
Q2 Skill？ C可沉淀复用AI能力模块✓
Q3 Harness工程？ BAI与业务工具链整合✓
...'
```
