#!/usr/bin/env python3
"""裸 CDP 小工具：给已开 --remote-debugging-port 的 Chrome 发指令。

前提（见 SKILL.md 步骤 1）：
  Chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=<独立目录>

用法：
  python3 cdp_client.py                      # 自检：列出页面 target
  python3 cdp_client.py show.js              # 在第一个非 chrome:// 页执行 JS，打印结果

作为模块：
  from cdp_client import CDP, page_ws
  u, t = page_ws("apaas")        # 按 URL 片段挑 target
  c = CDP(u)
  c.js("location.href")
  c.click(300, 420)              # 真实鼠标（React 组件必须用这个）
  c.insert("睿魔")               # 中文输入用 insertText
  c.shot("/tmp/a.png")           # 截当前视口
  c.shot_full("/tmp/b.png")      # 先把内层滚动容器撑开，再整页截
"""
import base64
import json
import sys
import time
import urllib.request

import websocket

BASE = "http://localhost:9222"  # 端口只监听 IPv6，别用 127.0.0.1


def targets():
    with urllib.request.urlopen(f"{BASE}/json/list", timeout=5) as r:
        return json.load(r)


def page_ws(prefer_url=None):
    ts = [t for t in targets()
          if t.get("type") == "page" and not (t.get("url") or "").startswith("chrome://")]
    if prefer_url:
        for t in ts:
            if prefer_url in (t.get("url") or ""):
                return t["webSocketDebuggerUrl"], t
    if not ts:
        raise SystemExit("no page target")
    return ts[0]["webSocketDebuggerUrl"], ts[0]


class CDP:
    def __init__(self, url):
        # suppress_origin=True 绕过 403 rejected from origin
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

    def js(self, expr, awaitp=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=awaitp, userGesture=True)
        if "exceptionDetails" in r:
            return {"__error": str(r["exceptionDetails"].get("text")),
                    "detail": str(r["exceptionDetails"].get("exception", {}).get("description", ""))[:400]}
        return r.get("result", {}).get("value")

    def click(self, x, y, wait=0.35):
        for ev in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", type=ev, x=x, y=y,
                      button="left", clickCount=1)
        time.sleep(wait)

    def insert(self, text, wait=0.4):
        self.send("Input.insertText", text=text)
        time.sleep(wait)

    def center(self, js_el):
        r = self.js(f"(() => {{const el={js_el}; if(!el) return null;"
                    "const b=el.getBoundingClientRect();"
                    "return JSON.stringify({x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)});})()")
        return json.loads(r) if r else None

    def shot(self, path):
        r = self.send("Page.captureScreenshot", format="png")
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    def shot_full(self, path):
        """内层滚动容器不撑开的话，captureBeyondViewport 只拿到视口。"""
        self.js("""(() => {
          [...document.querySelectorAll('*')]
            .filter(e=>e.scrollHeight>e.clientHeight+50 && e.clientHeight>200)
            .forEach(e=>{e.style.maxHeight='none'; e.style.height='auto'; e.style.overflow='visible';});
          document.documentElement.style.overflow='visible';
          document.body.style.overflow='visible';
          return 1;
        })()""")
        time.sleep(1.0)
        r = self.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    # ---- 表单常用 ----
    def text_inputs(self):
        return sorted(json.loads(self.js("""(() => JSON.stringify(
            [...document.querySelectorAll('input')].filter(e=>e.type==='text')
              .map(e=>{const r=e.getBoundingClientRect();
                       return {y:Math.round(r.y), x:Math.round(r.x+r.width/2), v:e.value};})))()""")),
            key=lambda d: d["y"])

    def options(self):
        return json.loads(self.js("""(() => {
          const its=[...document.querySelectorAll('li,[role=option],[class*=option]')]
              .filter(e=>e.offsetParent!==null && e.textContent.trim());
          const seen=new Set(), out=[];
          for (const e of its){const t=e.textContent.trim(); if(seen.has(t))continue; seen.add(t);
            const b=e.getBoundingClientRect(); if(!b.height)continue;
            out.push({t, x:Math.round(b.x+b.width/2), y:Math.round(b.y+b.height/2)});}
          return JSON.stringify(out);})()"""))

    def pick_option(self, target, exact=True):
        for o in self.options():
            if (o["t"] == target) if exact else (target in o["t"]):
                self.click(o["x"], o["y"], wait=0.8)
                return o["t"]
        return None


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for t in targets():
            print(t.get("type"), (t.get("url") or "")[:90])
    else:
        code = open(sys.argv[1]).read()
        u, t = page_ws()
        c = CDP(u)
        print("TARGET:", (t.get("url") or "")[:120])
        out = c.js(code, awaitp=True)
        print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)[:6000])
