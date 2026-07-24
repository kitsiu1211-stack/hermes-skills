#!/usr/bin/env python3
"""Group heartbeat: poll the Agent协作群 for new messages from known agents.

Stores last processed message_id in ~/.hermes/state/group_heartbeat.json.
Outputs new agent messages as JSON on stdout. Silent when nothing new.

USAGE:
  python3 group_heartbeat.py
  # Set in cron job: runs every 30s, no_agent=True mode
  # When script outputs data, cron delivers to user

ENV:
  FEISHU_APP_ID / FEISHU_APP_SECRET — for tenant_access_token
  Or FEISHU_APP_ACCESS_TOKEN — pre-obtained token
"""

import json
import os
import sys
import urllib.request

STATE_FILE = os.path.expanduser("~/.hermes/state/group_heartbeat.json")
GROUP_CHAT_ID = "oc_219a613c13292855c2dc4b80e59dfd6e"

# Agent filter: we care about replies from these agents
AGENT_APP_IDS = {
    "cli_9a31b280a1f3d101": "Aime 个人助理",
    "cli_a934e54959f99bd8": "马斯克",
}

MY_APP_ID = "cli_a964fd626078dcbc"
USER_OPEN_ID = "ou_dc055b0b5b0b5db2b1af5e79c0536db6"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_message_id": None, "last_create_time": "0"}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_token():
    """Get tenant access token from env or .env file."""
    token = os.environ.get("FEISHU_APP_ACCESS_TOKEN")
    if token:
        return token

    env_file = os.path.expanduser("~/.hermes/.env")
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if os.path.exists(env_file) and (not app_id or not app_secret):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("FEISHU_APP_ID="):
                    app_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("FEISHU_APP_SECRET="):
                    app_secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    if app_id and app_secret:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        return result.get("tenant_access_token")
    return None


def fetch_messages(token):
    url = (
        "https://open.feishu.cn/open-apis/im/v1/messages?"
        f"container_id_type=chat&container_id={GROUP_CHAT_ID}"
        "&sort_type=ByCreateTimeDesc&page_size=20"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def is_agent_message(msg):
    sender = msg.get("sender", {})
    sender_id = sender.get("id", "")
    if sender_id in (MY_APP_ID, USER_OPEN_ID, ""):
        return False
    if msg.get("msg_type") == "system":
        return False
    if sender_id in AGENT_APP_IDS:
        return True
    if sender.get("sender_type") == "app":
        return True
    return False


def extract_content(msg):
    msg_type = msg.get("msg_type", "")
    body = msg.get("body", {}).get("content", "{}")
    try:
        content = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return body
    if msg_type == "text":
        return content.get("text", "")
    if msg_type == "post":
        parts = content.get("content", [[]])
        text_parts = []
        for line in parts:
            for segment in line:
                if segment.get("tag") == "text":
                    text_parts.append(segment.get("text", ""))
                elif segment.get("tag") == "at":
                    text_parts.append(f"@{segment.get('user_name', '')}")
        return "".join(text_parts)
    if msg_type == "interactive":
        return "[交互卡片]"
    return f"[{msg_type}]"


def main():
    state = load_state()
    token = get_token()
    if not token:
        print("ERROR: Cannot get Feishu access token")
        sys.exit(1)

    result = fetch_messages(token)
    if result.get("code") != 0:
        print(f"ERROR: API error: {result}")
        sys.exit(1)

    items = result.get("data", {}).get("items", [])
    if not items:
        return

    last_id = state.get("last_message_id")
    last_time = int(state.get("last_create_time", "0"))
    new_agent_msgs = []

    for msg in items:
        msg_id = msg.get("message_id", "")
        create_time = int(msg.get("create_time", "0"))
        if msg_id == last_id or (last_time > 0 and create_time <= last_time):
            break
        if is_agent_message(msg):
            sender_id = msg.get("sender", {}).get("id", "")
            agent_name = AGENT_APP_IDS.get(sender_id, "Unknown Agent")
            new_agent_msgs.append({
                "agent": agent_name,
                "app_id": sender_id,
                "message_id": msg_id,
                "create_time": create_time,
                "content": extract_content(msg),
                "msg_type": msg.get("msg_type"),
                "parent_id": msg.get("parent_id"),
                "root_id": msg.get("root_id"),
                "mentions": msg.get("mentions", []),
            })

    if items:
        state["last_message_id"] = items[0].get("message_id")
        state["last_create_time"] = items[0].get("create_time", str(last_time))
    save_state(state)

    if new_agent_msgs:
        new_agent_msgs.reverse()
        print(json.dumps({
            "group": GROUP_CHAT_ID,
            "new_messages": new_agent_msgs,
            "count": len(new_agent_msgs),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
