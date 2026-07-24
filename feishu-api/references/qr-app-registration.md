# Feishu QR App Registration API

Programmatically create Feishu enterprise internal apps (bots) via the QR code device-code flow. Used by Hermes `hermes gateway setup` → `_setup_feishu()` but callable standalone for bulk profile bot creation.

## API Endpoint

```
POST https://accounts.feishu.cn/oauth/v1/app/registration
Content-Type: application/x-www-form-urlencoded
```

For Lark (international): `https://accounts.larksuite.com/oauth/v1/app/registration`

## Flow

### Step 1: Begin Registration

```python
import json, urllib.request
from urllib.request import Request, urlopen
from urllib.parse import urlencode

def post_reg(body):
    url = "https://accounts.feishu.cn/oauth/v1/app/registration"
    data = urlencode(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

res = post_reg({
    "action": "begin",
    "archetype": "PersonalAgent",
    "auth_method": "client_secret",
    "request_user_info": "open_id",
})
# Returns: device_code, user_code, verification_uri_complete, expires_in, interval
```

### Step 2: User Scans QR

The `verification_uri_complete` field contains the URL the user opens on their phone (Feishu app). Append `&from=hermes&tp=hermes` for Hermes tracking:

```python
qr_url = res["verification_uri_complete"]
if "?" in qr_url:
    qr_url += "&from=hermes&tp=hermes"
else:
    qr_url += "?from=hermes&tp=hermes"
```

### Step 3: Poll for Completion

```python
import time

def poll(device_code, interval=5, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = post_reg({"action": "poll", "device_code": device_code})
        if "app_id" in res:
            return {"app_id": res["app_id"], "app_secret": res["app_secret"]}
        error = res.get("error", "")
        if error == "access_denied":
            return None
        if error in ("authorization_pending", "slow_down"):
            time.sleep(interval)
            continue
        time.sleep(interval)
    return None
```

### Step 4: Write to Hermes .env

```python
env_path = f"~/.hermes/profiles/{profile}/.env"
# Replace FEISHU_APP_ID and FEISHU_APP_SECRET lines
```

## Critical Pitfalls

### ⚠️ Sequential Polling Causes Timeouts

When creating multiple bots, **poll all device codes in parallel** — not sequentially. Sequential polling means the Nth bot waits for all previous polls to complete, and by then its device code may have expired.

**Correct approach:** Start all registrations first (all `begin` calls), present all QR links to user, then poll all device codes concurrently (e.g., round-robin in a single loop).

### ⚠️ Device Code Expiry

Device codes expire after `expires_in` seconds (typically 600). Start polling immediately after the user confirms they've scanned. Don't wait between `begin` and polling.

### ⚠️ Wrong API Path

The correct path is `/oauth/v1/app/registration` on `accounts.feishu.cn`, NOT `/accounts/v3/registration/`. The wrong path returns 404.

### ⚠️ Poll Response Handling

The poll endpoint returns JSON even on 4xx errors (e.g., `authorization_pending` as 400). Always parse the response body regardless of HTTP status:

```python
from urllib.error import HTTPError

try:
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())
except HTTPError as exc:
    body_bytes = exc.read()
    if body_bytes:
        return json.loads(body_bytes.decode("utf-8"))
    raise
```

## No "List Apps" API

There is **no public API** to list all apps under a Feishu tenant. The only way to get app credentials is:
1. During registration (the `poll` response returns them)
2. Manually from the Open Platform console (https://open.feishu.cn/app)
3. From .env files if previously saved

After registration completes, save `app_id` and `app_secret` immediately — they cannot be retrieved later via API.
