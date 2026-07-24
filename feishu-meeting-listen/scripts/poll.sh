#!/bin/bash
# 飞书会议旁听轮询脚本 v3 — 全量拉取 + 去重，无 page_token 依赖
# 用法: bash poll.sh <meeting_id> [meeting_title]
# 每 10 秒用 --page-all 拉全量事件，Python 内存去重后写入 JSONL
# 检测到离会或 page_token 过期时自动退出
# 日志: ~/meeting_logs/<meeting_id>.jsonl

set -euo pipefail

MEETING_ID="${1:?Usage: bash poll.sh <meeting_id> [meeting_title]}"
MEETING_TITLE="${2:-未命名会议}"
LARK_CLI="/Users/bytedance/.npm-global/bin/lark-cli"
PYTHON3="/usr/bin/python3"
LOG_DIR="$HOME/meeting_logs"
LOG_FILE="${LOG_DIR}/${MEETING_ID}.jsonl"

mkdir -p "$LOG_DIR"

echo "=== 开始旁听: $MEETING_TITLE ==="
echo "会议ID: $MEETING_ID"
echo "日志: $LOG_FILE"

POLL_COUNT=0
while true; do
    sleep 10
    POLL_COUNT=$((POLL_COUNT + 1))

    # 全量拉取 — 不依赖 page_token，彻底避免过期问题
    EVENTS=$("$LARK_CLI" vc +meeting-events --as user \
        --meeting-id "$MEETING_ID" \
        --page-size 100 --page-all --format json 2>&1) || true

    # 检查是否离会
    if echo "$EVENTS" | grep -q "user is not in the meeting"; then
        echo "=== 用户已离会，旁听结束（共轮询 ${POLL_COUNT} 次） ==="
        echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
        break
    fi

    # 解析 + 去重 + 追加（全在 Python 一侧完成）
    "$PYTHON3" -c "
import sys, json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

events = data.get('data', {}).get('events', [])

# 从日志读取已见过的 sentence_id
seen = set()
try:
    with open('$LOG_FILE') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                sid = d.get('sentence_id')
                if sid:
                    seen.add(sid)
            except:
                pass
except FileNotFoundError:
    pass

new_lines = []
for e in events:
    p = e.get('payload', {})
    at = p.get('activity_event_type', '')
    if at == 'transcript_received':
        for item in p.get('transcript_received_items', []):
            sid = item.get('sentence_id', '')
            if sid in seen:
                continue
            seen.add(sid)
            new_lines.append(json.dumps({
                'type': 'transcript',
                'speaker': item.get('speaker', {}).get('user_name', '?'),
                'text': item.get('text', ''),
                'sentence_id': sid,
                'time': item.get('start_time_ms', ''),
            }, ensure_ascii=False))
    elif at == 'chat_received':
        for item in p.get('chat_received_items', []):
            new_lines.append(json.dumps({
                'type': 'chat',
                'speaker': item.get('operator', {}).get('user_name', '?'),
                'text': item.get('content', ''),
                'message_id': item.get('message_id', ''),
            }, ensure_ascii=False))
    elif at == 'participant_joined':
        for item in p.get('participant_joined_items', []):
            new_lines.append(json.dumps({
                'type': 'join',
                'speaker': item.get('participant', {}).get('user_name', '?'),
                'text': '入会',
                'time': item.get('join_time', ''),
            }, ensure_ascii=False))
    elif at == 'participant_left':
        for item in p.get('participant_left_items', []):
            lr = item.get('leave_reason', 0)
            reasons = {1: '主动离会', 2: '会议结束', 3: '被踢出'}
            new_lines.append(json.dumps({
                'type': 'leave',
                'speaker': item.get('participant', {}).get('user_name', '?'),
                'text': reasons.get(lr, str(lr)),
                'time': item.get('leave_time', ''),
            }, ensure_ascii=False))

if new_lines:
    with open('$LOG_FILE', 'a') as f:
        for line in new_lines:
            f.write(line + '\n')
" <<< "$EVENTS" 2>/dev/null
done

echo "日志已保存到: $LOG_FILE"
echo "=== 旁听脚本退出 ==="
