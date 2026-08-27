#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 赢单商机雷达 — 飞书卡片生成器 V2（跟进增强版）
读取三个文件组装总览卡片 → 发送到 Home：
  /tmp/radar_result.json     信号结果（radar_full.py 生成）
  /tmp/radar_followups.json  跟进扫描（fetch_followups.py 生成，可选）
  /tmp/radar_actions.json    逐户动作（Agent 手写，可选；缺省用模板兜底）

V2 相对 V1 的改进：
- 动作优先用 Agent 基于跟进记录写的（radar_actions.json），不再全员同一句模板
- Evaluator 打回的客户自动标记 ⚠️ 到期/异常，不计入强信号数
- 排序按剩余天数升序（紧急优先），到期节点最前
- 卡片 note 如实反映 Evaluator 结果（X 条通过 + Y 条打回）
"""
import json
import subprocess
import datetime
import os

HOME_CHAT = os.environ.get("RADAR_HOME_CHAT", "oc_e2f79ec1614a1efe1ebcd7c679bb45a8")


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def sort_key(f):
    """到期节点最前，其余按剩余天数升序"""
    ev = f["opportunity"].get("evidence", {})
    days = ev.get("days_left")
    days = days if isinstance(days, (int, float)) else 999
    return (-1 if not f["evaluator"]["passed"] else 0, days)


def strength_display(f):
    if not f["evaluator"]["passed"]:
        return "⚠️ 到期/异常"
    return f["opportunity"]["strength"]


def tier_action(opp):
    """模板兜底动作（仅当 Agent 未写动作时使用）"""
    tier, target = opp["tier"], opp["target"]
    strength = opp["strength"]
    urgency = "🔴 本周必须动作：" if "强" in strength else ("🟡 本周安排接触：" if "中" in strength else "🟢 观察跟进：")
    if tier == "entry":
        return f"{urgency}约 AI 第一负责人（CIO/技术负责人），带用量测算数据谈 9.9 万升级（模板动作，建议 Agent 基于跟进记录改写）"
    if tier == "mid":
        return f"{urgency}用真实租户数据做用量测算表，向 AI 第一负责人推 29.7 万（模板动作，建议 Agent 基于跟进记录改写）"
    return f"{urgency}先确认一把手态度，备好人效数据，推 99 万（模板动作，建议 Agent 基于跟进记录改写）"


def build_card(result, followups, actions):
    findings = sorted(result["findings"], key=sort_key)
    strong = [f for f in findings if "强" in strength_display(f)]
    mid = [f for f in findings if "中" in strength_display(f)]
    expiry = [f for f in findings if not f["evaluator"]["passed"]]
    weak = [f for f in findings if "弱" in strength_display(f)]

    elements = []
    elements.append({
        "tag": "column_set", "flex_mode": "none", "background_style": "default",
        "columns": [
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=red>{len(strong)}</font>\n<font size=14 color=red>强信号</font>\n<font size=12 color=grey>本周必须动作</font>"}]},
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=orange>{len(mid)}</font>\n<font size=14 color=orange>中信号</font>\n<font size=12 color=grey>本周安排接触</font>"}]},
            {"tag": "column", "width": "weighted", "weight": 1, "vertical_align": "top",
             "elements": [{"tag": "markdown", "content": f"<font size=24 weight=bold color=grey>{len(expiry)}</font>\n<font size=14 color=grey>到期节点</font>\n<font size=12 color=grey>非升级信号</font>"}]},
        ],
    })
    elements.append({"tag": "hr"})

    # 跟进洞察摘要（有数据才显示）
    if followups:
        no_follow = [n for n, v in followups.items() if not v.get("any_followup")]
        has_ai = [n for n, v in followups.items() if v.get("ai_hits")]
        insight = f"💡 跟进洞察：{len(findings)} 家信号客户中 {len(has_ai)} 家有近两周 AI 对话，{len(no_follow)} 家无任何跟进——数据在报警、人在沉默，动作需按真实跟进推进。"
        elements.append({"tag": "markdown", "content": insight})
        elements.append({"tag": "hr"})

    for i, f in enumerate(findings, 1):
        opp = f["opportunity"]
        name = f["account_name"]
        lines = []
        lines.append(f"<font size=16 weight=bold>{i}. {name} | {strength_display(f)}</font>")
        lines.append(f"<font size=14>当前 <font weight=bold>{opp['tier_label']}</font> → 建议升级 <font weight=bold color=red>{opp['target']}</font></font>")
        for s in opp["signals"]:
            lines.append(f"📊 {s}")

        # 跟进记录行
        fu = (followups or {}).get(name)
        if fu:
            if fu.get("ai_hits"):
                hit = fu["ai_hits"][0]
                content = hit["content"].replace("\n", " ")
                lines.append(f"📋 近两周 AI 跟进（{hit['date']}）：{content[:150]}")
                if len(fu["ai_hits"]) > 1:
                    lines.append(f"   …另有 {len(fu['ai_hits'])-1} 条 AI 跟进")
            elif fu.get("any_followup"):
                lines.append(f"📋 近两周有 {fu.get('total_14d', '?')} 条跟进但无 AI 话题")
            else:
                lines.append("📋 近两周无跟进记录")

        # 动作：Agent 手写 > 模板兜底
        action = (actions or {}).get(name)
        if action:
            lines.append(f"✅ 本周动作：{action}")
        else:
            lines.append(f"👉 {tier_action(opp)}")

        elements.append({"tag": "markdown", "content": "\n".join(lines)})
        elements.append({"tag": "hr"})

    # 底部说明（如实反映 Evaluator 结果）
    n_fail = len(expiry)
    ev_note = f"{len(findings)-n_fail} 条通过 + {n_fail} 条打回（到期节点）" if n_fail else f"{len(findings)} 条全部通过"
    generated = result.get("generated_at", "")
    try:
        time_str = datetime.datetime.fromisoformat(generated).strftime("%Y-%m-%d %H:%M")
    except Exception:
        time_str = generated
    followup_note = " + follow_up 跟进记录（只读）" if followups else ""
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"数据源：C360 tenant_metrics{followup_note} | 抓取时间：{time_str} | Evaluator 校验：{ev_note} | 阈值：主题34 升级信号清单 V3.1"}],
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": f"📡 AI 赢单商机雷达 V2 | {datetime.datetime.now().strftime('%m-%d')} 扫描"}, "template": "red" if strong else ("orange" if mid else "blue")},
        "elements": elements,
    }
    return card


if __name__ == "__main__":
    result = load("/tmp/radar_result.json")
    if not result:
        print("缺少 /tmp/radar_result.json，请先运行 radar_full.py")
        sys.exit(1)
    followups = load("/tmp/radar_followups.json")
    actions = load("/tmp/radar_actions.json")
    card = build_card(result, followups, actions)
    content = json.dumps(card, ensure_ascii=False)
    r = subprocess.run(
        ["lark-cli", "im", "+messages-send", "--as", "bot", "--msg-type", "interactive",
         "--chat-id", HOME_CHAT, "--content", content],
        capture_output=True, text=True, timeout=60,
    )
    print("exit:", r.returncode)
    print("STDOUT_FULL:", r.stdout[:1000] if r.stdout else "")
    print("STDERR:", r.stderr[-300:] if r.stderr else "")
