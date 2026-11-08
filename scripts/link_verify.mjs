// KnowUS link checker, step 2: a real browser's second opinion before a link is called "down".
// Reads links-pending.json (links that failed 2 checks in a row), opens each in headless Chromium,
// writes links-verified.json {results:{url:{ok,status,why}}}. DNS failures and parked domains skip this.
import fs from 'node:fs';
let chromium;
try { ({ chromium } = await import('playwright')); }
catch { const m = await import(process.env.PW_CORE || '/home/user/node_modules/playwright-core/index.js'); chromium = (m.default || m).chromium; }
const state = JSON.parse(fs.readFileSync('data/link-status.json', 'utf8')).links;
const pending = (JSON.parse(fs.readFileSync('links-pending.json', 'utf8')).urls || [])
  .filter(u => !['dns', 'parked'].includes((state[u] || {}).why));
const CAP = +(process.env.VERIFY_CAP || 300), CONC = +(process.env.VERIFY_CONC || 10), BUDGET = +(process.env.VERIFY_MIN || 12) * 60e3;
const PARKED = /(this domain (name )?(is|may be) for sale|buy this domain|domain is parked|parkingcrew|sedoparking|hugedomains\.com|domain has expired)/i;
const CHAL = /(just a moment|checking your browser|verify you are human|attention required|captcha|cloudflare|ddos protection)/i;
const list = pending.slice(0, CAP), results = {}, t0 = Date.now();
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined, args: ['--no-sandbox'] });
async function one(u) {
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true, locale: 'en-US',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36' });
  const page = await ctx.newPage();
  let r = { ok: false, why: 'browser-failed' };
  try {
    const resp = await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 25000 });
    const st = resp ? resp.status() : 0;
    await page.waitForTimeout(1500);
    const txt = (await page.evaluate(() => (document.title || '') + ' ' + (document.body ? document.body.innerText.slice(0, 4000) : '')).catch(() => '')) || '';
    if (st && st < 400 && !PARKED.test(txt)) r = { ok: true, status: st };
    else if ([401, 403, 429].includes(st) && txt.trim().length > 0) r = { ok: true, status: st };   // the site answered; it just refuses robots
    else if (st === 503 && CHAL.test(txt)) r = { ok: true, status: st };                               // a bot challenge page: the site is there
    else r = { ok: false, status: st, why: PARKED.test(txt) ? 'parked' : (st ? 'http' + st : 'browser-failed') };
  } catch (e) { r = { ok: false, why: String(e.message || e).split('\n')[0].slice(0, 80) }; }
  await ctx.close().catch(() => {});
  return r;
}
let i = 0;
async function lane() { while (i < list.length && Date.now() - t0 < BUDGET) { const u = list[i++]; results[u] = await one(u); } }
await Promise.all(Array.from({ length: CONC }, lane));
await browser.close();
fs.writeFileSync('links-verified.json', JSON.stringify({ results }));
const ok = Object.values(results).filter(r => r.ok).length;
console.log(`browser checked ${Object.keys(results).length} of ${pending.length}: ${ok} load fine (bot-blocked only), ${Object.keys(results).length - ok} really down`);
