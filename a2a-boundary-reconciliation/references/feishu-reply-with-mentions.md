# 飞书：定位当前消息 + 带真 @ 发进话题（2026-11-09 实测）

场景：要回群里某个 Agent 的一条消息，必须在话题内、且 @ 是真 mention（对方 `mentions` 数组非空才算送到）。

## 第 0 步：为什么不能靠最终响应

```
hermes-agent/plugins/platforms/feishu/adapter.py
  _build_outbound_payload(content, prefer_post)
    → msg_type="post", _build_markdown_post_payload(content)
      → _build_markdown_post_rows(content) → [[{"tag":"md","text": content}]]
```

整段内容只是一个 `md` 元素，**没有 at 元素解析路径**，`send()` 也不注入 mentions。
所以最终响应里写 `<at user_id="ou_xxx">名字</at>` 只会被当字面文本渲染。真 @ 必须自己发。

## 第 1 步：拿到「当前这条消息」的 message_id

`--reply-in-thread` 必须挂在一个真实 `om_` 消息上。**别指望列表接口**：

- `lark-cli im +threads-messages-list --thread omt_xxx`：实测当天话题里的消息查不到，只回旧批次（total=10 全是十天前的）
- `lark-cli im +chat-messages-list --as user|bot --chat-id oc_xxx`：同样看不到当天话题内的新消息（最新停在昨天）

**可靠路径：从 gateway 日志里捞 inbound 事件**（日志自带 message_id、chat_id、sender、thread）：

```bash
grep -n "Inbound group message received" ~/.hermes/logs/gateway.log | tail -5 | cut -c1-300
# → id=om_x100b60269ef8b0a0ce9fcc14836200a type=text chat_id=oc_xxx sender=user:ou_xxx text='...'
```

按关键词定位那条（`grep -n "哨兵告警" ~/.hermes/logs/gateway.log | tail -3`），取 `id=om_...`。

然后确认它属于哪个话题：

```bash
lark-cli im +messages-mget --as bot --message-ids om_xxx --json \
  | python3 -c "import sys,json;m=json.load(sys.stdin)['data']['messages'][0];print(m['thread_id'])"
```

## 第 2 步：发（长文本写文件，Python 传参，绕开引号地狱）

```python
import subprocess
text = open('/tmp/reply.txt').read()   # 用 write_file 落地，内含 <at user_id="ou_xxx">名字</at>
r = subprocess.run(['lark-cli','im','+messages-reply','--as','bot',
  '--message-id','om_xxx','--reply-in-thread','--text',text,
  '--idempotency-key','w46-reply-20261109-1018','--json'],
  capture_output=True, text=True, timeout=120)
print(r.stdout)
```

要点：
- `--as bot` 必带（user 身份报 `im:message.send_as_user` missing scope）
- `<at user_id="ou_xxx">` 的引号必须半角，全角会静默降级成纯文本
- `--idempotency-key` 必带，防止催出双回执
- 目标消息本身带 `thread_id` 才加 `--reply-in-thread`，否则会新开一串

## 第 3 步：核回执（不看调用返回 ok，要看 mentions）

```bash
lark-cli im +messages-mget --as bot --message-ids <新的om_id> --json
# 期望：thread_id=omt_xxx，mentions=[{"id":"ou_...","key":"@_user_1","name":"袁鑫杰"}, ...]
```

`mentions` 里每个人都在，才算真 @ 成功。`accessor` 报 'str' object has no attribute 'get' 只是解析脚本写错（mentions 结构是扁平 dict），不是投递失败。

## 第 4 步：最终响应收尾

群里的最终响应会自动再发一条。所以手动发出长文后，最终响应只留 2-4 行：
- 一句「已在话题里回了 Mark（message_id + mentions 已核）」
- 唯一需要人动手的那件事（链接单独一行）
- 链接过期怎么办（「过期说一声我重生成」）

## 历史坑

- 群里同名群可能不止一个：`lark-cli im +chat-search --as user --query "<群名>"` 确认 chat_id，别用 +chat-list 翻页猜
- `+chat-list` 返回键是 `data.chats`（不是 items）；`+threads-messages-list` 返回 `data.messages`，`+chat-messages-list` 也是 `data.messages`
