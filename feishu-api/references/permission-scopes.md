# Feishu Permission Scopes

## Authorization URL Builder

Replace `{APP_ID}` with your app's ID (e.g., `cli_a964fd626078dcbc`):

```
https://open.feishu.cn/app/{APP_ID}/auth?q=SCOPES&op_from=openapi&token_type=tenant
```

## Bitable Scopes

| # | Scope | API Endpoint | Error Without It |
|---|-------|-------------|------------------|
| 1 | `bitable:app:readonly` | App metadata, table list | All bitable APIs denied |
| 2 | `base:app:read` | Base metadata | — |
| 3 | `base:table:read` | List tables | 99991672: `[bitable:app:readonly, bitable:app, base:table:read]` |
| 4 | `base:field:read` | List fields | 99991672: `[bitable:app:readonly, bitable:app, base:field:read]` |
| 5 | `base:record:retrieve` | Read records | 99991672: `[bitable:app:readonly, bitable:app, base:record:retrieve]` |
| 6 | `base:record:write` | Create/update records | 99991672 (on PUT/POST) |

## Docx Scopes

| Scope | Used For |
|-------|----------|
| `docx:document:readonly` | rawContent, blocks listing |
| `docx:document` | Create/update documents, write blocks |
| `drive:drive:readonly` | Download attachments/media from docs |

## IM / Messaging Scopes

| Scope | Used For |
|-------|----------|
| `im:message:send_as_bot` | Send messages to users/groups |
| `im:chat` | Create/manage group chats |
| `im:chat.members:write_only` | Add members to groups |
| `contact:user.id:readonly` | Look up users by email/phone |

## Minutes (妙记) Scopes

| Scope | Used For |
|-------|----------|
| `minutes:minutes:readonly` | Read minutes metadata, statistics (minimum needed) |
| `minutes:minutes.basic:read` | Read basic minutes info |
| `minutes:minutes` | Full access (read + manage) |
| `minutes:minutes.transcript:export` | Download transcript / 逐字稿 |

**⚠️ Transcript requires TWO scopes granted separately:**
1. `minutes:minutes:readonly` — for metadata + statistics
2. `minutes:minutes.transcript:export` — for transcript content

The transcript endpoint (`/open-apis/minutes/v1/minutes/{token}/transcript`) returns 403 `code:2091005 permission deny` even with scopes granted — this is a known limitation. It likely requires a **user access token** (UAT) from someone who has viewed the minutes, not just tenant token. Fallback: have the user run `feishu-cli auth login` to get UAT.

**One-click authorization URLs (do in order):**
```
# Step 1: Metadata + stats
https://open.feishu.cn/app/{APP_ID}/auth?q=minutes:minutes,minutes:minutes:readonly,minutes:minutes.basic:read&op_from=openapi&token_type=tenant

# Step 2: Transcript (separate grant needed)
https://open.feishu.cn/app/{APP_ID}/auth?q=minutes:minutes.transcript:export&op_from=openapi&token_type=tenant
```

**Key minutes endpoints via feishu-cli:**
```bash
# Discover all minutes APIs
npx feishu-cli api search minutes

# Metadata (title, duration, owner, note_id)
npx feishu-cli exec minutes.v1.minute.get --params '{"path":{"minute_token":"obc..."}}' --token-mode tenant

# Statistics (PV, UV, viewer list with timestamps)
npx feishu-cli exec minutes.v1.minuteStatistics.get --params '{"path":{"minute_token":"obc..."}}' --token-mode tenant
```

**Minutes error patterns:**
| Error | Meaning | Fix |
|-------|---------|-----|
| 400 `99991672 Access denied` + scopes list | Missing permission scope(s) | Grant scopes in app console, publish |
| 403 `2091005 permission deny` | Scope granted but still blocked | Try `--token-mode user` with UAT |
| `note_id` is NOT a docx token | The 19-digit `note_id` from metadata is internal | Don't try `feishu_doc_read` or `docx/rawContent` on it |

Minutes API returns error `99991672` with a direct permission-grant URL in the error body — use that URL to add scopes quickly.

## One-Click Authorization URL (All Bitable Scopes)

```
https://open.feishu.cn/app/{APP_ID}/auth?q=bitable:app:readonly,base:app:read,base:table:read,base:field:read,base:record:retrieve,base:record:write&op_from=openapi&token_type=tenant
```

## Verification Checklist

After the user grants permissions, verify each scope works before proceeding:
- [ ] `GET /open-apis/bitable/v1/apps/{app_token}` — App metadata (scope 1)
- [ ] `GET /open-apis/bitable/v1/apps/{app_token}/tables` — Table listing (scope 3)
- [ ] `GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields` — Fields (scope 4)
- [ ] `GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=3` — Records (scope 5)

If any returns 99991672, include the missing scope in a new auth URL and ask the user to re-authorize.

## Error Code Reference

| Code | Meaning |
|------|---------|
| `99991672` | Missing permission scope(s). The `permission_violations` array lists exact missing scopes. |
| `401` (in MCP) | User access token expired — use tenant token instead, or re-auth. |

## Common Mistake

**App metadata works but table listing fails.** This happens when scopes 1-2 were granted but 3-6 were not. The app-level endpoint (`bitable:app:readonly`) succeeds, but table/field/record endpoints need their own scopes. Always test all 4 checkpoints above.

**After granting scopes in console, must 「发布」 (Publish).** Unpublished scope changes live only in draft. The #1 cause of "I added the permission but it still doesn't work" is forgetting to publish.
