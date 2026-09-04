---
name: c360-cli
description: Use lark-c360 CLI to look up customer accounts, profiles, follow-up records, opportunities, and tenants. Search by keyword, get detailed profiles, and list recent follow-ups.
category: productivity
---

# C360 CLI

Query customer data from C360 (Lark CRM) via the `lark-c360` CLI. Installed at `~/.npm-global/bin/lark-c360` (v1.2.2). Logged in as 袁鑫杰, online environment.

## Trigger

When the user asks to check customer account info, follow-up records, opportunities, or tenant details — use this CLI instead of browser or raw API.

## Auth / Session Recovery

会话过期（报 `session expired for online, run lark-c360 auth login again`）时恢复：

```bash
# 1. 生成授权链接（5 分钟有效）
lark-c360 auth login --no-wait --json   # 输出 authorize_url，发给用户点击授权
# 2. 用户授权后执行
lark-c360 auth login --resume
# 3. 验证
lark-c360 auth status
```

授权成功后有效期约 30 天（`Expires At` 字段可查）。过期后 C360 全部命令报错，第一时间走恢复流程，不要反复重试原命令。

## Quick Start

```bash
# Check auth status
lark-c360 auth status --json

# Search for an account by keyword
lark-c360 search all --keyword "高驰" --limit 5 --json

# Get account profile (MUST specify --field or you only get id+name)
lark-c360 account +profile --id <entity_id> --field name --field nickname --field paid_status --field owner_id --field csm_owner --json

# Get recent follow-ups (MUST use --account-id, not --id)
lark-c360 follow_up +recent --account-id <entity_id> --limit 5 --field follow_date --field content --field contacts --field contact_titles --json
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `search all --keyword` | Global keyword search across entities |
| `account +profile --id` | Get detailed account info |
| `follow_up +recent --account-id` | Get recent follow-up records |
| `follow_up get --id` | Get a single follow-up detail |
| `opportunity list` / `get` | List or get opportunity details |
| `order list` / `get` | List or get order details |
| `entity meta --entity <name>` | Discover available fields for an entity |
| `api --method POST --path ...` | Raw API access for entities without top-level commands |

### Orders

```bash
lark-c360 order get --id <order_entity_id_F> \
  --field order_form_no --field signing_status \
  --field earliest_start_date --field latest_end_date \
  --field product_names --field total_amount \
  --field currency --field total_list_fees --json
```

Order entity IDs end with `_F` (e.g., `7649239111592577982_F`). Find them via `search all`. Key fields: `signing_status`, `earliest_start_date`, `latest_end_date`, `product_names`, `total_amount`, `total_list_fees`, `currency`.

### Order Items (line-level pricing)

⚠️ **`order_item` is NOT a top-level CLI command.** Use raw API:

```bash
lark-c360 api --method POST --path /anchor/api/entity/order_item/list \
  --data '{"filter":{"relation":"AND","children":[{"field":"account_id","operator":"EQ","value":"<entity_id>"}]},"fields":["standard_unit_price","actual_unit_price","quantity","start_date","end_date","product","purchase_type","total_price","arr","purchase_period","quantity_unit"],"limit":50,"offset":0}' --json
```

Key fields: `standard_unit_price`, `actual_unit_price`, `quantity`, `start_date`, `end_date`, `product`, `purchase_type` (新购/增购/续约), `total_price`, `arr`, `purchase_period`.

### Pro-Rated Add-On Pricing

To estimate add-on cost for N licenses:

1. Get the active order → `latest_end_date`
2. Compute: `remaining_days = latest_end_date - today`
3. Pro-rata factor: `remaining_days / 365`
4. Formula: `N × unit_price × pro_rata_factor × discount_rate`

**Limitation**: Per-SKU unit prices are not reliably extractable from C360 order items (product filter is unreliable). Cross-reference with deal desk or CPQ for exact pricing.

## KDM / Contacts Extraction

**This is the authoritative source for customer KDM data. Never guess or fabricate personnel info — always pull from C360.**

### Single command to extract KDM list

```bash
lark-c360 follow_up +recent --account-id <entity_id> --field contacts --field contact_titles --limit 30 --json
```

The `contacts` and `contact_titles` arrays are positionally aligned — `contacts[i]` has role `contact_titles[i]`.

### Python dedup + frequency analysis

```python
import json, subprocess

result = subprocess.run([
    'lark-c360', 'follow_up', '+recent',
    '--account-id', entity_id,
    '--field', 'contacts', '--field', 'contact_titles',
    '--limit', '30', '--json'
], capture_output=True, text=True)
data = json.loads(result.stdout)

seen = {}
for item in data['data']['list']:
    contacts = item['contacts']['display_value']  # JSON array string
    titles = item['contact_titles']['display_value']
    key = f"{contacts}"
    if key not in seen:
        seen[key] = titles  # positionally aligned

# Output unique contact→role pairs
for c_str, t_str in seen.items():
    names = json.loads(c_str)
    roles = json.loads(t_str)
    for name, role in zip(names, roles):
        print(f'{name} → {role}')
```

### What this gives you

| Field | Example | Meaning |
|-------|---------|---------|
| `contacts` | `["刘 怀宇（雪碧）","猪脚面"]` | Display names (花名 or 真名+花名) |
| `contact_titles` | `["首席运营官","技术主管/经理/总监"]` | Positionally matched roles |

**Pitfall**: These are internal 花名/花名, not legal names. They are what your team actually uses to refer to contacts. C360 does not expose a separate "real name" field per contact.

### 历史跟进全貌（半年基线拉取）

需要客户半年跟进全貌（购买历史/购买原因/客户 AI 定位/是否值得推进）时，`follow_up +recent --limit 100` 一次即可拉回全部历史（实测 2026-08-27：limit 100 正常，单客户半年记录 4~23 条），**不要用多次小 limit 分页**。

```bash
lark-c360 follow_up +recent --account-id <id> --field follow_date --field content --limit 100 --json
```

- **窗口过滤在本地做**：`follow_date.display_value` 取前 10 位（YYYY-MM-DD）与截止日期字符串比较，C360 侧不传时间范围
- **建档一次 + 每周增量**节奏（用户定调 2026-08-27）：首次对客户拉 180 天全量建基线档案，之后每周只拉近 14 天增量；档案持久化到固定路径（如 `~/.hermes/radar_baseline.json`，别放 /tmp 会丢），增量时对档案缺失的新客户自动补拉 180 天
- 半年基线核心价值：识别「不该推进的客户」——业务出海/飞书仅作 IM/全员用竞品 AI/版本降级（实测机智连接：账号降 100-200 个、只做中国区 IM、全员 Gemini+Claude Code → 不是商机，移出推进清单）
- 排除信号关键词参考：出海/海外/IM/钉钉/企微/企业微信/国际/全球（命中即人工复核是否值得推进）

### When C360 returns nothing

If `follow_up +recent` returns zero records or contacts are empty, C360 has no KDM data for this account. Say "C360 无对接人记录" — do NOT guess.

## Critical Pitfalls

### 1. Flag names are counter-intuitive
- `account +profile` uses **`--id`** (NOT `--entity-id`)
- `follow_up +recent` uses **`--account-id`** (NOT `--id`, NOT `--entity-id`)
- `search all` uses **`--keyword`** (NOT positional arg)
- JSON 输出用 **`--json`**（NOT `--format json` — 实测 CLI 报 `flag provided but not defined: -format`）
- Always check `lark-c360 schema <command>` before running if unsure.

### 2. Commands return minimal data by default
Both `account +profile` and `follow_up +recent` only return `id` (and `name` for account) **unless you explicitly pass `--field` flags**. Without `--field`, you get almost nothing.

### 3. Field discovery
To find valid field names:
```bash
lark-c360 entity meta --entity account --json
lark-c360 entity meta --entity follow_up --json
```
Some fields may be marked "not readable" and will cause errors if included — remove them and retry.

### 4. Commonly used fields

**Account:**
`name`, `nickname`, `paid_status`, `owner_id`, `csm_owner`, `account_tier`, `business_primary_industry`, `number_of_employees`, `city`, `state`, `active_arr_cny`, `lighted_up_product`, `account_level`, `account_source`, `risk_types`, `high_level_perception`

Note: `industry` is the **overseas** industry field and is NOT readable via `+profile`. Use `business_primary_industry` for domestic (国内) classification.

**Follow-up (VERIFIED 2026-07-17):**
`follow_date`, `create_time`, `owner_id`, `content`, `contacts`, `contact_titles` — these are verified readable fields on the `follow_up` entity.

- `content`: Rich structured notes (typically 200-500 chars of meeting/visit summary).
- **`contacts`**: Multi-reference field returning contact display names (花名/昵称) — e.g., `["刘 怀宇（雪碧）","陈 新杰（阿豹）"]`. This is the primary source for KDM lists.
- **`contact_titles`**: Text field returning corresponding titles — e.g., `["首席运营官","其他主管/经理/总监"]`. Positionally aligned with `contacts`.

⚠️ The following field names were **batch-tested and confirmed invalid** (return "unknown field"): `progress`, `next_step`, `follow_up_type`, `visit_type`, `subject`, `description`, `status`, `type`, `name`, `summary`, `note`, `detail`, `category`, `priority`, `result`, `outcome`. Earlier documentation incorrectly listed some of these as valid — they are NOT.

**Order:**
`order_form_no`, `signing_status`, `earliest_start_date`, `latest_end_date`, `product_names`, `total_amount`, `total_list_fees`, `currency`

**Order Item (raw API only):**
`standard_unit_price`, `actual_unit_price`, `quantity`, `start_date`, `end_date`, `product`, `purchase_type`, `total_price`, `arr`, `purchase_period`, `quantity_unit`

### 5. Option-type fields return JSON strings
Fields like `paid_status`, `follow_up_type` return `{"label":"已付费","color":"green-option"}` — extract `label` for display.

### 6. Order item raw API response format

Raw `order_item` API responses have **fields at the top level** of each item (NOT nested under `field_values`). Currency and option fields in `display_value` are JSON strings:

```json
{
  "actual_unit_price": {"display_value": "{\"currency_iso_code\":\"CNY\",\"currency_value\":858}", ...},
  "purchase_type": {"display_value": "{\"label\":\"增购\",\"color\":\"wathet-option\"}", ...},
  "product": {"display_value": "飞书企业标准版", ...},
  "quantity": {"display_value": "50", ...}
}
```

- Currency fields: `json.loads(item["actual_unit_price"]["display_value"])["currency_value"]`
- Option fields: `json.loads(item["purchase_type"]["display_value"])["label"]` → 新购/增购/续约
- `product.display_value` returns the product name directly

### 7. owner_id filter does NOT work on account list

The `owner_id` field on the account entity is `is_filterable: true` in metadata but the filter is **ignored at runtime** — both via the raw API (`/anchor/api/entity/account/list`) and the CLI (`lark-c360 account list --filter-json`). Regardless of value format (bare ID, quoted ID, display name), the result always contains all 640K+ accounts unfiltered.

**Workaround**: To verify which accounts belong to a specific owner:
1. Get a known account's profile: `lark-c360 account +profile --id <known_id> --field owner_id --json` → extract the user entity ID
2. Batch-verify with per-client keyword search: `lark-c360 account list --keyword "客户名" --field owner_id --json`
3. From the keyword result, check `owner_id.display_value` matches the target owner
4. Do NOT waste time on owner_id filter syntax — confirmed API-level bug as of 2026.07

### 8. Feishu card sending from execute_code
The `execute_code` sandbox does NOT have `feishu-cli` on PATH. Use `terminal()` with the full path `~/.npm-global/bin/feishu-cli` instead.
**同样适用 lark-c360**（实测 2026-08-27）：execute_code 里 subprocess 直接调 `lark-c360` 报 FileNotFoundError——用全路径 `~/.npm-global/bin/lark-c360`，或 `from hermes_tools import terminal` 走 terminal()。

### 9. `search all` is the most efficient single-call pattern
For meeting support / real-time lookups, use `search all` (NOT individual `account list` + `opportunity list` calls):
```bash
lark-c360 search all --keyword "客户名" --limit 5 --json
```
Returns in ONE call:
- **Account**: `id` (for follow-up queries), `nickname`, `paid_status`, `age_type`
- **Opportunity**: `product_sku_keys[]`, `arr` (currency + value), `stage` label
- **Tenant**: `display_name`, `certification_status`

The opportunity section from `search all` provides `product_sku_keys` (array of product names like `["飞书企业旗舰版","飞书一线标准版"]`) and `arr` — fields that are NOT available via `opportunity list --field`.

### 10. Known unavailability
- **Multi-product CSM**: Only `csm_owner` field exists (single value). Office CSM, Meego CSM, People CSM are not exposed as separate fields.
- **Opportunity type (新购/增购/续约)**: Not exposed as a readable field on the opportunity entity. Available only via `order_item` raw API's `purchase_type` field.
- **ISV opportunities**: C360 CLI currently has read-only access to standard opportunities only; ISV opportunities are not readable.

### 10b. 🆕 `tenant metrics` / `account +usage` — AI 用量数据（2026-08-26 实测，推翻旧结论）

⚠️ 旧版本节曾写「account +usage / tenant metrics 对测试客户返回空」——**已推翻**。实测汉阳（有 AI 通用额度的租户）返回完整数据；拓竹/感臻为空是因为那些租户当时无 AI 额度数据，不是命令不可用。

**`tenant metrics get`**：`tenant_metrics` 实体共 **400 字段，其中 173 个 AI 相关**（消耗率/剩余天数/各场景 DAU/ARR 等）。用法：

```bash
lark-c360 tenant metrics get --tenant-id <F开头tenant_id> \
  --field ai_credits_usage_rate --field ai_credits_usage_rate_predict \
  --field ai_credits_quota_remaining_days --field ai_credits_quota_actual_remaining_days \
  --field ai_credits_usage_mom --field ai_credits_asset_time_rate \
  --field tenant_ai_credits_arr --field ai_arpu \
  --field ai_dau_avg_7workday --field ai_dau_avg_7workday_wow \
  --field knowledge_ai_dau --field nexus_bot_dau --field base_ai_dau --field vc_ai_dau --json
```

**关键 AI 字段**（tenant_metrics 实体，全部实测可读）：

| 字段 | 含义 | 信号用途 |
|------|------|---------|
| ai_credits_usage_rate | AI 通用额度当前消耗进度 % | 消耗率（0.7998 → 79.98%） |
| ai_credits_usage_rate_predict | 预计到期消耗进度 % | >100% = 会提前用完（汉阳 567% = 严重超标） |
| ai_credits_quota_remaining_days | 预计剩余可用天数 | <30 天告急（汉阳 14 天） |
| ai_credits_quota_actual_remaining_days | 实际到期剩余天数 | 与预计对比 |
| ai_credits_usage_mom | 用量月环比 % | 用量加速（汉阳 95.78%） |
| ai_credits_asset_time_rate | 当前时间进度 % | 消耗率/时间进度 ≥2 = 超标 |
| tenant_ai_credits_arr | AI 通用额度 ARR | 判档位（49500 = 入门档 9900×5） |
| ai_dau_avg_7workday / _wow | AI DAU 近 7 日均值 / 环比 | 激活规模与趋势 |
| knowledge_ai_dau / nexus_bot_dau / base_ai_dau / vc_ai_dau | 知识问答 / 豆包工作伙伴 / 多维表格 AI / 智能纪要 DAU | 场景分布 |

⚠️ 注意：字段值是字符串 JSON（`"0.7998233333333333"`），解析时 `json.loads` 或 `float()`；返回结构是 `data.entity.<field>.value`。

**`account +usage --id <account_id>`**：C360 自带的风险/机会/到期信号：

```bash
lark-c360 account +usage --id 001BB000004SwFZYA0 --json
# → data.list[0]: {opportunity_list: ["AI 通用额度","智能纪要专用额度"], risk_list: [], exp_soon_list: []}
```

| 字段 | 含义 |
|------|------|
| opportunity_list | 商机机会（AI 额度类型列表） |
| risk_list | 风险信号 |
| exp_soon_list | 到期预警 |

**tenant_id 获取**：`opportunity list` 的 `service_tenant_id` 字段（`F723430651-深圳汉阳科技股份有限公司`，取 `-` 前段）或 `account +usage` 返回的 `tenant_id`。

**全量 AI 字段清单**：`lark-c360 entity meta --entity tenant_metrics --json` 导出后本地过滤（173 个 AI 相关）。

### 10c. 🆕 枚举「我名下客户」的正确姿势（2026-08-26 修正：两步验证法）

`account list --filter-json` 的 owner_id 过滤不可用（见第 7 条）。**两步验证法**：

**第一步**：拉 `opportunity list` 全量 → 本地按 `owner_id.display_value` 过滤（商机 owner 是显示名）：

```bash
# opportunity 的 owner_id 字段返回显示名（袁鑫杰），不是 ID
lark-c360 opportunity list --field id --field account_name --field account_id \
  --field owner_id --field service_tenant_id --limit 100 --offset 0 --json
# 分页拉全量（offset += 100），Python 过滤 owner_id.display_value == "袁鑫杰"
# → 得到 (account_id, account_name, tenant_id) 三元组，顺带拿到 tenant_id
```

**第二步（关键，勿省略）**：⚠️ 商机 owner 是**历史归属**——客户转走后旧商机仍挂原 owner。只按商机过滤会把已转走客户误算进名下。实测（2026-08-26）：商机候选 301 个，`account get` 验证后真正名下仅 38 个——吉比特→陈柳均Lilo、飞速创新→张东琪、零一裂变→何月楠 均为误报。必须对每个候选执行：

```bash
lark-c360 account get --id <account_id> --field id --field name --field owner_id --json
# 验证 owner_id.display_value 仍是我 → 才算名下客户
```

**字段值坑（实测）**：
- `account_id` 的 `display_value` 是**客户名**（reference 字段显示名称），真实 ID 在 `.value`（带引号需 strip）——用 display_value 当 ID 会导致 account get 查询失败
- `account get` 响应：字段直接挂 `data` 下（`data.id/name/owner_id`），**不是** `data.entity`
- `tenant metrics get` 响应：字段在 `data.entity.<field>.value`（与 account get 不同！）

**AI 客户过滤**：`product_sku_keys` 的 value 是 JSON 数组字符串，AI 产品前缀 `feishu_ai_` / `aily` / `nexus_bot` / `vc_ai` / `base_ai` / `miaoda` 等；商机 stage 为「丢单/已退订」的直接跳过。

完整自动化数据链路（含汉阳实测值、升级信号阈值、解析坑）见 `references/ai-opportunity-radar-datapath.md`——做 AI 商机雷达/用量扫描类任务时直接引用。

⚠️ **filter-json DSL 坑（1.2.2）**：`--filter-json` 的 children 项试遍 `type: leaf/term/item/filter/condition` 全报 `unsupported filter item type`；不带 type 报空 type。**不要在 filter 语法上浪费时间——用全量拉取 + 本地过滤**。raw API（`lark-c360 api`）的 `filter.children[].field/operator/value` 在 order_item 场景是可行的（见上文），但 CLI 的 `--filter-json` 在 1.2.2 对 account/opportunity 均不可用。

### 11. 商机盘点：已购 ≠ 新商机

When doing AI opportunity audits（AI 商机盘点）across multiple CSM portfolios, **never mix already-purchased clients with net-new Q3 opportunities**. The user's definition:

- **新商机** = clients explicitly confirmed in meetings as having Q3 增购（upgrade）or 新购（new purchase）of AI 包
- **已购** = clients that already bought AI 包 in prior quarters — these are NOT opportunities, they are existing accounts

**Workflow rule**:
1. Before counting opportunities, cross-reference against any existing "已购客户" list from prior analysis
2. Flag "已XX" notation（e.g. 拓竹已99, 富途99）as already-purchased, not new opportunities
3. Put already-purchased clients in a separate appendix, not in the opportunity count
4. Only clients with explicit Q3 purchase/upgrade intent from meeting transcripts count as 新商机

This tripped the user in the 7/22 五行业交叉分析 — the original table listed 富途99, 领鑫9.9, 大疆, 创梦9.9, 星辉, 青木, 拓竹已99 as "Q3 商机" when they were all existing purchases. Full methodology: see `references/opportunity-audit-methodology.md`.

### 12. JSON 返回结构是 `data.list`（不是顶层 `list`）

`opportunity list` / `follow_up +recent` / `account list` 的 JSON 返回中，记录列表在 **`data.list`**，`total` 在 `data.total`。解析用 `d['data']['list']`；直接 `d.get('list')` 会静默拿到空列表（python 解析无报错但输出为空）。

结构对照：
- `opportunity list` / `follow_up +recent` → 顶层 `{"data": {"total": N, "list": [...]}}`
- `search all` → 顶层直接是 `list`（每条含 account/opportunity/tenant 摘要）
- `opportunity +summary` / `account +profile` → 只有 `entity` 对象

解析前不确定时先 `head -40` 打印原始返回确认层级，不要盲写解析。

### 13. `search all` 可能报 size exceed limit

商机多、返回数据大的客户（如凯迪仕 23 条商机）用 `search all --keyword` 会报 `remote error code=1000430958 size exceed limit`。

**先试最简修复：降低 `--limit`**（实测 2026-08-26：`--limit 10` 报 size exceed，`--limit 3` 直接成功）。关键词命中面广（如城市名「汉阳」、单字简称）时同样会触发，先用 limit 3 重试。

仍失败再回退模式，分实体查反而更干净：

```bash
lark-c360 account search --keyword <客户名>            # 客户概况
lark-c360 opportunity list --keyword <客户名> --field name --field stage --field close_date --json  # 商机阶段
lark-c360 follow_up +recent --account-id <id> --field follow_date --field content --limit 3 --json    # 跟进内容
```

注意 `opportunity scan` 不支持 `--keyword`，用 `opportunity list --keyword`。

### 14. 短名搜索会命中错误主体（同名/子公司）——写进纪要前必须核验

会议标题/客户简称搜 C360 时，短关键词可能命中**名称仅包含该词但并非该客户**的主体（子公司、相似名公司）。实测：会议标题「逸文 x 续约+AI 方案采购」用 `search all --keyword "逸文"` 命中了「深圳市博文馨逸文化传媒有限公司」（博商管理科学研究院旗下，名称含「逸文」二字），实际客户是「深圳市逸文科技有限公司」。用户纠正后才找到正确主体。

**核验清单（把主体名写进纪要/卡片前逐条过）**：

1. 付费状态：续约/采购场景的正确客户通常是**已付费**
2. 跟进记录：`follow_up +recent --account-id <id>` 应有近期记录（正确主体 91 条，错误主体 0 条）
3. 商机阶段与会议上下文吻合：续约会 → 应有客户签约/方案沟通阶段的商机（正确主体有 2026-08-31 客户签约商机）
4. 加后缀重搜：`--keyword "<简称>科技"` 往往直接命中正确主体

**流程**：搜到候选 → 用上述清单核验 → 确认后才写入纪要/卡片。候选主体无跟进、无匹配商机、付费状态对不上 → 换更精确关键词重搜，不要把第一个搜索结果当客户。

## Business Calculator Integration

User has a self-built prorated pricing calculator at `https://bytedance.aiforce.cloud/app/app_4k4ex0bzsderh/openapi/calculator/calculate`. When computing add-on/upgrade costs for a customer:

### Workflow

1. **C360 → extract unit price**: `order_item` API → filter by `product` + `purchase_type` → take latest `actual_unit_price`
2. **C360 → extract expiry**: `order get` → `latest_end_date`
3. **Call calculator** with `Authorization: Bearer OokzHETWqITNmSpEokF16moXN_eomkNlXp7iQLx1_Xs`

### Supported purchase types

| `purchaseType` | Formula | Required fields |
|------|------|------|
| `addon` | `unitPrice × quantity × (daysRemaining/365)` | `unitPrice`, `quantity`, `effectiveDate`, `expiryDate` |
| `upgrade` | `(upgradePrice - originalPrice) × quantity × (daysRemaining/365)` | `originalPrice`, `upgradePrice`, `unitPrice`, `quantity`, `effectiveDate`, `expiryDate` |

### Example (增购 500 seats)

```python
# 1. Get latest enterprise standard add-on unit price from C360
# 2. Get expiry from active order
# 3. Compute
curl -X POST 'https://bytedance.aiforce.cloud/app/app_4k4ex0bzsderh/openapi/calculator/calculate' \
  -H 'Authorization: Bearer OokzHETWqITNmSpEokF16moXN_eomkNlXp7iQLx1_Xs' \
  -H 'Content-Type: application/json' \
  -d '{"purchaseType":"addon","unitPrice":"858","quantity":"500","effectiveDate":"2026-07-06","expiryDate":"2026-12-30"}'
# → {"finalPrice":209210.96,"daysRemaining":178,"formula":"产品单价 × 席位 × (剩余天数 / 365)",...}
```

## Batch Query Pattern

When querying multiple customers, use `execute_code` with `terminal()` to parallelize the CLI calls. Each call is fast (~1-2s). The pattern:

```python
from hermes_tools import terminal
import json

for name, eid in [("高驰", "001xxx"), ("逸文", "001yyy")]:
    fields = 'name nickname paid_status owner_id csm_owner ...'
    cmd = f'lark-c360 account +profile --id {eid} --field {fields} --json'
    r = terminal(cmd, timeout=15)
    # parse and collect
```

Don't try to do this with shell loops — use `execute_code` for clean Python parsing of JSON output.
