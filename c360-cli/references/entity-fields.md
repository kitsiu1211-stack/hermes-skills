# C360 Entity Fields Reference

## Account Fields (readable)

| Field | Display Name | Type |
|-------|-------------|------|
| name | 客户名称 | text |
| nickname | 客户昵称 | text |
| paid_status | 付费状态 | option |
| owner_id | 客户所有人 | reference |
| csm_owner | CSM 所有人 | reference |
| account_tier | 客户等级 | option |
| business_primary_industry | 国内一级行业 | option |
| business_second_industry | 国内二级行业 | option |
| business_tertiary_industry | 国内三级行业 | option |
| business_quaternary_industry | 国内四级行业 | option |
| number_of_employees | 员工数 | option |
| city | 城市 | option |
| state | 省份/州 | option |
| active_arr_cny | 客户有效 ARR（CNY） | currency |
| active_arr_usd | 客户有效 ARR（USD） | currency |
| lighted_up_product | 点亮产品 | multi_option |
| account_level | CSM 客户分层 | option |
| account_source | 客户来源 | option |
| risk_types | 风险类型 | multi_option |
| high_level_perception | 高层感知 | option |
| negative_events | 负面事件 | multi_option |
| account_status_details | 客户状态详述 | textarea |
| channel_manager | 渠道经理（主责） | reference |
| pre_sales_consultant | 售前（主责） | reference |
| account_team_member_users | 客户团队成员 | multi_reference |
| claim_date | 认领日期 | date_string |
| total_employees | 公司员工总数 | integer |
| domestic_or_oversea | 数据归属 | option |
| named_account_categories | 目标客户类型 | multi_option |

## Follow-Up Fields (readable)

| Field | Display Name | Type |
|-------|-------------|------|
| follow_date | 跟进日期 | date_string |
| progress | 一句话进展 | textarea |
| next_step | 下一步计划 | rich_text |
| content | 沟通内容 | rich_text |
| owner_id | 记录所有人 | reference |
| follow_up_type | 跟进记录类型 | option |
| visit_type | 跟进方式 | option |
| contacts | 联系人 | multi_reference |
| account_nick_name | 客户昵称 | text |
| account_id | 跟进客户 | reference |
| participants | 参会人 | multi_reference |
| opportunity_id | 关联商机 | reference |
| service_ticket_id | 关联服务单 | reference |
| display_name | 展示名称 | text |
| rex_suggestion | 雷克斯建议 | text |
| rex_score | 雷克斯分数 | integer |
| write_type | 写入方式 | option |
| files | 附件 | multi_reference |
| minutes | 关联妙记 | text |

## Note

- Option-type fields return `{"label":"...", "color":"..."}` — extract `label` for display.
- Currency fields return `{"currency_iso_code":"CNY", "currency_value":123456.78}`.
- Multi-option/multi-reference return arrays of labels or IDs.

## Order Fields (readable)

| Field | Display Name | Type |
|-------|-------------|------|
| order_form_no | 订单编号 | reference |
| signing_status | 签约状态 | option |
| earliest_start_date | 最早服务开始日期 | date_string |
| latest_end_date | 最晚服务结束日期 | date_string |
| product_names | 订单包含产品 | multi_reference |
| total_amount | 销售总金额 | currency |
| total_list_fees | 列表总金额 | currency |
| currency | 币种 | option |
| account | 客户名称 | reference |
| signing_debook_status | 退订状态 | option |
| agreement_type | 协议类型 | option |
| subscription_method | 订阅方式 | option |
| order_create_method | 订单创建方式 | option |
| on_offline_order | 线上/线下订单 | option |

## Order Item Fields (raw API only, via `/anchor/api/entity/order_item/list`)

| Field | Display Name | Type |
|-------|-------------|------|
| standard_unit_price | 列表单价 | currency |
| actual_unit_price | 销售单价 | currency |
| quantity | 购买数量 | text |
| start_date | 服务开始日期 | date_string |
| end_date | 服务结束日期 | date_string |
| product | 产品名称 | reference |
| purchase_type | 购买类型 | option |
| total_price | 销售总价 | currency |
| arr | ARR | currency |
| purchase_period | 购买时长 | text |
| period_unit | 时长单位 | option |
| quantity_unit | 数量单位 | option |
| service_status | 服务状态 | option |
| discount_percent | 折扣率 % | text |
