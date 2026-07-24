#!/usr/bin/env python3
"""测试不同模型名"""
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

models = [
    "qwen-omni-turbo",
    "qwen-omni-turbo-realtime",
    "qwen-audio-realtime",
    "qwen3-audio-realtime",
    "qwen-audio-3.0-realtime",
    "qwen3-omni-realtime",
]

def test_model(model):
    print(f"\n{'─'*50}")
    print(f"[模型] {model}")
    
    signal.alarm(10)
    results = []
    
    def on_open(ws):
        config = {
            "type": "session.update",
            "session": {"model": model, "modalities": ["text"]}
        }
        ws.send(json.dumps(config))
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            t = data.get("type", "?")
            if t == "session.created":
                sid = data.get("session", {}).get("id", "?")
                results.append(f"✅ session={sid}")
            elif t == "error":
                err = data.get("error", {}).get("message", str(data))
                results.append(f"❌ {err[:120]}")
        except:
            results.append(f"⚠️ {message[:120]}")
    
    def on_error(ws, error):
        results.append(f"❌ {str(error)[:120]}")
    
    def on_close(ws, code, msg):
        pass
    
    try:
        ws = websocket.WebSocketApp(
            "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
            header={"Authorization": f"Bearer {API_KEY}"},
            on_open=on_open, on_message=on_message,
            on_error=on_error, on_close=on_close,
        )
        ws.run_forever()
    except:
        results.append(f"❌ 连接失败")
    
    for r in results:
        print(f"  {r}")
    return results

signal.signal(signal.SIGALRM, lambda *_: sys.exit(0))

for m in models:
    test_model(m)
