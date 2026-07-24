# TTS 供应商切换策略（2026-07-17）

## 当前状态
豆包 TTS Key（`c3c35e49`）HTTP 403 → 已切到 **Fish Audio HTTP API** 作为主力。

## 切换步骤
1. 确认症状：`[SPEAK]` 有输出但无声，`[TTS] ❌ HTTP 403`
2. 更换 `speak()` 中的 TTS 函数：
   - 豆包：`asyncio.run(doubao_tts(text))`
   - Fish：`fish_tts(text)` — 同步 HTTP POST
3. 验证：`python3 -c` 直接调 API，看状态码和音频字节数
4. 播放测试：`afplay ~/.hermes/cache/meeting_voice/last_response.wav`

## Fish Audio 注意事项
- API: `POST https://api.fish.audio/v1/tts`
- Header: `Authorization: Bearer <key>`
- Body: `{"text": "...", "format": "mp3"}`
- **不传 `reference_id`** → 默认音色（返回 200 + MP3 二进制）
- `reference_id` 如果无效 → HTTP 400 "Reference not found"

## 凭据位置
`~/.hermes/skills/feishu/feishu-meeting-listen/config/.env`
- `DOUBAO_TTS_KEY` → 豆包（当前失效）
- `FISH_AUDIO_KEY` → Fish Audio（当前主力）

## 豆包恢复后
1. 换新 Key 写入 `.env`
2. `speak()` 改回 `asyncio.run(doubao_tts(text))`
3. Fish 降为备用
