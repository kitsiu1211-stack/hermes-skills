---
name: chinese-search-workaround
category: research
label: 中文搜索绕行方案
description: 当百度/Google/Bing/知乎等中文网站触发反爬/验证码时，使用头条搜索（so.toutiao.com）作为替代渠道进行中文信息检索。
---

# 中文搜索绕行方案

## 问题背景

中文搜索引擎（百度、Google CN、Bing CN）和内容平台（知乎、CSDN、36氪）普遍对自动化请求有严格的bot检测机制，常见的反爬手段包括：
- Google：返回 `Error 400 (Bad Request)` + 触发 `sorry/index` CAPTCHA 页面
- 百度：返回验证码页面
- Bing：内容被截断/重定向到空白页
- 知乎：直接返回 403 或空页面
- CSDN：触发 WAF 拦截（403 Forbidden）
- 36氪：历史文章页面大量返回"数据不存在或已被删除"
- 微信公众号：反爬严格，New Bing/SerpApi 可搜到但无法直接抓取内容。**文章正文提取**：见 `references/wechat-article-extraction.md` — 通过 browser_console JS 直接抓 `#js_content`
- **Medium**：Cloudflare 安全验证拦截，浏览器和 API 均被阻

## 替代方案

### 方案A0（Medium 专用）：r.jina.ai 全文提取

**适用**：Medium.com 文章（含 paywall 文章摘要级别内容）。

**原理**：Jina AI 的 Reader API 可绕过 Cloudflare 并以 Markdown 返回全文。

**使用方式**：
```bash
curl -sL "https://r.jina.ai/<medium-article-url>" -H "Accept: text/plain"
```

或拼接 URL：
```bash
curl -sL "https://r.jina.ai/https://author.medium.com/article-slug-postid" -H "Accept: text/plain"
```

**特点**:
- ✅ 绕过 Medium Cloudflare 验证
- ✅ 返回干净的 Markdown 格式，含元数据（标题、发布时间、作者）
- ✅ 免费，无需 API Key
- ❌ 可能被 Medium 限流（控制频率）
- ❌ 图片以 CDN URL 形式保留，非内嵌

**实测**：2026.5.17 成功提取 Roberto Capodieci 的 OpenClaw 多 Agent 系统文章全文。

### 方案A（首选）：头条搜索聚合页

**原理**：今日头条的 `so.toutiao.com` 搜索引擎是字节跳动自建搜索引擎，对API自动化请求的检测较宽松，可以稳定获取中文站点的搜索结果。

**使用方式**：
```python
# 直接在浏览器中导航
browser_navigate("https://so.toutiao.com/search/?dvpf=pc&keyword=闲鱼+虚拟产品+热门&source=search")
```

**特点**：
- ✅ 对中文站点覆盖好（知乎、CSDN、36氪、网易等均可搜到）
- ✅ 不会被拦截
- ✅ 免费，无需API Key
- ✅ 支持"综合"和"资讯"两种视图
- ❌ 没有结构化API，依赖页面解析
- ❌ 结果偏向头条系/抖音内容
- ❌ 搜索结果可能不够全

### 方案B（已知URL直访）：浏览器直接打开文章页面

当用户提供或搜索到具体文章链接时，优先尝试直接用 `browser_navigate` 打开。成功率一般（视站点反爬强度而定），但比搜索环节容易过。

**已知可用站点**：微信公众号文章（部分可读）、36氪新版页面（部分）、B站

### 方案C（备选）：Bing 英文搜索

对于技术类、英文内容，Bing 的英文搜索通常可用。

### 方案D（可配置，推荐）：Bright Data 企业级解封方案

**适用场景**：需要稳定获取百度/Google/知乎等中文站点搜索结果的场景，且愿意配置免费API Key。

**推荐产品**：
- **Bright Data SERP API** — 支持 Google、Bing、Yandex、DuckDuckGo 等多搜索引擎的结构化搜索结果API，自动处理反爬/CAPTCHA
- **Bright Data Discover API**（FREE）— 专为AI Agent设计的免费实时网页发现API
- **Bright Data MCP**（FREE）— MCP协议集成，可挂载为Hermes Agent的本地MCP工具，实现零配置搜索

**配置方式**（Bright Data MCP）：
```yaml
# ~/.hermes/config.yaml 的 mcp_servers 配置
mcp_servers:
  brightdata:
    command: npx
    args: ["@brightdata/mcp"]
    env:
      BRIGHTDATA_API_TOKEN: "your_token_here"
```

**竞争产品**：
- **SerpApi**（serpapi.com）— 支持百度搜索API，$50/月起，有免费试用额度
- **Oxylabs** — 企业级，支持百度，询价

### 方案E（终极手段）：升级 Browserbase 到 Scale 计划

Browserbase 的 Scale 计划（$499/月）包含 residential proxy + advanced stealth，可解锁大多数被封站点。在当前免费/基础版下触发较多反爬。

需要用户决策是否升级。

## 执行流程

当遇到中文搜索需求且标准搜索工具被拦截时：

1. **先查 memory / session**：确认是否已有相关数据
2. **判断场景**：
   - 找地址/公司位置 → 头条搜索 + 百度地图两步法（方案F）
   - 找附近门店 → 先走两步法定位，再百度地图搜品牌
   - 找文章/资讯 → 头条搜索（方案A）
   - 已知 URL → 浏览器直开（方案B）
3. **走头条搜索**：用 `browser_navigate` 打开 `so.toutiao.com/search?keyword=...`
4. **解析搜索结果**：头条搜索页面结构复杂，地址类查询在「综合」tab 下直接显示结构化结果；资讯类需切换到「资讯」tab
5. **如搜索结果不够**：尝试直接用 `browser_navigate` 打开已知URL
6. **如果都失败**：如实告知用户「目前查不到这个方向的数据」
7. **⚠️ 跳过 Nominatim**：对中国地址不要尝试 `nominatim.openstreetmap.org`，直接走头条/百度地图

## 头条搜索结果解析技巧

- 搜索结果在 "综合" tab 下，包含了视频、图文、百科等混合结果
- 点击 "资讯" tab 可以只看图文资讯
- 搜索结果中的文章标题可能被 `<em>` 标签高亮关键词
- 页面内容会被 `browser_snapshot` 截断（约8000字），需要用 `browser_console` + JS 获取完整内容
- 需要多次 `browser_scroll` 触发加载更多结果

### 方案F（地图 POI 搜索）：百度地图浏览器搜索

当用户需要查找附近门店、餐厅、咖啡店等地理位置类信息，且 OSM/Nominatim/Overpass 在中国大陆完全不可用时使用。

**两步法（最常用 — 先找地址再搜周边）**：
1. **头条搜地址**：`browser_navigate("https://so.toutiao.com/search/?dvpf=pc&keyword=公司名+区域+地址")` → snapshot 中提取地址（头条对地址类查询返回结构化结果，含街道门牌号）
2. **百度地图搜周边**：导航到 `https://map.baidu.com/`，在搜索框中先输入步骤1提取的地址定位地标，点击结果确认 → 再搜目标品牌/类型（如「瑞幸咖啡」）→ snapshot 提取店名列表

**单步法（已知地标名）**：
1. `browser_navigate("https://map.baidu.com/")`
2. 在搜索框中输入参照地标（如「创智云城A2栋」），点击结果定位
3. 再搜索目标品牌/类型（如「瑞幸咖啡」），Enter 搜索
4. 百度地图会按距离排序返回 POI 结果，从 snapshot 中提取店名即可

**注意**：百度地图的搜索结果不直接显示距离数，但按由近到远排列，比例尺在页面中以「X公里」文字显示。多区域同名公司需根据用户指定的区域筛选正确地址。

## Limitations

- 头条搜索不适用于需要精确、完整、结构化搜索结果的场景（如学术调研、竞品数据对比）
- 不建议用于搜索时效性要求不高的内容（头条的结果排序偏向近期）
- **头条 JS 渲染陷阱**：通过 curl 可获取元数据但无法提取 URL（见「JS 渲染陷阱」章节）
- 对于深度调研，仍建议使用专业SERP API（如 Bright Data、SerpApi）
- **OSM/Nominatim 对中国地址查询几乎不可用**：`nominatim.openstreetmap.org` 搜中文地址（如「创智云城 深圳」）稳定返回空结果。查找中国地址一律走头条搜索或百度地图，不要浪费时间尝试 Nominatim。

## JS 渲染陷阱：可见的元数据 vs 可提取的 URL

头条搜索的一个重要特性（也是常见陷阱）：搜索结果页是 JS 动态渲染的，通过 `curl` 等纯 HTTP 工具访问时：

- ✅ **你可以拿到丰富的元数据**：文章标题、摘要描述、发布来源（如「网易科技」「搜狐网」）、发布时间范围（如「2小时前」）——这些信息嵌在页面的 text content 中
- ❌ **你无法提取目标文章的 URL**：链接是 JS 加载后生成的，原生 HTML 中不包含 article 级别的外链

### 影响

这意味着头条搜索可以帮你 **发现文章存在**，但 **不能直接告诉你文章在哪**。你需要：

1. 从元数据中提取关键信息：文章标题、来源站点（如 `163.com`、`sohu.com`）、大致发布时间
2. 用这些信息构造针对目标站点的搜索或直接导航
3. 如果目标站点反爬同样严格，如实告知用户：文章标题和摘要已有，但原文 URL 无法获取

### 已知案例

| 场景 | 头条搜到 | 无法做的事 | 替代方案 |
|------|----------|-----------|---------|
| 晚点LatePost 公众号转载 | 标题「AI 季报 26Q2:从 coding 到 RSI」、来源「网易科技」、时间「1小时前」 | 无法提取 163.com 的文章 URL | 浏览器直接搜目标站点标题；或用元数据+领域知识完成分析 |
| 微信公众号文章 | 标题、摘要 | 无法提取 `mp.weixin.qq.com` 的链接 | 从其他转载站点入手；或让用户提供 URL |
| 知乎高赞回答 | 标题、摘要、赞数 | 无法提取知乎答案 URL | 知乎 403 场景下用摘要做分析 |

## 2026.7.6 实测验证：晚点LatePost + 全网反爬阻击

在此轮「AI 季报 26Q2」文章中验证了多引擎同时在中文场景被阻击的情况：

| 引擎 | 结果 | 原因 |
|------|------|------|
| Google | CAPTCHA 拦截 | `browser` 即使有 stealth 也触发 `sorry/index` |
| Bing | Cloudflare 验证 | 提交搜索后要求人工验证 |
| DuckDuckGo | 无法访问 | 触发反爬机制 |
| Toutiao (curl) | 元数据可用 ✅ | 成功获取标题、来源、发布时间，但无 URL |
| 163.com | SSL 证书错误 | `so.163.com` hostname mismatch |

**结论**：当中文内容全网反爬时，Toutiao 仍然是唯一可用的**发现**渠道（获取文章存在性和摘要），但无法获取原文链接。此时应用 domain knowledge 结合用户补充的信息来完成深度分析。

## Pitfalls

| 陷阱 | 表现 | 正确做法 |
|------|------|----------|
| Nominatim 搜中文地址 | 返回空数组 `[]` | 用头条搜索或百度地图替代 |
| 头条「综合」tab 混入无关视频 | 结果被抖音内容淹没 | 切换到「资讯」tab 过滤 |
| 百度地图 snapshot 不显示距离 | 只看到店名没有距离数 | 结果按距离排序，比例尺在页面有「X公里」文字；前几条即最近 |
| 头条搜索地址类查询返回多地址 | 同名公司在多个区有办公点 | 根据用户指定的区域（如「南山」）筛选对应地址

## 2026.5.7 实测验证

在本轮闲鱼调研中，头条搜索成功获取了以下有效信息源：
- CSDN博客（"在闲鱼上卖虚拟品赚了12w+"）
- 网易/36氪/知乎的搜索结果标题和摘要
- B站教学视频标题和标签
- 微头条/抖音内容片段

但头条搜索无法打开这些文章的具体内容（CSDN返回403，36氪文章404，知乎跳转验证码）。要获取文章全文，仍需用 `browser_navigate` 直接打开已知URL，或使用 SERP API。

当天同时验证了 Bright Data 企业级解决方案的存在（首次发现其有免费的 MCP 和 Discover API），可作为后续升级路径。

## 2026.6.30 实测验证

在中国地址查找 + 附近门店搜索场景中验证了两步法：

1. **头条搜地址**：「多科电子 南山总部 深圳 地址」→ 头条直接返回结构化结果：
   - 深圳市多科电子有限公司：玉塘街道玉律村汉海达科技创新园三栋8楼
   - 多科电子(卫东龙商务大厦店)：梅龙大道194号卫东龙商务大厦3栋13楼
   - 多科公司：**西丽街道留仙大道创智云城A2栋30楼**（南山总部）
2. **百度地图搜周边**：定位创智云城A2栋 → 搜「瑞幸咖啡」→ 返回 10 家门店，按距离排序（前3家最近：南山智谷店、紫云大厦店、长园新材A栋店）
3. **Nominatim 确认失败**：`nominatim.openstreetmap.org` 搜「创智云城 深圳」返回空数组，搜「创智云城A2栋 深圳 西丽 留仙大道」同样空。结论：中国地址不走 Nominatim。
