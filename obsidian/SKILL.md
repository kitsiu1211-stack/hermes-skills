---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

### Resolution order

1. Check `OBSIDIAN_VAULT_PATH` from `~/.hermes/.env`
2. On macOS, parse `~/Library/Application Support/obsidian/obsidian.json` — the `vaults` dict maps vault IDs to `path` entries. Prefer the vault with `"open": true`.
3. Fallback: `~/Documents/Obsidian Vault`

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

### First-time setup

If `OBSIDIAN_VAULT_PATH` is not in `~/.hermes/.env`, discover the vault path (see above) then add it:

```bash
grep -q "OBSIDIAN_VAULT_PATH" ~/.hermes/.env 2>/dev/null || \
  echo 'OBSIDIAN_VAULT_PATH="$HOME/Documents/Obsidian Vault"' >> ~/.hermes/.env
```

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Note Structure Convention

When creating or updating knowledge-graph notes, follow this 4-section structure:

1. **`## Compiled Truth`** — the definitive, synthesized understanding of the topic
2. **`## 关键要点`** — bullet list with **bold** keywords, extracted from the Compiled Truth
3. **`## 关联主题`** — `[[wikilinks]]` to related notes with brief context on why they're linked
4. **`## Timeline`** — markdown table of dates and key progress milestones, including both historical dates (from original source) and new extensions from subsequent conversations

Always use `## 关联主题` (not `## 关联`) for consistency.

**主题编号铁律**：`concepts/` 下所有概念一律 `主题N-标题.md` 命名并编号，来源（文章提炼 vs 原创对话碰撞）不改变编号规则，编号 = 当前最大编号 + 1。禁止无编号概念文件。

## Bulk Migration Pattern

When migrating many notes at once (e.g., from an external document to Obsidian), use `execute_code` with `write_file` in batches:

- Put 5-6 `write_file` calls per `execute_code` invocation to stay within rate limits
- Prepare full markdown content as Python strings inside the script
- Use `hermes_tools` imports (`write_file`, `read_file`, `patch`) — not shell commands
- Verify with `search_files(target="files", pattern="*.md")` after each batch

## ⚠️ Pitfall: read_file → write_file Line Number Contamination

**Never re-write a file using raw `read_file` output.** `read_file` returns content with line number prefixes (`"1|     1|content"`). If you pass this directly to `write_file`, the line numbers become embedded in the file.

**Safe patterns:**
- For targeted edits: use `patch` with `old_string`/`new_string`
- For appending: use `patch` to insert after a stable anchor
- For full rewrites: construct the content from scratch in a Python string, don't pipe `read_file` output

If line number contamination occurs, fix by re-writing the file with clean content via `write_file`. Verify with `head -3` in terminal.
