---
name: c360-cli
description: Use lark-c360 CLI to look up customer accounts, profiles, follow-up records, opportunities, and tenants. Search by keyword, get detailed profiles, and list recent follow-ups.
category: productivity
---

# C360 CLI

Query customer data from C360 (Lark CRM) via the `lark-c360` CLI. Installed at `~/.npm-global/bin/lark-c360` (v1.2.2). Logged in as 袁鑫杰, online environment.

## Trigger

When the user asks to check customer account info, follow-up records, opportunities, or tenant details — use this CLI instead of browser or raw API.

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

### When C360 returns nothing

If `follow_up +recent` returns zero records or contacts are empty, C360 has no KDM data for this account. Say "C360 无对接人记录" — do NOT guess.

## Critical Pitfalls

### 1. Flag names are counter-intuitive
- `account +profile` uses **`--id`** (NOT `--entity-id`)
- `follow_up +recent` uses **`--account-id`** (NOT `--id`, NOT `--entity-id`)
- `search all` uses **`--keyword`** (NOT positional arg)
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
- **account +usage / tenant metrics**: Return empty for tested accounts (拓竹, 感臻) — data may not be populated for all accounts.

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
