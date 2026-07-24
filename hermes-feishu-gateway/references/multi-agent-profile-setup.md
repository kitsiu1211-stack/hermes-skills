# Multi-Agent Profile Setup (Programmatic)

When `hermes setup` can't run in a non-TTY environment (cron, delegated subagent, headless session), drive the Feishu QR registration flow by importing directly from Hermes internals.

## Workflow

### 1. Create Profiles

```bash
hermes profile create pm --clone
hermes profile create marketing --clone
hermes profile create designer --clone
hermes profile create data --clone
```

`--clone` copies model config, .env, SOUL.md, and skills from default.

### 2. Write SOUL.md

Each profile needs role-specific instructions. Key elements to cover:
- Role identity and core capabilities
- Work style and communication preferences
- Scope limitations (which directories/files it can touch)
- Language preference (Chinese for Feishu teams)

### 3. Verify .env

Cloned profiles inherit `.env` from default. Ensure these are set:
```
FEISHU_ALLOW_BOTS=mentions
FEISHU_ALLOW_ALL_USERS=true
FEISHU_GROUP_POLICY=open
```

### 4. QR Registration (Programmatic)

The registration endpoint is `https://accounts.feishu.cn/oauth/v1/app/registration`.

```python
import json, time
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

_ACCOUNTS_URL = "https://accounts.feishu.cn"
_REGISTRATION_PATH = "/oauth/v1/app/registration"

def post_reg(body: dict) -> dict:
    """POST to Feishu registration endpoint. Returns parsed JSON.
    Handles HTTP 400 responses (authorization_pending is a 400)."""
    url = f"{_ACCOUNTS_URL}{_REGISTRATION_PATH}"
    data = urlencode(body).encode("utf-8")
    req = Request(url, data=data,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body_bytes = exc.read()
        if body_bytes:
            try:
                return json.loads(body_bytes.decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                raise exc from None
        raise
```

**Start registration:**
```python
res = post_reg({
    "action": "begin",
    "archetype": "PersonalAgent",
    "auth_method": "client_secret",
    "request_user_info": "open_id",
})
# Returns: device_code, user_code, verification_uri_complete, expires_in, interval
```

**Present QR link to user:**
```python
qr_url = res["verification_uri_complete"]
if "?" in qr_url:
    qr_url += "&from=hermes&tp=hermes"
else:
    qr_url += "?from=hermes&tp=hermes"
```

User opens the link on mobile (Feishu app) to authorize. Multiple registrations can run in parallel — each has its own `device_code`.

**Poll for completion:**
```python
def poll_registration(device_code: str, interval: int = 5,
                      expire_in: int = 3600) -> dict | None:
    deadline = time.monotonic() + expire_in
    while time.monotonic() < deadline:
        res = post_reg({"action": "poll", "device_code": device_code})
        if "client_id" in res:
            return {
                "app_id": res["client_id"],
                "app_secret": res["client_secret"],
                "open_id": res.get("user_info", {}).get("open_id"),
            }
        error = res.get("error", "")
        if error == "access_denied":
            return None  # User declined
        if error == "expired_token":
            return None  # Expired
        # authorization_pending or slow_down → keep polling
        time.sleep(interval)
    return None
```

### 5. Write Credentials to .env

```python
def write_feishu_creds(profile: str, app_id: str, app_secret: str):
    env_path = f"/Users/bytedance/.hermes/profiles/{profile}/.env"
    with open(env_path, "r") as f:
        content = f.read()

    # Replace the cloned default app credentials
    import re
    content = re.sub(r"FEISHU_APP_ID=.*", f"FEISHU_APP_ID={app_id}", content)
    content = re.sub(r"FEISHU_APP_SECRET=.*", f"FEISHU_APP_SECRET={app_secret}", content)

    with open(env_path, "w") as f:
        f.write(content)
```

### 6. Start Gateways

```bash
pm gateway restart
marketing gateway restart
designer gateway restart
data gateway restart
```

### 7. Create Group Chat & Add Bots

1. Create a Feishu group chat
2. Invite human members
3. Settings → Group Bots → Add Bot → select each new bot
4. Verify: `@pm hello` should get a response

## Pitfalls

- **No TTY**: Don't bother with `hermes setup` in headless mode — it detects no TTY and exits immediately. Use the Python import approach above.
- **Wrong endpoint**: Use `accounts.feishu.cn/oauth/v1/app/registration`, NOT `open.feishu.cn/open-apis/authen/v1/device` (404).
- **Content-Type**: Must be `application/x-www-form-urlencoded`, NOT JSON.
- **Profile isolation**: Profiles share the same filesystem. Agents can modify other profiles' files. For strong isolation, deploy separate Hermes instances.
- **`group_sessions_per_user`**: Set to `false` to allow shared session context in group chats.
