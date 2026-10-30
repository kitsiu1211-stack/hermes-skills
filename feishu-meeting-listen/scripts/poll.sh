#!/bin/bash
# 飞书会议旁听轮询脚本 v3 — 全量拉取 + 去重，无 page_token 依赖
# 用法: bash poll.sh <meeting_id> [meeting_title] [bot]
#   · 第 3 参数传 bot（或 START_AS=bot）→ 从一开始就用 --as bot（Bot 单独入会、用户不在会的场景）
#   · EMPTY_EXIT_ROUNDS 环境变量可调「连续无新事件退出阈值」（默认 15，设 0 = 关闭该机制）
# 每 10 秒用 --page-all 拉全量事件，Python 内存去重后写入 JSONL
# 检测到离会或 page_token 过期时自动退出
# 日志: ~/meeting_logs/<meeting_id>.jsonl

set -euo pipefail

MEETING_ID="${1:?Usage: bash poll.sh <meeting_id> [meeting_title] [bot]}"
MEETING_TITLE="${2:-未命名会议}"
LARK_CLI="/Users/bytedance/.npm-global/bin/lark-cli"
PYTHON3="/usr/bin/python3"
LOG_DIR="$HOME/meeting_logs"
LOG_FILE="${LOG_DIR}/${MEETING_ID}.jsonl"

mkdir -p "$LOG_DIR"

echo "=== 开始旁听: $MEETING_TITLE ==="
echo "会议ID: $MEETING_ID"
echo "日志: $LOG_FILE"

AS_FLAG="--as user"
if [ "${3:-}" = "bot" ] || [ "${START_AS:-}" = "bot" ]; then
    AS_FLAG="--as bot"
    echo "=== 以 Bot 身份启动轮询（Bot 单独入会模式） ==="
fi

# 预检：智能体入会开关是否关闭
PREFLIGHT=$("$LARK_CLI" vc +meeting-events $AS_FLAG \
    --meeting-id "$MEETING_ID" \
    --page-size 1 --format json 2>&1) || true
if echo "$PREFLIGHT" | grep -q "switch for allowing agents"; then
    echo "=== 智能体入会开关已关闭，无法监听，退出 ==="
    exit 0
fi
if echo "$PREFLIGHT" | grep -q "bot is not in the meeting"; then
    echo "=== Bot 尚未入会（需先 +meeting-join --as bot），退出 ==="
    exit 0
fi

POLL_COUNT=0
EMPTY_COUNT=0
BOT_GONE=0
END_CONFIRM=0

# ---- 会议雷达（主动预警）2026-10-14 --------------------------------------
# 零token规则 + 小模型增量扫描；发现冲突/异常/需求/我方失手 → 立即私聊推给用户。
# ⚠️ 2026-10-26 起默认关闭（用户反馈噪音大、帮助有限）。需要时显式 RADAR_ENABLE=1 手动开。
# RADAR_ENABLE=1 开启；RADAR_CHAT 指定接收私聊；RADAR_LLM_EVERY=0 关闭模型层。
if [ "${RADAR_ENABLE:-0}" = "1" ] && [ -f "$HOME/.hermes/skills/feishu/feishu-meeting-listen/scripts/meeting_radar.py" ]; then
    RADAR_ARGS=("$MEETING_ID" --title "$MEETING_TITLE" --interval 15)
    [ -n "${RADAR_CHAT:-}" ] && RADAR_ARGS+=(--chat-id "$RADAR_CHAT")
    [ -n "${RADAR_LLM_EVERY:-}" ] && RADAR_ARGS+=(--llm-every "$RADAR_LLM_EVERY")
    nohup "$PYTHON3" "$HOME/.hermes/skills/feishu/feishu-meeting-listen/scripts/meeting_radar.py" \
        "${RADAR_ARGS[@]}" >> "$LOG_DIR/${MEETING_ID}.radar.log" 2>&1 &
    disown
    echo "=== 会议雷达已启动（会中主动预警 → 私聊） ==="
fi

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

    # 🚨 2026-10-13 补充：会议结束后 API 实际返回的是 {"status": "ended", "end_time": "..."}，
    # 并没有 "meeting has ended" 字样 → 旧逻辑识别不到，Bot 模式下会留下僵尸轮询进程
    # （实测：心玥交接沟通群 3 分钟会结束后进程仍在跑）。这里直接认 status=ended。
    if echo "$EVENTS" | grep -q '\"status\": *\"ended\"'; then
        echo "=== 会议已结束（API 返回 status=ended，第 ${POLL_COUNT} 次轮询） ==="
        echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
        break
    fi

    # 🚨 2026-10-14 修复（僵尸进程）：Bot 模式下会议结束后，meeting-events --as bot
    # 返回的是 {"ok": false, "code": 120004, "msg": "bot is not in the meeting"} ——
    # 既没有 "status: ended"，也没有 "ok": true，两条既有检测都不命中；而机制 1
    # （EMPTY_EXIT_ROUNDS）因计数器在子进程里递增、父进程永不累加而事实上失效
    # → 会议结束后僵尸进程无限空转（实测：豆包工作办公agent沟通结束后空转 324 轮）。
    # 现在：连续 2 轮确认 "bot is not in the meeting" 即判定会议结束并退出。
    if [ "$AS_FLAG" = "--as bot" ] && echo "$EVENTS" | grep -q "bot is not in the meeting"; then
        BOT_GONE=$((BOT_GONE + 1))
        echo "=== 结束信号：Bot 已不在会中（第 ${POLL_COUNT} 次轮询，确认 ${BOT_GONE}/2） ==="
        if [ $BOT_GONE -ge 2 ]; then
            echo "=== 会议已结束（连续 ${BOT_GONE} 轮 bot is not in the meeting，共轮询 ${POLL_COUNT} 次） ==="
            echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
            break
        fi
        continue
    fi
    BOT_GONE=0

    # 检查是否离会 — 用户离会后切换为 bot 身份继续监听（仅当 Bot 真的在会里）
    # 2026-10-12 修复：静默旁听（--as user，Bot 未入会）时，用户离会后原逻辑切到 --as bot →
    # 后续每轮返回 "bot is not in the meeting" 且不匹配任何退出条件 → 僵尸进程无限空转。
    if echo "$EVENTS" | grep -q "user is not in the meeting"; then
        BOT_PROBE=$("$LARK_CLI" vc +meeting-events --as bot --meeting-id "$MEETING_ID" --page-size 1 --format json 2>&1) || true
        if echo "$BOT_PROBE" | grep -q "bot is not in the meeting"; then
            echo "=== 用户已离会且 Bot 未入会，退出（静默旁听模式，共轮询 ${POLL_COUNT} 次） ==="
            echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
            break
        fi
        echo "=== 用户已离会，自动切换为 Bot 身份继续监听（第 ${POLL_COUNT} 次） ==="
        AS_FLAG="--as bot"
        continue
    fi

    # 解析 + 去重 + 追加（全在 Python 一侧完成）
    # 🚨 2026-10-14 修复：原版在 Python 代码里写 `EMPTY_COUNT=$((EMPTY_COUNT + 1))`，
    # 但那是在 `python3 -c "..."` 的子进程里执行 —— 父 shell 的 EMPTY_COUNT 永不累加，
    # 机制 1（EMPTY_EXIT_ROUNDS）事实上失效。现在让 Python 只打印 NEW/EMPTY 标记，
    # 计数与判定全部回到父 shell。
    NEW_MARK=$("$PYTHON3" -c "
import sys, json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

events = data.get('data', {}).get('events', [])

# 从日志读取已见过的 sentence_id（字幕）+ 已见过的 chat/join/leave 事件键
seen = set()
seen_ev = set()
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
                t = d.get('type')
                if t == 'chat':
                    seen_ev.add(('chat', d.get('speaker'), d.get('text'), d.get('message_id', '')))
                elif t in ('join', 'leave'):
                    seen_ev.add((t, d.get('speaker'), d.get('time')))
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
            key = ('chat', item.get('operator', {}).get('user_name', '?'), item.get('content', ''), item.get('message_id', ''))
            if key in seen_ev:
                continue
            seen_ev.add(key)
            new_lines.append(json.dumps({
                'type': 'chat',
                'speaker': item.get('operator', {}).get('user_name', '?'),
                'text': item.get('content', ''),
                'message_id': item.get('message_id', ''),
            }, ensure_ascii=False))
    elif at == 'participant_joined':
        for item in p.get('participant_joined_items', []):
            key = ('join', item.get('participant', {}).get('user_name', '?'), item.get('join_time', ''))
            if key in seen_ev:
                continue
            seen_ev.add(key)
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
            key = ('leave', item.get('participant', {}).get('user_name', '?'), item.get('leave_time', ''))
            if key in seen_ev:
                continue
            seen_ev.add(key)
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
    print('NEW')
else:
    print('EMPTY')
" <<< "$EVENTS" 2>/dev/null)

    if [ "$NEW_MARK" = "NEW" ]; then
        EMPTY_COUNT=0
    else
        EMPTY_COUNT=$((EMPTY_COUNT + 1))
    fi

    # 🚨 2026-10-14 加固：leave_reason=2 是飞书官方的「会议结束」信号（会议散会时对
    # 所有参会人推送一次），比「bot 已不在会」更早、更权威，且 --as user / --as bot
    # 两种身份都能看到。实测睿魔会议 16:16:48 就落了这条事件，但当时脚本不认识它，
    # 一直空转到 17:00。放在解析写盘之后判定，避免丢掉同一轮返回的最后几句字幕。
    if echo "$EVENTS" | grep -Eq '"leave_reason":[[:space:]]*"?2[",}]'; then
        echo "=== 会议已结束（检测到 leave_reason=2 会议结束事件，第 ${POLL_COUNT} 次轮询） ==="
        echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
        break
    fi

    # Bot 模式下检测会议是否已结束
    if [ "$AS_FLAG" = "--as bot" ]; then
        # 机制 1：连续 N 次无新事件（默认 15 次 / 2.5 分钟）→ 退出
        # 🚨 长活动/演示型会议静默期常超 2.5 分钟，可用 EMPTY_EXIT_ROUNDS 调大，设 0 = 关闭本机制（只靠机制 2 兜底）
        EMPTY_LIMIT="${EMPTY_EXIT_ROUNDS:-15}"
        if [ "$EMPTY_LIMIT" != "0" ] && [ $EMPTY_COUNT -ge "$EMPTY_LIMIT" ]; then
            echo "=== 会议已结束（连续 ${EMPTY_COUNT} 次无新事件，共轮询 ${POLL_COUNT} 次） ==="
            echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
            break
        fi
        # 机制 2：每 6 轮（1 分钟）用 meeting-events 验证会议是否还在（status=ongoing）
        # 修复 2026-08-19：meeting-list-active --as bot 缺 --user-id 永远报 validation error → 误判会议结束
        if [ $((POLL_COUNT % 6)) -eq 0 ]; then
            ACTIVE=$("$LARK_CLI" vc +meeting-events --as bot --meeting-id "$MEETING_ID" --page-size 1 --format json 2>&1) || true
            # 🚨 2026-10-13 修复误杀：原逻辑「响应里没有 ongoing 就算结束」会把
            # 探测失败（99991400 频率限制 / 超时 / 空响应）误判成会议结束 →
            # 豆包有约第 9 期实测 12 轮（2 分钟）即被误杀，会议其实还在进行。
            # 现在只在「API 明确返回 ok:true 且状态非 ongoing」时才计数，
            # 探测失败（无 ok:true）一律视为「未知」，不累加、继续轮询。
            if echo "$ACTIVE" | grep -q '"ongoing"'; then
                END_CONFIRM=0
            elif echo "$ACTIVE" | grep -q '"ok": *true'; then
                echo "=== 会议可能已结束（meeting-events 明确返回非 ongoing，第 ${POLL_COUNT} 次轮询，下一轮再确认） ==="
                END_CONFIRM=$((END_CONFIRM + 1))
                # 连续 2 次验证非 ongoing（约 2 分钟）才判定结束，避免偶发 API 异常误杀
                if [ $END_CONFIRM -ge 2 ]; then
                    echo "=== 会议已结束（meeting-events 验证: 连续 ${END_CONFIRM} 次非 ongoing，共轮询 ${POLL_COUNT} 次） ==="
                    echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(date '+%H:%M:%S')\"}" >> "$LOG_FILE"
                    break
                fi
            else
                echo "=== 结束探测失败（限流/超时/空响应），本轮不判定结束，继续轮询（第 ${POLL_COUNT} 次） ==="
            fi
        fi
    fi
done

echo "日志已保存到: $LOG_FILE"
echo "=== 旁听脚本退出 ==="
