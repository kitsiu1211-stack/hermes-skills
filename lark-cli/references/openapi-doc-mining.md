# 飞书 OpenAPI 文档挖掘（CLI 没封装某能力时）

场景：用户要的能力 CLI 里没有对应的 `+command`（例：批量撤回消息、群内撤回他人消息、管理类接口）。
**不要猜路径、也不要凭印象答**，按下面三级阶梯从官方文档挖到规范，再用 `lark-cli api` 裸调。

## 阶梯（全程 curl 即可，无需登录、无需授权）

1. `https://open.feishu.cn/llms.txt` — 顶层索引，列出所有模块文档链接（`llms-messaging.txt`、`llms-group-chat.txt`、`llms-admin.txt`、`llms-api-call-guide.txt` …）
2. `https://open.feishu.cn/llms-docs/zh-CN/llms-<module>.txt` — 模块索引，一行一个能力，含 HTTP 方法 / 路径 / 权限 / 限频 摘要，外加单接口文档链接
3. `https://open.feishu.cn/document/server-docs/<path>.md` — 单接口文档。**URL 末尾补一个 `.md` 就能拿干净的 Markdown 全文**（方法、路径、路径参数、请求体字段、响应、所需权限、错误码一应俱全），比读网页版省事得多

Lark 品牌把域名换成 `open.larksuite.com`。

## 实战：批量撤回消息（2026-10-15 实测）

```bash
curl -s https://open.feishu.cn/llms.txt > /tmp/llms.txt
grep -inE '消息|撤回' /tmp/llms.txt | head                      # → llms-docs/zh-CN/llms-messaging.txt
curl -s https://open.feishu.cn/llms-docs/zh-CN/llms-messaging.txt > /tmp/llms-msg.txt
grep -inE '撤回|删除' /tmp/llms-msg.txt                         # → 命中「批量撤回消息」+ 文档链接
curl -s https://open.feishu.cn/document/server-docs/im-v1/batch_message/delete.md | head -60
```

拿到结论：`DELETE /open-apis/im/v1/batch_messages/:batch_message_id`，只能撤「批量发送消息」接口发出的消息、异步有延迟、限频 1000 次/分钟（50 次/秒）、权限 `im:message:send_multi_users` 或 `im:message:send_multi_depts`。
整套「撤回 / 删除 / 存储口径」边界表见 `references/im-message-recall-and-delete.md`。

## grep 技巧

模块索引文件里 `grep -inE '<关键词>'` 一行定位目标能力，命中行自带文档链接 → 直接 curl `.md`。比逐条读完整个模块索引快一个数量级。

## 相关

- `lark-openapi-explorer` skill（用户自有，autonomous curator 不可写）讲同一套阶梯的 WebFetch 版本；本文件是 curl 版 + 实测实例，两者内容有重叠，合并需用户在前台 `hermes curator adopt lark-openapi-explorer`。
- CLI 已有封装时**先 `lark-cli <domain> --help`**，有 `+command` 就别挖文档。
