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

## Generator / Evaluator 双角色流程

```
┌─ Generator ─────────────────────────────┐
│ 1. 枚举名下客户 → 逐个拉数据            │
│ 2. 按信号清单判定 → 输出候选机会列表     │
│ 3. 每条结论必须带数据引用（字段名+值）   │
│ 4. 推荐动作（来自主题34打法库）          │
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

## 输出卡片格式

一张总览卡片，结构：
- Header：📡 AI 赢单商机雷达 | 第 X 周（日期范围）
- 顶部统计：扫描客户数 / 强信号 / 中信号 / 弱信号
- 每个信号客户一块：客户名（脱敏可选）+ 当前档位 → 建议升级档位 + 信号依据（具体数值）+ 推荐动作
- 底部 note：数据来源 + 抓取时间 + Evaluator 校验结论

**脱敏选项**：内部用保留客户名；对外分享用「某+行业+企业」。

## 定时任务（cron）

每周一早上 9:00 自动跑：
- cron schedule: `0 9 * * 1`
- 加载本 skill → 执行全流程 → 输出卡片到 Home
- 手动触发：用户说「跑一下商机雷达」→ 手动执行

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
