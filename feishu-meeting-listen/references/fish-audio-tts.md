# Fish Audio TTS（已接入，当前主力）

## 接入时间
2026-07-17 — 豆包 TTS WebSocket API Key `c3c35e49` HTTP 403 过期后切换。

## API
- 端点: `POST https://api.fish.audio/v1/tts`
- 鉴权: `Authorization: Bearer <API_KEY>`
- Key: `31ce9749f84b439cb2e1480dc54ba43d` (来自 `config/.env` `FISH_AUDIO_KEY`)
- 协议: HTTP JSON in → MP3 binary out（同步，非流式）

## 实际调用
```python
resp = requests.post(
    "https://api.fish.audio/v1/tts",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"text": text, "format": "mp3"},
    timeout=30,
)
if resp.status_code == 200:
    with open(path, "wb") as f:
        f.write(resp.content)
```

## 音色
- **当前**: 不传 `reference_id` — 使用默认音色（用户反馈：太魔性）
- **排坑**: 之前 `reference_id=03397b4c4be74759b72533b663fbd532` 已删除 → HTTP 400 "Reference not found"
- **改进**: 去 [fish.audio](https://fish.audio) 创建克隆音色 → 获取 reference_id → 在 `fish_tts()` 中传 `json={"text": text, "reference_id": ref_id, "format": "mp3"}`

## 集成位置
- `~/.hermes/scripts/meeting_voice.py` → `fish_tts()` 函数
- `speak()` 当前调用 `fish_tts()` (不再是 `doubao_tts()`)
- 播放在 V4 的 `speak()` 中: `fish_tts(text)` → `afplay` → 会议旁听 → 扬声器

## 验证状态
- ✅ HTTP 200: API 正常工作，国内可直连
- ✅ MP3 音频返回 (>10KB)
- ✅ `afplay` 播放正常
- ⚠️ 默认音色魔性 → 待用户创建克隆音色
- ⚠️ 非流式 → 不适合实时双工会话（但与 V4 的 HTTP 同步调用模式匹配，端到端 ~2-3s）

## 与豆包对比

| | Fish Audio | 豆包 (已挂) |
|---|---|---|
| 状态 | ✅ 当前主力 | ❌ HTTP 403 (Key过期/额度用完) |
| 协议 | HTTP 同步 | WebSocket 双向流式 |
| 音色 | 默认（可克隆） | 小何 2.0 (台湾腔) |
| 延迟 | ~1-2s | ~1s |
| 价格 | 免费额度 | 按字符付费 |
