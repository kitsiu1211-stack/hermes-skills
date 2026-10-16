---
name: feishu-internal-search
description: Use when 找飞书内部材料或确认客户名。docs +search 检索与实体确认。
category: feishu
version: 1.0.0
author: hermes-curator
license: internal
metadata:
  hermes:
    tags: [feishu, lark-cli, search, docs, calendar, meeting-followup]
    related_skills: [meeting-followup-material, feishu-meeting-listen, meeting-audit]
---

# 飞书内部检索与实体确认（Internal Search）

用 lark-cli 从飞书内部（文档库 / 知识库 / 日历）把「材料」和「实体身份」查出来——不问用户、不猜。
**铁律：检索和回忆是 Agent 的工作，不是用户的。**

## When to Use / 触发条件

- 会后要材料（客户案例 / 方案 / 销售一指禅 / 版本对比）
- 对话或会议里冒出一个系统、产品、ISV 名字，要搞清它是什么、有没有现成材料
- 要写客户名，但会议标题没写
- 怀疑同一时段有重复预约

## 1. 文档检索：`docs +search`

```bash
lark-cli docs +search --query "<产品名> <概念>" --as user --page-size 10 --format json > /tmp/s.json
```

**关键词铁律：产品名 + 概念组合，不要单搜泛词。**

| | 结果 |
|---|---|
| ✅ `Windchill PLM` / `参数领航 Windchill` | 精准命中对客方案、销售一指禅、协作客户一览表 |
| ❌ 单搜 `PLM` | 返回 1000+ 条噪音，等于没搜 |

**字段路径（踩过的坑）**
- 结果数组是 `data.results` — **不是** `data.items`
- 标题 `results[].title_highlighted`、摘要 `results[].summary_highlighted` — **不是**顶层 `title`
- 链接 `results[].result_meta.url`；`entity_type` = `WIKI` / `DOC`
- 标题和摘要里的 `</h>` 高亮标签要用正则去掉再展示

提取模板（写成文件再跑，避免 shell 引号地狱）：

```bash
python3.11 -c "
import json,re
d=json.load(open('/tmp/s.json'))
for r in d['data']['results']:
    m=r.get('result_meta',{})
    print('-', re.sub(r'</?h>','',r.get('title_highlighted','')), '|', m.get('url'))
    print('   ', re.sub(r'</?h>','',r.get('summary_highlighted','') or '')[:120])
"
```

**内部一定有的东西**（先试这些关键词）：销售一指禅、对客解决方案（按行业分版本）、ISV 专项宣贯、生态伙伴清单、协作客户一览表、历史同题的智能纪要。

**交付方式**：命中后按「无链接不交付 + 只交付用户要的 + 精选 1-3 条 + 每条附一句匹配理由」交付。
如果材料是在出纪要卡片的同一步拿到的，**直接嵌进纪要卡片的最后一段**，不另发一条消息（用户不用切两次消息）。

## 2. 实体确认：`calendar +search-event` 反查客户名

```bash
lark-cli calendar +search-event --as user --query "<会议关键词>" --start <今天> --end <+7天>
```

- 会议标题没写客户名时，**同期日程标题往往直接带客户名**。实测：「飞书 & PLM对接」不带客户 → 日历同一时段另有「感臻｜PLM沟通」→ 客户即感臻。零猜测，可以放心写进纪要。
- ❌ 反面做法：从字幕内容猜客户——字幕里提到的公司常是案例引用，不是会议对象。
- **顺带查重复预约**：同一时段出现两个日程（官方预约 + 客户发起）很常见，发现后主动提醒用户清一个。

## 3. 名字听不懂 / 对不上时：先怀疑转录

会议字幕会把专有名词转错。对不上的名字先按「转录错字 → 口语简称 → 真名」三步试。
实测一组（PLM 场景）见 `references/plm-windchill-material-bank.md`：`Winch` / `温琼` / `PC公司` / `PM系统` / `POM` → **PTC Windchill**；`参数李航` → **参数领航**（ISV）。

## 关联技能

- 会后材料的筛选规则与卡片交付格式：`meeting-followup-material`
- 会议旁听与纪要产出：`feishu-meeting-listen` / `meeting-audit`

## 关键约束

- 不问用户「这个客户是谁」「有没有材料」——那是你的活。找不到就诚实说「翻遍了没有」，不要反问。
- 检索用 `--as user`（用户身份授权）；只有 IM 发送才用 `--as bot`。
- 泛词搜不到时**不要**下结论「内部没有」，换「产品名 + 概念」再搜一次。
