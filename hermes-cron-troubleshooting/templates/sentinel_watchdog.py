#!/usr/bin/env python3
"""Sentinel watchdog for a cron job: silent on success, auto-rerun on failure.

Install:
  1. Copy this file to ~/.hermes/scripts/<name>.py and set JOB_ID.
  2. cronjob create with no_agent=True, script=<name>.py,
     schedule = 30-60 min AFTER the main job's schedule (e.g. main 9:05 -> sentinel 9:35).
  3. Optional second checkpoint (+30min more) for a second retry chance.

Behavior:
  - Main job succeeded today -> prints NOTHING (empty stdout = fully silent,
    no message delivered, zero tokens, zero noise).
  - Main job failed -> runs `hermes cron run <JOB_ID>` (scheduler fires it next
    tick; gateway/scheduler must be running) and prints a short alert.

Pitfall baked in: FAILED runs also write an output file. Presence of a file is
NOT success — only a file WITHOUT fail markers (## Error / RuntimeError /
timed out) counts. Verify with the real job's output before trusting it.
"""
import datetime
import glob
import os
import shutil
import subprocess

JOB_ID = "REPLACE_WITH_JOB_ID"  # from `cronjob action='list'`
OUT_DIR = os.path.expanduser("~/.hermes/cron/output/%s" % JOB_ID)
FAIL_MARKERS = ("## Error", "RuntimeError", "timed out")


def last_success_file():
    """Most recent output file for today WITHOUT fail markers, else None."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    files = sorted(glob.glob(os.path.join(OUT_DIR, today + "_*.md")))
    if not files:
        return None
    for f in reversed(files):
        try:
            content = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if not any(m in content for m in FAIL_MARKERS):
            return f
    return None


def main():
    if last_success_file():
        return  # silent
    now = datetime.datetime.now().strftime("%H:%M")
    hermes = shutil.which("hermes")
    if not hermes:
        print("⚠️ 任务未成功，且找不到 hermes 命令，请手动补跑（%s）" % now)
        return
    try:
        subprocess.run(
            [hermes, "cron", "run", JOB_ID],
            capture_output=True, timeout=120,
        )
        print("⚠️ 任务未成功，已自动触发补跑（%s）→ 完成后会收到产出" % now)
    except Exception as e:
        print("⚠️ 任务未成功，且自动补跑失败（%s）：%s" % (now, e))


if __name__ == "__main__":
    main()
