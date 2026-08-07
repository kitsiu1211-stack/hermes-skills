# C360 CLI 查询语法参考

## account 搜索

```bash
# 关键词搜索
lark-c360 account search --keyword "客户关键词" --limit 5 --json

# 返回 data.list[]，每项含 title.name + abstract.id
```

## account 详情

```bash
lark-c360 account +profile --id <account_id> --json
```

## opportunity 商机

```bash
lark-c360 opportunity list \
  --filter-json '[{"field":"account_id","op":"eq","value":"<account_id>"}]' \
  --json
```

## follow_up 最近跟进

```bash
lark-c360 follow_up +recent --account-id <account_id> --limit 3 --json
```

## 常见陷阱

- `--keyword` 是必需参数，不是位置参数
- `opportunity list` 需要 `--filter-json`，不能直接用位置参数
- `account get` 需要 `--id`，不是 `--name`
- 战新会 = 深圳市战略性新兴产业发展促进会（001TL0000048He5YAE），搜索 "战略" 可能找不到，需要搜 "战新"
- 有些客户 C360 无商机数据，标注 "未查到" 即可，不硬填
- C360 提醒升级（如 1.2.2 → 1.2.7）不影响功能，可忽略或顺手 `lark-c360 update`
