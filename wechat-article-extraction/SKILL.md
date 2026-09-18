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

用户问「过去几个月发了多少篇公众号文章 / 哪个公众号最多 / 文章分类」等回顾型统计 → 见 `references/history-analysis.md`（state.db 捞链接 + 批量抓标题/公众号 + 关键词分类 + 飞书卡片）。

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

**正文藏在 JS 变量 `content_noencode` 里**，用单引号包裹。转义有两种形态，都要能处理：
- 普通形态：`\x0a` 转义换行、`\"`、`\'` 转义引号
- 🚨 **全十六进制形态（2026-09-04 正和岛实测）**：整个正文每个字符都转成 `\xHH`（`\x3c`=`<`、`\x22`=`"`、`\x0a`=`\n`）。extract.py 若返回 char_len=0，或手工提取后 body 以 `\x3c`/`\x22` 开头，即命中此形态——**只替换 `\x0a`/`\"`/`\'` 不够，必须通用反 hex**。

通用反转义（extract.py 已内置此逻辑，手写 fallback 时用）：
```python
m = re.search(r"content_noencode:\s*'((?:[^'\\]|\\.)*)'", content, re.S)
body = re.sub(r'\\x([0-9a-fA-F]{2})', lambda mo: chr(int(mo.group(1), 16)), m.group(1))
# 先反 hex 再转段落——此时标签是真实形态
body = re.sub(r'<br[^>]*>', '\n', body)
body = re.sub(r'</p[^>]*>', '\n', body)
body = re.sub(r'<[^>]+>', '', body)
body = html.unescape(body)
body = re.sub(r'\n\s*\n+', '\n\n', body).strip()
```

- 标题此时用 `og:title` meta 或 `window.msg_title`（`<title>` 标签是空的）
- 正文可能较短（纯文本帖，几百~两千字）

## 判断顺序

1. 先试标准图文页提取（`rich_media_content` div）
2. 失败 → 查 `item_show_type`：`'10'` → 走 `content_noencode`
3. 仍失败 → 检查是否命中验证/环境异常页（搜「验证」「环境异常」关键词），考虑 blocked-page-recovery skill

## Pitfalls

- 页面 HTML 里第一个 `js_content` 出现位置可能是 JS 引用而非正文 div，正则要锚定 `id="js_content"` 再往后找
- `content_noencode` 的值是 JS 字符串转义，可能是 `\x0a`/`\"`/`\'` 普通形态，也可能是**全 `\xHH` 十六进制形态**——统一用通用反 hex（`\\x([0-9a-fA-F]{2})` 逐个还原）处理，两种都覆盖，且要先反 hex 再转段落/去标签
- 提取完保存 `/tmp/wx_article.txt` 供下游 skill 读取，不要把 3MB HTML 带进上下文
- 🚨 **`author` 字段是转载公众号名，不是原文出处**（2026-08-25 实测）：extract.py 从页面 meta 读 author，转载号（如「关注前沿科技」转载量子位文章）会显示转载号名。下游引用来源时需从正文/文末「来源」/作者署名判断原公众号（如量子位 QbitAI），避免写错来源——用户偏好来源必须查证准确。
