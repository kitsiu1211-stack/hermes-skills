#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract WeChat mp.weixin.qq.com article body + metadata.

Usage: python3 extract.py "<article_url>"

Output:
  - body saved to /tmp/wx_article.txt (for downstream skills)
  - JSON metadata {title, author, show_type, char_len} printed to stdout
    so downstream skills (e.g. 文章分析) get title/author without re-parsing HTML

Verified 2026-08-20 on a standard 图文页 (type A, 8329 chars).
"""
import re, html, json, sys, subprocess

if len(sys.argv) < 2:
    print(json.dumps({"error": "usage: extract.py <url>"}, ensure_ascii=False))
    sys.exit(1)

url = sys.argv[1]
HTML_PATH = "/tmp/wx_article.html"
TXT_PATH = "/tmp/wx_article.txt"

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

subprocess.run(["curl", "-sL", "-A", UA, url, "-o", HTML_PATH], check=True, timeout=60)
content = open(HTML_PATH, encoding="utf-8", errors="ignore").read()

# ---- Title (msg_title -> h1.rich_media_title -> og:title) ----
title = None
m = re.search(r"var msg_title = '(.+?)';", content)
if m:
    title = m.group(1)
if not title:
    m = re.search(r'<h1[^>]*class="rich_media_title"[^>]*>(.*?)</h1>', content, re.S)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
if not title:
    m = re.search(r'<meta property="og:title" content="([^"]*)"', content)
    if m:
        title = m.group(1)

# ---- Author (nickname -> meta author) ----
author = None
m = re.search(r"var nickname = '(.+?)';", content)
if m:
    author = m.group(1)
if not author:
    m = re.search(r'<meta name="author" content="([^"]*)"', content)
    if m:
        author = m.group(1)

# ---- Body: type A (standard 图文页) ----
body = None
# anchor on id="js_content" AND prefer the closing </div> followed by <script
# (the first js_content occurrence in HTML may be a JS reference, not the content div)
m = re.search(r'<div[^>]*class="rich_media_content[^"]*"[^>]*id="js_content"[^>]*>(.*?)</div>\s*<script', content, re.S)
if not m:
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', content, re.S)
if m:
    raw = m.group(1)
    raw = re.sub(r'<(br|/p|/section|/div|/li)[^>]*>', '\n', raw)
    raw = re.sub(r'<[^>]+>', '', raw)
    body = html.unescape(raw)
    body = re.sub(r'\n\s*\n+', '\n\n', body).strip()

# ---- show_type: '10' = TEXT_SHARE_PAGE (type B) ----
show_type = None
m = re.search(r"item_show_type\s*=\s*'(\d+)'", content)
if m:
    show_type = m.group(1)

# ---- Body fallback: type B (content_noencode JS var) ----
if not body or len(body) < 100:
    m = re.search(r"content_noencode:\s*'((?:[^'\\]|\\.)*)'", content, re.S)
    if m:
        body = m.group(1).replace('\\x0a', '\n').replace('\\"', '"').replace("\\'", "'")
        body = re.sub(r'\n\s*\n+', '\n\n', body).strip()

out = {"title": title, "author": author, "show_type": show_type,
       "char_len": len(body) if body else 0}
print(json.dumps(out, ensure_ascii=False))

if body:
    open(TXT_PATH, "w", encoding="utf-8").write(body)
    print("saved:", TXT_PATH)
else:
    print("WARN: no body extracted — check for 验证/环境异常 page "
          "(see blocked-page-recovery skill)")
    sys.exit(2)
