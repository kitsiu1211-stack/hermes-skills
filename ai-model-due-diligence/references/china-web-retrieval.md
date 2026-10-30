# 国内网络下的检索与正文抓取（实测 2026-09，macOS / 直连）

用于：需要搜中英文资料、官方文档站、技术博客时，浏览器通道不可用或很慢的场合。
配套：`chinese-search-workaround`（用户自有 skill，头条搜索细节在那里）。

## 1. 搜索通道可用性

| 通道 | 实测结果 | 说明 |
|---|---|---|
| `https://cn.bing.com/search?q=<关键词>` | ✅ 200，标题+摘要可用 | **首选**，中文结果质量够用 |
| `https://www.bing.com/search?q=<关键词>&setlang=zh-CN` | ✅ 200，结果完整（2026-10-26 复测） | 早前记的"302/177 字节"是缺 `setlang` 或 UA 不全；补上 Chrome UA 后可正常出结果 |
| `https://so.toutiao.com/search?keyword=<关键词>&pd=synthesis` | ✅ 200（返回 ~1.9MB JS 重页面） | 中文/头条系内容 |
| `https://html.duckduckgo.com/html/?q=...` | ❌ body 为空（len 0） | 别在这上面耗时间 |
| `https://www.baidu.com/s?wd=...` | ❌ 302，456 字节 | 无内容 |

正文侧（2026-10-26 实测）：

| 站 | 正文可否 curl 直取 |
|---|---|
| juejin.cn | ✅ 完整正文，`<script>` 去掉后按标签换行清洗即可 |
| huxiu.com | ❌ 只回 `{"traceid":...}` JSON（约 400 字节），**只有搜索结果的标题可用** |
| mp.weixin.qq.com | ✅ 走 `wechat-article-extraction` 的 extract.py，别自己写正则 |
| zhuanlan.zhihu.com | 大概率要 cookie，优先找转载或掘金/阿里云社区的同一篇文章 |
| api.npmjs.org / registry.npmjs.org / hn.algolia.com / api.github.com | ✅ 全部直连，无需 UA 伪装 |

必需请求头（缺了更容易被拦）：

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
```

## 2. cn.bing.com 提取结果链接

结果页的 `<a href>` 有 `bing.com/ck/a?...` 包装，真实 URL 在 `u=a1<base64>` 参数里：

```python
import re, base64, html

t = open('/tmp/cnbing.html', encoding='utf-8', errors='ignore').read()
urls = []
for m in re.findall(r'href="(https?://[^"]+)"', t):
    if any(d in m for d in ('bing.com', 'microsoft', 'msn.com')):
        continue
    urls.append(html.unescape(m))
for m in re.findall(r'u=a1([A-Za-z0-9_\-]+)', t):
    s = m + '=' * (-len(m) % 4)          # 补 padding，否则 b64 解码会抛错
    try:
        d = base64.urlsafe_b64decode(s).decode('utf-8', 'ignore')
        if d.startswith('http'):
            urls.append(d)
    except Exception:
        pass
print('\n'.join(dict.fromkeys(urls)))
```

标题/摘要在正文里就能直接读（把 `<script>/<style>` 去掉、标签换成空格后 `innerText` 式清洗），
但**要引用事实就必须 curl 正文**，摘要只能支撑摘要里字面写了的东西。

## 3. curl 抓正文 + 清洗（一次性配方）

```python
import re, html, urllib.request

UA = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 Chrome/126 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

def get(u, timeout=30):
    try:
        req = urllib.request.Request(u, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')
    except Exception as e:
        return f"ERR {e}"          # 单站失败不要中断整批

def txt(t):
    t = re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', '', t, flags=re.S)
    t = re.sub(r'<br\s*/?>|</p>|</div>|</h\d>|</li>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = html.unescape(t)
    return re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', t)).strip()
```

要点：

- **正文落盘再分段读**：`open('x.txt','w').write(txt(...))`，然后按关键词定位（`t.find('七、局限')`）切片打印，比一次 print 全文省很多 token。
- **`cd` 与 `-o` 目录要一致**：curl 写到 `/tmp/x.html`、python 又 `cd /tmp/jev` 后读 `x.html` → FileNotFoundError。跨目录时**全部用绝对路径**。
- **批处理容错**：每个 URL 单独 try/except 并把错误写成字符串，一个站 403 不影响其余。
- **中文技术文质量排序**：个人技术博客 / 博客园 / 腾讯云社区 / AI 科技评论（网易号）> 聚合站；深度复盘（含"局限""翻车"章节）优先。

## 4. 其他一手接口（不依赖搜索引擎）

```bash
# HN 搜索 + 全量评论（评论比网页版干净）
curl -sL "https://hn.algolia.com/api/v1/search?query=<名>&tags=story&hitsPerPage=20"
curl -sL "https://hn.algolia.com/api/v1/items/<story_id>"

# GitHub 元数据 / 关键词搜仓库（找第三方复刻、逆向实现）
curl -sL "https://api.github.com/repos/<owner>/<repo>"
curl -sL "https://api.github.com/search/repositories?q=<名>&sort=stars&per_page=10"

# 原始文件
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/main/README.md"
```

官方站若是 Framer/Webflow 这类建站工具生成的 SPA，HTML 里没有正文文本 → 直接抓 `/blog/<slug>` 这类的文章页，别去解析首页。
