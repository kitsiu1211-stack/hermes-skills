# 妙搭 HTML 发布全流程

## 场景
用户需要创建一个纯静态 HTML 页面，发布为公开可访问的 URL，挂到飞书个性签名等位置。

## 完整流程

### 0. 前置：授权 apps 域

```bash
lark-cli auth login --domain apps --no-wait --json
```

拿到 `device_code` 和 `verification_url` 后，生成二维码展示给用户。用户确认后：

```bash
lark-cli auth login --device-code "<code>"
```

### 1. 创建应用

```bash
lark-cli apps +create \
  --name "应用名" \
  --app-type html \
  --description "描述" \
  --as user
```

返回 `app_id`（`app_` 开头），记住它。

### 2. 构建 HTML

写一个独立的 `index.html`（CSS/JS 内联，无外部依赖）。放到一个目录如 `/tmp/myapp/`。

### 3. 发布

**必须 cd 到目标目录的父目录，使用相对路径**：

```bash
cd /tmp && lark-cli apps +html-publish --app-id <app_id> --path ./myapp --as user
```

❌ 错误：`--path /tmp/myapp`（绝对路径报错 `unsafe --path: --file must be a relative path`）

✅ 正确：先 `cd /tmp`，再 `--path ./myapp`

发布成功返回 `data.url`。

### 4. 设为公开

发布后默认仅创建者可见，需要放开：

```bash
lark-cli apps +access-scope-set --app-id <app_id> --scope public --require-login=false --as user
```

❌ 错误写法：`--require-login false`（空格分隔报错 `positional arguments are not supported`）

✅ 正确写法：`--require-login=false`（等号连接）

### 5. 更新

修改 HTML 后重复步骤 3（不需要重新创建应用或重新设置公开范围，scope 设置会保留）。

## 关键参数速查

| 命令 | 关键 flag | 注意 |
|------|----------|------|
| `+create` | `--app-type html`, `--name` | HTML 类型不需要 `--app-type full_stack` |
| `+html-publish` | `--path ./相对路径` | 必须 cd 到父目录后用相对路径 |
| `+access-scope-set` | `--scope public`, `--require-login=false` | 等号连接，不能空格 |

## 开发态 vs 发布态链接

- **开发态**：`https://miaoda.feishu.cn/app/{app_id}` — 编辑管理入口
- **发布态**：`+html-publish` 返回的 `data.url` — 实际分享给用户的链接

## 设计质量要求（公开展示页）

当页面面向公众（挂飞书签名、GitHub README 等），需满足以下质量标准：

### 视觉方向
- **优先加载 `design-taste-frontend` skill**（从 `gvnnya/taste-skill` GitHub 安装），它提供 Brief Inference → Dial Setting（VARIANCE/MOTION/DENSITY）→ 分场景的排版/色彩/动效规则
- 搭配 `popular-web-designs` skill 选用 Apple / Linear / Stripe 等成熟设计系统的具体 token
- 避免 AI 设计 slop：AI 紫蓝渐变、居中 Hero（VARIANCE≥7 时）、玻璃态滥用、三等分卡片、彩虹色
- 运行 `claude-design` 的 Slop Diagnostic（10 项自查），0 分才发布
- **图标用 Lucide SVG**（`lucide.dev`），禁止 emoji。CDN：`<script src=\"https://unpkg.com/lucide@latest\"></script>`，`<svg data-lucide=\"icon-name\"></svg>` + `lucide.createIcons()`

### 内容质量
- **每个 item 必须配真实使用示例**（对话形式），不能只有描述文字
- 示例格式：用户消息 + Agent 回复的对话气泡，让读者能「感受到」用法
- 描述文字去 AI 味：不要「赋能」「助力」「高效」「智能」等套话

### 交互细节
- 展开/折叠面板用**独立 toggle**（点 A 开 A，点 B 不影响 A），不要用手风琴（自动关其他）
- 引导式操作流程放在页面顶部，用动画箭头连接各步骤
- 复制按钮的 Toast 文案用通用词「Agent」而非「Hermes Agent」
- 右下角加反馈悬浮窗：引导式快捷选项 + 自由输入；按钮有脉冲动画吸引注意

### 移动端
- 响应式适配，手机端卡片单列、流程竖排
- 代码块在窄屏允许换行

### 常见设计踩坑（本 session 纠正）

1. **目录/导航不可见**：不要用 nav 栏里的 12px 小字做分类目录。用 Hero 下方的 **sticky pill bar**（胶囊按钮），每项含图标 + 名称 + 数量，当前项高亮为 Apple Blue 实心。
2. **Skill 名只用英文代码**：用户看不懂 `ljg-rank`。改为 **中文主名 + 小字代码名**（如「骨架分析 `ljg-rank`」），4 字以内，一眼知道干什么。
3. **手风琴变独立 toggle**：示例面板不要点 A 关 B，各自独立展开/收起。
4. **Toast 文案去品牌名**：写「Agent」不写「Hermes Agent」，别人不一定用 Hermes。
5. **反馈窗引导**：右下角悬浮按钮 + 脉冲动画 + 快捷引导选项（「我想定制」「示例不清楚」「还想要 XXX」）+ 自由输入。
6. **用 skill 设计，不要自己编**：taste skill 有 VARIANCE 级别决定 Hero 是否居中 — VARIANCE ≥5 时 Hero 应用分屏/非对称布局，不是默认居中。
7. **反馈入口不要暗色小圆点**：右下角悬浮按钮用品牌主色（Apple Blue）实心圆 + 发光脉冲光环 + 轻柔上下浮动动画 + 3 秒后右侧滑出「有建议？」文字标签（带三角箭头指向按钮）。三个层次同时作用：颜色吸引、动画抓住、文字引导。不用暗色圆点——太容易忽略。
