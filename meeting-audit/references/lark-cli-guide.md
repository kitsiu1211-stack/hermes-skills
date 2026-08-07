# 飞书操作铁律

全部走 lark-cli，**禁止用 browser 读飞书文档/页面**。

## lark-cli 覆盖的 23 个域

| 域 | 能力 |
|----|------|
| docs | 文档读写、历史版本、媒体插入/下载 |
| wiki | 空间/节点增删改查、移动复制 |
| calendar | 日程创建/搜索/忙闲/会议室预订 |
| im | 消息发送(text/markdown/post/卡片)、群管理、搜索 |
| vc | 活跃会议列表、入会/离会、会议事件(字幕/弹幕) |
| base | 多维表格：表/字段/记录/视图/仪表盘 |
| task | 任务创建/完成/分配/评论 |
| mail | 邮件草稿/发送/转发/HTML检查 |
| sheets | 单元格读写/样式/搜索替换/合并 |
| slides | 创建演示文稿、页面替换、截图 |
| markdown | Markdown 创建/读写/patch/diff |
| mindnotes | 思维笔记节点创建/列表 |
| minutes | 妙记详情/摘要/字幕/转写/下载 |
| okr | OKR 目标/关键结果/进度 |
| whiteboard | 白板查询/更新(mermaid/plantuml) |
| drive | 文件/文件夹管理、上传下载、导入导出 |
| contact | 用户信息查询/搜索 |
| event | 实时事件流消费 |
| apps | 妙搭部署/发布/自动化/分析 |
| approval | 审批实例/任务管理 |
| attendance | 考勤记录 |

## 高频命令

```bash
# 读文档
lark-cli docs +fetch --doc <url或token> --doc-format markdown

# 读 wiki（先取 obj_token）
lark-cli wiki +node-get --node-token <url> --jq '.data.obj_token'
lark-cli docs +fetch --doc <obj_token> --doc-format markdown

# 搜妙记
lark-cli minutes +search --as user --query <关键词>
```

## 已确认的坑

- `lark-cli docs +fetch` 需要 `--doc` flag，不接受 positional arg
- wiki 的 `+node-get` 返回元数据不含正文，需再调 `+fetch`
- 飞书卡片 `<font color='blue'>` 单引号报错，用 `<font color=blue>`
