#!/usr/bin/env python3
"""裸 CDP 客户端。用法一：命令行跑一段 JS

    python3 cdp.py /tmp/xxx.js         # 打印 JS 返回值
    python3 cdp.py                     # 从 stdin 读

用法二：import

    import sys; sys.path.insert(0, "/path/to/scripts")
    from cdp import CDP, page_ws
    u, target = page_ws("apaas.feishuapp.cn")
    c = CDP(u)
    print(c.js("document.title"))

前置：Chrome 已用 --remote-debugging-port=9222 --remote-allow-origins=* 启动。
注意端口监听在 IPv6，用 localhost 访问（127.0.0.1 会连不上）。
"""
import json
import sys
import urllib.request

import websocket


def targets():
    with urllib.request.urlopen("http://localhost:9222/json/list", timeout=5) as r:
        return json.load(r)


def page_ws(prefer_url=None, skip_chrome=True):
    """挑一个 page target。skip_chrome 会跳过 chrome:// 内部页面（否则常选中 managed-user-profile-notice）。"""
    ts = [t for t in targets() if t.get("type") == "page"]
    if skip_chrome:
        ts = [t for t in ts if not (t.get("url") or "").startswith("chrome://")]
    if prefer_url:
        for t in ts:
            if prefer_url in (t.get("url") or ""):
                return t["webSocketDebuggerUrl"], t
    if not ts:
        raise SystemExit("no page target")
    return ts[0]["webSocketDebuggerUrl"], ts[0]


class CDP:
    def __init__(self, url):
        # suppress_origin 必须开，否则握手 403（Chrome 拒绝带 Origin 的 ws 连接）
        self.ws = websocket.create_connection(url, timeout=60, suppress_origin=True)
        self.i = 0

    def send(self, method, **params):
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method} -> {msg['error']}")
                return msg.get("result", {})

    def js(self, expr, awaitp=True):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=awaitp, userGesture=True)
        if "exceptionDetails" in r:
            return {"__error": str(r["exceptionDetails"].get("text")),
                    "detail": str(r["exceptionDetails"].get("exception", {}).get("description", ""))[:400]}
        return r.get("result", {}).get("value")

    def click(self, x, y, settle=0.3):
        """真鼠标事件。React 组件不认 el.click()。"""
        self.send("Input.dispatchMouseEvent", type="mousePressed", x=int(x), y=int(y),
                  button="left", clickCount=1)
        self.send("Input.dispatchMouseEvent", type="mouseReleased", x=int(x), y=int(y),
                  button="left", clickCount=1)
        if settle:
            import time
            time.sleep(settle)

    def type_text(self, text):
        self.send("Input.insertText", text=text)

    def shot(self, path, full_page=False):
        import base64
        if full_page:
            self.js("""(() => {
              [...document.querySelectorAll('*')]
                .filter(e=>e.scrollHeight>e.clientHeight+50 && e.clientHeight>200)
                .forEach(e=>{e.style.maxHeight='none';e.style.height='auto';e.style.overflow='visible';});
              document.documentElement.style.overflow='visible';
              document.body.style.overflow='visible';
              return 1;})()""")
        r = self.send("Page.captureScreenshot", format="png", captureBeyondViewport=full_page)
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path


if __name__ == "__main__":
    code = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    u, t = page_ws()
    c = CDP(u)
    print("TARGET:", (t.get("url") or "")[:160])
    out = c.js(code)
    print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))
