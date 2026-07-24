"""Minimal working template for sending a Feishu interactive card via feishu-cli.

Copy this into execute_code or a Python script, replace the card dict and USER_OPEN_ID,
and run. Uses Python subprocess to avoid shell escaping traps.

AVOID Chinese quotation marks (like \u201c \u201d \u2018 \u2019) inside card content strings when
running in execute_code. The sandbox parser is strict about non-ASCII punctuation in
string literals and will throw SyntaxError at seemingly unrelated lines. Use plain
text without quotation marks, or \u201c/\u201d Unicode escapes if quotes are essential.
"""

import json, subprocess

FEISHU_CLI = "/Users/bytedance/.npm-global/bin/feishu-cli"
USER_OPEN_ID = "ou_dc055b0b5b0b5db2b1af5e79c0536db6"

card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": "标题"},
        "template": "blue"  # blue|turquoise|green|yellow|red|purple|indigo|gray|default
    },
    "elements": [
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**加粗** 正文内容"}
        },
        {
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": "底部备注"}]
        }
    ]
}

card_json = json.dumps(card, ensure_ascii=False)

payload = {
    "params": {"receive_id_type": "open_id"},
    "data": {
        "receive_id": USER_OPEN_ID,
        "msg_type": "interactive",
        "content": card_json
    }
}

result = subprocess.run(
    [FEISHU_CLI, "exec", "im.v1.message.create", "--params", json.dumps(payload)],
    capture_output=True, text=True, timeout=15
)

resp = json.loads(result.stdout)
if resp.get("ok") and resp["data"]["code"] == 0:
    print(f"OK: message_id={resp['data']['data']['message_id']}")
else:
    print(f"FAIL: {resp}")
