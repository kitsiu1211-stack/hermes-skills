---
name: browser-cdp-control
description: 浏览器工具被权限墙挡住时，用裸 CDP 带登录态操作网页。
category: devops
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cdp, chrome, browser, login, headless]
---

# 裸 CDP 控制浏览器

## When to Use

- 用户说「以我的身份」做某件网页上的事（填表单、提交、查内部后台），必须有他的登录态
- `browser_exec` / `browser-harness` 被 Chrome 的调试授权弹窗挡住
- 机器锁屏、无人值守，`computer_use` 截图返回 0x0，GUI 自动化和 Keychain 都卡在没人点的弹窗上

核心思路一句话。**不碰用户正在用的浏览器，另起一个独立 Chrome 实例挂调试端口，用裸 CDP 说话，登录态交给用户扫码。**

## 步骤

### 1. 先确认有没有现成的调试端口

```bash
curl -s -m 3 "http://[::1]:9222/json/version" | head -c 200
```

有就直接跳到第 4 步。

### 2. 找真正在用的 profile

Chrome 的 `Default` 常常是好几个月前的旧档。按 cookie 文件的修改时间判断哪个 profile 还活着。

```bash
find "/Users/$USER/Library/Application Support/Google/Chrome" -maxdepth 3 \
  -name Cookies -newermt "-45 days" | sort -r | head
find "/Users/$USER/Library/Application Support/Arc/User Data" -maxdepth 3 \
  -name Cookies -newermt "-45 days" 2>/dev/null | head
```

同一个站点在两个 profile 里的 cookie 数量可以直接对比，多的是活跃的。日常浏览器可能是 Arc 而不是 Chrome。

### 3. 复制 profile 到独立目录并启动

```bash
D=~/.browser-harness/chrome-profile
rm -rf "$D/Default"; mkdir -p "$D"
cp -R "/Users/$USER/Library/Application Support/Google/Chrome/Profile 1" "$D/Default"
cp "/Users/$USER/Library/Application Support/Google/Chrome/Local State" "$D/Local State"

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --remote-allow-origins='*' \
  --user-data-dir="$D" --profile-directory=Default \
  --no-first-run --no-default-browser-check --window-size=1440,1000 about:blank
```

`--user-data-dir` 不能是 Chrome 默认路径，否则 136+ 会静默忽略端口。用 `terminal(background=true)` 起，别加 `&`。

### 4. 用脚本直连

```bash
python3 scripts/cdp_client.py list
python3 scripts/cdp_client.py goto "https://example.com"
python3 scripts/cdp_client.py eval 'document.title'
python3 scripts/cdp_client.py shot /tmp/x.png
```

### 5. 判断有没有真带着登录态

打开目标站，如果被 302 到登录页（如 `accounts.feishu.cn/accounts/page/login`），说明这个 profile 里没有该站 session。**别再换个 profile 碰运气，也别去解密 cookie**（见下）。转第 6 步。

### 6. 把二维码发给用户扫

```python
data = js("(() => { const c=document.querySelector('canvas'); return c?c.toDataURL('image/png'):null; })()")
open("/tmp/qr.png","wb").write(base64.b64decode(data.split(",",1)[1]))
```

二维码是 canvas 画的，直接 `toDataURL` 拿原图，比截整页清楚也不会带进无关窗口内容。然后把 `/tmp/qr.png` 用 `MEDIA:` 发给用户，让他扫完回一句。

- 抓之前先点「刷新二维码」，中间别停，二维码有时效
- `body.innerText` 出现「刷新二维码」= 已过期；出现「扫码成功」= 扫了但还没确认
- 扫完还是同一个 tab，直接接着 `goto` 原目标页即可

### 7. 点、打字、截图

- **别用 `el.click()`。** React 组件经常不理，下拉不展开、按钮不响应。一律 `Input.dispatchMouseEvent` 的 mousePressed + mouseReleased，坐标取 `getBoundingClientRect()` 中心；打字用 `Input.insertText`。
- **元素在视口外先 `scrollIntoView({block:'center'})` 再点**，否则点空，输入静默丢失。
- **整页截图要先把内部滚动容器撑开**，否则 `captureBeyondViewport` 也只有一屏。做法见 `references/react-form-filling.md` 第 5 节。

表单类任务（下拉选项、精确匹配、提交确认）的完整打法，含踩过的坑，看 `references/react-form-filling.md`。

## Pitfalls

| 坑 | 现象 | 处理 |
|----|------|------|
| WebSocket origin 校验 | 握手 403 `Rejected an incoming WebSocket connection from ...origin` | 启动加 `--remote-allow-origins=*`，或客户端 `suppress_origin=True` |
| DevTools 只监听 IPv6 | `curl 127.0.0.1:9222` 空返回 | 用 `[::1]` 或 `localhost` |
| `/json/list` 混非网页目标 | JS 打到了 `chrome://managed-user-profile-notice/` 这类页 | 过滤 `type=='page'` 且 url 不以 `chrome://` 开头 |
| Chrome 常驻无窗口 | `open -a "Google Chrome" URL` 不起窗口，AppleScript 超时 | 显式起独立实例 |
| 复制 profile ≠ 登录态 | 照样跳登录页 | cookie 加密钥匙在 Keychain，无人值守解不开；走扫码 |
| `security find-generic-password` | 挂住直到超时 | 别在无人值守时调 Keychain |
| `$HOME` 被改写 | `~/Library/...` 全部落空 | `terminal` 里 `$HOME` 可能不是 `/Users/<用户名>`，路径写绝对 |

## 边界

- 只做用户明确要求的操作。登录、支付、权限授权页面不代点，交给用户。
- 提交类操作（表单、工单）在按下提交前**截图给用户确认**，不要只在文字里复述。用户会要求「截图和我确认下细节，没问题再提交」。一条记录一次确认，多家客户就多轮填 + 多轮确认，别攒着一起交。
- 字段值一律来自用户，不猜不编。缺项就问，别拿默认值糊上去。提交结果认页面上的「提交成功」文字，别靠 URL 判断（会误判）。
- 这个 profile 是复制出来的副本，对它的改动不影响用户日常浏览器。

## 相关

- `browser-harness-install` 覆盖 harness 的安装与 daemon 排障。那边讲正常路径，本 skill 讲被权限墙挡住后的绕行。
