# Bulk Docx Fix Patterns

Concrete Python fix recipes from real docx repair sessions. Use these as templates when fixing multi-issue documents.

## Pattern: Export → Fix → Markdown → Import

When a docx has multiple scattered issues (duplicates, missing headers, mixed content), block-level API edits are too slow. Use this pipeline:

```python
# 1. EXPORT
# feishu-cli docx document rawContent --document-id <id> > raw.txt

# 2. FIX (Python — example patterns below)
# ...

# 3. CONVERT TO MARKDOWN
# Add headers, bold markers, etc.

# 4. IMPORT (requires UAT)
# feishu-cli docx builtin import --markdown "$(cat fixed.md)" --file-name "Title" --use-uat true
```

## Common Fix Recipes

### Remove duplicate section blocks

```python
import re

# Pattern: duplicate Compiled Truth section after Timeline
dup_pattern = r'(Timeline.*?\n)\n### Compiled Truth.*?(?=\n## 🎯 主题\d)'
md = re.sub(dup_pattern, r'\1', md, flags=re.DOTALL)
```

### Extract embedded subsection from wrong parent

When theme B's content is accidentally inside theme A's section:

```python
# Find split point — usually starts with "Compiled Truth" or distinctive text
split_point = t18.find('Compiled Truth（当前最佳理解）\n美方从')

# Find appendix that belongs AFTER the extracted content
appendix_start = t18.find('本知识图谱源自')

t17 = t17_header + t18[split_point:appendix_start]
t18 = t18[:split_point] + t18[appendix_start:]
```

### Clean contaminated timeline tables

When a timeline table has entries from the wrong theme:

```python
# Find where correct entries start (by date)
correct_start = t10.find('2026.3.17\n\n初步形成', tl_start)

# Keep header, jump to correct entries
new_tl = t10[tl_start:tl_start + len('Timeline（思考演变）')] + '\n\n' + t10[correct_start:]
```

### Remove orphan content at document end

```python
# Find clean end marker
idx_end = md.find('🗓️ 记录时间：')
if idx_end > 0:
    md = md[:md.find('\n', idx_end) + 1]
```

### Split concatenated theme headers

```python
md = md.replace(
    '## 🎯 主题22：Skill 设计方法论\\n- 🎯 主题23：...',
    '## 🎯 主题22：Skill 设计方法论\n\n## 🎯 主题23：...'
)
```

### Fix duplicate sub-headers

```python
md = re.sub(r'(### Timeline（思考演变）)\n\n\1', r'\1', md)
md = re.sub(r'(#### 附录：原始日记索引)\n\n\1', r'\1', md)
```

## Verification Checklist

After fixing, verify:
- [ ] All 24 themes have `## 🎯 主题N：` headers in order 1-24
- [ ] No `Compiled Truth（当前最佳理解）` appears twice for any theme
- [ ] Timeline tables contain only entries relevant to their theme
- [ ] Document ends cleanly (no orphan `AI Split` or `已删除错误内容格式` fragments)
- [ ] No theme content mixed into adjacent themes
