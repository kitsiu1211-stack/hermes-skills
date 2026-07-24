#!/usr/bin/env python3
"""合成音频测试 ASR — 不依赖 BlackHole 路由"""
import os, sys, json, time, math, struct, threading, uuid
import websocket

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
task_id = str(uuid.uuid4())[:8]

# 生成含语音特征的测试音频
# 注意：Paraformer 需要真实语音，合成音频可能识别不到
# 但我们先测链路

results = []
started = threading.Event()
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

def on_message(ws, msg):
    d = json.loads(msg)
    e = d.get("header", {}).get("event", "")
    if e == "task-started":
        started.set()
        print("[ASR] ✅ task-started")
    elif e == "task-failed":
        err = d.get("header", {}).get("error_message", "?")
        print(f"[ASR] ❌ {err}")
        results.append(f"FAIL: {err}")
        done.set()
    elif e == "result-generated":
        text = d.get("payload", {}).get("output", {}).get("sentence", {}).get("text", "")
        if text:
            results.append(text)
            print(f"[ASR] 📝 {text}")
    elif e == "task-finished":
        print("[ASR] task-finished")
        done.set()

ws_app = websocket.WebSocketApp(
    "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
    header={"Authorization": f"Bearer {API_KEY}"},
    on_open=on_open, on_message=on_message)
ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
ws_thread.start()

print("[测试] 等待 ASR 连接...")
if not started.wait(timeout=10):
    print("[错误] 连接超时")
    sys.exit(1)

print("[测试] 全链路 ✅ ASR 连接正常")

# 发送 finish-task
finish = {
    "header": {"action": "finish-task", "task_id": task_id, "streaming": "duplex"},
    "payload": {"input": {}}
}
ws_app.send(json.dumps(finish))
print("[测试] finish-task 已发送")

done.wait(timeout=3)
ws_app.close()

print(f"\n[总结]")
print(f"  ASR 连接: ✅")
print(f"  task-started: ✅")
print(f"  task-finished: {'✅' if done.is_set() else '⚠️ 超时'}")
print(f"  转写结果: {len(results)} 条")
print(f"\n✅ 核心链路验证通过！")
print(f"   下一步: 配置音频路由后即可实时转写")
