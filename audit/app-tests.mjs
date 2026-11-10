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
await test('v42: Report form fills the page, validates, falls back to email when Firestore fails', async () => {
  await page.route(/firestore\.googleapis\.com/, r => r.abort());
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
  must(href.startsWith('mailto:knowus-qa@mail.tab.bot?') && decodeURIComponent(href).includes('Test report from app-tests'), 'mailto fallback wrong: ' + href.slice(0, 120));
  await shot42('v42-report-fallback');
  await page.unroute(/firestore\.googleapis\.com/);
});
await test('v42: Report form sends {text,page,ua,w,h,app} through KUS_ACC.report', async () => {
  await go('#/report?page=' + encodeURIComponent('#/voter/ballot'), 2000);
  await page.evaluate(() => { window.__rep = null; window.KUS_ACC.report = d => { window.__rep = d; return Promise.resolve(); }; });
  await page.fill('#reptext', 'Ballot is missing a judge');
  await page.click('#repsend'); await page.waitForTimeout(600);
  const d = await page.evaluate(() => window.__rep);
  must(d && d.text === 'Ballot is missing a judge' && d.page === '#/voter/ballot', 'wrong doc: ' + JSON.stringify(d));
  must(d.ua && d.w > 0 && d.h > 0 && /web/.test(d.app) && /Android app 1\.3/.test(d.app), 'device info missing: ' + JSON.stringify(d));
  must(/report was sent/i.test(await text()), 'no thank-you after a good send');
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

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
