# C360 CLI 能力矩阵（会议旁听实时情报源）

> 安装: `npm install -g @lark-c360/cli` → `~/.npm-global/bin/lark-c360`
> 登录: `lark-c360 auth login -no-browser` → 浏览器授权 → `lark-c360 auth login -resume`
> 有效期: OAuth token，过期后需重新 `lark-c360 auth login -resume`

## 核心概念

C360 CLI 通过 `anchor_web` 后端查询飞书 CRM 数据，只读权限。实体间关联链路：

```
公司名 → account search → account_id
                    ↓
          opportunity list (keyword)
          follow_up +recent (--account-id)
          order list (keyword)
          search all (keyword) ← 最省调用
```

## 一调用即得：`search all`

**最推荐的首选查询**。一次调用返回 account + tenant 信息，无需知道字段名。

```bash
lark-c360 search all --keyword <公司名> --limit 1 --json
```

**返回数据示例（拓竹）**：

| 字段 | 值 | 来源路径 |
|---|---|---|
| 公司名 | 深圳拓竹科技有限公司 | `account[0].title.name` |
| 客户类型 | 老客 | `account[0].title.age_type` → `{"label":"老客"}` |
| 付费状态 | 已付费 | `account[0].title.paid_status` → `{"label":"已付费"}` |
| 行业 | 消费电子和家电产业链 | `account[0].abstract.business_primary_industry` |
| CSM | 慕子柯 | `account[0].abstract.csm_owner` |
| 租户名 | Bambulab | `account[0].abstract.company_list[0].tenant_name` |
| 租户认证 | 未认证 | `tenant[0].title.certification_status` |

**解析 Python 片段**：
```python
accts = data['data']['account']['list']
a = accts[0]
name = a['title']['name']['display_value']
age_label = json.loads(a['title'].get('age_type',{}).get('display_value','{}')).get('label','?')
paid_label = json.loads(a['title'].get('paid_status',{}).get('display_value','{}')).get('label','?')
industry = json.loads(a['abstract'].get('business_primary_industry',{}).get('display_value','{}')).get('label','?')
csm = a['abstract'].get('csm_owner',{}).get('display_value','?')
```

## Opportunity（已集成 v5）

```bash
lark-c360 opportunity list --keyword <公司名> --limit 1 \
  --field name --field stage --field amount --field owner_id --field close_date --json
```

⚠️ **陷阱**：指定 `--field` 时必须显式加 `--field name`，否则只返回你指定的字段（id/name 不是默认值）。

解析 stage/amount 需要二次 `json.loads()`：
```python
stage_label = json.loads(o['stage']['display_value'])['label']  # → "方案沟通"
amt = json.loads(o['amount']['display_value'])                   # → {"currency_iso_code":"CNY","currency_value":"***"}
```

## 待探索（字段名未知，需要查 entity meta）

| 命令 | 已知 | 未知 |
|---|---|---|
| `follow_up +recent --account-id <id>` | 拓竹 133 条记录 | 字段名（非 name/subject/description/type） |
| `order list --keyword <公司名>` | 拓竹 432 条订单 | 字段名、订单详情结构 |
| `account +usage --id <id>` | 调用 tenant_metrics API | 拓竹返回空，可能数据依赖 |
| `tenant metrics risk-and-opportunity --account-id <id>` | 同上 | 同上 |

## 账号关联

`account search --keyword <公司名>` → `entity_id`，用于 follow_up / account +usage 等需要 `--account-id` 的命令。

## 已有客户实测

| 公司 | account_id | 商机数 | 跟进数 | 订单数 |
|---|---|---|---|---|
| 拓竹科技 | ***（已脱敏） | 457 | 133 | 432 |
| 感臻智能 | （待查） | 63 | - | - |
| 和生创新 | （待查） | 138 | - | - |
