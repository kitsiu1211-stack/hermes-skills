# 前端幻灯片设计风格

来自 Zara 的「如何打造 AI-native 组织」页面 (`app_17a8fkz1crs`)，用于后续演示页参考。

## 设计令牌

| 变量 | 值 | 用途 |
|------|-----|------|
| --paper | #F2EEDF | 背景/画布 |
| --ink | #2A241B | 主文字色 |
| --ink-soft | #5C5345 | 次要文字 |
| --pink | #E1A4C2 | 装饰/卡片底色 |
| --lemon | #D6DD63 | 装饰/卡片底色 |
| --blush | #E8C9B6 | 装饰/卡片底色 |
| --sage | #B7C7A8 | 装饰/卡片底色 |
| --lilac | #C9BEDC | 装饰/卡片底色 |
| --card | rgba(255,255,255,0.55) | 卡片底色 |
| --rule | rgba(42,36,27,0.12) | 分隔线 |

## 字体

- 英文/数字: **Albert Sans** (Google Fonts, 400-700)
- 中文: **Noto Serif SC** (思源宋体, 400-700)

## 布局

- 固定舞台: 1920×1080 (16:9)
- 卡片式布局，16px 圆角
- 柔和分隔线 (<1px, 低透明度)
- Hero 区域用模糊圆点装饰

## 应用

已用于 AI Atlas v6 (`/tmp/ai-atlas-v6.html`)。配合 baoyu-design skill (`~/.hermes/skills/baoyu-design/`) 使用。
