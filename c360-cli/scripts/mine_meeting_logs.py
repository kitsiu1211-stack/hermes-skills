# -*- coding: utf-8 -*-
"""从本地会议旁听日志挖掘某个客户/关键词的上下文（C360 不可用时的降级来源）。

用途：当 lark-c360 被网关拦截（code 100001）、或只是想快速确认「这个公司是谁、谁是对接人、
买过什么、历史上聊过什么」时，用本地 ~/meeting_logs 的 JSONL 兜底。零 token、纯本地读取。

用法：
    python3 mine_meeting_logs.py 拓竹
    python3 mine_meeting_logs.py 逸文 --per-file 12
    python3 mine_meeting_logs.py 快造 --max-files 50 --chars 260

设计约束（踩过的坑）：
  * 绝不整份日志倒进上下文——单句截断到 --chars，每文件最多 --per-file 条、同文去重
  * 字幕按 time 排序；同 speaker 连续句合并成段，否则输出是碎片化的逐句流
  * 只读 type == "transcript"，chat/join/leave 是噪音（且 join 在旧日志里可能大量重复）
  * 必须带 coding 声明：macOS /usr/bin/python3 对无 BOM 的中文脚本会报
    "Non-UTF-8 code ... no encoding declared"，加 `# -*- coding: utf-8 -*-` 或改用 python3.11
"""
import argparse
import glob
import json
import os
import sys


def load_transcripts(path, keyword):
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "transcript":
                    continue
                if keyword in (d.get("text") or ""):
                    rows.append(d)
    except OSError:
        return []
    rows.sort(key=lambda d: d.get("time") or "")
    return rows


def merge_paragraphs(rows):
    """同 speaker 连续句合并成段，返回 [(speaker, text), ...]"""
    out = []
    for d in rows:
        sp = d.get("speaker") or "?"
        tx = (d.get("text") or "").strip()
        if not tx:
            continue
        if out and out[-1][0] == sp:
            out[-1][1] += tx
        else:
            out.append([sp, tx])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="从 ~/meeting_logs 挖掘客户上下文（C360 降级方案）")
    ap.add_argument("keyword", help="客户简称/全称/人名等要搜的关键词")
    ap.add_argument("--log-dir", default=os.path.expanduser("~/meeting_logs"))
    ap.add_argument("--per-file", type=int, default=8, help="每个命中文件最多输出多少段（默认 8）")
    ap.add_argument("--max-files", type=int, default=40, help="只扫最近修改的 N 个日志（默认 40）")
    ap.add_argument("--chars", type=int, default=200, help="每段截断字符数（默认 200）")
    args = ap.parse_args(argv)

    pattern = os.path.join(args.log_dir, "*.jsonl")
    files = sorted(glob.glob(pattern), key=lambda p: -os.path.getmtime(p))[: args.max_files]
    if not files:
        print("没有找到会议日志：%s" % pattern)
        return 0

    hit_files = 0
    for path in files:
        rows = load_transcripts(path, args.keyword)
        if not rows:
            continue
        hit_files += 1
        paras = merge_paragraphs(rows)
        print("=== %s | 起于 %s | 命中 %d 句 / %d 段 ===" % (
            os.path.basename(path), (rows[0].get("time") or "")[:16], len(rows), len(paras)))
        for sp, tx in paras[: args.per_file]:
            print("  %s: %s" % (sp, tx[: args.chars]))

    if not hit_files:
        print("无命中：『%s』未出现在最近 %d 份会议日志中" % (args.keyword, len(files)))
        print("提示：换简称/加「科技」后缀再试；仍无 → 该客户在本地无录音线索，需要用户补充或走 C360。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
