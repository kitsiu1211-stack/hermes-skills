#!/usr/bin/env python3
"""
会议旁听轮询脚本 — 在 execute_code 中运行。
拉取飞书会议字幕/聊天事件，实时推送到用户 Home 频道。
会议结束时自动停止并通知用户。

用法：在 execute_code 中粘贴此脚本，修改 MEETING_ID 即可。
"""

import subprocess, json, time

LARK_CLI = "/Users/bytedance/.npm-global/bin/lark-cli"
FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"

# === 修改这里 ===
MEETING_ID = "7658508485941284060"
# ==============

CHAT_ID = "oc_e2f79ec1614a1efe1ebcd7c679bb45a8"  # 用户 Home 频道

page_token = None
seen = set()

while True:
    # 1. 检查是否还在会中
    r = subprocess.run([LARK_CLI, "vc", "+meeting-list-active", "--as", "user"],
                       capture_output=True, text=True, timeout=10)
    try:
        active = json.loads(r.stdout)
        meetings = active.get("data", {}).get("meetings", [])
        still_in = any(m["meeting_id"] == MEETING_ID for m in meetings)
    except:
        still_in = True

    if not still_in:
        # 会议结束
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "🔴 会议已结束"}, "template": "red"},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "停止监听。会上提到的任务会在会后处理。"}}]
        }
        p = json.dumps({"params": {"receive_id_type": "chat_id"}, "data": {"receive_id": CHAT_ID, "msg_type": "interactive", "content": json.dumps(card, ensure_ascii=False)}})
        subprocess.run([FEISHU_CLI, "exec", "im.v1.message.create", "--params", p], timeout=10)
        break

    # 2. 拉取事件
    cmd = [LARK_CLI, "vc", "+meeting-events", "--as", "user", "--meeting-id", MEETING_ID]
    cmd += ["--page-token", page_token] if page_token else ["--page-all"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(r.stdout)
    except:
        time.sleep(5)
        continue

    if data.get("ok"):
        events = [e for e in data.get("data", {}).get("events", []) if e["event_id"] not in seen]
        lines = []
        for e in events:
            seen.add(e["event_id"])
            p = e.get("payload", e)
            et = p.get("activity_event_type", "")

            if et == "transcript_received":
                for item in p.get("transcript_received_items", []):
                    lines.append(f"💬 **{item['speaker'].get('user_name','?')}**: {item.get('text','')}")
            elif et == "participant_joined":
                for item in p.get("participant_joined_items", []):
                    pp = item["participant"]
                    role = "主持人" if pp.get("user_role") == 2 else "参会人"
                    lines.append(f"👤 {pp.get('user_name','?')} 加入（{role}）")
            elif et == "participant_left":
                for item in p.get("participant_left_items", []):
                    pp = item["participant"]
                    reason = {1: "主动离会", 2: "会议结束", 3: "被踢出"}.get(item.get("leave_reason", 0), "?")
                    lines.append(f"👤 {pp.get('user_name','?')} 离开（{reason}）")

        if lines:
            card = {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": "🎙️ 会议实时"}, "template": "blue"},
                "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}]
            }
            p = json.dumps({"params": {"receive_id_type": "chat_id"}, "data": {"receive_id": CHAT_ID, "msg_type": "interactive", "content": json.dumps(card, ensure_ascii=False)}})
            subprocess.run([FEISHU_CLI, "exec", "im.v1.message.create", "--params", p], timeout=10)

        page_token = data.get("data", {}).get("page_token")

    time.sleep(5)
