# WeChat Article Content Extraction

WeChat articles (`mp.weixin.qq.com`) render poorly in `browser_snapshot` — the snapshot typically shows only ~12 top-level elements (title, author, like/share buttons) and truncates the actual article body.

## Extraction Method

Use `browser_console` to extract the article body via JavaScript:

```javascript
document.querySelector('#js_content').innerText
```

This targets the WeChat article content container directly and returns plain text with the full article body.

## Why It Works

- WeChat articles wrap their main content in `<div id="js_content">`
- `browser_snapshot` truncates deeply nested content but `browser_console` runs arbitrary JS in the page context
- The `innerText` property returns rendered text with natural line breaks preserved

## Limitations

- Images are lost (text-only extraction)
- Emoji and special formatting may not render
- Some articles use lazy-loading — if content is incomplete, scroll first then re-extract
- Paywalled or login-gated articles won't work

## Proven

2026.6.19: Successfully extracted a 虎嗅 (Huxiu) article from `mp.weixin.qq.com/s/ULDHCnGXmY1ktcdKS7OM3Q` — full ~3000 character article body captured in one call.

2026.6.25: Successfully extracted a 飞书和ta的朋友们 article (`mp.weixin.qq.com/s/oC3cY3J0MiwfklHsLNzacQ`) — ~4500 character article about 山海星辰 AI Native 组织 case study. Full extraction via `document.querySelector('#js_content').innerText` in one call. Article loaded directly via `browser_navigate` without anti-bot challenges; 头条搜索 was used for supplementary research and successfully found related articles on Sohu.
