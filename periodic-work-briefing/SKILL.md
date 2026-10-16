---
name: periodic-work-briefing
description: 周期性把工作汇总成卡片，或做成 Bot 入会语音汇报会。触发：周报/日报/汇报一下最近工作/开周报会。
category: productivity
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Weekly-Review, Briefing, Meeting, Voice, Feishu]
    related_skills: [feishu-meeting-listen, feishu-card-send, daily-session-summary, weekly-review-planning]
---

# 周期性工作汇报（卡片 · 语音汇报会）

把用户一段时间的工作（会议、日程、待办、对话）汇总成**可执行**的汇报，两种介质：
**卡片**（可存档/转发）+ **语音播报稿**（Bot 入会念给他听，然后实时问答）。

## When to Use（何时用）

- 「周报」「日报」「汇报一下我最近的工作」「总结这周/这周做了什么」
- 「开周报会」「语音汇报」「拉个会你给我讲」
- 定时任务产出晨报/周报/阶段汇报

## 核心设计原则（用户偏好，别违背）

1. **先跑起来再优化**：先做卡片版，跑顺 2~3 次再上全自动（cron 自动建会 + 主动播报）
2. **零 token 收素材，LLM 只做写作**：事实收集交给确定性脚本，Agent 只负责写卡片和口语稿
3. **一份内容两种介质**：同一份事实，卡片按结构化排版，播报稿按口语化改写（不要直接把卡片念出来）
4. **待办必须可执行**：不写「跟进 XX」式空泛项；写清人 / 时间点 / 材料，并注明是否已建日程
5. **诚实标注缺口**：哪块素材取不到就明说（「标题未取到」），不编造
6. **有数据先验证再落笔**：结论要能追溯到素材包里的具体行

## 数据源与采集脚本（已在生产使用）

脚本：`/Users/bytedance/.hermes/scripts/weekly_brief_build.py`（零 token，纯确定性）

```bash
/Users/bytedance/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/scripts/weekly_brief_build.py --days 7 --out /tmp/brief_week.md
```

**必须用 venv python**（`/usr/bin/python3` 是 3.9.6，跑含中文的脚本会报编码错）。
支持 `--days N` / `--start --end` / `--out`。

聚合四类事实，输出五段：

| 段 | 来源 | 坑 |
|---|---|---|
| 一、旁听会议 | `~/meeting_logs/*.jsonl`（场次/时长/字幕句数/主要发言人） | **标题不在日志里**，用日历反查 |
| 二、本周日程 | `lark-cli calendar +agenda` | `data` 是 **list**，时间是 `start_time.datetime` |
| 三、已创建跟进日程 | 查 `跟进：` 前缀的日程 | 建日程前先查重 |
| 四、Hermes 工作会话 | `state.db` sessions（排除 cron/subagent） | 用只读 URI，别用系统 sqlite3 |
| 五、规模统计 | 上列合计 | 用来对账卡片里的数字 |

**会议标题反查法**：同日 + 开始时间最接近（≤30 分钟）匹配当日 `calendar +agenda` 的 summary，命中就标注「（据日历匹配）」；会议太短/无日程的留「标题未取到」，不要猜。

## 卡片版流程

1. 跑脚本 → 读素材包
2. **按用户身份筛**（见下）——不是全量摘要
3. 飞书卡片（遵循 `feishu-card-send`：`<font>` 标签、≤10 元素/张、末尾 note 标 `N/M`）
4. 会后/汇报后建跟进日程（`calendar +create`，先 `+search-event` 查重；周末顺延到工作日）
5. **卡片发出后不要再把同样内容用文本重复一遍**——用户会同时收到两份

## 语音汇报会流程

Bot 入会 → 用豆包语音念播报稿 → 用户追问、实时问答。
完整运行手册（会前硬前提、启动命令、静默门控的唯一例外、降级路径、分工表）：
`references/weekly-voice-briefing.md`

## 按身份筛选（用户明确偏好）

给完长内容后用户常追加「按我的身份筛」——**挑出对他真正可用的，并给理由**，不要全量摘要：

- **客户侧**：他名下客户是否踩在这次活动的画像/高优行业上
- **可执行**：哪个人、哪个时间点、哪份材料、哪个链接
- **判断**：给一句「一句话判断」，把当天/当周不同会议串成一条链（例：A 会的卡点 = B 会的同一问题）
- **命名归位**：人名/企业名有歧义时用日历等一手来源确认，别从字幕猜客户

## Pitfalls

- **`lark-cli calendar +search-event` 有索引延迟**：`+create`/`+update` 后立刻 search 可能仍返回旧值 → **一律用 `+agenda` 验证**落地结果
- **`calendar +agenda` 的 `data` 是 list**（不是 dict），时间字段是 `start_time.datetime`，不是 `start.date_time`
- **`lark-cli wiki +node-get` 的标题在 `data.title`**（不是 `data.node.title`）
- state.db 查询用只读 URI（`file:<path>?mode=ro`）；写/读都优先走 venv 的 python/sqlite（系统 sqlite 有 WAL 版本 bug）
- 别把「机器休眠 N 天」写成「安静的一周」——先查 `~/.hermes/cron/executions.db` 有没有整天级断层
- 短会（几分钟）也要收，但纪要要短；**不要为了完整硬凑长度**
- 会议室设备入会的会，字幕 speaker 可能是**设备名**（如「XX广场-12F-曼谷(10)」）→ 人名归属按内容推断并**明确标注可能不准**
- 素材包只是素材：不要把它整段贴给用户，要写成他看得懂的结论和动作

## 验证

- [ ] 卡片里写的场次/数量与素材包对账一致
- [ ] 建日程前查过重；周末日期已顺延
- [ ] 卡片里没有任何猜测的客户名或数字；不确定的已标注
- [ ] 语音版：会前硬前提逐条确认过（owner 开关 / 模板 / 耳机）
