#!/usr/bin/env python3
"""
监听飞书 meeting_joined 事件，自动入会
配合 lark-cli event consume vc.meeting.participant_meeting_joined_v1 使用
用法: lark-cli event consume vc.meeting.participant_meeting_joined_v1 --as user | python3 auto_join_on_event.py
"""

from typing import Optional

import json, subprocess, os, sys, time
from pathlib import Path

PROJECT = Path.home() / "Documents/Codex_Project/feishu-voice-agent-starter"
VOICE_AGENT = PROJECT / "main.py"
LARK_CLI = "lark-cli"

def join_meeting(meeting_no: str):
    """启动浪子入会"""
    subprocess.Popen(
        [sys.executable, str(VOICE_AGENT), "--meeting-no", meeting_no],
        cwd=str(PROJECT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[auto-join] joined meeting {meeting_no}", flush=True)

def get_meeting_no(meeting_id: str) -> Optional[str]:
    """从会议 ID 拿到 9 位会议号"""
    try:
        r = subprocess.run(
            [LARK_CLI, "vc", "+meeting-list-active", "--as", "user"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        for m in data.get("data", {}).get("meetings", []):
            if m.get("meeting_id") == meeting_id:
                mn = m.get("meeting_number", "")
                if len(mn) >= 9:
                    return mn[-9:]
        return None
    except Exception as e:
        print(f"[auto-join] failed to get meeting_no: {e}", flush=True)
        return None

def main():
    print("[auto-join] listener started", flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("event", {}).get("type", "")
        if event_type != "vc.meeting.participant_meeting_joined_v1":
            continue

        meeting_id = event.get("event", {}).get("meeting_id", "")
        if not meeting_id:
            continue

        print(f"[auto-join] detected meeting_joined {meeting_id}", flush=True)
        time.sleep(2)  # 等会议就绪
        meeting_no = get_meeting_no(meeting_id)
        if meeting_no:
            join_meeting(meeting_no)
        else:
            print(f"[auto-join] could not resolve meeting_no for {meeting_id}", flush=True)

if __name__ == "__main__":
    main()
