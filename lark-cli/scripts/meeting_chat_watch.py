#!/usr/bin/env python3
"""Watch a Feishu meeting's chat for wake-word mentions (bot mode).

Polls `lark-cli vc +meeting-events --as bot` and prints each new
`chat_received` item as one JSON line, flagging whether it contains a wake
word. Dedupes by event_id via a state file, so re-running is safe.

Designed for the "voice pipeline unavailable" degradation path: when
`/vc/v1/realtime/endpoint` returns 121005 the bot cannot speak, so it
answers in the meeting chat box instead (pitfall 28).

Usage:
    python3 meeting_chat_watch.py <meeting_id>

Output (one JSON per line):
    {"ts": 1794279201.78, "sender": "袁鑫杰", "content": "浪子,打个招呼", "wake": true}
    {"ts": 1794279300.00, "meeting_status": "ended"}

Exits 0 when the meeting status is no longer "ongoing".
"""
import json
import subprocess
import sys
import time
from pathlib import Path

LARK_CLI = "/Users/bytedance/.npm-global/bin/lark-cli"
WAKE_WORDS = ("浪子", "小浪")
STATE_DIR = Path.home() / ".hermes" / "meeting_chat_state"


def load_seen(path: Path) -> set:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()))
    except Exception:
        return set()


def save_seen(path: Path, ids: set) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids)))


def fetch(meeting_id: str) -> dict:
    proc = subprocess.run(
        [LARK_CLI, "vc", "+meeting-events", "--as", "bot",
         "--meeting-id", meeting_id, "--page-all", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    raw = proc.stdout or ""
    start = raw.find("{")
    if start < 0:
        return {}
    try:
        return json.loads(raw[start:])
    except json.JSONDecodeError:
        return {}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: meeting_chat_watch.py <meeting_id>", file=sys.stderr)
        return 2

    meeting_id = sys.argv[1]
    state_path = STATE_DIR / f"{meeting_id}.json"
    known = load_seen(state_path)

    while True:
        try:
            data = fetch(meeting_id)
            payload = data.get("data", {}) or {}
            status = (payload.get("meeting") or {}).get("status", "")

            for event in payload.get("events") or []:
                if event.get("event_type") != "chat_received":
                    continue
                event_id = event.get("event_id", "")
                if event_id in known:
                    continue
                known.add(event_id)
                for item in (event.get("payload") or {}).get("chat_received_items", []):
                    content = (item.get("content") or "").strip()
                    if not content:
                        continue
                    # Skip system placeholders (typing indicator) and non-text items.
                    if item.get("message_type") != 1 or content == "Typing":
                        continue
                    sender = (item.get("operator") or {}).get("user_name", "?")
                    print(json.dumps({
                        "ts": time.time(),
                        "sender": sender,
                        "content": content,
                        "wake": any(w in content for w in WAKE_WORDS),
                    }, ensure_ascii=False), flush=True)

            save_seen(state_path, known)

            if status and status != "ongoing":
                print(json.dumps({"ts": time.time(), "meeting_status": status},
                                 ensure_ascii=False), flush=True)
                return 0
        except Exception as exc:
            print(json.dumps({"ts": time.time(), "error": str(exc)[:120]},
                             ensure_ascii=False), flush=True)

        time.sleep(6)


if __name__ == "__main__":
    sys.exit(main())
