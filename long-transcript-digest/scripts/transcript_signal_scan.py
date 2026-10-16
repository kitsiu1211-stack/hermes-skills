#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transcript_signal_scan.py —— 长字幕/逐字稿的「冲突与需求信号」零成本扫描器

用途：会前调词表 / 会后复盘 / 补救漏报。只读、零 token、不推送。
规则集端口自已验证的会议雷达（feishu-meeting-listen/scripts/meeting_radar.py）。

用法：
  python3 transcript_signal_scan.py ~/meeting_logs/<id>.jsonl
  python3 transcript_signal_scan.py <id>.jsonl --per-rule 5 --top 40
  python3 transcript_signal_scan.py /tmp/xxx.txt          # 纯文本也吃（行格式「说话人：内容」）
  python3 transcript_signal_scan.py <file> --json         # 机器可读，便于二次筛选

注意：本脚本**不做去重/冷却的推送抑制**——它是给人看的候选清单，命中越多越好过目。
"""

import argparse
import json
import os
import re
import sys

# (规则id, 级别, 说明, 正则, 建议动作)
RULES = [
    ("hostile_push", "🔴", "审判式/打断式发问",
     r"做不到|做不了|不支持|不能做到|没有得聊|别讲这些|不要讲|不用讲|不要给我讲|直接回答我|"
     r"是和不是|给我个准话|你听我说|打断一下|节省我的时间|讲干货|不要绕|不要引导|"
     r"能不能做到|你的工具.*能不能|我要的是|你现在就|快说|不要老",
     "别逐条口头答辩，改书面逐项应答（真不支持/需配置/需集成+插件）"),
    ("mainline_blocked", "🔴", "我方主线被当面否掉",
     r"不谈\s*AI|不讲\s*AI|不要讲\s*AI|别聊\s*AI|不要提\s*AI|AI\s*不可控|不要老引导",
     "差异点被封口 → 换赛道讲可配置项清单 + 实施工作量"),
    ("competitor", "🟠", "竞品与选型",
     r"Jira|JIRA|PingCode|千问|WorkBuddy|Workbody|Gemini|Atlassian|禅道|TAPD|Teambition|Linear|选型",
     "记竞品项，会后拉竞品对比口径"),
    ("opportunity", "🔴", "商机/商务",
     r"预算|报价|多少钱|价格|单价|席位|采购|招标|比价|续约|合同到期|(?<!测)试用|PoC|立项|增购|"
     r"扩大规模|隐性成本|人力成本|工作量",
     "金额·时间点·决策链立刻记，会后建跟进日程"),
    ("decider", "🟠", "决策链/关键人",
     r"老板|董事长|CEO|COO|CTO|CIO|一号位|拍板|决策权|总监|VP|采购部|信息化部|大领导",
     "确认能否约到拍板人"),
    ("risk", "🔴", "风险（合规/迁移/陪标/评分不公）",
     r"安全合规|合规|等保|私有化|数据出境|迁移成本|迁移到|换掉|停用|陪标|不公允|"
     r"权重|评分标准|得分率|偏离表|隐性成本|选型.*(评审|对比)",
     "单独列风险与应对口径；疑似陪标先算投入产出"),
    ("our_gap", "🟠", "我方失手/给不出答案",
     r"给不出|给不了|我说实话|这个我不确定|需要确认|待验证|会后.*(答复|应答|视频|再给)|我来找找",
     "24h 内书面补答，别让它变成扣分项"),
    ("commitment", "🟠", "我方当场承诺",
     r"我回头|会后发|马上发|我今天就|我明天|我发你|发到群里|我拉个|我来建|我去确认",
     "入待办，会后逐条兑现并回告"),
    ("emotion", "🟠", "情绪/场压异常",
     r"干起来|看不下去|好困|离谱|无语|过分|没礼貌|别说了|吵什么",
     "换节奏（只答是/否 + 会后书面），必要时打断拉回议程"),
]

DEVICE_HINT = re.compile(r"🎦|会议室|坐席|\(\d+\)$|Center|Block")


def load_rows(path):
    """返回 [(time, speaker, text)]，JSONL 去重后按时间排序；纯文本按行解析。"""
    rows = []
    if path.endswith(".jsonl"):
        seen = set()
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") not in ("transcript", "chat"):
                    continue
                sid = d.get("sentence_id")
                if sid and sid in seen:
                    continue
                if sid:
                    seen.add(sid)
                rows.append((d.get("time") or "", d.get("speaker") or "?", (d.get("text") or "").strip()))
    else:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = re.match(r"^(\d{2}:\d{2}(?::\d{2})?)\s+(.+?)[：:]\s*(.*)$", line)
                if m:
                    rows.append((m.group(1), m.group(2), m.group(3)))
                else:
                    rows.append(("", "?", line))
    # 🚨 JSONL 行序 ≠ 时间序（poll.sh 每轮把新事件追加到末尾）→ 必须排序
    rows.sort(key=lambda r: r[0])
    return rows


def short_time(t):
    if not t:
        return "--:--:--"
    return t[11:19] if len(t) >= 19 and t[4] == "-" else t[-8:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--per-rule", type=int, default=3)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print("文件不存在: " + args.path)
        return 1

    rows = load_rows(args.path)
    if not rows:
        print("没有解析到任何语句，确认文件格式（JSONL 或「说话人：内容」文本）")
        return 1

    speakers = {}
    device = 0
    for _t, s, _x in rows:
        speakers[s] = speakers.get(s, 0) + 1
        if DEVICE_HINT.search(s):
            device += 1

    print("=== 体检报告 ===")
    print("语句数: %d   时间范围: %s ~ %s" % (len(rows), short_time(rows[0][0]), short_time(rows[-1][0])))
    print("说话人 top: " + ", ".join("%s(%d)" % kv for kv in sorted(speakers.items(), key=lambda x: -x[1])[:8]))
    if device:
        print("⚠️ 会议室设备麦占比: %.0f%%（%d/%d）→ 归因需按内容推断并标注不确定" % (
            100.0 * device / len(rows), device, len(rows)))

    groups = {rid: [] for rid, _lv, _d, _rx, _a in RULES}
    compiled = [(rid, lv, desc, re.compile(rx), act) for rid, lv, desc, rx, act in RULES]
    for t, s, x in rows:
        if len(x) < 4:
            continue
        for rid, lv, desc, rx, act in compiled:
            if rx.search(x):
                groups[rid].append({"time": short_time(t), "speaker": s, "text": x, "level": lv, "desc": desc})

    if args.json:
        print(json.dumps({k: v for k, v in groups.items() if v}, ensure_ascii=False, indent=1))
        return 0

    total = 0
    for rid, lv, desc, _rx, act in compiled:
        hits = groups[rid]
        if not hits:
            continue
        total += len(hits)
        print("\n=== %s %s [%s] %d 处 ===" % (lv, desc, rid, len(hits)))
        print("👉 " + act)
        for h in hits[: args.per_rule]:
            print("  [%s] %s：%s" % (h["time"], h["speaker"], h["text"][:110]))
        if len(hits) > args.per_rule:
            print("  …另有 %d 处（--per-rule 调大看全）" % (len(hits) - args.per_rule))

    print("\n=== 合计命中 %d 处 ===" % total)
    print("回放数是给人过目用的：逐条判「该报/误报/漏报」→ 改词表 → 重复到误报≈0，再开实时推送。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
