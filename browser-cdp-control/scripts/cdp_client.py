#!/usr/bin/env python3
"""裸 CDP 客户端 —— 不依赖 browser-harness daemon。

前置：Chrome 已用 --remote-debugging-port=9222 --remote-allow-origins='*' 启动。
DevTools 只监听 IPv6，所以用 localhost / [::1]，不要用 127.0.0.1。

用法：
  python3 cdp_client.py list                      # 列出可操作的 page 目标
  python3 cdp_client.py goto <url> [--match 关键字]
  python3 cdp_client.py eval '<js 表达式>' [--match 关键字]
  python3 cdp_client.py file <脚本.js> [--match 关键字]
  python3 cdp_client.py shot <输出.png> [--match 关键字]
  python3 cdp_client.py cookies                   # 数一下 cookie，判断登录态

作为库用：
  from cdp_client import connect, js
  c, t = connect("accounts.feishu.cn")
  print(c.js("document.title"))
"""
import argparse
import base64
import json
import sys
import urllib.request

import websocket  # pip install websocket-client


def targets(port=9222):
    with urllib.request.urlopen(f"http://localhost:{port}/json/list", timeout=5) as r:
        return json.load(r)


def page_targets(port=9222):
    """只要真实网页目标。chrome:// 和 browser_ui 会被混进来，不能不过滤。"""
    return [
        t for t in targets(port)
        if t.get("type") == "page" and not (t.get("url") or "").startswith("chrome://")
    ]


class CDP:
    def __init__(self, ws_url):
        # suppress_origin 绕开 "Rejected an incoming WebSocket connection from ...origin"
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self._id = 0

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method} -> {msg['error']}")
                return msg.get("result", {})

    def js(self, expr, await_promise=True):
        r = self.send(
            "Runtime.evaluate",
            expression=expr,
            returnByValue=True,
            awaitPromise=await_promise,
            userGesture=True,
        )
        if "exceptionDetails" in r:
            ex = r["exceptionDetails"]
            return {
                "__error": str(ex.get("text")),
                "detail": str(ex.get("exception", {}).get("description", ""))[:400],
            }
        return r.get("result", {}).get("value")

    def goto(self, url, timeout=30):
        self.send("Page.enable")
        self.send("Page.navigate", url=url)
        return self.js(
            "new Promise(r => { if (document.readyState === 'complete') r(location.href);"
            " else window.addEventListener('load', () => r(location.href));"
            f" setTimeout(() => r(location.href), {timeout * 1000}); }})"
        )

    def shot(self, path):
        r = self.send("Page.captureScreenshot", format="png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path


def connect(match=None, port=9222):
    ts = page_targets(port)
    if not ts:
        raise SystemExit("没有可操作的 page 目标，检查 Chrome 是否带 --remote-debugging-port 启动")
    if match:
        hit = [t for t in ts if match in (t.get("url") or "")]
        if not hit:
            raise SystemExit(f"没有 URL 含 {match!r} 的目标。现有：{[t.get('url','')[:70] for t in ts]}")
        t = hit[0]
    else:
        t = ts[0]
    return CDP(t["webSocketDebuggerUrl"]), t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "goto", "eval", "file", "shot", "cookies"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--match", help="按 URL 子串挑目标 tab")
    ap.add_argument("--port", type=int, default=9222)
    a = ap.parse_args()

    if a.cmd == "list":
        for t in page_targets(a.port):
            print(t.get("url", "")[:110])
        return

    c, t = connect(a.match, a.port)
    print(f"# target: {t.get('url','')[:100]}", file=sys.stderr)

    if a.cmd == "goto":
        print(c.goto(a.arg))
    elif a.cmd == "eval":
        print(json.dumps(c.js(a.arg), ensure_ascii=False)[:6000])
    elif a.cmd == "file":
        with open(a.arg) as f:
            print(json.dumps(c.js(f.read()), ensure_ascii=False)[:6000])
    elif a.cmd == "shot":
        print(c.shot(a.arg))
    elif a.cmd == "cookies":
        print(c.js("JSON.stringify({n: document.cookie.split(';').length, url: location.href.slice(0,120)})"))


if __name__ == "__main__":
    main()
