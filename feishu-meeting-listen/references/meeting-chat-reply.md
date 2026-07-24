# 会中聊天 @浪子 回复机制

**2026-07-21 ✅ V3 — 集成到 main.py（当前方案）**

## 架构

```
会议聊天框有人发"浪子，XXX"
    ↓
main.py poll_meeting_chat()（3 秒轮询 vc +meeting-events）
    ↓
检测到 chat_received + message_type=1 + "浪子"
    ↓
doubao.say_text("【会中弹幕回复】<sender>问：<content>。请用一句话简短回复，控制在10秒以内。")
    ↓
豆包 ASR+Chat+TTS → ByteView → 会议音频/字幕
```

## 核心发现

**会议聊天消息不需要 `im.message.receive_v1` 事件订阅！** `vc +meeting-events` 会直接返回 `chat_received` 事件。

### 已验证：GTM 宣贯会议成功捕获 13+ 条弹幕

王栋、杨少杰、藏亮、楚先兵、赵鲁康、王传奇、王德昌、叶政杰、常鹏江、郭娟、左布啦、陈腾鹏——多人弹幕实时捕获。

### chat_received 事件结构

```json
{
  "event_type": "chat_received",
  "actors": [{"name": "王栋"}],
  "payload": {
    "chat_received_items": [{
      "content": "消息内容",
      "message_type": 1,
      "operator": {"user_name": "王栋"}
    }]
  }
}
```

`message_type`: 1=文本，3=表情

## 回复模式

| 触发方式 | 回复策略 | 效果 |
|---------|---------|------|
| 会中弹幕文字 | `say_text("【会中弹幕回复】{sender}问：{content}。请用一句话简短回复，控制在10秒以内。")` | 短 TTS，字幕可见，不打断会议 |
| 会中语音 | 豆包正常对话 | 自然 TTS 对话 |

## 限制

Bot 无法往会议聊天发送文字消息（Feishu API 不暴露会议聊天发送接口）。TTS 回复是唯一方案。

## V2（已弃用）

V2 使用独立 `meeting_chat_reply.py` + DeepSeek API + `+meeting-message-send`——此方案因无法获取会议 chat_id 且 API 权限受限而弃用。保留脚本 `scripts/meeting_chat_reply.py` 仅供参考。
