---
name: fish-audio-tts
description: Integrate Fish Audio TTS — free S2.1 Pro model, HTTP API, Hermes custom command provider setup, and pitfalls.
trigger: User wants to set up, test, or debug Fish Audio TTS, or references fish.audio / S2.1 Pro / s2.1-pro-free model.
---

# Fish Audio TTS Integration

Integrate Fish Audio TTS into Hermes via the custom command provider mechanism. Fish Audio offers a **free** model (`s2.1-pro-free`) with 83-language support via a straightforward HTTP REST API.

## Quick Reference

| Item | Value |
|------|-------|
| Endpoint | `https://api.fish.audio/v1/tts` |
| Free model | `s2.1-pro-free` |
| Auth | `Authorization: Bearer <api_key>` |
| API key page | `https://fish.audio/app/api-keys` |
| Developer/credit page | `https://fish.audio/app/developers` |
| Output formats | mp3, wav, ogg, flac |

## Critical Pitfalls

### 1. Free model STILL requires positive API balance

Even though `s2.1-pro-free` doesn't deduct credits per call, the API rejects calls with HTTP 402 if the account balance is $0:

```
{"message":"Insufficient API credit. API credit is managed independently 
from platform credit.","status":402}
```

**Fix**: Go to `https://fish.audio/app/developers` — API credit is separate from platform credit. Either claim free sign-up credits or top up $5 minimum.

### 2. Model goes in the HTTP header, NOT the request body

The docs code snippet shows the model in the header:

```bash
curl ... -H "model: s2.1-pro-free" ...
```

The request body's `reference_id` field is for **voice cloning** (reference audio ID), not for the model name. Using `reference_id` with a model name returns HTTP 400:

```
{"message":"reference_id must be 1..=128 chars of [A-Za-z0-9_-]","status":400}
```

### 3. VPN required from China

Fish Audio servers are hosted outside China. Requests from within China will time out without a VPN/proxy.

### 5. Default voice works without speaker/reference_id

As of 2026-07-17, the simplest working call uses no `speaker` or `reference_id`:

```python
resp = requests.post("https://api.fish.audio/v1/tts",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"text": text, "format": "mp3"})
# Returns 200 + MP3 bytes with default Chinese voice
```

This is the current fallback used when 豆包 TTS is unavailable. The model header (`model: s2.1-pro-free`) is optional.

The free model without a `speaker` parameter randomly selects a voice each call — alternating male/female. **Always include `"speaker": "zh_male"` or `"zh_female"` in the request body** to lock consistency.

```bash
curl ... -d '{"text":"你好","format":"wav","speaker":"zh_male"}'
```

Confirmed working speakers: `zh_male`, `zh_female`, `speaker_0`, `default`.

## Manual API Test

```bash
curl -s --max-time 15 "https://api.fish.audio/v1/tts" \
  -H "Authorization: Bearer <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -H "model: s2.1-pro-free" \
  -d '{"text":"你好，测试","format":"mp3"}' \
  -o /tmp/fish_test.mp3

file /tmp/fish_test.mp3
# MPEG ADTS, layer III, v1, 128 kbps, 44.1 kHz, Monaural
```

## Hermes Integration: Custom Command Provider

Fish Audio is NOT a built-in Hermes TTS provider. Use the `tts.providers.<name>` custom command provider mechanism.

### Wrapper Script

The command template uses `{input_path}` (text file) and `{output_path}` placeholders. A wrapper script handles JSON escaping properly:

```bash
#!/bin/bash
# ~/.hermes/scripts/fish_audio_tts.sh
API_KEY="<YOUR_KEY>"
MODEL="s2.1-pro-free"
ENDPOINT="https://api.fish.audio/v1/tts"

INPUT="$1"
OUTPUT="$2"

TEXT_JSON=$(python3 -c "import json,sys; print(json.dumps(open('$INPUT').read()))")

HTTP_CODE=$(curl -s --max-time 15 -w "%{http_code}" "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -H "model: $MODEL" \
    -d "{\"text\":$TEXT_JSON,\"format\":\"mp3\"}" \
    -o "$OUTPUT" 2>/dev/null)

if [ "$HTTP_CODE" != "200" ]; then
    echo "Error: HTTP $HTTP_CODE" >&2
    cat "$OUTPUT" >&2
    exit 1
fi
```

### Config

```bash
hermes config set tts.provider fish-audio
hermes config set tts.providers.fish-audio.type command
hermes config set tts.providers.fish-audio.command \
  "bash /Users/<user>/.hermes/scripts/fish_audio_tts.sh {input_path} {output_path}"
hermes config set tts.providers.fish-audio.format mp3
hermes config set tts.providers.fish-audio.voice_compatible true
```

Resulting `config.yaml`:

```yaml
tts:
  provider: fish-audio
  providers:
    fish-audio:
      type: command
      command: "bash /Users/<user>/.hermes/scripts/fish_audio_tts.sh {input_path} {output_path}"
      format: mp3
      voice_compatible: true
```

### How Custom Command Providers Work

- Hermes writes the text to synthesize into a temp file, passes the path as `{input_path}`
- `{output_path}` is where the command must write the audio file
- Available placeholders: `{input_path}`, `{text_path}`, `{output_path}`, `{format}`, `{voice}`, `{model}`, `{speed}`
- `{{...}}` double-brace escapes to literal `{...}` in the rendered command
- The command must write a valid audio file to `{output_path}` and exit 0 on success
- Non-zero exit / timeout / empty output are caught and surfaced as errors
- Hermes auto-converts the output to Opus OGG for voice delivery

### Verification

After config, test with:

```
# In Hermes session: /voice tts, then send any text
# Or use the text_to_speech tool directly
```

Check `~/.hermes/audio_cache/` for generated files.

## Comparison: Fish Audio vs Volcengine (豆包)

| | Fish Audio S2.1 Pro | 豆包 seed-tts-2.0 |
|---|---|---|
| Price | Free | Paid (per char) |
| Protocol | HTTP REST | WebSocket binary + HTTP |
| Latency | ~1-2s | ~500ms |
| Languages | 83 | Chinese-focused |
| VPN needed | No (2026-07-17 verified from China) | No |
| Hermes built-in | No | No |
| V4 integration | ✅ HTTP POST → afplay | ❌ Key expired 2026-07-17 (HTTP 403) |
