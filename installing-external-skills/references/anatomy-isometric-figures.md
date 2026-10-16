# 实测案例：Anatomy（等距 SVG 原理图 skill）

上游 https://github.com/wheresryan22/anatomy （MIT，10k+ stars）。一句话让 AI 把抽象原理做成**可交互的等距机械插图**（一行提示词 `/anatomy explain how a mechanical watch keeps time, interactive`），核心理念 *The object is the explanation* —— 不画方块和箭头，造一台「它的运转本身就是这个概念」的真机器。

## 安装（2026-10-15 实测）

- 落地：`~/.hermes/skills/anatomy/`（12MB，含 8 个官方示例）· 源副本 `~/Documents/Codex_Project/anatomy/`
- 依赖：Node ≥ 20.10（本机 v24.13.0）+ 本机 Chrome；**零 npm 依赖**（无 package.json，纯 ESM）
- 坑：`git clone github.com` 超时、`raw.githubusercontent.com` 不通 → 走 **codeload tarball**（见主 SKILL.md 第 2 步）
- 坑：仓库有 `kit/ examples/ scripts/ tests/ agents/ evals/` 非标准子目录 → 必须 `rsync -a --delete --exclude '.git'`，不能用 skill_manage(create)

冒烟测试（装完必跑）：

```bash
cd ~/.hermes/skills/anatomy
node examples/dial-indicator/build.mjs && node examples/dial-indicator/build.mjs --light
node scripts/capture.mjs examples/dial-indicator/dial-indicator.html --out /tmp/shot.png
# capture 打印：clip 尺寸 / 画内 readout / console 是否干净
```

`capture.mjs --out` 的路径**不自动补 `.png`**：拿到的是无后缀 PNG，`vision_analyze` 前先 `cp x x.png`。

## 构建循环（已跑通）

1. **只读两段文档**，不要全文通读 `craft.md`(50KB)+`kit.md`(68KB)：
   - 零件配方 → `craft.md` 第 3 节 Parts vocabulary + 第 4 节 tones + 第 5 节 painter's order
   - 函数签名 → `kit.md` 第 2~8 节（相机/实体/面上线/零件库/移动/卡片，约 110 行）
   - 模板抄 `examples/dial-indicator/build.mjs`（275 行，最小且已验证）
2. **真值先行**：把被解释对象的真实数字抽成纯 `model.mjs`，build 与 live 都从它取值；真值出处写进文件头注释。实测这样「读数正确」第一轮就成立，不返工。
3. 循环（每轮约一分钟）：`node build.mjs && node build.mjs --light` → `scripts/capture.mjs` 出深/浅两张 PNG → **用 `vision_analyze` 自己读图**（先读浅色版，paper 主题最容易看出崩坏）。`console: clean` 才说明 live 脚本没报错。
4. 有管道/曲面件（`tube.mjs` / `lathe.mjs`）时才需要 `node build.mjs --audit`，必须 `audit passed` 各项为 0；只用 `slabOf`/`cylinder`/线/点的 Figure 不需要跑 audit。

## 第一张图实测返工的三处（下次直接规避）

1. **亮件被挡住 = 主角消失。** 给滑块上的探头设了 `lit`，但滑块本体把它压在下面，1× 图里根本看不见。修法：抬高承载件（导轨 z 8 → 15），让 lit 件从滑块下方明确伸出、底面**贴在被测面顶面**（flush contact）。任何「滑块 + 探针/触头」机构先查这一条。
2. **世界里分得开 ≠ 屏幕上分得开。** 计数器滚筒原放后左角，与滑块停靠位在屏幕空间糊在一起。修法：挪到**前方那片空底板**上——一次解决两个问题（去重叠 + 填空面板）。同一 y 带、不同高度的两件必须错开 x。
3. **空面板 = 没做完**（craft.md 反模式明写）。底板露出大片无零件的面就是未完成；补法是加**有叙事功能的零件**而非纯装饰（我加了「五路进线模块」= 5 个带滚花的圆柱口 + 螺钉，并把标签牌挪到后左角）。

## 可复制的成品模板

`~/.hermes/skills/anatomy/examples/context-manifold/` —— 约 46 个实体的完整 Figure（底板 / 脚 / 导轨 / 立柱 / 行程挡块 / 5 个料位 / 汇流头 + 探针 / 表盘立柱 / 计数器滚筒 / 进线条），含 `model.mjs` + `build.mjs`；交互 = 指针沿 x 吸附到最近料位 + 方向键 + 空转 tour，读数由 model 给出。用途：给客户/工作坊讲「豆包工作怎么把上下文接进来」。**下一个新图直接从它抄结构**，比从 dial-indicator 起步省一轮。

> ⚠️ 该目录在 anatomy skill 内部，属于**用户所属**目录（`created_by=None`）。上游更新覆盖安装、或用户在别处重装时，这个模板会一起丢掉 —— 要长期留用就复制到自己的工作目录。

## 成本（对用户必须讲清）

一个 Figure（40~80 零件）= 300~1500 行 build.mjs + 3~6 轮截图返工；Hero（80~150 零件）2~4 小时；Epic 6 小时+（官方明说别擅自开始）。**先做最小 Figure 验证手感，再上工作坊级。**
