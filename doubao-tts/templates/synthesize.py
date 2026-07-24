import asyncio
import sys
import json
import uuid
import copy
from pathlib import Path

# Path to the unzipped protocols directory from:
# https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_5ec6e28945592c909158dc1e2cf9a89c.zip
PROTO_DIR = "<path-to-extracted-protocols>"
sys.path.insert(0, PROTO_DIR)

import websockets
from protocols_ import (
    EventType, MsgType, MsgTypeFlagBits,
    start_connection, finish_connection,
    start_session, finish_session, task_request,
    receive_message, wait_for_event,
)

API_KEY = "<your-api-key>"
RESOURCE_ID = "seed-tts-2.0"
SPEAKER = "zh_female_vv_uranus_bigtts"
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"


async def synthesize(text: str) -> bytes:
    """Synthesize text to MP3 audio bytes."""
    headers = {
        "X-Api-Key": API_KEY,
        "X-Api-Resource-Id": RESOURCE_ID,
    }

    async with websockets.connect(
        WS_URL, additional_headers=headers, max_size=10 * 1024 * 1024
    ) as ws:
        # 1. Start connection
        await start_connection(ws)
        await wait_for_event(ws, MsgType.FullServerResponse, EventType.ConnectionStarted)

        # 2. Start session
        session_id = str(uuid.uuid4())
        base_req = {
            "req_params": {
                "speaker": SPEAKER,
                "audio_params": {"format": "mp3", "sample_rate": 24000},
            }
        }
        start_req = copy.deepcopy(base_req)
        start_req["event"] = EventType.StartSession
        await start_session(ws, json.dumps(start_req).encode(), session_id)
        await wait_for_event(ws, MsgType.FullServerResponse, EventType.SessionStarted)

        # 3. Send text — text goes INSIDE req_params
        task_req = copy.deepcopy(base_req)
        task_req["event"] = EventType.TaskRequest
        task_req["req_params"]["text"] = text
        await task_request(ws, json.dumps(task_req).encode(), session_id)
        await finish_session(ws, session_id)

        # 4. Collect audio
        audio = bytearray()
        while True:
            msg = await receive_message(ws)
            if msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
                elif msg.event == EventType.SessionFailed:
                    raise RuntimeError(f"SessionFailed: {msg.payload}")
            elif msg.type == MsgType.AudioOnlyServer:
                audio.extend(msg.payload)
            elif msg.type == MsgType.Error:
                raise RuntimeError(f"Error: {msg.payload}")

        return bytes(audio)


async def main():
    audio = await synthesize("你好，我是浪子，语音合成测试成功。")
    path = "/tmp/tts_output.mp3"
    with open(path, "wb") as f:
        f.write(audio)
    print(f"Saved: {path} ({len(audio)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
