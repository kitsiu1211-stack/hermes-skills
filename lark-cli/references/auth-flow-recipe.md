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

**Always also render a QR code**（手机上扫码比复制长 URL 快得多；CLI 的 hint 也强制要求）：

```bash
cd /tmp && lark-cli auth qrcode "<verification_url>" --output /tmp/lark_auth_qr.png
# → {"file_path":"/private/tmp/lark_auth_qr.png","ok":true}
```

然后在回复里 `MEDIA:/tmp/lark_auth_qr.png` 附图，URL 写在上方。

⚠️ **`auth qrcode` 的 URL 是位置参数，没有 `--url` flag。** 写成 `--url "<url>"` 不报错，
只是返回 `ok:false` 的 notice JSON 且**不生成文件**（`ls` 才会发现没有 png）。参数说明见
`lark-cli auth qrcode --help`；`--output` 是必需的，路径必须在 `cwd` / `/tmp` / `~/files` 之下。

### 补单个 scope 的变体（不是 `--recommend` 全量重授权）

```bash
lark-cli auth login --scope "im:message.send_as_user" --no-wait --json
# → device_code + verification_url（600s 有效）
# 用户扫码/点链接授权回来后：
lark-cli auth login --device-code '<device_code>'
```

- CLI **不会**在发起阶段校验 scope 是否存在/可授予，所以拿到 device_code ≠ 能授权成功；
  真实结果只在 `--device-code` 那一步揭晓。对外说话按这个口径（可以发起、不许承诺）。
- 一次只能补一个 `--scope`；需要多个时重复该流程或改用 `--domain <domain>`。
- 提示屏传给用户的原始 URL 不要 URL-encode / 加空格标点，原样贴。

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
| `auth qrcode --url "…"` 返回 `ok:false` 且无 png 文件 | URL 是**位置参数**，写了 `--url` 会被当成未知参数静默忽略 | `lark-cli auth qrcode "<url>" --output /tmp/qr.png`（`--output` 必填，路径限 cwd / `/tmp` / `~/files`） |
| `missing required scope(s): im:message.send_as_user` | `--as user` 发消息但用户 token 没有该 scope | 按上面的「补单个 scope 变体」走设备码授权；不要改回 bot 身份硬发（服务台只认用户消息） |

## URL formats (for identification)

- **lark-cli device verify:** `https://accounts.feishu.cn/oauth/v1/device/verify?flow_id=...&user_code=...`
- **Hermes registration (NOT this):** `https://open.feishu.cn/page/launcher?user_code=...` or `https://accounts.feishu.cn/oauth/v1/app/registration`
