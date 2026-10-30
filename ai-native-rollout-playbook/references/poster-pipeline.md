# 一页纸 → PNG 生产管线

客户材料用 HTML 手写再截图，比调 ljg-card 之类的成品模具更可控（也没有第三方 footer 品牌）。一次成型，改字只需 30 秒重出。

## 1. 环境（本机已具备，不需装 playwright）

`ljg-card` 的 `capture.js` 依赖 `playwright` 模块，本机没装；**但 ms-playwright 的 chromium 二进制在缓存里**，直接用全局 `puppeteer-core` 指过去即可：

```js
const puppeteer = require('/Users/bytedance/.npm-global/lib/node_modules/puppeteer-core');

(async () => {
  const [html, out] = process.argv.slice(2);
  const browser = await puppeteer.launch({
    executablePath: '/Users/bytedance/Library/Caches/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-mac-arm64/chrome-headless-shell',
    args: ['--no-sandbox', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1240, height: 1000, deviceScaleFactor: 2 });
  await page.goto('file://' + html, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 600));
  console.log('height:', await page.evaluate(() => document.body.scrollHeight));
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
```

- 视口宽固定 1240，`fullPage: true` 让高度自适应；`deviceScaleFactor: 2` 出 2480px 宽，手机上点开仍然清楚。
- 版本号目录（`chromium_headless_shell-1208`）会随 playwright 升级变化，找不到就 `find ~/Library/Caches/ms-playwright -name "chrome-headless-shell" -type f`。
- 中文字体直接写 `"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif`，headless 下渲染正常。

## 2. 版式 token（四页共用一套，视觉才成系列）

```
纸底  #F6F2EA     墨 #1B1A17     次要文字 #4A453B / #8A8272
Agent 侧（可判定）  #1B4A40 深 / #3E7F6E 中 / #E6F0EB 淡
人 侧（偏好）      #B4472A 砖红 / #4A2418 深 / #FBEDE4 淡
卡片底 #FFFDF8     描边 #E3DACA
```

- 纸底加一层 `radial-gradient(#D9D1C2 0.7px, transparent 0.7px) / 22px` 点阵，opacity .35，质感立刻上来但打印友好。
- 每页固定骨架：kicker（客户×飞书｜第 N 页 · 主题）→ 大标题（50px/800）→ 一句副标题 → 3px 短横线 → 3–5 个区块 → 深色结论条 → footer（日期 + 项目 + 页码语义）。
- 禁区：紫蓝渐变、三等分 hero、居中大标题、Inter 字体、纯黑 #000。

## 3. 常用模块

- **判据条**：深色圆角卡，一句大问句 + 左右两个有色分支（能/不能），每支给「谁承接 + 承接什么」。
- **四栏流程**：`flex` 等宽卡，每栏底部一条 5px 进度条表示「可被规则校验的比例」，比写百分比更有冲击力。
- **甘特**：用 `display:grid; grid-template-columns:160px repeat(10,1fr)`，**别用 flex + gap**，否则表头与格子会错位几像素。
- **两栏对照（错的做法 / 对的做法）**：淡米 vs 淡绿，标题用「错 的 做 法」字间距撑开。
- **结论条**：深底 + 一句话，字号 21–23px，行高 1.6。

## 4. 排版踩坑（这几条每页都遇得到）

- **中文断词**：一句话里出现「业务流」被拆成「业 / 务流」这种，就是容器宽度差 3px。改法：缩短句子、显式 `<br>` 控行、或把 `max-width` 放宽 20px。**不要**用 `word-break: break-all`。
- **孤字成行**：标题尾部只剩一个字（如「…一个环节节」）。改法：拆成两行，第二行用 `·` 分隔的短词组合。
- **卡片高度不齐**：父容器 `display:flex` + 子项 `display:flex` + 内部 `width:100%`，底部标签用 `margin-top:auto` 顶到同一基线。
- **深色卡留白过多**：给深色那一侧加 `justify-content:center`，或补一行内容，别让它在视觉上下沉。
- **窄框里再断词**：判断框那种 190px 宽的卡片，正文控制在 10 字以内。

## 5. 出图后必须自查一遍

用 `vision_analyze` 看渲染结果，逐条问：有没有溢出/裁切/重叠、断词孤行、色块文字是否居中、几栏是否对齐、整体能不能当客户材料。

实测四页里每页都要改 1–2 轮才干净，别指望一次成型；改完重出只要几秒，比在会议桌上被客户指出排版问题便宜得多。
