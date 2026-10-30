---
name: feishu-apaas-form-filler
description: 以用户身份代填飞书 aPaaS(apaas.feishuapp.cn) 表单。先登录、再填、截图确认、提交。
version: 1.0.0
author: Hermes Agent
license: MIT
category: feishu
metadata:
  hermes:
    tags: [feishu, apaas, form, cdp, browser-automation]
---

# 飞书 aPaaS 表单代填

## When to Use

用户发来 `apaas.feishuapp.cn/ae/apps/...` 链接，并说「帮我填一下 / 以我的身份填 / 提交个线索」时用。

也要用的情况：表单需要登录态、提交后记录提交人身份的飞书内部系统页面（aPaaS / 妙搭表单）。

核心约束：表单要登录态，提交后记的是**提交人身份**。必须真的用用户的飞书账号登录，不能匿名提交。

## 铁律

1. **提交前必须截图给用户确认**，用户明确说「提交」才点提交。这条是用户 2026-10-28 明确要求的。
2. 截图要**截全**，用户会检查底部字段。用「撑开滚动容器 + captureBeyondViewport」，见下方。
3. 提交后必须验证成功（页面出现「提交成功」或 URL 跳到 `aadh...` 新页面），看不到证据不算完成。
4. 干完 kill 掉临时 Chrome，别把登录态留在机器上。
5. 一条线索一个提交。多家客户 = 多次填 + 多次提交，每次都单独截图确认。

## 第一步：拿到能用的浏览器

`browser-use` / browser-harness 在这台机器上经常连不上（Chrome 弹「Allow remote debugging?」且桌面锁屏时点不了）。别在它上面耗时间，直接用裸 CDP。

### 1.1 复制用户的 Chrome profile

用户日常浏览器可能不是 Chrome（2026-10 实测：日常用 Arc，Chrome 的 `Default` 是 3 月的旧 profile，`Profile 1` 才是活的）。

```bash
C="/Users/bytedance/Library/Application Support/Google/Chrome"
ls -la "$C"/*/Cookies                      # 找 mtime 最新的那个 profile
cp -R "$C/Profile 1" ~/.browser-harness/chrome-profile/Default
cp "$C/Local State"  ~/.browser-harness/chrome-profile/"Local State"
```

cookie 拷过去多数情况还是**登不上**（Keychain 解密、SSO 域名不全），所以别指望复用登录态，直接准备扫码。

### 1.2 启动带调试端口的 Chrome

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir="/Users/bytedance/.browser-harness/chrome-profile" \
  --profile-directory=Default --no-first-run --no-default-browser-check \
  --window-size=1440,1000 about:blank
```

用 terminal `background=true` 起。验证：`curl -s "http://[::1]:9222/json/version"`（监听在 IPv6，用 127.0.0.1 会连不上）。

### 1.3 扫码登录（唯一稳定路径）

页面会跳到 `accounts.feishu.cn/accounts/page/login`。取二维码发给用户：

```js
document.querySelector('canvas').toDataURL('image/png')   // base64，存成 png
```

⚠️ 二维码有时效，先点「刷新二维码」再取，取完立刻发给用户。用户扫完页面会自动跳到授权页，点「授权」按钮（文字正好是「授权」）才进入应用。

Keychain 读 cookie（`security find-generic-password`）会弹 GUI 确认框，桌面锁屏时直接挂死，不要走这条路。

## 第二步：读写表单

脚本都在本 skill 的 `scripts/` 下，直接拿去用，别重写：

- `scripts/cdp.py` — 裸 CDP 客户端，`CDP(url).js()/.click()/.type_text()/.shot(full_page=True)`
- `scripts/apaas_fill.py` — 表单读写助手，`pick_select / fill_text / fill_textarea / state / values / submit`

```bash
python3 scripts/cdp.py /tmp/xxx.js        # 跑一段 JS 并打印返回值
```

```python
import sys; sys.path.insert(0, "<skill_dir>/scripts")
from cdp import CDP, page_ws
import apaas_fill as A
u, t = page_ws("apaas.feishuapp.cn")
A.bind(CDP(u))
A.pick_select(1, "汇联易", "汇联易费控和商旅解决方案", exact=True)
A.fill_text(0, "刘鑫蕾")
A.fill_textarea("给张晨")
print(A.values(), A.state())
```

### 必须知道的四个坑

| 坑 | 现象 | 解法 |
|---|---|---|
| React 不认 `.click()` | `el.click()` 后下拉不展开 | 用 `Input.dispatchMouseEvent` 真鼠标事件，坐标从 `getBoundingClientRect()` 取 |
| `input[type=text]` 选不到 | `querySelectorAll('input[type=text]').length === 0` | type 是 IDL 默认值不是 attribute，改用 `[...querySelectorAll('input')].filter(e=>e.type==='text')` |
| textarea 填不进 | 点击后 `insertText` 无效 | 先 `scrollIntoView({block:'center'})` 再取坐标点击，否则点在视口外 |
| 下拉搜索匹配到错的公司 | 搜「睿魔」拿到「睿魔智能科技（杭州）」 | 把完整公司名当搜索词，并且**精确匹配** option 文本，别用 contains |

### 下拉字段通用做法

1. `input[type=search]` 按 `getBoundingClientRect().y` 排序，序号即字段顺序（方案类型那种多选也会占一个）
2. 点开 → `Input.insertText` 输关键词 → 等 1.5s → 枚举 `li,[role=option],[class*=option]` 的可见项
3. 按文本命中 → 真鼠标点击选项中心
4. 没命中就按 `Escape` 关掉，别留一个展开的下拉挡住后面的字段

### 截全图

页面滚动在内部容器（`class*="kunlun-root"`），`window.scrollTo` 没用，`captureBeyondViewport` 也只会截视口高度。

```js
[...document.querySelectorAll('*')]
  .filter(e=>e.scrollHeight>e.clientHeight+50 && e.clientHeight>200)
  .forEach(e=>{e.style.maxHeight='none'; e.style.height='auto'; e.style.overflow='visible';});
document.documentElement.style.overflow='visible';
document.body.style.overflow='visible';
```

撑开后再 `Page.captureScreenshot(format="png", captureBeyondViewport=True)`，得到整页（2x DPR，高度约 2272px）。

### 提交与验证

```js
[...document.querySelectorAll('button')].find(e=>e.textContent.trim()==='提交')
```

先 `scrollIntoView` 再取坐标点击。点完可能出现几秒 loading 转圈，等 4-6 秒再查：`document.body.innerText` 出现「提交成功」且 URL 变成 `.../aadhXXXX` 即成功。

我踩过的假阴性：点完 5 秒时读到的还是旧 URL（导航未完成），误判成没提交。**看到「提交成功」文字才算数**，别只信 URL。

## 参考案例（2026-10-28 ISV 线索提报）

字段：方案类型（多选，默认已选联盟+精选）/ 解决方案（下拉方案库）/ 客户公司（下拉公司库，可搜索）/ 客户需求人职位 / 客户姓名 / 客户手机号 / 线索推荐人 / 客户预算 / 客户需求简述（textarea）。

推荐人搜自己名字会返回「袁鑫杰yuanxinjie.01@bytedance.com」，选中后显示成「袁鑫杰」。

## 收尾

```bash
kill <chrome_pid>
```

然后回报：填了哪几家、每家的关键字段、提交是否成功。多一条线索就多一轮截图确认。
