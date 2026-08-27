#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 跟进记录扫描器（V2 新增）
读取 /tmp/radar_result.json 的信号客户 → 逐个拉 C360 follow_up 近14天记录 → 过滤 AI 相关 → 保存 /tmp/radar_followups.json

用法: python3 fetch_followups.py [--days 14] [--limit 30]
输出: /tmp/radar_followups.json
  {
    "<account_name>": {
      "ai_hits": [{"date": "2026-08-26", "content": "..."}, ...],   # 近14天含AI关键词的记录(最多3条)
      "any_followup": true/false,   # 近14天是否有任何跟进记录(AI与否)
      "total_14d": N                # 近14天跟进总条数
    }
  }
"""
import json
import subprocess
import os
import sys
import datetime

C360 = os.path.expanduser("~/.npm-global/bin/lark-c360")

# AI 相关关键词（命中即视为 AI 跟进）
AI_KW = ["ai", "AI", "豆包", "智能", "知识库", "机器人", "额度", "消耗", "用量", "模型", "纪要",
         "多维", "助手", "工作伙伴", "大模型", "激活", "训练", "场景", "升级", "采购", "续费",
         "到期", "演示", "培训"]

CONTENT_CAP = 500  # 每条内容截断长度，控制 token


def parse_days():
    days = 14
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    return days


def fetch_followups(account_id, cutoff, limit=30):
    """拉取跟进记录，返回 (近14天全部, 近14天AI命中)"""
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
        return [], []
    recent = []
    for it in lst:
        fd = str(it.get("follow_date", {}).get("display_value", ""))[:10]
        if not fd or fd < cutoff:
            continue
        content = it.get("content", {}).get("display_value", "") or ""
        recent.append({"date": fd, "content": content})
    ai_hits = [rec for rec in recent if any(kw in rec["content"] for kw in AI_KW)]
    return recent, ai_hits


def main():
    days = parse_days()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    print(f"=== 跟进记录扫描 ===", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print(f"时间窗口: 近 {days} 天 (>= {cutoff})")

    with open("/tmp/radar_result.json") as f:
        result = json.load(f)
    findings = result.get("findings", [])
    print(f"信号客户数: {len(findings)}")

    out = {}
    for f in findings:
        name = f["account_name"]
        acct_id = f["account_id"]
        recent, ai_hits = fetch_followups(acct_id, cutoff)
        entry = {
            "ai_hits": [{"date": h["date"], "content": h["content"][:CONTENT_CAP]} for h in ai_hits[:3]],
            "any_followup": len(recent) > 0,
            "total_14d": len(recent),
        }
        out[name] = entry
        status = f"AI跟进 {len(ai_hits)} 条" if ai_hits else ("有跟进无AI话题" if recent else "无跟进记录")
        print(f"  {name}: {status} (近14天共{len(recent)}条)")

    with open("/tmp/radar_followups.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n已保存: /tmp/radar_followups.json")


if __name__ == "__main__":
    main()
