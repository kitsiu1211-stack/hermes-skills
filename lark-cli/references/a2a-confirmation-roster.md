# A2A 群内规则广播 → 已读确认 → 接入台账（2026-10-29 实测）

场景：在 Agent 协作群里发一份**群内协作规则**（本项目里叫 A2A 交接规则 v1），要求所有 bot 回一行确认，
并约定「24 小时内没回的按未接入处理，后续派活绕过并记录在案」。之后每收到一条确认，都要：**回话 + 登记台账**。
这类群里有 10 个 bot，一对一确认会来回几十条——靠脑子记谁确认过必然漏。

## 一、先定位群（chat_id）

会话上下文只给群显示名，**不要靠记忆中的 `oc_…`**（本项目同时存在主群、Agent 协作群、多个话题 thread）：

```bash
lark-cli im +chat-search --query "早日让鑫杰实现" --as bot     # → data.chats[].chat_id
lark-cli im +chat-list --page-size 50 --as bot                 # 列全部群（+chat-list，单数）
```

`+chats-list` 不存在，跑出来空 stdout + 退出码 0——不报错，容易误判成「bot 不在群里」。

## 二、拉最近消息，看清「谁确认到哪了」

```bash
lark-cli im +chat-messages-list --chat-id oc_xxx --as bot --page-size 30 --order desc > /tmp/chat.raw 2>&1
python3 -c "
import json
raw=open('/tmp/chat.raw').read(); d=json.loads(raw[raw.find('{'):])
msgs=d['data'].get('messages') or d['data'].get('items') or []
for m in msgs:
    body=(m.get('body') or {}).get('content') or m.get('content','')
    try: body=json.loads(body).get('text',body)
    except Exception: pass
    print(m.get('create_time'),'|',(m.get('sender') or {}).get('name'),'|',str(body).replace(chr(10),' / ')[:120])
"
```

要点：
- **解析前先切到第一个 `{`**（stdout 可能带 warning 行）；
- `data.messages` / `data.items` 两个字段名**都见得到，做兼容取值**，别写死一个；
- 一眼能看出「小管家已回、TC 刚回、其余 8 个没动静」，这条时间线就是台账的事实来源。

## 三、回话：短、@ 到人、带幂等键

确认类回话不要长篇复述规则（对方已经读过），四件事就够：**收到 / 复述 2–3 条硬要求定格 / 说明下一步怎么派活 / 说明什么情况会退回**。

```bash
lark-cli im +messages-send --chat-id oc_xxx --as bot \
  --idempotency-key "a2a-confirm-tc-20261029" \
  --text '<at user_id="ou_…">TC 交付数字员工</at> 收到，记入接入名单。三条硬要求复述一遍对齐：①… ②… ③…'
```

- `--idempotency-key` 必带：同一条 bot 确认可能并发投到两个 session，键相同则不会重复发（键取名规则 `<事项>-<对象>-<日期>`，见 `duplicate-delivery-guard`）。
- 引号**必须半角** `user_id="ou_…"`；全角 `“ ”` 会让 @ 退化成纯文本、对方收不到。

## 四、验证 @ 真的生效（别只看 ok:true）

```bash
lark-cli im +messages-mget --message-ids om_xxx --as bot > /tmp/mg.json 2>&1
python3 -c "
import json; d=json.load(open('/tmp/mg.json')); m=d['data']['messages'][0]
print('mentions:', [(x.get('name'), x.get('id')) for x in m.get('mentions',[])])"
```

**bot 的 `mentions[].id` 是 app_id（`cli_…`），不是 `ou_…`**——看到不是 `ou_` 不代表 @ 失败；`mentions` 为空才代表退化成纯文本。

## 五、台账落地（Obsidian，同步镜像库）

写进既有的路由表文档末尾，独立一节，表格三列就够，便于日后点名：

```markdown
## A2A-v1 接入确认名单（2026-10-29 起）

规则原文发布于本群主聊天流（消息 `om_xxx`，10-28 15:32 发出，已 @ 全部 10 个 bot）。
确认口径：回一行「✅ 已读 A2A-v1」，24h 内未回按未接入处理，后续派活绕过并记录在案。

| Bot | 确认时间 | 状态 |
|---|---|---|
| 大湾区样板间专项小管家 | 2026-10-29 15:31 | ✅ 已确认，四条要点复述无误 |
| TC 交付数字员工 | 2026-10-29 15:32 | ✅ 已确认，三条硬要求复述无误 |
| 其余 8 个（列全名） | — | ⏳ 待回，截止 2026-10-30 15:32 |

回执期次口径：统一 ISO 周号 `YYYY-Www`，不用日期（与定时任务回执口径一致）。
```

写完立即同步 Obsidian 双库（见 memory 里的双库约定）：

```bash
rsync -a --exclude '.git' --exclude '.obsidian' \
  "$HOME/Documents/Obsidian Vault/AI场景/" "$HOME/Documents/My Great Vault/AI场景/"
```

## 六、收尾口径

- 台账里的「待回」要带**明确截止时间**（广播时刻 + 24h），否则这条台账永远关不掉。
- 回复里报「几 / 10 已确认」，比只说「收到」有用——发起方一眼知道进度。
- 主动提一句「到期我可以点一次未回的」，把后续动作留给用户决定，不擅自挂 cron。
