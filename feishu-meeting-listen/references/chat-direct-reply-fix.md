# 会中弹幕自动回复 — 架构（2026-07-27 最终版）

## 当前方案（v3 — 直接调 DeepSeek API）

Chat watcher 检测到"浪子" → 直接调 DeepSeek API（`_call_hermes_api()`）→ `lark.meeting_message_send()` 发回会议。

**不走 inbox，不走 HTTP server，不依赖 Hermes DM session。**

```python
# main.py poll_meeting_chat() 核心逻辑
if "浪子" in content:
    reply = await _call_hermes_api(content, sender)
    if reply:
        lark.meeting_message_send(meeting_id, reply)
```

`_call_hermes_api()` 在 main.py L247-278 实现，用 httpx 调 `https://api.deepseek.com/v1/chat/completions`，model=deepseek-chat，max_tokens=200。

## 启动命令

```bash
cd ~/Documents/Codex_Project/feishu-voice-agent-starter
DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY ~/.hermes/.env | cut -d= -f2) \
python3.11 main.py --config config.yaml --meeting-no <9位号> --keep-in-meeting --poll-events
```

## 已废除方案（不应再用）

- ❌ inbox + HTTP server (localhost:19876) — Hermes DM session 无法消费 inbox 文件，导致无人回复
- ❌ 临时 bash poll inbox 脚本 — 脆弱，硬编码回复模板
- ❌ 硬编码 "收到 ✅ 私聊 @浪子" — 给每条消息回同样内容，用户反馈「怎么只会回复一个信息」

## 踩坑记录

- `lark-cli vc +meeting-message-send` flag 是 `--text`，不是 `--content`
- chat poll 间隔 10s（防限流 99991400）
- 10s cooldown 防死循环
- 跳过 sender="浪子" 的自消息
