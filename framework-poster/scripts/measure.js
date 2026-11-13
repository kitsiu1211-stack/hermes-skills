#!/usr/bin/env node
// 打印一页纸图里所有卡片的真实几何，替代「用眼睛判断对齐」。
// 用法: node measure.js <input.html> [selector1,selector2,...]
//   默认选择器覆盖本 skill 所有版式模块。输出每张卡的 top / bottom / height。
//   所有同类卡片 height 一致 = 已对齐，不要再改 CSS。

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const [, , htmlArg, selArg] = process.argv;
if (!htmlArg) {
  console.error('Usage: node measure.js <input.html> [selectors]');
  process.exit(1);
}
const html = path.resolve(htmlArg);
if (!fs.existsSync(html)) {
  console.error('not found: ' + html);
  process.exit(1);
}
const SELECTORS =
  selArg ||
  '.node,.stg,.card,.step,.br,.tp,.tg,.chan,.chipbox,.quote,.risk-l,.risk-r';

function loadPuppeteer() {
  const candidates = [
    'puppeteer-core',
    'puppeteer',
    path.join(process.env.HOME || '', '.npm-global/lib/node_modules/puppeteer-core'),
    path.join(process.env.HOME || '', '.npm-global/lib/node_modules/puppeteer'),
    '/opt/homebrew/lib/node_modules/puppeteer-core',
    '/usr/local/lib/node_modules/puppeteer-core',
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) { /* next */ }
  }
  throw new Error('找不到 puppeteer-core。装一个: npm i -g puppeteer-core');
}

function findChrome() {
  const cache = path.join(process.env.HOME || '', 'Library/Caches/ms-playwright');
  const globs = [
    path.join(cache, 'chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell'),
    path.join(cache, 'chromium_headless_shell-*/chrome-headless-shell-mac-x64/chrome-headless-shell'),
    path.join(cache, 'chromium-*/chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium'),
    path.join(cache, 'chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
  ];
  for (const g of globs) {
    try {
      const hit = execSync(`ls -d ${g} 2>/dev/null | head -1`, { encoding: 'utf8' }).trim();
      if (hit && fs.existsSync(hit)) return hit;
    } catch (_) { /* next */ }
  }
  for (const s of ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium']) {
    if (fs.existsSync(s)) return s;
  }
  return undefined;
}

(async () => {
  const puppeteer = loadPuppeteer();
  const browser = await puppeteer.launch({
    executablePath: findChrome(),
    args: ['--no-sandbox', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1240, height: 1000, deviceScaleFactor: 1 });
  await page.goto('file://' + html, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 500)); // 等字体落位

  const box = await page.evaluate((sel) => {
    return [...document.querySelectorAll(sel)].map((e, i) => {
      const b = e.getBoundingClientRect();
      const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 14);
      return { i, cls: e.className || '', top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height), t };
    });
  }, SELECTORS);

  const pageH = await page.evaluate(() => document.body.scrollHeight);
  console.log(`page: 1240 x ${pageH}`);
  if (!box.length) {
    console.log('no matching elements — pass selectors as 2nd arg');
  }
  for (const b of box) {
    console.log(
      `#${String(b.i).padStart(2, '0')} ${String(b.cls).padEnd(16)} top=${String(b.top).padStart(5)} bottom=${String(b.bottom).padStart(5)} h=${String(b.h).padStart(4)}  ${b.t}`
    );
  }
  // 分组汇总：同类元素高度是否一致
  const byCls = {};
  for (const b of box) (byCls[b.cls] ||= []).push(b.h);
  console.log('--- height groups ---');
  for (const [k, v] of Object.entries(byCls)) {
    const uniq = [...new Set(v)];
    console.log(`${k}: ${v.length} 个, heights=${v.join(',')} ${uniq.length === 1 ? 'ALIGNED' : 'MISMATCH'}`);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
