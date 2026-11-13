---
name: corporate-vpn-git-recovery
description: "Use when 飞连/CorpLink 挡住 git push、GitHub 超时。"
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [git, github, vpn, corplink, 飞连, network, macos]
    related_skills: [github-repo-management, macos-computer-use]
---

# 企业 VPN 恢复 GitHub/git 访问（飞连本机）

打开 VPN → 确认连通 → **补齐上次没推上去的 commit** → 用远端 API 证明真上去了。

触发场景一句话：`git push` 卡 443 超时、`ssh -T git@github.com` 认证不过、gh 命令超时，用户说"把飞连点开应该就能登录/推 GitHub 了"。

## When to Use

任一命中就用本 skill：

- `git push` / `git clone` / `git ls-remote` 卡 443 超时，或 `ssh -T git@github.com` 认证不过；`gh` 命令长时间无响应。
- 用户说"把飞连点开""开 VPN 应该就能登录/推 GitHub 了""飞连开了没"。
- 上次会话留了"GitHub 推不上去，commit 只在本地"的尾巴，现在网络恢复了要收尾。
- 本地 `git rev-list --count origin/main..HEAD` > 0（有欠推 commit），需要确认远端兜底。

不适用：token 过期/权限不足（先 `gh auth login`）、仓库冲突或 detached HEAD（先修 git 状态）。


核心原则：**用户让你"开飞连"时，真正要交付的是"推送补完了"，不是"App 打开了"。**

## 0. 先看欠了多少

操作前先量化缺口，它决定收尾动作：

```bash
cd "<repo>" && git status --short | head; \
git rev-list --count origin/main..HEAD;        # 本地领先远端几个 commit
git log --oneline -4 | cat
```

working tree 干净 + 领先 N>0 = 只差网络和一次 push。

## 1. 启动飞连 = CorpLink

| 项 | 值 |
|---|---|
| 名称映射 | 飞连 = **CorpLink** |
| 路径 | `/Applications/CorpLink.app` |
| bundle id | `com.volcengine.corplink` |
| 形态 | Electron，**常驻菜单栏，正常状态没有窗口** |

```bash
open -a /Applications/CorpLink.app && sleep 4 && pgrep -lf CorpLink | head -3
```

**不要**接着去 `computer_use capture(app='CorpLink')` 找窗口，那是白跑：菜单栏态返回 `0x0 / no on-screen window matched`，`list_windows` 里也没有它。也别用 `osascript ... activate`（AppleEvent 超时 -1712）。

唯一要碰 UI 的情况：`setupInfo.show_mobile_authorization_login=true`（首次/掉登录）时它会**弹二维码窗口**，这时才截图 —— 扫码必须由用户做。

## 2. 探连通性（最便宜的先跑）

```bash
curl -sS -m 8 -o /dev/null -w "api.github:%{http_code}\n" https://api.github.com
gh auth status 2>&1 | head -6          # 顺便确认 token 没过期
git ls-remote https://github.com/<owner>/<repo> HEAD | head -2
```

任一正常 = 不用管 VPN 界面，直接进第 3 步。

## 3. 补推 + 验证（两步都不能省）

```bash
cd "<repo>" && GIT_TERMINAL_PROMPT=0 git push origin HEAD:main 2>&1 | tail -6
git rev-list --count origin/main..HEAD          # 必须变成 0
git log --oneline -1 origin/main | cat          # 远端 ref 指向新 commit
gh api repos/<owner>/<repo>/commits/main --jq '.sha[0:7] + " | " + .commit.message'
gh api repos/<owner>/<repo> --jq '.pushed_at'
```

一键版：`scripts/retry-push-verify.sh "<repo-dir>" <owner>/<repo> [branch]`

**push 输出说成功不算证据**：必须三样齐 —— (a) 本地 ahead=0、(b) `origin/main` 指向新 SHA、(c) 远端 API 返回同一 SHA。齐了才能说"推上去了"。

## 4. 回给用户什么

结果表 + 链接，别讲排障过程（用户只要结论）：

- 飞连进程已起 / 三项探测结果
- `bce5d76..fb42f8d  HEAD -> main` 这种 push 摘要
- 本地领先 `2 → 0`
- 仓库链接 + commit 链接

## Pitfalls

- **本机没有 `timeout` 命令**（未装 coreutils）：`timeout 90 git push` 会报 `timeout: command not found`，而整条管道 `exit=0` 会骗你以为跑过了。要限时靠 `git config http.lowSpeedLimit/lowSpeedTime` 或 terminal 工具自身 timeout。
- **别用 CorpLink config.json 的 `vpn_status` 判断连接**：`~/Library/Application Support/CorpLink/config.json` 的 `setupInfo.vpn_status` 是启动时快照（曾在已连通时仍为 0）。以第 2 步实测为准。
- **网页能开 ≠ git 能推**：443 长连接超时对 push 和浏览器影响不同，一定测具体操作（`git ls-remote`/push），别用"curl github.com 200"就断言恢复。
- **别急着换协议**：HTTPS 失败后不要立刻改走 SSH 重试（SSH 认证那条同样死，白耗几分钟）。先开 VPN，再按 HTTPS 试。
- **本地 commit 不会自己上去**：网络恢复后要显式补推，并把"欠了几个 commit"一起报给用户（他关心远端有没有兜底）。
- 不要因为 `git status` 曾报错就断定仓库坏了；先看 ahead 数。

## 验证脚本

`scripts/retry-push-verify.sh` — 传 repo 路径，依次输出 ahead 数 → 连通探测 → push → 复核远端 SHA，任一步失败非 0 退出。
