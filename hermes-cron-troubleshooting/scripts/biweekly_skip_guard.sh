#!/bin/bash
# biweekly_skip_guard.sh — 双周任务的「轮空周 ⏭ 回执」确定性兜底
#
# 为什么存在：观察方判轮空周的唯一依据是群里有没有 ⏭ 回执，而「LLM 任务记得发」
# 是不可靠的（模型漏发 / 任务没跑 / 静默跳过）。这个脚本把 ⏭ 变成脚本动作，零 token。
#
# 用法：装成两个 no_agent cron，各在自己的日子跑
#   40 10 * * 5   周五（双周任务 A：Skill 同步之类）
#   40 9  * * 1   周一（双周任务 B：商机雷达之类）
# 时间点必须晚于真任务、早于观察方的判定时刻。
#
# 逻辑：非双周日 → 静默；偶数周（执行周）→ 静默，✅/❌ 由真任务负责；
#       奇数周且本期日志里没有 ✅/❌/⏭ → 补发 ⏭。
# 自测：BIWEEK_DOW_OVERRIDE / BIWEEK_WEEK_OVERRIDE 可覆盖日期（见 references/receipt-chain-hardening.md）
set -u

LOG="${RECEIPT_LOG:-$HOME/.hermes/cron/receipts.log}"
RECEIPT="${RECEIPT_SCRIPT:-$HOME/.hermes/scripts/cron_receipt.sh}"

DOW=${BIWEEK_DOW_OVERRIDE:-$(date +%u)}   # 1=周一 5=周五
WEEK=${BIWEEK_WEEK_OVERRIDE:-$(date +%V)}
YEAR=${BIWEEK_YEAR_OVERRIDE:-$(date +%G)}
PERIOD="${YEAR}-W${WEEK}"

case "$DOW" in
  5) TASK="${BIWEEK_TASK_FRI:-Skill同步}" ;;
  1) TASK="${BIWEEK_TASK_MON:-赢单雷达}" ;;
  *) exit 0 ;;                       # 非双周任务的日子，静默
esac

if [ $((10#$WEEK % 2)) -eq 0 ]; then  # 偶数周 = 执行周，真任务负责 ✅/❌
  exit 0
fi

if [ -f "$LOG" ] && grep -qF -e "✅ ${TASK} ${PERIOD}" \
                          -e "❌ ${TASK} ${PERIOD}" \
                          -e "⏭ ${TASK} ${PERIOD}" "$LOG"; then
  exit 0
fi

OUT=$(bash "$RECEIPT" skip "$TASK" "本周非执行周" "$PERIOD" 2>&1)
RC=$?
if [ $RC -ne 0 ]; then
  printf 'BIWEEK_SKIP_GUARD_FAILED: %s %s\n%s\n' "$TASK" "$PERIOD" "$OUT"
  exit 1
fi
# 成功时保持静默：回执已直接进群，cron 不需要再发一条
exit 0
