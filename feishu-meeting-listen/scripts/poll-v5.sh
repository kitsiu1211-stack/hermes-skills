#!/bin/bash
# ── poll.sh v5 ── 会议旁听 v5：自动检测 + 会前点名 + 实时告警 + C360 查客户
# 用法: bash poll-v5.sh                        # 自动检测入会
#       bash poll-v5.sh <meeting_id> [title]    # 手动指定会议

set -uo pipefail
# 注：不使用 set -e，run_poll 内部 API 错误不应杀死守护进程

LARK_CLI="${LARK_CLI:-/Users/bytedance/.npm-global/bin/lark-cli}"
C360_CLI="${C360_CLI:-/Users/bytedance/.npm-global/bin/lark-c360}"
PYTHON3="${PYTHON3:-/usr/bin/python3}"
LOG_DIR="$HOME/meeting_logs"
mkdir -p "$LOG_DIR"

# ── 配置 ──
ALERT_CHAT="oc_219a613c13292855c2dc4b80e59dfd6e"  # 告警群
USER_DM="ou_dc055b0b5b0b5db2b1af5e79c0536db6"     # 你的 DM（入会/离会通知）
ALERT_ENABLED=true                                   # 是否发送实时告警
C360_ENABLED=true                                    # C360 CLI 已就绪
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

# 直接发到你 DM（入会/离会等关键事件）
send_dm() {
  local text="$1"
  lark-cli im +messages-send --receive-id "$USER_DM" --receive-id-type open_id \
    --msg-type text --as bot --content "{\"text\":\"$text\"}" 2>/dev/null || true
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
        if isinstance(c, dict):
            name = c.get('name', '')
            alias = c.get('alias', '')
            c360s = c.get('c360_search', '')
            # 打印 name 及其变体
            print(name)
            short = name.replace('有限公司','').replace('股份有限公司','').replace('责任公司','').replace('（','').replace('）','').strip()
            if short != name:
                print(short)
            parts = short.split('科技')
            if parts[0].strip() and parts[0].strip() != short:
                print(parts[0].strip())
            # 打印 alias 中的各项
            if alias:
                for a in alias.split('/'):
                    a = a.strip()
                    if a and a != name:
                        print(a)
            # 打印 c360_search 关键词
            if c360s and c360s != alias and c360s != name:
                print(c360s)
        else:
            print(c)
" 2>/dev/null)
  fi
  [ ${#KNOWN_CLIENTS[@]} -eq 0 ] && KNOWN_CLIENTS=("拓竹" "和生" "疆海" "安克")
}
_load_clients

# ── C360 综合查询（商机产品 + 最近跟进）──
c360_lookup() {
  local name="$1"
  if [ "$C360_ENABLED" != "true" ]; then
    echo "C360: 未启用"
    return
  fi
  if [ ! -x "$C360_CLI" ]; then
    echo "C360: CLI 不可用"
    return
  fi

  # Step 1: search all → 拿 account_id + 商机摘要
  local sresult
  sresult=$("$C360_CLI" search all --keyword "$name" --limit 5 --json 2>/dev/null)
  if [ -z "$sresult" ]; then
    echo "C360: 查询超时"
    return
  fi

  echo "$sresult" | python3 -c "
import json, sys, os

try:
    data = json.load(sys.stdin)
except:
    print('C360: 解析失败')
    sys.exit(0)

if not data.get('ok'):
    print('C360: API 失败')
    sys.exit(0)

d = data.get('data', {})

# 取 account_id
accts = d.get('account', {}).get('list', [])
account_id = ''
if accts:
    account_id = accts[0].get('abstract', {}).get('id', {}).get('display_value', '')

# 取商机摘要（取最近一条非赢单的）
opps = d.get('opportunity', {}).get('list', [])
opp_lines = []
for opp in opps[:3]:
    t = opp.get('title', {})
    ab = opp.get('abstract', {})
    stage = t.get('stage', {}).get('display_value', '{}')
    arr = ab.get('arr', {}).get('display_value', '{}')
    skus = ab.get('product_sku_keys', {}).get('display_value', '[]')

    try:
        sl = json.loads(stage)
        stage_label = sl.get('label', '?')
    except:
        stage_label = '?'
    try:
        al = json.loads(arr)
        arr_str = str(al.get('currency_iso_code', '')) + ' ' + str(al.get('currency_value', '?'))
    except:
        arr_str = '?'
    try:
        sku_list = json.loads(skus) if isinstance(skus, str) else skus
    except:
        sku_list = []

    if stage_label in ('赢单', '输单', '关闭', '丢单'):
        continue
    opp_lines.append('📦 ' + ', '.join(sku_list[:3]) + '  |  ' + stage_label)
    break

# 输出给 shell：account_id + 商机摘要（用 EOF 分隔）
print('ACCT=' + account_id)
for line in opp_lines:
    print('OPP=' + line)

# 标记：需要查跟进
if account_id:
    print('NEED_FU=1')
else:
    print('NEED_FU=0')
" 2>/dev/null
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
  send_dm "$msg"
}

# ── 客户名检测 → C360 综合查询 ──
check_client_mention() {
  local text="$1" meeting_id="$2"
  for client in "${KNOWN_CLIENTS[@]}"; do
    if echo "$text" | grep -q "$client"; then
      log "CLIENT MENTION: $client"

      # 找到匹配的完整客户名（取最长的那条）
      local full_name="$client"
      for c in "${KNOWN_CLIENTS[@]}"; do
        if echo "$c" | grep -q "$client" && [ ${#c} -gt ${#full_name} ]; then
          full_name="$c"
        fi
      done

      # 查 client_list.json 获取 c360_search 关键词
      local search_term="$full_name"
      local c360_kw
      c360_kw=$(python3 -c "
import json
with open('$HOME/.hermes/data/client_list.json') as f:
    for c in json.load(f).get('clients', []):
        if isinstance(c, dict):
            name = c.get('name', '')
            alias = c.get('alias', '')
            c360s = c.get('c360_search', '')
            # 检查是否匹配这个 client（name、alias 中子项、c360_search）
            candidates = [name] + ([a.strip() for a in alias.split('/')] if alias else []) + ([c360s] if c360s else [])
            if '$client' in candidates or any(x in candidates for x in ['$client'] if x):
                print(c360s if c360s else name)
                break
" 2>/dev/null)
      [ -n "$c360_kw" ] && search_term="$c360_kw"

      # 调用 C360 综合查询
      local acct_id="" opp_info="" need_fu=0
      while IFS='=' read -r key val; do
        case "$key" in
          ACCT) acct_id="$val" ;;
          OPP) opp_info="$val" ;;
          NEED_FU) need_fu="$val" ;;
        esac
      done < <(c360_lookup "$search_term" 2>/dev/null)

      # 查最近跟进
      local fu_info=""
      if [ "$need_fu" = "1" ] && [ -n "$acct_id" ]; then
        fu_info=$(c360_followup "$acct_id" 2>/dev/null)
      fi

      local alert="【🔔 客户提及】「${client}」($(ts))
会议: ${meeting_id}
原文: ...${text}...

${opp_info}
${fu_info}"

      send_alert "$alert"
      return
    fi
  done
}

# ── C360 查最近跟进 ──
c360_followup() {
  local account_id="$1"
  local result
  result=$("$C360_CLI" follow_up +recent --account-id "$account_id" --limit 1 \
    --field id --field follow_date --field owner_id --field content \
    --json 2>/dev/null)
  if [ -z "$result" ]; then
    echo "📝 最近跟进: 查询失败"
    return
  fi
  echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print('📝 最近跟进: 解析失败')
    sys.exit(0)
if not data.get('ok'):
    print('📝 最近跟进: 无记录')
    sys.exit(0)
items = data.get('data', {}).get('list', [])
if not items:
    print('📝 最近跟进: 无记录')
    sys.exit(0)
item = items[0]
fd = item.get('follow_date', {}).get('display_value', '?')
content = item.get('content', {}).get('display_value', '')
# 截取前 200 字
if len(content) > 200:
    content = content[:200] + '...'
print('📝 最近跟进(' + fd + '): ' + content)
"
}

# ── 关键词检测 ──
check_keywords() {
  local text="$1" meeting_id="$2"
  local keywords=("预算" "价格" "报价" "todo" "下一步" "待办" "action" "决策" "确认" "签约" "合同" "交付")
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

for a in alerts:
    print(f'ALERT|{a[\"type\"]}|{a[\"speaker\"]}|{a[\"text\"]}')
" <<< "$events" 2>/dev/null | while IFS='|' read -r _ type speaker text; do
      [ "$type" = "transcript" ] && check_client_mention "$text" "$meeting_id"
      [ "$type" = "transcript" ] && check_keywords "$text" "$meeting_id"
    done
  done
}

# ── 自动检测模式（v4 简洁逻辑）──
auto_mode() {
  log "AUTO MODE: 后台检测会议中..."
  local last_id=""
  local poll_pid=""

  while true; do
    local info
    info=$(perl -e 'alarm shift; exec @ARGV' -- 30 "$LARK_CLI" vc +meeting-list-active --as user --format json 2>/dev/null || echo '{"data":{"meetings":[]}}')

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
      [ -n "$poll_pid" ] && kill "$poll_pid" 2>/dev/null || true
      last_id=""
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
