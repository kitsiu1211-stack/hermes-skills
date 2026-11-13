# lark-cli 实操字段 / 参数 / 超时坑

全部在 2026-11-10 真实飞书域操作中踩到并验证（会议旁听、取妙记、发纪要卡片）。

## 1. `docs +fetch` 正文在 `data.document.content`

```python
# ✅
c = json.load(open("/tmp/d.json"))["data"]["document"]["content"]
# ❌ 拿到空串，看起来像权限问题，其实是取错字段
c = d.get("data", {}).get("content", "")
```

`+fetch` 结构：`{ok, identity, data: {document: {content, title, ...}, tips}, _notice}`。
写脚本前先 `print(list(d["data"].keys()))` 确认路径，否则会得到 `total lines: 0`
然后误判「文档没权限 / 没内容」。

## 2. `+detail` 类命令参数是复数

| 需求 | 正确 | 错写 |
|---|---|---|
| 会议详情 | `vc +detail --meeting-ids <id>` | `--meeting-id` |
| 妙记详情 | `minutes +detail --minute-tokens <tok>` | `--minute-token` |

报错会给 `did you mean --meeting-ids?`，照用即可。

## 3. `im` 子命令名

| 需求 | 正确 | 说明 |
|---|---|---|
| 会话信息 | `im chats get --chat-id <id>` | 不是 `im chat get` |
| 关键词搜消息 | `im +messages-search --query ...` | 需独立 scope `search:message` |
| 拉会话消息 | `api GET /open-apis/im/v1/messages`（`container_id_type=chat`） | `im +messages-list` 不存在 |

`search:message` 不在会议/Gateway 的 scope 里。缺 scope 时按需单独授这一个，
不要全量重跑 `auth login`。

## 4. 大输出命令：先落盘，再单独解析

`docs +search` / `docs +fetch` / `vc +detail` / `calendar +agenda` /
`calendar +search-event` 单次 15–90 秒、输出几十 KB。
**在同一条命令里 `| python3 -c "..."` 内联解析很容易撞执行超时或审批中断**，
整条白跑还得重来。

```bash
# 第一步：只落盘
lark-cli docs +search --as user --query "灵宠" --page-size 8 --json > /tmp/pet.json 2>&1
```

```python
# 第二步：独立 .py 脚本读文件解析（别内联）
import json
d = json.load(open("/tmp/pet.json"))
for r in d.get("data", {}).get("results", []):
    m = r.get("result_meta", {})
    t = r.get("title_highlighted", "").replace("<h>", "").replace("</h>", "")
    print(t, "|", m.get("url"))
```

落盘成功就不会丢，解析失败可反复重跑而不用重新请求。

## 5. `calendar +agenda` 的 `data` 有时直接是 list

同一 CLI 不同命令包裹层不一致，解析要归一：

```python
items = d if isinstance(d, list) else (
    d["data"] if isinstance(d.get("data"), list)
    else d.get("data", {}).get("items", [])
)
```

漏了会 `'list' object has no attribute 'get'`。

## 6. 私聊 vs 群聊判定

```bash
lark-cli im chats get --as bot --chat-id <id> --json
```

`chat_mode == "p2p"` 且 `owner_id` == 本人 open_id → 本人私聊（Home 频道即此）。
决定要不要记「私聊交付索引」时靠这个区分，别靠 chat_id 长相猜。

## 7. 卡片发送必须回读验证

发送只返回 `message_id`；**是否真的可见要回读**：

```bash
lark-cli im +messages-mget --as bot --message-ids om_xxx --json
# 结果在 data.messages[]，不是 data.items[]
```

回读到完整 content 才算送达。不要发完就报「已发送」。
