#!/usr/bin/env node
/**
 * HTML → PNG for Chinese consulting posters.
 *
 * Usage:
 *   node render_png.js <input.html> <output.png> [width] [scale]
 *
 * Why not playwright: the ljg-card skill's capture.js requires the `playwright`
 * node module, which is not installed in that skill dir. This machine does have
 * puppeteer-core globally and a chromium build cached by playwright. So we point
 * puppeteer-core at the cached binary — no install needed.
 *
 * Defaults: width 1240 (A4-ish portrait at 1x), scale 2 (deviceScaleFactor) →
 * 2480px wide output, which stays crisp when opened on desktop and readable on
 * phone after tap-zoom. Full page height is auto-measured, so the HTML does not
 * need a fixed height — let content flow and this script captures all of it.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

function loadPuppeteer() {
  const candidates = [
    'puppeteer-core',
    'puppeteer',
    path.join(os.homedir(), '.npm-global/lib/node_modules/puppeteer-core'),
    '/usr/local/lib/node_modules/puppeteer-core',
    '/opt/homebrew/lib/node_modules/puppeteer-core',
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) {}
  }
  throw new Error('puppeteer-core not found. Install: npm i -g puppeteer-core');
}

function findChromium() {
  const roots = [
    path.join(os.homedir(), 'Library/Caches/ms-playwright'), // macOS
    path.join(os.homedir(), '.cache/ms-playwright'),          // linux
    path.join(os.homedir(), 'AppData/Local/ms-playwright'),   // windows
  ];
  const hits = [];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    for (const dir of fs.readdirSync(root)) {
      const base = path.join(root, dir);
      // headless shell (fastest, no window)
      for (const pattern of [
        'chrome-headless-shell-mac-arm64/chrome-headless-shell',
        'chrome-headless-shell-mac-x64/chrome-headless-shell',
        'chrome-headless-shell-linux64/chrome-headless-shell',
        'chrome-headless-shell-win64/chrome-headless-shell.exe',
      ]) {
        const p = path.join(base, pattern);
        if (fs.existsSync(p)) hits.push({ p, rank: 0 });
      }
      // full chromium as fallback
      for (const pattern of [
        'chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium',
        'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
        'chrome-linux/chrome',
        'chrome-win/chrome.exe',
      ]) {
        const p = path.join(base, pattern);
        if (fs.existsSync(p)) hits.push({ p, rank: 1 });
      }
    }
  }
  if (!hits.length) {
    throw new Error('No cached chromium found under ms-playwright. Run: npx playwright install chromium');
  }
  // newest playwright build wins (dir names are date-sorted-ish), headless shell preferred
  hits.sort((a, b) => (a.rank - b.rank) || b.p.localeCompare(a.p));
  return hits[0].p;
}

(async () => {
  const [html, out, widthArg, scaleArg] = process.argv.slice(2);
  if (!html || !out) {
    console.error('Usage: node render_png.js <input.html> <output.png> [width] [scale]');
    process.exit(1);
  }
  const width = parseInt(widthArg, 10) || 1240;
  const scale = parseFloat(scaleArg) || 2;

  const puppeteer = loadPuppeteer();
  const executablePath = process.env.CHROME_PATH || findChromium();
  console.log('chromium:', executablePath);

  const browser = await puppeteer.launch({
    executablePath,
    args: ['--no-sandbox', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width, height: 1000, deviceScaleFactor: scale });
  await page.goto('file://' + path.resolve(html), { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 600)); // let webfonts/layout settle
  const height = await page.evaluate(() => document.body.scrollHeight);
  console.log('page height:', height);
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  console.log('wrote', out);
})().catch((e) => { console.error(e.message || e); process.exit(1); });
