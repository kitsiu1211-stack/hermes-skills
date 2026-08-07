# 飞书会议语音 Agent 指南

## 三种会议模式（用户 2026-07-21 定义）

### 模式 1：静默旁听 → 会后出纪要
用户说"旁听会议"→ 启动 `listen_subtitles.py`，不入会，静默收集字幕，会议结束后自动生成纪要。
- 不接豆包 TTS，不发声
- 会后根据会议内容的待办，找对应 Agent 完成

### 模式 2：拉入会 → 语音对话（ByteView + 豆包）
用户拉 Bot 入会 → Bot 加入，默认静音。用户说"浪子可以开麦了"→ 启动语音管线：
```bash
python3.11 main.py --config config.yaml --meeting-no <会议号> --keep-in-meeting --poll-events
```
- ByteView WebSocket 桥接会议音频 ↔ 豆包实时语音
- 不走 BlackHole，不走系统音频设备

### 模式 3：会中聊天框 @浪子 → 文字回复
Chat poller 检测聊天事件中的"浪子"，通过 Hermes LLM 即时生成回复，用 `lark-cli vc +meeting-message-send` 发回会议聊天框。

## 卡顿修复（最终方案）

**根因**：`voice_agent/byteview.py` 的 `send_audio()` 将 TTS 音频按 4800 字节分片后，每片 `asyncio.sleep()` 延迟发送，句子中间产生真空期导致卡顿。

**修复**：保留分片（ByteView 协议要求），**去掉 delay**——连续快速发出：

```python
async def send_audio(self, audio: bytes) -> None:
    for chunk in split_pcm_s16le(audio):      # 4800 字节/帧
        _, frame = build_audio_upstream_append_frame(self.session_id, chunk)
        await self.ws.send(frame)              # 无 sleep，连续发送
```

**试错记录**：

| 尝试 | 结果 | 原因 |
|------|------|------|
| sleep 用 16000 替代 48000 | 仍卡 | 豆包实际输出 24kHz，非 16kHz |
| 分片增大到 19200 字节 | 完全无声 | ByteView 静默丢弃大帧 |
| 整段发不拆分 | 完全无声 | 同上 |
| 分片 4800 + 无 sleep | ✅ 流畅 | 当前方案 |

**豆包 TTS 参数**：24kHz s16le mono（`doubao.py` 第 177 行）。

## 依赖安装

```bash
pip3 install pyyaml websockets --break-system-packages
```

## ByteView 实时音频兼容性

**并非所有会议都支持 ByteView 实时音频**。会议创建时决定了是否启用该能力，无法中途升级。

**判别方法**：启动 `main.py` 后，如果日志只有 `session created` 但**没有后续 `[bv] raw msg` 音频流**，说明该会议不支持 ByteView 实时音频。

**降级方案**：会议不支持语音时自动切换：
- `lark-cli vc +meeting-message-send` 在会议聊天框发文字回复
- `listen_subtitles.py` 旁听字幕

## listen_subtitles.py 修复

**Bug**：inbox JSON 文件可能因历史损坏返回 dict 而非 list，导致 `inbox.append()` 报 `AttributeError`。

**修复**：`json.load` 后检查类型：
```python
inbox = json.load(f)
if not isinstance(inbox, list):
    inbox = [inbox]
```
