#!/usr/bin/env python3
"""
Phase 2: Agent 会议语音输出
数据流: 文本 → 豆包 TTS (WebSocket) → MP3 → Opus → 系统音频播放 → BlackHole → 会议麦克风

用法:
  python3 meeting_speaker.py "要说的话"

前置:
  - Multi-Output Device (BlackHole + 扬声器) 已设为默认输出
  - 豆包语音 API Key 已配置
  - protocols_.py 已下载到指定路径
"""

import asyncio
import sys
import json
import os
import uuid
import copy
import subprocess
import tempfile

sys.path.insert(0, "/tmp/tts_proto/TTS Websocket Bidirection protocols")

import websockets
from protocols_ import (
    Message, MsgType, MsgTypeFlagBits, EventType,
    start_connection, start_session, finish_session, task_request,
    receive_message, wait_for_event,
)

# ── 配置 ──
API_KEY = "c3c35e49-452f-4c7a-a434-355d97dbb179"
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

# 默认音色
DEFAULT_SPEAKER = "zh_female_xiaohe_uranus_bigtts"

# 可用音色
SPEAKERS = {
    "小何": "zh_female_xiaohe_uranus_bigtts",
    "vivi": "zh_female_vv_uranus_bigtts",
    "清新": "zh_female_qingxinnvsheng_uranus_bigtts",
    "魅力": "zh_female_meilinvyou_uranus_bigtts",
    "小天": "zh_male_taocheng_uranus_bigtts",
    "暖阳": "zh_female_kefunvsheng_uranus_bigtts",
}


async def synthesize(text, speaker=None, output_path=None):
    """调用豆包 TTS 合成语音，返回 MP3 文件路径"""
    speaker_id = SPEAKERS.get(speaker, DEFAULT_SPEAKER) if speaker else DEFAULT_SPEAKER
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"tts_{uuid.uuid4().hex[:8]}.mp3")

    headers = {
        "X-Api-Key": API_KEY,
        "X-Api-Resource-Id": "seed-tts-2.0",
    }

    async with websockets.connect(WS_URL, additional_headers=headers, max_size=10*1024*1024) as ws:
        await start_connection(ws)
        await wait_for_event(ws, MsgType.FullServerResponse, EventType.ConnectionStarted)

        session_id = str(uuid.uuid4())
        base = {
            "req_params": {
                "speaker": speaker_id,
                "audio_params": {"format": "mp3", "sample_rate": 24000},
            }
        }

        # StartSession
        start_req = copy.deepcopy(base)
        start_req["event"] = EventType.StartSession
        await start_session(ws, json.dumps(start_req).encode(), session_id)
        await wait_for_event(ws, MsgType.FullServerResponse, EventType.SessionStarted)

        # TaskRequest — text 在 req_params 里面
        task_req = copy.deepcopy(base)
        task_req["event"] = EventType.TaskRequest
        task_req["req_params"]["text"] = text
        await task_request(ws, json.dumps(task_req).encode(), session_id)
        await finish_session(ws, session_id)

        # 收集音频
        audio = b""
        while True:
            msg = await receive_message(ws)
            if msg.type == MsgType.AudioOnlyServer:
                audio += msg.payload
            elif msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
                elif msg.event == EventType.SessionFailed:
                    raise RuntimeError(f"Session failed: {msg.payload[:200]}")

        with open(output_path, "wb") as f:
            f.write(audio)

        return output_path, len(audio)


def play_audio(filepath):
    """播放音频到系统默认输出（→ Multi-Output Device → BlackHole → 会议麦克风）"""
    subprocess.run(["afplay", filepath], check=True)


def speak_in_meeting(text, speaker="小何"):
    """完整链路：文本 → TTS → 播放到会议"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        mp3_path, size = loop.run_until_complete(synthesize(text, speaker))
        print(f"[TTS] 合成完成: {mp3_path} ({size} bytes)")

        print(f"[播放] 输出到系统音频...")
        play_audio(mp3_path)
        print(f"[播放] 完成")

        # 清理
        os.remove(mp3_path)
        return True
    except Exception as e:
        print(f"[错误] {e}")
        return False
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════
#  命令行入口
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 meeting_speaker.py <要说的话> [音色名]")
        print(f"可用音色: {', '.join(SPEAKERS.keys())}")
        sys.exit(1)

    text = sys.argv[1]
    speaker = sys.argv[2] if len(sys.argv) > 2 else "小何"

    print(f"[启动] 音色={speaker}, 文本={text}")
    success = speak_in_meeting(text, speaker)
    sys.exit(0 if success else 1)
