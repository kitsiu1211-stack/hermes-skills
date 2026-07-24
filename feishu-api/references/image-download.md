# Feishu Image/File Download from Messages

## The Correct Endpoint

Feishu has **two** image-related API endpoints, and they are NOT interchangeable:

| Endpoint | Purpose | Works for message images? |
|----------|---------|--------------------------|
| `GET /im/v1/images/{image_key}` | Download images **sent by the current app** | ❌ Returns 234001 or 234008 for images sent by users/other bots |
| `GET /im/v1/messages/{message_id}/resources/{file_key}?type=image` | Download **any** image/file attached to a message | ✅ The correct way |

## Full Recipe: Download Image from a DM/Group Message

### Step 1: Find the image_key and message_id

List messages in the chat/thread to find the image:

```bash
feishu-cli exec im.v1.message.list --params '{
  "params": {
    "container_id_type": "chat",
    "container_id": "<chat_id>",
    "page_size": 10,
    "sort_type": "ByCreateTimeAsc"
  }
}'
```

For thread replies, use `container_id_type: "thread"` and the `thread_id` (omt_ prefix).

The response will contain messages with `msg_type: "post"` — parse `body.content` JSON to find `image_key` in the nested `content` array. Record both the `message_id` (om_ prefix) and the `image_key` (img_v3_ prefix).

### Step 2: Get tenant access token

```bash
TOKEN=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"<app_id>","app_secret":"<app_secret>"}' | jq -r '.tenant_access_token')
```

Credentials are in `~/.feishu-cli/config.yaml`.

### Step 3: Download the image

```bash
curl -s -o /tmp/output.png \
  -H "Authorization: Bearer $TOKEN" \
  "https://open.feishu.cn/open-apis/im/v1/messages/<message_id>/resources/<image_key>?type=image"
```

The response body is the raw binary file (not JSON). Check with `file /tmp/output.png`.

## File Types

The `type` query parameter accepts: `image`, `file`, `audio`, `media`. Same endpoint for all message resources.

## Pitfalls

1. **`/im/v1/images/{key}` always fails for message images.** This endpoint is for images uploaded by the app itself (e.g., for bot avatars or card images), not for images attached to messages by users or other bots. Error codes: 234001 (invalid param) or 234008 (not the resource sender).

2. **The resource endpoint returns raw binary, not JSON.** Don't try to `jq` parse the output — it's the raw file bytes. Check with `file` command to verify the format.

3. **No scope beyond `im:message` is needed.** The resource download uses the same tenant access token as other message APIs.
