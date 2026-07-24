# Bot 入会 SayHello 无声 Bug

**日期**：2026-07-19
**会议**：629602570「袁鑫杰的视频会议」
**状态**：待排查

## 现象

`main.py` 全链路连接成功，但会中无人听到 Bot 说话。

## 日志时间线

```
23:43:40 [bv] joined meeting meeting_id=7664112450137328623
23:43:42 [bv] realtime endpoint ready
23:43:43 [bv] WS connected
23:43:44 [bv] session created
23:43:47 [doubao] connected
23:43:47 [doubao] session started
23:43:47 [fwd] doubao_to_byteview started    ← 音频转发就绪
23:43:48 [doubao] SayHello sent              ← 开场白发出
                 ↓
                 ← 没有任何 TTS 音频回传！
                 ← forward_doubao_to_byteview 的 "got tts audio" 从未触发
                 ← receive_audio() 的 AudioOnlyServer 分支从未进入
```

## 根因假设

`say_text()` 使用 `EventType.SayHello` + `task_request()` 发送文字给豆包，但豆包服务端**未返回 TTS 音频**。可能原因：

1. SayHello 在豆包协议中不触发 TTS 生成（仅用于握手/连接确认）
2. 需要额外配置参数（如 speaker voice 设置）
3. 豆包服务端连接模式不匹配

## 已验证正常的部分

| 组件 | 状态 |
|------|------|
| Bot 入会 API | ✅ |
| ByteView WebSocket 连接 | ✅ |
| Doubao WebSocket 连接 | ✅ |
| Session 建立 | ✅ |
| 音频转发框架 | ✅（创建了 forward 任务，等待音频） |
| 音频流方向 (ByteView → Doubao) | 未测试（需要真人说话触发） |

## 下次测试建议

1. 跳过 `SayHello` 开场白，直接测试会中对话——看真人说话时 Doubao 是否生成 TTS
2. 或使用 `--poll-events` 与会中字幕联动
3. 检查豆包 SayHello 协议文档，确认是否需要不同的事件类型触发 TTS
