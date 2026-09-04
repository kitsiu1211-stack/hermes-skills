# lark-cli api 裸调模式

当 lark-cli 没有内置 `+subcommand` 时，用 `lark-cli api <method> <path>` 直接调飞书 Open API。

## 发现（2026-07-29）

lark-cli 1.0.79 没有文档评论的内置命令，但通过 `api` 子命令可以直接访问飞书 Drive Comments API：

```bash
# 列文档评论（全部类型）
lark-cli api GET "/open-apis/drive/v1/files/<doc_token>/comments?file_type=docx&page_size=20" --as user

# 仅全文档评论
lark-cli api GET "/open-apis/drive/v1/files/<doc_token>/comments?file_type=docx&page_size=20&is_whole=true" --as user
```

## 事件系统发现

```bash
lark-cli event list  # 列出所有可用事件
```

当前无 `drive.file.comment.created` 事件。可用事件包括：
- `board.whiteboard.updated_v1` — 画板更新
- `minutes.minute.generated_v1` — 妙记生成
- `vc.meeting.*` — 会议生命周期事件
- `im.message.receive_v1` — IM 消息

## 凭证状态查询

```bash
lark-cli auth status  # 查看当前 token、scope、过期时间
```

输出包含 `docx:document.comment:read` / `docs:document.comment:create` 等 scope 状态。

## 注意事项

- `--as user` 需要用户 OAuth 授权过对应 scope
- `api` 子命令对所有飞书 Open API endpoint 通用
- JSON 输出可直接 pipe 给 `python3.11 -c` 解析
