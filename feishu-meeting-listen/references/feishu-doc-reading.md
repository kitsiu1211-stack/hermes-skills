# 飞书文档读取

## 飞书 Wiki 文档

```bash
# 1. 解析 wiki token（从 Lark URL 中提取）
#    https://bytedance.larkoffice.com/wiki/NgpPw7AvbiyJwAkQwvYcZlePnkb
#    → node_token = "NgpPw7AvbiyJwAkQwvYcZlePnkb"

# 2. 获取文档 obj_token 和类型
lark-cli wiki +node-get --node-token "<node_token>" --as user
# → obj_token: "VGqhdzvTmoXLgCxL4xocFTrknTh"
# → obj_type: "docx"

# 3. 拉取完整内容（大文档用文件重定向避免 JSON 炸上下文）
lark-cli docs +fetch --doc "<obj_token>" --doc-format markdown --as user > /tmp/doc.md

# 4. 如果是 XML 格式（markdown 输出可能仍是 XML），提取纯文本
python3 -c "
import json, re, html
with open('/tmp/doc.md') as f:
    d = json.load(f)
content = d['data']['document']['content']
content = content.replace('\\\\\"', '\"').replace('\\\\n', '\n')
content = re.sub(r'<cite[^>]*></cite>', '', content)
content = re.sub(r'<[^>]+>', '', content)
content = html.unescape(content)
lines = [l.strip() for l in content.split('\n') if l.strip()]
print('\n'.join(lines[:5000]))
"
```

## 飞书 Doc 文档（docx/doc）

```bash
# 直接用 feishu_doc_read（需要 Feishu 评论上下文）
feishu_doc_read <doc_token>
# 若无评论上下文 → 用 lark-cli docs +fetch 替代
```

## 飞书文档 URL 结构

```
https://bytedance.larkoffice.com/docx/<doc_token>   # 普通文档
https://bytedance.larkoffice.com/wiki/<wiki_token>   # Wiki 文档
https://bytedance.larkoffice.com/sheets/<token>      # 电子表格
```

## 注意事项

- Wiki 文档的 node_token ≠ doc_token，需两步获取
- 大文档 (>100KB) 避免 `--format json` 进上下文 → 用文件重定向
- XML 格式需去除 cite 标签（用户 @ 引用）避免噪音
- `--doc-format markdown` 有时仍返回 XML 包裹的 JSON，需双重处理
