# 南区区域AI总表 解析指南

## 表信息

- Base: `GlAubuVt4aFD6Vsk6KYcu5DonGg`（南区区域AI总表）
- Table: `tblNTJtyLAeIPqN1`（每日更新-客户商机表）
- 关键视图: 鑫杰表（view_id: `vewuOyTxYA`）

## 关键字段

| 字段名 | 字段 ID | 类型 | 说明 |
|--------|---------|------|------|
| 客户名称 | `fldeXTnJKL` | text | |
| Q3 AI 商机盘点 | `fldxplYlHm` | text | 不为空且不以 `无商机` 开头 = 有商机 |
| 客户所有人 | `fldqvWUeak` | user (multiple) | JSON 数组 `[{"id":"ou_xxx","name":"姓名"}]` |
| CSM 所有人 | `fld3xOviwV` | user (multiple) | 同上 |
| 国内一级行业 | `fldF1YknMK` | select | |
| AI商机ARR | `fldPMbSgXh` | formula | 计算字段，9.9万=9900, 29.7万=297000, 99万=990000 |
| AI商机阶段 | `fldnrSkgH4` | formula | |
| 已购 AI 包（9.9 万以上）的使用场景 | `fldu54gK0p` | text | 已购客户的场景描述 |
| 付费状态 | `fldT5Kt73f` | select | 已付费/未付费/流失 |

## 查询命令

```bash
# 分页拉取全表
lark-cli base +record-list \
  --base-token "GlAubuVt4aFD6Vsk6KYcu5DonGg" \
  --table-id "tblNTJtyLAeIPqN1" \
  --limit 200 \
  --offset 0 \
  --as user
```

## 输出格式与解析

CLI 1.0.71 的 `+record-list` **默认输出 Markdown 表格**：

```
| _record_id | 客户 ID | ... | 客户名称 | ... | Q3 AI 商机盘点 | ... | 客户所有人 | ... |
| --- | --- | ... | --- | ... | --- | ... | --- | ... |
| recvcu... | 001BB... | ... | 康舒电子... | ... |  | ... | [{"id":"ou_...","name":"周晶心"}] | ... |
...
Meta: count=200; has_more=true; ...
```

### 解析策略

```python
# 1. 找到表头行定位列索引
header_cols = [c.strip() for c in header_line.split('|')]
name_idx = header_cols.index('客户名称')
q3_idx = header_cols.index('Q3 AI 商机盘点')
owner_idx = header_cols.index('客户所有人')

# 2. 解析数据行（跳过 Meta 行）
for line in data_lines:
    if line.startswith('Meta:'):
        # 检查 has_more 决定是否继续分页
        break
    parts = line.split('|')
    name = parts[name_idx].strip()
    q3 = parts[q3_idx].strip()
    owners = json.loads(parts[owner_idx].strip())  # JSON 数组
```

## 踩坑清单

| 尝试 | 结果 | 教训 |
|------|------|------|
| `--json` flag | 返回 total=0 | CLI 不支持此 flag 用于 +record-list |
| `--format json` | validation error | 不支持 |
| `--field-ids "fldeXTnJKL,fldxplYlHm"` | 返回空 | 指定字段 ID 反而没有数据 |
| `--limit 500` | validation error | 最大 200 |
| 不传 `--limit` | 默认只有 3 条 | 必须显式传 limit |
| 用 `--view-id` 过滤 | 返回空 | 直接用 table 级查询，Python 侧过滤人员 |

## 分页示例

```python
offset = 0
limit = 200
while True:
    result = subprocess.run([
        'lark-cli', 'base', '+record-list',
        '--base-token', 'GlAubuVt4aFD6Vsk6KYcu5DonGg',
        '--table-id', 'tblNTJtyLAeIPqN1',
        '--limit', str(limit),
        '--offset', str(offset),
        '--as', 'user'
    ], capture_output=True, text=True, timeout=60)
    
    # 解析表格...
    
    if 'has_more=true' not in result.stdout:
        break
    offset += limit
```
