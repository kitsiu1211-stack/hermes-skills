# Anatomy 在 Hermes 上的安装与验证（2026-10-15）

## 来源与安装

- 上游：https://github.com/wheresryan22/anatomy （MIT，10.7k stars，作者 wheresryan22，卡兹克 2026-10 推荐）
- 安装位置：`~/.hermes/skills/anatomy/`（Hermes 顶层 skill，无 category）
- 源仓库副本：`~/Documents/Codex_Project/anatomy/`

## 🚨 安装坑

- **`git clone github.com` 在本机不通**（75s 超时）。可用通道是 codeload：
  ```bash
  curl -sL --max-time 60 -o anatomy.tgz "https://codeload.github.com/wheresryan22/anatomy/tar.gz/refs/heads/main"
  mkdir anatomy && tar xzf anatomy.tgz -C anatomy --strip-components=1
  ```
  `api.github.com` 通，`raw.githubusercontent.com` 不通（返回 000）。升级版本时同样走 codeload。
- 用 `rsync -a --delete --exclude '.git'` 同步到 skills 目录，**不要**用 skill_manage(create) —— 仓库带 `kit/ examples/ scripts/ tests/ agents/ evals/` 等非标准子目录，会被写入规则拦掉。
- 安装后总体积约 12MB（examples 里的 HTML 图画就占大头），可接受。

## 依赖（零 npm 依赖）

| 需求 | 本机状态 |
|---|---|
| Node.js ≥ 20.10 | ✅ v24.13.0（`/usr/local/bin/node`） |
| Chrome / Chromium（截图与校验） | ✅ `/Applications/Google Chrome.app` |
| npm 包 | 不需要，无 package.json，脚本是纯 ESM |

## 验证过的命令链

```bash
cd ~/.hermes/skills/anatomy
node examples/dial-indicator/build.mjs            # 写 HTML，1324×994 渲染
node examples/dial-indicator/build.mjs --light    # 浅色主题版本
node scripts/capture.mjs examples/dial-indicator/dial-indicator.html --out /tmp/shot.png
node scripts/capture.mjs examples/dial-indicator/dial-indicator-light.html --out /tmp/shot_light.png
```

`capture.mjs` 会打印 clip 尺寸、画内 readout 文本、console 是否干净，并把 PNG 写到 `--out`。
**`--out` 给的路径不带扩展名时不会自动补 `.png`**，拿到的文件是 PNG 但没后缀，`vision_analyze` 前先 `cp x x.png`。

## ⚠️ 成本提示（对用户讲清楚）

这个 skill 是 **token 重型**的。一个 Figure（40–80 零件）意味着：

1. 先写 parts list + 一句话机理（这一步决定质量）
2. 写一份 300–1500 行的 `build.mjs`（每个零件都是坐标 + 材质 + 明暗）
3. 循环 `capture.mjs` + 自己读 PNG 找崩坏 → 改代码（通常 3–6 轮）
4. 有管道/曲面件时还要跑 `node build.mjs --audit`，必须 `audit passed` 且各项为 0

建议节奏：**先用最小 Figure 验证手感**，再上工作坊级（Hero）。别一上来点 Epic。

## 用法速记

- 一行提示词形态：`/anatomy explain how a mechanical watch keeps time, interactive`
- 核心设计律：**The object is the explanation** —— 不要画方块和箭头，要造一台「它的运转本身就是这个概念」的真机器。
- 尺寸分档：Figure（40–80 零件，≤1 小时）/ Hero（80–150 零件，2–4 小时）/ Epic（6 小时+，别擅自开始）
- 开工前必读最近的 example（`examples/dial-indicator` 最小，约 300 行，是最佳起手参考）
- 全套工艺规则在 `references/craft.md`，校验清单在 `references/verify.md`
