#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluator 独立校验：从 C360 重新拉取关键字段，与 radar_result.json 比对（数据存在性 + 计算正确性）"""
import json
import subprocess

FIELDS = [
    "ai_credits_usage_rate", "ai_credits_usage_rate_predict",
    "ai_credits_quota_remaining_days", "ai_credits_asset_time_rate",
    "ai_credits_usage_mom", "tenant_ai_credits_arr", "ai_arpu",
    "ai_dau_avg_7workday", "ai_credits_quota_actual_remaining_days",
]

res = {f["account_name"]: f for f in json.load(open("/tmp/radar_result.json"))["findings"]}
names = [
    "深圳市零壹创新科技有限公司", "深圳市相当顺科技有限公司", "未知星球科技（东莞）有限公司",
    "深圳汉阳科技有限公司", "广州疆海科技有限公司", "深圳市凯迪仕智能科技股份有限公司",
    "深圳市多科电子有限公司", "深圳市智能派科技有限公司", "深圳出版集团有限公司",
    "广东高驰运动科技有限公司", "摩米士科技（深圳）有限公司",
]

for n in names:
    f = res.get(n)
    if not f:
        print(n, "NOT IN RESULT")
        continue
    tid = f["tenant_id"]
    cmd = ["lark-c360", "tenant", "metrics", "get", "--tenant-id", tid, "--json"]
    for fld in FIELDS:
        cmd += ["--field", fld]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(r.stdout)["data"]["entity"]
    except Exception as e:
        print(n, "PARSE_FAIL", r.stdout[:200], r.stderr[:200])
        continue
    def g(k):
        v = d.get(k)
        return v.get("display_value") if isinstance(v, dict) else None
    print(f"--- {n} ({tid})")
    print("   rate=%s predict=%s days_left=%s time_rate=%s actual_days=%s mom=%s arr=%s arpu=%s dau=%s" % (
        g("ai_credits_usage_rate"), g("ai_credits_usage_rate_predict"), g("ai_credits_quota_remaining_days"),
        g("ai_credits_asset_time_rate"), g("ai_credits_quota_actual_remaining_days"), g("ai_credits_usage_mom"),
        g("tenant_ai_credits_arr"), g("ai_arpu"), g("ai_dau_avg_7workday")))
    ev = f["opportunity"]["evidence"]
    print("   radar: rate=%s predict=%s days_left=%s mom=%s dau=%s" % (
        ev.get("rate"), ev.get("predict"), ev.get("days_left"), ev.get("mom"), ev.get("dau")))
