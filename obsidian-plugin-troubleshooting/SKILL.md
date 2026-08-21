---
name: obsidian-plugin-troubleshooting
description: Use when an Obsidian plugin won't load or needs updating.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [obsidian, plugins, troubleshooting, macos]
    related_skills: [obsidian]
---

# Obsidian 插件 / 应用排障

先分清一件事：**插件文件在磁盘上 ≠ 插件真的加载了**。大多数"插件装好了却用不了"的问题，卡在"加载"这一步，不在配置。

## When to Use

- 命令面板搜不到某插件命令（返回"未找到命令"）
- 左侧边栏看不到插件的 ribbon 图标
- 插件视图打不开（比如"星空视图"不显示）
- 插件在本地仓正常、另一个仓不正常
- 提示有新版本但一直没生效

## 诊断顺序（按序走）

1. **看插件是否启用**：读 `<vault>/.obsidian/community-plugins.json`，确认插件 id 在数组里。
2. **看插件以前是否加载过**：用 `search_files` 搜 `<vault>/.obsidian/workspace.json`，`left-ribbon.hiddenItems` 里若有 `"<插件id>:<命令名>"` 条目，说明以前加载过——那就是"当前这次没加载"，不是"从没装过"。
3. **看版本兼容性**：读 `<vault>/.obsidian/plugins/<id>/manifest.json` 的 `version` 和 `minAppVersion`。插件版本过旧、与当前 Obsidian 不兼容，是「命令搜不到」的高频根因 → 更新插件。
4. **看更新是否卡住**：读 `~/Library/Application Support/obsidian/obsidian.log`，找 `An update is already downloaded` 或 `Loaded updated app package`。

## 关键文件位置（macOS）

```
<vault>/.obsidian/community-plugins.json           # 已启用插件 id 数组
<vault>/.obsidian/workspace.json                   # ribbon 配置 + 已打开的视图
<vault>/.obsidian/plugins/<id>/manifest.json       # 插件版本 + minAppVersion
<vault>/.obsidian/plugins/<id>/data.json           # 插件设置（与代码文件分离）
<vault>/.obsidian/plugins/<id>/main.js             # onload 里看命令注册顺序
~/Library/Application Support/obsidian/obsidian.json   # vault 列表 + open 状态
~/Library/Application Support/obsidian/obsidian.log    # 版本/更新状态
```

## 代码层：为什么"命令搜不到"

压缩后的 `main.js`，命令注册一般在 onload 的最后：

```js
onload(){this.settings=X(await this.loadData()), ... , this.addCommand({id:"open",name:...})}
```

`addCommand` 排在 `loadData()` + 设置校验之后，所以 data.json 读坏会连带命令全不注册。但大多数插件的校验是"带默认值的安全归一化"，合法 JSON 不会抛——所以命令搜不到更可能是**版本不兼容**或**没彻底重启**，不是 data.json 坏了。验证 data.json 是否合法：`python3 -c "import json; json.load(open('.../data.json'))"`。

## 两个高频坑

### 1. macOS「关窗口 ≠ 退出应用」

点红叉只是关窗口，app 还在后台跑。更新/重启插件必须彻底退出再开：

```bash
osascript -e 'tell application "Obsidian" to quit'
sleep 3
open -a Obsidian
```

判断是否真重启：`obsidian.log` 有没有新的 `Loaded ... app package` 行。

### 2. `defaults read` 读版本会骗人

Obsidian 的 macOS 自动更新是把新 `.asar` 下载到 `~/Library/Application Support/obsidian/`，下次启动加载它；`/Applications/Obsidian.app/.../Info.plist` 的 `CFBundleShortVersionString` 仍显示旧版本。**以 `obsidian.log` 里 `Loaded updated app package obsidian-X.Y.Z.asar` 为准**。注意 log 时间戳是 UTC（比北京时间晚 8 小时）。

## 更新一个社区插件（从 GitHub release）

1. `https://api.github.com/repos/<owner>/<repo>/releases/latest` 拿 tag 和 assets 下载地址。
2. 下载 assets（通常 `main.js` / `manifest.json` / `styles.css`）到 /tmp。
3. 校验下载的 `manifest.json` 版本号对。
4. 备份旧代码文件到 `backup-<旧版本>/`。
5. 复制新代码文件进 `<vault>/.obsidian/plugins/<id>/`，**保留 `data.json` 不动**（那是用户配置）。
6. 彻底重启 Obsidian（见上）。
7. 多仓时每个 vault 都要更新。

## 验证

- 重启后让用户看：ribbon 图标是否出现、命令面板能不能搜到插件命令。
- 别用 `defaults read` 验证版本，看 `obsidian.log`。

## 本用户特有

见 `references/galaxy-view.md`（双库 + Galaxy View 星空插件细节）。
