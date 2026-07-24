#!/bin/bash
# 会议自动守护脚本（纯 bash，零 token 消耗）
# 每分钟运行一次，检测到用户入会则启动旁听
# 静默无输出 = 不在会议中，不触发 Agent

STATE_FILE="$HOME/meeting_logs/.active_monitors"
LOG_DIR="$HOME/meeting_logs"
POLL_SCRIPT="$HOME/.hermes/skills/feishu/feishu-meeting-listen/scripts/poll.sh"

mkdir -p "$LOG_DIR"
touch "$STATE_FILE"

# 1. 检查用户是否在会议中
meetings=$(lark-cli vc +meeting-list-active --as user --format json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('ok'):
    for m in d.get('data', {}).get('meetings', []):
        print(m['meeting_id'], m.get('meeting_title', ''))
")

if [ -z "$meetings" ]; then
    exit 0
fi

# 2. 逐个检查是否需要启动旁听
started=0
while IFS=' ' read -r mid mtitle; do
    [ -z "$mid" ] && continue
    
    if grep -q "^$mid:" "$STATE_FILE" 2>/dev/null; then
        continue
    fi
    
    echo "[$(date '+%H:%M:%S')] 检测到会议：$mtitle ($mid)，启动旁听"
    bash "$POLL_SCRIPT" "$mid" "$mtitle" &
    echo "$mid:$mtitle:$(date +%s)" >> "$STATE_FILE"
    started=1
done <<< "$meetings"

# 3. 清理已结束的会议记录
if [ -f "$STATE_FILE" ]; then
    while IFS=':' read -r mid mtitle _; do
        [ -z "$mid" ] && continue
        if ! pgrep -f "poll.sh $mid" > /dev/null 2>&1; then
            sed -i '' "/^$mid:/d" "$STATE_FILE" 2>/dev/null
        fi
    done < "$STATE_FILE"
fi

exit 0
