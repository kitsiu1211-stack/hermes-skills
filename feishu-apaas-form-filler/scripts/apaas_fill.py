"""aPaaS 表单读写助手。配合 cdp.py 使用。

用法：
    import sys; sys.path.insert(0, "/path/to/scripts")
    from cdp import CDP, page_ws
    import apaas_fill as A

    u, t = page_ws("apaas.feishuapp.cn")
    A.bind(CDP(u))
    A.pick_select(1, "汇联易", "汇联易费控和商旅解决方案", exact=True)
    A.fill_text(0, "刘鑫蕾")
    A.fill_textarea("给张晨")

字段序号约定：input[type=search] 按 y 排序即字段顺序（多选字段也占一个），
input 里 type==='text' 的按 y 排序是纯文本输入框。
"""
import json
import time

C = None


def bind(client):
    global C
    C = client
    return C


def _center(js_el):
    r = C.js("""(() => {const el=%s; if(!el) return null;
        const b=el.getBoundingClientRect();
        return JSON.stringify({x:Math.round(b.x+b.width/2), y:Math.round(b.y+b.height/2)});})()""" % js_el)
    return json.loads(r) if r else None


def search_inputs():
    """所有下拉的搜索框，按 y 排序。"""
    raw = C.js("""(() => JSON.stringify([...document.querySelectorAll('input[type=search]')]
        .filter(e=>e.offsetParent!==null)
        .map(e=>{const r=e.getBoundingClientRect();return {y:Math.round(r.y),x:Math.round(r.x+r.width/2)};})))()""")
    return sorted(json.loads(raw), key=lambda d: d["y"])


def text_inputs():
    """纯文本输入框。注意：type 是 IDL 默认值，不能用 input[type=text] 选。"""
    raw = C.js("""(() => JSON.stringify([...document.querySelectorAll('input')]
        .filter(e=>e.type==='text' && e.offsetParent!==null)
        .map(e=>{const r=e.getBoundingClientRect();return {y:Math.round(r.y),x:Math.round(r.x+r.width/2),v:e.value};})))()""")
    return sorted(json.loads(raw), key=lambda d: d["y"])


def option_boxes():
    """当前展开的下拉可见选项（去重，带中心坐标）。"""
    raw = C.js("""(() => {
      const its=[...document.querySelectorAll('li,[role=option],[class*=option]')]
        .filter(e=>e.offsetParent!==null && e.textContent.trim());
      const seen=new Set(); const out=[];
      for (const e of its){const t=e.textContent.trim(); if(seen.has(t)) continue; seen.add(t);
        const b=e.getBoundingClientRect(); if(!b.height) continue;
        out.push({t:t, x:Math.round(b.x+b.width/2), y:Math.round(b.y+b.height/2)});}
      return JSON.stringify(out);})()""")
    return json.loads(raw)


def open_select(idx, query=None):
    pos = search_inputs()[idx]
    C.click(pos["x"], max(pos["y"], 2) + 14, settle=0.9)
    if query:
        C.type_text(query)
        time.sleep(1.5)
    return True


def pick_option(match, exact=False):
    for o in option_boxes():
        if (o["t"] == match) if exact else (match in o["t"]):
            C.click(o["x"], o["y"], settle=0.8)
            return o["t"]
    return None


def pick_select(idx, query, match, exact=False):
    """点开第 idx 个下拉，输关键词，选中匹配项。失败返回 None 并关掉下拉。"""
    open_select(idx, query)
    got = pick_option(match, exact)
    if not got:
        C.send("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape",
               windowsVirtualKeyCode=27)
        time.sleep(0.4)
    return got


def fill_text(idx, text):
    pos = text_inputs()[idx]
    C.click(pos["x"], pos["y"], settle=0.3)
    C.js("(() => {const el=document.activeElement; if(el&&el.select) el.select(); return 1;})()")
    C.type_text(text)
    time.sleep(0.4)
    return text


def fill_textarea(text):
    """必须先 scrollIntoView，否则点击落在视口外，文字进不去。"""
    C.js("(() => {const el=document.querySelector('textarea'); el.scrollIntoView({block:'center'}); return 1;})()")
    time.sleep(0.7)
    r = _center("document.querySelector('textarea')")
    C.click(r["x"], r["y"], settle=0.4)
    C.type_text(text)
    time.sleep(0.5)
    return C.js("document.querySelector('textarea').value")


def state():
    return C.js("document.body.innerText.replace(/\\n+/g,' | ').slice(0,600)")


def values():
    return C.js("""(() => JSON.stringify({texts:[...document.querySelectorAll('input')]
        .filter(e=>e.type==='text').map(e=>e.value),
        ta:(document.querySelector('textarea')||{}).value}))()""")


def submit(wait=5):
    """点提交并验证。返回 (按钮坐标, 提交后页面文本, URL)。"""
    C.js("""(() => {const b=[...document.querySelectorAll('button')]
        .find(e=>e.textContent.trim()==='提交'); if(b) b.scrollIntoView({block:'center'}); return !!b;})()""")
    time.sleep(0.8)
    r = _center("[...document.querySelectorAll('button')].find(e=>e.textContent.trim()==='提交')")
    if not r:
        return None, "no submit button", None
    C.click(r["x"], r["y"], settle=0.5)
    time.sleep(wait)
    return r, C.js("document.body.innerText.slice(0,200)"), C.js("location.href")
