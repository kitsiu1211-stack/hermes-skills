#!/usr/bin/env python3
"""
豆包 TTS WebSocket 双向流式 API 测试脚本
端点: wss://openspeech.bytedance.com/api/v3/tts/bidirection
用法: 修改 API_KEY 后运行 python3 test_doubao_tts.py
"""

import asyncio
import websockets
import json
import uuid
import base64

# ========== 配置（使用前修改） ==========
API_KEY = "YOUR_SPEECH_API_KEY"  # 豆包语音的 Key，非豆包大模型 ARK
RESOURCE_ID = "seed-tts-2.0"     # seed-tts-2.0 或 seed-icl-2.0
SPEAKER = "zh_female_qingxin"    # 音色 ID
AUDIO_FORMAT = "mp3"             # pcm 推荐用于流式，mp3 方便试听
SAMPLE_RATE = 24000
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
TEST_TEXT = "你好，我是浪子，测试语音合成功能。"
OUTPUT_PATH = "/tmp/tts_test.mp3"
# ========================================

async def test_tts():
    headers = {
        "X-Api-Key": API_KEY,
        "X-Api-Resource-Id": RESOURCE_ID,
    }

    print(f"[1] Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL, additional_headers=headers, ping_interval=20) as ws:
        # === StartConnection ===
        print("[2] Sending StartConnection...")
        await ws.send(json.dumps({"EventType": "StartConnection"}))

        resp = await asyncio.wait_for(ws.recv(), timeout=10)
        resp_json = json.loads(resp)
        event = resp_json.get("EventType", "")

        if event != "ConnectionStarted":
            print(f"[FAIL] Expected ConnectionStarted, got: {event}")
            print(f"       Full: {resp[:500]}")
            return

        # === StartSession ===
        session_id = str(uuid.uuid4())
        print(f"[3] Sending StartSession (id={session_id[:8]}...)")

        await ws.send(json.dumps({
            "EventType": "StartSession",
            "session_id": session_id,
            "req_params": {
                "speaker": SPEAKER,
                "audio_params": {
                    "format": AUDIO_FORMAT,
                    "sample_rate": SAMPLE_RATE
                }
            }
        }))

        resp = await asyncio.wait_for(ws.recv(), timeout=10)
        resp_json = json.loads(resp)
        event = resp_json.get("EventType", "")

        if event != "SessionStarted":
            print(f"[FAIL] Expected SessionStarted, got: {event}")
            print(f"       Full: {resp[:500]}")
            return

        # === TaskRequest ===
        print(f"[4] Sending TaskRequest: '{TEST_TEXT}'")
        await ws.send(json.dumps({
            "EventType": "TaskRequest",
            "session_id": session_id,
            "text": TEST_TEXT
        }))

        # === Receive responses ===
        audio_chunks = []
        for i in range(50):
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=10)
                resp_json = json.loads(resp)
                event = resp_json.get("EventType", "")

                if event == "TTSResponse":
                    audio_b64 = resp_json.get("payload", {}).get("audio", "")
                    if audio_b64:
                        audio_chunks.append(audio_b64)
                    print(f"    TTSResponse #{i+1}, audio_b64_len={len(audio_b64)}")
                elif event == "TTSSentenceStart":
                    print(f"    TTSSentenceStart")
                elif event == "TTSSentenceEnd":
                    print(f"    TTSSentenceEnd")
                elif event == "SessionFinished":
                    usage = resp_json.get("payload", {}).get("usage", {})
                    print(f"[5] SessionFinished, text_words={usage.get('text_words', '?')}")
                    break
                elif event in ("SessionFailed", "ConnectionFailed"):
                    print(f"[FAIL] {event}: {resp[:500]}")
                    break
                else:
                    print(f"    Event: {event}")
            except asyncio.TimeoutError:
                print("[TIMEOUT] No response, finishing...")
                break

        # === Cleanup ===
        await ws.send(json.dumps({"EventType": "FinishSession", "session_id": session_id}))
        await ws.send(json.dumps({"EventType": "FinishConnection"}))

        if audio_chunks:
            audio_bytes = b"".join(base64.b64decode(c) for c in audio_chunks)
            with open(OUTPUT_PATH, "wb") as f:
                f.write(audio_bytes)
            print(f"\n[SUCCESS] Audio saved to {OUTPUT_PATH}, size={len(audio_bytes)} bytes")
        else:
            print("\n[FAIL] No audio received")

if __name__ == "__main__":
    asyncio.run(test_tts())
