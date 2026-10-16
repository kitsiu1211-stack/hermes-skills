#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把会议 JSONL / 长逐字稿压成「可安全 read_file」的阅读件。

为什么需要它：合并同说话人后的段落常有 2000+ 字符，直接 read_file 会在**行内**
截断（输出出现 [truncated]），你会不知情地漏掉整段发言的后半部分。本脚本把每段
折成 <=width 字符/行，每段带 `### [序号] 说话人 @HH:MM:SS (len=N)` 头，之后就能
用 read_file + offset/limit 分段读，零丢失。

用法：
    python3 wrap_for_reading.py <input.jsonl|input.txt> [output.txt] [--width 100]

输入两种形态自动识别：
  * JSONL（poll.sh 产出，每行 {"type":"transcript","speaker":..,"text":..}）：
    只取 type=transcript；同 speaker 连续合并；丢弃近重复长段（宣传片回声）
  * 纯文本：按空行/换行分段，不做说话人合并

stdout 打印统计，务必看一眼再决定读法。
"""

import json
import os
import re
import sys
import textwrap
from collections import Counter

PLACEHOLDER_SPEAKER = "?"


def norm_speaker(s):
    s = (s or "").strip()
    return s or PLACEHOLDER_SPEAKER


def hhmmss(t):
    """time 字段可能是 '2026-09-18T14:07:57+08:00' 或毫秒 epoch 字符串。"""
    t = str(t or "")
    if not t:
        return "--:--:--"
    if t.isdigit() and len(t) >= 10:  # epoch ms
        try:
            import datetime
            return datetime.datetime.fromtimestamp(int(t) / 1000).strftime("%H:%M:%S")
        except Exception:
            return "--:--:--"
    m = re.search(r"T(\d{2}:\d{2}:\d{2})", t)
    return m.group(1) if m else "--:--:--"


def load_jsonl(path):
    """→ [(speaker, text, time)]. 只保留 transcript，按句子顺序。"""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            # 明确只取字幕：join/leave 每轮重复追加，chat 需单独按 message_id 去重
            if d.get("type") != "transcript":
                continue
            txt = (d.get("text") or "").strip()
            if not txt:
                continue
            rows.append((norm_speaker(d.get("speaker")), txt, d.get("time", "")))
    return rows


def load_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    rows = []
    for para in re.split(r"\n\s*\n", raw):
        para = " ".join(para.split())
        if para:
            rows.append((PLACEHOLDER_SPEAKER, para, ""))
    return rows


def merge_consecutive(rows):
    out = []
    for sp, txt, t in rows:
        if out and out[-1]["speaker"] == sp and len(txt) < 400 and len(out[-1]["text"]) < 6000:
            out[-1]["text"] += txt
        else:
            out.append({"speaker": sp, "text": txt, "time": t})
    return out


def drop_echoes(segs, min_len=200, probe=150):
    """宣传片/重播回声：长段的前 probe 字出现在更早的长段里 → 丢弃。

    实测开场循环播放品牌宣传片时，ASR 会把它记到某位参会人头上并反复产出
    近似长段（1393/730/191 字符），不清掉会占掉开场 20 分钟且造成内容错觉。
    """
    kept, dropped = [], 0
    long_seen = []
    for s in segs:
        t = s["text"]
        if len(t) > min_len:
            head = t[:probe]
            if any(head in prev or prev[:probe] in t for prev in long_seen):
                dropped += 1
                continue
            long_seen.append(t)
        kept.append(s)
    return kept, dropped


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    width = 100
    for a in sys.argv[1:]:
        if a.startswith("--width"):
            width = int(a.split("=", 1)[1]) if "=" in a else 100
    if not args:
        print(__doc__)
        sys.exit(1)

    src = args[0]
    dst = args[1] if len(args) > 1 else "/tmp/tr_wrap.txt"

    is_jsonl = src.endswith(".jsonl")
    if not is_jsonl:
        # 逐行 JSON 也当 jsonl 处理
        with open(src, "r", encoding="utf-8", errors="replace") as f:
            head = f.readline().strip()
        is_jsonl = head.startswith("{") and '"type"' in head

    raw_rows = load_jsonl(src) if is_jsonl else load_text(src)
    segs = merge_consecutive(raw_rows)
    segs, dropped = drop_echoes(segs)

    total_chars = sum(len(s["text"]) for s in segs)
    with open(dst, "w", encoding="utf-8") as f:
        for i, s in enumerate(segs, 1):
            f.write("### [%d] %s @%s (len=%d)\n" % (i, s["speaker"], hhmmss(s["time"]), len(s["text"])))
            # break_long_words=True 是硬要求：中文无空格，False 会让整段不折行
            for line in textwrap.wrap(s["text"], width, break_long_words=True):
                f.write(line + "\n")
            f.write("\n")

    n_lines = sum(1 for _ in open(dst, encoding="utf-8"))
    print("输入段: %d → 合并后: %d → 去回声丢弃: %d" % (len(raw_rows), len(segs) + dropped, dropped))
    print("总字数: %d | 输出行数: %d | 折行宽: %d" % (total_chars, n_lines, width))
    if is_jsonl:
        spk = Counter(s["speaker"] for s in segs)
        print("说话人段数 Top8: %s" % dict(spk.most_common(8)))
    print("阅读件: %s" % dst)
    print("→ 接下来用 read_file 配 offset/limit 分段读（%d 行，约 %d 次读完）" % (n_lines, max(1, n_lines // 250 + 1)))
    if os.path.getsize(dst) == 0:
        print("!! 输出为空：确认输入是 transcript 事件（join/leave/chat 会被本脚本忽略）")


if __name__ == "__main__":
    main()
