#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 飞书卡片生成器
读取 /tmp/radar_result.json → 生成总览卡片 → 发送到 Home
"""
import json
import subprocess
import datetime
import os

# 目标飞书聊天 ID：优先从环境变量读（默认 Home 频道）
HOME_CHAT = os.environ.get("RADAR_HOME_CHAT", "oc_e2f79ec1614a1efe1ebcd7c679bb45a8")

def load_result():
    with open("/tmp/radar_result.json") as f:
        return json.load(f)

def build_card(result):
    findings = result["findings"]
    scan_count = result["scan_count"]
    strong = [f for f in findings if "强" in f["opportunity"]["strength"]]
    mid = [f for f in findings if "中" in f["opportunity"]["strength"]]
    weak = [f for f in findings if "弱" in f["opportunity"]["strength"]]

    # 排序：强 > 中 > 弱
    order = {"🔴 强": 0, "🟡 中": 1, "🟢 弱": 2}
    findings.sort(key=lambda f: order.get(f["opportunity"]["strength"], 9))

    elements = []
    # 顶部统计
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "default",
        "columns": [
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold>{scan_count}</font>\n<font size=14 color=blue>扫描客户</font>\n<font size=12 color=grey>名下客户去重</font>"}]},
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=red>{len(strong)}</font>\n<font size=14 color=red>强信号</font>\n<font size=12 color=grey>本周必须动作</font>"}]},
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=orange>{len(mid)}</font>\n<font size=14 color=orange>中信号</font>\n<font size=12 color=grey>本周安排接触</font>"}]},
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=green>{len(weak)}</font>\n<font size=14 color=green>弱信号</font>\n<font size=12 color=grey>观察跟进</font>"}]},
        ],
    })
    elements.append({"tag": "hr"})

    # 每个信号客户
    for i, f in enumerate(findings, 1):
        opp = f["opportunity"]
        lines = []
        lines.append(f"<font size=16 weight=bold>{i}. {f['account_name']} | {opp['strength']}</font>")
        lines.append(f"<font size=14>当前 <font weight=bold>{opp['tier_label']}</font> → 建议升级 <font weight=bold color=red>{opp['target']}</font></font>")
        for s in opp["signals"]:
            lines.append(f"📊 {s}")
        # 推荐动作（来自主题34打法库）
        action = recommend_action(opp)
        if action:
            lines.append(f"👉 {action}")
        elements.append({"tag": "markdown", "content": "\n".join(lines)})
        elements.append({"tag": "hr"})

    # 底部说明
    generated = result.get("generated_at", "")
    try:
        dt = datetime.datetime.fromisoformat(generated)
        time_str = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        time_str = generated
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"数据源：C360 tenant_metrics（只读）| 抓取时间：{time_str} | Evaluator 校验：{len(findings)} 条全部通过 | 阈值：主题34 升级信号清单 V3.1"}],
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📡 AI 赢单商机雷达 | {datetime.datetime.now().strftime('%m-%d')} 扫描"},
            "template": "red" if strong else ("orange" if mid else "blue"),
        },
        "elements": elements,
    }
    return card

def recommend_action(opp):
    """根据档位和信号推荐动作（来自主题34打法）"""
    tier = opp["tier"]
    target = opp["target"]
    signals = opp["signals"]
    strength = opp["strength"]

    if "强" in strength:
        urgency = "🔴 本周必须动作："
    elif "中" in strength:
        urgency = "🟡 本周安排接触："
    else:
        urgency = "🟢 观察跟进："

    if tier == "entry":
        return f"{urgency}约 AI 第一负责人（CIO/技术负责人），带用量测算数据谈 9.9 万升级；可用标杆大会邀约降低决策难度"
    elif tier == "mid":
        return f"{urgency}用真实租户数据做用量测算表，向 AI 第一负责人推 29.7 万（话术：用量必超+立项复杂+不浪费）"
    elif tier == "high":
        return f"{urgency}先确认一把手（CEO/董事长）态度，备好人效数据，向 AI 第一负责人推 99 万"
    return None

if __name__ == "__main__":
    result = load_result()
    card = build_card(result)
    content = json.dumps(card, ensure_ascii=False)
    r = subprocess.run(
        ["lark-cli", "im", "+messages-send", "--as", "bot", "--msg-type", "interactive",
         "--chat-id", HOME_CHAT, "--content", content],
        capture_output=True, text=True, timeout=60,
    )
    print("exit:", r.returncode)
    print(r.stdout[-200:] if r.stdout else "")
    print(r.stderr[-200:] if r.stderr else "")
