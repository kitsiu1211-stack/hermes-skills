#!/usr/bin/env python3
"""Probe a fallback LLM endpoint with a real chat completion.

Deterministic connectivity check for fallback_providers entries — never
trust config alone; verify the endpoint actually answers.

Default: MiniMax CN endpoint (this user's fallback chain as of 2026-08-22).
Customize via argv:  test_fallback_endpoint.py <url> <model> <key_env>
Keys are read from ~/.hermes/.env (never printed).

Usage:
    python3 test_fallback_endpoint.py
    python3 test_fallback_endpoint.py https://api.deepseek.com/v1 deepseek-v4-flash DEEPSEEK_API_KEY
"""
import json
import os
import sys
import urllib.request

DEFAULT_URL = "https://api.minimaxi.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M3"
DEFAULT_KEY_ENV = "MINIMAX_API_KEY"


def read_env_key(name: str) -> str | None:
    env_path = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env_path):
        return None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    model = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    key_env = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_KEY_ENV

    key = read_env_key(key_env)
    if not key:
        print(f"FAIL: {key_env} not found in ~/.hermes/.env")
        return 1

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "回复两个字：正常"}],
        "max_tokens": 20,
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "?")
            print(f"OK: {resp.status} | model={data.get('model')} | reply={reply[:60]}")
            return 0
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
