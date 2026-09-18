# 飞书交互卡片：批量发送模板（多卡片长内容）

> 用途：会议纪要、多主题汇总等长结构化内容 → 拆成多张 `interactive` 卡片，一段 Python 循环发完。
> 实测可用（2026-09-17，一次发 3 张会议纪要卡片 + 1 张话术卡片，全部 `ok: true`）。
> 相关：`feishu-card-send` skill 讲卡片语法细则；本文只给「批量构建 + 发送」的可复制模板。

## 为什么用 Python 而不是 bash

- bash 里 JSON 的换行/引号会被写成字面量 → 卡片渲染出原始转义符。
- 多张卡片要循环发、要复用 `md()`/`note()` 辅助函数，bash 拼不出来。
- 用 `#!/usr/bin/env python3.11`。

## 模板

```python
#!/usr/bin/env python3.11
import json, re, subprocess

CHAT = "oc_e2f79ec1614a1efe1ebcd7c679bb45a8"   # 默认 Home

def md(c):        # 正文照常写 **粗体**，自动转飞书认的 <font>
    c = re.sub(r"\*\*(.+?)\*\*", r"<font weight=bold>\1</font>", c)
    return {"tag": "markdown", "content": c}

def note(t):      # note 的 elements 只支持 plain_text，禁止 <a> 标签
    return {"tag": "note", "elements": [{"tag": "plain_text", "content": t}]}

HR = {"tag": "hr"}

def send(card):
    p = subprocess.run(["lark-cli", "im", "+messages-send", "--as", "bot",
        "--msg-type", "interactive", "--chat-id", CHAT,
        "--content", json.dumps(card, ensure_ascii=False)],
        capture_output=True, text=True)
    print(p.returncode, (p.stdout or p.stderr)[:200])

card1 = {
  "config": {"wide_screen_mode": True},
  "header": {"template": "blue", "title": {"tag": "plain_text", "content": "📹 标题｜一句话摘要"}},
  "elements": [
    # 顶部 4 列数字：background_style 必须写 default，否则是一排裸数字
    {"tag": "column_set", "flex_mode": "none", "background_style": "default", "columns": [
      {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
       "elements": [md("<font size=24 weight=bold>54min</font>\n<font size=14 color=grey>09:00-09:54</font>\n<font size=12 color=grey>会议时长</font>")]},
      # ...其余 3 列同构
    ]},
    HR,
    md("<font size=16 weight=bold>一句话结论</font>\n……"),
    HR,
    md("**小节**\n用普通 Markdown 写，md() 会转标签。注意**不要**写 `##`、表格、`---`。"),
    note("卡片 1/3 ｜ 来源 + 时间戳 ｜ AI 自动整理"),
  ]
}
# card2 / card3 同构

for c in (card1, card2, card3):
    send(c)
```

## 分片与排版规则（实测）

- 每张 `elements` ≤ 10 个（`hr` 也算一个）→ 超了就拆下一张。
- 分片逻辑：**第一张 = 概览（column_set 数字）+ 一句话结论 + 第一个主题**；后续 = 细节 / 洞察 / 行动项。
- 每张末尾 `note` 写「卡片 N/M」+ 来源 + 时间 → 用户能看出还有没有后续。
- header 配色按分片轮换：`blue`（概览）、`turquoise` / `orange` / `green` / `purple` / `indigo`（后续主题）。
- 颜色语义：好消息/达成 `blue`/`green`，风险/短板 `red`，需关注 `orange`，中性 `grey`。
- 发送后核对返回值：N 张卡片应有 N 个 `{"ok": true, "data": {"message_id": ...}}`。

## 已踩过的坑

- `tag: markdown` 的 content **不支持** `**粗体**`、`##`、表格、`---` → 用 `<font weight=bold>` / `<font size=16 weight=bold>` / `{"tag": "hr"}`。
- `<font color=red>` 属性不能加引号（`color='red'` 会失效甚至发送失败）。
- `note.elements` 只能 `plain_text`，塞 `<a>` 会报 230099 parse card json err。
- `column_set` 漏 `"background_style": "default"` → 数字列没有灰底卡片框，排版塌。
- 本地信息量大但**每张卡片有长度上限**：整段超长文本（超过几千字）要拆小节，别硬塞进一个 element。

## 相关 skill 的状态（2026-09-17）

`feishu-card-send` 是**用户自有 skill**（非 curator 管理），autonomous curator 无法写入。卡片语法细则以那份 skill 为准；本文件只承载批量发送模板。若希望把模板并入该 skill，由用户在前台执行 `hermes curator adopt feishu-card-send` 后再合并。
