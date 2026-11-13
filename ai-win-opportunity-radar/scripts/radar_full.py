#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 全流程（枚举 AI 客户 → 拉数据 → Generator 判定 → Evaluator 校验 → 汇总）
枚举逻辑：名下活跃商机（非丢单/退订）中含 AI 产品（feishu_ai_* 等）的客户
用法: python3 radar_full.py [--limit N]
"""
import json
import subprocess
import shutil
import sys
import os
import re
import datetime

# C360 可执行文件：优先 C360_BIN（跨环境适配），否则 PATH，最后兜底本机 npm 路径
C360 = (os.environ.get("C360_BIN")
        or shutil.which("lark-c360")
        or os.path.expanduser("~/.npm-global/bin/lark-c360"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location("radar", os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar.py"))
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)

MY_OWNER = "袁鑫杰"
# 个人 C360 user id：优先从环境变量读，避免硬编码敏感信息
MY_OWNER_ID = os.environ.get("C360_OWNER_ID", "005BB000000Hg80YAC")
AI_PREFIX = ("feishu_ai_", "ai_", "aily", "nexus_bot", "vc_ai", "meego_ai", "base_ai", "miaoda", "openclaw")

def _err_code(blob):
    m = re.search(r"code=(\d+)", blob or "")
    return m.group(1) if m else None

def preflight_auth():
    """开跑前校验 C360 会话 + 网关；区分「过期需授权」和「100001 白名单拦截」，
    两者都必须硬失败，否则会被当成「0 个客户」静默吞掉。"""
    r = subprocess.run([C360, "auth", "status", "--json"],
                       capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout[r.stdout.find('{'):])
    except json.JSONDecodeError:
        print("❌ 无法解析 lark-c360 auth status 输出，请先执行 lark-c360 auth login", file=sys.stderr)
        sys.exit(2)
    if not d.get("logged_in"):
        exp = d.get("expires_at")
        exp_s = datetime.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M") if isinstance(exp, int) else "未知"
        print(f"❌ C360 会话不可用（logged_in=false，expires_at={exp_s}）。"
              f"请人工执行 lark-c360 auth login 后重跑。", file=sys.stderr)
        sys.exit(2)

    # 真实探针：auth status 显示有效 ≠ 能取数（2026-11-09 二次踩坑）
    probe = subprocess.run([C360, "account", "list", "--limit", "1", "--json"],
                           capture_output=True, text=True, timeout=30)
    blob = (probe.stdout or "") + (probe.stderr or "")
    code = _err_code(blob)
    if code == "100001":
        _exp = d.get("expires_at")
        _exp_s = datetime.datetime.fromtimestamp(_exp).strftime("%Y-%m-%d %H:%M") if isinstance(_exp, (int, float)) else str(_exp)
        print("❌ C360 网关拦截 code=100001（安全检测 / Agent 白名单）。"
              "auth status 有效（expires_at=%s）也没用——重新授权无效。"
              "处置：向 C360-CLI 反馈群申请加白，或改用官方允许的客户端执行；"
              "不得伪造结果。" % _exp_s, file=sys.stderr)
        sys.exit(4)
    if "session expired" in blob.lower():
        print("❌ C360 会话已过期（session expired），需人工 lark-c360 auth login 后重跑。", file=sys.stderr)
        sys.exit(2)
    if not blob.strip():
        print("⚠️ C360 探针无输出，继续尝试主流程", file=sys.stderr)

def list_ai_accounts(limit_page=100):
    """枚举名下含 AI 产品的客户：
    1. opportunity 拉候选（owner_id == 我 且 含 AI 产品）
    2. account get 逐个验证当前 owner_id 仍是我（排除历史已转走客户）
    """
    candidates = {}
    offset = 0
    while True:
        r = subprocess.run(
            [C360, "opportunity", "list",
             "--field", "id", "--field", "account_name", "--field", "account_id",
             "--field", "owner_id", "--field", "service_tenant_id", "--field", "stage",
             "--field", "product_sku_keys",
             "--limit", str(limit_page), "--offset", str(offset), "--json"],
            capture_output=True, text=True, timeout=90,
        )
        try:
            d = json.loads(r.stdout[r.stdout.find('{'):])
        except json.JSONDecodeError:
            break
        if not d.get("ok"):
            msg = (d.get("error") or {}).get("message", "unknown")
            if offset == 0:
                raise RuntimeError(f"opportunity list 失败（首页即报错）: {msg}")
            print(f"⚠️ opportunity list 分页在第 {offset} 条中断: {msg}", file=sys.stderr)
            break
        lst = d.get("data", {}).get("list", [])
        if not lst:
            break
        for it in lst:
            owner = it.get("owner_id", {}).get("display_value", "")
            if owner != MY_OWNER:
                continue
            stage_raw = it.get("stage", {}).get("display_value", "")
            try:
                stage = json.loads(stage_raw).get("label", "") if stage_raw else ""
            except Exception:
                stage = stage_raw
            if stage in ("丢单", "已退订"):
                continue
            acct_id = it.get("account_id", {}).get("value", "").strip('"') or it.get("account_id", {}).get("display_value", "")
            if not acct_id:
                continue
            prods_raw = it.get("product_sku_keys", {}).get("value", "[]")
            try:
                p_list = json.loads(prods_raw)
            except Exception:
                p_list = []
            ai_prods = [p for p in p_list if p.startswith(AI_PREFIX)]
            if not ai_prods:
                continue  # 只保留含 AI 产品的客户
            if acct_id not in candidates:
                candidates[acct_id] = {
                    "id": acct_id,
                    "name": it.get("account_name", {}).get("display_value", ""),
                    "tenant_id": it.get("service_tenant_id", {}).get("display_value", "").split("-")[0],
                    "ai_products": ai_prods,
                }
        offset += limit_page
        if offset > 3000:
            break

    # 逐个验证 account 当前 owner（排除历史已转走客户）
    accounts = []
    for acct in candidates.values():
        info = verify_owner(acct["id"])
        if info is None:
            continue
        is_mine = info["owner"] == MY_OWNER or info["owner_val"] == MY_OWNER_ID
        if is_mine:
            accounts.append(acct)
    return accounts

def verify_owner(account_id):
    """查 account 当前 owner，返回 {owner, owner_val, name} 或 None"""
    r = subprocess.run(
        [C360, "account", "get", "--id", account_id,
         "--field", "id", "--field", "name", "--field", "owner_id", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    try:
        d = json.loads(r.stdout[r.stdout.find('{'):])
    except json.JSONDecodeError:
        return None
    ent = d.get("data", {})
    if not ent or "id" not in ent:
        return None
    return {
        "owner": ent.get("owner_id", {}).get("display_value", "?"),
        "owner_val": ent.get("owner_id", {}).get("value", "").strip('"'),
        "name": ent.get("name", {}).get("display_value", "?"),
    }

def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    print("=== AI 赢单商机雷达 ===", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    preflight_auth()
    accounts = list_ai_accounts()
    print(f"名下 AI 客户数: {len(accounts)}")
    if limit:
        accounts = accounts[:limit]
        print(f"本次扫描: {len(accounts)} 个")

    findings = []
    skipped = 0
    for acct in accounts:
        tenant_id = acct["tenant_id"]
        if not tenant_id:
            skipped += 1
            continue
        try:
            metrics = radar.fetch_tenant_metrics(tenant_id)
        except Exception:
            metrics = None
        if not metrics:
            skipped += 1
            continue
        opp, note = radar.judge_signals(metrics)
        ok, problems = radar.evaluator_check(opp, metrics)
        if opp:
            findings.append({
                "account_id": acct["id"],
                "account_name": acct["name"],
                "tenant_id": tenant_id,
                "ai_products": acct["ai_products"],
                "opportunity": opp,
                "evaluator": {"passed": ok, "problems": problems},
            })
            print(f"🟢 {acct['name']}: {opp['strength']} | {opp['tier_label']} → {opp['target']} | predict={opp['evidence']['predict']} 剩余={opp['evidence']['days_left']}天")
        else:
            print(f"⚪ {acct['name']}: 无信号 ({note})")

    print(f"\n=== 汇总 ===")
    print(f"扫描: {len(accounts)} | 有信号: {len(findings)} | 无数据/无信号跳过: {skipped}")
    strong = [f for f in findings if "强" in f["opportunity"]["strength"]]
    mid = [f for f in findings if "中" in f["opportunity"]["strength"]]
    weak = [f for f in findings if "弱" in f["opportunity"]["strength"]]
    print(f"🔴 强信号: {len(strong)} | 🟡 中信号: {len(mid)} | 🟢 弱信号: {len(weak)}")

    out = {
        "generated_at": datetime.datetime.now().isoformat(),
        "scan_count": len(accounts),
        "findings": findings,
    }
    with open("/tmp/radar_result.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("结果已保存: /tmp/radar_result.json")

if __name__ == "__main__":
    main()
