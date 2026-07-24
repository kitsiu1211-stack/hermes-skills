---
name: hermes-feishu-gateway
description: Hermes Feishu/Lark gateway registration, auth troubleshooting, and platform internals. Use when debugging Feishu OAuth, device-flow, token refresh, or gateway setup issues.
---

# Hermes Feishu Gateway

## Trigger
Load this skill when:
- Troubleshooting Feishu/Lark OAuth device flow registration
- Debugging Feishu gateway auth token issues
- Setting up or re-registering the Hermes Feishu platform connection
- The user asks about Feishu gateway internals

## Source of Truth
The canonical reference for Feishu platform integration is:
`gateway/platforms/feishu.py` (~5058 lines)

Key constants and functions:

| Name | Location | Purpose |
|------|----------|---------|
| `_ONBOARD_ACCOUNTS_URLS` | L244-247 | `feishu` → `https://accounts.feishu.cn`, `lark` → `https://accounts.larksuite.com` |
| `_REGISTRATION_PATH` | L252 | `/oauth/v1/app/registration` |
| `_begin_registration()` | L4783-4806 | Start device flow, returns `device_code`, `user_code`, `verification_uri_complete`, `interval`, `expire_in` |
| `_poll_registration()` | L4809-4869 | Poll until user authorizes; returns `app_id`, `app_secret`, `domain`, `open_id` on success |
| `_post_registration()` | L4745-4765 | POST form-encoded to `{base_url}/oauth/v1/app/registration` |

## Device Flow Registration (the correct way)

**CRITICAL**: Hermes uses `https://accounts.feishu.cn/oauth/v1/app/registration` — NOT the standard Feishu Open API device flow (`open.feishu.cn/open-apis/authen/v1/device`). The standard endpoint returns 404 for Hermes' use case.

### Step 1: Begin
```bash
curl -s -X POST 'https://accounts.feishu.cn/oauth/v1/app/registration' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'action=begin&archetype=PersonalAgent&auth_method=client_secret&request_user_info=open_id'
```

Returns: `device_code`, `user_code`, `verification_uri`, `verification_uri_complete`, `expires_in` (3600s), `interval` (5s).

### Step 2: User authorizes
Send the user `verification_uri_complete` (e.g., `https://open.feishu.cn/page/launcher?user_code=XXXX-XXXX`). They open it in browser and grant permission.

### Step 3: Poll
```bash
curl -s -X POST 'https://accounts.feishu.cn/oauth/v1/app/registration' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'action=poll&device_code=<DEVICE_CODE>&tp=ob_app'
```

Poll every `interval` seconds until `expires_in` deadline. Success returns `client_id` (app_id), `client_secret` (app_secret), `user_info.open_id`.

### Terminal errors during poll
- `error: "access_denied"` — user declined
- `error: "expired_token"` — device_code expired; restart from Step 1
- `error: "authorization_pending"` — user hasn't acted yet; keep polling (returns as HTTP 400)

## Pitfalls

1. **Wrong endpoint**: Do NOT use `open.feishu.cn/open-apis/authen/v1/device` — it returns 404. Use `accounts.feishu.cn/oauth/v1/app/registration`.
2. **Content-Type**: Must be `application/x-www-form-urlencoded`, NOT `application/json`.
3. **Domain auto-detection**: The poll response may include `user_info.tenant_brand: "lark"` — if so, switch to `accounts.larksuite.com` for subsequent polls.
4. **Open Platform requires QR login**: `open.feishu.cn` login pages use QR-code scanning (飞书移动端扫码). There is no username/password fallback. Browser-based automation cannot log in — prefer API-based approaches or local log inspection instead.
5. **Event subscription API returns 404**: `GET /open-apis/event/v1/app/event_subscription` returns 404. The event subscription status cannot be queried via the REST API directly. Use the local gateway log inspection approach below.

## Diagnosing Event Channel Conflicts (远程实例占事件通道)

When the user reports "remote event consumer blocking" — a Hermes gateway can't start because another instance (cloud, another machine, stale process) is consuming all event channels for an app.

### Don't try
- ❌ Logging into `open.feishu.cn` in a browser — requires QR code scan (see Pitfall #4)
- ❌ `GET /open-apis/event/v1/app/event_subscription` — returns 404 (see Pitfall #5)

### Do this instead: inspect local gateway logs
```bash
# 1. Check if local gateway is running
ps aux | grep -i hermes | grep -v grep

# 2. Check WebSocket connection status (look for "connected to wss://msg-frontier")
grep -i "connected to wss" ~/.hermes/logs/gateway.log | tail -5

# 3. Check for recent event flow (proof the channel is alive)
tail -50 ~/.hermes/logs/gateway.log | grep -i "message_type: event"

# 4. Check error log for subscription conflicts
grep -iE "conflict|duplicate|block|subscription" ~/.hermes/logs/gateway.error.log | tail -10
```

### Interpreting results
- **WebSocket connected + events flowing** → local gateway has the channel, remote instance is gone. Done.
- **WebSocket connected but no recent events** → channel is held but idle. The remote instance may have been killed; the local one just hasn't seen traffic yet.
- **No WebSocket connection, no errors** → gateway may not be running at all. Start it with `hermes gateway run`.
- **Errors about "conflict" or "duplicate"** → remote instance is still active. The user needs to kill it from the Open Platform UI (Event Subscriptions → 在线实例).

### Gateway log paths
| File | Purpose |
|------|---------|
| `~/.hermes/logs/gateway.log` | Main gateway log: connections, events, message handling |
| `~/.hermes/logs/gateway.error.log` | Errors: subscription conflicts, handler failures |

## Group Bot Discovery

When working with Feishu group chats that contain multiple bots:

- `chatMembers.get` API **filters out all robot members** — returns only human users. Do NOT rely on it to discover bots.
- System invite messages (`msg_type: system`) do NOT expose the invited member's `open_id` — only the display name.
- **Workaround**: Analyze message history — extract unique `app_id`s from `sender.id` in message objects. Each `app_id` (format: `cli_*`) represents a distinct bot agent.
- `application.v6.application.list` requires `admin:app.info:readonly` scope (may need additional permission grant).
- For full multi-agent group management patterns, see `feishu-group-chat` skill.

## Multi-Agent Profile Setup (Programmatic)

When setting up multiple Hermes profiles for a Feishu agent team, the interactive `hermes setup` wizard requires a real TTY. Use the Python import approach instead to drive the registration flow programmatically. Full recipe in `references/multi-agent-profile-setup.md`.

### Starting Multiple Profile Gateways

After writing `.env` files for each profile, start all gateways in parallel background processes:

```bash
# Start each profile's gateway in background
hermes --profile pm gateway run &
hermes --profile designer gateway run &
hermes --profile marketing gateway run &
hermes --profile data gateway run &
```

Or from within a Hermes session using the terminal tool:
```python
terminal(command="hermes --profile pm gateway run", background=True)
terminal(command="hermes --profile designer gateway run", background=True)
# ... etc
```

Profile gateways are independent — each uses its own port, config, sessions, and memory.

### Creating the Multi-Agent Group Chat

After gateways are running, create a shared group chat containing all bots:

1. Pick one bot as the "group creator" (e.g., PM)
2. Use its app credentials to call `POST /im/v1/chats` with all `bot_id_list` values
3. Add human members — **beware of the cross-app open_id pitfall**: use `batch_get_id` to resolve the user's open_id for the creating app

Full recipe with code and permission requirements: see `feishu-api` skill → `references/group-chat-operations.md`.
