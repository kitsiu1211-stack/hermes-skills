# 微信公众号 & 外部文章抓取

## 微信公众号

微信公众号文章内容藏在 `#js_content` 元素里，页面标题和元信息通过常规 DOM 获取。

### 抓取流程

1. **`browser_navigate`** 打开文章链接
2. **`browser_console`** 提取内容：
   ```js
   document.querySelector('#js_content').innerText
   ```
3. 如需标题/作者，从页面 snapshot 或 `document.title` 获取

### 示例

```python
# Step 1: Navigate
browser_navigate(url="https://mp.weixin.qq.com/s/xxxxx")

# Step 2: Extract
browser_console(expression="document.querySelector('#js_content').innerText.substring(0, 8000)")
```

### 注意事项

- 微信文章可能触发反爬（`#js_content` 不存在），此时改用 `browser_vision` 截图识别
- 长文章分段提取：`substring(0, 5000)`、`substring(5000, 10000)` 等
- `browser_snapshot` 会截断长文，不要用它读全文——用 `browser_console` 取 `innerText`

## 其他网站

- **Medium**：用 `r.jina.ai` 代理（`https://r.jina.ai/https://medium.com/...`）
- **一般网站**：`browser_navigate` → `browser_snapshot` 或 `browser_console` 取 `document.body.innerText`

## 文章总结后发飞书卡片

参考 `feishu-api` skill 中「Message Sending → Interactive Card」章节。
