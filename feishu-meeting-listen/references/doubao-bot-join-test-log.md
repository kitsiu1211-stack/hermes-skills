# 豆包 Bot 入会实践记录

## 2026-07-19 四次入会测试

### 连接状态

Bot 入会全链路通 4 次：ByteView WS 连接 → 豆包 WS 连接 → Session 创建 → 音频转发 task 启动。但豆包端到端模型**全程未生成语音输出**。

### 关键修复

1. **`_start_session_payload` 缺字段**：
   - `opening_line` 未传给豆包 → 补入 `payload["opening_line"]`
   - `doubao_model` 未传给豆包 → 补入 `payload["model"]`
   - `opening_line` 位置：从 `dialog.opening_line` 改为根级别 `opening_line`（实测飞书入门文档提供者未给确切字段位置，需豆包官方 API 确认）

2. **`say_text()` 与端到端模型不兼容**：
   - `EventType.SayHello` 发送文字 → 豆包不生成 TTS
   - 端到端模型是对话模型不是 TTS——需要真人音频输入才触发语音输出
   - 已从 `main.py` 移除 `say_text()` 调用，opening_line 改由 `start_session` payload 触发

### 未解决

- 豆包 `opening_line` 虽已传入 payload，但模型仍不主动发声
- 推测：① `opening_line` 字段名不对（可能是 `greeting`/`welcome_text`）② 模型版本 `1.2.1.1` 不支持此字段 ③ 需要真人先说话激活
- 官方文档确认："空会议会报错，会议里要先有真人在场"
- 端到端模型 barge-in 默认开启，真人一开口打断 Bot

### 当前可用能力

字幕旁听（`poll.sh` → JSONL → 纪要）稳定可用。Bot 入会+Dolby 语音**仅连接层已验证**，语音输出待真人会议测试。
