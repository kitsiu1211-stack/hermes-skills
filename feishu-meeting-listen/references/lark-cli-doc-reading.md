# 用 lark-cli 读取飞书文档

```bash
# 获取文档内容（markdown 格式最清晰）
lark-cli docs +fetch --doc "<doc_token>" --doc-format markdown

# xml 格式保留完整结构
lark-cli docs +fetch --doc "<doc_token>" --doc-format xml
```

doc_token 从飞书文档 URL 提取：
- `https://bytedance.larkoffice.com/docx/VXnpdcUFWotAmexKWmUcAwA4nCe`
- token = `VXnpdcUFWotAmexKWmUcAwA4nCe`

**注意**：`lark-cli docs` 不是 `docx`。`+fetch` 必须用 `--doc` flag 传 token，不支持位置参数。
