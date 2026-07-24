# C360 跟进记录查询 (`follow_up +recent`)

## 命令

```bash
lark-c360 follow_up +recent --account-id <account_id> --limit 3 --json
```

- `--account-id`（必需）：来自 `search all` 返回的 account 的 `entity_id`
- `--limit`（可选，默认 10）：返回条数
- 默认按 `follow_date desc, create_time desc` 排序

## 使用场景

客户会议入会时，在 `search all` 获取商机信息后，用此命令获取最近跟进记录，帮助用户了解上次沟通内容。

## 完整流程

```bash
# Step 1: 搜索客户，获取 account_id
lark-c360 search all --keyword "拓竹" --limit 5 --json
# 从返回的 data.account.list[0].entity_id 获取 account_id

# Step 2: 查最近跟进
lark-c360 follow_up +recent --account-id 0010o00002xxx --limit 3 --json
```

## 输出字段

| 字段 | 说明 |
|---|---|
| `follow_date` | 跟进日期 |
| `content` | 跟进内容/摘要 |
| `follow_up_type` | 跟进类型 |
| `creator_name` | 创建人 |

## 注意事项

- `account_id` 格式如 `0010o00002h2zwvAAA`，来自 C360 search all 的 account entity_id
- 与 `follow_up +history` 的区别：`+recent` 返回有 `content` 字段的近期记录，`+history` 返回更长时间范围的记录
