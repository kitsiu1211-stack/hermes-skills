#!/usr/bin/env python3
"""
Meeting Chat Reply Monitor — V2 (LLM 即时回复)
实时监听 poll.sh 的 JSONL，检测"浪子"关键词 → DeepSeek LLM 即时回复 → fallback 模板
用法: python3 meeting_chat_reply.py <meeting_id>
"""

import sys
import json
import os
import subprocess
import time
import re
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── 配置 ──
MEETING_ID = sys.argv[1]
LOG_DIR = os.path.expanduser("~/meeting_logs")
LOG_FILE = os.path.join(LOG_DIR, f"{MEETING_ID}.jsonl")
REPLIED_FILE = os.path.join(LOG_DIR, f"{MEETING_ID}.chat_replied.txt")
LARK_CLI = os.path.expanduser("~/.npm-global/bin/lark-cli")

# ── DeepSeek API ──
def _load_api_key():
    """从 ~/.hermes/.env 读取 DEEPSEEK_API_KEY"""
    env_path = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env_path):
        return None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

DEEPSEEK_KEY = _load_api_key()
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
LLM_MODEL = "deepseek-chat"  # 轻量够快
LLM_TIMEOUT = 5  # API 超时（秒）

# ── LLM 回复生成 ──
SYSTEM_PROMPT = """你是"浪子"，一个在飞书会议中旁听的 AI 助手。参会者会在会议聊天框里 @ 你提问。

回复规则：
- 用中文，口语化，像真人聊天
- 简短精炼，控制在 2-3 句话以内（会议聊天框不比群聊，别长篇大论）
- 如果问题是你能回答的，直接回答
- 如果你不确定或不知道，诚实说"这个我不确定，会后帮你查"
- 如果只是打招呼（"浪子" "浪子在吗"），友好回应
- 不要用 markdown，纯文本"""

def generate_reply(speaker: str, text: str) -> str | None:
    """调用 DeepSeek API 生成回复，失败返回 None"""
    if not DEEPSEEK_KEY:
        return None

    # 去掉"浪子"前缀，保留问题核心
    question = text.replace("浪子", "").strip().strip("@").strip("，,。.").strip()
    if not question:
        question = "在吗"

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{speaker} 在会议聊天框里说：{question}"},
        ],
        "max_tokens": 150,
        "temperature": 0.7,
        "stream": False,
    }).encode("utf-8")

    req = Request(DEEPSEEK_URL, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_KEY}")

    try:
        resp = urlopen(req, timeout=LLM_TIMEOUT)
        body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"].strip()
        # 去掉可能的 markdown 标记
        content = re.sub(r"\*\*|__|`|#+\s?", "", content)
        return content
    except Exception as e:
        print(f"[chat_reply] ⚠️ LLM 调用失败: {e}", flush=True)
        return None

def fallback_reply(speaker: str, text: str) -> str:
    """模板 fallback，LLM 不可用时使用"""
    question = text.replace("浪子", "").strip().strip("@").strip("，,。.")
    if not question or question in ("在吗", "在不在", "hi", "hello", "嗨"):
        return f"在的 @{speaker}！有什么需要帮忙的？👋"
    return f"收到 @{speaker}，浪子正在处理中 🙋"

# ── 发送消息到会议聊天框 ──
def send_meeting_msg(text: str) -> bool:
    """发送消息到会议聊天框，返回是否成功"""
    try:
        result = subprocess.run(
            [
                LARK_CLI, "vc", "+meeting-message-send",
                "--meeting-id", MEETING_ID,
                "--msg-type", "text",
                "--text", text,
                "--as", "user",
            ],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[chat_reply] ❌ 发送异常: {e}", flush=True)
        return False

# ── 主循环 ──
def main():
    replied = set()
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE) as f:
            replied = {line.strip() for line in f if line.strip()}

    last_pos = os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0

    print(f"[chat_reply] V2 启动 (LLM={'✓' if DEEPSEEK_KEY else '✗ fallback'})", flush=True)
    print(f"[chat_reply] meeting_id={MEETING_ID}", flush=True)
    print(f"[chat_reply] 已回复记录: {len(replied)} 条", flush=True)

    while True:
        time.sleep(3)

        if not os.path.exists(LOG_FILE):
            for _ in range(10):
                time.sleep(3)
                if os.path.exists(LOG_FILE):
                    break
            else:
                print("[chat_reply] 日志文件消失，退出监控", flush=True)
                break

        current_size = os.path.getsize(LOG_FILE)
        if current_size <= last_pos:
            continue

        try:
            with open(LOG_FILE) as f:
                f.seek(last_pos)
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if entry.get("type") != "chat":
                        continue

                    text = entry.get("text", "")
                    if "浪子" not in text:
                        continue

                    message_id = entry.get("message_id", "")
                    if not message_id or message_id in replied:
                        continue

                    speaker = entry.get("speaker", "?")

                    # ── 生成回复（LLM 优先，fallback 兜底）──
                    reply = generate_reply(speaker, text)
                    if reply is None:
                        reply = fallback_reply(speaker, text)

                    print(f"[chat_reply] {speaker}: \"{text[:60]}...\"", flush=True)
                    print(f"[chat_reply] → {reply}", flush=True)

                    if send_meeting_msg(reply):
                        print(f"[chat_reply] ✅ 已发送", flush=True)
                    else:
                        print(f"[chat_reply] ❌ 发送失败", flush=True)

                    # 标记已回复
                    replied.add(message_id)
                    with open(REPLIED_FILE, "a") as f2:
                        f2.write(f"{message_id}\n")

        except Exception as e:
            print(f"[chat_reply] ⚠️ 读取异常: {e}", flush=True)

        last_pos = current_size

if __name__ == "__main__":
    main()
