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

# 预检：智能体入会开关是否关闭
PREFLIGHT=$("$LARK_CLI" vc +meeting-events --as user \
    --meeting-id "$MEETING_ID" \
    --page-size 1 --format json 2>&1) || true
if echo "$PREFLIGHT" | grep -q "switch for allowing agents"; then
    echo "=== 智能体入会开关已关闭，无法监听，退出 ==="
    exit 0
fi

POLL_COUNT=0
EMPTY_COUNT=0
END_CONFIRM=0
AS_FLAG="--as user"
while true; do
    sleep 10
    POLL_COUNT=$((POLL_COUNT + 1))

    # 全量拉取 — 不依赖 page_token，彻底避免过期问题
    EVENTS=$("$LARK_CLI" vc +meeting-events $AS_FLAG \
        --meeting-id "$MEETING_ID" \
        --page-size 100 --page-all --format json 2>&1) || true

    # 🚨 会议已结束的直接信号：API 返回 meeting has ended（最快检测，无需等确认轮）
    if echo "$EVENTS" | grep -q "meeting has ended"; then
        echo "=== 会议已结束（API 直接返回 meeting has ended，第 ${POLL_COUNT} 次轮询） ==="
        echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
        break
    fi

    # 检查是否离会 — 用户离会后切换为 bot 身份继续监听
    if echo "$EVENTS" | grep -q "user is not in the meeting"; then
        echo "=== 用户已离会，自动切换为 Bot 身份继续监听（第 ${POLL_COUNT} 次） ==="
        AS_FLAG="--as bot"
        continue
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
    EMPTY_COUNT=0
    with open('$LOG_FILE', 'a') as f:
        for line in new_lines:
            f.write(line + '\n')
else:
    EMPTY_COUNT=$((EMPTY_COUNT + 1))
" <<< "$EVENTS" 2>/dev/null

    # Bot 模式下检测会议是否已结束
    if [ "$AS_FLAG" = "--as bot" ]; then
        # 机制 1：连续 15 次无新事件（2.5 分钟）→ 退出（缩短：原 30 次/5 分钟）
        if [ $EMPTY_COUNT -ge 15 ]; then
            echo "=== 会议已结束（连续 ${EMPTY_COUNT} 次无新事件，共轮询 ${POLL_COUNT} 次） ==="
            echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
            break
        fi
        # 机制 2：每 6 轮（1 分钟）用 meeting-events 验证会议是否还在（status=ongoing）
        # 修复 2026-08-19：meeting-list-active --as bot 缺 --user-id 永远报 validation error → 误判会议结束
        if [ $((POLL_COUNT % 6)) -eq 0 ]; then
            ACTIVE=$("$LARK_CLI" vc +meeting-events --as bot --meeting-id "$MEETING_ID" --page-size 1 --format json 2>&1) || true
            if ! echo "$ACTIVE" | grep -q '"ongoing"'; then
                echo "=== 会议可能已结束（meeting-events 未返回 ongoing，第 ${POLL_COUNT} 次轮询，下一轮再确认） ==="
                END_CONFIRM=$((END_CONFIRM + 1))
                # 连续 2 次验证非 ongoing（约 2 分钟）才判定结束，避免偶发 API 异常误杀
                if [ $END_CONFIRM -ge 2 ]; then
                    echo "=== 会议已结束（meeting-events 验证: 连续 ${END_CONFIRM} 次非 ongoing，共轮询 ${POLL_COUNT} 次） ==="
                    echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
                    break
                fi
            else
                END_CONFIRM=0
            fi
        fi
    fi
done

echo "日志已保存到: $LOG_FILE"
echo "=== 旁听脚本退出 ==="
