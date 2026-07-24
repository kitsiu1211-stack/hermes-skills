# lark-cli Auth Flow — Reproduction Recipe

## Exact command and expected output

### Step 1: Initiate device flow

```bash
/Users/bytedance/.npm-global/bin/lark-cli auth login --no-wait --recommend --json
```

**Expected output (example):**

```json
{
  "device_code": "OIP_...",
  "expires_in": 600,
  "hint": "Show verification_url to the user exactly as returned...",
  "verification_url": "https://accounts.feishu.cn/oauth/v1/device/verify?flow_id=ONIIWI9wW7pl...&user_code=XXXX-XXXX"
}
```

### Step 2: Present URL to user

Show `verification_url` verbatim in a fenced code block. The user opens it in a browser and clicks "授权" (Authorize).

### Step 3: Poll for completion

```bash
/Users/bytedance/.npm-global/bin/lark-cli auth login --device-code '<device_code>'
```

Blocks until authorized or timeout (600s).

## Failure modes observed

| Symptom | Cause | Fix |
|---------|-------|-----|
| "创建智能助手" page instead of auth | Used Hermes registration flow (`_begin_registration`) instead of `lark-cli auth login` | Use `lark-cli auth login --recommend` |
| `--no-wait` returns "please specify the scopes" | `--recommend` flag not combined with `--no-wait` | Use `--no-wait --recommend --json` |
| Background process has no output / `command not found` | PATH differs in background sessions | Use full path: `/Users/bytedance/.npm-global/bin/lark-cli` |
| Device code expired after timeout | Each restart invalidates previous code | Always re-initiate with fresh `--no-wait` call after timeout |

## URL formats (for identification)

- **lark-cli device verify:** `https://accounts.feishu.cn/oauth/v1/device/verify?flow_id=...&user_code=...`
- **Hermes registration (NOT this):** `https://open.feishu.cn/page/launcher?user_code=...` or `https://accounts.feishu.cn/oauth/v1/app/registration`
