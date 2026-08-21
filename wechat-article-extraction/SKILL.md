---
name: wechat-article-extraction
description: 抓取微信公众号(mp.weixin.qq.com)文章正文。用户发公众号链接需提取全文时触发。
version: 1.0.0
author: Hermes Agent
license: MIT
category: research
metadata:
  hermes:
    tags: [wechat, extraction, scraping, mp-weixin]
    related_skills: [文章分析, blocked-page-recovery]
---

## When to Use

用户发 mp.weixin.qq.com 链接（文章分析、摘要、引用素材），需要先提取正文全文时。

# 微信公众号文章正文提取

用户发 mp.weixin.qq.com 链接时，先用本 skill 提取正文，再交给下游（如 文章分析）处理。

## 标准流程

```bash
curl -sL -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1" \
  "https://mp.weixin.qq.com/s/<ID>" -o /tmp/wx_article.html
```

iPhone UA 基本都能过，不需要 cookie。

### 🚀 一键提取脚本（推荐，2026-08-20 验证）

```bash
python3 ~/.hermes/skills/research/wechat-article-extraction/scripts/extract.py "<url>"
```

脚本自动完成：curl 抓取 → 标题/作者/正文提取（类型 A/B 自动判断）→ 正文存 `/tmp/wx_article.txt` → stdout 打印 JSON 元数据 `{"title", "author", "show_type", "char_len"}`。下游 skill（如 文章分析）直接读元数据 + `/tmp/wx_article.txt`，不用自己写提取代码。正文提取失败时退出码 2 并提示检查验证页。

## 两种页面结构（关键判断）

### 类型 A：标准图文页（多数情况）

- 标题：`<h1 class="rich_media_title">` 或 `var msg_title = '...'`
- 正文：`<div class="rich_media_content" id="js_content">...</div>`
- 提取：`<br>`/`</p>` 转 `\n` → 去标签 → `html.unescape` → 压缩空行

### 类型 B：文本分享页（正文拿不到时优先怀疑）

**症状**：搜 `js_content` 找到但 `rich_media_content` div 匹配失败，或提取出一堆 JS 脚本而非正文。特征是 `window.item_show_type = '10'`（TEXT_SHARE_PAGE）。

**正文藏在 JS 变量 `content_noencode` 里**，用单引号包裹、`\x0a` 转义换行：

```python
m = re.search(r"content_noencode:\s*'((?:[^'\\]|\\.)*)'", content, re.S)
body = m.group(1).replace('\\x0a', '\n').replace('\\"', '"').replace("\\'", "'")
```

- 标题此时用 `og:title` meta 或 `window.msg_title`（`<title>` 标签是空的）
- 正文可能较短（纯文本帖，几百~两千字）

## 判断顺序

1. 先试标准图文页提取（`rich_media_content` div）
2. 失败 → 查 `item_show_type`：`'10'` → 走 `content_noencode`
3. 仍失败 → 检查是否命中验证/环境异常页（搜「验证」「环境异常」关键词），考虑 blocked-page-recovery skill

## Pitfalls

- 页面 HTML 里第一个 `js_content` 出现位置可能是 JS 引用而非正文 div，正则要锚定 `id="js_content"` 再往后找
- `content_noencode` 的值是 JS 字符串转义，`\x0a`、`\"`、`\'` 都要反转义，否则正文粘成一行
- 提取完保存 `/tmp/wx_article.txt` 供下游 skill 读取，不要把 3MB HTML 带进上下文
