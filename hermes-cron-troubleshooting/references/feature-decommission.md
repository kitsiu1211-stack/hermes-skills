# 功能下线实例：会中雷达（2026-10-26）

一次完整的「用户说关掉」操作记录，配合 SKILL.md 的「反向操作：用户说『关掉它』」一节使用。

## 触发原话

> 关于会议中的雷达，我觉得关闭掉吧，帮助不是很大，而且噪音很大

关键信号是**效用否定**（帮助不大）+ **成本抱怨**（噪音大）。这是价值判断，不是缺陷报告。当时的正确动作是直接下线，而不是问「要不要把阈值调高」。

## 改了什么

文件 `~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh`。

```diff
 # ---- 会议雷达（主动预警）2026-10-14 --------------------------------------
 # 零token规则 + 小模型增量扫描；发现冲突/异常/需求/我方失手 → 立即私聊推给用户。
-# RADAR_ENABLE=0 关闭；RADAR_CHAT 指定接收私聊；RADAR_LLM_EVERY=0 关闭模型层。
-if [ "${RADAR_ENABLE:-1}" != "0" ] && [ -f "$HOME/.../meeting_radar.py" ]; then
+# ⚠️ 2026-10-26 起默认关闭（用户反馈噪音大、帮助有限）。需要时显式 RADAR_ENABLE=1 手动开。
+# RADAR_ENABLE=1 开启；RADAR_CHAT 指定接收私聊；RADAR_LLM_EVERY=0 关闭模型层。
+if [ "${RADAR_ENABLE:-0}" = "1" ] && [ -f "$HOME/.../meeting_radar.py" ]; then
```

要点：**默认值反转，代码块保留**。`meeting_radar.py` 原文件一行没动，opt-in 路径完整。

同步改了 skill 文档 `feishu-meeting-listen/SKILL.md`，在原「会议雷达」小节标题上加「· 2026-10-26 默认关闭」，正文加一段引用块写清用户原话 + 「用户没有重新要求别自作主张开」，并把「默认随旁听自动启动」改为「启动方式（已改为手动）」。

## 验收命令

```bash
bash -n ~/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh && echo "syntax OK"
ps aux | grep -E "meeting_radar|poll.sh" | grep -v grep        # 应为空
```

本次两项都通过（无正在跑的实例，所以不需要 kill/冷启）。

cron 侧用 `cronjob action='list'` 逐个看了 10 个 job，确认没有任何一个会拉起 radar。

## 会议流水线的组件表（下线时最容易误伤的地方）

只听名字会以为关掉雷达 = 整条会议链路停摆。实际是四个独立件：

| 组件 | 入口 | 职责 | 2026-10-26 处置 |
|---|---|---|---|
| 字幕采集 | `scripts/poll.sh` | 拉 `vc +meeting-events`，写 `<mid>.jsonl` | **保留** |
| 会中主动预警 | `scripts/meeting_radar.py`（由 poll.sh 拉起） | L1 规则 + L2 模型层，异常私聊推 Home | **关闭**（`RADAR_ENABLE` 默认 0） |
| 会后纪要 | cron「会议收尾哨兵」`scripts/meeting_finisher.py` | 监控 `PENDING <mid>`，会议结束自动出纪要卡片 | **保留** |
| bot 入会 | `lark-cli vc +meeting-join --as bot` | 进会议 | **保留** |

交付话术里把这四行说清楚，用户才不会担心「关了雷达纪要也没了」。

## 遗留物

radar 的历史日志 `~/meeting_logs/*.radar.log` 合计 28K，未清理。下线功能时顺手报一下这类残留的体积，让用户决定要不要清 —— 但不要未经确认就删日志。
