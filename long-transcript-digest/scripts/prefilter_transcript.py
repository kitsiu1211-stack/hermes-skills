#!/usr/bin/env python3
"""长字幕/长会议日志预压缩器（零 token，读文件不进 LLM）。

用法：
    python3 prefilter_transcript.py <日志路径> [--min-len 16] [--out /tmp/clean.txt]

支持两种输入：
    1) poll.sh 写出的 JSONL（每行 {"type": "transcript"|"chat"|"join"|..., ...}）
    2) 纯文本逐字稿（每行 "[说话人] 文本"）

输出：清理后的文本 + stdout 打印统计 JSON（句数、说话人排行、聊天链接归属）。
先读统计，再决定读哪一段正文——不要整份塞进上下文。
"""
import argparse
import collections
import json
import re
import sys

FILLER_CHARS = re.compile(r"[哈啊哦嗯诶嘿呀吧的呢了\s，。！？~、…]")
NOISE_CHAT = {
    "OK", "Yes", "NO", "LOL", "THUMBSUP", "LightThumbsup", "MediumThumbsup",
    "DarkThumbsup", "MediumLightThumbsup", "APPLAUSE", "LightApplaud",
    "FINGERHEART", "PARTY", "GLANCE", "SMIRK", "ROSE", "LOVE", "BLUSH",
    "AWESOMN", "JIAYI", "TEARS", "FACEPALM", "YouAreTheBest", "BeamingFace",
    "WITTY", "ENOUGH", "Trophy", "好评",
}


def is_filler(text, min_len):
    """短语气句 / 纯笑声 / 系统噪音行 -> True。"""
    t = text.strip()
    if len(t) < min_len:
        return True
    if not FILLER_CHARS.sub("", t) or len(FILLER_CHARS.sub("", t)) <= 2:
        return True
    return False


def parse(path):
    """返回 (transcript_records, chat_records, event_counts)。"""
    transcripts, chats = [], []
    counts = collections.Counter()
    raw = open(path, encoding="utf-8", errors="replace").read().splitlines()

    jsonl = False
    for line in raw[:20]:
        if line.strip().startswith("{"):
            jsonl = True
            break

    if jsonl:
        for line in raw:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            kind = d.get("type", "")
            counts[kind] += 1
            if kind == "transcript":
                transcripts.append((d.get("speaker", "?"), d.get("text", ""),
                                    d.get("sentence_id"), d.get("time", "")))
            elif kind == "chat":
                chats.append((d.get("speaker", "?"), (d.get("text") or "").strip()))
    else:
        for line in raw:
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line.strip())
            if m:
                transcripts.append((m.group(1), m.group(2), None, ""))
    return transcripts, chats, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min-len", type=int, default=16)
    ap.add_argument("--out", default="/tmp/transcript_clean.txt")
    args = ap.parse_args()

    transcripts, chats, counts = parse(args.path)

    # 1) sentence_id 去重（同一句会多次推送修正版），无 id 时按 (speaker, text) 去重
    seen, ordered = set(), []
    for rec in transcripts:
        key = rec[2] if rec[2] else (rec[0], rec[1])
        if key in seen:
            continue
        seen.add(key)
        ordered.append(rec)

    # 2) 丢填充行
    kept = [r for r in ordered if not is_filler(r[1], args.min_len)]
    dropped = len(ordered) - len(kept)

    # 3) 说话人排行
    per_speaker = collections.Counter(r[0] for r in kept)

    # 4) 聊天去噪（按 (speaker, text) 去重后剔系统噪音） + URL 提取
    seen_chat, real_chat, urls = set(), [], {}
    for speaker, text in chats:
        if not text or text.startswith("VC_"):
            continue
        if (speaker, text) in seen_chat:
            continue
        seen_chat.add((speaker, text))
        for u in re.findall(r"https?://[^\s，,）)]+", text):
            urls.setdefault(u, speaker)
        if len(text) > 3 and text not in NOISE_CHAT and not text.isascii():
            real_chat.append({"speaker": speaker, "text": text})
        elif len(text) > 3 and text not in NOISE_CHAT:
            real_chat.append({"speaker": speaker, "text": text})

    body = "\n".join(f"[{r[0]}] {r[1]}" for r in kept)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")

    stats = {
        "source": args.path,
        "out": args.out,
        "events": dict(counts),
        "transcript_unique": len(ordered),
        "transcript_kept": len(kept),
        "filler_dropped": dropped,
        "kept_chars": len(body),
        "speakers_by_volume": per_speaker.most_common(20),
        "chat_events_raw": len(chats),
        "chat_unique_after_dedupe": len(seen_chat),
        "chat_meaningful": len(real_chat),
        "urls": [{"url": u, "first_posted_by": s} for u, s in urls.items()],
        "meaningful_chat_sample": real_chat[:60],
    }
    json.dump(stats, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
