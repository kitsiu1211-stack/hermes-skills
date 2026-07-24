#!/usr/bin/env python3
"""测试 DashScope 实时语音识别 (Paraformer)"""
import os, sys, json, uuid, threading

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
TASK_ID = str(uuid.uuid4())

models = [
    "paraformer-realtime-v2",
    "paraformer-realtime-v1",
    "fun-asr-realtime",
    "qwen3-asr-flash-realtime",
]

for model in models:
    print(f"\n{'='*60}")
    print(f"[测试] model={model}")
    print(f"{'='*60}")
    
    results = []
    task_id = str(uuid.uuid4())[:8]
    
    def on_open(ws):
        # Send run-task
        run_task = {
            "header": {
                "action": "run-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": model,
                "parameters": {
                    "format": "pcm",
                    "sample_rate": 16000,
                    "enable_intermediate_result": True,
                    "enable_punctuation": True,
                }
            }
        }
        ws.send(json.dumps(run_task))
        print(f"[发送] run-task task_id={task_id}", flush=True)
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            header = data.get("header", {})
            event = header.get("event", "?")
            task_id_resp = header.get("task_id", "?")
            
            if event == "task-started":
                results.append("✅ task-started")
                print(f"[响应] ✅ task-started (task_id={task_id_resp})", flush=True)
            elif event == "task-failed":
                code = header.get("error_code", "")
                msg_text = header.get("error_message", "")
                results.append(f"❌ {code}: {msg_text[:80]}")
                print(f"[响应] ❌ {code}: {msg_text[:120]}", flush=True)
            elif event == "result-generated":
                payload = data.get("payload", {})
                output = payload.get("output", {})
                sentence = output.get("sentence", {})
                text = sentence.get("text", "")
                if text:
                    results.append(f"📝 {text}")
                    print(f"[转写] {text}", flush=True)
            else:
                results.append(f"event={event}")
                print(f"[响应] event={event}", flush=True)
        except Exception as e:
            print(f"[解析] {e}: {message[:200]}", flush=True)
    
    def on_error(ws, error):
        print(f"[WS错误] {str(error)[:100]}", flush=True)
        results.append(f"WS错误: {str(error)[:80]}")
    
    def on_close(ws, code, msg):
        print(f"[关闭] code={code} msg={str(msg)[:80]}", flush=True)
    
    try:
        ws = websocket.WebSocketApp(
            "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            header={"Authorization": f"Bearer {API_KEY}"},
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        t = threading.Thread(target=ws.run_forever, daemon=True)
        t.start()
        t.join(timeout=8)
        try:
            ws.close()
        except:
            pass
    except Exception as e:
        print(f"[异常] {e}", flush=True)
    
    print(f"  结果: {' | '.join(results) if results else 'no_response'}")
