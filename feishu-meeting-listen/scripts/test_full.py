#!/usr/bin/env python3
"""快速测试 ASR 全链路"""
import os, sys, json, time, threading, uuid
import pyaudio, websocket

env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
SAMPLE_RATE = 16000
CHUNK_SIZE = 3200

# Find BlackHole
p = pyaudio.PyAudio()
device_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if "BlackHole" in info["name"] and info["maxInputChannels"] > 0:
        device_index = i
        print(f"[音频] 设备: {info['name']} (index={i})", flush=True)
        break

if device_index is None:
    print("[错误] 找不到 BlackHole", flush=True)
    sys.exit(1)

stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE,
                input=True, input_device_index=device_index,
                frames_per_buffer=CHUNK_SIZE)

# ASR
task_id = str(uuid.uuid4())[:8]
started = threading.Event()
results = []
done = threading.Event()

def on_open(ws):
    ws.send(json.dumps({
        "header": {"action": "run-task", "task_id": task_id, "streaming": "duplex"},
        "payload": {
            "task_group": "audio", "task": "asr", "function": "recognition",
            "model": "paraformer-realtime-v2",
            "parameters": {
                "format": "pcm", "sample_rate": SAMPLE_RATE,
                "enable_intermediate_result": True, "enable_punctuation": True,
            },
            "input": {}
        }
    }))
    print("[ASR] run-task 已发送", flush=True)

def on_message(ws, msg):
    d = json.loads(msg)
    e = d.get("header", {}).get("event", "")
    if e == "task-started":
        started.set()
        print("[ASR] ✅ task-started", flush=True)
    elif e == "task-failed":
        err = d.get("header", {}).get("error_message", "?")
        print(f"[ASR] ❌ {err}", flush=True)
        results.append(f"FAIL: {err}")
        done.set()
    elif e == "result-generated":
        text = d.get("payload", {}).get("output", {}).get("sentence", {}).get("text", "")
        if text:
            results.append(text)
            print(f"[ASR] 📝 {text}", flush=True)
    elif e == "task-finished":
        print("[ASR] task-finished", flush=True)
        done.set()

ws_app = websocket.WebSocketApp(
    "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
    header={"Authorization": f"Bearer {API_KEY}"},
    on_open=on_open, on_message=on_message)
ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
ws_thread.start()

if not started.wait(timeout=8):
    print("[错误] ASR 连接超时", flush=True)
    sys.exit(1)

# 推流 5 秒
print("\n[测试] 推流 5 秒音频...\n", flush=True)
start_time = time.time()
while time.time() - start_time < 5 and not done.is_set():
    try:
        data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        ws_app.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
    except Exception as e:
        print(f"[推流错误] {e}", flush=True)
        break

# Finish
finish = {
    "header": {"action": "finish-task", "task_id": task_id, "streaming": "duplex"},
    "payload": {"input": {}}
}
ws_app.send(json.dumps(finish))
print(f"\n[测试] finish-task 已发送", flush=True)

# Wait for task-finished
done.wait(timeout=3)

ws_app.close()
stream.stop_stream()
stream.close()
p.terminate()

print(f"\n[结果] 转写句子数: {len(results)}")
for i, r in enumerate(results):
    print(f"  [{i}] {r}")

if not results:
    print("  (正常 — 没有语音输入时不会有转写)")
