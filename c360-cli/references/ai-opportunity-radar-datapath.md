# C360 AI 商机雷达数据链路（2026-08-26 实测，供 ai-win-opportunity-radar 类自动化引用）

## 完整数据链路

```
opportunity list 分页拉全量
  → 本地过滤 owner_id.display_value == 目标人
  → 过滤 product_sku_keys 含 AI 前缀（feishu_ai_ / aily / nexus_bot / vc_ai / base_ai / miaoda / openclaw）
  → 过滤 stage 非「丢单/已退订」
  → 候选 account_id 去重
  → 逐个 account get 验证当前 owner_id 仍是目标人（两步验证法，防历史商机误报）
  → 对每个验证通过的客户：tenant metrics get 拉 AI 字段
  → 按升级信号清单判定 → Generator/Evaluator → 飞书卡片
```

## 实测数据点（汉阳，2026-08-26）

- `ai_credits_usage_rate`: 0.7998（79.98%）
- `ai_credits_usage_rate_predict`: 5.6727（**567%** — 严重超标，强升级信号）
- `ai_credits_quota_remaining_days`: 14（预计剩余天数告急）
- `ai_credits_quota_actual_remaining_days`: 364（实际到期天数）
- `ai_credits_usage_mom`: 0.9578（月环比 +95.78%）
- `tenant_ai_credits_arr`: 49500（≈ 入门档 9900×5）
- `ai_dau_avg_7workday`: 302.29；knowledge_ai_dau 162 / nexus_bot_dau 93 / base_ai_dau 71 / vc_ai_dau 127

## 升级信号判定阈值（V3.1 清单）

| 档位 | 阈值 |
|------|------|
| 入门→9.9万 | predict > 150% 或 消耗率/时间进度 ≥ 2 或 剩余 < 30 天 |
| 9.9万→29.7万 | predict > 200% 或 (消耗率>80% 且 mom>50%) 或 (剩余<30天 且 DAU环比涨) |
| 29.7万→99万 | predict > 300% 或 DAU>800 或 (消耗率>70% 且 多场景涨) |

强度：🔴 强 = predict>300% 或 剩余<15天；🟡 中 = predict 150-300% 或 剩余 15-30 天；🟢 弱 = predict 100-150% 或 DAU 环比涨

## 解析注意事项

- `tenant metrics get` 返回 `data.entity.<field>.value`（字符串，需 float()）
- `opportunity list` 的 `account_id.display_value` 是客户名，真实 ID 在 `.value`（strip 引号）
- `account get` 返回 `data.<field>`（不在 entity 下）——与 tenant metrics 结构不同！
- C360 CLI 的 `--filter-json` DSL 对 account/opportunity 不可用（试遍 type: leaf/term/item/filter/condition 全报 unsupported），一律全量拉取 + 本地过滤
