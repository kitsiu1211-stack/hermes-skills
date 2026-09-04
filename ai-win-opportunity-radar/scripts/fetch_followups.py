#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 跟进记录扫描器（V3.1：基线建档一次，之后每周只跑增量）

设计（2026-08-27 用户定调）：
  - 基线只跑一次：首次扫描客户时建 180 天基线档案 → 持久化到 ~/.hermes/radar_baseline.json
  - 之后每周只检查新数据（近 14 天增量）；基线文件自动复用
  - 新客户进雷达（基线档案里没有）→ 自动补拉该客户 180 天基线并入档

用法:
  python3 fetch_followups.py --baseline [--limit 120]   # 首次建档（全量180天）
  python3 fetch_followups.py [--days 14] [--limit 30]   # 每周增量（自动补缺失客户基线）
输出:
  /tmp/radar_followups.json      增量摘要（卡片用，V2 结构不变）
  ~/.hermes/radar_baseline.json  基线档案（持久化，Agent 读它做判断）
    {
      "<account_name>": {
        "total_in_window": N,
        "ai_hits": [{"date": "...", "content": "..."}],   # 最多15条×500字符
        "timeline": [{"date": "...", "snippet": "..."}],  # 非AI记录, 最多40条×90字符
        "exclude_signals": [...],                          # 出海/海外/IM/钉钉等排除信号, 最多5条
        "any_followup": bool,
        "latest_date": "..."
      }
    }
"""
import json
import subprocess
import os
import sys
import datetime

C360 = os.path.expanduser("~/.npm-global/bin/lark-c360")
BASELINE_PATH = os.path.expanduser("~/.hermes/radar_baseline.json")

# AI 相关关键词（命中即视为 AI 跟进）
AI_KW = ["ai", "AI", "豆包", "智能", "知识库", "机器人", "额度", "消耗", "用量", "模型", "纪要",
         "多维", "助手", "工作伙伴", "大模型", "激活", "训练", "场景", "升级", "采购", "续费",
         "到期", "演示", "培训"]
# 排除信号关键词：判定「不该推进」的客户
EXCLUDE_KW = ["出海", "海外", "IM", "钉钉", "企微", "企业微信", "国际", "全球"]

CONTENT_CAP = 500   # AI 命中内容截断
SNIPPET_CAP = 90    # 时间线条目截断
MAX_AI_HITS = 15    # 每个客户最多保留的 AI 命中条数
MAX_TIMELINE = 40   # 每个客户最多保留的非 AI 时间线条目


def parse_args():
    days = 14
    limit = 30
    baseline = False
    argv = sys.argv[1:]
    if "--baseline" in argv:
        baseline = True
        days = 180
        limit = max(limit, 100)
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    return days, limit, baseline


def fetch_followups(account_id, cutoff, limit):
    """拉取跟进记录，返回窗口内全部记录（按时间过滤）"""
    r = subprocess.run(
        [C360, "follow_up", "+recent", "--account-id", account_id,
         "--field", "follow_date", "--field", "content",
         "--limit", str(limit), "--json"],
        capture_output=True, text=True, timeout=90,
    )
    try:
        d = json.loads(r.stdout[r.stdout.find('{'):])
        lst = d.get("data", {}).get("list", [])
    except Exception:
        return []
    records = []
    for it in lst:
        fd = str(it.get("follow_date", {}).get("display_value", ""))[:10]
        if not fd or fd < cutoff:
            continue
        content = it.get("content", {}).get("display_value", "") or ""
        records.append({"date": fd, "content": content})
    return records


def build_entry(records, baseline, days):
    entry = {
        "total_in_window": len(records),
        "any_followup": len(records) > 0,
        "latest_date": records[0]["date"] if records else None,
        "window_days": days,
    }
    ai_hits = [rec for rec in records if any(kw in rec["content"] for kw in AI_KW)]
    entry["ai_hits"] = [
        {"date": h["date"], "content": h["content"][:CONTENT_CAP]}
        for h in ai_hits[:MAX_AI_HITS]
    ]
    if baseline:
        # 基线模式：非 AI 记录也保留摘要时间线（购买/签约/日常维护上下文）
        non_ai = [rec for rec in records if rec not in ai_hits]
        entry["timeline"] = [
            {"date": t["date"], "snippet": t["content"][:SNIPPET_CAP]}
            for t in non_ai[:MAX_TIMELINE]
        ]
        entry["exclude_signals"] = [
            {"date": h["date"], "content": h["content"][:CONTENT_CAP]}
            for h in records if any(kw in h["content"] for kw in EXCLUDE_KW)
        ][:5]
    else:
        entry["timeline"] = []
        entry["exclude_signals"] = []
    return entry


def load_baseline():
    if os.path.exists(BASELINE_PATH):
        try:
            with open(BASELINE_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_baseline(data):
    with open(BASELINE_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    days, limit, baseline = parse_args()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    mode = "半年基线建档" if baseline else f"近 {days} 天增量扫描"
    print(f"=== 跟进记录扫描 [{mode}] ===", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print(f"时间窗口: {days} 天 (>= {cutoff}), 单客户上限 {limit} 条")

    with open("/tmp/radar_result.json") as f:
        result = json.load(f)
    findings = result.get("findings", [])
    print(f"信号客户数: {len(findings)}")

    baseline_store = load_baseline() if not baseline else {}
    out = {}
    for f in findings:
        name = f["account_name"]
        acct_id = f["account_id"]
        # 增量模式：已有基线档案的客户不重跑 180 天，只拉增量
        if not baseline and name in baseline_store:
            records = fetch_followups(acct_id, cutoff, limit)
            entry = build_entry(records, False, days)
            out[name] = entry
            ai_n = len(entry["ai_hits"])
            print(f"  {name}: 增量 {entry['total_in_window']} 条, AI命中 {ai_n} 条 (基线复用)")
            continue
        # 建档模式 或 新客户：拉 180 天全量
        records = fetch_followups(acct_id, cutoff, limit)
        entry = build_entry(records, True, 180)
        out[name] = entry
        excl_n = len(entry.get("exclude_signals", []))
        tag = "建档" if baseline else "新客户补基线"
        print(f"  {name}: 窗口内 {entry['total_in_window']} 条, AI命中 {len(entry['ai_hits'])} 条" +
              (f", ⚠️排除信号 {excl_n} 条" if excl_n else "") + f" [{tag}]")

    # 增量模式：把新客户基线 merge 进档案
    if not baseline:
        new_entries = {k: v for k, v in out.items() if k not in baseline_store}
        if new_entries:
            baseline_store.update(new_entries)
            save_baseline(baseline_store)
            print(f"\n已合并 {len(new_entries)} 个新客户基线 → {BASELINE_PATH}")

    # 增量摘要写 /tmp（卡片用）；建档模式写持久化档案
    if baseline:
        save_baseline(out)
        print(f"\n已保存基线档案: {BASELINE_PATH} ({len(out)} 客户)")
        print(f"提示: 之后每周只需 python3 fetch_followups.py（自动复用基线+补新客户）")
    else:
        with open("/tmp/radar_followups.json", "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("\n已保存增量摘要: /tmp/radar_followups.json")


if __name__ == "__main__":
    main()
