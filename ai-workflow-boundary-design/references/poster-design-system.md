# 中文咨询海报设计系统（HTML → PNG）

一套已经验证过的版式。目标：客户会上投屏能看清、手机上点开能读、发到群里不像 AI 生成物。
产出形态：1240px 宽、高度自适应、`deviceScaleFactor=2`（2480px 输出）。

## 画布与渲染

```bash
node scripts/render_png.js poster.html out.png 1240 2
```

- `body { width:1240px }`，**不要**给 body 写死高度，让内容自然撑开，脚本自己量 `scrollHeight`
- 每个文件就是一个独立 poster，三页材料 = 三个 HTML 文件（方便单独改单页）
- 输出到 `~/Downloads/`，命名带序号：`1-归因.png / 2-推进路径.png / 3-责任机制.png`

## 配色（已在客户材料上验证，避开 AI 味紫蓝渐变）

| 用途 | 值 |
|---|---|
| 纸底 | `#F6F2EA` |
| 墨（正文/标题） | `#1B1A17` |
| 次级文字 | `#4A453B` / `#8A8272` / `#A79C86` |
| 卡底 | `#FFFDF8`，描边 `#E3DACA` |
| Agent / 可判定 | 深墨绿 `#1B4A40`、`#173B34`、亮绿 `#5E9E8C`、`#7FBFA9` |
| 人 / 偏好 / 风险 | 砖红 `#B4472A`、`#4A2418`、`#D5794F`、`#E89B72` |
| 中性过渡 | 橄榄 `#8A8B5C` |

- 背景加一层 `radial-gradient(#D9D1C2 0.7px, transparent 0.7px) / 22px` 点阵，opacity .35，纸质感立刻出来
- **禁止**：三等分卡片、居中 Hero、纯黑 `#000`、紫蓝渐变

## 字体与字号

`"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif`；`antialiased`。

| 元素 | 字号 |
|---|---|
| kicker（顶部小标 + 栏目标签） | 11.5–12.5px，`letter-spacing:.2em` |
| h1 | 50–52px / 800 / `line-height:1.2` / `letter-spacing:-.8px` |
| sub 导语 | 16.5px / `line-height:1.8`，最高 2–3 行 |
| section 标题 | 22px / 800 |
| 卡片标题 | 15.5–19px / 800 |
| 正文 | 13–13.5px / `line-height:1.65` |
| 卡内 bullet | 12.5px |

## 区块语法（从上到下）

1. `.kicker` — `客户名 × 飞书 ｜ 第 N 页 · 主题`
2. `h1` — 一句反常识的判断，关键词上色（`<em class="h">` 砖红 / `<em class="a">` 墨绿）
3. `.sub` — 2 行导语，**第二行是转折**，`<br>` 手动断行
4. `.rule` — 96×3px 短墨线，比整条分隔线高级
5. 若干 `.sec` — 每个含 `sec-head`（黑底序号 + 标题 + 右对齐灰注释）
6. `.end` — 深底一句话结论，全文只允许这一处"大口号"
7. `.foot` — 日期 · 项目名 + 右侧 `FDE 前置咨询 · 主题`

区块类型选型：
- 对照关系 → `table`（表头灰底 `#F1EADB`，行分隔 `#EFE7D8`，关键格上砖红/墨绿）
- 两条路径对比 → `.tracks`（左右深色卡，各一条竖排 `flowline`：圆点 + 竖线 + 标题 + 一行说明）
- 阶段演进 → `.stages`（三卡 + `→` 间隔，卡片底部 badge 用 `margin-top:auto` 对齐）
- 并列原则/护栏 → `.guards`（三张深底卡）
- 一个判据的金句 → `.test`（整条黑底 + 左右两个判断框）

## 三个必须做的排版动作

```css
/* 1. 同行卡片等高，badge 贴底对齐 */
.row { display:flex; align-items:stretch; }
.cell { flex:1; display:flex; }
.card { width:100%; display:flex; flex-direction:column; }
.card .badge { margin-top:auto; align-self:flex-start; }

/* 2. 深色卡内容垂直居中，避免半侧留白 */
.dark-card { display:flex; flex-direction:column; justify-content:center; }

/* 3. 引语卡用左边框立住，别用巨大的引号字符（渲染成一个小黑点） */
.quote { border-left:4px solid #B4472A; }
```

## 质检清单（出图后必须看一眼）

- [ ] **中文词中断行**：`「不卡，只是变慢 → 玩具」` 会被折成「玩／具」。中文断词比英文难看十倍。修法：加宽容器（`.verdict{width:192px}`）、缩短文案、或手动 `<br>`。
- [ ] **标题下导语断行**：`业务流一点没变` 被拆到两行中间。修法：`max-width` 给到 1050–1080px + 显式 `<br>` 控节奏。
- [ ] **卡片高度不齐**：badge/按钮类元素浮在文字下方 → 用上面第 1 条 CSS。
- [ ] **深色卡半侧空**：内容只占上半 → 用第 2 条 CSS。
- [ ] **badge 过长**：`人的角色：定标准 · 看指标 · 处理例外` 会变成一条像按钮的长胶囊 → 拆成两行正文 + 短 badge（`授权额度上调`）。

改完重出图只要 3 秒，宁可多迭代一轮也不要交出断字的图。
