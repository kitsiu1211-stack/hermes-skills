# Manual Docx Block Construction

When `docx document convert` produces blocks in wrong order, or when the output includes table blocks
(type 32) that `documentBlockChildren.create` rejects with code `1770029`, **build blocks manually**
as Python dicts.

## Block Type Reference

| block_type | Meaning     | Dict Key    |
|-----------|-------------|-------------|
| 2         | Plain text  | `text`      |
| 3         | Heading 1   | `heading1`  |
| 4         | Heading 2   | `heading2`  |
| 12        | Bullet list | `bullet`    |
| 32        | Table cell  | (avoid — not supported in children create) |

## Helper Functions

```python
def text_block(content):
    return {
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": content, "text_element_style": {}}}],
            "style": {}
        }
    }

def heading1(content):
    return {
        "block_type": 3,
        "heading1": {
            "elements": [{"text_run": {"content": content, "text_element_style": {}}}],
            "style": {}
        }
    }

def heading2(content):
    return {
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": content, "text_element_style": {}}}],
            "style": {}
        }
    }

def bullet(content):
    return {
        "block_type": 12,
        "bullet": {
            "elements": [{"text_run": {"content": content, "text_element_style": {}}}],
            "style": {}
        }
    }
```

## Write to Document

```python
import json, subprocess

FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"

# Create doc
result = subprocess.run(
    [FEISHU_CLI, "docx", "document", "create", "--title", "Document Title"],
    capture_output=True, text=True, timeout=15
)
doc = json.loads(result.stdout)
DOC_ID = doc["data"]["document"]["document_id"]

# Build blocks
blocks = [
    heading1("Title"),
    heading2("Section 1"),
    text_block("Paragraph text..."),
    bullet("Bullet point"),
]

# Write (index 0 = beginning)
payload = {
    "path": {"document_id": DOC_ID, "block_id": DOC_ID},
    "data": {"children": blocks, "index": 0}
}

subprocess.run(
    [FEISHU_CLI, "exec", "docx.v1.documentBlockChildren.create",
     "--params", json.dumps(payload)],
    capture_output=True, text=True, timeout=30
)
```

## When to Use

- Markdown `convert` returns blocks in **reverse order** — reverse the array or build manually
- Convert output includes tables → code `1770029` — strip tables or build manually without them
- Need precise control over formatting that convert doesn't produce correctly
