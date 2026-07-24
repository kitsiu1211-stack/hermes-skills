# 字幕旁听（bot 入会 + 字幕轮询）

## 触发

用户说「旁听会议」→ 启动 `listen_subtitles.py`。

## 方案

```
1. lark-cli vc +meeting-list-active --as user → 获取 meeting_no
2. lark-cli vc +meeting-join --as bot --meeting-number <meeting_no> → 入会
3. while True: lark-cli vc +meeting-events --as bot --meeting-id <id> --page-all
   → 过滤 transcript_received + chat_received → 打印到 stdout
4. 连续 3 次 JSON parse 空 → 会议已结束 → lark-cli vc +meeting-leave
```

## 为什么不用 --as user

`--as user` 会中有效但 session 短命，会议一结束 API 返回空 JSON，持续报 `Expecting value` 错误。Bot 入会后 `--as bot` 稳定得多。

## 脚本位置

`~/Documents/Codex_Project/feishu-voice-agent-starter/listen_subtitles.py`

## 输出格式

```
旁听: 飞书文档安全功能沟通 (839186947)
已入会 meeting_id=xxx
张三: 今天我们来讨论一下方案
李四: 我觉得可以从三个方向入手
[弹幕] 袁鑫杰: OK
[结束] 会议已结束
已离会
```

## 与 main.py（ByteView + 豆包）的区别

| | listen_subtitles.py | main.py |
|---|---|---|
| 入会方式 | bot 入会 | bot 入会 |
| 音频 | 无（字幕文本） | ByteView WebSocket 24kHz |
| 语音交互 | ❌ | 豆包 ASR+TTS |
| 弹幕监控 | ✅ chat_received | ✅ poll_meeting_chat |
| 适用 | 旁听不打扰 | 实时对话 |
| 稳定性 | 高（纯轮询） | 中（ASR 偶空白） |
