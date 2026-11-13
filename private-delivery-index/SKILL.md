---
name: private-delivery-index
description: Use when 登记私聊交付索引或出周五周报小节。
---

# 私聊交付索引

鑫杰 2026-11-02 批准启用。周报固定小节，用来回答「这周你到底交付了什么、还在不在」。

## 四条铁律（定稿，不再讨论）

1. **只记已完成**。在途、半成品、口头结论都不进索引。
2. **只核存在性，不核内容**。回读得到就算过；对不对、好不好不看。
3. **事项用泛称**，不带客户名、不带人名（写「客户高层餐叙话题准备」，不写具体客户与姓名）。
4. **第四列给锚点**，不给主题细节。文档给 `docx:<token>`，消息给 `om_xxx`（或话题 `omt_xxx`）。

归属三档：私聊 / 群内 / 定时任务。**索引只登记私聊**——群内和定时任务的产出本来就在群里可见，重复登记是噪音。

## 「代发」栏（2026-11-06 定稿）

代鑫杰向第三方私聊交付（如代他给某客户 RM 传交接重点）**登记，但不进正文小节**——另起一栏「代发」，只记三列：谁代发 / 发给谁 / 锚点。这样既不污染「鑫杰私聊」口径，也不留追溯盲区。

- 归类边界：**鑫杰自己在群里发的链接=群内，不登记**；只有「我代他私聊发出去的」才算代发。四家案例文档这类群内交付不进任何栏。
- 登记：`add --owner 代发 --via 我 --to <泛称> --item <泛称> --anchor om_xxx`
- 输出：`section` 在正文小节之后自动追加「代发」块，锚点回读不到的标 `[回读不到]`。
- 措辞：回执一律写「**已送达（message_id 回读可见）**」，不写「确认可见」——按 message_id 回读只能证明消息存在，证明不了人看过。


## 存储与命令

- 数据：`~/.hermes/data/private-delivery-index.json`
- 脚本：`~/.hermes/scripts/private_delivery_index.py`
- Python：`/Users/bytedance/.hermes/hermes-agent/venv/bin/python`

```bash
PY=/Users/bytedance/.hermes/hermes-agent/venv/bin/python
S=~/.hermes/scripts/private_delivery_index.py

# 登记一条（交付完成、锚点已拿到之后才跑）
$PY $S add --item "事项泛称" --date 2026-10-28 --anchor docx:xxxx
$PY $S add --item "事项泛称" --date 2026-10-28 --anchor om_xxxxx

# 周报小节（默认 plain，飞书文本不渲染 markdown 表格）
$PY $S section --week 2026-W44
# 嵌进卡片/文档时才用 markdown 表格
$PY $S section --week 2026-W44 --format md

$PY $S verify  --week 2026-W44
$PY $S list
```

周号：`python3 -c "import datetime;c=datetime.date.today().isocalendar();print(f'{c[0]}-W{c[1]:02d}')"`

## 交付时怎么记

在私聊里发完实质产出后：立刻 `add` 一条；一次交付多条就逐条 `add`，不要合并成一行。锚点取发送后返回的 `message_id`，或文档 token。

## 坑

- 取文档是 `lark-cli docs +fetch --doc <token>`（没有 `--document-id`）；批量回读消息是 `im +messages-mget --message-ids`（没有 `im message get`）。
- `im +messages-mget` 的结果在 `data.messages[]`，不是 `data.items[]`。
- 回读不到时不要进重试链死循环；直接在小节里点名 `MISSING`，让人去查。
- 飞书文本消息不渲染 markdown：`section` 默认输出纯文本四段式（序号 · 事项 · 日期 · 锚点），别手改回表格，否则群里露出竖线和反引号。要放进卡片或文档才加 `--format md`。
- 索引编号与登记顺序一致（脚本按日期稳定排序，同日不重排）。
- **批量回读会被一个坏锚点毒化**：`+messages-mget` 一次传多个 id，只要有一个不存在，整批可能返回空 → 全部误判 MISSING。脚本已对未命中项逐条复核（`verify_anchors`），手写命令时要留意这点。
- 别把索引当成果清单去补内容；它只是存在性台账。

## 周五 17:00

cron `周五周报·私聊交付索引`（`0 17 * * 5`）自动跑 `verify` + `section`，把那两段原样作为周报的「本周私聊交付索引」小节；有 MISSING 就在核验行点名。
