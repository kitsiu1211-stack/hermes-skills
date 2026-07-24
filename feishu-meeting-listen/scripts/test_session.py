#!/usr/bin/env python3
"""测试 Qwen-Audio-Realtime WebSocket Session"""
import os, sys, json, signal

env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import websocket

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

def test_url(url, label):
    print(f"\n{'='*50}")
    print(f"[测试] {label}: {url}")
    print(f"{'='*50}")
    
    def on_open(ws):
        print("[WS] 已连接", flush=True)
        config = {
            "type": "session.update",
            "session": {
                "model": "qwen-audio-3.0-realtime-flash",
                "modalities": ["text"]
            }
        }
        ws.send(json.dumps(config))
        print("[发送] session.update", flush=True)
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type", "?")
            print(f"[响应] type={msg_type}", flush=True)
            if msg_type == "session.created":
                sid = data.get("session", {}).get("id", "?")
                print(f"✅✅✅ Session 创建成功！ID: {sid}", flush=True)
            elif msg_type == "error":
                print(f"❌ 错误: {json.dumps(data, ensure_ascii=False)[:300]}", flush=True)
        except Exception as e:
            print(f"[解析] {e}: {message[:200]}", flush=True)
    
    def on_error(ws, error):
        print(f"[WS错误] {error}", flush=True)
    
    def on_close(ws, code, msg):
        print(f"[WS关闭] {code}: {msg}", flush=True)
    
    signal.alarm(12)
    try:
        ws = websocket.WebSocketApp(
            url,
            header={"Authorization": f"Bearer {API_KEY}"},
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever()
    except Exception as e:
        print(f"[失败] {e}", flush=True)

signal.signal(signal.SIGALRM, lambda *_: sys.exit(0))
test_url("wss://dashscope.aliyuncs.com/api-ws/v1/realtime", "realtime")
