# 飞书 CLI 实战 103 例

涵盖 `lark-cli`（飞书客户端）和 `lark-c360`（客户 360），按使用频率排序。

## 一、vc — 视频会议（14 例）

| # | 命令 | 用途 |
|---|------|------|
| 1 | `lark-cli vc +meeting-list-active --as user` | 查当前活跃会议 |
| 2 | `lark-cli vc +meeting-join --meeting-number <no> --as bot --json` | bot 入会 |
| 3 | `lark-cli vc +meeting-join --meeting-number <no> --as user --json` | user 入会 |
| 4 | `lark-cli vc +meeting-events --as user --meeting-id <id> --page-all --json` | 全量拉事件 |
| 5 | `lark-cli vc +meeting-events --as user --meeting-id <id> --page-token <token>` | 分页拉 |
| 6-14 | 事件解析: participant_joined / transcript_received / chat_received / participant_left / leave_reason | 字幕+聊天+进出 |

## 二、im — 消息群聊（22 例）

| # | 命令 | 用途 |
|---|------|------|
| 15 | `lark-cli im +messages-send --as bot --chat-id <id> --msg-type interactive --content '<json>'` | bot 发卡片 |
| 16 | `lark-cli im +messages-send --as user --chat-id <id> --msg-type post` | user 发富文本 |
| 17 | `lark-cli im +chat-members-list --chat-id <id> --member-types bot --page-all` | 列群 bot |
| 18 | `lark-cli im +chat-messages-list --chat-id <id> --sort desc --page-size 10` | 拉最近消息 |

### Agent 群 bot ID 速查

| bot | open_id |
|-----|---------|
| 浪子 | ou_9b18941c79156bd08a70431dc5dcf7f9 |
| 样板间小管家 | ou_459dac1c298c48d280a3ea3260aac80e |
| ISV 业务助手 | ou_abdda0c6cd5e362bca041cb3dbd88f86 |
| Aime | ou_b33d3f6e144a9730db025d288c81212c |
| 飞书 CodeM | ou_eddd322192a9443949686c7896c3ad93 |
| TRAE ASSISITANT | ou_1d0748623c4f90fd2f4a92b6a6734b45 |
| 马斯克 | ou_ec816541777287f722b0896287c4486a |
| TC 交付数字员工 | ou_c9cd24728752004e848f099d2b448d29 |
| 客户 AI 场景登记表 | ou_0ef4cd7a1f7ce714d503fa244edf95c0 |

### 飞书卡片要素速查

| 元素 | JSON |
|------|------|
| 宽屏 | `"config": {"wide_screen_mode": true}` |
| 蓝色 header | `"template": "blue"` |
| 富文本 | `{"tag": "div", "text": {"tag": "lark_md", "content": "..."}}` |
| 分隔线 | `{"tag": "hr"}` |
| 备注 | `{"tag": "note", "elements": [{"tag": "plain_text", "content": "..."}]}` |

### 卡片发送模板（Python OpenAPI）

```python
import json, urllib.request
# 1. token
req = urllib.request.Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id":"APP_ID","app_secret":"APP_SECRET"}).encode(),
    headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req) as r: token = json.loads(r.read())['tenant_access_token']
# 2. card JSON
card = {"config":{"wide_screen_mode":True},"header":{"title":{"tag":"plain_text","content":"标题"},"template":"blue"},"elements":[...]}
# 3. send
msg = {"receive_id":"<chat_id>","msg_type":"interactive","content":json.dumps(card)}
req = urllib.request.Request("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=json.dumps(msg).encode(),
    headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'})
```

## 三、apps — 妙搭（10 例）

| # | 命令 | 用途 |
|---|------|------|
| 37 | `lark-cli apps +create --name "xxx" --app-type html` | 创建应用 |
| 38 | `lark-cli apps +html-publish --app-id <id> --path ./index.html` | 发布 HTML |
| 39 | `lark-cli apps +access-scope-set --app-id <id> --scope=public --require-login=false` | 公开访问 |

## 四、C360 CLI（25 例）

| # | 命令 | 用途 |
|---|------|------|
| 57 | `lark-c360 search all --keyword "<客户>" --limit 5 --json` | 搜索客户+商机 |
| 69 | `lark-c360 follow_up +recent --account-id <id> --limit 3 --json` | 查最近跟进 |
| 72 | `lark-c360 contact list --filter-json '...' --limit 10 --json` | 查联系人 |

### 数据过滤规则
- ✅ 输出：非 Closed Lost 商机、30/90 天内续约、进行中工单
- ❌ 跳过：Closed Lost、90 天外续约、已完成工单、已归档协议

## 五、实战组合（22 例）

### 会议全链路
`vc +meeting-list-active` → 提取客户名 → `c360 search all` → `follow_up +recent` → DM 卡片

### 会前准备
会议标题 → 客户名 → C360 查商机+跟进+联系人 → 政策搜索 → 延展话题 → 飞书卡片

### Cron 自动化
- 去重: `meeting_state.json` — ongoing/ended
- 上下文: `client_context.json` — 跨会议记忆
- 调度: `1,6,11,16,21,26,31,36,41,46,51,56 * * * *` 错开整点

### Agent 协作
`im +chat-messages-list` 读消息 → `im +messages-send` @bot 分派

## 六、通用模式（4 例）

- JSON 管道: `--json | python3 -c "import sys,json;..."`  
- 容错: `2>/dev/null || echo 'fallback'`  
- 后台: launchd / `&` / crontab  
- 多卡分片: elements ≤ 10, 末尾标注 "卡片 N/M"
