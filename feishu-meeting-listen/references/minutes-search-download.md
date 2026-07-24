# 妙记搜索与下载（Post-hoc Minutes Retrieval）

当需要回查已经转写完成的会议妙记时使用。与实时旁听不同——这是事后查历史会议。

## 搜索妙记

```bash
# 按 owner 搜索（自己的会议）
lark-cli minutes +search --as user --owner-ids me --start 2026-07-21 --page-size 10 --format table

# 按参与者搜索
lark-cli minutes +search --as user --participant-ids <open_id> --start 2026-07-21 --format table

# 按关键词搜索
lark-cli minutes +search --as user --query "商机" --start 2026-07-21 --format table

# 按 owner（其他人）
lark-cli minutes +search --as user --owner-ids <open_id> --start 2026-07-21 --format table
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `--query` | 搜索关键词（不是 `--keyword`） |
| `--owner-ids` | owner open_id，`me` = 当前用户 |
| `--participant-ids` | 参与者 open_id，`me` = 当前用户 |
| `--start` | 时间下限（ISO 8601 或 YYYY-MM-DD） |
| `--end` | 时间上限 |
| `--page-size` | 1-30，默认 15 |
| `--format` | json / pretty / table / ndjson / csv |

## 下载转写

```bash
# 下载单个妙记的转写文本
lark-cli minutes +detail --minute-tokens <token> --transcript

# 批量下载（逗号分隔）
lark-cli minutes +detail --minute-tokens token1,token2,token3 --transcript
```

**⚠️ 注意**：flag 是 `--minute-tokens`（复数），不是 `--minutes-token`。

## 文件位置

下载后文件保存在 `~/.hermes/minutes/minutes/<token>/transcript.txt`。
注意路径是嵌套的 `minutes/minutes/`（lark-cli 输出会打印实际路径）。

## 常见场景

### 场景 1：查找最近的会议

```bash
# 最近几天的所有会议
lark-cli minutes +search --as user --owner-ids me --start $(date -v-7d +%Y-%m-%d) --format table
```

### 场景 2：找某人参加的会议

```bash
# 先查 open_id
lark-cli contact +search-user --query "姓名"

# 再用 participant-ids 搜
lark-cli minutes +search --as user --participant-ids <open_id> --start 2026-07-20 --format table
```

### 场景 3：会议刚结束，妙记尚未生成

妙记生成有延迟（通常 1-5 分钟）。如果 `+search` 查不到：
1. 等 1-2 分钟后重试
2. 如果用户发了妙记链接，直接从 URL 提取 token 用 `+detail` 下载
