# 转写里的名词 → 厂商官方事实：查证打法

**适用**：会议/直播/长文里冒出一个产品名，用户当场问「X 是什么 / 是不是等于 Y / 跟 Z 像不像」。
名字多半是 **ASR 听来的**（英文名尤甚），所以第一件事不是搜，是**对齐名字**。

---

## 0. 名字先对齐（在开会中提问时这一步最关键）

1. 先 grep 实时转写拿**上下文原话**，不要凭用户给的字面直接搜：

```bash
grep -n -i "tag\|claude\|<关键词>" ~/meeting_logs/<meeting_id>.jsonl
# 或按说话人过滤：python3 -c "import json;..." 只打某人句子
```

实测：会上 ASR 输出「**克劳 Tag**」，实为 Anthropic 的 **Claude Tag**；同一段里还出现过「克劳在 6 月份发布」。
字面直搜「克劳 Tag」= 零结果，直接搜会把答案带偏。

2. 判断是**营销名**还是**产品真名**：官网导航上的链接文字常是营销名（`@Claude`），URL slug 才是真名（`/product/tag`）。

3. 字面搜不到时**不要下「查不到 / 不存在」的结论**——先换拼写、换厂商、换语言再试。

---

## 1. 厂商官网是唯一权威源（curl 就能拿，别先搜）

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"

# ① 产品集合页 / 新闻页 → 抓导航与链接文字，拿真实 slug
curl -sL -A "$UA" "https://<vendor>/news" -o /tmp/news.html
python3 - <<'EOF'
import re
t = open('/tmp/news.html', encoding='utf-8', errors='ignore').read()
for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{0,60})', t):
    if '<关键词>' in m.group(2) or '<关键词>' in m.group(1):
        print(m.group(2), '->', m.group(1))
EOF

# ② 产品页正文 = 官方定位原话，可直接引用
curl -sL -A "$UA" "https://<vendor>/product/<slug>" -o /tmp/prod.html
python3 -c "import re,html;t=re.sub(r'<(script|style)[^>]*>.*?</\1>',' ',open('/tmp/prod.html',encoding='utf-8',errors='ignore').read(),flags=re.S);print(re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))[:6000])"
```

---

## 2. 拿官方发布时间：grep 页面内嵌的 JSON

新闻页/产品页虽然 JS 渲染，HTML 里通常内嵌 **Next.js flight / Sanity / __NEXT_DATA__** 数据，
`grep` 就能拿到结构化事实（比二手报道可信）：

```bash
grep -o "Tag[^<]\{0,80\}" /tmp/news.html | head
# → "...Tag is a new way for teams to work with Claude.","title":"Introducing Claude Ta..." 
```

```python
i = t.find('Introducing Claude Ta')
print(t[max(0, i-1500):i+600])   # 拿到 publishedOn / slug.current / summary / title
```

实测产出（2026-09-20 核实）：

| 字段 | 值 |
|---|---|
| 公告标题 | `Introducing Claude Tag` |
| publishedOn | `2026-06-23T14:00:00.000Z` |
| slug | `introducing-claude-tag` → `anthropic.com/news/introducing-claude-tag` |
| 产品页 | `claude.com/product/tag`（营销名 `@Claude`） |

用品类里的一句话定位原话（可直接引用）：
> "Claude Tag is a new way for teams to work with Claude... We're starting on Slack, which Claude can join as a team member."（beta，Claude Enterprise / Team；官方页显示后续上 Microsoft Teams）

---

## 3. 搜索引擎只当兜底

实测同一轮里：DuckDuckGo html 端点返回 **0 字节**；Bing 首页 **302** 到 `cn.bing.com`；Bing 结果区 / Bing news 结果区是 **JS 渲染**，正则抓不到条目。
→ **优先直接打厂商域名**，别在搜索上耗轮次；需要搜索时用能返回 HTML 的端点并跟随重定向（`curl -sL` + `-c cookiejar`）。

---

## 4. 回答结构：用户要的是**判断**，不是资料

1. **第一行给是非判断** —— 例：「是——Claude Tag 就是团队智能体」。别铺垫。
2. 官方定义 + 官方原话（带**发布日**，可引用）
3. **说人话的类比** —— 例：个人 AI 助理 = 私人秘书；团队智能体 = 进群的同事（谁都能 @ 它、它记得群里的事）
4. 关键机制/差异点（3-4 条，每条一句话）
5. **对用户身份的意义** —— 客户会怎么问、该怎么答（这一步决定这条回答有没有用）
6. 末尾附来源链接（`厂商产品页 ｜ 官方公告页`）

---

## 5. 常见坑

- **把「搜索不到」当成「不存在」** → 先怀疑名字（ASR 听歪 / 营销名 vs 产品真名 / 中英文名不同），再怀疑检索通道被挡
- **只给资料不给判断** → 用户问「是不是 X」时，第一行必须是是/不是/部分类似，依据排后面
- **拿搜索结果摘要当事实** → 厂商官网产品页 / 官方公告才是权威；摘要只用于找入口
- **靠传闻写发布时间**（「好像是 6 月发的」）→ 官网内嵌 JSON 里有确定的 `publishedOn`，取它
- **忘记把结论带回用户的工作场景** → 同一个事实，对客户话术的价值 > 对概念的转述
