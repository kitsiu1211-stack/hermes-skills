---
name: feishu-agent-media-handoff
description: 飞书群聊 Bot 间媒体/文件交接与权限墙救援（仅收@/230027）。当委派任务含图、Bot 收不到、需转媒体时使用。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [feishu, agent-collab, media, lark-cli]
    related_skills: [feishu-group-chat, agent-group-collab, lark-im, github-repo-management]
---

# 飞书群聊 Bot 间媒体/文件交接

## When to Use

- 委派给群 Bot（Kimi Code 等）的任务含图片/文件
- Bot 回复「收不到图片/文件」「没权限」或报 230027
- 需要把群里的图片/文件转给另一个 Bot
- 从群消息下载媒体资源（图片/文件/音视频）

## 核心问题：Bot 权限不对称

群 Bot 的典型配置是**事件订阅仅接收 @ 消息**（未 @ 的图片消息不进它的事件流）+ **无拉群消息列表权限**（`im:message:readonly` 未开通，API 报 230027）。这两条组合是死局：它既等不到图，也查不到图——它自己无法解决。

Hub 主 Agent（浪子/Hermes）权限更宽：能读群消息（`--as bot` 即可）、能下载媒体、能访问云盘/GitHub/本地文件。**所以卡点应该由 Hub 解决，不要把问题丢回给用户重发。**

## 救援阶梯（按优先级）

### 1. 本地文件优先（零 API 调用）

用户常说「我本地有个文件夹」——先搜本地常见目录：`~/Desktop/`、`~/Desktop/分享/`、`~/Downloads/`。

2026-08-18 实测：用户说图片在本地「分享」文件夹，群里 00:05 发的 3 张图原图就在 `~/Desktop/分享/`，直接取用，完全不用碰 API。

### 2. 从群消息下载（无本地源时）

```bash
# 方式 A：列消息时直接下载（image/file 自动落盘到 ./lark-im-resources/）
lark-cli im +chat-messages-list --chat-id <oc_xxx> --as bot \
  --start "2026-08-18 00:00:00" --end "2026-08-18 00:10:00" \
  --order desc --download-resources

# 方式 B：已知 message_id 单条下载
lark-cli im +messages-resources-download --message-id <om_xxx>
```

注意：图片消息的 `content` 是 `{"image_key":"img_v3_xxx"}`，用 `--download-resources` 会自动下载成文件。

### 3. 代转给目标 Bot（保持分工）

目标 Bot 只收 @ 消息 → 重发时必须带 @。**纯 image 消息无法携带 @**，必须图片+说明文字组合：

- `--markdown` 转 post：`lark-cli im +messages-send --chat-id <oc> --as bot --markdown $'![alt](img_v3_xxx)\n<at user_id="ou_xxx">Bot名</at> 图1 说明'`（markdown 的 @ 内联标签可用）
- 或 `--msg-type post --content` 手写 post JSON（`at` 元素节点 + `img` 元素 + text）

### 4. Hub 直接接管（最快闭环）

权限墙任务直接自己做：本地取图/群下载 → 压缩 → 改文件 → push → 验证 → 群里 @ 对方「这项不用再处理了」。用户偏好如此（说一遍就够、自主排查不反问）。

#### 委派 bot 失联时的接管阶梯（2026-08-18 实测）

1. **先 @nudge 一次**，等 ~2 分钟。它可能只是 webhook 卡，nudge 后常见「↪ Redirected current run」确认它还活着。
2. **识别它的状态消息**：bot 的「⏳ Working — N min — iteration N/60」状态消息在 `chat-messages-list` 里 sender 名常显示为本群 bot 名（不可靠），**按内容模式识别**，别按 sender 名过滤。
3. **判定死亡**：nudge 后 10+ 分钟仍无新状态、无 push → 终端关机/额度耗尽。此时不要反复重发任务：用户已授权过「直接上 GitHub 修改」时（2026-08-18 两次失联均为预授权路径），从发任务起 ~8 分钟仍无 Working 状态即可直接接管、不必再问；未授权过则先跟用户确认。
4. **接管完成后 @bot 停手**：「任务已完成，不用再继续」——避免它复活后按旧任务白耗额度重跑。
5. **双 Agent 共推同一仓库**：Kimi Code push 后本地 `git pull` 会报 `divergent branches`。本地改动已全部 push 时安全处理：`git fetch origin main && git reset --hard origin/main`，再基于最新远端改。
6. **委派文案/设计改动给远程 Agent 时给终稿**：文案直接写进任务书并注明「直接用，别改」——远程 agent 自己发挥容易把 AI 味写回来（冒号/破折号/「沉淀赋能闭环」等黑话）。验收用 grep 清单：关键词残留=0（如 `grep -c "沉淀\|赋能" index.html`）、新元素存在（`grep -n "关键段"`）、结构顺序正确。

## 发送前压缩（原图常 1-2MB+）

macOS 原生 sips，2MB → ~200KB，网页加载友好：

```bash
sips -s format jpeg -s formatOptions 82 -Z 1200 "原图.jpg" --out compressed.jpg
```

## 陷阱

| 问题 | 原因 | 解决 |
|------|------|------|
| Bot 说收不到图片 | 事件订阅仅接收 @ 消息，未 @ 的媒体不进事件流 | 重发必须带 @，或 Hub 代转/接管 |
| API 报 230027 | Bot 无 `im:message:readonly`（拉消息列表权限） | 这是 Bot 配置死结，别指望它自己解决；Hub 用 `--as bot` 拉 |
| 图片消息没有 @ | image 类型消息无法携带 at 标签 | 用 post 消息（img 元素 + at 元素 + text）组合发 |
| 不要要求用户重发 | 用户说过一遍就够，重发=重复劳动 | 先查本地原图 → 群下载 → 接管 |
| push 后线上 404 | GitHub Pages 构建中（1-3 分钟） | raw.githubusercontent 200 即已上传；轮询 `gh api repos/O/R/pages --jq '.status'` 到 built 再验收，别误报失败 |
| grep 到电话/邮箱变星号（如 `tel:+861\*\*\*\*6353`） | 工具输出层 PII 脱敏，**文件实际是对的** | 用模式匹配验证真身，别信显示：`grep -c 'tel:+86136' file`（=1 即真实号码存在）或 `grep -c 'tel:+861\\*\\*\\*\\*'`（=0 即无字面星号） |

## 相关

- `agent-group-collab` / `feishu-group-chat`（用户自有）：群 Bot 目录、@mention 教学、心跳轮询——媒体交接是它们的补充模块
- `github-repo-management`（bundled）：Pages 部署验证
