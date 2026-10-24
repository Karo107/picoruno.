// 使い方: node shot.js <html> <outdir> <steps.json相当のJS関数ファイル>
// ゲームを開いてコンソールエラーを集め、テスト手順を実行してスクリーンショットを撮る。
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [file, outdir, stepsFile, vp] = process.argv.slice(2);
  const steps = require(path.resolve(stepsFile));
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'], proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined });
  const [w, h] = (vp || '390x844').split('x').map(Number);
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2, hasTouch: false, ignoreHTTPSErrors: true });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  await page.goto('file://' + path.resolve(file));
  await page.waitForTimeout(1500);
  let n = 0;
  const shot = async name => { await page.screenshot({ path: `${outdir}/${String(++n).padStart(2, '0')}-${name}.png` }); };
  try { await steps(page, shot); } catch (e) { errors.push('step error: ' + e.message); }
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
  await browser.close();
})();
