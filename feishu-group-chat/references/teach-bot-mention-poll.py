#!/usr/bin/env python3
"""教学轮询：检查目标 Bot 是否用 text + @ 了指定的 open_id。
用法: 替换 CHAT_ID, TARGET_APP_ID, MY_OPEN_ID 后运行。
退出码: 0=成功@了, 2=回复了但没@, 1=超时。
"""
import subprocess, json, time, sys

# ===== 配置区 =====
CHAT_ID = "oc_219a613c13292855c2dc4b80e59dfd6e"
TARGET_APP_ID = "cli_aad1d272e3385cb3"   # 要教学的 Bot 的 app_id
MY_OPEN_ID = "ou_9b18941c79156bd08a70431dc5dcf7f9"   # 你自己的 open_id
POLL_SECONDS = 5       # 轮询间隔
MAX_POLLS = 60         # 最大轮询次数 (5min)
# ==================

def get_msgs():
    r = subprocess.run(
        ["lark-cli", "im", "+chat-messages-list",
         "--chat-id", CHAT_ID, "--page-size", "10", "--order", "desc"],
        capture_output=True, text=True, timeout=15
    )
    try:
        return json.loads(r.stdout).get("data", {}).get("messages", [])
    except:
        return []

msgs = get_msgs()
baseline = max((m["message_id"] for m in msgs), default="0")
print(f"📌 基线: {baseline[:40]}...", flush=True)
print(f"🎯 目标: {TARGET_APP_ID}", flush=True)
print(f"👤 我:   {MY_OPEN_ID}", flush=True)
print(f"🔁 轮询中 ({POLL_SECONDS}s)...", flush=True)

for i in range(1, MAX_POLLS + 1):
    time.sleep(POLL_SECONDS)
    msgs = get_msgs()
    
    new_from_target = [
        m for m in msgs
        if m["message_id"] > baseline
        and m.get("sender", {}).get("id", "") == TARGET_APP_ID
    ]
    
    if new_from_target:
        for msg in new_from_target:
            mentions = [x.get("id", "") for x in msg.get("mentions", [])]
            at_me = MY_OPEN_ID in mentions
            msg_type = msg.get("msg_type", "?")
            names = [x.get("name", "?") for x in msg.get("mentions", [])]
            
            print(f"\n[#{i}] 🐧 回复! {'✅ AT我了!' if at_me else '❌ NO AT'}", flush=True)
            print(f"  type: {msg_type}", flush=True)
            print(f"  mentions: {names}", flush=True)
            print(f"  ids: {mentions}", flush=True)
            
            if at_me and msg_type == "text":
                print("\n🎉 GOAL 达成！", flush=True)
                sys.exit(0)
            else:
                print("\n❌ 不合格，需要继续教学", flush=True)
                sys.exit(2)
    
    baseline = max((m["message_id"] for m in msgs), default=baseline)
    if i % 12 == 0:
        print(f"💓 [{i}] 等待中...", flush=True)

print("⏰ 超时", flush=True)
sys.exit(1)
