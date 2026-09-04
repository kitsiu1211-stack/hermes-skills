#!/usr/bin/env python3
"""doc_mention_watcher.py — 监听飞书文档 @ 提及，自动回复
由 Hermes cron 周期性触发，轮询已注册的文档列表，检测新评论中的 @Mark 42-浪子
"""

import json, os, sys, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# === 配置 ===
STATE_FILE = Path.home() / ".hermes" / "doc_mention_state.json"
WATCHED_DOCS = [
    "WCkhdGFCroIvazxcVtDcntzjnpe",  # 飞书AI商业化作战地图
]
MENTION_PATTERNS = ["Mark 42-浪子", "浪子", "mark-42", "Mark 42"]

# === 获取 Token ===
def get_token():
    """从 lark-cli 获取 user access token"""
    import subprocess
    r = subprocess.run(
        ["lark-cli", "auth", "+token", "--as", "user"],
        capture_output=True, text=True, timeout=10
    )
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None

# === 拉取评论 ===
def list_comments(doc_token, token):
    url = f"https://open.feishu.cn/open-apis/drive/v1/files/{doc_token}/comments?file_type=docx&page_size=50&is_whole=true"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urlopen(req)
        data = json.loads(resp.read())
        return data.get("data", {}).get("items", [])
    except HTTPError as e:
        err = e.read().decode()
        print(f"API error for {doc_token}: {err[:200]}", file=sys.stderr)
        return []

# === 检测新 @ 提及 ===
def check_mentions():
    token = get_token()
    if not token:
        print("Failed to get token", file=sys.stderr)
        return []

    # 加载状态
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())

    new_mentions = []

    for doc in WATCHED_DOCS:
        comments = list_comments(doc, token)
        seen_ids = set(state.get(doc, []))

        for c in comments:
            cid = c.get("comment_id", "")
            if cid in seen_ids:
                continue

            content = c.get("content", "")
            for pattern in MENTION_PATTERNS:
                if pattern in content:
                    new_mentions.append({
                        "doc_token": doc,
                        "comment_id": cid,
                        "content": content,
                        "pattern": pattern,
                    })
                    break

        # 更新状态
        state[doc] = [c.get("comment_id", "") for c in comments]

    STATE_FILE.write_text(json.dumps(state, indent=2))
    return new_mentions


# === 回复评论 ===
def reply_comment(doc_token, comment_id, text, token):
    url = f"https://open.feishu.cn/open-apis/drive/v1/files/{doc_token}/comments/{comment_id}/replies"
    body = json.dumps({"content": text, "file_type": "docx"}).encode()
    req = Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        resp = urlopen(req)
        data = json.loads(resp.read())
        return data.get("code") == 0
    except HTTPError as e:
        print(f"Reply error: {e.read().decode()[:200]}", file=sys.stderr)
        return False


# === 主流程 ===
if __name__ == "__main__":
    mentions = check_mentions()
    if not mentions:
        sys.exit(0)

    print(f"Found {len(mentions)} new mention(s)")
    for m in mentions:
        print(f"  [{m['comment_id'][:8]}...] {m['content'][:100]}")

    # 输出到 stdout，让 cron 的 agent 收到后自动处理
    for m in mentions:
        print(f"\n[MENTION] doc={m['doc_token']} cid={m['comment_id']}")
        print(f"  Content: {m['content']}")
