---
name: web-form-autofill
description: 用用户身份填并提交网页/内部系统表单（飞书 aPaaS、OA、后台），CDP 驱动 + 截图确认。
category: productivity
metadata:
  hermes:
    tags: [form, cdp, browser, feishu, apaas, automation]
---

# 网页表单代填（以用户身份）

## 何时用

用户丢一个表单链接并说「你以我的身份填/提交这个」。典型场景：飞书 aPaaS（妙搭）表单、内部 OA 提报、ISV线索提报、报销/申请类页面。

## 铁律

1. **提交前必须整页截图 + 逐字段清单给用户确认**，确认后才点提交。用户原话「提交前先截图和我确认下细节，没问题再提交」。
2. **截图必须包含整张表单**（顶部字段到最底部提交按钮）。只截视口会被打回「没有截全，下面看不到」——见步骤 5。
3. 缺字段信息时**一次问全**，不要让用户分几轮补。
4. 用户确认后直接提交，不要追加二次确认。

## 步骤 1：接上浏览器（裸 CDP）

不要用会弹窗的路径。Chrome 用默认 profile 开 remote debugging 会弹「Allow remote debugging?」，无人值守时这个框没人点，AppleScript / cua 都会卡死。

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir="/Users/<user>/.browser-harness/chrome-profile" \
  --no-first-run --no-default-browser-check about:blank &
```

坑：
- 端口只监听 IPv6 → `curl http://127.0.0.1:9222` 不通，用 `http://localhost:9222` 或 `http://[::1]:9222`。
- websocket 握手报 `403 Forbidden ... rejected from origin` → 客户端加 `suppress_origin=True`，或启动参数加 `--remote-allow-origins=*`。
- 用 `scripts/cdp_client.py`，不要再手写一遍。

## 步骤 2：登录态

先判断要不要登录：`curl -sL -o /dev/null -w "%{url_effective}" <url>`，若跳到 `accounts.feishu.cn/accounts/page/login` 就需要。

- **不要试图复用用户日常浏览器的 cookie**：chi 日常浏览器可能是 Arc 而不是 Chrome，Chrome 里的 cookie 可能几个月没更新；复制 cookie DB 拿不到 session。解密要 Keychain 图形授权，屏幕锁着时会一直挂（`security find-generic-password` 超时）。
- **最快且可复现的办法是扫码登录**：
  1. CDP 打开目标页，等它跳到登录页。
  2. 抓二维码图：`document.querySelector('canvas').toDataURL('image/png')`，base64 存 png（比 Page.captureScreenshot 干净，不用裁图）。
  3. 用 `MEDIA:/path/qr.png` 发给用户，让他用手机端扫。
  4. 若页面文本里出现「刷新二维码」说明已失效，先点刷新再抓。
  5. 扫码后可能停在「飞书授权」页，需要点「授权」按钮才回到应用页。

## 步骤 3：读表单结构

一次性 dump 所有可交互元素和纵坐标，先排序再定位，别靠猜：

```js
[...document.querySelectorAll('input,textarea,select,[role=combobox]')].map(e=>({
  type:e.type, cls:(e.className||'').slice(0,40), ph:e.placeholder, val:e.value,
  y:Math.round(e.getBoundingClientRect().top)
}))
```

读下拉的可选项：用真实鼠标点开 select，再 dump `li,[role=option],[class*=option]`。

## 步骤 4：填写（React 组件必须真实事件）

- `el.click()` 对 React/aPaaS 组件**无效**，必须 `Input.dispatchMouseEvent` 发 mousePressed + mouseReleased 到元素中心坐标。
- 文本：真实点击聚焦 → `Input.insertText`（不要逐字符发 keyDown，中文会碎）。
- 下拉：点 select 的 `input[type=search]` → `insertText` 搜索词 → 等 1.2~1.5s → 按文本匹配选项 → 真实点击。搜索是**包含匹配**，查询词别取前 N 个字（查「深圳市多」可能命中一堆，查「多科电子」才准）。
- **同名主体必须全名精确匹配**：如「睿魔智能科技（杭州）」vs「（深圳）」，第一次随便匹配选中了错的那家。选完立刻用 `document.body.innerText` 复核，不对就重选。
- `document.querySelectorAll('input[type=text]')` 可能返回 0 —— 很多组件 `type` 是 IDL 默认值而非属性。用 `[...document.querySelectorAll('input')].filter(e=>e.type==='text')`。
- 富文本/多行框：先 `scrollIntoView({block:'center'})` 再点，否则坐标落在视口外点不到，值会静默丢失（要读 `textarea.value` 验证）。

## 步骤 5：整页截图确认（关键）

aPaaS/SPA 常用**内层滚动容器**，`captureBeyondViewport` 只能拿到视口高度，直接导致用户说「下面看不到」。

```js
// 先把滚动容器撑开，让整页一次渲染
[...document.querySelectorAll('*')]
  .filter(e=>e.scrollHeight>e.clientHeight+50 && e.clientHeight>200)
  .forEach(e=>{e.style.maxHeight='none'; e.style.height='auto'; e.style.overflow='visible';});
```

然后 `Page.captureScreenshot(format='png', captureBeyondViewport=True)`。用 PIL 检查图片高度（CSS px × DPR），确认覆盖到提交按钮。

发图时**附逐字段清单**（方案类型/主体/姓名/手机/…每项一行），用户核对成本最低。

## 步骤 6：提交与验证

- 点「提交」后页面会出现 loading 遮罩，**此时不代表成功**，等 3~5s 再查。
- 成功判据：`document.body.innerText` 出现「提交成功」，或 URL 跳到新页面（带 trace_event 之类参数）。
- 第二次及以后提交：重新 `Page.navigate` 回原表单 URL，不要依赖提交后的页面。

## 一次多单的表单

用户可能一次给多家客户。**第一单走完整流程（填→截图→确认→提交）**，拿到确认后第二单重复。每单独立截图确认，不要合并成一张图或批量提交。

更细的飞书 aPaaS / udesigner 选择器与字段实测见 `references/feishu-apaas-ud.md`。
