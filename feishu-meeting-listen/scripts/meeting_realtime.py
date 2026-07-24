#!/usr/bin/env python3
"""
Phase 1: 会议实时监听 — 音频采集 + 实时转写 + 千问分析 + C360 查询

数据流:
  BlackHole → PyAudio → DashScope ASR (WebSocket) → 转写文本
  → 千问 REST API (分析) → C360 CLI (客户查询)

用法:
  python3 meeting_realtime.py

前置:
  - brew install blackhole-2ch (已装)
  - 系统设置 → 声音 → 输出 → Multi-Output Device (BlackHole + 扬声器)
  - config/.env 中配置 DASHSCOPE_API_KEY
"""

import os
import sys
import json
import time
import uuid
import queue
import struct
import threading
import subprocess
import pyaudio
import websocket

# ── 加载 .env ──
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# ── 音频参数 ──
SAMPLE_RATE = 16000
CHUNK_SIZE = 3200       # 200ms per chunk at 16kHz
CHANNELS = 1
FORMAT = pyaudio.paInt16
BLACKHOLE_DEVICE = "BlackHole 2ch"

# ── ASR WebSocket ──
ASR_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

# ── 分析配置 ──
ANALYSIS_MODEL = "qwen-plus"
ANALYSIS_INTERVAL = 5.0  # 每 5 秒分析一次累积文本
C360_CHECK_COOLDOWN = 30  # 同一客户 30 秒内不重复查询

# ══════════════════════════════════════════════════════════
#  音频采集
# ══════════════════════════════════════════════════════════

def find_blackhole(p):
    """查找 BlackHole 输入设备"""
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if BLACKHOLE_DEVICE in info["name"] and info["maxInputChannels"] > 0:
            return i, info
    return None, None


def audio_capture(p, device_index, audio_queue, stop_event):
    """后台线程：从 BlackHole 持续采集音频"""
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK_SIZE,
    )
    print(f"[音频] 采集启动 (device={device_index}, rate={SAMPLE_RATE})")
    try:
        while not stop_event.is_set():
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_queue.put(data)
    except Exception as e:
        print(f"[音频] 采集异常: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        print("[音频] 采集停止")


# ══════════════════════════════════════════════════════════
#  ASR 实时转写 (WebSocket)
# ══════════════════════════════════════════════════════════

class ASRClient:
    """DashScope 实时语音识别 WebSocket 客户端"""

    def __init__(self, api_key, transcript_queue):
        self.api_key = api_key
        self.transcript_queue = transcript_queue  # 输出转写结果
        self.ws = None
        self.task_id = str(uuid.uuid4())[:8]
        self.started = threading.Event()
        self.error = None
        self._buffer = b""
        self._current_sentence = ""

    def _on_open(self, ws):
        run_task = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": "paraformer-realtime-v2",
                "parameters": {
                    "format": "pcm",
                    "sample_rate": SAMPLE_RATE,
                    "enable_intermediate_result": True,
                    "enable_punctuation": True,
                },
                "input": {}
            }
        }
        ws.send(json.dumps(run_task))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            header = data.get("header", {})
            event = header.get("event", "")

            if event == "task-started":
                self.started.set()
                print(f"[ASR] ✅ 连接成功 (task={self.task_id})")

            elif event == "task-failed":
                self.error = f"{header.get('error_code')}: {header.get('error_message')}"
                print(f"[ASR] ❌ {self.error}")

            elif event == "result-generated":
                payload = data.get("payload", {})
                output = payload.get("output", {})
                sentence = output.get("sentence", {})
                text = sentence.get("text", "")
                is_end = sentence.get("sentence_end", False)

                if text and text != self._current_sentence:
                    self._current_sentence = text
                    item = {"text": text, "is_end": is_end, "ts": time.time()}
                    self.transcript_queue.put(item)
                    marker = "。 " if is_end else "..."
                    print(f"[ASR] {text}{marker}", flush=True)

        except Exception as e:
            print(f"[ASR] 解析错误: {e}")

    def _on_error(self, ws, error):
        print(f"[ASR] WS错误: {error}")

    def _on_close(self, ws, code, msg):
        print(f"[ASR] 连接关闭 (code={code})")

    def send_audio(self, data):
        """发送音频数据到 ASR"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                self.ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception:
                pass

    def connect(self):
        """建立 WebSocket 连接（阻塞直到 task-started 或超时）"""
        self.ws = websocket.WebSocketApp(
            ASR_WS_URL,
            header={"Authorization": f"Bearer {self.api_key}"},
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()

        if not self.started.wait(timeout=10):
            print("[ASR] 连接超时")
            return False
        return True

    def close(self):
        """发送 finish-task 并关闭连接"""
        try:
            finish = {
                "header": {
                    "action": "finish-task",
                    "task_id": self.task_id,
                    "streaming": "duplex"
                },
                "payload": {"input": {}}
            }
            self.ws.send(json.dumps(finish))
            print("[ASR] 已发送 finish-task")
        except Exception:
            pass
        try:
            self.ws.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  千问文本分析
# ══════════════════════════════════════════════════════════

def analyze_transcript(text, api_key):
    """用千问分析转写文本，识别客户名和关键信息"""
    if not text or len(text) < 10:
        return None

    system_prompt = """你是一个销售会议分析助手。根据会议转写文本，提取以下信息，以 JSON 格式返回：
{
  "client_names": ["提及的客户公司名称"],
  "key_topics": ["讨论的关键话题"],
  "action_items": ["需要跟进的行动项"],
  "sentiment": "positive/neutral/negative",
  "needs_c360_lookup": true/false   // 是否提到了需要查询背景的新客户
}

如果文本中没有客户相关信息，返回 {"client_names": [], "key_topics": [], "action_items": [], "sentiment": "neutral", "needs_c360_lookup": false}
只返回 JSON，不要其他文字。"""

    import urllib.request
    payload = {
        "model": ANALYSIS_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"会议转写文本：\n{text}"}
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        req = urllib.request.Request(
            f"{DASHSCOPE_BASE}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]

        # 解析 JSON（处理 markdown code block）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)

    except Exception as e:
        print(f"[分析] 错误: {e}")
        return None


# ══════════════════════════════════════════════════════════
#  C360 客户查询
# ══════════════════════════════════════════════════════════

def lookup_customer(company_name):
    """调用 lark-c360 查询客户商机信息"""
    try:
        result = subprocess.run(
            ["lark-c360", "search", "all", "--keyword", company_name,
             "--limit", "3", "--json"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        opps = data.get("data", {}).get("opportunity", {}).get("list", [])
        summary = []
        for opp in opps[:3]:
            title = opp.get("title", {})
            abstract = opp.get("abstract", {})
            name = title.get("name", {}).get("display_value", "?")
            stage = title.get("stage", {}).get("display_value", "?")
            arr = abstract.get("arr", {}).get("display_value", "?")
            summary.append(f"{name} | {stage} | {arr}")
        return summary
    except Exception as e:
        return [f"查询失败: {e}"]


# ══════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════

def main():
    if not API_KEY:
        print("❌ 请设置 config/.env 中的 DASHSCOPE_API_KEY")
        sys.exit(1)

    # ── 初始化 PyAudio ──
    p = pyaudio.PyAudio()
    device_index, device_info = find_blackhole(p)
    if device_index is None:
        print(f"❌ 未找到 {BLACKHOLE_DEVICE} 音频设备")
        print("   请确认：brew install blackhole-2ch 已安装并重启")
        print("   然后创建 Multi-Output Device:")
        print("   打开「音频 MIDI 设置」→ + → 创建多输出设备")
        print("   勾选 BlackHole 2ch + MacBook Air扬声器")
        p.terminate()
        sys.exit(1)
    print(f"[音频] 设备: {device_info['name']}")

    # ── 队列 ──
    audio_queue = queue.Queue(maxsize=200)
    transcript_queue = queue.Queue()

    # ── 启动音频采集 ──
    stop_event = threading.Event()
    audio_thread = threading.Thread(
        target=audio_capture, args=(p, device_index, audio_queue, stop_event),
        daemon=True
    )
    audio_thread.start()

    # ── 连接 ASR ──
    asr = ASRClient(API_KEY, transcript_queue)
    if not asr.connect():
        print("[错误] ASR 连接失败")
        stop_event.set()
        p.terminate()
        sys.exit(1)

    # ── 音频推流线程 ──
    def audio_pusher():
        while not stop_event.is_set():
            try:
                data = audio_queue.get(timeout=0.5)
                asr.send_audio(data)
            except queue.Empty:
                continue
            except Exception:
                break

    pusher_thread = threading.Thread(target=audio_pusher, daemon=True)
    pusher_thread.start()

    # ── 主循环：分析转写文本 ──
    print("\n" + "=" * 60)
    print("🎤 会议监听已启动 — Ctrl+C 退出")
    print("   请确保系统音频输出已路由到 BlackHole")
    print("=" * 60 + "\n")

    accumulated_text = ""
    last_analysis = 0
    c360_cooldown = {}  # company_name → last_query_ts
    last_transcript_ts = time.time()

    try:
        while True:
            # 取转写结果
            try:
                item = transcript_queue.get(timeout=0.3)
                text = item["text"]
                is_end = item["is_end"]
                accumulated_text += text
                last_transcript_ts = time.time()

                # 完整句子结束时分析
                if is_end:
                    accumulated_text += "\n"
            except queue.Empty:
                pass

            # 每 ANALYSIS_INTERVAL 秒分析一次
            now = time.time()
            text_len = len(accumulated_text.strip())
            if text_len > 20 and (now - last_analysis) > ANALYSIS_INTERVAL:
                print(f"\n[分析] 处理 {text_len} 字符...")
                result = analyze_transcript(accumulated_text, API_KEY)

                if result:
                    clients = result.get("client_names", [])
                    topics = result.get("key_topics", [])
                    sentiment = result.get("sentiment", "neutral")
                    needs_c360 = result.get("needs_c360_lookup", False)

                    if clients:
                        print(f"[分析] 🏢 客户: {', '.join(clients)}")
                    if topics:
                        print(f"[分析] 📋 话题: {', '.join(topics[:5])}")
                    if sentiment != "neutral":
                        icon = "😊" if sentiment == "positive" else "😟"
                        print(f"[分析] {icon} 情绪: {sentiment}")

                    # C360 查询
                    if needs_c360 and clients:
                        for name in clients:
                            if name not in c360_cooldown or \
                               (now - c360_cooldown[name]) > C360_CHECK_COOLDOWN:
                                print(f"[C360] 🔍 查询 {name}...")
                                summary = lookup_customer(name)
                                c360_cooldown[name] = now
                                if summary:
                                    for s in summary:
                                        print(f"[C360]   {s}")
                                else:
                                    print(f"[C360]   无商机记录")

                accumulated_text = ""
                last_analysis = now

            # 空闲检测
            if now - last_transcript_ts > 30 and len(accumulated_text.strip()) < 5:
                accumulated_text = ""

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[退出] 正在停止...")

    finally:
        stop_event.set()
        asr.close()
        p.terminate()
        print("[退出] 已停止")


if __name__ == "__main__":
    main()
