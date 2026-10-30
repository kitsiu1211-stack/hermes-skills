# 飞书群里的 A2A 落地细节（2026-10-29 实跑记录）

协议本体见 SKILL.md。这里是飞书平台侧的具体动作和踩过的坑。

## 发布一条规则消息

```bash
lark-cli im +messages-send --as bot --chat-id <oc_xxx> --text '<at user_id="ou_a">甲</at> <at user_id="ou_b">乙</at>

【规则标题】
正文…'
```

- text 消息里 `<at user_id="ou_xxx">显示名</at>` 会被解析，API 返回的 `mentions[]` 是唯一可信的核对依据
- **必须半角引号**。全角 `“”`（中文输入法默认）不会被解析，消息里只剩纯文本，对方静默收不到，也不报错

## 坑一：@ 到已退群的 bot，名字渲染成「某bot0」「某bot1」

**症状** 帖子里出现 `@南区 ISV 业务助手0` `@南区 ISV 业务助手1` 这类奇怪名字，`mentions[]` 长度却是对的。

**原因** 静态路由表过期，里面的 bot 已经退群。飞书对无法解析的 mention 会用「第一个成功解析的名字 + 序号」占位。

**每次派活前先刷新成员表**

```bash
lark-cli im +chat-members-list --chat-id <oc_xxx> --as bot --member-types bot --page-all > /tmp/members.json
```

输出前面会插 `[page 1] fetching...` 和 `Found N bot(s)` 两行，**不能直接 json.load**，要先 `s[s.find('{'):]` 再解析。返回结构是 `data.bots[]`，每项 `name` / `member_id`(ou_) / `app_id`(cli_)。

**核对口径** 成员表是唯一事实源，比任何静态文件可信。用完顺手把静态表改掉。

## 坑二：编辑消息不算新事件

`lark-cli im +messages-edit --as bot --message-id om_xxx --text '...'`（bot only）能改已发消息，适合发错后原地修正。

但**被 @ 的 bot 已经按旧版触发过了，编辑不会重新触发**。所以改完之后要单独给新增/漏掉的那一方补一条短消息定向提醒，否则它永远收不到。

## 拉群消息看回执

```bash
lark-cli im +chat-messages-list --chat-id <oc_xxx> --as bot --order desc
```

- 返回结构是 `data.messages[]`（**不是** `items[]`，写错就永远得到 0 条）
- 每项字段 `create_time` / `content`（纯文本正文，已含 @ 名字）/ `sender.name` / `sender.id`（app_id）/ `mentions[]`
- `--start-time` 传错 epoch 会静默返回空。不确定就别传，直接取最近 N 条按 `create_time` 前缀过滤
- 输出前可能有 `warning: reactions_partial_failed` 行，同样要先截到第一个 `{`

统计谁回了：

```python
from collections import Counter
c = Counter(m['sender']['name'] for m in msgs
            if m['create_time'].startswith('2026-10-29 15:3'))
```

## 坑三：同一个 app 挂两个 Hermes 实例 → 身份串号

**症状** 一个 bot 名字下同时出现「你发的内容」和「你没发过的内容」，后者像内部状态行（`↪ Redirected current run`、`⚡ Interrupting current task`、`⏰ Scheduling list`）。

**判断** 同一个飞书 app 上跑了两个实例（本地 + 云端）。`+chat-members-list` 只列出一个 bot，但消息流里露出两条执行轨迹。

**后果** @ 一次唤醒两个实例，回执翻倍，确认往返被放大，外部哨兵的判定通道也会跟着失真。

**处理** 拆成不同 app，或者让云端实例只在自己被点名到专属话题时才响应。别靠 prompt 里写「你不要回」来压制，压不住。

## 观察到的真实数据（首轮）

- 10 个成员，2 分钟内回了 2 个（TC 交付数字员工、样板间小管家），8 个静默
- 同期群里多出 26 条消息，大半是互相「收到/已对齐/口径锁定」
- 结论：@ 全员 + 要求回一行确认，成本低、信号强，但必须同时上防往返规则，否则前十分钟全是噪声
