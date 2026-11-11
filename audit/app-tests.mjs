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


// 0) v41: the bottom "More" tab opens the More menu, never the person row behind the bar (Shmuel, Nov 9 11 PM: it opened RFK Jr.)
await newPage();
await test('Bottom tab "More" opens More (not the person row underneath)', async () => {
  await go('#/federal');
  await page.evaluate(() => { const a = [...document.querySelectorAll('#app a')].find(x => /Kennedy/.test(x.textContent)); const tb = document.querySelector('.tabbar a[data-tab="more"]').getBoundingClientRect(); if (a) window.scrollBy(0, a.getBoundingClientRect().top - tb.top + 5); });
  await page.waitForTimeout(400);
  const pt = await page.evaluate(() => { const r = document.querySelector('.tabbar a[data-tab="more"]').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
  await page.touchscreen.tap(pt.x, pt.y); await page.waitForTimeout(1500);
  must((await page.evaluate(() => location.hash)) === '#/more', 'More tab went to ' + await page.evaluate(() => location.hash));
  // a click that lands on the page under the bar (WebView tap-through) must still open More
  await go('#/federal');
  await page.evaluate(() => { const a = [...document.querySelectorAll('#app a')].find(x => /Kennedy/.test(x.textContent)); const r = document.querySelector('.tabbar a[data-tab="more"]').getBoundingClientRect(); a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 })); });
  await page.waitForTimeout(1500);
  const h = await page.evaluate(() => location.hash);
  must(h === '#/more', 'tap-through onto a person row opened ' + h);
});

// 1) Official page tabs: Overview (default) | In office | Positions (v39c)
await newPage();
await test('Official page: Overview, In office and Positions tabs', async () => {
  await go('#/p/K000377');
  const tabs = await page.$$eval('.ptabs a', a => a.map(x => x.textContent.trim()));
  must(JSON.stringify(tabs) === JSON.stringify(['Overview', 'In office', 'Positions']), 'tabs wrong: ' + JSON.stringify(tabs));
  must(/overview/i.test(await page.$eval('.ptabs [aria-selected="true"]', x => x.textContent)), 'name link does not land on Overview');
  must(/about the role/i.test(await text()), 'Overview has no About the role card');
  const fit = await page.$$eval('.ptabs a', a => a.every(x => x.scrollWidth <= x.clientWidth + 1));
  must(fit, 'tab labels overflow at 390px');
  await page.click('.ptabs a:has-text("Positions")'); await page.waitForTimeout(2500);
  must(/\/positions$/.test(await page.evaluate(() => location.hash)), 'Positions tab did not open #/p/<id>/positions');
  must(/positions by issue/i.test(await text()), 'Positions page shows no positions');
  await page.click('.ptabs a:has-text("In office")'); await page.waitForTimeout(2500);
  must(/\/office$/.test(await page.evaluate(() => location.hash)), 'In office tab did not open #/p/<id>/office');
  must(/record in office|in office since|term/i.test(await text()), 'In office page is empty');
  await page.click('.ptabs a:has-text("Overview")'); await page.waitForTimeout(2000);
  must(!/\/(office|positions)$/.test(await page.evaluate(() => location.hash)), 'Overview tab did not go back');
});
await test('Trump page: Overview with structured bio, In office record', async () => {
  await go('#/p/pr47', 4500);
  must(/about the role/i.test(await text()), 'no About the role');
  must(await page.$('.bio2 .bio2-list'), 'Overview has no structured bio (Born / Spouse / Children list)');
  must(/born/i.test(await page.$eval('.bio2', x => x.textContent)) && /written by ai/i.test(await page.$eval('.bio2', x => x.textContent)), 'bio box missing Born or AI label');
  await go('#/p/pr47/office', 4000);
  must(/executive orders|record in office|in office since|term/i.test(await text()), 'In office empty');
});
await test('Candidate page: Overview, In office and Positions tabs', async () => {
  const idx = await (await ctx.request.get(SITE + 'data/candidates/index.json?x=' + Date.now())).json();
  let cid = null; for (const L of Object.values(idx.races || {})) { for (const e of L) if (e.f && !e.m && /^house_/.test(e.id)) { cid = e.id; break; } if (cid) break; }
  must(cid, 'no candidate without an official page found');
  await go('#/candidate/' + cid, 4000);
  const tabs = await page.$$eval('.ptabs a', a => a.map(x => x.textContent.trim()));
  must(JSON.stringify(tabs) === JSON.stringify(['Overview', 'In office', 'Positions']), cid + ' tabs wrong: ' + JSON.stringify(tabs));
  await page.click('.ptabs a:has-text("In office")'); await page.waitForTimeout(2500);
  must(/\/office$/.test(await page.evaluate(() => location.hash)), 'candidate In office tab did not open');
  must(/public offices held|has never held public office|no public office on record|record in office as mayor/i.test(await text()), cid + ' In office tab shows none of the expected lines');
  await page.click('.ptabs a:has-text("Positions")'); await page.waitForTimeout(2500);
  must(/\/positions$/.test(await page.evaluate(() => location.hash)), 'candidate Positions tab did not open');
});
// v40: photos (owner, Nov 9 2026: "Everyone should have a picture") and bottom-sheet gestures (Nov 9 2026, 10:14 PM)
await test('Person pages show the photo (not initials) when a photo exists, with a Photo: credit', async () => {
  const D = await page.evaluate(() => { const P = (window.GOV_DATA && GOV_DATA.people) || {}; const w = Object.values(P).filter(p => p.img && p.imgSrc && /^img\//.test(p.img)); return w.slice(0, 1).map(p => p.id).concat(w.slice(-1).map(p => p.id)); });
  must(D.length, 'no official with a stored photo in data.js');
  for (const id of D) {
    await go('#/p/' + id, 3500);
    const ok = await page.evaluate(() => { const i = document.querySelector('#app .hero img, #app .phead img'); return !!(i && i.complete && i.naturalWidth > 0); });
    must(ok, id + ': person page shows no loaded photo');
    must(/Photo:/.test(await text()), id + ': no Photo: credit');
  }
  const ph = await page.evaluate(() => fetch('data/candidates/photos.json?x=' + Date.now(), { cache: 'no-store' }).then(r => r.json()));
  const ids = Object.keys(ph.photos || {}); must(ids.length > 100, 'photos.json has only ' + ids.length + ' candidates');
  const pick = ['senate_mi_abdul-sayed'].filter(x => ph.photos[x]).concat(ids.filter((x, i) => i % Math.max(1, Math.floor(ids.length / 3)) === 0).slice(0, 3));
  for (const cid of pick) {
    await go('#/candidate/' + cid, 4500);
    if (/#\/p\//.test(await page.evaluate(() => location.hash))) continue;
    const ok = await page.evaluate(() => { const i = document.querySelector('#app .hero img'); return !!(i && i.complete && i.naturalWidth > 0); });
    must(ok, cid + ': candidate page shows initials although photos.json has a photo');
    must(/Photo:/.test(await text()), cid + ': no Photo: credit');
  }
});
await test('Bottom sheet: drag down on the handle closes it, tapping the background closes it, back closes it', async () => {
  const open = async () => { await go('#/election/senate', 3500); await page.evaluate(() => { location.hash = '#/election/senate/OH'; }); await page.waitForTimeout(1200); return page.evaluate(() => !!document.querySelector('#sheet.open')); };
  must(await open(), 'race sheet did not open');
  const cdp = await ctx.newCDPSession(page);
  const g = await page.$eval('#sheet .grab', e => { const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  const tp = (type, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: g.x, y }] });
  await tp('touchStart', g.y); for (let k = 1; k <= 12; k++) { await tp('touchMove', g.y + k * 40); await page.waitForTimeout(16); } await tp('touchEnd', 0);
  await page.waitForTimeout(900);
  must(!(await page.evaluate(() => !!document.querySelector('#sheet.open'))), 'drag down on the handle did not close the sheet');
  must(/^#\/election\/senate(\?|$)/.test(await page.evaluate(() => location.hash)), 'after the drag the page is not the Senate map: ' + await page.evaluate(() => location.hash));
  // a short drag snaps back and keeps it open
  must(await open(), 'race sheet did not reopen');
  const g2 = await page.$eval('#sheet .grab', e => { const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: g2.x, y: g2.y }] });
  for (let k = 1; k <= 3; k++) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: g2.x, y: g2.y + k * 10 }] }); await page.waitForTimeout(60); }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await page.waitForTimeout(600);
  must(await page.evaluate(() => !!document.querySelector('#sheet.open')), 'a short drag closed the sheet (it should snap back)');
  // tap the dim background above the sheet
  await page.touchscreen.tap(195, 30); await page.waitForTimeout(900);
  must(!(await page.evaluate(() => !!document.querySelector('#sheet.open'))), 'tapping the background did not close the sheet');
  // the back button closes the sheet and stays on the map
  must(await open(), 'race sheet did not reopen (back test)');
  await page.goBack(); await page.waitForTimeout(900);
  must(!(await page.evaluate(() => !!document.querySelector('#sheet.open'))), 'back did not close the sheet');
  must(/^#\/election\/senate/.test(await page.evaluate(() => location.hash)), 'back left the Senate map: ' + await page.evaluate(() => location.hash));
});
// 2) Sign-in form (#/ gate and #/account)
await test('Sign-in form on #/account', async () => {
  await go('#/account', 3500);
  must(await page.$('#aemail') && await page.$('#apw'), 'no email/password fields');
  await page.fill('#aemail', 'test@example.com'); await page.fill('#apw', 'x');
  const btns = await page.$$eval('#app button, #app input[type=submit]', b => b.map(x => x.textContent.trim()).filter(Boolean));
  must(btns.some(t => /sign in/i.test(t)), 'no Sign in button: ' + JSON.stringify(btns.slice(0, 8)));
  must(btns.some(t => /google/i.test(t)), 'no Google sign-in button');
});
await test('Sign-in gate on #/', async () => {
  await ctx.clearCookies(); await page.evaluate(() => { try { localStorage.removeItem('kus_session'); } catch (e) {} });
  await page.goto(SITE + '#/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
  const g = await page.evaluate(() => { const el = document.getElementById('gate'); return el ? { shown: getComputedStyle(el).display !== 'none', html: el.innerText.slice(0, 300), email: !!el.querySelector('input[type=email]'), btn: [...el.querySelectorAll('button')].map(b => b.textContent.trim()) } : null; });
  if (!g) return 'no sign-in gate on this version (home page opens directly)';
  must(g.email || g.btn.some(t => /sign in|google|continue/i.test(t)), 'gate shows no way to sign in: ' + JSON.stringify(g).slice(0, 300));
});
// 3) Voter: address -> sample ballot page (two blue buttons) -> Download; Fillable page: fill an oval, Clear all, Save PDF
await newPage();
const voterAddr = async () => {
  await go('#/voter', 2500);
  await page.fill('#vaddr', ADDR); await page.click('#vgo');
  await page.waitForFunction(() => /congressional district|your districts|district/i.test((document.getElementById('app') || document.body).innerText) && !document.querySelector('#vgo[disabled]'), null, { timeout: 45000 });
};
await test('Sample ballot page: Download sample ballot + Fillable sample ballot buttons', async () => {
  await voterAddr();
  await page.evaluate(() => { location.hash = '#/voter/ballot'; }); await page.waitForTimeout(4000);
  await page.waitForSelector('section.bal [data-pdfblank]', { timeout: 45000 });
  const labels = await page.$$eval('section.bal .bbig .bbtn', b => b.map(x => x.textContent.trim()));
  must(labels[0] === 'Download sample ballot', 'first button is not "Download sample ballot": ' + JSON.stringify(labels));
  must(labels.includes('Fillable sample ballot'), 'no "Fillable sample ballot" button: ' + JSON.stringify(labels));
  const blue = await page.$$eval('section.bal .bbig .bbtn', b => b.map(x => getComputedStyle(x).backgroundColor));
  must(blue.every(c => { const m = c.match(/\d+/g) || []; return +m[2] > +m[0] + 40; }), 'buttons are not blue: ' + JSON.stringify(blue));
  must(!(await page.$('section.bal .bopt[data-c]')), 'the inline ballot is still shown on the sample ballot page');
  await page.click('section.bal [data-pdfblank]'); await page.waitForTimeout(2500);
  const k = await kus(); must(k.lastSave, 'Download sample ballot did not call the app bridge (saveFile)');
  must(k.lastSave.pdf && k.lastSave.mime === 'application/pdf' && /\.pdf$/.test(k.lastSave.name), 'bridge got a bad file: ' + JSON.stringify(k.lastSave));
  must(/saved to your downloads/i.test(await text()), 'no "Saved to your Downloads" message');
  const tst = await page.evaluate(() => { const t = document.getElementById('kustoast'); return t ? { on: t.classList.contains('on'), txt: t.textContent, bg: getComputedStyle(t).backgroundColor, pos: getComputedStyle(t).position } : null; });
  must(tst && tst.on && /downloaded/i.test(tst.txt) && tst.pos === 'fixed', 'no grey "Downloaded" box at the bottom: ' + JSON.stringify(tst));
  await page.click('section.bal .bbig a.bbtn'); await page.waitForTimeout(3000);
  must(/#\/voter\/ballot\/fill/.test(await page.evaluate(() => location.hash)), 'Fillable sample ballot did not open #/voter/ballot/fill');
  return 'blank PDF ' + k.lastSave.len + ' base64 chars, ' + k.lastSave.name;
});
await test('Fillable sample ballot: fill, Clear all, Save PDF (app bridge, no print dialog)', async () => {
  if (!/#\/voter\/ballot\/fill/.test(await page.evaluate(() => location.hash))) { await page.evaluate(() => { location.hash = '#/voter/ballot/fill'; }); await page.waitForTimeout(3000); }
  await page.waitForSelector('section.bal[data-b] .bopt[data-c]', { timeout: 45000 });
  const cnt = async () => page.$eval('section.bal[data-b] [data-count]', e => e.textContent);
  const c0 = await cnt();
  await page.click('section.bal[data-b] .bopt[data-c]'); await page.waitForTimeout(500);
  const c1 = await cnt(); must(parseInt(c1) === parseInt(c0) + 1 || /^1 of/.test(c1), 'tapping an oval did not fill it (' + c0 + ' -> ' + c1 + ')');
  await page.click('section.bal[data-b] [data-clear]'); await page.waitForTimeout(400);
  const yes = await page.$('section.bal[data-b] [data-clryes]'); must(yes, 'Clear all showed no in-page confirm');
  await yes.click(); await page.waitForTimeout(500);
  must(/^0 of/.test(await cnt()), 'Clear all did not clear (' + await cnt() + ')');
  await page.click('section.bal[data-b] .bopt[data-c]'); await page.waitForTimeout(300);
  await page.evaluate(() => { window.__kus.lastSave = null; });
  await page.click('section.bal[data-b] [data-pdf]'); await page.waitForTimeout(2500);
  const k = await kus(); must(k.lastSave, 'Save PDF did not call the app bridge (saveFile)');
  must(k.lastSave.pdf && k.lastSave.mime === 'application/pdf' && /\.pdf$/.test(k.lastSave.name), 'bridge got a bad file: ' + JSON.stringify(k.lastSave));
  must(/saved to your downloads/i.test(await text()), 'no "Saved to your Downloads" message');
  const lbl = await page.$$eval('section.bal[data-b] .btools button', b => b.map(x => x.textContent.trim()));
  must(lbl.includes('Save PDF') && !lbl.some(x => /print/i.test(x)), 'buttons should be "Save PDF" with no Print: ' + JSON.stringify(lbl));
  const tst = await page.evaluate(() => { const t = document.getElementById('kustoast'); return t ? { on: t.classList.contains('on'), txt: t.textContent, bg: getComputedStyle(t).backgroundColor, pos: getComputedStyle(t).position } : null; });
  must(tst && tst.on && /downloaded/i.test(tst.txt) && tst.pos === 'fixed', 'no grey "Downloaded" box at the bottom: ' + JSON.stringify(tst));
  return 'PDF ' + k.lastSave.len + ' base64 chars, ' + k.lastSave.name;
});
await test('Web browser: Download sample ballot downloads the file and shows the grey box', async () => {
  const c2 = await browser.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 2, serviceWorkers: 'block', isMobile: true, hasTouch: true, acceptDownloads: true });
  if (LOCAL) await c2.route('**/*', async r => { const u = new URL(r.request().url()); if (u.origin === ORIGIN) { let p = decodeURIComponent(u.pathname); if (p.endsWith('/')) p += 'index.html'; const f = path.join(LOCAL, p); if (fs.existsSync(f) && fs.statSync(f).isFile()) return r.fulfill({ path: f, contentType: MT[path.extname(f)] || 'application/octet-stream' }); return r.fulfill({ status: 404, body: 'nf' }); } return r.continue(); });
  await c2.addInitScript(() => { window.__printed = 0; window.print = () => { window.__printed++; }; try { localStorage.setItem('kus_session', '1'); } catch (e) {} });
  const p0 = page; page = await c2.newPage();
  try {
    await voterAddr();
    await page.evaluate(() => { location.hash = '#/voter/ballot'; }); await page.waitForTimeout(4000);
    await page.waitForSelector('section.bal [data-pdfblank]', { timeout: 45000 });
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), page.click('section.bal [data-pdfblank]')]);
    must(/\.pdf$/.test(dl.suggestedFilename()), 'download is not a PDF: ' + dl.suggestedFilename());
    await page.waitForTimeout(1500);
    const tst = await page.evaluate(() => { const t = document.getElementById('kustoast'); return t ? { on: t.classList.contains('on'), txt: t.textContent } : null; });
    must(tst && tst.on && /downloaded/i.test(tst.txt), 'no grey "Downloaded" box: ' + JSON.stringify(tst));
    await page.evaluate(() => { location.hash = '#/voter/ballot/fill'; }); await page.waitForTimeout(3000);
    await page.waitForSelector('section.bal[data-b] [data-pdf]', { timeout: 45000 });
    const [dl2] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), page.click('section.bal[data-b] [data-pdf]')]);
    must(/\.pdf$/.test(dl2.suggestedFilename()), 'Save PDF did not download a PDF');
    must((await page.evaluate(() => window.__printed)) === 0, 'Save PDF opened the print dialog');
    return dl.suggestedFilename() + ' + ' + dl2.suggestedFilename();
  } finally { await page.close(); page = p0; await c2.close(); }
});
// 5) Election tab: summary cards add up; every map colour is in the legend; each state's shade matches its own leader/winner
await newPage();
const hexOf = c => { const m = String(c).match(/\d+/g); if (!m) return String(c).toLowerCase(); return '#' + m.slice(0, 3).map(x => (+x).toString(16).padStart(2, '0')).join(''); };
await test('Election cards: won + leading + no count add up to 100 / 435 / 50', async () => {
  await go('#/election/senate', 4000);
  const bars = await page.$$eval('.tot', t => t.map(x => ({ n: x.getAttribute('data-tot'), total: +(x.querySelector('.bar[data-total]') || {}).getAttribute?.('data-total'), sum: +(x.querySelector('.bar[data-sum]') || {}).getAttribute?.('data-sum'), txt: x.innerText.replace(/\s+/g, ' ') })));
  must(bars.length === 3, 'expected 3 summary cards, got ' + bars.length);
  const want = { Senate: 100, House: 435, Governors: 50 };
  for (const b of bars) { must(b.total === want[b.n] && b.sum === want[b.n], b.n + ' card adds up to ' + b.sum + ' (should be ' + want[b.n] + '): ' + b.txt); must(!/not certified/i.test(b.txt), b.n + ' card still says "not certified": ' + b.txt); }
  must(/Leading = ahead in the state/i.test(await text()), 'no "Leading = ..." footnote');
  return bars.map(b => b.txt.slice(0, 80)).join(' | ');
});
for (const mode of ['senate', 'gov', 'house', 'mayor']) {
  await test('Election map (' + mode + '): every colour shown is in the legend', async () => {
    await go('#/election/' + mode, 4000);
    const r = await page.evaluate((mode) => {
      const sel = mode === 'mayor' ? '.usmap circle.cdot' : '.usmap path[data-st], .usmap circle[data-st]:not(.hit)';
      const fills = [...document.querySelectorAll(sel)].map(e => (e.getAttribute('fill') || '').toLowerCase());
      const leg = document.querySelector('.mlegend'); const sw = leg ? [...leg.querySelectorAll('i')].map(i => getComputedStyle(i).backgroundColor) : [];
      return { fills, sw, legTxt: leg ? leg.innerText : '' };
    }, mode);
    must(r.fills.length, 'no map shapes found');
    const sw = new Set(r.sw.map(hexOf));
    const odd = [...new Set(r.fills)].filter(f => !sw.has(f));
    let bad = odd;
    if (mode === 'house' && /darker = bigger share/i.test(r.legTxt)) bad = odd.filter(f => { const m = f.match(/[0-9a-f]{2}/g).map(x => parseInt(x, 16)); return !(m[2] > m[0] + 20 || m[0] > m[2] + 20); });
    must(!bad.length, 'colours on the map that the legend does not explain: ' + bad.join(', ') + ' (legend: ' + [...sw].join(', ') + ')');
    return new Set(r.fills).size + ' colours, all explained';
  });
}
await test('Election maps: each state is shaded for its own winner or leader', async () => {
  const d = LOCAL ? JSON.parse(fs.readFileSync(path.join(LOCAL, 'data/election-official.json'), 'utf8')) : await (await ctx.request.get(SITE + 'data/election-official.json?x=' + Date.now())).json();
  const pc = p => /^Republican/.test(p || '') ? 'R' : /^Democrat/.test(p || '') ? 'D' : 'O';
  const hue = f => { const m = f.slice(1).match(/../g).map(x => parseInt(x, 16)); return m[2] > m[0] + 20 ? 'D' : m[0] > m[2] + 20 ? 'R' : 'X'; };
  const bad = [];
  for (const mode of ['senate', 'gov']) {
    await go('#/election/' + mode, 3500);
    const fills = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('.usmap path[data-st]')].map(p => [p.getAttribute('data-st'), p.getAttribute('fill').toLowerCase()])));
    for (const [ab, rs] of Object.entries(d[mode] || {})) {
      const r = rs.find(x => !x.called) || rs[0]; const f = fills[ab]; if (!f) continue;
      const partial = (r.cands || []).filter(c => c && c.n).length < 2 && !r.unopp; /* v42 KUS-PARTIAL: never shown as decided */
      const want = partial ? null : r.called ? r.winner : r.leader;
      if (want === 'D' || want === 'R') { if (hue(f) !== want) bad.push(mode + ' ' + ab + ' shaded ' + f + ' but ' + (r.called ? 'won by ' : 'led by ') + want); }
      if (r.leader && r.cands && r.cands.every(c => c.votes != null)) { const top = r.cands.slice().sort((a, b) => b.votes - a.votes)[0]; if (pc(top.p) !== r.leader && (r.leader === 'D' || r.leader === 'R')) bad.push(mode + ' ' + ab + ' leader field ' + r.leader + ' but most votes: ' + top.n); }
    }
  }
  must(!bad.length, bad.slice(0, 8).join(' · '));
  return 'shading matches the leader/winner in every Senate and Governor state';
});
// 6) Source policy on pages: no Democratic sources on anyone else's page (Trump first), no banned link anywhere checked
await newPage();
await test('No Democratic or banned sources on Trump\'s pages and a sample of others', async () => {
  const P = LOCAL ? JSON.parse(fs.readFileSync(path.join(LOCAL, 'data/sources-policy.json'), 'utf8')) : await (await ctx.request.get(SITE + 'data/sources-policy.json?x=' + Date.now())).json();
  must(P.democratic_sources && P.democratic_sources.rule === 'ban', 'policy has no democratic_sources ban');
  const cls = makePolicy(P), bad = [];
  for (const [id, sub] of [['pr47', ''], ['pr47', '/office'], ['pr47', '/positions'], ['K000377', '/office'], ['J000289', '/positions'], ['P000197', '/positions'], ['S000148', '/positions'], ['K000377', '/positions']]) {
    await go('#/p/' + id + sub, 3500);
    const hrefs = await page.$$eval('#app a[href^="http"]', a => a.map(x => x.href));
    for (const u of hrefs) if (cls(u, [], [id]) === 'banned') bad.push(id + sub + ': ' + u);
  }
  must(!bad.length, bad.length + ' banned links shown: ' + bad.slice(0, 6).join(' · '));
  return 'checked Trump, Jordan, Pelosi, Schumer, Kelly pages';
});
// 4) Delete account up to the DELETE step (needs a test account; never deletes)
await test('Delete account flow up to "type DELETE" (cancelled)', async () => {
  const E = process.env.KNOWUS_TEST_EMAIL, P = process.env.KNOWUS_TEST_PASSWORD;
  if (!E || !P) return 'skipped: set KNOWUS_TEST_EMAIL and KNOWUS_TEST_PASSWORD repo secrets (a test account) to run it';
  await newPage(); await go('#/account', 3500);
  await page.fill('#aemail', E); await page.fill('#apw', P);
  await page.click('#app button:has-text("Sign in")'); await page.waitForSelector('#delacct', { timeout: 30000 });
  await page.click('#delacct'); await page.waitForSelector('#delconfirm', { timeout: 10000 });
  must(await page.$eval('#delyes', b => b.disabled), 'delete button is on before typing DELETE');
  await page.fill('#delconfirm', 'delete'); await page.waitForTimeout(200);
  must(await page.$eval('#delyes', b => b.disabled), 'lower-case "delete" turned the delete button on');
  await page.fill('#delconfirm', 'DELETE'); await page.waitForTimeout(200);
  must(!(await page.$eval('#delyes', b => b.disabled)), 'typing DELETE did not turn the delete button on');
  await page.click('#delno'); await page.waitForTimeout(500);
  must(!(await page.$('#delconfirm')), 'cancel did not close the delete box');
  await page.click('#signout').catch(() => {});
});

// ===== v42 (Shmuel's call, Nov 9 2026 11 PM): Report a problem · Founding tab · incomplete races =====
const V42SHOTS = process.env.V42_SHOTS || OUT; fs.mkdirSync(V42SHOTS, { recursive: true });
const shot42 = (n, o = {}) => page.screenshot({ path: path.join(V42SHOTS, n + '.png'), ...o }).catch(() => {});
await newPage();
await test('v42: More keeps account/sources/privacy + "Report a problem"; founding rows moved out', async () => {
  await go('#/more');
  const t = await text();
  must(/Report a problem/.test(t), 'no "Report a problem" row in More');
  must(/Sources/.test(t) && /Privacy policy/.test(t), 'More lost Sources or Privacy');
  must(!/The Federalist Papers|The Declaration of Independence|The Constitution/.test(t), 'founding documents still listed in More');
  await shot42('v42-more-menu');
});
await test('v42: "Report a problem" link under person pages (all 3 tabs) and not on home', async () => {
  for (const sub of ['', '/office', '/positions']) {
    await go('#/p/S000148' + sub, 3000);
    const st = await page.evaluate(() => { const e = document.getElementById('replink'); return e ? { hidden: e.hidden, href: e.querySelector('a').getAttribute('href') } : null; });
    must(st && !st.hidden, 'no Report a problem link on #/p/S000148' + sub);
    must(decodeURIComponent(st.href).includes('#/p/S000148' + sub), 'link does not carry the page: ' + st.href);
  }
  await go('#/', 1500);
  must(await page.evaluate(() => document.getElementById('replink').hidden), 'Report link shown on the home page');
});
await test('v42/v43: Report form fills the page, validates, falls back to a mailto when the email POST fails', async () => {
  await page.route(/firestore\.googleapis\.com/, r => r.abort());
  await page.route(/formsubmit\.co/, r => r.abort());
  await go('#/p/S000148/positions', 3000);
  await page.click('#replink a'); await page.waitForSelector('#reptext', { timeout: 8000 });
  must((await page.inputValue('#reppage')).includes('#/p/S000148/positions'), 'Page field not prefilled');
  must(await page.isChecked('#repdev'), 'device-info checkbox missing');
  await shot42('v42-report-form');
  await page.click('#repsend'); await page.waitForTimeout(300);
  must(/describe what/i.test(await page.textContent('#repmsg')), 'empty report was not stopped');
  must((await page.getAttribute('#reptext', 'aria-invalid')) === 'true', 'empty textarea not marked invalid');
  await page.fill('#reptext', 'Test report from app-tests (offline path)');
  await page.click('#repsend');
  await page.waitForSelector('#repmail', { timeout: 20000 });
  const href = await page.getAttribute('#repmail', 'href');
  must(href.startsWith('mailto:knowussupport@gmail.com?') && decodeURIComponent(href).includes('Test report from app-tests'), 'mailto fallback wrong: ' + href.slice(0, 120));
  await shot42('v42-report-fallback');
  await page.unroute(/firestore\.googleapis\.com/);
  await page.unroute(/formsubmit\.co/);
});
await test('v43: Report form emails knowussupport@gmail.com via formsubmit (stubbed) and keeps the Firestore copy silent', async () => {
  let posted = null;
  await page.route(/formsubmit\.co/, async r => { posted = { url: r.request().url(), method: r.request().method(), accept: r.request().headers()['accept'], body: JSON.parse(r.request().postData() || '{}') };
    await r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ success: 'true', message: 'The form was submitted successfully.' }) }); });
  await go('#/report?page=' + encodeURIComponent('#/voter/ballot'), 2000);
  await page.evaluate(() => { window.__rep = null; window.KUS_ACC.report = d => { window.__rep = d; return Promise.reject(new Error('rules')); }; });
  await page.fill('#reptext', 'Ballot is missing a judge');
  await page.click('#repsend'); await page.waitForSelector('#repok', { timeout: 10000 });
  must(posted && posted.url === 'https://formsubmit.co/ajax/knowussupport@gmail.com' && posted.method === 'POST' && /application\/json/.test(posted.accept || ''), 'POST wrong: ' + JSON.stringify(posted && { url: posted.url, method: posted.method, accept: posted.accept }));
  const b = posted.body;
  must(b._subject === 'KnowUS problem report' && b.message === 'Ballot is missing a judge' && b.page === '#/voter/ballot' && b._template === 'table' && b._captcha === 'false', 'POST body wrong: ' + JSON.stringify(b));
  must(b.device && /\d+ x \d+/.test(b.screen) && /web/.test(b.app_version) && /Android app 1\.3/.test(b.app_version), 'device info missing: ' + JSON.stringify(b));
  const d = await page.evaluate(() => window.__rep);
  must(d && d.text === 'Ballot is missing a judge', 'Firestore copy not attempted: ' + JSON.stringify(d));
  must(/Sent ✓ — thanks!/.test(await text()), 'no "Sent ✓ — thanks!" after a good send (Firestore failure must be silent)');
  await shot42('v43-report-sent');
  await page.unroute(/formsubmit\.co/);
});
await test('v42/v43: Learn tab (was Founding) opens the hub and each document', async () => {
  await go('#/', 2000);
  await page.click('.tabbar a[data-tab="founding"]'); await page.waitForTimeout(1200);
  must((await page.evaluate(() => location.hash)) === '#/founding', 'Founding tab went to ' + await page.evaluate(() => location.hash));
  const t = await text();
  for (const k of ['The Constitution', 'The Declaration of Independence', 'The Federalist Papers', 'Civics lessons']) must(t.includes(k), 'hub lacks ' + k);
  // v43: Shmuel named the 6th tab "Learn" (Nov 10 2026); no visible "Founding" label on the tab or the hub
  must(await page.evaluate(() => document.querySelector('.tabbar a[data-tab="founding"] span').textContent.trim()) === 'Learn', 'tab label is not Learn');
  must(await page.evaluate(() => document.querySelector('#app h1').textContent.trim()) === 'Learn', 'hub title is not Learn');
  must(!/\bFounding\b/.test(await page.evaluate(() => document.querySelector('.tabbar').textContent)), 'tab bar still says Founding');
  await shot42('v42-founding-hub');
  for (const [h, re] of [['#/constitution', /We the People/i], ['#/declaration', /When in the Course of human events/i], ['#/federalist', /Federalist/i], ['#/learn', /./]]) {
    await go('#/founding', 1200);
    await page.click('#app a[href="' + h + '"]'); await page.waitForTimeout(1800);
    must((await page.evaluate(() => location.hash)).startsWith(h), 'row did not open ' + h);
    must(re.test(await text()), h + ' page has no expected text');
    must(await page.evaluate(() => document.querySelector('.tabbar a[data-tab="founding"]').getAttribute('aria-current') === 'page'), h + ' does not light the Founding tab');
  }
  await go('#/federalist/85', 2500);
  must(/85/.test(await text()), 'Federalist No. 85 does not open');
});
await test('v42: 6 bottom tabs fit at 390px and 320px (no overflow, Learn between Voter and More)', async () => {
  const out = [];
  for (const w of [390, 320]) {
    await page.setViewportSize({ width: w, height: 760 }); await go('#/', 1500);
    const r = await page.evaluate(() => { const bar = document.querySelector('.tabbar'); const as = [...bar.querySelectorAll('a[data-tab]')];
      return { tabs: as.map(a => a.dataset.tab), barOver: bar.scrollWidth > window.innerWidth + 0.5,
        bad: as.filter(a => { const s = a.querySelector('span'), r = a.getBoundingClientRect(), rs = s.getBoundingClientRect(); return s.scrollWidth > a.clientWidth + 0.5 || rs.left < r.left - 0.5 || rs.right > r.right + 0.5 || r.right > window.innerWidth + 0.5; }).map(a => a.dataset.tab),
        minW: Math.min(...as.map(a => a.getBoundingClientRect().width)), font: getComputedStyle(as[0]).fontSize }; });
    must(r.tabs.join(',') === 'officials,election,bills,voter,founding,more', w + 'px tabs: ' + r.tabs.join(','));
    must(!r.barOver && !r.bad.length, w + 'px overflow: ' + JSON.stringify(r));
    out.push(w + 'px: tab ' + Math.round(r.minW) + 'px wide, font ' + r.font);
    await shot42('v42-tabbar-' + w, { clip: { x: 0, y: 760 - 80, width: w, height: 80 } });
  }
  await page.setViewportSize({ width: W, height: 844 });
  return out.join(' · ');
});
await test('v42: the tab-bar tap guard still works with 6 tabs (Learn over a person row)', async () => {
  await go('#/federal');
  await page.evaluate(() => { const a = [...document.querySelectorAll('#app a')].find(x => /Kennedy/.test(x.textContent)); const r = document.querySelector('.tabbar a[data-tab="founding"]').getBoundingClientRect(); a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 })); });
  await page.waitForTimeout(1200);
  const h = await page.evaluate(() => location.hash);
  must(!/#\/p\//.test(h), 'click under the Learn tab opened ' + h);
});
await test('v44: AP House calls show "Called by AP" with a live AP link only on the Elections tab; AP stays unlinked elsewhere', async () => {
  await go('#/election/house', 3500); await page.evaluate(() => { location.hash = '#/election/house/OH'; }); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => { const sh = document.querySelector('#sheet'); const t = sh ? sh.innerText : '';
    const live = [...(sh || document).querySelectorAll('a[data-apcall="1"]')].map(a => a.href);
    return { calls: (t.match(/Called by AP/g) || []).length, live: live.length, liveOk: live.every(u => /^https:\/\/apnews\.com\//.test(u)), note: /AP calls the race/.test(t) }; });
  must(r.calls >= 10 && r.live >= 10 && r.liveOk, 'OH House sheet: ' + JSON.stringify(r));
  must(r.note, 'House sheet note does not mention AP calls');
  await shot42('v44-house-oh-apcalls');
  const cls = await page.evaluate(() => [KUS_SRC.cls('https://apnews.com/article/x'), KUS_SRC.cls('https://apnews.com/article/x', null, null, 'house_call'), KUS_SRC.cls('https://reuters.com/x', null, null, 'house_call')]);
  must(cls[0] === 'banned' && cls[1] === 'allowed' && cls[2] === 'banned', 'AP exception not narrow: ' + cls.join(','));
  await go('#/p/S000148', 3000);
  await page.evaluate(() => { const a = document.createElement('a'); a.href = 'https://apnews.com/article/test'; a.dataset.apcall = '1'; a.id = '__ap'; a.textContent = 'AP ↗'; document.getElementById('app').appendChild(a); });
  for (let i = 0; i < 30 && (await page.$('#__ap')); i++) await page.waitForTimeout(100);
  must(!(await page.$('#__ap')), 'an AP link on a person page was not unlinked');
  const h = await page.evaluate(() => { const d = window.KUS_ELECTION && KUS_ELECTION.data, hs = (d && d.house && d.house.states) || {}; let n = 0; for (const k in hs) n += (hs[k].districts || []).length; return n; });
  return 'OH: ' + r.calls + ' AP calls, ' + r.live + ' live links · house districts in data: ' + h;
});
await test('v42: a race with fewer than 2 candidates listed always says so; 0 candidates is never called; a network call (1 listed) keeps its call', async () => {
  const bad = await page.evaluate(() => { const d = window.KUS_ELECTION && KUS_ELECTION.data, out = [];
    const chk = (r, k) => { if (!r || !Array.isArray(r.cands) || r.unopp) return; const n = r.cands.filter(c => c && c.n).length; if (n >= 2) return;
      if (!r.partial) out.push(k + ' (no note)'); if (n === 0 && (r.called || r.winner)) out.push(k + ' (0 listed but called)');
      if (n === 1 && r.called && !r.callBy) out.push(k + ' (called with 1 listed and no network call)'); };
    ['senate', 'gov'].forEach(m => Object.entries(d[m] || {}).forEach(([st, v]) => (Array.isArray(v) ? v : [v]).forEach(r => chk(r, m + ' ' + st))));
    Object.entries((d.house && d.house.states) || {}).forEach(([st, s]) => (s.districts || []).forEach(x => chk(x, 'house ' + st + '-' + x.d)));
    return out; });
  must(!bad.length, bad.join(', '));
  const pick = await page.evaluate(() => { const d = KUS_ELECTION.data, out = [];
    for (const m of ['senate', 'gov']) { const st = Object.keys(d[m] || {}).sort().find(s => (Array.isArray(d[m][s]) ? d[m][s] : [d[m][s]]).some(r => r && r.partial)); if (st) out.push([m, st]); }
    return out; });
  if (!pick.length) return 'no race with fewer than 2 candidates in the data right now';
  for (const [m, st] of pick) {
    await go('#/election/' + m + '/' + st, 3500);
    const s = await page.evaluate(() => { const b = document.getElementById('sheetbody'); const a = b && b.querySelector('.rstat a'); return { t: b ? b.innerText : '', href: a ? a.href : '' }; });
    must(/Not all candidates listed yet/.test(s.t), m + ' ' + st + ': no "Not all candidates listed yet"');
    must(/^https:\/\/[^/]*(\.gov|\.us)\//.test(s.href), m + ' ' + st + ': no official results link (' + s.href + ')');
    if (m === 'senate') await shot42('v42-one-candidate-race');
  }
  return 'checked ' + pick.map(x => x.join(' ')).join(', ');
});

// v46 (Shmuel, Nov 10 9:04 AM: "only 2 things in the sample ballot ... why do I keep having to tell you this?"): every ballot is either a verified
// COMPLETE official ballot, or carries the heading "Races we've confirmed for your address (may not be complete)" + the blue official button.
await test('v46: ballot rule — complete official ballot, or "may not be complete" + blue official button (CT towns, Rockland NY, every state)', async () => {
  await newPage(); await go('#/voter/ballot', 4000);
  const r = await page.evaluate(async () => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { bad: [], ct: 0, ctFull: 0, rk: 0, st: 0 };
    const chk = (g, tag) => { if (!g) return; const ver = K._isVerified(g); const l = ver ? g.fullLink : K._fullFor(g);
      if (!ver && !(l && l.url && /official sample ballot/i.test(l.label))) out.bad.push(tag + ': not complete and no blue official button');
      if (ver && !g.contests.length) out.bad.push(tag + ': complete ballot with no contests'); };
    await K._prepFull({ state: 'CT' }); const D = K._CT.d;
    for (const town of Object.keys(D.towns)) for (const f of D.towns[town].f) {
      const vr = { state: 'CT', townsub: [town + ' town'], place: [], cd: f.cd ? { num: +f.cd } : null, upper: f.sd ? ['State Senate District ' + f.sd] : [], lower: f.ad ? ['State House District ' + f.ad] : [], matched: '1 Test St, ' + town + ', CT' };
      const g = K._gen26(vr); out.ct++; if (K._isVerified(g)) out.ctFull++; chk(g, 'CT ' + town + ' ' + f.vd); }
    const w = K._gen26({ state: 'CT', townsub: ['Waterbury town'], place: ['Waterbury city'], cd: { num: 5 }, upper: ['State Senate District 15'], lower: ['State House District 73'], matched: '88 AVALON CIR, WATERBURY, CT, 06710' });
    out.wtb = { ver: K._isVerified(w), n: w && w.contests.length, offices: w && w.contests.map(c => c.office || c.title) };
    const rv = { state: 'NY', county: ['Rockland County'], townsub: ['Ramapo town'], place: [], cd: { num: 17 }, upper: ['State Senate District 38'], lower: ['Assembly District 98'], matched: '41 S PARKER DR, MONSEY, NY, 10952' };
    await K._prepFull(rv); const m = K._gen26(rv); out.monsey = { ver: K._isVerified(m), n: m && m.contests.length }; chk(m, 'NY Monsey');
    const cl = { state: 'NY', county: ['Rockland County'], townsub: ['Clarkstown town'], place: [], cd: { num: 17 }, upper: ['State Senate District 38'], lower: ['Assembly District 96'], matched: '1 Test St, New City, NY' };
    const c2 = K._gen26(cl); out.clark = { ver: K._isVerified(c2), n: c2 && c2.contests.length }; chk(c2, 'NY Clarkstown (wards)');
    for (const ab of ['AL','AK','AZ','AR','CA','CO','DE','DC','FL','GA','HI','ID','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']) {
      const g = K._gen26({ state: ab, cd: { num: 1, code: '01' }, county: ['Nowhere County'], place: [], townsub: [], upper: [], lower: [], matched: '1 Main St, Nowhere, ' + ab + ' 00000' }); out.st++; chk(g, ab); }
    return out; });
  must(!r.bad.length, r.bad.slice(0, 5).join(' | '));
  must(r.wtb.ver && r.wtb.n === 9, 'Waterbury 88 Avalon Cir is not the complete 9-contest official ballot: ' + JSON.stringify(r.wtb));
  must(r.monsey.ver && r.monsey.n === 11, 'Monsey 41 S Parker Dr is not the complete 11-item official ballot: ' + JSON.stringify(r.monsey));
  must(!r.clark.ver, 'Clarkstown (ward unknown) must not claim a complete ballot');
  return 'CT ballots ' + r.ct + ' (complete ' + r.ctFull + ', rest labelled + button) · Waterbury ' + r.wtb.n + ' contests · Monsey ' + r.monsey.n + ' · ' + r.st + ' states labelled + button';
});
await test('v46: the "may not be complete" heading and the blue button are on the page for a labelled ballot', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const r = await page.evaluate(async () => { const K = window.KUS_BALLOT; await K._loadLinks();
    const g = K._gen26({ state: 'TX', cd: { num: 18, code: '18' }, county: ['Harris County'], place: ['Houston city'], townsub: [], upper: [], lower: [], matched: '901 BAGBY ST, HOUSTON, TX, 77002' });
    return { ver: K._isVerified(g), link: K._fullFor(g) }; });
  must(!r.ver && r.link && /See your complete official sample ballot/.test(r.link.label), 'Houston: ' + JSON.stringify(r));
  return 'Houston: labelled, button → ' + r.link.url;
});

// v49 (Shmuel, Nov 10 11:34 AM: full ballots "for every address in the u.s."): North Carolina from the State Board's own data, every county.
// An address on the State Board's street list gets its verified official ballot (checked against the printed sample ballot PDF and the canvass);
// anything else gets the "may not be complete" heading + the blue official button.
await test('v49: North Carolina — every county: an address on the State Board street list gets its verified official ballot; otherwise labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const r = await page.evaluate(async () => {
    const K = window.KUS_BALLOT; await K._loadLinks();
    const idx = await (await fetch('data/ballots/nc/index.json?x=' + Date.now())).json();
    const out = { counties: 0, styles: 0, full: 0, lab: 0, bad: [], real: {} };
    for (const [co, meta] of Object.entries(idx.counties)) {
      const vr0 = { state: 'NC', county: [co + ' County'], place: [], townsub: [], upper: [], lower: [] };
      await K._prepFull(vr0); const D = K._NCB.d[meta.f]; if (!D) { out.bad.push(co + ': file did not load'); continue; }
      out.counties++;
      /* one real address range per ballot style, straight from the State Board's street list */
      const ex = {};
      for (const [st, Z] of Object.entries(D.st)) for (const [zip, v] of Object.entries(Z)) {
        const rs = typeof v[0] === 'number' ? [[v[0], v[1], 0, v[2]]] : v;
        for (const q of rs) { const si = D.sp[q[3]][0]; if (ex[si]) continue;
          for (let h0 of [q[0] || 1, (q[0] || 1) + 2, Math.floor((q[0] + q[1]) / 2), q[1]]) { let h = h0; if (q[2] === 1 && h % 2 === 0) h++; if (q[2] === 2 && h % 2 === 1) h++; if (h > q[1] || h < 1) continue;
            const f = K._ncFind(D, K._ncParse(h + ' ' + st + ', X, NC, ' + zip)); const sty = [...new Set(f.styles.map(j => D.sp[j][0]))]; if (sty.length === 1 && sty[0] === si) { ex[si] = h + ' ' + st + ', X, NC, ' + zip; break; } } }
      }
      D.s.forEach((S, i) => { out.styles++; const a = ex[i]; if (!a) { out.bad.push(co + ' style ' + i + ': no address pins it'); return; }
        const g = K._gen26(Object.assign({}, vr0, { matched: a })); const ver = K._isVerified(g);
        if (S.ok) { if (!ver || g.contests.length !== S.o.length) out.bad.push(co + ' ' + a + ': verified style not shown complete'); else out.full++; }
        else { const l = K._fullFor(g); if (ver || !(l && /official sample ballot/i.test(l.label))) out.bad.push(co + ' ' + a + ': unverified style without label/button'); else out.lab++; }
        if (ver && !/^https:\/\/dl\.ncsbe\.gov\//.test(g.fullLink && g.fullLink.url || '')) out.bad.push(co + ' ' + a + ': no official PDF link'); });
      const nf = K._gen26(Object.assign({}, vr0, { matched: '999999 NO SUCH STREET RD, X, NC, 27000' })); const l = K._fullFor(nf);
      if (K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label) && /ncsbe\.gov/.test(l.url))) out.bad.push(co + ': unknown street not labelled + button');
    }
    /* real addresses, as the Census geocoder returns them */
    const real = [['Mecklenburg', '600 E 4TH ST, CHARLOTTE, NC, 28202'], ['Guilford', '300 W WASHINGTON ST, GREENSBORO, NC, 27401'], ['Forsyth', '101 N MAIN ST, WINSTON SALEM, NC, 27101'],
      ['Transylvania', '2 E MAIN ST, BREVARD, NC, 28712'], ['Pender', '15027 STATE HWY 210, ROCKY POINT, NC, 28457'], ['Brunswick', '1474 SHELL DR, SHALLOTTE, NC, 28470']];
    for (const [co, a] of real) { const vr = { state: 'NC', county: [co + ' County'], place: [], townsub: [], upper: [], lower: [], matched: a }; await K._prepFull(vr);
      const g = K._gen26(vr); out.real[a] = { ver: K._isVerified(g), n: g && g.contests.length, first: g && g.contests[0] && (g.contests[0].office || g.contests[0].title) }; }
    return out; });
  must(r.counties === 100, 'NC counties loaded: ' + r.counties);
  must(!r.bad.length, r.bad.slice(0, 6).join(' | '));
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.n > 10 && x.first === 'US Senate', a + ': ' + JSON.stringify(x));
  return 'NC: ' + r.counties + ' counties, ' + r.styles + ' ballot styles (' + r.full + ' complete, ' + r.lab + ' labelled + button) · real addresses: ' + Object.entries(r.real).map(([a, x]) => a.split(',')[1].trim() + ' ' + x.n).join(', ');
});
await test('v49: Philadelphia — every official split (Congress-Senate-House) gives its verified official ballot; unmatched districts labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const r = await page.evaluate(async () => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {} };
    const base = { state: 'PA', county: ['Philadelphia County'], place: ['Philadelphia city'], townsub: [] };
    await K._prepFull(base); const D = K._PHL.d; if (!D) return { bad: ['data did not load'] };
    for (const [k, S] of Object.entries(D.s)) { const [cd, sd, hd] = k.split('-');
      const vr = Object.assign({}, base, { cd: { num: +cd, code: cd.padStart(2, '0') }, upper: [sd === 'xx' ? 'State Senate District 1' : 'State Senate District ' + sd], lower: ['State House District ' + hd], matched: '1 TEST ST, PHILADELPHIA, PA, 19107' });
      const g = K._gen26(vr); out.n++; if (K._isVerified(g) && g.contests.length === S.o.length + D.q.length && /vote\.phila\.gov/.test(g.fullLink.url)) out.full++; else out.bad.push(k); }
    const nf = K._gen26(Object.assign({}, base, { cd: { num: 9, code: '09' }, upper: ['State Senate District 99'], lower: ['State House District 999'], matched: '1 TEST ST, PHILADELPHIA, PA, 19107' }));
    const l = K._fullFor(nf); if (K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('unmatched not labelled');
    for (const [a, cd, sd, hd] of [['1400 JOHN F KENNEDY BLVD, PHILADELPHIA, PA, 19107', 3, 1, 182], ['3401 WALNUT ST, PHILADELPHIA, PA, 19104', 3, 8, 188], ['7700 FRANKFORD AVE, PHILADELPHIA, PA, 19136', 2, 5, 173]]) {
      const g = K._gen26(Object.assign({}, base, { cd: { num: cd, code: String(cd).padStart(2, '0') }, upper: ['State Senate District ' + sd], lower: ['State House District ' + hd], matched: a }));
      out.real[a] = { ver: K._isVerified(g), n: g && g.contests.length }; }
    return out; });
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.n >= 5, a + ': ' + JSON.stringify(x));
  return 'Philadelphia: ' + r.full + '/' + r.n + ' splits complete · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' ' + x.n).join(', ');
});
await test('v50: Montgomery County, PA — every voting district on the county map gives its official printed ballot; an address off the map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["100 E HECTOR ST, CONSHOHOCKEN, PA, 19428", -75.30579, 40.072857, "Conshohocken 2", 5], ["1950 SCHOOL RD, HATFIELD, PA, 19440", -75.285481, 40.285108, "Hatfield 2-1", 5], ["1 MONTGOMERY AVE, NORRISTOWN, PA, 19401", -75.321467, 40.13269, "East Norriton 2-2", 3]];
  const r = await page.evaluate(async (real) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'PA', county: ['Montgomery County'], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: -75.3, y: 40.2, matched: 'PRELOAD' })); const C = K._PAC.montgomery; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 400 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: 'MC ' + key + ', PA' }); await K._prepFull(vr);
      const g = K._gen26(vr), S = C.d.s[key];
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'Governor and Lieutenant Governor' && /montcopa\.org/.test(g.fullLink.url)) { out.full++; out.q += g.contests.filter(c => c.type === 'measure').length ? 1 : 0; } else out.bad.push(key); }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP, PA' }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, real);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 431, 'districts complete: ' + r.full + '/' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Montgomery: ' + r.full + '/' + r.n + ' voting districts complete (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v50: Delaware County, PA — every voting district on the county map gives its official printed ballot; an address off the map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["201 W FRONT ST, MEDIA, PA, 19063", -75.391329, 39.91921, "MEDIA BOR PRECINCT NORTHERN", 5], ["3300 CONCORD RD, ASTON, PA, 19014", -75.423169, 39.867005, "ASTON TWP WD05", 4], ["8501 LANSDOWNE AVE, UPPER DARBY, PA, 19082", -75.293447, 39.965717, "UPPER DARBY TWP 04 08", 5]];
  const r = await page.evaluate(async ([real, ck, cn]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, lab: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'PA', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647; const done = {};
    for (const p of C.geo.p) { const [key, b] = p; if (done[key]) continue; done[key] = 1; let pt = null;
      for (let i = 0; i < 600 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', PA' }); await K._prepFull(vr);
      const g = K._gen26(vr), S = C.d.s[key];
      if (S && S.ok) { if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && /^Governor/.test(g.contests[0].office) && /delcopa\.gov/.test(g.fullLink.url)) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key); }
      else { const l = K._fullFor(g); if (g && !K._isVerified(g) && l && /official sample ballot/i.test(l.label)) out.lab++; else out.bad.push(key + ' should be labelled'); } }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, "delaware", "Delaware County"]);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 381 && r.n === 383, 'districts complete: ' + r.full + '/' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Delaware County, PA: ' + r.full + '/' + r.n + ' complete, ' + r.lab + ' labelled + button (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v50: Chester County, PA — every voting district on the county map gives its official printed ballot; an address off the map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["313 W MARKET ST, WEST CHESTER, PA, 19382", -75.609111, 39.95768, "850 WEST CHESTER 6", 3], ["1 W LANCASTER AVE, PAOLI, PA, 19301", -75.484228, 40.041976, "630 TREDYFFRIN W-1", 4], ["117 E KING ST, MALVERN, PA, 19355", -75.513384, 40.036586, "350 MALVERN", 4], ["201 N UNION ST, KENNETT SQUARE, PA, 19348", -75.712403, 39.847684, "305 KENNETT SQUARE NORTH", 3]];
  const r = await page.evaluate(async ([real, ck, cn]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, lab: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'PA', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647; const done = {};
    for (const p of C.geo.p) { const [key, b] = p; if (done[key]) continue; done[key] = 1; let pt = null;
      for (let i = 0; i < 600 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', PA' }); await K._prepFull(vr);
      const g = K._gen26(vr), S = C.d.s[key];
      if (S && S.ok) { if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && /^Governor/.test(g.contests[0].office) && /chesco\.org/.test(g.fullLink.url)) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key); }
      else { const l = K._fullFor(g); if (g && !K._isVerified(g) && l && /official sample ballot/i.test(l.label)) out.lab++; else out.bad.push(key + ' should be labelled'); } }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, "chester", "Chester County"]);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 230 && r.n === 230, 'districts complete: ' + r.full + '/' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Chester County, PA: ' + r.full + '/' + r.n + ' complete, ' + r.lab + ' labelled + button (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v51: Hamilton County, OH — every precinct on the county map gives its official printed ballot; split precincts pick the split by school district / district; unmatched is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["801 PLUM ST, CINCINNATI, OH, 45202", -84.518867, 39.104334, "CINCINNATI 16-A", 31, ["Cincinnati City School District"]], ["11500 LEBANON RD, SHARONVILLE, OH, 45241", -84.403502, 39.281672, "SHARONVILLE 3-A", 30, ["Princeton City School District"]], ["6303 HARRISON AVE, CINCINNATI, OH, 45247", -84.65172, 39.186165, "GREEN CC", 29, ["Oak Hills Local School District"]], ["7000 BLUE ASH RD, CINCINNATI, OH, 45236", -84.40012, 39.197111, "SILVERTON C", 30, ["Cincinnati City School District"]]];
  const r = await page.evaluate(async ([real, p3701]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, splitP: 0, splitOK: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'OH', county: ['Hamilton County'], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD HAM' })); const C = K._PAC.hamilton; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    const title = (k) => k.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()) + ' City School District';
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 600 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key];
      if (S.ok) { const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: 'HAM ' + key + ', OH' }); await K._prepFull(vr); const g = K._gen26(vr);
        if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && /^Governor/.test(g.contests[0].office) && /votehamiltoncountyohio\.gov/.test(g.fullLink.url)) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key); continue; }
      out.splitP++; const all = {}; S.splits.forEach((x) => x.sch.forEach((k) => { all[k] = 1; }));
      for (const x of S.splits) {
        const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: 'HAM ' + key + ' s' + x.pdf.slice(-5), unified: x.sch.length ? [title(x.sch[0])] : ['Somewhere Else City School District'] });
        if (x.cd) vr.cd = { num: +x.cd, code: x.cd.padStart(2, '0') }; if (x.hd) vr.lower = ['State House District ' + x.hd]; if (x.sd) vr.upper = ['State Senate District ' + x.sd];
        await K._prepFull(vr); const g = K._gen26(vr);
        if (g && K._isVerified(g) && g.precinct === key && g.contests.length === x.o.length && g.fullLink.url === x.pdf) out.splitOK++; else out.bad.push(key + ' split ' + x.pdf.slice(-6)); }
      const un = Object.assign({}, base, { x: pt[0], y: pt[1], matched: 'HAM ' + key + ' unknown', unified: [] }); await K._prepFull(un); const gu = K._gen26(un), lu = K._fullFor(gu);
      const needs = Object.keys(all).length > 0 || S.splits.some((x) => x.cd || x.hd || x.sd);
      if (needs && !(gu && !K._isVerified(gu) && lu && /official sample ballot/i.test(lu.label))) out.bad.push(key + ' unknown split not labelled'); }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP HAM' }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n, u] of real) { const vr = Object.assign({}, base, { x, y, matched: a, unified: u }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, [-84.30172528547784, 39.266688548953375]]);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 511 && r.splitP === 52 && r.splitOK === 107, 'precincts complete: ' + r.full + ' + ' + r.splitOK + ' splits in ' + r.splitP + ' split precincts / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Hamilton County, OH: ' + r.full + ' single-ballot precincts + ' + r.splitOK + ' splits in ' + r.splitP + ' split precincts complete (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v51: Lucas County, OH — every precinct on the county map gives its official printed ballot; split precincts pick the split by school district / district, else labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["640 JACKSON ST, TOLEDO, OH, 43604", -83.53507, 41.655101, "TOLEDO 8E", 27, ["Toledo City School District"]], ["6730 MONROE ST, SYLVANIA, OH, 43560", -83.70568, 41.715569, "SYLVANIA CITY 4", 23, ["Sylvania City School District"]], ["400 CONANT ST, MAUMEE, OH, 43537", -83.65387, 41.562956, "MAUMEE 3", 27, ["Maumee City School District"]], ["5330 SEAMAN ST, OREGON, OH, 43616", -83.420897, 41.652425, "OREGON 5", 26, ["Oregon City School District"]], ["2 MAIN ST, TOLEDO, OH, 43605", -83.526517, 41.651178, "TOLEDO 14A", 27, ["Toledo City School District"]]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, splitOK: 0, lab: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'OH', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    const title = (k) => k.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()) + ' City School District';
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647; const done = {};
    for (const p0 of C.geo.p) { const key = p0[0]; if (done[key]) continue; done[key] = 1; let pt = null;
      for (const p of C.geo.p.filter((q) => q[0] === key)) { const b = p[1];
        for (let i = 0; i < 600 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; } }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S) { out.bad.push(key + ': no ballot'); continue; }
      if (S.ok) { const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', OH' }); await K._prepFull(vr); const g = K._gen26(vr);
        if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && /^Governor/.test(g.contests[0].office) && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key); continue; }
      if (S.splits[0].ok) {
        for (const x of S.splits) {
          const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ' ' + x.pdf.slice(-12), unified: x.sch.length ? [title(x.sch[0])] : ['Somewhere Else City School District'] });
          if (x.cd) vr.cd = { num: +x.cd, code: x.cd.padStart(2, '0') }; if (x.hd) vr.lower = ['State House District ' + x.hd]; if (x.sd) vr.upper = ['State Senate District ' + x.sd];
          await K._prepFull(vr); const g = K._gen26(vr);
          if (g && K._isVerified(g) && g.precinct === key && g.contests.length === x.o.length && g.fullLink.url === x.pdf) out.splitOK++; else out.bad.push(key + ' split ' + x.pdf.slice(-8)); }
      } else { const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ' unresolved', unified: ['Somewhere Else City School District'] }); await K._prepFull(vr); const g = K._gen26(vr), l = K._fullFor(g);
        if (g && !K._isVerified(g) && l && /official sample ballot/i.test(l.label)) out.lab++; else out.bad.push(key + ' should be labelled'); } }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n, u] of real) { const vr = Object.assign({}, base, { x, y, matched: a, unified: u }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'lucas', 'Lucas County', 'lookup.boe.ohio.gov/vtrapp/lucas']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 259 && r.splitOK === 36 && r.lab === 4, 'complete: ' + r.full + ' + ' + r.splitOK + ' splits, labelled ' + r.lab + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Lucas County, OH: ' + r.full + ' single-ballot precincts + ' + r.splitOK + ' splits complete, ' + r.lab + ' split precincts labelled + button (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v51: Montgomery County, OH — every precinct on the county map gives its official printed ballot; split precincts pick the split by school district / district, else labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["10 N 1ST ST, MIAMISBURG, OH, 45342", -84.287713, 39.641861, "MIAMISBURG 2-A", 23, ["Miamisburg City School District"]]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, splitOK: 0, lab: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'OH', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    const title = (k) => k.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase()) + ' City School District';
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647; const done = {};
    for (const p of C.geo.p) { const [key, b] = p; if (done[key]) continue; done[key] = 1; let pt = null;
      for (let i = 0; i < 600 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S) { out.bad.push(key + ': no ballot'); continue; }
      if (S.ok) { const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', OH' }); await K._prepFull(vr); const g = K._gen26(vr);
        if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && /^Governor/.test(g.contests[0].office) && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key); continue; }
      if (S.splits[0].ok) {
        for (const x of S.splits) {
          const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ' ' + x.pdf.slice(-12), unified: x.sch.length ? [title(x.sch[0])] : ['Somewhere Else City School District'] });
          if (x.cd) vr.cd = { num: +x.cd, code: x.cd.padStart(2, '0') }; if (x.hd) vr.lower = ['State House District ' + x.hd]; if (x.sd) vr.upper = ['State Senate District ' + x.sd];
          await K._prepFull(vr); const g = K._gen26(vr);
          if (g && K._isVerified(g) && g.precinct === key && g.contests.length === x.o.length && g.fullLink.url === x.pdf) out.splitOK++; else out.bad.push(key + ' split ' + x.pdf.slice(-8)); }
      } else { const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ' unresolved', unified: ['Somewhere Else City School District'] }); await K._prepFull(vr); const g = K._gen26(vr), l = K._fullFor(g);
        if (g && !K._isVerified(g) && l && /official sample ballot/i.test(l.label)) out.lab++; else out.bad.push(key + ' should be labelled'); } }
    const off = Object.assign({}, base, { x: -77.0, y: 39.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n, u] of real) { const vr = Object.assign({}, base, { x, y, matched: a, unified: u }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'montgomeryoh', 'Montgomery County', 'lookup.boe.ohio.gov/vtrapp/montgomery']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 347 && r.splitOK === 39 && r.lab === 15, 'complete: ' + r.full + ' + ' + r.splitOK + ' splits, labelled ' + r.lab + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Montgomery County, OH: ' + r.full + ' single-ballot precincts + ' + r.splitOK + ' splits complete, ' + r.lab + ' split precincts labelled + button (' + r.q + ' with local questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v53: Palm Beach County, FL — every precinct on the Supervisor of Elections map gives its official printed ballot (all races, retention and amendments); off-map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["301 N OLIVE AVE, WEST PALM BEACH, FL, 33401", -80.051908, 26.715294, "7654", 22], ["360 N COUNTY RD, PALM BEACH, FL, 33480", -80.038113, 26.725203, "5601", 23], ["100 NE 1ST AVE, DELRAY BEACH, FL, 33444", -80.072196, 26.463516, "2430", 21], ["201 W PALMETTO PARK RD, BOCA RATON, FL, 33432", -80.089844, 26.350527, "1724", 22], ["10500 N MILITARY TRL, PALM BEACH GARDENS, FL, 33410", -80.105316, 26.830957, "5729", 23]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'FL', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 800 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S || !S.ok) { out.bad.push(key + ': no ballot'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', FL' }); await K._prepFull(vr); const g = K._gen26(vr);
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'United States Senator' && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key + ' ' + (g && g.contests.length)); }
    const off = Object.assign({}, base, { x: -81.9, y: 26.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = nf && K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'palmbeach', 'Palm Beach County', 'votepalmbeach.gov']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 812, 'complete: ' + r.full + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Palm Beach County, FL: ' + r.full + ' of ' + r.n + ' precincts complete (' + r.q + ' with questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v54: Orange County, FL — every precinct (and each part of a split precinct) on the Supervisor of Elections maps gives its official printed ballot; off-map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["400 S ORANGE AVE, ORLANDO, FL, 32801", -81.37896, 28.538316, "610 (ballot 233G)", 16], ["300 N PARK AVE, WINTER PARK, FL, 32789", -81.350992, 28.599639, "519", 16], ["300 W PLANT ST, WINTER GARDEN, FL, 34787", -81.589084, 28.565038, "104 (ballot 004G)", 16], ["120 W MAIN ST, APOPKA, FL, 32703", -81.51442, 28.674442, "216", 15], ["4000 CENTRAL FLORIDA PKWY, ORLANDO, FL, 32837", -81.424502, 28.410271, "805", 17]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'FL', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 800 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S || !S.ok) { out.bad.push(key + ': no ballot'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', FL' }); await K._prepFull(vr); const g = K._gen26(vr);
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'United States Senator' && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key + ' ' + (g && g.contests.length)); }
    const off = Object.assign({}, base, { x: -81.9, y: 26.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = nf && K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'orange', 'Orange County', 'voteorangefl.gov']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 330, 'complete: ' + r.full + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Orange County, FL: ' + r.full + ' of ' + r.n + ' precinct ballots complete (' + r.q + ' with questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v56: Brevard County, FL — every precinct on the Supervisor of Elections precinct map gives its official printed ballot (one ballot per precinct); off-map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["2725 JUDGE FRAN JAMIESON WAY, MELBOURNE, FL, 32940", -80.731806, 28.247713, "424", 18], ["120 MALABAR RD SW, PALM BAY, FL, 32907", -80.673307, 27.998982, "516", 20], ["900 E STRAWBRIDGE AVE, MELBOURNE, FL, 32901", -80.606937, 28.079443, "509", 22], ["2 S ORLANDO AVE, COCOA BEACH, FL, 32931", -80.610157, 28.318382, "222", 20]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'FL', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 800 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S || !S.ok) { out.bad.push(key + ': no ballot'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', FL' }); await K._prepFull(vr); const g = K._gen26(vr);
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'United States Senator' && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key + ' ' + (g && g.contests.length)); }
    const off = Object.assign({}, base, { x: -81.9, y: 26.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = nf && K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'brevard', 'Brevard County', 'votebrevard.gov']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 166, 'complete: ' + r.full + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Brevard County, FL: ' + r.full + ' of ' + r.n + ' precincts complete (' + r.q + ' with questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v58: Osceola County, FL — every precinct on the Supervisor of Elections precinct map gives its official printed ballot (one ballot per precinct); off-map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["1300 9TH ST, ST CLOUD, FL, 34769", -81.2836, 28.249718, "5200", 13], ["7380 W IRLO BRONSON MEMORIAL HWY, KISSIMMEE, FL, 34747", -81.582968, 28.332356, "1001", 13], ["3500 HARMONY SQUARE DR W, HARMONY, FL, 34773", -81.145588, 28.19015, "5505", 15], ["1300 POINCIANA BLVD, KISSIMMEE, FL, 34746", -81.479482, 28.271682, "1003", 13], ["101 N CHURCH ST, KISSIMMEE, FL, 34741", -81.407227, 28.294202, "4101", 15]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'FL', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 800 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      out.n++; if (!pt) { out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (!S || !S.ok) { out.bad.push(key + ': no ballot'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', FL' }); await K._prepFull(vr); const g = K._gen26(vr);
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'United States Senator' && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key + ' ' + (g && g.contests.length)); }
    const off = Object.assign({}, base, { x: -81.9, y: 26.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = nf && K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'osceola', 'Osceola County', 'voteosceola.gov']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 150, 'complete: ' + r.full + ' / ' + r.n);
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Osceola County, FL: ' + r.full + ' of ' + r.n + ' precincts complete (' + r.q + ' with questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});
await test('v47: tapping the tab you are in goes to that tab\'s home and the top (Officials, Election, Bills, Voter, Learn, More)', async () => {
  const tapTab = (t) => page.evaluate((t) => document.querySelector('.tabbar a[data-tab="' + t + '"]').click(), t);
  const out = [];
  const cases = [['officials', '#/federal', '#/'], ['officials', '#/s/OH/local/39035/p78932', '#/'], ['election', '#/election/house/OH', '#/election'],
    ['bills', '#/bills', '#/bills'], ['voter', '#/voter', '#/voter'], ['founding', '#/federalist/85', '#/founding'], ['more', '#/about', '#/more']];
  for (const [t, from, root] of cases) {
    await go(from, 2200);
    await page.evaluate(() => window.scrollTo(0, Math.max(400, document.body.scrollHeight / 2))); await page.waitForTimeout(250);
    await tapTab(t); await page.waitForTimeout(1600);
    const r = await page.evaluate(() => ({ h: location.hash || '#/', y: Math.round(window.scrollY), sheet: !!(document.querySelector('#sheet') && document.querySelector('#sheet').classList.contains('open')) }));
    const rootOk = r.h.replace(/^#\/?/, '') === root.replace(/^#\/?/, '');
    must(rootOk, t + ' tab from ' + from + ' went to ' + r.h + ' (want ' + root + ')');
    must(r.y < 40, t + ' tab home is not at the top (scrollY ' + r.y + ')');
    must(!r.sheet, t + ' tab home left a bottom sheet open');
    out.push(t + ' ✓');
  }
  // already at the root: a tap scrolls back to the top
  await go('#/', 1800); await page.evaluate(() => window.scrollTo(0, 900)); await page.waitForTimeout(200);
  await tapTab('officials'); await page.waitForTimeout(1200);
  must(await page.evaluate(() => window.scrollY) < 40, 'tapping Officials at home did not scroll to the top');
  // a different tab still keeps its place
  await go('#/federal', 1500); await tapTab('bills'); await page.waitForTimeout(1200); await tapTab('officials'); await page.waitForTimeout(1500);
  must((await page.evaluate(() => location.hash)) === '#/federal', 'switching tabs no longer returns to where you were');
  return out.join(' ');
});
await test('v47: every University Heights official with a photo shows it on Local, with a credit and Contact on their page', async () => {
  await go('#/s/OH/local/39035/p78932', 4000);
  const r = await page.evaluate(() => ({ imgs: [...document.querySelectorAll('#app img')].filter(i => /^Photo of/.test(i.alt)).map(i => [i.alt, i.complete && i.naturalWidth > 0]) }));
  must(r.imgs.length >= 12, 'UH Local shows only ' + r.imgs.length + ' photos');
  for (let k = 0; k < r.imgs.length; k++) { await page.evaluate((k) => [...document.querySelectorAll('#app img')].filter(i => /^Photo of/.test(i.alt))[k].scrollIntoView({ block: 'center' }), k); await page.waitForTimeout(250); }
  await page.waitForTimeout(1500);
  const broken = await page.evaluate(() => [...document.querySelectorAll('#app img')].filter(i => /^Photo of/.test(i.alt) && !(i.complete && i.naturalWidth > 0)).map(i => i.alt));
  must(!broken.length, 'broken photos: ' + broken.join(', '));
  await go('#/s/OH/local/39035/p78932/o/0', 3000);
  const p = await page.evaluate(() => ({ t: document.querySelector('#app').innerText, tel: (document.querySelector('#app .ctbox a[href^="tel:"]') || {}).getAttribute ? document.querySelector('#app .ctbox a[href^="tel:"]').getAttribute('href') : '', credit: /Photo:/.test(document.querySelector('#app').innerText) }));
  must(/Contact/i.test(p.t) && /Source/.test(p.t), 'Mayor page has no Contact block with Source');
  must(p.tel === 'tel:+12169327800,222', 'Mayor phone link dials ' + p.tel + ' (want tel:+12169327800,222)');
  must(p.credit, 'Mayor page has no Photo: credit');
  return r.imgs.length + ' photos on UH Local';
});

await test('v48: the Election tab reads the watchdog\'s refreshed official counts (repo data/elections) for this build, else its own copy', async () => {
  const has = await page.evaluate(() => typeof window.KUS_ELEC_GET === 'function');
  if (!has) return 'skipped: this build predates v48 (no KUS_ELEC_GET)';
  const r = await page.evaluate(async () => {
    const E = window.KUS_ELECTION; await E.refresh(true);
    const base = (window.KUS_GH_BASE || 'https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/') + 'elections/';
    const repo = await fetch(base + 'election-official.json?t=' + Date.now()).then(x => x.ok ? x.json() : null).catch(() => null);
    const snap = window.KUS_ELECTION_SNAPSHOT || {};
    const usable = !!(repo && repo.builtAt && (!snap.builtAt || Date.parse(repo.builtAt) >= Date.parse(snap.builtAt)));
    const pick = d => { const g = (d && d.gov && d.gov.MD || [])[0]; return g ? g.cands.map(c => c.votes).join(',') : ''; };
    const sw = await window.KUS_ELEC_GET('statewide.json', 'data/statewide.json?v=20');
    const dist = await window.KUS_ELEC_GET('districts/UT.json', 'data/districts/UT.json?v=20');
    return { usable, fromRepo: !!(E.data && E.data.fromRepo), same: usable ? pick(E.data) === pick(repo) : true, sw: !!(sw && sw.gov), dist: !!(dist && dist.off && dist.off.r) };
  });
  must(r.usable === r.fromRepo, 'repo copy usable=' + r.usable + ' but the app used ' + (r.fromRepo ? 'the repo copy' : 'its own copy'));
  must(r.same, 'the app shows different MD Governor counts than the repo copy');
  must(r.sw && r.dist, 'statewide or district counts did not load');
  return r.fromRepo ? 'reads data/elections from the repo (counts refreshed by the watchdog)' : 'repo copy not for this build; uses its own copy';
});

await newPage();
await test('AI summary box under the official summary on bills and executive orders (repo data/ai-summaries)', async () => {
  const src = await page.evaluate(async (s) => { const g = u => fetch(s + u + '?t=' + Date.now()).then(x => x.ok ? x.text() : '').catch(() => ''); return { a: await g('account.js'), e: await g('eo.js') }; }, SITE);
  if (!/ai-summaries/.test(src.a) || !/ai-summaries/.test(src.e)) return 'skipped: this build predates the AI summary files';
  const base = 'https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/ai-summaries/';
  const repo = await page.evaluate(async (b) => { const g = u => fetch(b + u + '?t=' + Date.now()).then(x => x.ok ? x.json() : null).catch(() => null); return { us: await g('US.json'), eo: await g('EO.json') }; }, base);
  must(repo.us && repo.eo, 'the AI summary files did not load from the repo');
  // H.R. 8313 is the bill in Shmuel's screenshot (Nov 10) that had no AI box; it must be in the app's bill list too
  const lists = await page.evaluate(async (s) => { const g = u => fetch(u).then(x => x.ok ? x.json() : null).catch(() => null); return [await g(s + 'data/bills/US.json'), await g('https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/bills/US.json?t=' + Date.now())]; }, SITE);
  const inList = new Set(lists.flatMap(l => ((l && l.bills) || []).map(b => b.id)));
  const bid = repo.us.items['US-119-HR8313'] && inList.has('US-119-HR8313') ? 'US-119-HR8313' : Object.keys(repo.us.items).find(k => inList.has(k)),
    eo = Object.keys(repo.eo.items).sort((a, b) => b - a)[0];
  must(bid, 'no bill in the app list has an AI summary');
  await go('#/bill/' + bid, 4500);
  let t = (await text()).toLowerCase();
  must(/what it does/.test(t), 'bill page did not load for ' + bid);
  must(/ai summary/.test(t) && /written by ai from the bill.s official text/.test(t), 'no AI summary box on ' + bid);
  must(t.indexOf('what it does') < t.indexOf('ai summary'), 'AI summary is not below the official summary on ' + bid);
  const nt = Object.keys(repo.us.noText || {}).find(k => inList.has(k));
  if (nt) { await go('#/bill/' + nt, 4000); t = (await text()).toLowerCase(); must(!/ai summary/.test(t), 'AI box shown on ' + nt + ', which has no fetchable official text'); }
  await go('#/bills/eo/' + eo, 4500);
  t = (await text()).toLowerCase();
  must(/ai summary/.test(t) && /written by ai from the order.s official text/.test(t), 'no AI summary box on EO ' + eo);
  must(/status/.test(t) && t.indexOf('status') < t.indexOf('ai summary'), 'EO page layout changed around the AI box');
  return bid + ' and EO ' + eo + ' show the AI box under the official summary' + (nt ? '; ' + nt + ' (no official text yet) shows none' : '');
});

await newPage();
await test('v55: people search matches the names people use (Bernie Sanders, Chuck Schumer, sanders bernard)', async () => {
  const src = await page.evaluate(async (s) => fetch(s + 'app.js?t=' + Date.now()).then(x => x.text()).catch(() => ''), SITE);
  if (!/nameToks/.test(src)) return 'skipped: this build predates the v55 name search';
  const out = [];
  for (const [q, id] of [['Bernie Sanders', 'S000033'], ['Chuck Schumer', 'S000148'], ['sanders bernard', 'S000033'], ['Sanders', 'S000033']]) {
    await go('#/', 2500);
    await page.fill('#q', ''); await page.type('#q', q, { delay: 20 }); await page.waitForTimeout(1200);
    const hit = await page.$('#results a[href="#/p/' + id + '"]');
    must(hit, 'typing "' + q + '" does not show #/p/' + id);
    out.push(q + ' → ' + id);
  }
  return out.join(', ');
});


// v56 KUS-STANCE (Shmuel, Nov 10 11:20 PM): thumbs up / thumbs down on every bill and executive order, saved to the account like
// tracked bills, listed under Tracked > Support / Against. No test account here (the captcha rule), so the account is a mock
// Firestore (users/{uid} kept in localStorage '__kus_fakefs', which the app never touches) used through the same profile code
// (loadProfile / setPref / saveProfile) that real accounts use. "Another device" = a reload with the app's own copies wiped.
await test('Support / Against: thumbs on bill + EO pages, Tracked sub-tabs, saved to the account (survives reload / new device), switching moves it', async () => {
  await newPage();
  const src0 = await page.evaluate(async (s) => fetch(s + 'stance.js?t=' + Date.now()).then(x => x.ok ? x.text() : '').catch(() => ''), SITE);
  if (!/KUS_STANCE/.test(src0)) return 'skipped: this build predates v56 Support / Against';
  const signIn = async (wipeLocal) => {
    await page.waitForFunction(() => window.KUS_ACC && window.KUS_STANCE && KUS_ACC.trackedSnapshot && KUS_ACC.trackedSnapshot() !== null, null, { timeout: 30000 });
    await page.evaluate((wipe) => {
      const K = '__kus_fakefs', rd = () => { try { return JSON.parse(localStorage.getItem(K) || '{}'); } catch (e) { return {}; } }, wr = s => localStorage.setItem(K, JSON.stringify(s));
      if (wipe) Object.keys(localStorage).filter(k => /^kus_(prefs|profile_|pending_)/.test(k)).forEach(k => localStorage.removeItem(k));
      const setPath = (o, p, v) => { const ks = p.split('.'); let x = o; ks.slice(0, -1).forEach(k => { x = x[k] = x[k] || {}; }); if (v && v.__del) delete x[ks[ks.length - 1]]; else x[ks[ks.length - 1]] = v; };
      window.__fsWrites = 0;
      const FB = { doc: (db, c, id) => ({ c, id }), collection: (db, c) => ({ c }), serverTimestamp: () => new Date().toISOString(), deleteField: () => ({ __del: 1 }),
        getDoc: r => Promise.resolve((s => ({ exists: () => !!s, data: () => JSON.parse(JSON.stringify(s)) }))(rd()[r.c + '/' + r.id])),
        setDoc: (r, d) => { const s = rd(); s[r.c + '/' + r.id] = JSON.parse(JSON.stringify(d)); wr(s); window.__fsWrites++; return Promise.resolve(); },
        updateDoc: (r, d) => { const s = rd(), k = r.c + '/' + r.id; if (!s[k]) return Promise.reject(Object.assign(new Error('no doc'), { code: 'not-found' })); Object.keys(d).forEach(p => setPath(s[k], p, JSON.parse(JSON.stringify(d[p])))); wr(s); window.__fsWrites++; return Promise.resolve(); },
        deleteDoc: () => Promise.resolve() };
      const u = { uid: 'stance-test', email: 'stance-test@example.com', emailVerified: false, displayName: 'Test', reload: () => Promise.resolve(), getIdToken: () => Promise.resolve('x') };
      KUS_ACC._test.set({ user: u, FB, db: {}, storage: 'ok', profile: null });
      return KUS_ACC._test.loadProfile();
    }, !!wipeLocal);
    await page.waitForFunction(() => { const g = KUS_ACC._test.get(); return g.profile && g.storage === 'ok'; }, null, { timeout: 15000 });
  };
  const server = () => page.evaluate(() => { const s = JSON.parse(localStorage.getItem('__kus_fakefs') || '{}')['users/stance-test'] || {}; return (s.prefs && s.prefs.stance) || {}; });
  const btn = k => page.$('#app .bdacts [data-stance="' + k + '"]');
  const pressed = async k => (await (await btn(k)).getAttribute('aria-pressed')) === 'true';
  const listTxt = async (h) => { await page.evaluate(x => { location.hash = x; }, h); await page.waitForTimeout(2500); return text(); };

  // signed out: the thumbs are there (icon-only, labelled) and ask for sign-in instead of saving
  await go('#/bills', 2500);
  const bid = await page.evaluate(() => fetch('data/bills/US.json').then(r => r.json()).then(d => d.bills[0].id)).catch(() => null) || null;
  await go('#/bill/' + encodeURIComponent(bid || 'US-119-HR1'), 4000);
  const B = await page.evaluate(() => ([...document.querySelectorAll('#app .bdacts [data-stance]')].map(b => ({ k: b.dataset.stance, l: b.getAttribute('aria-label'), t: b.textContent.trim(), svg: !!b.querySelector('svg') }))));
  must(B.length === 2 && B[0].l === 'Support' && B[1].l === 'Against' && !B[0].t && !B[1].t && B[0].svg && B[1].svg, 'bill page should have two icon-only thumbs labelled Support / Against: ' + JSON.stringify(B));
  if (!(await page.evaluate(() => KUS_ACC.signedIn()))) { await (await btn('support')).click(); await page.waitForTimeout(300);
    must(/sign in to save support and against/i.test(await text()), 'signed out: tapping 👍 did not ask to sign in'); must(!(await pressed('support')), 'signed out: 👍 lit up without an account'); }

  // signed in: 👍 the bill
  await signIn(true); await page.waitForTimeout(1500);
  await (await btn('support')).click(); await page.waitForTimeout(800);
  must(await pressed('support') && !(await pressed('against')), '👍 did not turn on');
  must((await server())[bid] && (await server())[bid].s === 'support', 'support was not written to the account doc: ' + JSON.stringify(await server()));
  const num = await page.$eval('#app .bdhead .bnum', x => x.textContent.trim());
  let t = await listTxt('#/bills/support');
  must(/Tracked/.test(t) && /Support \(1\)/.test(t) && /Against/.test(t), 'no Tracked / Support (1) / Against sub-tabs: ' + t.slice(0, 300));
  must(t.includes(num), 'Support list does not show ' + num);
  must(!(await listTxt('#/bills/against')).includes(num), 'Against list shows a supported bill');

  // executive order: 👍 it too
  const eo = await page.evaluate(() => fetch('data/eo/index.json').then(r => r.json()).then(i => { const p = i.presidents[0]; return fetch('data/eo/' + p.id + '.json').then(r => r.json()).then(d => d.items[0].n); })).catch(() => null);
  if (eo) { await page.evaluate(n => { location.hash = '#/bills/eo/' + n; }, eo); await page.waitForTimeout(3500);
    must((await page.$$('#app .bdacts [data-stance]')).length === 2, 'EO ' + eo + ' page has no thumbs');
    await (await btn('support')).click(); await page.waitForTimeout(800); must(await pressed('support'), 'EO 👍 did not turn on');
    t = await listTxt('#/bills/support'); must(/Support \(2\)/.test(t) && /executive orders/i.test(t) && t.includes('EO ' + eo), 'Support list has no EO ' + eo + ': ' + t.slice(0, 400)); }

  // reload as a new device (the app's local copies wiped): the account brings both back
  await page.reload({ waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2500);
  await page.evaluate(() => { document.documentElement.classList.remove('gated'); const g = document.getElementById('gate'); if (g) g.style.display = 'none'; });
  await signIn(true);
  t = await listTxt('#/bills/support'); must(t.includes(num) && (!eo || t.includes('EO ' + eo)), 'after reload on a "new device" the Support list lost items: ' + t.slice(0, 400));

  // switch the bill to 👎: it moves from Support to Against; tap 👎 again clears it
  await page.evaluate(x => { location.hash = x; }, '#/bill/' + encodeURIComponent(bid)); await page.waitForTimeout(3000);
  must(await pressed('support'), 'after reload the bill page 👍 is not lit');
  await (await btn('against')).click(); await page.waitForTimeout(800);
  must(await pressed('against') && !(await pressed('support')), '👎 did not replace 👍');
  must((await server())[bid].s === 'against', 'account doc not switched to against');
  must(!(await listTxt('#/bills/support')).includes(num), 'bill still under Support after 👎');
  must((await listTxt('#/bills/against')).includes(num), 'bill not under Against after 👎');
  await page.evaluate(x => { location.hash = x; }, '#/bill/' + encodeURIComponent(bid)); await page.waitForTimeout(2500);
  await (await btn('against')).click(); await page.waitForTimeout(800);
  must(!(await pressed('against')) && !(await server())[bid], 'tapping 👎 again did not clear it');
  t = await listTxt('#/bills/against'); must(!t.includes(num) && /nothing here yet/i.test(t), 'Against list not empty after clearing: ' + t.slice(0, 300));
  t = await listTxt('#/bills/tracked'); must(/Track/.test(t) && /Support/.test(t), 'Tracked sub-tab broke');
  return 'bill ' + bid + (eo ? ', EO ' + eo : '') + '; mock account doc writes: ' + await page.evaluate(() => window.__fsWrites);
});


// v59 (Shmuel, Nov 11 12:13 AM): 👍/👎 on the OUTSIDE of every bill and executive-order card (lists, search, Tracked/Support/Against),
// same saved state as the detail page; tapping a thumb never opens the bill; signed out shows the sign-in note; nothing overflows at 360/390px.
await test('v59: 👍/👎 on every bill and order card — saves without opening the bill, shares state with the page and the Support/Against tabs, fits at 360px', async () => {
  await newPage();
  const src0 = await page.evaluate(async (s) => fetch(s + 'stance.js?t=' + Date.now()).then(x => x.ok ? x.text() : '').catch(() => ''), SITE);
  if (!/KUS_STANCE/.test(src0)) return 'skipped: no stance.js';
  const signIn = async (wipeLocal) => {
    await page.waitForFunction(() => window.KUS_ACC && window.KUS_STANCE && KUS_ACC.trackedSnapshot && KUS_ACC.trackedSnapshot() !== null, null, { timeout: 30000 });
    await page.evaluate((wipe) => {
      const K = '__kus_fakefs', rd = () => { try { return JSON.parse(localStorage.getItem(K) || '{}'); } catch (e) { return {}; } }, wr = s => localStorage.setItem(K, JSON.stringify(s));
      if (wipe) Object.keys(localStorage).filter(k => /^kus_(prefs|profile_|pending_)/.test(k)).forEach(k => localStorage.removeItem(k));
      const setPath = (o, p, v) => { const ks = p.split('.'); let x = o; ks.slice(0, -1).forEach(k => { x = x[k] = x[k] || {}; }); if (v && v.__del) delete x[ks[ks.length - 1]]; else x[ks[ks.length - 1]] = v; };
      window.__fsWrites = 0;
      const FB = { doc: (db, c, id) => ({ c, id }), collection: (db, c) => ({ c }), serverTimestamp: () => new Date().toISOString(), deleteField: () => ({ __del: 1 }),
        getDoc: r => Promise.resolve((s => ({ exists: () => !!s, data: () => JSON.parse(JSON.stringify(s)) }))(rd()[r.c + '/' + r.id])),
        setDoc: (r, d) => { const s = rd(); s[r.c + '/' + r.id] = JSON.parse(JSON.stringify(d)); wr(s); window.__fsWrites++; return Promise.resolve(); },
        updateDoc: (r, d) => { const s = rd(), k = r.c + '/' + r.id; if (!s[k]) return Promise.reject(Object.assign(new Error('no doc'), { code: 'not-found' })); Object.keys(d).forEach(p => setPath(s[k], p, JSON.parse(JSON.stringify(d[p])))); wr(s); window.__fsWrites++; return Promise.resolve(); },
        deleteDoc: () => Promise.resolve() };
      const u = { uid: 'stance-test', email: 'stance-test@example.com', emailVerified: false, displayName: 'Test', reload: () => Promise.resolve(), getIdToken: () => Promise.resolve('x') };
      KUS_ACC._test.set({ user: u, FB, db: {}, storage: 'ok', profile: null });
      return KUS_ACC._test.loadProfile();
    }, !!wipeLocal);
    await page.waitForFunction(() => { const g = KUS_ACC._test.get(); return g.profile && g.storage === 'ok'; }, null, { timeout: 15000 });
  };

  const server = () => page.evaluate(() => { const s = JSON.parse(localStorage.getItem('__kus_fakefs') || '{}')['users/stance-test'] || {}; return (s.prefs && s.prefs.stance) || {}; });
  const fit = () => page.evaluate(() => { const out = []; const cards = [...document.querySelectorAll('#app .bill')].slice(0, 8);
    cards.forEach(c => { const cr = c.getBoundingClientRect(), cs = getComputedStyle(c), right = cr.right - parseFloat(cs.paddingRight) + 1;
      const row = c.querySelector('.strow'); if (!row) { out.push('no thumbs row: ' + (c.dataset.id || c.dataset.eo)); return; }
      const th = [...row.querySelectorAll('[data-stance]')]; if (th.length !== 2 || th[0].getAttribute('aria-label') !== 'Support' || th[1].getAttribute('aria-label') !== 'Against' || th.some(b => b.textContent.trim() || !b.querySelector('svg'))) out.push('thumbs not 2 icon-only labelled buttons');
      [...c.querySelectorAll('.bacts > *, .strow > *, .strow [data-stance]')].forEach(e => { const r = e.getBoundingClientRect(); if (r.right > right || r.left < cr.left) out.push('overflow ' + e.textContent.trim().slice(0, 20) + ' ' + Math.round(r.right) + '>' + Math.round(right)); });
      if (th.length === 2 && Math.abs(th[0].getBoundingClientRect().top - th[1].getBoundingClientRect().top) > 2) out.push('thumbs split over two lines');
      const ba = c.querySelector('.bacts'); if (ba && [...ba.children].some(e => Math.abs(e.getBoundingClientRect().top - ba.children[0].getBoundingClientRect().top) > 2)) out.push('Track/Details/Official wrapped'); });
    return { n: cards.length, bad: out.slice(0, 6) }; });
  const first = (sel) => page.evaluate((sel) => { const c = document.querySelector('#app ' + sel); return c && (c.dataset.id || ('EO-' + c.dataset.eo)); }, sel);
  const tap = async (id, k) => { await page.click('#app .bill [data-sid="' + id + '"][data-stance="' + k + '"]'); await page.waitForTimeout(700); };
  const pressedOn = (id, k, where) => page.evaluate(([id, k, where]) => { const b = document.querySelector('#app ' + where + ' [data-sid="' + id + '"][data-stance="' + k + '"]'); return b ? b.getAttribute('aria-pressed') === 'true' : null; }, [id, k, where]);
  // Bills list at this width, signed out
  await go('#/bills', 3500);
  let f = await fit(); must(f.n >= 3 && !f.bad.length, 'Bills list cards: ' + JSON.stringify(f));
  const bid = await first('article.bill'); must(bid, 'no bill card');
  if (!(await page.evaluate(() => KUS_ACC.signedIn()))) { const h0 = await page.evaluate(() => location.hash); await tap(bid, 'support');
    must((await page.evaluate(() => location.hash)) === h0, 'tapping 👍 on a card opened the bill');
    const note = await page.evaluate((id) => { const c = document.querySelector('#app article.bill[data-id="' + id + '"]'); const n = c && c.querySelector('.needsin'); return n ? n.innerText : null; }, bid);
    must(note && /sign in to save support and against/i.test(note), 'signed out: no sign-in note on the card: ' + note);
    must(!(await pressedOn(bid, 'support', 'article.bill')), 'signed out: 👍 lit up'); }
  // signed in: 👍 on the card saves, stays on the list, shows on the detail page and in Support
  await signIn(true); await page.waitForTimeout(1200);
  const h1 = await page.evaluate(() => location.hash); await tap(bid, 'support');
  must((await page.evaluate(() => location.hash)) === h1, 'signed in: tapping 👍 on a card opened the bill');
  must(await pressedOn(bid, 'support', 'article.bill'), 'card 👍 did not turn on');
  must((await server())[bid] && (await server())[bid].s === 'support', 'card 👍 was not saved to the account: ' + JSON.stringify(await server()));
  await page.evaluate((id) => { location.hash = '#/bill/' + encodeURIComponent(id); }, bid); await page.waitForTimeout(3500);
  must(await pressedOn(bid, 'support', '.bdacts'), 'detail page does not show the 👍 set on the card');
  await page.click('#app .bdacts [data-stance="against"]'); await page.waitForTimeout(800);
  await page.evaluate(() => { location.hash = '#/bills/against'; }); await page.waitForTimeout(3000);
  must(await pressedOn(bid, 'against', 'article.bill'), 'Against tab card does not show 👎 set on the page');
  must(!(await pressedOn(bid, 'support', 'article.bill')), 'Against tab card still shows 👍');
  f = await fit(); must(!f.bad.length, 'Against tab cards: ' + JSON.stringify(f));
  await tap(bid, 'against'); await page.waitForTimeout(1500);
  must(!(await server())[bid], 'tapping the lit 👎 on the Against card did not clear it');
  must(!(await page.$('#app article.bill[data-id="' + bid + '"]')), 'cleared bill still listed under Against');
  // Tracked tab: thumbs share the Notify row
  await page.evaluate(() => { location.hash = '#/bills/passed'; }); await page.waitForTimeout(3000);
  const tid = await first('article.bill'); if (tid) { await page.click('#app article.bill[data-id="' + tid + '"] [data-track]'); await page.waitForTimeout(800);
    await page.evaluate(() => { location.hash = '#/bills/tracked'; }); await page.waitForTimeout(3000);
    const nr = await page.evaluate((id) => { const c = document.querySelector('#app article.bill[data-id="' + id + '"]'); return c ? !!c.querySelector('.strow .notify') && c.querySelectorAll('.strow [data-stance]').length === 2 : null; }, tid);
    must(nr, 'Tracked card: thumbs not on the Notify row'); f = await fit(); must(!f.bad.length, 'Tracked cards: ' + JSON.stringify(f)); }
  // executive orders list
  await page.evaluate(() => { location.hash = '#/bills/eo'; }); await page.waitForTimeout(4000);
  f = await fit(); must(f.n >= 3 && !f.bad.length, 'EO list cards: ' + JSON.stringify(f));
  const eid = await first('.eocard'); const h2 = await page.evaluate(() => location.hash); await tap(eid, 'support');
  must((await page.evaluate(() => location.hash)) === h2, 'tapping 👍 on an order card opened the order');
  must((await server())[eid] && (await server())[eid].s === 'support' && (await server())[eid].j === 'EO', 'order card 👍 not saved: ' + JSON.stringify((await server())[eid]));
  await page.evaluate(() => { location.hash = '#/bills/support'; }); await page.waitForTimeout(3500);
  must(await pressedOn(eid, 'support', '.eocard'), 'Support tab: order card missing or not lit');
  // 360px
  await page.setViewportSize({ width: 360, height: 780 });
  for (const h of ['#/bills', '#/bills/eo', '#/bills/tracked', '#/bills/support']) { await page.evaluate(x => { location.hash = x; }, h); await page.waitForTimeout(2500); f = await fit(); must(!f.bad.length, '360px ' + h + ': ' + JSON.stringify(f)); }
  await page.evaluate(() => { location.hash = '#/bills'; }); await page.waitForTimeout(2000); await shot42('v59-card-thumbs-360');
  await page.setViewportSize({ width: W, height: 844 });
  return 'bill ' + bid + ' and ' + eid + ' set from their cards; detail page / Against tab share it; 360px fits';
});

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
