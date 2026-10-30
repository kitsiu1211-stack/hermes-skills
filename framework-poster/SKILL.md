---
name: framework-poster
description: "Use when 要把分析做成一张可发群的框架图/一页纸 PNG。"
version: "1.0.0"
author: hermes-curator
license: MIT
metadata:
  requires:
    bins: ["node"]
  hermes:
    tags: [poster, infographic, html-to-png, client-deliverable]
    related_skills: [ljg-card, baoyu-design, beautiful-feishu-whiteboard]
---

# 一页纸框架图（framework-poster）

把一段口头/文字分析压成**一张可转发的图**：结论先给、模块分层、客户能当场看。

## When to Use / 何时用、何时不用

- **用**：客户诊断结论、方法论框架、会后跟进材料、给老板/客户"一眼看到"的结构图。
- **不用**：
  - 情绪化阅读卡、小红书大字卡 → `ljg-card`（注意：它的模板带第三方作者 footer，客户材料不能直接交付）。
  - UI mockup / 落地页 / PPT → `baoyu-design`（流程重，要问一堆问题）。
  - 飞书原生画板 → `beautiful-feishu-whiteboard`。

## 为什么自建 HTML，不套现成模板

1. 对外材料不能带别人的品牌 footer。
2. 框架图结构每次都不一样（判据条 / 流程栏 / 分拣机 / 风险+解药），模板会逼你削内容。
3. HTML 到 PNG 全可控：字重、对齐、2x 清晰度；客户要改一个词，30 秒重出。

## 五步

1. **先定主线一句话**——用户自己那句判断就是标题，别另起一个中性标题。
   例："别在每个环节加 Agent，先把流程切成「可判定」与「偏好型」"。
2. **选版式模块**（见下面 poster grammar），先画骨架再填字，不要边写边排版。
3. **复制 `templates/poster.html`**，替换内容；配色/字号体系保留，只改文字和色值。
4. **出图**：`node scripts/shot.js in.html out.png 1240 2`（宽 1240、2x → 2480px，A4 比例）。
5. **自检 → 交付**：见"自检"与"交付"两节，**自检必做**。

## Poster grammar（可复用版式模块）

| 模块 | 结构 | 作用 |
|---|---|---|
| 判据条 | 顶部深色卡：一个大问句 + 左右两个分支（各给"谁承接 + 干什么"） | 全图只回答一个问题，读者 5 秒抓住主线 |
| 分度栏 | 3–4 栏横向，每栏底部一根比例条 + 百分比 | 让"程度差异"可视化，比文字列表有说服力 |
| 分拣机 | 左一个原始输入（引语卡）→ 中部箭头 → 右侧两条通道（各给"进哪个库 + 后果"） | 把抽象边界落成一道可执行工序 |
| 风险 + 解药 | 左深色讲死亡螺旋（箭头链），右白底给 3 条带编号的机制 | 先制造痛感再给办法，客户不会只记住问题 |
| 结论条 | 底部深色：一句加粗结论 + 两行解释 | 决定这张图会不会被转发 |

每块给 `01/02/03` 编号，并在右上角加一句"这一栏为什么值得看"（如"这是企业唯一能攒下来的 AI 资产"）。

## 设计约束（都是踩过的坑）

- **CJK 断词**：固定 `max-width` 下中文会在词中断行（出现过 "AI，业 / 务流"）。→ 用显式 `<br>` 控制换行点，别指望自动折行。
- **不要改第三方模板的 footer/branding**：客户材料里出现别人的名字就废了，所以自建。
- **2x + fullPage**：`deviceScaleFactor=2`，高度由内容撑开（`document.body.scrollHeight`），别写死。
- **字号下限**：正文 12.5px、注解 11.5px（以 1240 宽为 1x 基准），再小手机上必须放大会烦。
- **配色**：纸白 `#F6F2EA` / 墨 `#1B1A17` / "可判定"墨绿 `#1B4A40` / "偏好"砖红 `#B4472A`。禁紫蓝渐变、禁纯黑、禁"三等分卡片凑数"。
- **数字优先**：写"影响 3 个环节、2 份提案、6 人日"，不写"影响很大"。形容词会让老板反感，数字不会。
- 侧栏高度不齐时给容器加 `display:flex; flex-direction:column; justify-content:center`，别留一大片空底。

## 自检（Generator → Evaluator，必做）

出图后 `vision_analyze` 问四件事：
1. 有没有文字溢出 / 截断 / 重叠？
2. 各区块是否对齐（卡片高度、横条宽度）？
3. 哪里空、哪里挤？
4. 能不能直接当正式客户材料发出去？

不合格就改 CSS 重出，**最多 2 轮**（第 3 轮收益极低，先交付再按反馈改）。

## 交付

- 先发 `MEDIA:/绝对路径.png`，再跟 3–5 行文字：**每一块在图里起什么作用**（不是复述图上的字），最后给源文件路径 + 一句"要不要再出极简版 / 换客户配色"。
- 源 HTML 留在原处并告知路径，客户改词时只改 HTML 重跑 `shot.js`。

## 支持文件

- `scripts/shot.js` — HTML → PNG，自动定位 puppeteer-core 与 chromium。
- `templates/poster.html` — 完整骨架（判据条 + 分度栏 + 分拣机 + 风险解药 + 结论条），已调好 CJK 字体与配色。
- `references/example-ai-process-attribution.md` — 一次真实交付的完整论证骨架（客户 AI 流程改造的"可判定性归因"），做同类主题时直接复用结构。
