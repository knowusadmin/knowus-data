// KnowUS app-flow tests (owner asked for constant testing, Nov 10 2026).
// Opens the app at phone width the way the Android app 1.3 does: same user agent tag, a mock of the app's JS bridge
// (window.KnowUSAndroid with exactly app 1.3's methods) and window.confirm/alert/prompt that do nothing, as the
// app's WebView does (it has no dialog handler, so confirm() answers "no" without showing anything).
//   node audit/app-tests.mjs [--site https://knowus.sites.tab.bot/] [--local SITE_DIR] [--width 390] [--out out/app-tests]
// Exit 1 when any test fails. Results: <out>/results.json + results.md (+ a screenshot per failure).
// Read-only against the live project: no account is created or deleted. The delete-account check stops at the
// "type DELETE" step and cancels; it runs only when KNOWUS_TEST_EMAIL / KNOWUS_TEST_PASSWORD are set.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { makePolicy } from './policy.mjs';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(process.env.PW_CORE || 'playwright-core')); }
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const SITE = (arg('site', process.env.KNOWUS_SITE || 'https://knowus.sites.tab.bot/')).replace(/\/?$/, '/');
const LOCAL = arg('local', ''); const W = +arg('width', '390'); const OUT = arg('out', 'out/app-tests');
const ADDR = process.env.KNOWUS_TEST_ADDRESS || '2301 Milton Rd, Cleveland, OH 44118';
fs.mkdirSync(OUT, { recursive: true });
const ORIGIN = new URL(SITE).origin;
const MT = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webmanifest': 'application/manifest+json', '.webp': 'image/webp' };
const results = []; let page, ctx;
const BRIDGE = () => {
  const log = window.__kus = { calls: [], dialogs: [] };
  const rec = (m, a) => { log.calls.push({ m, a: a.map(x => typeof x === 'string' && x.length > 200 ? '[' + x.length + ' chars]' : x) }); };
  const pdfOk = b => { try { const s = atob(String(b || '').replace(/^data:[^,]*,/, '').slice(0, 64)); return s.startsWith('%PDF'); } catch { return false; } };
  window.KnowUSAndroid = {
    version() { rec('version', []); return '1.3'; },
    capabilities() { rec('capabilities', []); return 'googleSignIn,googleSilent,saveFile,shareFile,alerts'; },
    getAppCheckToken(id) { rec('getAppCheckToken', [id]); setTimeout(() => window.KUS_NATIVE_CB && window.KUS_NATIVE_CB(id, JSON.stringify({ ok: false, code: 'unavailable', message: 'test' })), 50); },
    googleSignIn(id) { rec('googleSignIn', [id]); },
    getGoogleIdTokenSilent(e, id) { rec('getGoogleIdTokenSilent', [e, id]); },
    googleSignOut() { rec('googleSignOut', []); },
    saveFile(b, n, m) { rec('saveFile', [b, n, m]); log.lastSave = { pdf: pdfOk(b), name: n, mime: m, len: (b || '').length }; return pdfOk(b) ? 'saved' : 'error'; },
    shareFile(b, n, m) { rec('shareFile', [b, n, m]); return pdfOk(b) ? 'shared' : 'error'; },
    setTracked(j) { rec('setTracked', [j]); },
    notificationStatus() { rec('notificationStatus', []); return 'denied'; },
    requestNotifications() { rec('requestNotifications', []); },
    toast(r) { rec('toast', [r]); },
  };
  window.confirm = (q) => { log.dialogs.push('confirm: ' + q); return false; };
  window.alert = (q) => { log.dialogs.push('alert: ' + q); };
  window.prompt = (q) => { log.dialogs.push('prompt: ' + q); return null; };
  window.print = () => { log.dialogs.push('print dialog'); };
  try { localStorage.setItem('kus_session', '1'); } catch (e) {}
};
async function newPage() {
  if (ctx) await ctx.close();
  ctx = await browser.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 2, serviceWorkers: 'block', isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.0.0 Mobile Safari/537.36 KnowUS-Android/1.3' });
  if (LOCAL) await ctx.route('**/*', async r => {
    const u = new URL(r.request().url());
    if (u.origin === ORIGIN) { let p = decodeURIComponent(u.pathname); if (p.endsWith('/')) p += 'index.html'; const f = path.join(LOCAL, p);
      if (fs.existsSync(f) && fs.statSync(f).isFile()) return r.fulfill({ path: f, contentType: MT[path.extname(f)] || 'application/octet-stream' }); return r.fulfill({ status: 404, body: 'nf' }); }
    return r.continue();
  });
  await ctx.addInitScript(BRIDGE);
  page = await ctx.newPage(); page.__errs = [];
  page.on('pageerror', e => page.__errs.push(String(e).slice(0, 300)));
  return page;
}
const go = async (hash, wait = 2500) => { await page.goto(SITE + (hash || '#/'), { waitUntil: 'domcontentloaded', timeout: 45000 }); await page.waitForTimeout(wait); await page.evaluate(() => { document.documentElement.classList.remove('gated'); const g = document.getElementById('gate'); if (g) g.style.display = 'none'; }); };
const text = () => page.evaluate(() => (document.getElementById('app') || document.body).innerText);
const kus = () => page.evaluate(() => window.__kus);
async function test(name, fn) {
  const t0 = Date.now(); let ok = true, msg = '';
  try { msg = (await fn()) || ''; } catch (e) { ok = false; msg = String(e && e.message || e).slice(0, 400); }
  try { const k = await kus(); if (k && k.dialogs && k.dialogs.length) { ok = false; msg += (msg ? ' · ' : '') + 'used a browser dialog the app cannot show: ' + k.dialogs.join(' | '); } } catch {}
  const errs = (page && page.__errs || []).filter(e => !/Failed to fetch|NetworkError|Load failed|AbortError|appCheck|app-check/i.test(e));
  if (errs.length) { ok = false; msg += (msg ? ' · ' : '') + 'page error: ' + errs.join(' | '); }
  if (!ok) { try { await page.screenshot({ path: path.join(OUT, name.replace(/\W+/g, '-') + '.png') }); } catch {} }
  results.push({ name, ok, ms: Date.now() - t0, msg }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (msg ? ' — ' + msg : ''));
}
const must = (c, m) => { if (!c) throw new Error(m); };
const browser = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined, args: ['--no-sandbox'] });



// v84: Back steps back inside the tab you're in (Shmuel, Nov 12 2:25 AM: on a bill page Back jumped him to the Learn tab).
// At a tab's first step Back goes to the tab you were on before, where you left it (scroll, search). Same for the browser /
// Android Back (the app's WebView goBack). Lists come back at the same spot with the same search.
await newPage();
await test('v84: Back stays inside the tab (bill → Bills list at the same spot and search, person → Officials list); at a tab\'s first step it goes to the previous tab where you left it; Android/browser Back the same; deep links', async () => {
  const H = () => page.evaluate(() => location.hash);
  const backShown = () => page.evaluate(() => { const b = document.getElementById('back'); return !!b && !b.hidden && b.getBoundingClientRect().width > 0; });
  const tapBack = async (w = 2500) => { await page.click('#back'); await page.waitForTimeout(w); };
  const curTab = () => page.evaluate(() => { const a = document.querySelector('.tabbar a[aria-current="page"]'); return a ? a.dataset.tab : ''; });
  const tab = async (t, w = 3000) => { await page.click('.tabbar a[data-tab="' + t + '"]'); await page.waitForTimeout(w); };
  const out = [];
  // Learn: open a document page inside the tab and scroll a little
  await go('#/founding', 3000);
  const lh = await page.evaluate(() => { const a = [...document.querySelectorAll('#app a[href^="#/"], #app [data-href]')].find(x => /^#\/(constitution|declaration|federalist|learn)/.test(x.getAttribute('href') || x.getAttribute('data-href') || '')); return a ? (a.getAttribute('href') || a.getAttribute('data-href')) : ''; });
  must(lh, 'no Learn link on the Learn hub');
  await page.evaluate(h => { location.hash = h; }, lh); await page.waitForTimeout(3000);
  const learnHash = await H(); await page.evaluate(() => window.scrollTo(0, 300)); await page.waitForTimeout(300); const learnY = await page.evaluate(() => window.scrollY);
  // Bills tab: search, scroll down, open a bill
  await tab('bills', 5000);
  await page.fill('#bq', 'health'); await page.waitForTimeout(1500);
  const n0 = await page.evaluate(() => document.querySelectorAll('#blist article.bill').length); must(n0 >= 8, 'bills search "health" listed only ' + n0);
  await page.evaluate(() => { const L = document.querySelectorAll('#blist article.bill'); L[Math.min(L.length - 2, 7)].scrollIntoView(); window.scrollBy(0, -120); }); await page.waitForTimeout(500);
  const pick = await page.evaluate(() => { const hb = document.querySelector('header.top').getBoundingClientRect().bottom; const c = [...document.querySelectorAll('#blist article.bill')].find(x => x.getBoundingClientRect().top >= hb + 20); const r = c.getBoundingClientRect(); return { id: c.dataset.id, top: Math.round(r.top), x: r.left + 30, y: r.top + 20, sy: window.scrollY }; });
  await page.evaluate(id => { document.querySelector('#blist article.bill[data-id="' + CSS.escape(id) + '"] h3, #blist article.bill[data-id="' + CSS.escape(id) + '"]').click(); }, pick.id); await page.waitForTimeout(3000);
  must(/^#\/bill\//.test(await H()), 'tapping the bill card did not open the bill: ' + await H());
  must(await backShown(), 'no Back arrow on the bill page');
  // header Back → the Bills list, same search, same card at the same spot (not Learn)
  await tapBack(3000);
  must(await H() === '#/bills', 'Back from the bill went to ' + await H() + ' (want #/bills)');
  must(await curTab() === 'bills', 'Back from the bill switched the tab to ' + await curTab());
  must(await page.inputValue('#bq') === 'health', 'Back lost the search text: "' + await page.inputValue('#bq') + '"');
  const after = await page.evaluate(id => { const c = document.querySelector('#blist article.bill[data-id="' + CSS.escape(id) + '"]'); return c ? Math.round(c.getBoundingClientRect().top) : null; }, pick.id);
  must(after != null && Math.abs(after - pick.top) <= 40, 'the bill card is not where it was: top ' + after + ' vs ' + pick.top + ' (scrollY ' + await page.evaluate(() => window.scrollY) + ' vs ' + pick.sy + ')');
  out.push('bill→Bills list (search kept, card ' + pick.top + '→' + after + 'px)');
  // Back at the Bills list (the tab's first step) → Learn, where it was left
  must(await backShown(), 'no Back arrow on the Bills list although Learn is behind it');
  await tapBack(3000);
  must(await H() === learnHash, 'Back from the Bills list went to ' + await H() + ' (want the Learn page ' + learnHash + ')');
  must(await curTab() === 'founding', 'Back from the Bills list: tab is ' + await curTab());
  const ly = await page.evaluate(() => window.scrollY); must(Math.abs(ly - learnY) <= 40, 'Learn page not restored where left: scrollY ' + ly + ' vs ' + learnY);
  out.push('Bills list→Learn (' + learnHash + ', scroll ' + ly + ')');
  // the same with the Android / browser Back (WebView goBack = history back)
  await tab('bills', 4000);
  await page.evaluate(() => { document.querySelector('#blist article.bill').click(); }); await page.waitForTimeout(3000);
  must(/^#\/bill\//.test(await H()), 'second bill did not open');
  await page.goBack(); await page.waitForTimeout(3000);
  must(await H() === '#/bills', 'Android/browser Back from the bill went to ' + await H());
  await page.goBack(); await page.waitForTimeout(3000);
  must(await H() === learnHash, 'Android/browser Back from the Bills list went to ' + await H() + ' (want ' + learnHash + ')');
  out.push('Android Back: bill→Bills→Learn');
  // Officials: state → person → Back → the state list; Back → Officials home; nothing else in the tab
  await tab('officials', 3000);
  await page.evaluate(() => { location.hash = '#/s/CA'; }); await page.waitForTimeout(3000);
  await page.evaluate(() => { document.querySelector('#app a[href^="#/p/"]').click(); }); await page.waitForTimeout(3000);
  must(/^#\/p\//.test(await H()), 'person page did not open: ' + await H());
  await page.evaluate(() => { const a = document.querySelector('#app a[href$="/office"]'); if (a) a.click(); }); await page.waitForTimeout(1500);
  await tapBack(3000);
  must(await H() === '#/s/CA', 'Back from the person page went to ' + await H() + ' (want #/s/CA; Overview/In office are one step)');
  await tapBack(3000);
  must(await H() === '#/' || await H() === '', 'Back from California went to ' + await H() + ' (want Officials home)');
  must(await curTab() === 'officials', 'Officials Back switched tab to ' + await curTab());
  out.push('person→CA→Officials home');
  // a tab hop: bill page → Officials tab → Back → the bill page again
  await tab('bills', 4000); await page.evaluate(() => { document.querySelector('#blist article.bill').click(); }); await page.waitForTimeout(3000);
  const bh = await H(); await tab('officials', 2500); await tapBack(3000);
  must(await H() === bh, 'Back from the Officials home (first step) did not return to the bill page: ' + await H() + ' vs ' + bh);
  // deep link straight into a bill: Back → the Bills list (not off the site); browser Back too
  const bid = bh.replace('#/bill/', '');
  await newPage(); await go('#/bill/' + bid, 3500);
  must(await backShown(), 'no Back arrow on a deep-linked bill');
  await tapBack(3500); must(await H() === '#/bills', 'Back on a deep-linked bill went to ' + await H());
  await newPage(); await go('#/bill/' + bid, 3500);
  await page.goBack(); await page.waitForTimeout(3000); must(await H() === '#/bills', 'Android Back on a deep-linked bill went to ' + await H());
  // deep link to a positions page keeps working; Back → the person
  await newPage(); await go('#/s/CA', 3000); const pid = await page.evaluate(() => document.querySelector('#app a[href^="#/p/"]').getAttribute('href'));
  await newPage(); await go(pid + '/positions', 3500);
  must(/\/positions$/.test(await H()), 'positions route changed to ' + await H());
  await tapBack(2500); must(await H() === pid, 'Back on a deep-linked positions page went to ' + await H() + ' (want ' + pid + ')');
  return out.join(' · ') + ' · tab hop back to ' + bh + ' · deep links OK';
});

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
