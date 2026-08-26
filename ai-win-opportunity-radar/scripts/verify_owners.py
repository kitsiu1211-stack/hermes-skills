#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证名下客户归属：从 opportunity 枚举候选 account → 逐个 account get 验证当前 owner
输出：真正的名下客户（owner == 袁鑫杰）
"""
import json
import subprocess
import sys
import os
import datetime

MY_OWNER = "袁鑫杰"
# 个人 C360 user id：优先从环境变量读，避免硬编码敏感信息
MY_OWNER_ID = os.environ.get("C360_OWNER_ID", "005BB000000Hg80YAC")

def get_account_owner(account_id):
    """查 account 当前 owner"""
    r = subprocess.run(
        ["lark-c360", "account", "get", "--id", account_id,
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
    owner = ent.get("owner_id", {}).get("display_value", "?")
    owner_val = ent.get("owner_id", {}).get("value", "").strip('"')
    name = ent.get("name", {}).get("display_value", "?")
    return {"owner": owner, "owner_val": owner_val, "name": name}

def list_candidate_accounts(limit_page=100):
    """从 opportunity 枚举候选客户（历史+当前）"""
    accounts = {}
    offset = 0
    while True:
        r = subprocess.run(
            ["lark-c360", "opportunity", "list",
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
            break
        lst = d.get("data", {}).get("list", [])
        if not lst:
            break
        for it in lst:
            owner = it.get("owner_id", {}).get("display_value", "")
            if owner != MY_OWNER:
                continue
            acct_id = it.get("account_id", {}).get("value", "").strip('"') or it.get("account_id", {}).get("display_value", "")
            if not acct_id:
                continue
            if acct_id not in accounts:
                accounts[acct_id] = {
                    "id": acct_id,
                    "name": it.get("account_name", {}).get("display_value", ""),
                    "tenant_id": it.get("service_tenant_id", {}).get("display_value", "").split("-")[0],
                }
        offset += limit_page
        if offset > 3000:
            break
    return list(accounts.values())

def main():
    print("=== 验证名下客户归属 ===", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    candidates = list_candidate_accounts()
    print(f"候选客户（商机维度）: {len(candidates)}")

    mine = []
    not_mine = []
    for i, acct in enumerate(candidates, 1):
        info = get_account_owner(acct["id"])
        if info is None:
            print(f"[{i}/{len(candidates)}] {acct['name']}: 查询失败")
            continue
        is_mine = info["owner"] == MY_OWNER or info["owner_val"] == MY_OWNER_ID
        if is_mine:
            mine.append({**acct, "owner": info["owner"]})
        else:
            not_mine.append({**acct, "owner": info["owner"]})
            print(f"  ⚠️ 已转走: {acct['name']} → owner={info['owner']}")

    print(f"\n=== 结果 ===")
    print(f"真正名下客户: {len(mine)}")
    print(f"已不在名下: {len(not_mine)}")
    for a in not_mine[:30]:
        print(f"  {a['name']} → {a['owner']}")

    out = {"verified_at": datetime.datetime.now().isoformat(), "mine": mine, "not_mine": not_mine}
    with open("/tmp/mine_accounts.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已保存: /tmp/mine_accounts.json")

if __name__ == "__main__":
    main()
