# 公众号文章历史分析（批量统计用户分享过哪些文章）

触发：用户问「过去 N 个月我发了多少篇公众号文章」「哪个公众号最多」「文章分类」等回顾型问题。

## 流程（2026-08-21 验证，178 篇全量成功）

### 1. 从 state.db 捞全部链接

```sql
-- 用户消息里所有含 mp.weixin.qq.com 的（注意列名是 timestamp 不是 created_at）
SELECT id, session_id, content, timestamp FROM messages
WHERE role='user' AND content LIKE '%mp.weixin.qq.com%'
  AND timestamp >= strftime('%s','2026-02-21 00:00:00','utc')
ORDER BY timestamp;
```

- 链接正则：`https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_\-]+`
- 同一 URL 可能多次出现（引用、重发），**按 URL 去重**，保留最早日期
- 月份边界注意：Hermes 可能 4 月中旬才启用，早于启用的月份无数据——如实说明，别编

### 2. 批量抓标题+公众号（关键坑）

`og:author` meta **经常为空**，不能只信它。提取优先级：

1. `<meta property="og:title" content="...">` → 标题
2. `og:author` → 公众号（常空）
3. `var nickname = '...'` → 公众号（**实际主力来源**，iPhone UA 下有效）
4. `var msg_title = '...'` → 标题兜底

并发抓取：`ThreadPoolExecutor(max_workers=6)`，每个 URL `curl -sL --max-time 12 -A "iPhone UA"`。178 篇约 3-4 分钟。抓到后按 URL 合并回 meta dict。

### 3. 标题特征补全

仍空的公众号用标题特征推断（`【经纬低调分享】`/`【经纬低调出品】` → 经纬创投；含「晚点」→ 晚点LatePost；`｜Hao` → Hao好聊）。已知个案可手补（吴声演讲→正和岛）。

### 4. 主题分类（关键词规则）

用包含判断而非精确匹配，关键词要覆盖中英文变体：
- AI/Agent/工具：Harness、Skill、Prompt、Agent、智能体、Claude、Codex、DeepSeek、GLM、Kimi、模型、Token、LLM、大模型、AI Coding、Loop、SDLC、蒸馏、Scaling、AI Native、AI原生、FDE、豆包、Seedance、Qwen、TTS、RAG、Anthropic、OpenAI、世界模型、AI中间层、硅基…
- 企业/组织/办公：飞书、钉钉、企业微信、火山引擎、SaaS、To B、ToB、组织、员工…
- 资本/投资：投资、估值、融资、IPO、资本、收购、市值、财报、红杉、龙珠、VC、创始人…
- 宏观/财经：中国、美国、经济、出口、政治局、政策、半导体、芯片、A股、宏观、产业…
- 消费/出海：跨境、电商、出海、品牌、营销、增长、小红书、种草、直播、零售、门店…

首轮分类后检查「其他」类，逐条手动归正（标题含 AI 但漏关键词的，如「花800块钱找点罪受」→ 消费/出海）。

### 5. 输出

飞书卡片：顶部 column_set 四数字（总数/AI占比/最高产公众号/单月高峰）→ 月度节奏 → 主题分布 → 公众号 Top5 → AI 占比趋势（可结合用户工作节奏解读，如 TRAE 直播/FDE 定位）→ note 标注统计口径。

## Pitfalls

- 公众号名抓不到时**不要**编造——标「其他/未知」，用标题特征只补有把握的
- 分类关键词首轮总会有漏，必须跑一遍「其他」清单人工过目
- 统计口径写进 note：起止日期 + 去重方式 + 数据源（Hermes 会话库）
