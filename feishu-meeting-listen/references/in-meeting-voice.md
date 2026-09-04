# 会中语音对话（V4 实时版）

## 当前架构（2026-07-17）

```
MacBook 麦克风 → Paraformer-realtime-v2 ASR (DashScope WebSocket)
  → DeepSeek (LLM 思考)
  → 豆包 TTS (小何 2.0, WebSocket 双向流式)
  → SwitchAudioSource 切 BlackHole → afplay → 会议麦克风
  → SwitchAudioSource 切回「会议旁听」

往返延迟：~2-3 秒（零轮询，实时音频流）
```

## TTS 方案

| 方案 | 协议 | 延迟 | 音色 | 当前 |
|------|------|------|------|------|
| **豆包 TTS** | WebSocket 双向流式 | ~500ms | 小何 2.0 (`zh_female_xiaohe_uranus_bigtts`) | ✅ 主力 |
| Fish Audio | HTTP POST | ~2s | `zh_male` | 🆘 备用 |

### 豆包 TTS 凭据

- **Key**: `<your-doubao-tts-key>`（新版控制台 X-Api-Key）
- **Resource ID**: `seed-tts-2.0`
- **端点**: `wss://openspeech.bytedance.com/api/v3/tts/bidirection`
- **协议库**: `~/.hermes/scripts/doubao_tts_proto.py`
- **⚠️ 旧版凭据陷阱**: 旧版控制台 AppId (`2241627617`) + AccessKey (`-6iyrKPj-...`) 鉴权通过但返回 `data:null`（空音频），看起来像通了但实际不通。必须用新版 X-Api-Key。

### Fish Audio 凭据（备用）

- **Key**: `<your-fish-audio-key>`
- **端点**: `https://api.fish.audio/v1/tts`
- **音色**: `zh_male`（已锁定，不再随机变声）
- **注意**: 免费模型，无实时流式，仅备用。

## 凭据管理

全部集中在 `config/.env`：

```env
DOUBAO_TTS_KEY=<your-doubao-tts-key>
DOUBAO_TTS_RESOURCE_ID=seed-tts-2.0
DOUBAO_TTS_SPEAKER=zh_female_xiaohe_uranus_bigtts
DEEPSEEK_API_KEY=<your-deepseek-api-key>
FISH_AUDIO_KEY=<your-fish-audio-key>
DASHSCOPE_API_KEY=<your-dashscope-api-key>
```

版本快照：`Obsidian/hermes-skills/feishu-meeting-listen/versions/V4-realtime-asr-20260717.md`

## 音频路由

### BlackHole 搭建（推荐）

```bash
brew install blackhole-2ch
# Audio MIDI Setup → + → 创建多输出设备 → 勾选 BlackHole 2ch + MacBook Air扬声器
# 命名为「会议旁听」→ 右键 → 设为默认输出
# 飞书会议 → 音频设置 → 扬声器选「会议旁听」
```

### BlackHole 静音排坑

**症状**：ASR 连上了但不输出字幕，`find_input_device` 找到 BlackHole 但静音（峰值 = 0）。

**根因**：多输出设备「会议旁听」不含 BlackHole 子设备——可能只含扬声器。

**检查**：`system_profiler SPAudioDataType` 或 Audio MIDI Setup 查看子设备列表。

**临时方案**：V4 自动回退 MacBook 麦克风收音，TTS 通过 `SwitchAudioSource` 临时切 BlackHole 播放后切回「会议旁听」。

### TTS 输出到会议

当前方案：`SwitchAudioSource -t output -s "BlackHole 2ch"` → `afplay` → `SwitchAudioSource -t output -s "会议旁听"`

飞书会议麦克风必须选 **BlackHole 2ch** 才能收到 TTS 音频。注意：此时你的声音可能不进会（MacBook 麦克风未被 Feishu 捕获）。

## 启动

```bash
python3 ~/.hermes/scripts/meeting_voice.py
```

说「浪子」触发回复。

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 豆包 TTS 返回 `data:null` | 用了旧版 AppId+AccessKey | 用新版 X-Api-Key (`c3c35e49...`) |
| 豆包 TTS `resource ID mismatched` | 音色不匹配 model | 小何 2.0 (`zh_female_xiaohe`) 只匹配 `seed-tts-2.0`；`zh_female_vv` 是 Vivi 不是小何 |
| BlackHole 静音 | 多输出设备不含 BlackHole | Audio MIDI Setup 重建，或自动回退 MacBook 麦克风 |
| ASR 连接超时 | DashScope 网络问题 | 检查 VPN / 重试 |
| TTS 声音不进入会议 | 飞书麦克风未选 BlackHole | 飞书会议 → 音频设置 → 麦克风 → BlackHole 2ch |
| 声音变来变去（百变星君） | Fish Audio 未指定 speaker | 加 `"speaker": "zh_male"` |
| **🚨 信息错乱（前后结论矛盾）** | 凭据散落，复测用错凭据 | ① 统一读 `.env` ② Obsidian 快照 ③ 复测前 `read_file` 上次成功脚本 |
