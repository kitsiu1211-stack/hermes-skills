"""
ISV助手线程轮询脚本 — 发消息给 ISV 助手并等待线程回复。

使用方式：
    python isv_poll.py "客户需要XX的最新对客材料，麻烦发一下，谢谢！"
"""
import json, subprocess, sys, time

FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"
LARK_CLI = "/Users/bytedance/.npm-global/bin/lark-cli"

CHAT_ID = "oc_219a613c13292855c2dc4b80e59dfd6e"
ISV_OPEN_ID = "ou_abdda0c6cd5e362bca041cb3dbd88f86"

def send_and_poll(question: str, wait_secs: int = 8) -> str:
    """发送消息到 ISV 助手并返回线程回复内容"""
    
    # Step 1: 发 post 消息 @ISV助手
    content = json.dumps({
        "zh_cn": {
            "title": "ISV 材料请求",
            "content": [[
                {"tag": "at", "user_id": ISV_OPEN_ID},
                {"tag": "text", "text": f" {question}"}
            ]]
        }
    }, ensure_ascii=False)
    
    payload = json.dumps({
        "params": {"receive_id_type": "chat_id"},
        "data": {"receive_id": CHAT_ID, "msg_type": "post", "content": content}
    })
    
    r = subprocess.run(
        [FEISHU_CLI, "exec", "im.v1.message.create", "--params", payload],
        capture_output=True, text=True, timeout=15
    )
    result = json.loads(r.stdout)
    msg_id = result["data"]["data"]["message_id"]
    print(f"Message sent: {msg_id}", file=sys.stderr)
    
    # Step 2: 等待 ISV 助手回复
    time.sleep(wait_secs)
    
    # Step 3: 从群消息中找到 thread_id
    r2 = subprocess.run(
        [LARK_CLI, "im", "+chat-messages-list", "--as", "user",
         "--chat-id", CHAT_ID, "--page-size", "5"],
        capture_output=True, text=True, timeout=15
    )
    msgs_data = json.loads(r2.stdout)
    
    thread_id = None
    for m in msgs_data.get("data", {}).get("messages", []):
        if m.get("message_id") == msg_id:
            thread_id = m.get("thread_id", "")
            break
    
    if not thread_id:
        print("ERROR: No thread found for message", file=sys.stderr)
        return ""
    
    print(f"Thread: {thread_id}", file=sys.stderr)
    
    # Step 4: 拉取线程回复
    r3 = subprocess.run(
        [LARK_CLI, "im", "+threads-messages-list", "--as", "user",
         "--thread", thread_id],
        capture_output=True, text=True, timeout=15
    )
    thread_data = json.loads(r3.stdout)
    
    for m in thread_data.get("data", {}).get("messages", []):
        sender = m.get("sender", {}).get("id", "")
        if sender == "cli_aaa06c74f1f89bcb":  # ISV 助手
            return m.get("content", "")
    
    return ""


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "客户需要材料，麻烦发一下"
    reply = send_and_poll(question)
    print(reply)
