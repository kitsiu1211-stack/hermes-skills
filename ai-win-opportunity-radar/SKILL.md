---
name: ai-win-opportunity-radar
description: 每周扫描名下客户 AI 使用数据，识别升级商机机会并出飞书卡片。
category: feishu
---

# AI 赢单商机雷达（AI Win Opportunity Radar）

基于主题34「AI赢单策略」（五人赢单蒸馏沉淀：AI 第一负责人 / 场景用量 / 组织推动力三大洞察）的升级信号清单 + C360 CLI 真实租户数据，每周自动识别用户名下客户的 AI 商机机会，无幻觉约束输出。

## 🚨 核心纪律（无幻觉铁律）

1. **每条结论必须引用具体字段值**（如：消耗率 79.98%、预计到期 567%）——禁止凭空判断
2. **Generator → Evaluator 双角色**：Generator 生成机会判断，Evaluator 独立逐条校验
3. **Evaluator 校验三件事**：数据存在性（字段确实返回了值）/ 计算正确性（阈值判定算对了）/ 信号强度（是强/中/弱）
4. **无数据支撑的结论直接打回**，不进卡片
5. **卡片标注数据来源 + 抓取时间**（如：数据源 C360 tenant metrics，2026-08-26 09:00 抓取）
6. **只读不写**：全程只调用只读命令，不修改任何 C360 数据

## 数据链路（已实测验证）

```bash
# 1. 枚举自己名下的客户（owner_id 过滤）
lark-c360 account list --field id --field name --filter-json @filter.json --limit 50 --json
# filter.json: {"owner_id": {"operator": "eq", "value": "<我的user_id>"}}

# 2. 对每个客户拉 AI 使用数据（173 个 AI 字段，取关键字段）
lark-c360 tenant metrics get --tenant-id <tenant_id> --field ai_credits_usage_rate --field ai_credits_usage_rate_predict --field ai_credits_quota_remaining_days --field ai_credits_quota_actual_remaining_days --field ai_credits_usage_mom --field ai_credits_asset_time_rate --field tenant_ai_credits_arr --field ai_arpu --field ai_dau_avg_7workday --field ai_dau_avg_7workday_wow --field knowledge_ai_dau --field nexus_bot_dau --field base_ai_dau --field vc_ai_dau --json

# 3. 可选：C360 自带信号（机会/风险/到期）
lark-c360 account +usage --id <account_id> --json
```

**关键字段速查（tenant_metrics 实体）：**

| 字段 | 含义 | 信号用途 |
|------|------|---------|
| ai_credits_usage_rate | AI 通用额度当前消耗进度 | 消耗率 ≥2倍 → 升级信号 |
| ai_credits_usage_rate_predict | 预计到期消耗进度 | >100% → 会提前用完 → 强信号 |
| ai_credits_quota_remaining_days | 预计剩余可用天数 | <30 天 → 告急 |
| ai_credits_quota_actual_remaining_days | 实际到期剩余天数 | 与预计对比 |
| ai_credits_usage_mom | 用量月环比 | 高增长 → 场景在长 |
| ai_credits_asset_time_rate | 当前时间进度 | 消耗率 vs 时间进度 对比 |
| tenant_ai_credits_arr | AI 通用额度 ARR | 判断当前档位（9900/9.9万/29.7万/99万） |
| ai_arpu | 人均 AI 消耗金额 | 使用深度 |
| ai_dau_avg_7workday | AI DAU 近7日均值 | 激活规模 |
| ai_dau_avg_7workday_wow | AI DAU 环比 | 增长趋势 |
| knowledge_ai_dau / nexus_bot_dau / base_ai_dau / vc_ai_dau | 各场景 DAU | 场景分布（豆包工作伙伴/知识问答/多维表格/智能纪要） |

## 升级信号清单（判定规则，来自主题34）

### 档位识别（先判断客户当前在哪个档位）
- `tenant_ai_credits_arr` ≈ 9900×N → 入门档（9900 包）
- ≈ 9.9 万×N → 9.9 万档
- ≈ 29.7 万×N → 29.7 万档
- ≈ 99 万 → 旗舰档

### 信号判定（每档对应升级方向）

**🟢 入门档 → 9.9 万（新签升级）：**
- 消耗率 ≥ 2 倍时间进度（`ai_credits_usage_rate` / `ai_credits_asset_time_rate` ≥ 2）
- 或 `ai_credits_usage_rate_predict` > 150%
- 或 预计剩余天数 < 时间进度剩余天数（提前用完）

**🟡 9.9 万 → 29.7 万（增购）：**
- `ai_credits_usage_rate_predict` > 200%
- 或 消耗率 > 80% 且 `ai_credits_usage_mom` > 50%（用量在加速）
- 或 预计剩余 < 30 天且场景 DAU 在涨

**🔴 29.7 万 → 99 万（增购）：**
- `ai_credits_usage_rate_predict` > 300%（按当前速度一年要 3 个包）
- 或 激活人数到千级（ai_dau_avg_7workday > 800）
- 或 多场景 DAU 全面增长 + 消耗率 > 70%

**信号强度分级：**
- 🔴 强：predict > 300% 或 剩余 < 15 天 → 本周必须动作
- 🟡 中：predict 150-300% 或 剩余 15-30 天 → 本周安排接触
- 🟢 弱：predict 100-150% 或 DAU 环比增长 → 观察跟进

## V2 跟进记录增强（2026-08-27 实测）

V1 的通病：所有信号客户的动作是同一句模板话术（"约 AI 第一负责人，带用量数据谈升级"）——既没承接真实对话，也没发现"数据在报警、人在沉默"的空窗。V2 增加跟进扫描 + Agent 动作增强：

### 跟进扫描（脚本 fetch_followups.py）

```bash
cd ~/.hermes/skills/feishu/ai-win-opportunity-radar/scripts
python3 fetch_followups.py [--days 14]   # 读 /tmp/radar_result.json → 输出 /tmp/radar_followups.json
```

- 对每个信号客户拉 `follow_up +recent --account-id <id> --field follow_date --field content --limit 30`
- 过滤近 N 天（默认 14 天）+ AI 关键词，每个客户最多留 3 条 AI 命中（截断 500 字符）
- 输出结构：`{客户名: {ai_hits: [{date, content}], any_followup: bool, total_14d: N}}`
- `any_followup=false` 表示近两周连普通跟进都没有 → 这是重要洞察，不是缺失数据

**AI 关键词清单**：`ai / AI / 豆包 / 智能 / 知识库 / 机器人 / 额度 / 消耗 / 用量 / 模型 / 纪要 / 多维 / 助手 / 工作伙伴 / 大模型 / 激活 / 训练 / 场景 / 升级 / 采购 / 续费 / 到期 / 演示 / 培训`

### 动作增强规则（Agent 写 /tmp/radar_actions.json）

逐户手写动作，禁止全员套模板。规则：

1. **有 AI 跟进**：动作必须承接跟进内容——交付已承诺材料 / 关闭卡住的流程 / 换正确场景重聊（上次话题错位就换）/ 给具体演示 agenda（上次邀约太泛没答复就带清单）。例：客户已问"版本区别"= 升级话题已由客户开启；客户在等费用流程 = 先关流程再谈。
2. **无跟进**：动作 = 首次 AI 触达，用消耗数据敲门（"按当前速度 X 天用完"），按指标分化：
   - mom 高 → 问什么场景在涨（如零壹 mom+138.5% → 先搞清什么在爆）
   - mom 负 → 先诊断用量下滑是场景萎缩还是封顶（如唯迹 -26.3%）
   - DAU 高 → 摸清谁在用、哪些场景（如凯迪仕 DAU 467）
   - 剩余天数少（<15）→ 紧急对话，先确认续费/升级意向
   - 剩余天数多（>100）→ 不逼单，轻触达为下季度铺路
3. **Evaluator 打回的客户**：标记 ⚠️ 到期/异常节点，动作 = 确认续费/到期状态，**不用升级话术**。实测案例：机智连接 predict=100% 被标强 → 打回，实为额度耗尽/到期节点。
4. **排序**：卡片按剩余天数升序（紧急优先），到期节点最前。
5. **诚实标注**：卡片 note 必须如实写 Evaluator 结果（"X 条通过 + Y 条打回"），有打回时不许写"全部通过"。

动作文件格式：`/tmp/radar_actions.json` = `{客户名: "动作文本"}`。send_radar_card.py 优先用 Agent 动作，缺省才用模板兜底（兜底动作会标注"建议改写"）。

## V3 半年基线扫描（2026-08-27 用户定调）

V2 只扫近两周 → 只有「切片」没有「全貌」：历史购买记录、购买原因、客户 AI 定位全缺失，动作仍会跑偏。
用户规则：**第一次用 c360cli 扫描客户时，必须拉近 180 天全量跟进做基线**，建立客户 AI 认知后再谈商机。每周 cron 每次跑基线（窗口内自然包含增量）。

### 基线能回答的问题
- 客户买过什么（AI 包/版本/席位变化）、为什么买（购买原因）
- 客户 AI 定位（自研/全员工具/仅 IM）、用谁家的模型（Gemini/Claude Code/豆包）
- 哪些客户「不该推进」→ 直接排除出商机清单（此乃基线最大价值）

### 实测案例：机智连接（2026-08-27）
- 近两周无跟进 → V2 判「无跟进」，升级信号仍挂着
- 半年基线一条记录直接定性（2026-07-15）：**账号将降至 100-200 个、只做中国区域 IM 使用、版本降为基础版；全员配 Gemini + Claude Code，招聘主要在海外**
- 结论：业务出海、飞书仅作 IM 工具 → **不是商机，从雷达排除**，卡片标注原因。用户原话「以此内推」= 每个客户都过一遍基线再定推不推

### 脚本用法（基线建档一次，之后每周只跑增量）
```bash
cd ~/.hermes/skills/feishu/ai-win-opportunity-radar/scripts
python3 fetch_followups.py --baseline        # 首次建档：180天全量 → ~/.hermes/radar_baseline.json（持久化）
python3 fetch_followups.py                   # 每周增量：近14天 → /tmp/radar_followups.json；自动复用基线+补新客户
```
- 基线档案持久化在 `~/.hermes/radar_baseline.json`（不在 /tmp，跨周不丢）
- 增量模式自动检查档案：已有客户只拉近 14 天；**新客户进雷达自动补拉 180 天基线并入档**
- 建档后每周不再重跑基线——用户定调：每周一次，只看新的一周数据

### 基线判定规则（Agent 逐户过一遍，写 actions 前必做）
1. **排除信号命中**（出海/海外/仅IM/全员用竞品AI/降版本）→ 从商机清单移除，卡片标注「排除：原因」
2. **档位与基线矛盾**（实测雷鸟：radar 判入门档但基线显示 6 月已购 9.9 万 AI 企业版）→ 动作按基线事实写（已购客户谈增购/续费），卡片标注需人工核实档位
3. **购买历史**（已购/待购/明确说不续约）→ 动作承接历史对话（如疆海 4 月底曾「明确不再续约」→ 先恢复信任再谈增量），禁止模板话术
4. **AI 定位与用量矛盾**（实测零壹：用量 mom+138.5% 但 sponsor 明说「暂无落地 AI 场景」）→ 先摸清是谁在消耗，不直接推升级
5. 基线决定「为什么聊」（客户画像），增量决定「这周聊什么」（最新状态）

## Generator / Evaluator 双角色流程

```
┌─ Generator ─────────────────────────────┐
│ 1. 枚举名下客户 → 逐个拉数据            │
│ 2. 按信号清单判定 → 输出候选机会列表     │
│ 3. 每条结论必须带数据引用（字段名+值）   │
└──────────────┬───────────────────────────┘
               ▼
┌─ 跟进扫描（V2）─────────────────────────┐
│ 4. 对每个信号客户拉近14天 follow_up      │
│ 5. 过滤 AI 关键词 → 输出跟进摘要         │
│ 6. Agent 按动作增强规则逐户写动作        │
└──────────────┬───────────────────────────┘
               ▼
┌─ Evaluator ─────────────────────────────┐
│ 1. 数据存在性：字段确实返回了值？         │
│ 2. 计算正确性：阈值判定算对了？           │
│ 3. 信号强度：标注是否合理？               │
│ 4. 无数据支撑的结论 → 打回删除            │
└──────────────┬───────────────────────────┘
               ▼
        飞书总览卡片（数据来源+时间戳）
```

## 输出卡片格式（V2）

一张总览卡片，结构：
- Header：📡 AI 赢单商机雷达 V2 | MM-DD 扫描
- 顶部统计：强信号（本周必须动作）/ 中信号（本周安排接触）/ 到期节点（非升级信号）
- 💡 跟进洞察行（有跟进数据时）：X 家有近两周 AI 对话，Y 家无任何跟进
- 每个信号客户一块：客户名 + 信号强度（打回客户标 ⚠️ 到期/异常）+ 当前档位 → 建议升级档位 + 信号依据（具体数值）+ 📋 近两周跟进摘要 + ✅ 本周动作（Agent 基于跟进手写）
- ⛔ 排除客户块（V3.1，有排除时显示）：客户名 + 排除原因（来自基线判定，如出海/仅IM/降版本/全员竞品AI）
- 打回客户不显示「建议升级」箭头，改写「Evaluator 打回，不做升级建议」——避免卡片自相矛盾
- 底部 note：数据来源（tenant_metrics + follow_up）+ 排除客户数 + 抓取时间 + Evaluator 校验（如实写通过/打回数）+ 阈值版本

**脱敏选项**：内部用保留客户名；对外分享用「某+行业+企业」。

## 定时任务（cron）——每双周周一早上 9:00 自动跑（job: 755f8ece681d）

- cron schedule: `0 9 * * 1`（每周一触发，prompt 内判断 ISO 周号，**偶数周执行、奇数周静默跳过**）
- 发送节奏（2026-08-27 用户定调）：14 天增量窗口 → 双周发一次。实测：8/31=周36发 → 9/7=周37跳过 → 9/14=周38发
- 加载本 skill → 执行全流程（radar_full.py → fetch_followups.py 增量 → Agent 写 actions → send_radar_card.py）→ 输出卡片到 Home
- 🚨 **发送前强制步骤**：必须先跑 c360cli 跟进检索（近14天增量），结合基线档案+跟进情况给策略——没跑跟进检索不允许写策略、不允许发卡片（已写死进 cron prompt）
- 手动触发：用户说「跑一下商机雷达」→ 手动执行，同样先跑跟进检索（不受双周限制）

全流程命令（四步 + Agent 写作两份 JSON）：

```bash
cd ~/.hermes/skills/feishu/ai-win-opportunity-radar/scripts
python3 radar_full.py          # 1. 信号扫描 → /tmp/radar_result.json
python3 fetch_followups.py     # 2. 每周增量扫描 → /tmp/radar_followups.json（自动复用基线档案+补新客户，不重跑180天）
# 3. Evaluator 独立复核（数据存在性）：python3 /tmp/verify_metrics.py 重新拉 C360 关键字段与 radar_result 逐项比对
# 4. Agent 读雷达结果 + 基线档案(~/.hermes/radar_baseline.json) + 增量摘要，按「基线判定规则」先排除/纠偏，再按「动作增强规则」逐户写：
#      /tmp/radar_actions.json      {客户名: 本周动作文本}
#      /tmp/radar_exclusions.json   {客户名: 排除原因}（无排除时可不写）
python3 send_radar_card.py     # 5. 组装V3.1卡片发 Home
```
首次建档（一次性）：`python3 fetch_followups.py --baseline` → 生成 ~/.hermes/radar_baseline.json

## 注意事项

1. **枚举「现在名下」客户的两步法（2026-08-26 修正）**：
   - ❌ 错误做法：只用 opportunity 的 owner_id 枚举——商机 owner 是历史归属，客户已转走（如吉比特→陈柳均Lilo、飞速→张东琪）仍会出现在商机里，导致误报
   - ✅ 正确做法：opportunity 拉候选（owner_id==我 且 含 AI 产品）→ 逐个 `account get --field owner_id` 验证**当前** owner 仍是我 → 才算名下客户
   - 实测：商机候选 301 个 → 验证后真正名下 38 个，其中含 AI 产品 35 个
2. **account_id 的 value 才是真实 ID**：opportunity 的 `account_id` 字段 `display_value` 是客户名（reference 字段显示名称），真实 ID 在 `.value`（带引号，需 strip）。用 display_value 当 ID 会导致 account get 查询失败
3. **account get 响应结构**：`data.id/name/owner_id` 直接挂在 `data` 下（不是 `data.entity`）
4. **先小范围验证**：首跑只扫 3-5 个客户核对数据准确性，再全量
5. **tenant_id vs account_id**：`tenant metrics` 用 tenant_id（F 开头），`account +usage` 用 account_id（001 开头），别混
6. **空数据客户**：`tenant metrics` 可能返回空（无 AI 额度客户）→ 跳过，不计入扫描数
7. **C360 CLI 版本**：当前 1.2.10；filter-json DSL 在 CLI 对 account/opportunity 均不可用（试遍 type: leaf/term/item/filter/condition 全报 unsupported）——不要在 filter 语法上浪费时间
8. **Evaluator 是校验器不是生成器**：只删不改，发现异常打回 Generator 重跑该客户
9. **阈值可调**：信号清单阈值写在脚本常量区，方便根据实际命中率调整
10. **account_id 禁止手动转写**（2026-08-27 实测翻车）：手敲 `0010o00002tr5GYAY` 漏了一个字符（正确 `0010o00002tr5GYAAY`），导致凯迪仕 3 条 AI 跟进被漏查、误判"无跟进"。脚本（fetch_followups.py）直接读 radar_result.json 的 `account_id` 字段，天然免疫——任何手动转写客户 ID 的环节都是 bug 源头
