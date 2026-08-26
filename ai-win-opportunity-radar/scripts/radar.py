#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 核心判定引擎（Generator + Evaluator）
基于 C360 tenant_metrics 真实数据，按主题34升级信号清单判定商机机会。
用法: python3 radar.py --account-id <account_id>   # 单客户测试
      python3 radar.py --owner <owner_id>          # 扫描名下全部客户
      python3 radar.py --demo                      # 用内置示例数据演示
"""
import json
import os
import subprocess
import sys
import datetime

# ── 配置 ──
LARK_C360 = "lark-c360"
C360_ENV = "online"

# 关键字段（tenant_metrics）
FIELDS = [
    "ai_credits_usage_rate",          # 当前消耗进度 %
    "ai_credits_usage_rate_predict",  # 预计到期消耗进度 %
    "ai_credits_quota_remaining_days",    # 预计剩余天数
    "ai_credits_quota_actual_remaining_days",  # 实际剩余天数
    "ai_credits_usage_mom",           # 用量月环比 %
    "ai_credits_asset_time_rate",     # 时间进度 %
    "tenant_ai_credits_arr",          # AI 通用额度 ARR
    "ai_arpu",                        # 人均 AI 消耗
    "ai_dau_avg_7workday",            # AI DAU 近7日均值
    "ai_dau_avg_7workday_wow",        # AI DAU 环比
    "knowledge_ai_dau",               # 知识问答 DAU
    "nexus_bot_dau",                  # 豆包工作伙伴 DAU
    "base_ai_dau",                    # 多维表格 AI DAU
    "vc_ai_dau",                      # 智能纪要 DAU
]

# ── 升级信号清单阈值（来自主题34，可调）──
THRESHOLDS = {
    "entry_upgrade_predict": 1.50,   # 入门档→9.9万: predict > 150%
    "entry_rate_time_ratio": 2.0,    # 入门档: 消耗率/时间进度 ≥ 2
    "mid_upgrade_predict": 2.00,     # 9.9万→29.7万: predict > 200%
    "mid_rate_high": 0.80,           # 消耗率 > 80%
    "mid_mom_high": 0.50,            # 月环比 > 50%
    "high_upgrade_predict": 3.00,    # 29.7万→99万: predict > 300%
    "high_dau_thousand": 800,        # 激活人数近千级
    "high_rate_floor": 0.70,         # 消耗率 > 70%
    "strong_predict": 3.00,          # 强信号
    "strong_days": 15,               # 强信号: 剩余 < 15 天
    "mid_days": 30,                  # 中信号: 剩余 < 30 天
}

# 档位识别（按 ARR）
def detect_tier(arr):
    if arr is None or arr <= 0:
        return None
    if arr < 90000:
        return "entry"       # 入门档（9900 包）
    elif arr < 297000:
        return "mid"         # 9.9 万档
    elif arr < 990000:
        return "high"        # 29.7 万档
    else:
        return "flagship"    # 99 万档

TIER_LABEL = {"entry": "入门档(9900)", "mid": "9.9万档", "high": "29.7万档", "flagship": "99万档"}
UPGRADE_TARGET = {"entry": "9.9万", "mid": "29.7万", "high": "99万", "flagship": None}

def fmt_pct(v):
    """百分数 → 显示（0.798 -> 79.98%）"""
    if v is None:
        return "N/A"
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return str(v)

# ── Generator：数据拉取 ──
def fetch_tenant_metrics(tenant_id):
    """拉取指定租户的 AI 使用数据，返回 {field: value}"""
    cmd = [LARK_C360, "tenant", "metrics", "get", "--tenant-id", tenant_id,
           "--env", C360_ENV]
    for f in FIELDS:
        cmd += ["--field", f]
    cmd += ["--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    entity = d.get("data", {}).get("entity", {})
    if not entity:
        return None
    result = {}
    for f in FIELDS:
        v = entity.get(f, {})
        if isinstance(v, dict):
            result[f] = v.get("value")
        else:
            result[f] = v
    return result

def fetch_account_usage(account_id):
    """C360 自带信号（机会/风险/到期）"""
    cmd = [LARK_C360, "account", "+usage", "--id", account_id, "--env", C360_ENV, "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    lst = d.get("data", {}).get("list", [])
    if not lst:
        return None
    item = lst[0]
    return {
        "opportunity": item.get("opportunity_list", {}).get("value", "[]"),
        "risk": item.get("risk_list", {}).get("value", "[]"),
        "exp_soon": item.get("exp_soon_list", {}).get("value", "[]"),
    }

# ── Generator：信号判定 ──
def judge_signals(metrics, usage=None):
    """按信号清单判定，返回机会条目（每条带数据引用）"""
    if not metrics:
        return None, "无 AI 使用数据（可能无 AI 额度）"

    tier = detect_tier(_num(metrics.get("tenant_ai_credits_arr")))
    if tier is None:
        return None, "无 AI ARR 数据"

    target = UPGRADE_TARGET[tier]
    if target is None:
        return None, "已是旗舰档(99万)，无常规升级方向"

    rate = _num(metrics.get("ai_credits_usage_rate"))
    predict = _num(metrics.get("ai_credits_usage_rate_predict"))
    days_left = _num(metrics.get("ai_credits_quota_remaining_days"), int)
    time_rate = _num(metrics.get("ai_credits_asset_time_rate"))
    mom = _num(metrics.get("ai_credits_usage_mom"))
    dau = _num(metrics.get("ai_dau_avg_7workday"))
    dau_wow = _num(metrics.get("ai_dau_avg_7workday_wow"))

    signals = []       # 命中的信号（带数据引用）
    strength = None    # 强/中/弱

    # 各档位判定
    if tier == "entry":
        if predict is not None and predict > THRESHOLDS["entry_upgrade_predict"]:
            signals.append(f"预计到期消耗 {fmt_pct(predict)}（阈值 150%）→ 严重超标")
        if rate is not None and time_rate and time_rate > 0 and rate / time_rate >= THRESHOLDS["entry_rate_time_ratio"]:
            signals.append(f"消耗率 {fmt_pct(rate)} 是时间进度 {fmt_pct(time_rate)} 的 {rate/time_rate:.1f} 倍")
        if days_left is not None and days_left < THRESHOLDS["mid_days"]:
            signals.append(f"预计剩余 {days_left} 天（<30 天告急）")
    elif tier == "mid":
        if predict is not None and predict > THRESHOLDS["mid_upgrade_predict"]:
            signals.append(f"预计到期消耗 {fmt_pct(predict)}（阈值 200%）→ 提前用完")
        if rate is not None and rate > THRESHOLDS["mid_rate_high"] and mom is not None and mom > THRESHOLDS["mid_mom_high"]:
            signals.append(f"消耗率 {fmt_pct(rate)} + 月环比 {fmt_pct(mom)} → 用量加速")
        if days_left is not None and days_left < THRESHOLDS["mid_days"] and dau_wow is not None and dau_wow > 0:
            signals.append(f"剩余 {days_left} 天 + AI DAU 环比 {fmt_pct(dau_wow)} → 场景在长")
    elif tier == "high":
        if predict is not None and predict > THRESHOLDS["high_upgrade_predict"]:
            signals.append(f"预计到期消耗 {fmt_pct(predict)}（阈值 300%）→ 一年要 3 个包")
        if dau is not None and dau > THRESHOLDS["high_dau_thousand"]:
            signals.append(f"AI DAU {dau:.0f} 人（近千级）")
        if rate is not None and rate > THRESHOLDS["high_rate_floor"]:
            signals.append(f"消耗率 {fmt_pct(rate)}（>70%）")

    # 强度分级
    if predict is not None and predict > THRESHOLDS["strong_predict"]:
        strength = "🔴 强"
    elif days_left is not None and days_left < THRESHOLDS["strong_days"]:
        strength = "🔴 强"
    elif predict is not None and predict > THRESHOLDS["mid_upgrade_predict"]:
        strength = "🟡 中"
    elif days_left is not None and days_left < THRESHOLDS["mid_days"]:
        strength = "🟡 中"
    elif dau_wow is not None and dau_wow > 0:
        strength = "🟢 弱"
    else:
        strength = "🟢 弱"

    if not signals:
        return None, f"无升级信号（消耗率 {fmt_pct(rate)}，预计到期 {fmt_pct(predict)}）"

    return {
        "tier": tier,
        "tier_label": TIER_LABEL[tier],
        "target": target,
        "signals": signals,
        "strength": strength,
        "evidence": {
            "rate": fmt_pct(rate),
            "predict": fmt_pct(predict),
            "days_left": days_left,
            "mom": fmt_pct(mom),
            "dau": dau,
            "dau_wow": fmt_pct(dau_wow),
        },
        "usage": usage,
    }, None

def _num(v, cast=float):
    if v is None or v == "":
        return None
    try:
        s = str(v).strip().strip('"')
        if not s:
            return None
        return cast(s)
    except (TypeError, ValueError):
        return None

# ── Evaluator：独立校验 ──
def evaluator_check(opportunity, metrics):
    """校验：数据存在性 / 计算正确性 / 信号强度。返回 (是否通过, 问题列表)"""
    problems = []
    if opportunity is None:
        return True, []
    ev = opportunity.get("evidence", {})
    # 1. 数据存在性
    required = ["rate", "predict"]
    for k in required:
        if ev.get(k) in (None, "N/A"):
            problems.append(f"缺关键数据: {k}")
    # 2. 计算正确性：predict 强度分级一致性
    predict_raw = _num(metrics.get("ai_credits_usage_rate_predict"))
    days_left_raw = _num(metrics.get("ai_credits_quota_remaining_days"), int)
    strength = opportunity.get("strength", "")
    if predict_raw is not None:
        if "强" in strength and predict_raw < 1.5 and (days_left_raw or 999) >= 15:
            problems.append(f"强度标为强但 predict={fmt_pct(predict_raw)} 未达强阈值")
    # 3. 信号必须有数据支撑
    if not opportunity.get("signals"):
        problems.append("无信号明细")
    return len(problems) == 0, problems

# ── 主流程 ──
def run_for_account(account_id, tenant_id=None):
    """单客户全流程：拉数据 → Generator 判定 → Evaluator 校验"""
    # tenant_id 未提供时尝试从 account 拿
    if tenant_id is None:
        # 从 account +usage 拿 tenant_id
        usage = fetch_account_usage(account_id)
        tenant_id = usage.get("tenant_id") if usage else None
    else:
        usage = fetch_account_usage(account_id)

    metrics = fetch_tenant_metrics(tenant_id) if tenant_id else None
    opp, note = judge_signals(metrics, usage)
    ok, problems = evaluator_check(opp, metrics) if metrics else (False, ["无数据"])

    return {
        "account_id": account_id,
        "tenant_id": tenant_id,
        "opportunity": opp,
        "note": note,
        "evaluator": {"passed": ok, "problems": problems},
    }

def demo():
    """汉阳实测数据演示"""
    metrics = {
        "ai_credits_usage_rate": 0.7998,
        "ai_credits_usage_rate_predict": 5.6727,
        "ai_credits_quota_remaining_days": 14,
        "ai_credits_quota_actual_remaining_days": 364,
        "ai_credits_usage_mom": 0.9578,
        "ai_credits_asset_time_rate": 0.05,
        "tenant_ai_credits_arr": 49500,
        "ai_arpu": 0.33,
        "ai_dau_avg_7workday": 302.29,
        "ai_dau_avg_7workday_wow": None,
        "knowledge_ai_dau": 162,
        "nexus_bot_dau": 93,
        "base_ai_dau": 71,
        "vc_ai_dau": 127,
    }
    opp, note = judge_signals(metrics)
    ok, problems = evaluator_check(opp, metrics)
    print("=== 汉阳实测数据判定 ===")
    print(f"客户: 深圳汉阳科技")
    print(f"判定: {note if opp is None else opp['strength']} 信号 | {opp['tier_label']} → {opp['target']}" if opp else f"判定: {note}")
    if opp:
        print(f"档位: {opp['tier_label']} → 建议升级 {opp['target']}")
        print("信号依据:")
        for s in opp["signals"]:
            print(f"  • {s}")
        print(f"证据: 消耗率={opp['evidence']['rate']} predict={opp['evidence']['predict']} 剩余={opp['evidence']['days_left']}天 月环比={opp['evidence']['mom']}")
    print(f"Evaluator: {'✅ 通过' if ok else '❌ ' + '; '.join(problems)}")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    elif "--account-id" in sys.argv:
        idx = sys.argv.index("--account-id")
        aid = sys.argv[idx + 1]
        result = run_for_account(aid)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(__doc__)
