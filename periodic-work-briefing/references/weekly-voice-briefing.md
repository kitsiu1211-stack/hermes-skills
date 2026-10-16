# 语音汇报会 · 运行手册（2026-10-13 建立，试跑版 v1）

目标：每周或按需，Bot 入会 → 用豆包语音把工作汇报念给用户 → 用户追问，实时问答。
形态为**轻量版**：用户拉会 + 说一句触发，其余全自动（全自动版 = cron 自动建会 + 主动播报，跑顺 2~3 次后再上）。

## 会前 3 条硬前提（缺一条就降级）

1. **会议 owner 勾选「允许智能体加入会议」**——每次新建会议都要勾，不是一次设置永久生效
2. **会议用「袁鑫杰的视频会议」模板创建**——ByteView 音频流只有这类模板稳定有；其他模板可能 Bot 入会成功但完全没声音
3. **戴耳机**——外放回声会触发豆包打断（barge-in 默认开）

## 触发方式（用户只需做一件事）

在聊天里发一句「**开周报会**」（可附 9 位会议号）。

## Agent 执行清单

```bash
# 1) 收素材（零 token，纯确定性；必须用 venv python）
/Users/bytedance/.hermes/hermes-agent/venv/bin/python \
    ~/.hermes/scripts/weekly_brief_build.py --days 7 --out /tmp/brief_week.md

# 2) 读素材包 → 写播报稿（3~5 分钟口语稿，不要直接念卡片排版）→ /tmp/weekly_report.txt
#    写完默认直接念，除非用户要先看

# 3) 备份配置 + 把播报稿设为开场（唯一需要改配置的一步）
cd ~/Documents/Codex_Project/feishu-voice-agent-starter
cp config.yaml config.yaml.bak-weekly
# 把 opening_line: "" 改成 opening_line: "<播报稿全文或首段>"

# 4) Bot 入会
lark-cli vc +meeting-join --meeting-number <9位会议号> --as bot

# 5) 等 3 秒（时序竞争会让 ByteView 无声），再起语音管线
sleep 3
python3.11 main.py --config config.yaml --meeting-no <9位会议号> --keep-in-meeting --poll-events

# 6) 会后立刻恢复静音铁律 + 离会
cp config.yaml.bak-weekly config.yaml
lark-cli vc +meeting-leave --as bot --meeting-id <长 meeting_id>
```

**静音门控的唯一例外**：默认 `mute_by_default: true` + wake word（「浪子」）+ 90 秒窗口 = 全程闭嘴、被点名才答。汇报会时临时用 `opening_line` 念播报稿——**这是唯一允许主动开麦的场景，必须由用户显式触发，用完立刻恢复**。绝不自作主张改配置去开麦。

## 分工

| 时段 | 谁 | 做什么 |
|---|---|---|
| 前 3~5 分钟（播报） | Agent | 念播报稿：上周做了什么 / 待办进展 / 卡点 / 需要用户决策的事 |
| 之后（问答） | 双方 | 用户随时打断追问；没人喊 wake word 时 Agent 继续静默 |

播报稿写法：先说结论和「需要你决策的事」，再讲进展；口语化、不念术语、不超过 5 分钟。

## 降级路径（音频不通时）

启动后 5 秒内日志没有 `[bv] raw msg` = 该会议没有 ByteView 音频流 → 立刻 kill 语音管线，改走
**字幕旁听 + 聊天框文字**（用户在会里打字问，Agent 在聊天框回）。

## 已知限制（豆包侧，非我方 bug）

- 只会说普通话
- 看不到会中聊天文本（端到端模型无聊天感知）
- 首句延迟 2~3 秒（`end_smooth_window_ms=500` 已优化过）

## 素材包实测（2026-10-07 ~ 10-13）

11 场会议 / 4518 句字幕 / 10 个工作会话 / 9 项跟进日程，11 场会议里 7 场标题由日历自动补齐
（未补齐的都是几分钟的临时呼叫，无日历日程）。

## 待验证 / 下一步

- [ ] 试跑确认：① 能听到播报 ② 能实时追问 ③ 静默门控在没人喊时确实闭嘴
- [ ] 跑顺后再考虑全自动（cron 自动建会 + Bot 自动入会 + 主动播报）
- [ ] 会议妙记录存到 Obsidian，形成可回查的汇报档案

## 相关

- 采集脚本：`/Users/bytedance/.hermes/scripts/weekly_brief_build.py`
- 原运行手册（同内容副本）：`/Users/bytedance/.hermes/scripts/weekly_voice_runbook.md`
- 语音管线项目：`~/Documents/Codex_Project/feishu-voice-agent-starter`（`main.py --check` 可验证凭据是否就绪）
- 会议旁听与 Bot 入会细节：`feishu-meeting-listen` skill（用户自有，如需补充请让用户 `hermes curator adopt feishu-meeting-listen`）
