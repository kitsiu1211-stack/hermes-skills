#!/usr/bin/env python3
"""轻量会议字幕旁听——以用户身份轮询会议字幕和聊天事件。不入会，零 Bot 开销。"""
import subprocess, json, time

r = subprocess.run(["lark-cli", "vc", "+meeting-list-active", "--as", "user"], capture_output=True, text=True)
d = json.loads(r.stdout)
ms = d.get("data", {}).get("meetings", [])
if not ms:
    print("无活跃会议")
    exit(1)
meeting = ms[0]
meeting_id = meeting["meeting_id"]
print(f"旁听: {meeting['meeting_title']} ({meeting['meeting_no']})")

seen = set()
while True:
    try:
        r = subprocess.run(
            ["lark-cli", "vc", "+meeting-events", "--as", "user", "--meeting-id", meeting_id, "--page-all"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(r.stdout)
        events = data.get("data", {}).get("events", [])
        for e in events:
            eid = e.get("event_id", "")
            if eid in seen:
                continue
            seen.add(eid)
            t = e.get("event_type", "")
            if t == "transcript_received":
                items = e.get("payload", {}).get("transcript_items", [])
                for item in items:
                    speaker = item.get("speaker", {}).get("user_name", "?")
                    text = item.get("text", "")
                    if text.strip():
                        print(f"{speaker}: {text}")
            elif t == "chat_received":
                items = e.get("payload", {}).get("chat_received_items", [])
                for item in items:
                    sender = item.get("operator", {}).get("user_name", "?")
                    content = item.get("content", "")
                    if content.strip():
                        print(f"[弹幕] {sender}: {content}")
        time.sleep(4)
    except subprocess.TimeoutExpired:
        pass
    except KeyboardInterrupt:
        break
    except Exception as exc:
        print(f"[err] {exc}")
        time.sleep(4)
