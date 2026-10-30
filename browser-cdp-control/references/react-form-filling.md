# React 表单场景实战打法

面向 aPaaS / 妙搭 / 各类 React + 组件库（ud / semi / antd）表单。2026-10-28 在飞书 aPaaS「ISV线索提报」上完整验证，两张表单提交成功。

## 1. 先盘字段，别急着填

```js
(() => {
  const out = [];
  document.querySelectorAll('input,textarea,select,[role=combobox]').forEach(e => {
    const r = e.getBoundingClientRect();
    out.push({tag:e.tagName, type:e.type, ph:e.placeholder||'', val:(e.value||'').slice(0,30),
              w:Math.round(r.width), y:Math.round(r.top)});
  });
  return JSON.stringify(out);
})()
```

再配一张截图看标签，两者对一下就知道第几个框对应哪一项。**下拉的搜索框 `input[type=search]` 按 y 排序，序号就是字段顺序**，多选字段（那种一排 tag 的）也占一个位。

## 2. 点不开下拉 = 没用真鼠标

`el.click()` 在 React 组件上大概率无效。用 CDP 真事件：

```python
c.send("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
c.send("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
```

坐标取 `getBoundingClientRect()` 的中心。点开后等 0.9s，再 `Input.insertText` 输关键词，等 1.5s 枚举选项：

```js
[...document.querySelectorAll('li,[role=option],[class*=option]')]
  .filter(e=>e.offsetParent!==null && e.textContent.trim())
```

去重后按文本命中，再真鼠标点选项中心。**没命中一定要按 Escape 关掉下拉**，否则展开的浮层会挡住后面所有字段，表现为「下一个字段点不动」。

## 3. 三个玄学坑

| 坑 | 现象 | 解法 |
|---|---|---|
| `input[type=text]` 选不到 | `querySelectorAll('input[type=text]').length === 0`，但元素明明有 | type 是 IDL 默认值不是 attribute。用 `[...querySelectorAll('input')].filter(e=>e.type==='text')` |
| 下拉搜索短词命中不全 | 搜「多科」出来 11 家名字带「多」的，独独没有要找的那家；搜「多科电子」第一行就是 | 服务端搜索，用**更长更有区分度**的词重试一次（公司名里最特别的两个字 + 行业词） |
| 同名主体选错 | 搜「睿魔」拿到「睿魔智能科技（杭州）」，要的是「（深圳）」 | 用完整名称做**精确匹配**，别用 contains |

## 4. textarea 要先滚进视野

```python
c.js("document.querySelector('textarea').scrollIntoView({block:'center'})")
time.sleep(0.7)
# 再取 rect、点击、Input.insertText
```

不滚就直接点，坐标落在视口外，文字静默丢失，`innerText` 也看不出来（textarea 的 value 不进 innerText），一定要单独查 `document.querySelector('textarea').value`。

## 5. 截整页给用户确认

内部滚动容器会让 `window.scrollTo` 和 `captureBeyondViewport` 都只拿一屏。先撑开：

```js
[...document.querySelectorAll('*')]
  .filter(e=>e.scrollHeight>e.clientHeight+50 && e.clientHeight>200)
  .forEach(e=>{e.style.maxHeight='none';e.style.height='auto';e.style.overflow='visible';});
document.documentElement.style.overflow='visible';
document.body.style.overflow='visible';
```

再 `Page.captureScreenshot({format:"png", captureBeyondViewport:true})`。产出是 2x DPR，像素高除以 2 应该接近 `scrollHeight`。截不全用户会直接说「下面看不到」，别让他重复一遍。

## 6. 提交：认文字，别认 URL

点提交用同样的真鼠标事件（先 `scrollIntoView`）。点完会转几秒 loading。

**只看 `document.body.innerText` 里有没有「提交成功」。** 实测踩过一次假阴性，点完 5 秒读到的还是旧 URL，误判成没提交，其实马上就成功了。URL 变成新的 `aadhXXXX` 页面是辅助证据，不是判据。

## 7. 流程铁律

- 用户会明确要求「提交前先截图给我确认」。**一条记录一次确认**，多家客户就是多轮填 + 多轮确认，别攒着一起交。
- 字段值一律来自用户，不猜。用户给的信息缺项就问，别拿默认值填。
- 提交成功一条就先回报一条，别等全部到齐。

## 8. 复用

`feishu-apaas-form-filler` skill 里有一份按本流程封装的 `apaas_fill.py`（`pick_select / fill_text / fill_textarea / state / values / submit`），封得很贴合飞书 aPaaS 的类名，换系统要按上面的通用打法改。
