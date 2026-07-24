# Feishu Group Chat Operations — Full Recipe

Complete workflow for creating Feishu group chats with multiple bots and adding human members. Updated 2026-06-17 with verified API behavior.

## Create Group (Bots Only)

When you have the app credentials but not the user's correct open_id:

```python
import urllib.request, json

APP_ID = "cli_xxx"
APP_SECRET = "xxx"
CHAT_NAME = "🤖 Team Collaboration"

# 1. Get tenant access token
url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode('utf-8'))["tenant_access_token"]

# 2. Create group with bots
# ⚠️ bot_id_list is UNRELIABLE — see pitfall below
url = "https://open.feishu.cn/open-apis/im/v1/chats?user_id_type=open_id"
payload = json.dumps({
    "name": CHAT_NAME,
    "description": "Multi-agent collaboration space",
    "chat_type": "private",
    "group_message_type": "chat",
    "membership_approval": "no_approval_required",  # anyone can join
    "bot_id_list": [
        "cli_aaa",  # Bot 1 app_id
        "cli_bbb",  # Bot 2 app_id
        "cli_ccc",  # Bot 3 app_id
    ]
}).encode('utf-8')

req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
})

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    chat_id = result["data"]["chat_id"]
    print(f"Group created: {chat_id}")

# 3. ⚠️ ALWAYS VERIFY: bot_id_list may not have worked
import time; time.sleep(2)
url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members?member_id_type=open_id&page_size=20"
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req) as resp:
    members = json.loads(resp.read().decode('utf-8'))
print(f"Members after creation: {members['data']['member_total']}")
# If member_total is 0 or less than expected, bot_id_list failed — use fallback below
```

**⚠️ `bot_id_list` is UNRELIABLE.** In multiple tests (2026-06-17), `chat.create` succeeded (returned chat_id) but the member list was **empty** — bots listed in `bot_id_list` were NOT actually added. Always verify with `GET /chats/{chat_id}/members` after creation.

## Fallback: Add Bots After Creation

When `bot_id_list` doesn't add bots, you have three options:

### Option A: meJoin (Public Groups Only)

Each bot joins itself via `meJoin`. **Only works for public groups** (`chat_type: "public"`).

```python
# For each bot, using its OWN token:
url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members/me_join"
req = urllib.request.Request(url, data=b'', headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {bot_token}'
})
req.method = 'PATCH'
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
```

**Requirements:**
- Group must be `chat_type: "public"` (private groups return `232008`)
- Bot must have `im:chat.members:write_only` scope
- Each bot joins using its OWN token

### Option B: Add by open_id (Requires Known IDs)

The group-creating bot adds each bot by open_id. Requires knowing the bot's open_id **as seen by the creating app**.

```python
# Must use open_ids that are valid for THIS app's namespace
url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members?member_id_type=open_id"
payload = json.dumps({
    "id_list": [
        "ou_xxx_from_this_app",  # Bot A's open_id (for this app)
        "ou_yyy_from_this_app",  # Bot B's open_id (for this app)
    ]
}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
})
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
```

**Gotcha:** Bots **cannot look up other bots** via `contact/v3/users/batch_get_id` — the contact API only returns users within the app's contacts scope, and bots are excluded. This means cross-bot open_id resolution is nearly impossible via API alone. The only reliable ways to get cross-app open_ids:

1. **Use `bot/v3/info` on each bot** to get its own open_id, then have the group-creating bot attempt to add it. This will fail with `99992361 open_id cross app` because the open_id is from the bot's own namespace, not the creating app's.
2. **Manual resolution** — create the group in Feishu client UI.

### Option C: Manual Group Creation (Most Reliable)

When API routes are exhausted, create the group in the Feishu client UI:
1. Open Feishu → New Group Chat
2. Name it → Add members by searching bot display names
3. This bypasses all API permission scope and cross-app open_id issues

## Add Human Members (With Correct open_id)

When adding human users, you MUST resolve their open_id for the specific app that owns the group:

```python
# 1. Look up user's open_id for THIS app
url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id"
payload = json.dumps({"emails": ["user@example.com"]}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
})

with urllib.request.urlopen(req) as resp:
    user_data = json.loads(resp.read().decode('utf-8'))
    # ⚠️ User may not be found if app lacks contact:user.id:readonly
    user_list = user_data.get("data", {}).get("user_list", [])
    if user_list and "open_id" in user_list[0]:
        correct_open_id = user_list[0]["open_id"]
    else:
        print("User not found — app may lack contact permissions")
        # Fallback: manual join

# 2. Add user to group
url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members?member_id_type=open_id"
payload = json.dumps({"id_list": [correct_open_id]}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
})

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print(f"Members added: {result}")
```

## Manual Join Fallback

When the creating app lacks `contact:user.id:readonly` and you can't look up the user's open_id:

1. Create the group with `membership_approval: "no_approval_required"`
2. Tell the user the group name — they can search and join in the Feishu client
3. Once joined, send a welcome message to verify connectivity

## Send Welcome Message

```python
# POST /open-apis/im/v1/messages?receive_id_type=chat_id
msg_content = {
    "zh_cn": {
        "title": "👋 Welcome",
        "content": [
            [{"tag": "text", "text": "Group is ready!\n"}],
            [{"tag": "text", "text": "Members: Bot1, Bot2, Bot3"}],
        ]
    }
}

payload = json.dumps({
    "receive_id": chat_id,
    "msg_type": "post",
    "content": json.dumps(msg_content)
}).encode('utf-8')

url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
})

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print(f"Message sent: msg_id={result['data']['message_id']}")
```

## Permission Setup Checklist

Before any group operation, ensure the app has these scopes (in Open Platform console → Permissions → app identity permissions):

| Operation | Scope | Notes |
|-----------|-------|-------|
| Create group | `im:chat` or `im:chat:create` | Also needs `im:chat:create_by_user` for user-identity mode |
| Add members | `im:chat` or `im:chat.members:write_only` | Required for both `chatMembers.create` and `meJoin` |
| Delete group | `im:chat` or `im:chat:delete` | |
| Lookup user by email | `contact:user.id:readonly` | Needed to resolve cross-app open_id |
| Send messages | `im:message` | Usually auto-granted |

**After granting:** Click **「发布」** (Publish) — scopes in draft don't take effect.

## Error Reference

| Error Code | Meaning | Fix |
|-----------|---------|-----|
| 99992361 `open_id cross app` | open_id belongs to a different app's namespace | Use `batch_get_id` with this app's token; for bots, fallback to manual creation |
| 99991672 `Access denied` | Missing scope | Grant scope in console + publish |
| 232008 `chat is not public` | `meJoin` only works for public groups | Set `chat_type: "public"` or add via `chatMembers.create` |
| 230002 `Bot/User can NOT be out of the chat` | Bot not a member | No API to join existing chats; use manual methods |
| 99992351 `id not exist` | Wrong ID type (e.g., app_id used as open_id) | Use correct open_id for the target app |
| `contact:user.id:readonly` required | Can't look up users | Grant scope; fallback to manual join |
