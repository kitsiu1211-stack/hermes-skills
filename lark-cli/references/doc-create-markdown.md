# Creating Feishu Docs from Markdown Files

Use `lark-cli docs +create --doc-format markdown` to import a local `.md` file as a Feishu docx in one call.

## One-liner

```bash
cd /path/to/md/dir && lark-cli docs +create \
  --title "Document Title" \
  --doc-format markdown \
  --content "@./filename.md" \
  --as user \
  --json
```

Returns: `{"data": {"document": {"document_id": "...", "url": "https://bytedance.larkoffice.com/docx/..."}}}`

## Key Pitfall: `@file` must be relative

The `--content` flag's `@file` syntax **requires a relative path within the current directory**. Absolute paths are rejected:

```
❌ --content "@/Users/x/docs/file.md"  →  invalid file path
✅ cd /Users/x/docs && --content "@./file.md"  →  works
```

Error message: `--content: invalid file path "...": --file must be a relative path within the current directory`

## Flag Reference

| Flag | Purpose |
|------|---------|
| `--title` | Document title. CLI prepends `<title>` block, wins over any H1 in content. |
| `--doc-format markdown` | Treat content as markdown (default is `xml`). Auto-converts tables, code blocks, bold, etc. |
| `--content "@./file.md"` | Read from local file. Also supports `-` (stdin) or inline string. |
| `--as user` | Create as user identity (needs UAT). Use `--as bot` for bot-owned docs. |
| `--json` | Machine-readable output. Omit for pretty-printed. |
| `--parent-token` | Place doc in a specific folder/wiki node. |
| `--dry-run` | Print request body without executing. Useful for debugging. |

## Markdown Support

The converter handles:
- `#` H1 through `######` H6
- `**bold**`, `*italic*`, `~~strikethrough~~`
- `[links](url)`
- `-` / `*` bullet lists, `1.` numbered lists
- `| tables |` with headers
- `>` blockquotes
- `---` horizontal rules
- `` `code` `` and ```` ```code blocks``` ````
- ASCII art in code blocks (box-drawing characters preserved)

## Reading Back

```bash
lark-cli docs +fetch --doc <doc_id_or_url> --as user --json
```

Returns `data.document.content` as docx XML.

## Updating

```bash
# Append markdown
lark-cli docs +update --doc <doc_id> --command append --doc-format markdown --content "# New" --as user --json

# Full overwrite
lark-cli docs +update --doc <doc_id> --command overwrite --doc-format markdown --content "@./new.md" --as user --json
```
