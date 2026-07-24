#!/bin/bash
# ── poll.sh v4 ── 会议旁听 v4：自动检测 + 会前点名 + 实时告警 + C360 查客户
# 用法: bash poll.sh                        # 自动检测入会
#       bash poll.sh <meeting_id> [title]    # 手动指定会议

set -uo pipefail
# 注：不使用 set -e，run_poll 内部 API 错误不应杀死守护进程

LARK_CLI="${LARK_CLI:-/Users/bytedance/.npm-global/bin/lark-cli}"
PYTHON3="${PYTHON3:-/usr/bin/python3}"
LOG_DIR="$HOME/meeting_logs"
mkdir -p "$LOG_DIR"

# ── 配置 ──
ALERT_CHAT="oc_219a613c13292855c2dc4b80e59dfd6e"  # 告警群
ALERT_ENABLED=true                                   # 是否发送实时告警
C360_ENABLED=false                                   # C360 CLI 当前不可用
POLL_INTERVAL=10                                     # 轮询间隔

# ── 工具函数 ──
ts() { date '+%H:%M:%S'; }
log() { echo "[$(ts)] $*" >&2; }

send_alert() {
  local text="$1"
  [ "$ALERT_ENABLED" != "true" ] && return
  lark-cli im +messages-send --chat-id "$ALERT_CHAT" --msg-type text --as bot \
    --content "{\"text\":\"$text\"}" 2>/dev/null || true
}

# ── 客户名列表（从 client_list.json 动态加载）──
KNOWN_CLIENTS=()
_load_clients() {
  if [ -f "$HOME/.hermes/data/client_list.json" ]; then
    while IFS= read -r name; do
      [ -n "$name" ] && KNOWN_CLIENTS+=("$name")
    done < <(python3 -c "
import json
with open('$HOME/.hermes/data/client_list.json') as f:
    d = json.load(f)
    clients = d.get('clients', [])
    for c in clients:
        name = c.get('name', c) if isinstance(c, dict) else c
        # 提取简称（公司名中去掉「有限公司」「股份」等后缀）
        short = name.replace('有限公司','').replace('股份有限公司','').replace('责任公司','').replace('（','').replace('）','').strip()
        print(name)
        if short != name:
            print(short)
        # 提取前2-4字作为简称补充
        parts = short.split('科技')
        if parts[0].strip() and parts[0].strip() != short:
            print(parts[0].strip())
" 2>/dev/null)
  fi
  # 兜底
  [ ${#KNOWN_CLIENTS[@]} -eq 0 ] && KNOWN_CLIENTS=("拓竹" "和生" "疆海" "安克")
}
_load_clients

# ── C360 查客户（预留接口）──
c360_lookup() {
  local name="$1"
  if [ "$C360_ENABLED" != "true" ]; then
    echo "C360: 不可用（CLI 未安装）"
    return
  fi
  # TODO: 接入真实 C360 CLI
  lark-cli c360 opportunity list --keyword "$name" --format json 2>/dev/null || echo "C360: 查询失败"
}

# ── 会前点名 ──
do_rollcall() {
  local meeting_id="$1" meeting_title="$2"
  log "ROLLCALL: $meeting_title ($meeting_id)"

  local events
  events=$("$LARK_CLI" vc +meeting-events --as user --meeting-id "$meeting_id" \
    --page-all --format json 2>/dev/null || echo "{}")

  local participants
  participants=$(echo "$events" | "$PYTHON3" -c "
import sys,json
try:
    d=json.load(sys.stdin)
    evs=d.get('data',{}).get('events',[])
    names=set()
    for e in evs:
        p=e.get('payload',{})
        at=p.get('activity_event_type','')
        if at=='participant_joined':
            for item in p.get('participant_joined_items',[]):
                names.add(item.get('participant',{}).get('user_name','?'))
    for n in sorted(names):
        print(f'  👤 {n}')
    print(f'TOTAL: {len(names)}人已入会')
except: print('解析失败')
" 2>/dev/null)

  local msg="【📹 会议已入会】${meeting_title}
会议号: ${meeting_id}
时间: $(ts)

点名:
${participants:-  获取中...}"

  log "$msg"
  send_alert "$msg"
}

# ── 客户名检测 ──
check_client_mention() {
  local text="$1" meeting_id="$2"
  for client in "${KNOWN_CLIENTS[@]}"; do
    if echo "$text" | grep -q "$client"; then
      log "CLIENT MENTION: $client"
      local c360_info
      c360_info=$(c360_lookup "$client" 2>/dev/null | head -5)
      local alert="【🔔 客户提及】「${client}」($(ts))
会议: ${meeting_id}
原文: ...${text}...
C360: ${c360_info:-暂无数据}"
      send_alert "$alert"
      return
    fi
  done
}

# ── 关键词检测 ──
check_keywords() {
  local text="$1" meeting_id="$2"
  local keywords=("预算" "价格" "报价" "todo" "下一步" "待办" "action" "决策" "确认")
  for kw in "${keywords[@]}"; do
    if echo "$text" | grep -qi "$kw"; then
      log "KEYWORD: $kw → $text"
      send_alert "【🔑 关键词】「${kw}」( $(ts) )
会议: ${meeting_id}
原文: ...${text}..."
      break
    fi
  done
}

# ── 核心轮询 ──
run_poll() {
  local meeting_id="$1" meeting_title="$2"
  local log_file="${LOG_DIR}/${meeting_id}.jsonl"
  local poll_count=0

  log "START: $meeting_title ($meeting_id) → $log_file"
  send_alert "【🎙 开始旁听】${meeting_title}"

  while true; do
    sleep "$POLL_INTERVAL"
    poll_count=$((poll_count + 1))

    local events
    events=$("$LARK_CLI" vc +meeting-events --as user --meeting-id "$meeting_id" \
      --page-size 100 --page-all --format json 2>&1) || true

    if echo "$events" | grep -q "user is not in the meeting"; then
      log "END: 用户离会（共 ${poll_count} 次轮询）"
      echo "{\"type\":\"meta\",\"event\":\"meeting_ended\",\"time\":\"$(ts)\"}" >> "$log_file"
      send_alert "【🔚 会议结束】${meeting_title}（${poll_count}次轮询）
日志: ${log_file}"
      return 0
    fi

    # 解析 + 去重 + 实时告警
    "$PYTHON3" -c "
import sys, json

try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

evs = data.get('data', {}).get('events', [])

seen = set()
try:
    with open('$log_file') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                sid = d.get('sentence_id')
                if sid: seen.add(sid)
            except: pass
except FileNotFoundError:
    pass

new_lines = []
alerts = []

for e in evs:
    p = e.get('payload', {})
    at = p.get('activity_event_type', '')
    if at == 'transcript_received':
        for item in p.get('transcript_received_items', []):
            sid = item.get('sentence_id', '')
            if sid in seen: continue
            seen.add(sid)
            speaker = item.get('speaker', {}).get('user_name', '?')
            text = item.get('text', '')
            new_lines.append(json.dumps({
                'type': 'transcript', 'speaker': speaker,
                'text': text, 'sentence_id': sid,
                'time': item.get('start_time_ms', ''),
            }, ensure_ascii=False))
            alerts.append({'type': 'transcript', 'speaker': speaker, 'text': text})
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
            nm = item.get('participant', {}).get('user_name', '?')
            new_lines.append(json.dumps({
                'type': 'join', 'speaker': nm, 'text': '入会',
                'time': item.get('join_time', ''),
            }, ensure_ascii=False))
            alerts.append({'type': 'join', 'speaker': nm, 'text': '入会'})
    elif at == 'participant_left':
        for item in p.get('participant_left_items', []):
            nm = item.get('participant', {}).get('user_name', '?')
            lr = item.get('leave_reason', 0)
            reasons = {1: '主动离会', 2: '会议结束', 3: '被踢出'}
            new_lines.append(json.dumps({
                'type': 'leave', 'speaker': nm,
                'text': reasons.get(lr, str(lr)),
                'time': item.get('leave_time', ''),
            }, ensure_ascii=False))

if new_lines:
    with open('$log_file', 'a') as f:
        for line in new_lines:
            f.write(line + '\n')

# 输出告警给 shell
for a in alerts:
    print(f'ALERT|{a[\"type\"]}|{a[\"speaker\"]}|{a[\"text\"]}')
" <<< "$events" 2>/dev/null | while IFS='|' read -r _ type speaker text; do
      [ "$type" = "transcript" ] && check_client_mention "$text" "$meeting_id"
      [ "$type" = "transcript" ] && check_keywords "$text" "$meeting_id"
    done
  done
}

# ── 自动检测模式 ──
auto_mode() {
  log "AUTO MODE: 后台检测会议中..."
  local last_id=""
  local poll_pid=""

  while true; do
    local info
    info=$("$LARK_CLI" vc +meeting-list-active --as user --format json 2>/dev/null || echo '{"data":{"meetings":[]}}')

    local cur_id cur_title
    cur_id=$(echo "$info" | python3 -c "import sys,json;d=json.load(sys.stdin);ms=d.get('data',{}).get('meetings',[]);print(ms[0]['meeting_id'] if ms else '')" 2>/dev/null)
    cur_title=$(echo "$info" | python3 -c "import sys,json;d=json.load(sys.stdin);ms=d.get('data',{}).get('meetings',[]);print(ms[0].get('meeting_title','?') if ms else '')" 2>/dev/null)

    # 检测到新会议 → 后台启动旁听，主循环继续扫
    if [ -n "$cur_id" ] && [ "$cur_id" != "$last_id" ]; then
      last_id="$cur_id"
      do_rollcall "$cur_id" "$cur_title"
      run_poll "$cur_id" "$cur_title" &
      poll_pid=$!
      log "AUTO: spawned run_poll PID=$poll_pid for $cur_id"
    fi

    # 如果当前会议已结束（无活跃会议），清理状态
    if [ -z "$cur_id" ] && [ -n "$last_id" ]; then
      log "AUTO: no active meeting, resetting (was $last_id)"
      last_id=""
      # 杀死残留子进程（如果还活着）
      [ -n "$poll_pid" ] && kill "$poll_pid" 2>/dev/null || true
      poll_pid=""
    fi

    sleep 10
  done
}

# ── 入口 ──
if [ $# -eq 0 ]; then
  auto_mode
elif [ $# -ge 1 ]; then
  MEETING_ID="$1"
  MEETING_TITLE="${2:-未命名会议}"
  do_rollcall "$MEETING_ID" "$MEETING_TITLE"
  run_poll "$MEETING_ID" "$MEETING_TITLE"
fi
