#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议雷达 — 主动式会议异常侦测与私聊推送（零token规则 + 小模型增量扫描）

设计目标（用户 2026-10-14 提出）：
  会议进行中，自动发现「冲突 / 异常 / 对方真实需求 / 我方失手」，主动私聊推给用户，
  而不是等用户问「刚才那场会怎么回事」。

三层：
  L1 规则层（本脚本内置，零 token，秒级）：审判式发问、竞品对标、商机信号、决策链、
     风险、我方失手、承诺待办、AI 被否 等关键词/句式 → 命中即私聊。
  L2 模型层（--llm，默认开，每 --llm-every 秒扫一次增量字幕，deepseek-chat）：
     结构化输出 {level,type,evidence,why,action}，只推 高 级别；中 级别合并成一条摘要。
  L3 会后层：现有 poll.sh → 纪要卡片（不变）。本脚本只负责「会中主动预警」。

用法：
  python3 meeting_radar.py <meeting_id|xxx.jsonl> [选项]
    --title <会议标题>
    --chat-id <飞书会话/用户ID>   (默认 $HERMES_HOME_CHAT 或 oc_e2f79ec1614a1efe1ebcd7c679bb45a8)
    --interval 15        日志轮询间隔秒
    --llm-every 360      L2 扫描间隔秒（0 = 关闭 L2）
    --max-alerts 12      单场会最多主动推送条数（防刷屏）
    --cooldown 480       同规则冷却秒数
    --idle-exit 1800     日志静默这么久视为会议结束退出
    --no-send            只打印不发送（调试）
    --replay             回放已存在的日志（一次性扫完历史，用于测试/补救）

状态/审计：
  ~/.hermes/cache/meeting_radar/<meeting_id>.state.json
  ~/.hermes/cache/meeting_radar/<meeting_id>.alerts.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, "meeting_logs")
STATE_DIR = os.path.join(HOME, ".hermes", "cache", "meeting_radar")
LARK_CLI = os.path.join(HOME, ".npm-global", "bin", "lark-cli")
DEFAULT_CHAT = "oc_e2f79ec1614a1efe1ebcd7c679bb45a8"  # Home DM
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ---------------------------------------------------------------- L1 规则表
# (id, 级别, 说明, 正则, 建议动作, 触发模式)
#   once   = 整场会只报第一次（宽泛的上下文信号，避免刷屏）
#   repeat = 每次命中都可报（高价值信号，受 --cooldown 约束）
RULES = [
    ("hostile_push", "🔴", "对方审判式/打断式发问",
     r"做不到|做不了|不支持|不能做到|没有得聊|就没有得聊|别讲这些|不要讲|不用讲|不要给我讲|"
     r"直接回答我|是和不是|给我个准话|你听我说|打断一下|节省我的时间|讲干货|不要绕|不要引导|"
     r"能不能做到|你的工具.*能不能|我要的是|你现在就|快说|不要老",
     "别逐条口头答辩，建议会后书面逐项应答（分：真不支持/需配置/需集成+插件）", "repeat"),

    ("ai_blocked", "🔴", "我方主线（AI/差异化）被当面否掉",
     r"不谈\s*AI|不讲\s*AI|不要讲\s*AI|别聊\s*AI|不要提\s*AI|AI\s*不可控|不要老引导",
     "差异点被封口 → 换赛道：讲可配置项清单 + 实施工作量，或改约线下演示", "repeat"),

    ("competitor", "🟠", "竞品/选型信号",
     r"Jira|JIRA|PingCode|pingcode|千问|WorkBuddy|Workbody|Gemini|Atlassian|禅道|TAPD|Teambition|Linear|选型",
     "记录竞品项，会后拉竞品对比口径（内部文档/样板间）", "once"),

    ("opportunity", "🔴", "商机/商务信号",
     r"预算|报价|多少钱|价格|单价|席位|采购|招标|比价|续约|合同到期|(?<!测)试用|PoC|立项|增购|"
     r"扩大规模|隐性成本|人力成本|工作量",
     "金额/时间点/决策链要立刻记下，会后建跟进日程", "once"),

    ("decider", "🟠", "决策链/关键人信号",
     r"老板|董事长|CEO|COO|CTO|CIO|一号位|拍板|决策权|总监|VP|采购部|信息化部|大领导",
     "谁拍板→会后确认能否约到该人，判断推进路径", "once"),

    ("risk", "🔴", "风险信号（安全/迁移/陪标/评分不公）",
     r"安全合规|合规|等保|私有化|数据出境|迁移成本|迁移到|换掉|停用|陪标|不公允|"
     r"权重|评分标准|得分率|偏离表|隐性成本|选型.*(评审|对比)",
     "风险项单独列，会后给应对口径；若疑似陪标，先评估投入产出", "repeat"),

    ("our_gap", "🟠", "我方答辩失手/给不出答案",
     r"给不出|给不了|我说实话|这个我不确定|需要确认|待验证|会后.*(答复|应答|视频|再给)|我来找找",
     "当场没答上的点 → 会后 24h 内必须书面补答，别让它变成扣分项", "repeat"),

    ("commitment", "🟠", "我方当场承诺（会后要兑现）",
     r"我回头|会后发|马上发|我今天就|我明天|我发你|发到群里|我拉个|我来建|我去确认",
     "承诺清单入待办，会后逐条兑现并回告", "repeat"),

    ("emotion", "🟠", "情绪/场压异常",
     r"干起来|看不下去|好困|离谱|无语|过分|没礼貌|别说了|吵什么",
     "场压偏高：提醒你换节奏（改成只答是/否 + 会后书面），必要时打断拉回议程", "repeat"),
]


# 一句里命中这些词 → 该句不参与「我方失手」等弱规则的误伤抑制
SOFT_RULES = {"our_gap", "commitment", "emotion"}


# ------------------------------------------------ 弱关键词二次校验（2026-10-14）
# 用户反馈：「他席位对，跳动的。」被判成 🔴 商机信号 —— 太模糊。
# 原因：「席位」这类词本身不构成商务信号，它大量出现在账号/权限/租户/镜像等
# **技术配置讨论**里（这场会正是在聊 Lark 与飞书账号能不能一套）。
# 规则：若该句的商务信号完全靠「弱词」撑起来（没有强词），则必须同句（或前一行）
# 出现「伴随词」（数字+单位 / 计费 / 成本 / 浮动 / 采购 …），否则不报。
WEAK_COMBO = {
    "opportunity": {
        "weak": r"席位|立项|增购|试用|扩大规模",
        "strong": (r"预算|报价|多少钱|价格|单价|采购|招标|比价|续约|合同到期|PoC|"
                   r"隐性成本|人力成本|工作量|成本"),
        "companion": (r"[0-9０-９一两三四五六七八九十百千万]+\s*(个席位|席|元|块|万|千|人天|用户|账号数)|"
                      r"多少|几多|怎么算|怎么收|计费|收费|费用|成本|价格|报价|预算|采购|比价|"
                      r"浮动|按人头|人头数|结算|扩容|升级|增购|续签|加席位|席位数量|多[买购]|要买|订购"),
    },
}


def rule_match(rx: re.Pattern, rid: str, text: str, window: str):
    """返回 (是否命中, 命中词列表)。弱词需伴随词兜底。"""
    ms = list(rx.finditer(text))
    if not ms:
        return False, []
    hits = []
    for m in ms:
        w = m.group(0).strip()
        if w and w not in hits:
            hits.append(w)
    combo = WEAK_COMBO.get(rid)
    if combo:
        if not re.search(combo["strong"], window) and not re.search(combo["companion"], window):
            return False, []
    return True, hits[:5]


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def load_env_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        with open(os.path.join(HOME, ".hermes", ".env")) as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


def send_dm(chat_id: str, text: str, dry: bool = False) -> bool:
    if dry:
        print(f"[DRY-DM] {chat_id}\n{text}\n{'─'*40}")
        return True
    try:
        r = subprocess.run(
            [LARK_CLI, "im", "+messages-send", "--as", "bot",
             "--chat-id", chat_id, "--text", text],
            capture_output=True, text=True, timeout=45)
        ok = '"ok": true' in (r.stdout or "")
        if not ok:
            print(f"[warn] 私聊推送失败: {(r.stdout or r.stderr)[:200]}", flush=True)
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 私聊推送异常: {e}", flush=True)
        return False


def read_jsonl_tail(path: str, offset: int):
    """返回 (新行列表, 新 offset)。"""
    if not os.path.exists(path):
        return [], offset
    size = os.path.getsize(path)
    if size < offset:          # 文件被截断/重建
        offset = 0
    if size == offset:
        return [], offset
    out = []
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read()
        offset = f.tell()
    for raw in chunk.decode("utf-8", "replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:  # noqa: BLE001
            continue
    return out, offset


def fmt_line(e: dict) -> str:
    sp = e.get("speaker", "?")
    tx = (e.get("text") or "").strip()
    raw = e.get("time") or ""
    t = raw[11:19] if len(raw) >= 19 and raw[4] == "-" else (raw[-8:] if raw else now_str())
    return f"{t} {sp}：{tx}"


# ---------------------------------------------------------------- L2 模型层
LLM_PROMPT = """你是飞书销售袁鑫杰的会议实时雷达。下面是会议《{title}》的增量字幕。
只输出 JSON，不要任何解释文字。找出「袁鑫杰此刻必须知道」的异常/冲突/需求信号，最多 3 条，宁缺勿滥。

判断维度：
1) 冲突：对方否定、质问、打断、当面说「你做不到」；我方被逼到墙角
2) 需求：对方真正想要的东西（往往藏在抱怨后面）、预算/时间点/决策链/竞品
3) 风险：安全合规、迁移成本、陪标、隐性成本、评分不公
4) 我方失手：答不上来、含糊、承诺没给时间
5) 人：某个发言人背后的真实诉求（他要交的差、他的 KPI）

输出格式：
{{"alerts":[{{"level":"高|中","type":"冲突|需求|风险|失手|人","who":"谁","evidence":"原话片段(不超过40字)","why":"为什么重要(不超过40字)","action":"建议动作(不超过30字)"}}]}}
没有值得报的就输出 {{"alerts":[]}}

字幕：
{chunk}"""


def llm_sweep(title: str, chunk_lines: list[str], api_key: str):
    if not api_key or not chunk_lines:
        return []
    chunk = "\n".join(chunk_lines)[-6000:]
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": LLM_PROMPT.format(title=title, chunk=chunk)}],
        "max_tokens": 700, "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        txt = data["choices"][0]["message"]["content"]
        i = txt.find("{")
        return json.loads(txt[i:]).get("alerts", []) or []
    except Exception as e:  # noqa: BLE001
        print(f"[warn] L2 扫描失败: {e}", flush=True)
        return []


def render_llm_alert(title: str, a: dict) -> str:
    icon = "🔴" if a.get("level") == "高" else "🟠"
    return (f"⚡ 会议雷达｜{icon} {a.get('type','信号')}\n"
            f"《{title}》\n"
            f"{a.get('who','')}「{a.get('evidence','')}」\n"
            f"为什么：{a.get('why','')}\n"
            f"👉 {a.get('action','')}")


CTX_KEEP = 4          # 命中句前取几行上文
CTX_MAXLEN = 90       # 每行上文最长字符


def clean_ctx(recent: list[str], n: int = CTX_KEEP) -> list[str]:
    """从滚动窗口取上下文：去掉过短噪音行 + 去掉连续重复，取最后 n 行。"""
    out: list[str] = []
    prev = None
    for s in recent:
        s = s.strip()
        if len(s) < 8:                 # "嗯" / "对。" / "他席位对" 这类无信息碎片
            continue
        if s == prev:                  # 同一句重复推送
            continue
        out.append(s[:CTX_MAXLEN])
        prev = s
    return out[-n:]


def render_rule_alert(title: str, rule_id: str, level: str, desc: str, line: dict,
                      action: str, ctx: list[str] | None = None,
                      hits: list[str] | None = None) -> str:
    """带上下文的规则预警。

    2026-10-14 用户反馈：只有一句「是的，这个回头我可以发到群里面」看不出承诺的是什么，
    必须把命中句前面的对话一起给出。ctx 是命中句之前已播出的字幕（零 token，纯滑动窗口）。

    2026-10-14 二次反馈：「他席位对，跳动的。」被判成商机信号太模糊 ——
    只给结论不给触发原因。故补「命中词」，让用户一眼看出是哪个词报警。
    """
    head = [f"⚡ 会议雷达｜{level} {desc}", f"《{title}》"]
    if ctx:
        head.append("上文：")
        head.extend("    " + s for s in ctx)
        head.append("👇 命中：")
    head.append(fmt_line(line))
    if hits:
        head.append(f"　命中词：{'、'.join(hits)}")
    head.append(f"👉 {action}")
    return "\n".join(head)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="meeting_id 或 jsonl 路径")
    ap.add_argument("--title", default="")
    ap.add_argument("--chat-id", default=os.environ.get("HERMES_HOME_CHAT", DEFAULT_CHAT))
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--llm-every", type=int, default=360)
    ap.add_argument("--max-alerts", type=int, default=12)
    ap.add_argument("--cooldown", type=int, default=480)
    ap.add_argument("--idle-exit", type=int, default=1800)
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    if args.target.endswith(".jsonl"):
        log_path = args.target
        mid = os.path.basename(log_path)[:-6]
    else:
        mid = args.target
        log_path = os.path.join(LOG_DIR, f"{mid}.jsonl")
    title = args.title or mid

    os.makedirs(STATE_DIR, exist_ok=True)
    suffix = ".replay" if args.replay else ""
    state_path = os.path.join(STATE_DIR, f"{mid}{suffix}.state.json")
    audit_path = os.path.join(STATE_DIR, f"{mid}{suffix}.alerts.jsonl")

    state = {"offset": 0, "sent": {}, "sent_rules": {}, "rule_ts": {}, "count": 0,
             "llm_ts": 0.0, "llm_offset": 0, "lines": 0}
    fresh = not os.path.exists(state_path)
    if not args.replay and not fresh:
        try:
            state.update(json.load(open(state_path)))
        except Exception:  # noqa: BLE001
            pass
    # 🚨 实时模式首次启动：从日志末尾开始跟，避免把会议前半场的旧内容一股脑推给用户
    if not args.replay and fresh and os.path.exists(log_path):
        state["offset"] = os.path.getsize(log_path)

    api_key = "" if (args.no_llm or args.llm_every <= 0) else load_env_key()
    compile_rules = [(rid, lv, desc, re.compile(rx), act, mode)
                     for rid, lv, desc, rx, act, mode in RULES]

    print(f"=== 会议雷达启动 ===\n会议：{title}（{mid}）\n日志：{log_path}\n"
          f"推送：{args.chat_id}{' [DRY]' if args.no_send else ''}  规则冷却 {args.cooldown}s  "
          f"上限 {args.max_alerts} 条  L2:{'off' if not api_key else f'{args.llm_every}s'}", flush=True)

    llm_buf: list[str] = []
    recent: list[str] = []          # 滚动上文窗口（命中句之前的字幕）
    last_new = time.time()
    rounds = 0
    while True:
        rounds += 1
        lines, state["offset"] = read_jsonl_tail(log_path, state["offset"])
        ended = False
        for e in lines:
            if e.get("type") == "meta" and e.get("event") == "meeting_ended":
                ended = True
                continue
            if e.get("type") not in ("transcript", "chat"):
                continue
            state["lines"] += 1
            text = e.get("text") or ""
            if e.get("type") == "transcript":
                llm_buf.append(fmt_line(e))
                recent.append(fmt_line(e))      # 先入窗口；取 ctx 时用 recent[:-1] 保证只含命中句之前
                if len(recent) > 12:
                    del recent[:-12]
            window = "\n".join(recent[-3:]) or text     # 命中句 + 前两行，用于弱词兜底
            for rid, lv, desc, rx, act, mode in compile_rules:
                ok, hits = rule_match(rx, rid, text, window)
                if not ok:
                    continue
                if mode == "once":
                    if len(text) < 8 or rid in state.get("sent_rules", {}):
                        continue
                if state["count"] >= args.max_alerts:
                    break
                last = state["rule_ts"].get(rid, 0)
                if time.time() - last < args.cooldown:
                    continue
                key = f"{rid}:{text[:60]}"
                if key in state["sent"]:
                    continue
                state["sent"][key] = True
                state.setdefault("sent_rules", {})[rid] = True
                state["rule_ts"][rid] = time.time()
                state["count"] += 1
                ctx = clean_ctx(recent[:-1])
                msg = render_rule_alert(title, rid, lv, desc, e, act, ctx, hits)
                send_dm(args.chat_id, msg, dry=args.no_send)
                with open(audit_path, "a") as f:
                    f.write(json.dumps({"ts": now_str(), "layer": "L1", "rule": rid,
                                        "level": lv, "line": e, "ctx": ctx, "hits": hits},
                                       ensure_ascii=False) + "\n")
                if not args.replay:
                    break   # 每轮最多推一条，避免刷屏

        if lines:
            last_new = time.time()

        # L2 增量扫描
        if api_key and llm_buf and (args.replay or time.time() - state["llm_ts"] >= args.llm_every):
            if len(llm_buf) >= 15 or args.replay:
                alerts = llm_sweep(title, llm_buf, api_key)
                state["llm_ts"] = time.time()
                mids: list[str] = []
                for a in alerts:
                    if args.no_send:
                        print("[DRY-L2] " + render_llm_alert(title, a).replace("\n", " | "), flush=True)
                    if a.get("level") == "高" and state["count"] < args.max_alerts:
                        state["count"] += 1
                        send_dm(args.chat_id, render_llm_alert(title, a), dry=args.no_send)
                        with open(audit_path, "a") as f:
                            f.write(json.dumps({"ts": now_str(), "layer": "L2", "alert": a},
                                               ensure_ascii=False) + "\n")
                    else:
                        mids.append(render_llm_alert(title, a))
                if mids and state["count"] < args.max_alerts:
                    state["count"] += 1
                    send_dm(args.chat_id, "⚡ 会议雷达｜🟠 中优先信号汇总\n" + "\n---\n".join(mids),
                            dry=args.no_send)
                    with open(audit_path, "a") as f:
                        f.write(json.dumps({"ts": now_str(), "layer": "L2", "level": "中批",
                                            "batch": len(mids)}, ensure_ascii=False) + "\n")
                llm_buf = []

        json.dump(state, open(state_path, "w"))

        if ended:
            print("=== 会议已结束，雷达退出 ===", flush=True)
            return 0
        if args.replay:
            print("=== 回放完毕 ===", flush=True)
            return 0
        if time.time() - last_new > args.idle_exit:
            print(f"=== 日志静默超过 {args.idle_exit}s，雷达退出 ===", flush=True)
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n=== 雷达手动停止 ===")
        sys.exit(0)
