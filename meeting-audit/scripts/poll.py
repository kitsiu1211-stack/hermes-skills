#!/usr/bin/env python3
"""
meeting_poll.py — 飞书会议增量事件轮询器

供 meeting-audit cronjob 使用。维护状态文件，每次只返回新事件。
用法：python3 meeting_poll.py <meeting_id>
输出：JSON 数组 [{event_type, items, ...}, ...]，无新事件时输出空数组 []

状态文件：~/.hermes/meeting_state/<meeting_id>.json
{
  "page_token": "...",
  "seen_events": ["event_id1", "event_id2", ...],
  "participant_left_meeting_end": false  // 是否检测到 leave_reason=2
}
"""

import json
import os
import subprocess
import sys

LARK_CLI = "/Users/bytedance/.npm-global/bin/lark-cli"
STATE_DIR = os.path.expanduser("~/.hermes/meeting_state")


def load_state(meeting_id):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{meeting_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"page_token": None, "seen_events": [], "participant_left_meeting_end": False}


def save_state(meeting_id, state):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{meeting_id}.json")
    with open(path, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_active(meeting_id):
    """检查用户是否还在会中"""
    try:
        r = subprocess.run(
            [LARK_CLI, "vc", "+meeting-list-active", "--as", "user"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        meetings = data.get("data", {}).get("meetings", [])
        return any(m["meeting_id"] == meeting_id for m in meetings)
    except Exception:
        return True  # 网络错误时假设还在会中，避免误判结束


def poll_events(meeting_id, page_token):
    """拉取事件，返回 (events_list, new_page_token)"""
    if " " in meeting_id:
        meeting_id = meeting_id.strip()
    if not meeting_id.isdigit():
        print(json.dumps({"error": f"Invalid meeting_id: {meeting_id}"}))
        sys.exit(2)

    cmd = [LARK_CLI, "vc", "+meeting-events", "--as", "user", "--meeting-id", meeting_id]
    if page_token:
        cmd += ["--page-token", page_token]
    else:
        cmd += ["--page-all"]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(r.stdout)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(2)

    if not data.get("ok"):
        code = data.get("code", "?")
        error_data = data.get("error", {})
        msg = error_data.get("message", data.get("msg", "?"))
        # 120002: switch disabled — 会议未开启智能体入会
        # 230002: permission denied — 用户不在会中
        # 120003: user is not in the meeting — 用户已离会/会议已结束
        if code in (120002, 230002):
            print(json.dumps({"error": f"code={code} msg={msg}"}))
            sys.exit(2)
        if code == 120003:
            # 用户已不在会中 → 返回空事件，让上层判断 meeting_ended
            return [], None
        print(json.dumps({"error": f"code={code} msg={msg}"}))
        sys.exit(2)

    events = data.get("data", {}).get("events", [])
    new_page_token = data.get("data", {}).get("page_token")

    return events, new_page_token


def extract_items(event):
    """从事件中提取可展示的数据项"""
    p = event.get("payload", event)  # 实际数据在 payload 下
    et = p.get("activity_event_type", "")

    if et == "transcript_received":
        items = []
        for item in p.get("transcript_received_items", []):
            items.append({
                "type": "transcript",
                "speaker": item.get("speaker", {}).get("user_name", "?"),
                "text": item.get("text", ""),
            })
        return items

    if et == "participant_joined":
        items = []
        for item in p.get("participant_joined_items", []):
            pp = item.get("participant", {})
            items.append({
                "type": "joined",
                "name": pp.get("user_name", "?"),
                "role": "主持人" if pp.get("user_role") == 2 else "参会人",
            })
        return items

    if et == "participant_left":
        items = []
        for item in p.get("participant_left_items", []):
            pp = item.get("participant", {})
            reason_code = item.get("leave_reason", 0)
            reason_map = {1: "主动离会", 2: "会议结束", 3: "被踢出"}
            items.append({
                "type": "left",
                "name": pp.get("user_name", "?"),
                "reason": reason_map.get(reason_code, "?"),
                "reason_code": reason_code,
            })
        return items

    if et == "chat_received":
        items = []
        for item in p.get("chat_received_items", []):
            items.append({
                "type": "chat",
                "sender": item.get("operator", {}).get("user_name", "?"),
                "content": item.get("content", ""),
            })
        return items

    return []  # 未知事件类型，跳过


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: meeting_poll.py <meeting_id>"}))
        sys.exit(2)

    meeting_id = sys.argv[1]
    state = load_state(meeting_id)

    # 检查是否还在会中
    still_active = check_active(meeting_id)

    if not still_active:
        # 会议已结束
        # 如果之前没检测到 meeting_end 事件，补充一条
        if not state.get("participant_left_meeting_end"):
            # 检查最后一次事件中是否已有 leave_reason=2
            events, pt = poll_events(meeting_id, state.get("page_token"))
            new_events = [e for e in events if e.get("event_id", "") not in state.get("seen_events", [])]
            has_end_event = False
            for e in new_events:
                items = extract_items(e)
                for item in items:
                    if item.get("reason_code") == 2:
                        has_end_event = True
                        break
                if has_end_event:
                    break

            if has_end_event:
                # 还有未处理的事件，更新状态后正常返回
                result = []
                for e in new_events:
                    items = extract_items(e)
                    if items:
                        result.append({"event_id": e.get("event_id", ""), "items": items})
                for e in new_events:
                    state["seen_events"].append(e.get("event_id", ""))
                state["page_token"] = pt
                state["participant_left_meeting_end"] = has_end_event
                save_state(meeting_id, state)
                print(json.dumps({"events": result, "meeting_ended": False}, ensure_ascii=False))
                return

        # 会议已结束且已处理完毕
        print(json.dumps({"events": [], "meeting_ended": True}, ensure_ascii=False))
        return

    # 拉取事件
    events, new_page_token = poll_events(meeting_id, state.get("page_token"))

    # 过滤已见事件
    new_events = [e for e in events if e.get("event_id", "") not in state.get("seen_events", [])]

    if not new_events:
        print(json.dumps({"events": [], "meeting_ended": False}, ensure_ascii=False))
        return

    # 提取并格式化
    result = []
    meeting_ended = False
    for e in new_events:
        items = extract_items(e)
        if items:
            result.append({"event_id": e.get("event_id", ""), "items": items})
        # 检查是否是会议结束事件
        for item in items:
            if item.get("reason_code") == 2:
                meeting_ended = True

    # 更新状态
    for e in new_events:
        state["seen_events"].append(e.get("event_id", ""))
    state["page_token"] = new_page_token
    if meeting_ended:
        state["participant_left_meeting_end"] = True
    # 裁剪 seen_events，最多保留 500 条
    if len(state.get("seen_events", [])) > 500:
        state["seen_events"] = state["seen_events"][-500:]

    save_state(meeting_id, state)

    output = {"events": result, "meeting_ended": meeting_ended}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
