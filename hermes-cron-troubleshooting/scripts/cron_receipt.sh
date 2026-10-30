#!/bin/bash
# cron_receipt.sh — 周期任务「完成回执」，供外部哨兵（另一台机器 / 另一个 Agent）观测
# 设计说明：hermes-cron-troubleshooting/references/external-sentinel-receipt.md
# 加固与自测：hermes-cron-troubleshooting/references/receipt-chain-hardening.md
#
# 用法：
#   cron_receipt.sh ok   "<任务名>" "<期次>" ["补跑"]
#   cron_receipt.sh fail "<任务名>" "<期次>" "<一句原因>"
#   cron_receipt.sh skip "<任务名>" ["<说明>"] ["<期次>"]   # 双周任务的非执行周
#   cron_receipt.sh selfcheck                              # 链路自检（上线前必跑一次）
# 任务名用白名单（示例：周复盘 / 周深读 / Skill同步 / 赢单雷达）——观察方按字符串解析，别自创别名。
# 期次一律 ISO 周 `YYYY-Www`（含双周任务）：观察方按周匹配，用日期会两边对不上。
#
# 可覆盖的环境变量：
#   RECEIPT_ROOT_MSG  话题根消息 om_xxx（默认：本机 Agent 协作群那个话题，按需改）
#   RECEIPT_AS        身份 bot|user（默认 bot）
#   RECEIPT_LOG       日志路径（默认 ~/.hermes/cron/receipts.log）
set -u

ROOT_MSG="${RECEIPT_ROOT_MSG:-om_x100b612ee8eec8a8cfc83c91842ffaf}"
AS="${RECEIPT_AS:-bot}"
LOG="${RECEIPT_LOG:-$HOME/.hermes/cron/receipts.log}"
KIND="${1:-}"

iso_week() { python3 -c 'import datetime;d=datetime.date.today();print(f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}")'; }

case "$KIND" in
  ok)
    TASK="${2:?task name required}"; PERIOD="${3:-$(iso_week)}"; SUF="${4:-}"
    # ⚠️ 不能用 ${SUF:+（$SUF）}：全角括号会被 bash 当成变量名的一部分，
    # 在 set -u 下直接 `SUF）: unbound variable` 退出（普通 shell 也复现，不是 locale 问题）。
    SUFFIX=""
    [ -n "$SUF" ] && SUFFIX="（${SUF}）"
    MSG="✅ ${TASK} ${PERIOD}${SUFFIX}"
    KEY="rcpt-ok-${TASK}-${PERIOD}"
    [ -n "$SUF" ] && KEY="${KEY}-${SUF}"
    ;;
  fail)
    TASK="${2:?task name required}"; PERIOD="${3:-$(iso_week)}"; WHY="${4:-未知原因}"
    MSG="❌ ${TASK} ${PERIOD} 失败：${WHY}"
    KEY="rcpt-fail-${TASK}-${PERIOD}"
    ;;
  skip)
    TASK="${2:?task name required}"; WHY="${3:-本周非执行周}"
    PERIOD="${4:-$(iso_week)}"
    # ⏭ 必须带期次：观察方多数按「任务名 + 期次」匹配，没有周号会被当成对不上号而重复催
    MSG="⏭ ${TASK} ${PERIOD} ${WHY}"
    KEY="rcpt-skip-${TASK}-${PERIOD}"
    ;;
  selfcheck)
    MSG="🔧 回执链路自检 ok（非产物，哨兵忽略本条）"
    KEY="rcpt-selfcheck-$(date +%Y%m%d%H%M)"
    ;;
  *)
    echo "usage: $0 ok|fail|skip|selfcheck <task> [period] [note]" >&2; exit 2
    ;;
esac

KEY="${KEY:0:50}"   # 飞书 idempotency-key 上限 50 字符
mkdir -p "$(dirname "$LOG")"
OUT=$(lark-cli im +messages-reply --message-id "$ROOT_MSG" --text "$MSG" \
      --reply-in-thread --as "$AS" --idempotency-key "$KEY" 2>&1)
RC=$?
OK=$(printf '%s' "$OUT" | grep -c '"ok": true')
printf '%s\t%s\trc=%s\tok=%s\t%s\n' "$(date '+%F %T')" "$KIND" "$RC" "$OK" "$MSG" >> "$LOG"

if [ "$OK" -lt 1 ]; then
  # 静默失败的代价是观察方把「没收到回执」误判成「任务没跑」——必须显式报错 + 非零退出
  printf '%s\n' "$OUT" | head -6
  echo "RECEIPT_SEND_FAILED: $MSG" >&2
  exit 1
fi
echo "receipt sent: $MSG"
