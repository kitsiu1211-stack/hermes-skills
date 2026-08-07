#!/usr/bin/env python3
"""
ISV 助手交互脚本 — 在 Agent 协作群 @南区 ISV 助手，获取材料链接。
助手回复在线程（Thread）中，需要监听线程回复。

用法：修改 QUERY 后，在 execute_code 中运行。
"""

import subprocess, json, time, re

FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"
LARK_CLI = "/Users/bytedance/.npm-global/bin/lark-cli"
CHAT_ID = "oc_219a613c13292855c2dc4b80e59dfd6e"  # Agent 协作群
HOME_ID = "oc_e2f79ec1614a1efe1ebcd7c679bb45a8"   # 用户 Home 频道
ISV_OPEN_ID = "ou_abdda0c6cd5e362bca041cb3dbd88f86"  # 南区 ISV 业务助手

# === 修改这里 ===
QUERY = "客户需要飞连的最新对客材料，麻烦发一下，谢谢！"
# ==============

# Step 1: 发 post 消息（必须带 at 元素，纯文本 @ 不触发）
content = json.dumps({
    "zh_cn": {
        "title": "ISV 材料请求",
        "content": [[
            {"tag": "at", "user_id": ISV_OPEN_ID},
            {"tag": "text", "text": f" {QUERY}"}
        ]]
    }
}, ensure_ascii=False)

payload = json.dumps({
    "params": {"receive_id_type": "chat_id"},
    "data": {"receive_id": CHAT_ID, "msg_type": "post", "content": content}
})

r = subprocess.run([FEISHU_CLI, "exec", "im.v1.message.create", "--params", payload],
                   capture_output=True, text=True, timeout=15)
result = json.loads(r.stdout)
msg_id = result.get("data", {}).get("data", {}).get("message_id", "")
print(f"消息已发送: {msg_id}")

# Step 2: 等待助手回复（5-10s）
time.sleep(8)

# Step 3: 查找线程回复
r2 = subprocess.run([LARK_CLI, "im", "+chat-messages-list", "--as", "user",
                     "--chat-id", CHAT_ID, "--page-size", "5"],
                    capture_output=True, text=True, timeout=15)
msgs = json.loads(r2.stdout).get("data", {}).get("messages", [])
thread_id = None
for m in msgs:
    if m.get("message_id") == msg_id:
        thread_id = m.get("thread_id", "")
        break

if not thread_id:
    print("未找到线程回复")
    exit()

# Step 4: 拉取线程消息
r3 = subprocess.run([LARK_CLI, "im", "+threads-messages-list", "--as", "user",
                     "--thread", thread_id],
                    capture_output=True, text=True, timeout=15)
thread_msgs = json.loads(r3.stdout).get("data", {}).get("messages", [])
print(f"线程回复数: {len(thread_msgs)}")

for m in thread_msgs:
    s = m.get("sender", {})
    c = m.get("content", "")
    print(f"[{s.get('name','?')}] {c[:500]}")

    # 提取卡片中的链接
    urls = re.findall(r'https?://[^\s\\\"<>]+', c)
    if urls:
        print(f"  URLs: {urls}")

# Step 5: 用 lark-cli docs +search 补全卡片按钮中的链接
# （卡片「点击查看」按钮的链接在文本中不可见，需要按材料名称搜索）
