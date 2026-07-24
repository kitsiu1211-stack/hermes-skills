# Skill Hub (bytedance.aiforce.cloud)

The user maintains TWO self-built Skill Hubs on the Magic Builder (妙搭) platform. Both are static Next.js SPA apps — data is hardcoded in JS bundles, NOT pulled from any live API.

## Two Skill Hubs

| App ID | Name | Skills | Categories | Source of Truth |
|--------|------|--------|------------|-----------------|
| `app_4k5x4btce2wuf` | Business Skill Hub (业务工具) | 24 | 10 (客户管理/销售工具/内容创作/汇报工具/效率工具/知识管理/活动策划/个人成长/系统工具/开发工具) | Magic Builder only |
| `app_179xr3ds4q0` | Hermes Agent Skill Hub (Agent 认知方法) | 21 | 3 (思考方式/开发方法/工具效率) | GitHub `kitsiu1211-stack/hermes-skills` |

## Endpoint (Business Hub only)

```
GET https://bytedance.aiforce.cloud/app/app_4k5x4btce2wuf/openapi/skills
Authorization: Bearer <token>
```

**The Hermes Skill Hub (`app_179xr3ds4q0`) does NOT have an OpenAPI endpoint** — it's a pure static SPA.

## Auth Token

The Bearer token is a 43-character string. To recover it when redacted in chat logs:

```python
import re
session_file = "~/.hermes/sessions/<session_id>.jsonl"
with open(session_file, errors="replace") as f:
    content = f.read()
matches = re.findall(r'BEARER_TOKEN_PREFIX[A-Za-z0-9]+', content)
# Take the 43-char match
```

The token appears in:
- `~/.hermes/sessions/*.jsonl` — user messages and tool call arguments
- `~/.hermes/logs/agent.log` — redacted but prefix visible for identification

## Response Structure

```json
{
  "totalSkills": 24,
  "activeSkills": 23,
  "categories": [
    {
      "id": "客户管理",
      "icon": "🎯",
      "description": "客户关系维护、动态监控、需求匹配",
      "skillCount": 2
    }
  ],
  "updateCycle": "双周迭代",
  "lastUpdated": "2026-06-08T00:00:00Z"
}
```

## Categories (as of June 2026)

| Icon | Category | Skills |
|------|----------|--------|
| 🎯 | 客户管理 | 2 |
| 💼 | 销售工具 | 5 |
| ✍️ | 内容创作 | 3 |
| 📊 | 汇报工具 | 1 |
| ⚡ | 效率工具 | 2 |
| 🧠 | 知识管理 | 2 |
| 🎪 | 活动策划 | 1 |
| 🌱 | 个人成长 | 4 |
| ⚙️ | 系统工具 | 1 |
| 🔧 | 开发工具 | 3 |

## Updating Skill Hub Content

### Hermes Agent Skill Hub (`app_179xr3ds4q0`) — Programmatic Update ✅

**The agent CAN update this Hub programmatically.** Source HTML lives locally at `/tmp/skillhub/index.html`.

**Full update workflow:**

1. **Edit the source HTML**: `/tmp/skillhub/index.html` — a static SPA with skills data as inline JS arrays under `categories[].skills[]`.
   - Each skill entry: `{ cn, code, icon, desc, exUser, exAgent }`
   - Category: `{ id, icon, label, title, desc, skills: [...] }`
   - Update counts: category pill count, hero dot grid count (`for (let i = 0; i < N; i++)`), `copyAll` toast text

2. **Republish via lark-cli**:
   ```bash
   cd /tmp && lark-cli apps +html-publish --app-id app_179xr3ds4q0 --path ./skillhub --as user --json
   ```
   Returns `{"ok": true, "data": {"url": "..."}}` on success.

3. **GitHub** (optional, for record-keeping): Push SKILL.md + update README → `kitsiu1211-stack/hermes-skills`. This repo is the source of truth for skill content; the Skill Hub is the display layer.

**⚠️ Pitfall: DO NOT try the Magic Builder browser auth route.** The builder at `magic.solutionsuite.cn/app/app_179xr3ds4q0` returns "无权限" — Feishu SSO is required and agent cannot pass it. Use `lark-cli apps +html-publish` instead. This was discovered after a failed attempt to access the builder via browser (2026-07-13).

### Business Skill Hub (`app_4k5x4btce2wuf`) — Manual Only

This Hub is NOT updatable programmatically. Requires authenticated 妙搭 builder session via browser.

## Related Endpoints

| Path | Method | Response |
|------|--------|----------|
| `/app/app_4k5x4btce2wuf/openapi` | GET | HTML page (SPA) |
| `/app/app_4k5x4btce2wuf/api/faas` | GET/POST | HTML (requires browser auth) |
| `/app/app_4k5x4btce2wuf/api/html-box` | GET/POST | HTML (requires browser auth) |
| `/app/app_179xr3ds4q0/` | GET | Hermes Agent Skill Hub SPA |
| `/app/app_179xr3ds4q0/openapi/skills` | GET | 401 (no Bearer endpoint) |

The Magic Builder production platform is at `https://magic.solutionsuite.cn` (different IP, separate deployment).

## GitHub Source (Hermes Hub)

The Hermes Skill Hub's source of truth is:
```
https://github.com/kitsiu1211-stack/hermes-skills
```
Skills added to this repo should also be manually added to the Skill Hub via 妙搭 builder.
