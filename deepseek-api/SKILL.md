---
name: deepseek-api
description: DeepSeek 模型/定价/版本管理与 Hermes 路由控成本。Use when 问涨价/价格/切模型。
category: mlops
---

# DeepSeek API 模型与定价

用户（袁鑫杰）的 Hermes 跑在 DeepSeek 上，且高度关注成本和模型版本。涉及 DeepSeek 模型名、涨价、价格、V4、Flash/Pro、缓存命中、是否切模型的提问，用本技能快速给出有来源的结论，不靠记忆猜。

## 模型命名（稳定，调用方式不变）

- 旗舰：`deepseek-v4-pro`，底层版本 `DeepSeek-V4-Pro-0813`
- 轻量：`deepseek-v4-flash`，底层版本 `DeepSeek-V4-Flash-0731`
- 调用时写短名（`deepseek-v4-pro` / `deepseek-v4-flash`）即可，官方自动路由到最新底层版本，改版本不用改代码。
- 两模型均支持 thinking/non-thinking、JSON Output、Tool Calls、Responses API、Anthropic API，上下文 1M，max output 384K。

## 定价结构（峰谷计费，长期结构）

DeepSeek 已从单一价改为**峰谷计费**，谷价 = 峰价的一半（2026-08 起生效）。

- 峰值时段（UTC）01:00–04:00 与 06:00–10:00 → **北京时间 9–12 点、14–18 点**（用户的白天工作时间基本都在峰价）。
- 其余时段半价。夜间跑的 cron/后台任务天然走谷价。

每 100 万 token 的价签形状（**具体美元数字会变，查证以官方页为准，别背数字**）：

| 档位 | 输入(缓存命中) | 输入(未命中) | 输出 |
|---|---|---|---|
| Pro 峰值 | 约 $0.044 | 约 $1.32 | 约 $3.96 |
| Flash 峰值 | 约 $0.014 | 约 $0.44 | 约 $1.32 |

Flash 三条线基本是 Pro 的约 1/3 价格。

## 如何查当前价格（验证优先，不背数字）

1. **价格表**：`browser_navigate https://api-docs.deepseek.com/quick_start/pricing`。该页 JS 渲染，`curl -L | grep` 拿不到价格数字（返回空），必须走浏览器 snapshot，表格会完整吐出来。
2. **模型名/版本**：任意 API docs 页用 `curl -sL` 就能看到模型名和底层版本号，不需要浏览器。
3. 用户画像要求「结论需官方来源验证」——涉及价格、模型能力，先查官方 docs 再下结论，别引用二手公众号数字当事实。

## 涨价/切模型的判断口径（本用户场景）

- 别只看「缓存命中涨 N 倍」这种标题党数字。命中价基数极小（$0.0036→$0.044），涨 12 倍绝对值仍可忽略。
- 真正花钱的大头是**输出价**和**未命中输入价**。
- 用户量低（销售，非 7x24 写代码），峰值 Pro 一个月也就几刀。深度推理活（文章分析 Rank-Learn-Plain、会议纪要合成、多 Agent 编排）用 Flash 会掉质量。
- ⚠️ **路由方案 2026-08-16 已反转**：此前是「Pro 兜底 + 简单消息自动走 Flash」；用户当天明确表态「pro 太费钱、日常没什么任务需要 pro」，拍板改成**默认 Flash、整切 Flash、routing 关闭**，仅明确要求时才切回 Pro。别再推荐「调路由阈值 / Pro 兜底」的旧方案——那已被否掉。真遇到深度任务质量下降，也只对**那一个**任务（如每周深读推荐、每日认知对话）单独切回 Pro，其余保持 Flash。

## Hermes 模型路由（成本控制主杠杆）

`model.routing` 段是 Hermes 自带的「简单消息自动走便宜模型」功能，bundled hermes-agent skill 里没写，这里补上：

```yaml
model:
  default: deepseek-v4-pro
  routing:
    enabled: true
    cheap_model:
      provider: deepseek
      model: deepseek-v4-flash
    max_simple_chars: 500   # 短消息自动降级到 flash
    max_simple_words: 80
```

- 改阈值：`hermes config set model.routing.max_simple_chars 500`（同理 `max_simple_words`）。注意 key 前缀是 `model.routing.*`，不是顶层 `routing.*`。
- 改动需重启 gateway 才生效，当前会话不受影响。
- 阈值是「简单」判据：字符数/词数低于阈值 → 走 cheap_model。中文消息主要看 `max_simple_chars`。
- 关掉路由 / 换默认模型：`hermes config set model.routing.enabled false` + `hermes config set model.default deepseek-v4-flash`。

## 切默认模型必做：同步 cron 任务（否则定时任务会 fail closed）

`hermes config set model.default ...` 成功后，若 cron 里有任务存的 `model`/`model_snapshot` 跟新全局默认不一致，Hermes 会警告：**unpinned（`model: null` 但有 `model_snapshot`）的任务下次运行会 fail closed 静默挂掉**；显式 `model: xxx` 的任务则继续用旧模型（不会跟默认，也浪费钱）。所以切默认模型后必须扫一遍所有 cron 任务并显式改模型：

```bash
# 1. 列出所有任务，逐个看 model / model_snapshot 字段
hermes cron list   # 或直接读 ~/.hermes/cron/jobs.json

# 2. 逐个改模型（正确命令，走 CLI）
hermes cron edit <job_id> --model deepseek-v4-flash --provider deepseek
```

⚠️ **坑**：`cronjob` 工具的 `action=update` **没有** `model` / `provider` 参数，传了会报 `No updates provided.`。warning 里那行 `cronjob action=update job_id=... provider=... model=...` 提示是误导，别照做——正解是上面的 `hermes cron edit`。

## 缓存命中 vs 未命中（给用户/客户讲价用白话）

- **缓存命中**：这次输入里跟上次重复、能复用缓存的部分（系统提示词、记忆、技能、历史对话前缀），几乎免费。
- **缓存未命中**：输入里新冒出来、缓存没有、必须从头算的部分，贵。
- 类比：每天走同一条上班路，前 80% 闭眼都认识（命中，免费），最后 20% 新路才要认真看（未命中，全价）。
- 账单上真正花钱的是「未命中输入 + 输出」，命中价再涨也是零头。
