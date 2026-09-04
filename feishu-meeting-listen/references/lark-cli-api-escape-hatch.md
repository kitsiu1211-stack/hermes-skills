# lark-cli api — Raw HTTP Escape Hatch

当 `lark-cli <domain> <subcommand>` 没有对应命令时，用 `lark-cli api` 直接调用飞书 Open API 的任意端点。

## 基本语法

```bash
lark-cli api GET "/open-apis/drive/v1/files/{file_token}/comments?file_type=docx&page_size=20" --as user
lark-cli api POST "/open-apis/..." --data '{"key":"value"}' --as user
```

## 已验证的端点

| 端点 | 用途 | 备注 |
|------|------|------|
| `GET /open-apis/drive/v1/files/{token}/comments?file_type=docx` | 列出文档评论 | 用于文档 @ 提及监控 |
| `GET /open-apis/drive/v1/files/{token}/comments?is_whole=true` | 仅整文档评论 | 过滤内嵌评论 |

## 发现

- `lark-cli docs` 没有 `+comments` 子命令，必须走 `lark-cli api`
- `lark-cli api` 自动使用 `lark-cli auth` 的 token，无需单独管理凭据
- 返回 JSON 结构与飞书 Open API 文档一致

## 使用场景

```bash
# 文档评论轮询（用于 cron job 检测 @ 提及）
lark-cli api GET "/open-apis/drive/v1/files/WCkhdGFCroIvazxcVtDcntzjnpe/comments?file_type=docx&page_size=20&is_whole=true" --as user
```
