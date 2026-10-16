#!/bin/bash
# restart_stateful_watcher.sh — 重启一个有状态的长跑 watcher（告警器 / poll / watchdog）
#
# 为什么需要它：长跑进程用的是启动时载入的旧代码，改完源码必须重启；而这类进程把
# 游标(offset)/已发ID/计数器落在 state.json 里，直接重启会把"游标→现在"的积压
# 一次性回灌（用户被一堆过期告警砸中），per-run 配额被耗尽时更是"改了也一条不推"。
# 本脚本把 杀旧进程 → 游标拨到日志末尾 → 重置耗尽计数 → detached 冷启动 → 单实例校验
# 固化成一步。
#
# 用法：
#   restart_stateful_watcher.sh <script> <pgrep匹配串> [选项]
#
# 选项：
#   --state <path>        状态 JSON（python dict）；给了才会动游标/计数
#   --log   <path>        日志文件；游标 = 该文件的当前大小（EOF）
#   --cursor-key <key>    要拨到 EOF 的键，默认 offset
#   --reset-key <key>     要清零的键，可重复（如 count）
#   --args  "<string>"    原样追加给脚本的参数串（重启时必须原样复用，见下）
#   --logfile <path>      nohup 追加输出；默认 <script>.nohup.log
#   --cwd   <path>        启动前 cd 到这里（脚本用相对路径读配置时必须给）
#   --python <path>       解释器，默认 /usr/bin/python3；给 "" 则直接执行脚本本身（.sh）
#   --wait  <secs>        启动后等待秒数再校验，默认 2
#
# 退出码：0 成功且单实例；1 旧进程没死干净（中止，避免双实例）；2 启动后实例数 != 1
#
# 🚨 <pgrep匹配串> 要足够独特（例："meeting_radar.py 7696445042760535267"），
#    否则会杀掉别的会议/任务的同名进程。

set -uo pipefail

SCRIPT="${1:?用法: restart_stateful_watcher.sh <script> <pgrep匹配串> [选项]}"
MATCH="${2:?缺少 pgrep 匹配串}"
shift 2

STATE=""; LOG=""; CURSOR_KEY="offset"; RESET_KEYS=(); ARGS=""
LOGFILE=""; CWD=""; PYTHON="/usr/bin/python3"; WAIT=2

while [ $# -gt 0 ]; do
  case "$1" in
    --state)      STATE="$2"; shift 2 ;;
    --log)        LOG="$2"; shift 2 ;;
    --cursor-key) CURSOR_KEY="$2"; shift 2 ;;
    --reset-key)  RESET_KEYS+=("$2"); shift 2 ;;
    --args)       ARGS="$2"; shift 2 ;;
    --logfile)    LOGFILE="$2"; shift 2 ;;
    --cwd)        CWD="$2"; shift 2 ;;
    --python)     PYTHON="$2"; shift 2 ;;
    --wait)       WAIT="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

[ -n "$LOGFILE" ] || LOGFILE="${SCRIPT}.nohup.log"

# ---------------------------------------------------------------- 1. 停旧进程
# 排除自己（$$）和父 shell（$PPID）：本脚本命令行里就含 $MATCH，否则会自伤
own_pids() { pgrep -f "$MATCH" 2>/dev/null | grep -v -x -e "$$" -e "$PPID"; }

before="$(own_pids | wc -l | tr -d ' ')"
if [ "$before" != "0" ]; then
  echo "[1/4] 停旧进程：命中 $before 个 → $MATCH"
  # 逐个 kill，不用 xargs：macOS 的 BSD xargs 没有 GNU 的 -r，空输入会报错
  for p in $(own_pids); do kill "$p" 2>/dev/null || true; done
  sleep 2
  if [ "$(own_pids | wc -l | tr -d ' ')" != "0" ]; then
    echo "    仍存活，SIGKILL"
    for p in $(own_pids); do kill -9 "$p" 2>/dev/null || true; done
    sleep 1
  fi
  if [ "$(own_pids | wc -l | tr -d ' ')" != "0" ]; then
    echo "[abort] 旧进程杀不掉（可能双实例）→ 先人工排查，不要盲目起新的" >&2
    exit 1
  fi
else
  echo "[1/4] 没有在跑的旧进程（首次启动）"
fi

# ---------------------------------------------------------------- 2. 状态归位
if [ -n "$STATE" ] && [ -f "$STATE" ]; then
  echo "[2/4] 状态归位：$STATE（游标 $CURSOR_KEY → 日志末尾；清零 ${RESET_KEYS[*]:-无}）"
  "$PYTHON" - "$STATE" "$LOG" "$CURSOR_KEY" ${RESET_KEYS[@]+"${RESET_KEYS[@]}"} <<'PY'
import json, os, sys
sp, log, ckey, *reset = sys.argv[1:]
st = json.load(open(sp))
if log and os.path.exists(log):
    st[ckey] = os.path.getsize(log)      # 跳过积压，避免重启后回灌
for k in reset:
    st[k] = 0                            # 配额被误报耗尽时必须清，否则新代码一条不推
json.dump(st, open(sp, "w"))
print(f"      {ckey}={st.get(ckey)}  清零={reset or '无'}")
PY
elif [ -n "$STATE" ]; then
  echo "[2/4] state 不存在（$STATE）→ 首次启动，跳过游标归位"
else
  echo "[2/4] 未指定 --state → 跳过游标归位（无状态 watcher）"
fi

# ---------------------------------------------------------------- 3. detached 冷启动
# 🚨 nohup/disown 必须写在脚本里：terminal 工具会拒收命令行中的 shell 级 background wrapper
echo "[3/4] 冷启动：$SCRIPT $ARGS"
[ -n "$CWD" ] && cd "$CWD" || true
if [ -n "$PYTHON" ]; then
  # shellcheck disable=SC2086
  nohup "$PYTHON" "$SCRIPT" $ARGS >> "$LOGFILE" 2>&1 &
else
  # shellcheck disable=SC2086
  nohup "$SCRIPT" $ARGS >> "$LOGFILE" 2>&1 &
fi
disown

# ---------------------------------------------------------------- 4. 单实例校验
sleep "$WAIT"
n="$(own_pids | wc -l | tr -d ' ')"
echo "[4/4] 实例数 = $n （必须 = 1）  日志：$LOGFILE"
if [ "$n" != "1" ]; then
  echo "[abort] 实例数不是 1：可能启动即崩（看日志尾）或起了双份" >&2
  tail -n 15 "$LOGFILE" 2>/dev/null >&2
  exit 2
fi

echo "--- 启动横幅（确认新代码 + 参数没漏） ---"
tail -n 6 "$LOGFILE" 2>/dev/null
echo "OK"
