---
name: renewal-proposal
description: Generate customer renewal proposals by pulling C360 CLI data (products, seats, pricing, history) and matching against the RM renewal strategy framework (3 scenarios). Output in spreadsheet/document format for direct customer delivery.
category: productivity
---

# Renewal Proposal Generation

Generate customer renewal proposals for expiring Feishu contracts. Combines C360 CLI data retrieval with the RM old-customer renewal strategy framework.

## Trigger

When the user asks to generate a renewal proposal/scheme for a specific customer, or analyze expiring contracts and suggest renewal strategies.

## Prerequisites

- `lark-c360` CLI authenticated (v1.1.15+, as 袁鑫杰)
- `feishu-cli` available for document search/output
- Knowledge of the three renewal scenarios (see `references/renewal-strategy.md`)

## Workflow

### Phase 1: Research (Learn from Past Proposals)

Before generating any new proposal, search for past renewal proposals to understand the user's actual pricing patterns. Document naming pattern:
```
截止至<date>，<customer_name> & 2026飞书续约方案
```

Use `feishu-cli docx builtin search` (requires UAT) to find these. Read at least 3-5 past proposals covering different scenarios to calibrate pricing logic.

### Phase 2: Pull Customer Data

For the target customer, use `lark-c360`:

```bash
# 1. Search for account
lark-c360 search all --keyword "<customer_name>" --limit 5 --json

# 2. Get full profile
lark-c360 account +profile --id <entity_id> \
  --field name --field nickname --field paid_status \
  --field owner_id --field csm_owner --field account_tier \
  --field business_primary_industry --field number_of_employees \
  --field active_arr_cny --field lighted_up_product \
  --field account_level --field risk_types --json

# 3. Get active orders → find expiration dates, products, amounts
lark-c360 order get --id <order_entity_id_F> \
  --field order_form_no --field signing_status \
  --field earliest_start_date --field latest_end_date \
  --field product_names --field total_amount \
  --field total_list_fees --field currency --json

# 4. Get order items (line-level: unit prices, quantities, discounts)
lark-c360 api --method POST --path /anchor/api/entity/order_item/list \
  --data '{"filter":{"relation":"AND","children":[{"field":"account_id","operator":"EQ","value":"<entity_id>"}]},"fields":["standard_unit_price","actual_unit_price","quantity","start_date","end_date","product","purchase_type","total_price","arr","purchase_period","quantity_unit"],"limit":50,"offset":0}' --json

# 5. Get recent follow-ups (relationship status, risk signals)
lark-c360 follow_up +recent --account-id <entity_id> --limit 5 \
  --field follow_date --field progress --field next_step --field owner_id --json
```

### Phase 3: Scenario Classification

Match the customer against the three renewal scenarios:

| Scenario | Criteria | Core Strategy |
|----------|----------|---------------|
| **1+1 打包续约** | Has discount room + cross-sell opportunity | Bundle renewal with new product, staircase pricing |
| **抬价型** | Non-standard discount OR seat reduction | 3-month advance notice, emotional value, multiple guided options |
| **平续型** | Already at standard minimum discount | Early bird lock-in, decision tree, success stories |

Key data points for classification:
- `actual_unit_price` vs `standard_unit_price` → discount level
- Whether discount is below standard minimum → non-standard flag
- Current `quantity` vs historical quantity → seat change trend
- `purchase_type` containing 新购/增购 → cross-sell history

### Phase 4: Generate Proposal

Output a renewal scheme containing:

**Historical Summary (up to expiration date):**
- Products purchased, seats, unit prices, discounts, total costs
- Historical giveaways or special conditions (from past orders)

**New Proposal:**
- Scenario classification with reasoning
- Pricing strategy (specific discount, price, total)
- Cross-sell recommendation (for 1+1 scenario)
- Risk points and mitigation
- Suggested communication timeline and approach

**Output Format:** Feishu docx document (preferred over card due to security — cards lack access control). The template structure follows the user's existing format (see past proposals).

### Phase 5: Delivery

Create the document via `feishu-cli`:
```bash
feishu-cli docx document create --title "截止至<date>，<customer> & 2026飞书续约方案"
```

Then write content using the two-step convert+create flow (max 50 blocks per call).

## Pitfalls

1. **UAT required for doc search**: Finding past proposals requires user access token. If expired, run `feishu-cli auth login --print-url --scopes "drive:drive docx:document"` and have the user authorize in browser.
2. **Historical giveaways**: Some customers have legacy freebies/giveaways. Check past order items for `actual_unit_price = 0` or quantity discrepancies.
3. **Pro-rata add-on pricing**: For mid-cycle add-ons, compute `remaining_days / 365 × unit_price × quantity × discount_rate`.
4. **Order item product filter unreliable**: Per-SKU unit prices may not be extractable via product filter. Cross-reference with deal desk if needed.
5. **Wiki doc reading**: If the doc endpoint fails, the document may be a Bitable/Sheet — try alternative APIs or ask the user to share directly.

## References

- `references/renewal-strategy.md` — Full RM renewal strategy document text

## 质检：Generator → Evaluator（强制）

本 Skill 产出客户续约提案，**必须经过 Evaluator 独立评分后才能交付**。

| 维度 | 阈值 | 检查要点 |
|------|------|---------|
| **客户匹配度** | ≥7 | 提案内容是否针对该客户的具体情况？有无模板感？ |
| **数据准确性** | ≥7 | C360 数据是否正确引用？金额、日期、版本号是否准确？ |
| **可操作性** | ≥7 | 用户拿到后能否直接发给客户？还是需要二次加工？ |

Generator→Evaluator→全部≥7交付/修正重评（最多3轮）。禁止自评。
