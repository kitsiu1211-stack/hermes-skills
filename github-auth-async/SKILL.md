---
name: github-auth-async
description: "GitHub authentication when the user is on a messaging platform (Feishu, Slack, etc.) and can't interact with the terminal in real-time. Covers device flow via curl, scope pitfalls, and token exchange."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [GitHub, Authentication, gh-cli, Device-Flow, Async, Feishu]
    related_skills: [github-auth]
---

# GitHub Async Authentication (Chat Platforms)

## When to Use

When the user is on a messaging platform (Feishu, Slack, Telegram, etc.) and can't interact with the terminal in real-time, `gh auth login --web` will time out before they can enter the one-time code. Use the two-phase curl-based device flow instead.

**Triggers:**
- User says "授权", "login to GitHub", or similar in a chat context
- `gh auth login --web` times out with "Command timed out"
- User needs GitHub auth but isn't on a desktop where they can see the terminal in real-time

## Phase 1: Request a Device Code

```bash
# gh CLI's OAuth app client_id (stable — don't change)
CLIENT_ID="178c6fc778ccc68e1d6a"

RESP=$(curl -s -X POST https://github.com/login/device/code \
  -H "Accept: application/json" \
  -d "client_id=$CLIENT_ID" \
  -d "scope=repo,workflow,read:org")

USER_CODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_code'])")
DEVICE_CODE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['device_code'])")
EXPIRES=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['expires_in'])")

echo "User code: $USER_CODE  (expires in ${EXPIRES}s)"
# Save DEVICE_CODE for phase 2
```

Present the `USER_CODE` and `https://github.com/login/device` link to the user. **Block — do not proceed to phase 2 until the user explicitly confirms they've completed the browser step.**

## Phase 2: Exchange for Access Token

Run only after user confirmation:

```bash
TOKEN=$(curl -s -X POST https://github.com/login/oauth/access_token \
  -H "Accept: application/json" \
  -d "client_id=$CLIENT_ID" \
  -d "device_code=$DEVICE_CODE" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "$TOKEN" | gh auth login --with-token
gh auth setup-git
gh auth status
```

`gh auth setup-git` configures git's credential helper so that `git push` / `git clone` use the gh token. Without it, git operations will fail with `could not read Username for 'https://github.com'` even though `gh auth status` shows logged in.

## Pitfalls

### Scope error: "missing required scope 'read:org'"

`gh auth login --with-token` rejects tokens without `read:org`. The correct scope list is always `repo,workflow,read:org`. If you hit this error, request a **fresh** device code with all three scopes — don't reuse the old one.

### Reused/expired device codes

Device codes are single-use and expire in ~900 seconds. If phase 2 fails:
1. The code may have been consumed by a previous timed-out `gh auth login` process
2. Get a fresh code from phase 1
3. Show the new `USER_CODE` to the user

### Masked token in terminal output

The access_token response may show a masked token in curl output (`gho_Z8...iHXD`). Always pipe through `python3 -c` to extract the full value — never copy-paste a masked version.

### `git push` fails with "could not read Username" after gh auth succeeds

`gh auth login --with-token` registers the token with gh but doesn't configure git's credential helper. Run `gh auth setup-git` to fix this. Always include it in Phase 2.

### User says "授权好了" but gh still shows not authenticated

The device code they authorized may not match the one you're polling. Request a fresh code and give them the new `USER_CODE`. If this happens twice, verify the browser is at the correct URL (`github.com/login/device`, not `github.com/login`).

## Verification

After auth completes, always run:

```bash
gh auth status
```

Expected output shows logged-in account, active=true, and scopes including `read:org`, `repo`, `workflow`.
