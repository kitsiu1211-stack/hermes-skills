#!/usr/bin/env node
// HTML -> PNG，用于一页纸框架图。
// 用法: node shot.js <input.html> <output.png> [width=1240] [scale=2]
//
// 为什么不用 playwright模块：很多机器上 playwright 的 npm 包装在了别处，
// 但 puppeteer-core 往往是全局装的，且 chromium 已经躺在 ms-playwright 缓存里。
// 本脚本先找 puppeteer-core（本地 -> 全局），再找可执行的 chromium。

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const [, , htmlArg, outArg, widthArg, scaleArg] = process.argv;
if (!htmlArg || !outArg) {
  console.error('Usage: node shot.js <input.html> <output.png> [width=1240] [scale=2]');
  process.exit(1);
}
const width = parseInt(widthArg || '1240', 10);
const scale = parseFloat(scaleArg || '2');
const html = path.resolve(htmlArg);
const out = path.resolve(outArg);

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
  const linuxCache = path.join(process.env.HOME || '', '.cache/ms-playwright');
  const globs = [
    path.join(cache, 'chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell'),
    path.join(cache, 'chromium_headless_shell-*/chrome-headless-shell-mac-x64/chrome-headless-shell'),
    path.join(cache, 'chromium-*/chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium'),
    path.join(cache, 'chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
    path.join(linuxCache, 'chromium-*/chrome-linux/chrome'),
    path.join(linuxCache, 'chromium_headless_shell-*/chrome-linux/headless_shell'),
  ];
  for (const g of globs) {
    try {
      const hit = execSync(`ls -d ${g} 2>/dev/null | head -1`, { encoding: 'utf8' }).trim();
      if (hit && fs.existsSync(hit)) return hit;
    } catch (_) { /* next */ }
  }
  const system = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ];
  for (const s of system) if (fs.existsSync(s)) return s;
  return undefined; // 让 puppeteer 自己找
}

(async () => {
  const puppeteer = loadPuppeteer();
  const browser = await puppeteer.launch({
    executablePath: findChrome(),
    args: ['--no-sandbox', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width, height: 1000, deviceScaleFactor: scale });
  await page.goto('file://' + html, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 600)); // 等字体落位
  const h = await page.evaluate(() => document.body.scrollHeight);
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  console.log(`ok: ${out}  (${width}x${h} @${scale}x -> ${width * scale}x${h * scale}px)`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
