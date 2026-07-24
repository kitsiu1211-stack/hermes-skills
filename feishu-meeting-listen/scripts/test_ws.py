#!/usr/bin/env python3
"""测试 WebSocket 连通性"""
import os, sys, json

# 加载 .env
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import websocket
import signal

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
WS_URL = "wss://dashscope.aliyuncs.com/api/v1/realtime"

def timeout_handler(signum, frame):
    print("\n[超时] 15s 无响应，可能 WS URL 不对")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(15)

print(f"[测试] 连接 {WS_URL}...", flush=True)
try:
    ws = websocket.create_connection(
        WS_URL,
        header={"Authorization": f"Bearer {API_KEY}"},
        timeout=10
    )
    print("[连接] OK", flush=True)

    config = {
        "type": "session.update",
        "session": {
            "model": "qwen-audio-3.0-realtime-flash",
            "modalities": ["text"]
        }
    }
    ws.send(json.dumps(config))
    print("[发送] session.update", flush=True)

    for i in range(5):
        try:
            ws.settimeout(3)
            msg = ws.recv()
            data = json.loads(msg)
            msg_type = data.get("type", "?")
            print(f"[响应#{i}] type={msg_type}", flush=True)
            
            if msg_type == "session.created":
                session_id = data.get("session", {}).get("id", "?")
                print(f"✅ Session 创建成功！ID: {session_id}", flush=True)
                break
            elif msg_type == "error":
                print(f"❌ 错误: {json.dumps(data, ensure_ascii=False)}", flush=True)
                break
        except websocket.WebSocketTimeoutException:
            print(f"[等待#{i}] ...", flush=True)
            continue
        except Exception as e:
            print(f"[异常] {e}", flush=True)
            break

    ws.close()
    print("[关闭] 连接已关闭", flush=True)

except Exception as e:
    print(f"[失败] {e}", flush=True)
