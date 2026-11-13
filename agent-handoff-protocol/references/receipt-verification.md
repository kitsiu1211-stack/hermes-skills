# 回执回读核验（飞书，2026-11-02 实跑）

判「发出去了没有」的唯一合法依据是回读，不是发送返回值。以下命令都带 `--as bot`（用户身份会缺 `im:message.send_as_user` 权限）。

## 1. 核对方声称的回执

```bash
lark-cli im +messages-mget --as bot --message-ids om_xxx > /tmp/verify.json 2>&1
```

| 字段 | 意义 | 判据 |
|---|---|---|
| `deleted` | 是否已删 | 必须 false |
| `thread_id` | 在哪个话题（`omt_`） | null = 在主聊天流 |
| `thread_message_position` | 话题里第几条 | 复述给对方时贴这个数，比「我发了」硬得多 |
| `sender.name` / `sender.id` | 谁发的 | 同一账号显示名会变（实测同一 ou_ 一会叫 `Mark`、一会叫 `Mark 42`），认 open_id 不认名字 |
| `mentions[]` | @ 是否真生效 | 缺对方 open_id = 纯文本，对方收不到且不报错 |

`message_app_link` 里带 `thread_position`，可以直接甩链接让对方自己点进去看。

## 2. 决定回在话题里还是主聊天流

```bash
lark-cli im chats get --chat-id <oc_xxx> --as bot   # 看 chat_mode
```

- 目标消息 `thread_id` 有值 → 加 `--reply-in-thread`，留在原串
- 目标消息 `thread_id` 为 null（`chat_mode=group` 的普通流消息）→ **不要**加 `--reply-in-thread`，它会新建一个话题串，把一段对话劈成两半
- 原则：回在对方最近一条消息所在的观测面上，不回在「我觉得整齐」的位置

## 3. 回完立刻核自己这条

```bash
lark-cli im +messages-reply --as bot --message-id <对方最新 msg_id> \
  --text "$(cat /tmp/reply.txt)" --idempotency-key <业务键>-<日期>
```

正文先写进文件再用 `"$(cat ...)"` 传，长中文和换行不会被 shell 吃掉。回读写进 `/tmp/reply.txt` 时 `<at user_id="ou_xxx">Name</at>` 要用**半角引号**，全角 `“”` 会静默降级成纯文本。

回读自己这条要核四件事：`deleted=false`、`thread_id` 与预期一致、`mentions[]` 命中对方 open_id、**正文首尾各看一段防截断**（长度对不上通常是传参被截，不是平台吞字）。

## 4. 解析输出的两个坑

- `lark-cli` 的 JSON 前面可能插提示行（`[page 1] fetching...`、`warning: ...`），不要直接 `json.load`。把输出重定向到 `/tmp/x.json`，再用**单独一步**解析。
- 一条命令里写 `lark-cli ... ; python3 - <<EOF` 容易被网关的命令守卫误判拦下，拆成两步（命令一步、`execute_code` 解析一步）更稳。
- 列表字段名不统一：`+chat-messages-list` 是 `data.messages[]`，`+threads-messages-list` 是 `data.items[]`，写错永远得到 0 条且不报错。
- 话题 ID 不存在时返回 `{"ok":false,"error":{"subtype":"not_found","message":"thread ID not found for this message"}}` —— 说明你手上那条消息本身不在话题里，别当成权限问题重试。

## 5. 对账一句话模板

> 我核的是话题 omt_xxx（或：主聊天流 11-02 00:40–00:46 共 N 条）。你的 om_AAA 在第 34 位、om_BBB 在第 36 位，`deleted=false`，都在；我的 om_CCC 在 00:45 落主聊天流，`mentions[]` 命中你的 open_id。

先贴自己的观测面和 ID，再谈结论。这样即使判错，对方也能一眼指出是哪一层口径不一致，而不是互相怀疑。
