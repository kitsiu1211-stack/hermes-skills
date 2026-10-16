#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会议转写预压缩：JSONL / 纯文本 → 分段正文 + 归因体检（零 token，不调 LLM）。

用法:
  python3 transcript_paragraphs.py <meeting_log.jsonl | transcript.txt> [-o /tmp/out.txt] [--min-chars 3]

它做四件事:
  1. 体检报告打到 stdout —— 时间范围 / 事件类型计数 / 说话人句数排行 / 会议室麦占比 / 段落数与字符数
     （先看这份报告再决定怎么读；说话人排行同时暴露归因质量）
  2. 会议室内设备名（如「深圳景湖大厦-F15-03🎦[应急会议室](13)」）统一改写成 (会议室麦) 并给出占比警告
  3. 同一说话人的连续句子合并成段落（1154 句 → 一百多段，读起来才有上下文）
  4. 丢掉纯语气词段落（去掉「嗯/对/是的/啊…」后不足 --min-chars 字的整段）

输出文件每行一段：[说话人] 正文 —— 再用 read_file 分段读。
⚠️ 折行交给 wrap_for_reading.py，中文必须 break_long_words=True（见 SKILL.md）。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

FILLER = re.compile(r"[。，、？！：；,.!?\s嗯对是的啊哦诶哈好的嘛呢吧呀哎额呃~～]")
ROOM_HINTS = ("会议室", "🎦", "Meeting Room", "meeting room")


def is_room(speaker: str) -> bool:
    return any(h in speaker for h in ROOM_HINTS)


def load(path: str):
    """返回 (lines, raw_kind)；lines = [{'type','speaker','text','time'}]"""
    rows = []
    with open(path, encoding="utf-8") as f:
        head = f.readline()
        f.seek(0)
        if head.lstrip().startswith("{"):
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                rows.append({
                    "type": d.get("type", "transcript"),
                    "speaker": d.get("speaker", "?"),
                    "text": (d.get("text") or "").strip(),
                    "time": (d.get("time") or "")[:19],
                })
            return rows, "jsonl"
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
            if m:
                rows.append({"type": "transcript", "speaker": m.group(1),
                             "text": m.group(2).strip(), "time": ""})
            else:
                rows.append({"type": "transcript", "speaker": "?",
                             "text": line.strip(), "time": ""})
        return rows, "txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--min-chars", type=int, default=3,
                    help="去掉语气词后不足该字数的段落整段丢弃（默认 3）")
    ap.add_argument("--top", type=int, default=15, help="说话人排行打印前 N（默认 15）")
    args = ap.parse_args()

    rows, kind = load(args.path)
    if not rows:
        sys.exit("空文件/解析不到内容: " + args.path)

    kinds = Counter(r["type"] for r in rows)
    tr = [r for r in rows if r["type"] == "transcript"]
    tr.sort(key=lambda r: r["time"])
    if not tr:
        sys.exit("没有 transcript 行（只有 %s）" % dict(kinds))

    # ---- 体检 ----
    print("=== 体检报告 %s (%s) ===" % (os.path.basename(args.path), kind))
    print("事件类型计数: %s" % dict(kinds))
    print("时间范围: %s -> %s" % (tr[0]["time"] or "?", tr[-1]["time"] or "?"))
    sp = Counter(r["speaker"] for r in tr)
    room_n = sum(c for s, c in sp.items() if is_room(s))
    print("字幕句数: %d | 说话人种类: %d | 会议室麦占比: %d/%d (%.0f%%)"
          % (len(tr), len(sp), room_n, len(tr), 100.0 * room_n / len(tr)))
    if room_n:
        print("  ⚠️ 有 %d 句记在会议室设备名下 → 无法归因到个人，输出里必须显式说明"
              % room_n)
        for s, c in sp.most_common():
            if is_room(s):
                print("     设备名: %s (%d 句)" % (s, c))
    print("说话人句数排行:")
    for s, c in sp.most_common(args.top):
        print("   %5d  %s%s" % (c, s, "  [会议室麦]" if is_room(s) else ""))
    chat = [r for r in rows if r["type"] == "chat" and len(r["text"]) > 3]
    uniq_chat = {(r["speaker"], r["text"]) for r in chat}
    if chat:
        print("聊天: %d 条 → 唯一(说话人,内容) %d 条，唯一长消息样例 %s"
              % (len(chat), len(uniq_chat),
                 list({t for _, t in uniq_chat})[:3]))

    # ---- 分段 ----
    paras = []
    for r in tr:
        text = r["text"]
        if not text:
            continue
        name = "(会议室麦)" if is_room(r["speaker"]) else r["speaker"]
        if paras and paras[-1][0] == name:
            paras[-1][1].append(text)
        else:
            paras.append([name, [text]])

    kept = []
    for name, chunks in paras:
        body = "".join(chunks)
        if len(FILLER.sub("", body)) < args.min_chars:
            continue
        kept.append("[%s] %s" % (name, body))

    out = args.out or os.path.splitext(args.path)[0] + ".paragraphs.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")
    print("段落: %d → 保留 %d | 输出 %s (%d 字符)"
          % (len(paras), len(kept), out, os.path.getsize(out)))
    print("下一步: python3 wrap_for_reading.py %s /tmp/tr_wrap.txt 再 read_file 分段读" % out)


if __name__ == "__main__":
    main()
