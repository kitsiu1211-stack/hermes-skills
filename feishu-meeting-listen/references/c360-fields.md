# C360 CLI 可查字段速查

> 实测有效的 field name，避免反复试错。

## 最高效入口：`search all`

一次调用同时返回 account + opportunity + tenant：

```bash
lark-c360 search all --keyword <公司名> --limit 5 --json
```

### 返回结构

**account.title** — 客户属性
- `name` — 公司全称
- `age_type` — `{"label":"老客"}` 或 `{"label":"新客"}`
- `paid_status` — `{"label":"已付费"}` 或 `{"label":"未付费"}`

**account.abstract** — 客户详情
- `csm_owner` — CSM 负责人（单一字段，**不区分** Office/Meego/People）
- `owner_id` — 销售负责人
- `business_primary_industry` — 行业（如 `{"label":"消费电子和家电产业链"}`）
- `nickname` — 客户简称
- `company_list` — 关联租户列表

**opportunity.title** — 商机摘要
- `name` — `Oppty-公司名-日期`
- `stage` — `{"label":"方案沟通"|"客户签约"|"赢单"|"丢单"}`

**opportunity.abstract** — 商机详情
- `product_sku_keys` — 产品名称数组，如 `["飞书企业旗舰版","飞书一线标准版"]`
- `arr` — 年化收入，`{"currency_iso_code":"CNY","currency_value":"***"}`（⚠️ 敏感数据，禁止输出到告警/摘要）
- `account_name` — 关联客户名

**tenant** — 租户信息
- `certification_status` — 认证状态
- `display_name` — 租户显示名

## 精确字段查询：`account list`

```bash
lark-c360 account list --keyword <公司名> --limit 1 \
  --field name --field csm_owner --field owner_id \
  --field age_type --field paid_status --field business_primary_industry \
  --field nickname --json
```

> ⚠️ `account search` 不接受 `--field`，用 `account list`。

## 精确字段查询：`opportunity list`

```bash
lark-c360 opportunity list --keyword <公司名> --limit 1 \
  --field name --field stage --field amount --field owner_id --field close_date \
  --json
```

**已验证可用的 opportunity 字段**：`name`, `stage`, `amount`, `owner_id`, `close_date`

> ⚠️ `search all` 中的 opportunity 字段与 `opportunity list` 不完全重叠。`search all` 有 `product_sku_keys` 和 `arr`，`opportunity list` 有 `amount` 和 `close_date`。

## 跟进记录

```bash
lark-c360 follow_up +recent --account-id <account_id> --limit 1 \
  --field id --field follow_date --field owner_id --field content --json
```

**已验证可用的 follow_up 字段**：`id`, `follow_date`, `create_time`, `owner_id`, `content`

> ⚠️ `follow_up +recent` 默认只返回 `id`，必须显式传 `--field`。`content` 字段包含完整的跟进笔记文本（通常数百字），适合截取前 200 字作为摘要。
>
> **字段发现方法**：C360 各实体字段名与常见 CRM 命名不一致（如 follow_up 没有 `name`/`subject`/`description`），无法靠猜测。可用 `dry-run` 看 sorts 中引用的字段（如 `follow_date`、`create_time`）反推有效字段名，再批量 `--field` 试错。`search all` 返回的结构体中的 key 也是有效的 field name 来源。

## poll-v5.sh 集成方式

客户名命中时的完整查询链：

1. `search all --keyword <客户名>` → 拿 `account_id` + `product_sku_keys` + `stage`
2. `follow_up +recent --account-id <account_id>` → 拿 `content` 截前 200 字
3. 组装告警：产品线 + 阶段 + 跟进摘要

告警不输出用户已知的基础信息（行业/CSM/客户类型/付费状态）。

## 已知限制

| 限制 | 说明 |
|---|---|
| 多产品线 CSM | 无法区分 Office CSM / Meego CSM / People CSM，仅 `csm_owner` |
| 商机类型 | 新购/增购/续约字段未暴露 |
| ISV 商机 | C360 CLI 暂不能读取 ISV 商机 |
| account +usage | 多数客户返回空 list（依赖租户使用数据存在） |
| tenant metrics | `risk-and-opportunity` 多数客户返回空 |
| 用户已知信息 | 行业、CSM 姓名、付费状态等用户开会前就知道，告警中不输出 |

## 🚨 敏感数据脱敏规则

C360 部分字段属于客户商业机密，**禁止出现在任何对外输出中**（告警、摘要、cron 输出、飞书卡片、Obsidian 笔记）。

| 字段 | 敏感性 | 规则 |
|---|---|---|
| `arr` (年化收入) | ⚠️ 敏感 | 禁止输出具体数字。仅用于内部判断客户量级 |
| `amount` (商机金额) | ⚠️ 敏感 | 同上。提及商机时仅描述产品线 + 阶段 |
| `account_id` | ⚠️ 敏感 | 仅用于 API 调用链，不暴露给用户 |
| `currency_value` | ⚠️ 敏感 | 所有含此子字段的上级字段（arr/amount）均按敏感处理 |
