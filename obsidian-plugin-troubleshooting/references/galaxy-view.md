# Galaxy View 星空插件（本用户特有）

张鑫杰的双库 Obsidian 里装的星空关系图谱插件。2026-08-15 排查过一次，记录现状。

## 基本事实

- 插件 id：`galaxy-view`，作者 Rick，repo `longwind1984/galaxy-view`
- 插件的作用：3D 电影感图谱（"fly through your notes like NASA Eyes"）
- 已从 0.5.0 升级到 0.6.1（0.5.0 与新版 Obsidian 不兼容导致加载失败，命令搜不到）

## 星空样式配置

在 `<vault>/.obsidian/plugins/galaxy-view/data.json` 里：

- `colorTheme: "aurora"`（极光配色，本地仓的"炫酷星空"样式）
- `activePreset: "spiral"`（螺旋预设）
- 云端仓原本是 `hubble` + `galaxy`（哈勃橙），已改成和本地一致

## 关键坑：「星空视图」是独立视图，不是原生「关系图谱」

- Obsidian 自带的「关系图谱」（Graph View）永远是朴素灰球，跟 Galaxy View 无关。
- 星空视图靠两个入口打开：
  - 左侧边栏**最底部**的 orbit 轨道图标
  - 命令面板：中文 UI 输「打开星系视图」/「星系」，英文 UI 输 `Open Galaxy View`
- 命令名会随界面语言自动翻译（插件 `language: "auto"` 跟随 Obsidian UI 语言）。中文界面搜英文名搜不到，反之亦然。

## 双库同步

- 主库 `~/Documents/Obsidian Vault` + 云端镜像 `~/Documents/My Great Vault`
- 插件更新、配置改动，两个仓都要做；改完 `rsync -a`（排除 `.git` `.obsidian`）同步笔记
- `.obsidian` 是故意排除在 rsync 外的（避免两仓设置打架），所以插件/配置改动**不会**自动同步，要手动两边改
