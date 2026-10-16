# 竞品：Claude Tag（Anthropic 的团队智能体）

> 用途：客户/会议提到「Claude Tag」「@Claude」「团队智能体」时的对照弹药。2026-09-20 核实。
> ⚠️ 海外产品迭代快，引用前重跑文末「核实方法」确认状态未变。

## 一、官方事实（可引用）

| 项 | 内容 |
|---|---|
| 发布 | **2026-06-23**，官方公告标题 "Introducing Claude Tag"（slug `introducing-claude-tag`） |
| 官方定位原话 | "Claude Tag is a new way for teams to work with Claude. We're starting on Slack, **which Claude can join as a team member**." |
| 产品页 | `claude.com/product/tag`（导航里显示为 **@Claude**），页面标题 "Claude in Slack: Tag @Claude in any thread" |
| 可用性 | **Slack 内 beta**，面向 Claude Enterprise / Team 客户；官方页标注 "Coming soon to Microsoft Teams"（waitlist） |
| 内部实证 | Anthropic 自述：**65% 的产品团队代码**由内部版 Claude Tag 产出；"Tagging @Claude is now one of the main ways we get things done at Anthropic" |

## 二、四个机制（这才是「团队智能体 ≠ 个人助理」的分界）

1. **Multiplayer** — 一个频道里只有一个 Claude，服务所有人。别人交代的活，你可以接着往下聊；做事情是公开可见的
2. **越用越懂** — 跟着频道积累上下文，不必每次重新解释；授权后可学其他频道/数据源（官方明确：**不读 private channel**）
3. **会主动开口** — ambient 行为开启后主动提醒、追问没人管的线程、flag 待决事项，不需要被 @
4. **异步 + 自己排期** — 可跑几小时到几天；能给自己排定时任务（盯频道、周报、标急事）；也支持私聊 DM（用个人的 connectors）

接入方式：按频道授权 + 挂工具/数据/代码库；官方客户案例中出现的是 Datadog、Linear、GitHub。权限是 org 级管控设计。

## 三、与豆包工作伙伴的对位（客户最常问的那句）

**范式相同**：都是「加进群、继承群/频道权限、接外部系统、带组织上下文的同事」，都不是问答机器人、不是个人 AI 助理。
（2026-09-20 飞书内部培训「豆包工作伙伴相关内容分享」即用 Claude Tag 作类比：把 Tag 当真正的同事来理解。）

**可讲的差异（都成立、都不需要编）：**

| 维度 | Claude Tag | 豆包工作伙伴 |
|---|---|---|
| 载体 | 只有 Slack（IM 层）+ connectors | 飞书全家桶：群 + 文档 + 多维表格 + 审批 + 妙搭 |
| 数据流 | 频道授权 + 外接工具，数据出 IM | 数据不出飞书 |
| 交付/合规 | 海外，Enterprise/Team beta | 国内合规 + 本地交付体系 |

**话术铁律**：**先承认范式一致，再讲集成深度、数据边界与合规。** 硬说「我们不一样」会被当场拆穿——与本 skill「不比速度 / 不比数量」两条铁律同源：把对话从产品参数拉回业务闭环。

## 四、核实方法（海外闭源产品，无浏览器也能验证）

1. **先把被 ASR 听歪的名词还原**：会上听到「克劳 Tag」这类词，先 grep 会议 JSONL 拿到上下文原话（本次即靠字幕还原出「克劳在 6 月份发布的这个叫克劳 Tag 的产品」）
2. **curl 厂商 /news 列表页并 grep 产品名**：Next.js 站点的内嵌 JSON 里直接带发布日期和 slug，不需要 JS 渲染
   ```
   curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" https://www.anthropic.com/news -o news.html
   # grep 到："publishedOn":"2026-06-23T14:00:00.000Z","slug":{"current":"introducing-claude-tag"}
   ```
   同一段 JSON 还能定位导航里的产品页 href（本次由 `@Claude -> https://claude.com/product/tag` 确认产品页 slug 是 `tag`）
3. **curl 公告页/产品页 + strip HTML 标签**取官方原话，引用原话而不是转述
4. **输出必带两个官方链接**：`claude.com/product/tag` 与 `anthropic.com/news/introducing-claude-tag`（用户可自行复核）

来源：claude.com/product/tag ｜ anthropic.com/news/introducing-claude-tag
