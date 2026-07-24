# C360 CLI 参考

## 安装

```bash
# 下载安装脚本
curl -o /tmp/lark-c360-agent-install.sh https://lf-ldic360.feishucdn.com/obj/ldi-c360/cli/lark-c360-agent-install.sh
bash /tmp/lark-c360-agent-install.sh

# 二进制路径
~/.npm-global/bin/lark-c360

# 加入 PATH（一次性）
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc
```

## 首次登录

```bash
# 1. 发起授权
lark-c360 auth login   # 打开浏览器完成飞书 OAuth

# 2. 授权完成后确认（⚠️ 是 -resume 不是 --result）
lark-c360 auth login -resume
```

## 查询商机（opportunity list）

```bash
# 基础查询：按关键词搜索
lark-c360 opportunity list --keyword "拓竹" --limit 3 --json

# ⚠️ 关键陷阱：一旦使用 --field 参数，必须显式加 --field name
# 否则 name 字段不会出现在输出中
lark-c360 opportunity list --keyword "感臻" --limit 3 \
  --field name --field stage --field amount --field owner_id --field close_date \
  --json
```

## 字段解析

C360 API 返回的字段值多为 JSON 字符串，需要二次解析：

| 字段 | 原始值示例 | 解析方式 |
|---|---|---|
| `stage` | `{"label":"客户签约","color":"blue-option"}` | `json.loads(...)["label"]` |
| `amount` | `{"currency_iso_code":"CNY","currency_value":"***"}` | `json.loads(...)` → （⚠️ 敏感，不输出） |
| `owner_id` | `"005BB000000Hg80YAC"` / display: `"袁鑫杰"` | 直接用 `display_value` |
| `close_date` | `"2026-09-16"` | 直接用 `display_value` |

## Bash 脚本中安全传 JSON 到 Python

❌ **错误**：通过命令行参数传 JSON（转义问题，f-string 嵌套引号冲突）
```bash
python3 -c "data = json.loads('''$result''')"
```

✅ **正确**：通过 stdin 管道传入
```bash
echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
# ... 处理 data ...
"
# 注意：-c 的 Python 代码中避免使用 f-string（bash 双引号内 \" 会破坏引号配对）
# 改用字符串拼接：'前缀: ' + str(val)
```

## 可用命令

```bash
lark-c360 opportunity list   # 商机列表
lark-c360 opportunity get    # 商机详情（按 ID）
# 权限：仅读取，无创建/写入
```
