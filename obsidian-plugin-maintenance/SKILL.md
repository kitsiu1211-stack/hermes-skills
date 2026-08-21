---
name: obsidian-plugin-maintenance
description: Use when an Obsidian plugin won't load or needs updating.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
---

# Obsidian 插件维护与排障

诊断和修复 Obsidian 社区插件加载失败、命令搜不到、版本过旧；手动更新插件；理解 macOS 自动更新机制。

## When to Use

- Obsidian 社区插件的命令在 Cmd+P 命令面板里搜不到（「未找到命令」）
- 插件的视图 / ribbon 图标打不开、不出现
- 插件版本过旧需要手动更新
- Obsidian 提示有新版本但一直没生效，怀疑插件因此卡住
- 多个 Obsidian 库之间插件状态不一致

## 核心诊断结论（最重要的一条）

**命令面板（Cmd+P）搜不到插件的命令 = 插件没有加载**，即使磁盘上所有文件都正确。

Obsidian 插件在 `onload()` 里、读完设置之后才注册命令（`addCommand`），所以只要加载失败，命令就不会出现。这是判断「插件没加载」最可靠的信号。

命令名是本地化的：中文界面下 `Open Galaxy View` 会显示为「打开星系视图」。搜英文搜不到属正常；但**中英文都搜不到，就一定是插件没加载**，别在语言上纠结。

## 诊断清单（按顺序查）

1. `.obsidian/plugins/<id>/` 下四件套齐全：`main.js` `manifest.json` `styles.css` `data.json`
2. `.obsidian/community-plugins.json` 里包含该插件 id（= 已启用）
3. `manifest.json` 的 `version` 是否为最新（对比 GitHub，见「手动更新」）
4. `data.json` 是否合法 JSON：`python3 -c "import json;json.load(open('data.json'))"`
5. 观察 `~/Library/Application Support/obsidian/obsidian.log`（**时间戳是 UTC**，中国时区减 8 小时）

## macOS 自动更新机制（关键坑）

- 自动更新把新版 `obsidian-<版本>.asar` 下载到 `~/Library/Application Support/obsidian/`，**下次启动才加载**它。
- 因此 `defaults read /Applications/Obsidian.app/Contents/Info.plist CFBundleShortVersionString` 仍然显示**旧版本号**——这不能证明没更新。看 log 里 `Loaded updated app package .../obsidian-<版本>.asar` + `App is up to date` 才是准的。
- log 里出现 `An update is already downloaded` = 下载了新版本但**一直没重启生效**，这种状态下插件可能卡住不加载。彻底重启即可。

## 修复步骤

1. **彻底退出**（不是点红叉关窗口——macOS 关窗口应用仍常驻后台，Cmd+Q 才是真退出）：
   `osascript -e 'tell application "Obsidian" to quit'`
2. **重新打开**：`open -a Obsidian`（会自动加载已下载的新版本）
3. 若仍不行 → 更新插件本身（见下）。

## 手动更新社区插件（保留用户配置）

1. 反查插件 repo：
   `curl -s https://raw.githubusercontent.com/obsidianmd/obsidian-releases/master/community-plugins.json` → 找 `id`/`repo`
2. 查最新版本 + 下载地址：
   `curl -s https://api.github.com/repos/<owner>/<repo>/releases/latest` → `tag_name` + `assets[].browser_download_url`
3. 下载 `main.js` `manifest.json` `styles.css` 三个文件（用 `curl -sL`）
4. 备份旧的，替换 `.obsidian/plugins/<id>/` 下同名文件
5. **保留 `data.json` 不动**——那是用户的配置/节点位置缓存，插件升级不覆盖它
6. 再次彻底重启 Obsidian

## 验证插件是否加载的旁证

- `workspace.json` 里出现该插件的 view type（如 `"type": "galaxy-view"`）→ 说明以前加载成功过、开过它的视图。
- `workspace.json` 的 `left-ribbon.hiddenItems` 里出现 `"<plugin-id>:<命令名>": false` → 说明它的 ribbon 图标曾经注册过（false = 图标可见）。
- 这两个痕迹能区分「从来没加载过」和「以前能加载、现在加载失败」，后者几乎都是版本/更新/重启问题。

## 多库注意

本机可能有多个 Obsidian 库（如 `Obsidian Vault` 主库 + `My Great Vault` 云端镜像），各自有独立的 `.obsidian/` 配置。插件升级要**每个库都替换**。若日常 `rsync` 同步是 `--exclude='.obsidian'` 的，插件文件/设置不会自动同步过去，必须手动分别处理。

## 全局 vault 注册表

`~/Library/Application Support/obsidian/obsidian.json` 的 `vaults` dict 列出所有库路径与 `open` 状态，用于确认本机有几个库、哪些在开。Obsidian 日志同目录 `obsidian.log`。
