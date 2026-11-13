---
name: obsidian-vault-admin
description: Use when syncing/migrating/auditing the Obsidian dual-vault or debugging a plugin.
platforms: [macos, linux, windows]
---

# Obsidian Vault Admin

Filesystem-first administration of Obsidian vaults: syncing the dual-vault setup,
auditing drift / broken wikilinks between the two, and diagnosing community plugins.
Complements the bundled `obsidian` skill (which covers note CRUD) — use THIS one for
sync, drift audits, and plugin troubleshooting.

## When to Use

- User asks to sync the Obsidian vaults, or reports one vault is missing/out-of-date.
- Someone (user or another Agent) asks **which files differ** between the two vaults,
  whether their mirror edits survived, or how many broken links there really are.
- Another Agent wants write access to the vault and you need a coordination gate.
- A community plugin is "not working": command not found, view won't open, starry graph
  missing, or plugin settings not applying.

## Dual-vault setup

This user runs TWO vaults:

| Vault | Path | Role |
|---|---|---|
| Obsidian Vault | `~/Documents/Obsidian Vault/` | git 主库 → GitHub `obsidian-project-hub`. Primary; write here. |
| My Great Vault | `~/Documents/My Great Vault/` | cloud mirror (read by phone / other devices). |

**Every edit to the primary vault MUST be synced to the mirror.** A past session only
knew one vault and the two drifted for weeks. After writing notes, run:

```bash
rsync -a --exclude='.git' --exclude='.gitignore' --exclude='.obsidian' \
  "$HOME/Documents/Obsidian Vault/" "$HOME/Documents/My Great Vault/"
```

- `.obsidian` is intentionally excluded so the two vaults' settings/plugins don't fight.
  Consequence: **plugin config changes (e.g. Galaxy View style) do NOT auto-sync** — copy
  the specific file over manually when the user wants them matched.
- `rsync` without `--delete` preserves mirror-only files; `diff` the two trees to catch drift.

### 同步方向单向：主库 → 镜像

镜像里写的东西一律算草稿，回迁前不进主库。原因：从主库 rsync 过去时，**共享文件里在镜像做的编辑会被静默覆盖**（不带 `--delete` 时只有「镜像独有」文件能活下来）。所以当有人说"我在镜像改了某个文件"时，先怀疑已被覆盖 —— 证据看下面审计的 `content_diff`：共享文件字节级 0 差异 + `main_only=0` ⇒ 他的改动已经没了。

### 回迁（镜像草稿 → 主库）——仅在用户明确点头后做

镜像独有文件默认当草稿。用户（不是另一个 Agent）拍板要并入后，按这个顺序，6 步都别省：

1. **先跑审计**：`content_diff` 必须是 0。0 差异才证明「镜像里改过的共享文件都已被 rsync 覆盖、回迁只是纯新增」，否则回迁就是把旧版本写回去。
2. **`cp -a` 而不是 `mv`**：保留目录结构与 mtime（`cp -a "$M/builders" "$V/"`）。镜像要留着，它还是手机/其他设备的读取副本。
3. **index.md 一起改**（SCHEMA 要求）：新增文件必须进对应分类；顺手更新 frontmatter `updated` 和头部 `Total pages: N concepts + N project + N builders + 3 meta`。补分类时按主题分组、每页写一句话描述，不要只堆 `[[文件名]]`。
4. **log.md 追加一条**：触发（谁在哪天定的）→ 清单（每个文件一句话）→ 两库数字前后对比 → 后续待办（谁负责哪一步）。决策若推翻了 Agent 的建议，明写「此前建议 X，未采纳」。
5. **只验这次新增文件的 wikilink**（`scripts/vault-integrity-check.py --files …`），别把整库历史断链算进本次账。给用户报「新增 0 断链」比「全库仍 15 条」有用。
6. **commit 后 rsync 主库→镜像**，`diff -rq` 应为空 —— 回迁后两库文件集必须一致，这是对方能独立验证的唯一证据。

commit message 要写清：**谁定的、几个文件、逐项清单、哪个版本没动、后续谁负责**。一次 commit 只做一次回迁，别把不相干的改动混进来。

**Pitfall：同一主题两版并存时**。常见形态是两个不同文件名（`主题36-AI 落地的三条路径` vs `主题36-AI 落地的三个闭环`），各带一套图。回迁时只搬用户点名的那个，另一版**一个字节不动**，在 index.md 里并列标注「待合并，合并后只留一个文件」。**不要**替它改名、合并或挪进 `_staging/` —— 另一个 Agent 正在起草合并稿，改名会直接打断它的引用。

## 双库审计（回答"到底差哪些文件"）

别手工 `ls` / 肉眼 diff，跑 `scripts/dual-vault-audit.py`：

```bash
python3 ~/.hermes/skills/note-taking/obsidian-vault-admin/scripts/dual-vault-audit.py \
  "$HOME/Documents/Obsidian Vault" "$HOME/Documents/My Great Vault"
```

写完/回迁完再跑一次 `scripts/vault-integrity-check.py <vault>`：扫 `read_file` 行号前缀污染（`--fix-corruption` 可批修，先 `--dry-run`），并用 `--files` 只验本次新增文件的 wikilink，避免把历史断链混进本次回执。

三张表就是回迁决策的全部依据：

| 指标 | 含义 | 决策含义 |
|---|---|---|
| `main_only` | 只在主库 | 镜像缺 → 一次 rsync 补上 |
| `mirror_only` | 只在镜像 | 草稿，要决定是否回迁 |
| `content_diff` | 同路径、字节不同 | 看 mtime 判谁新，冲突源头 |
| broken links | 拆「可修」/「真缺」 | 见下 |

两个必查的坑（都会让断链数虚高，报出去会被对方当场推翻）：

1. **图片嵌入不是断链**。`![[assets/blueprint/p1-overview.png]]` 指向非 md 文件，只扫 `.md` 的检查器会误判。先 `find <vault>/assets -type f` 确认图真实存在再剔除。实测：一份 19 条的"断链"清单，剔掉存在的 png 和 `[[filename]]` 这类文档示例后，真实是 15 条。
2. **必须分类，不能只报总数**。「目标存在、只是链接文字漂移」（空格/连字符差异，如 `[[Skill 路由表]]` vs 实际 `AI场景/Skill路由表.md`）是可脚本批修的；「目标真不存在」才要人工判断。混在一起报，对方会以为全是硬伤。

## 多 Agent 共用一个库时的门禁口径

别的 Agent 要动这个库，门禁写成 **「我已提交 baseline，`git status` 干净」**，不要写成「等 git status 干净」—— 工作区可能本来就有几天前的未落盘改动，对方没法自己判断何时轮到他。顺序：审计 → 把遗留改动提交成 baseline（message 写清这批改动的时间范围与内容）→ 群里报一声 → 对方才动手。

`git push` 失败（网络/代理）不推翻本地门禁：commit 已落本地、`git status` 干净就成立，但回执里要明说"远端没有兜底"。

## Debugging a community plugin

Full checklist lives in `references/plugin-debugging.md`. The one-liner that matters:

**Command palette returns "未找到命令 / Command not found" for a plugin's command ⇒
the plugin is NOT loaded** (not a language mismatch, not a config problem, not a missing
file). Verify files / enable-state / config / version, then restart Obsidian (`Cmd+Q`,
not close-window) to apply any pending update and force a clean reload.

## Pitfalls

- **macOS TCC 会“挂死”而不是报错**：`ls`/`git status`/`read_file` 对 `~/Documents` 一律无限等待（不是 EPERM），先怀疑权限而不是仓库损坏。诊断三行：① `stat` 能过但 `os.listdir` 阻塞 ⇒ 不是磁盘坏，是 open 被拦；② `log show --last 30m --predicate 'process == "tccd"' | grep -E 'SystemPolicyDocumentsFolder|AUTHREQ_PROMPTING'` 看有没有挂起的弹窗；③ 同目录 `ls ~` 正常、`ls ~/Desktop` 也挂 ⇒ 是整个 TCC 保护目录集。责任进程（responsible）是 gateway 的父 `osascript`，弹窗无人点击时后续所有请求排队 ⇒ 全部超时。**无法脚本绕过**：换 `/System/Volumes/Data/...` 路径、`launchctl` 分离、sudo 都无效，只能人工点弹窗或在「完全磁盘访问权限」里加 `/usr/bin/osascript` 后重启 gateway。此时不要报“git 不干净”，要报“连 .git 都读不到”。
- **`read_file` 行号前缀污染（会静默毁掉一篇笔记）**：症状是正文里出现 `     1|     1|     1|     1|     1|---` 这种嵌套前缀，每嵌套一层来自一次「拿 `read_file` 的带行号输出当内容回写」。检测：`grep -rlE '^[[:space:]]*[0-9]+\|[[:space:]]*[0-9]+\|' --include='*.md' .`（单层前缀不算，必须是两层以上）。修复：逐行反复剥离 `^\s*\d+\|` 直到不再匹配，只动前缀不动正文，改完 `git diff` 里应该只剩前缀差异。预防：整文件回写一律先 `open(path).read()` 取原文，绝不用 `read_file` 的输出当 payload。实测 80 行的 log.md 前 53 行被套了 3–5 层，全库只有这一个文件受影响——发现一处就要全库扫一遍。
- **这次新增文件的断链要单独验**：`scripts/vault-integrity-check.py` 同时做污染扫描和指定文件的 wikilink 存在性检查（basename 或相对路径命中即算通），比把整库审计的数字混进本次回执更可信。
- **Separate-view confusion**: a plugin may render its OWN view, not the native feature.
  `Galaxy View` (starry 星空) ≠ Obsidian's native `关系图谱` (Graph View). If the user
  screenshots the native graph and says "还是没有", first confirm they're opening the
  plugin's view (ribbon icon / command palette), not the native one.
- **Pending update = stale plugins**: `"An update is already downloaded"` in the app
  log means an update is waiting on a restart; plugins often stop loading cleanly until
  that restart happens.
- **Read-only diagnosis first**: never tell the user to restart until you've confirmed
  files/enable/config on disk are correct — otherwise a restart hides the real cause.
