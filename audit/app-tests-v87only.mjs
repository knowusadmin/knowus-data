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

// KUS-SPONSORS (Shmuel, Nov 12 2026): every federal bill's sponsor (and cosponsors) taps through to a full profile.
// N random bills: the Details "Sponsor" row is a link whenever sponsor-ids.json resolves the sponsor to a page; the link
// opens a person page with a name, a photo or initials, and terms; Back returns to the bill.
await newPage();
await test('Bill sponsor links: random federal bills -> person page with name, photo, terms; Back returns to the bill', async () => {
  await go('#/bills', 3000);
  const pick = await page.evaluate(async () => {
    const j = await (await fetch('data/bills/US.json')).json(); const m = await (await fetch('data/bills/sponsor-ids.json')).json();
    const ok = (bg) => { const p = m.people[bg] || {}; return !!(p.a ? window.KUS_P(p.a) : (window.KUS_P(bg) || p.x)); };
    if (window.KUS_PX) await window.KUS_PX();
    const all = j.bills.filter(b => b.sponsor).map(b => ({ id: b.id, bg: b.sponsorId || m.ids['F:' + b.sponsor] })).filter(b => b.bg);
    const res = all.filter(b => ok(b.bg)); const sh = res.sort(() => Math.random() - .5);
    const x = Object.keys(m.people).filter(bg => m.people[bg].x || m.people[bg].a);
    const ex = all.filter(b => x.indexOf(b.bg) >= 0).sort(() => Math.random() - .5).slice(0, 3);
    return { n: all.length, linkable: res.length, ids: sh.slice(0, 8).concat(ex) };
  });
  must(pick.n > 100 && pick.linkable / pick.n > 0.95, 'too few federal bills resolve to a page: ' + pick.linkable + '/' + pick.n);
  const seen = [];
  for (const b of pick.ids) {
    await page.evaluate(id => { location.hash = '#/bill/' + encodeURIComponent(id); }, b.id); await page.waitForTimeout(2500);
    const a = await page.$('#app .bdfacts a.splink');
    must(a, b.id + ': Sponsor is not a link');
    const label = (await a.textContent()).trim(); must(!/,(?!\s*(Jr|Sr|II|III|IV|V)\.?$)/.test(label), b.id + ': sponsor name not flipped: ' + label);
    const y = await page.evaluate(() => { window.scrollTo(0, 400); return window.scrollY; });
    await a.click(); await page.waitForTimeout(2500);
    const h = await page.evaluate(() => location.hash); must(/^#\/p\//.test(h), b.id + ': sponsor link opened ' + h);
    const info = await page.evaluate(() => ({ n: (document.querySelector('#app .hero h1') || {}).textContent || '', ph: !!document.querySelector('#app .hero img, #app .hero .ini') }));
    must(info.n.trim(), b.id + ': person page has no name'); must(info.ph, b.id + ': person page has no photo or initials');
    await page.click('#app .ptabs a:has-text("In office")'); await page.waitForTimeout(2000);
    const ot = await text(); must(/in office since|term|in congress/i.test(ot), b.id + ': In office tab shows no terms (' + info.n + ')');
    let h2 = '', k = 0; for (; k < 3; k++) { await page.click('#back'); await page.waitForTimeout(1800); h2 = await page.evaluate(() => location.hash); if (/^#\/bill\//.test(h2)) break; }
    must(h2 === '#/bill/' + encodeURIComponent(b.id) || h2 === '#/bill/' + b.id, b.id + ': Back went to ' + h2);
    seen.push(info.n.trim());
  }
  // one cosponsor link
  await page.evaluate(id => { location.hash = '#/bill/' + encodeURIComponent(id); }, pick.ids[0].id); await page.waitForTimeout(2500);
  const c = await page.$('#app ul.cos a.splink'); if (c) { await c.click(); await page.waitForTimeout(2000); must(/^#\/p\//.test(await page.evaluate(() => location.hash)), 'cosponsor link did not open a person page'); }
  // bill list card: sponsor shown as a link
  await go('#/bills', 3500);
  const cl = await page.$$eval('#app article.bill .bspon a.splink', x => x.length); must(cl > 0, 'bill list cards: no sponsor links');
  return pick.linkable + '/' + pick.n + ' federal bills link their sponsor; checked ' + seen.join(', ');
});

// KUS-SPONSORS 2: built profiles for sponsors with no other page (delegates + former members, data/people-extra.json):
// each opens from a bill's Sponsor link with name, photo, "In Congress" terms, and a Positions tab carrying the AI label.
await newPage();
await test('Built sponsor profiles (delegates, former members): name, photo, In Congress terms, Positions with AI label; Back returns to the bill', async () => {
  await go('#/bills', 3000);
  const pick = await page.evaluate(async () => {
    const j = await (await fetch('data/bills/US.json')).json(); const m = await (await fetch('data/bills/sponsor-ids.json')).json();
    const by = {}; j.bills.filter(b => b.sponsor).forEach(b => { const bg = b.sponsorId || m.ids['F:' + b.sponsor]; if (bg && m.people[bg] && m.people[bg].x && !by[bg]) by[bg] = b.id; });
    return Object.keys(by).sort(() => Math.random() - .5).slice(0, 6).map(bg => ({ bg, id: by[bg] }));
  });
  must(pick.length >= 3, 'too few bills by built-profile sponsors: ' + pick.length);
  const seen = [];
  for (const b of pick) {
    await page.evaluate(id => { location.hash = '#/bill/' + encodeURIComponent(id); }, b.id); await page.waitForTimeout(2500);
    const a = await page.$('#app .bdfacts a.splink'); must(a, b.id + ': Sponsor is not a link');
    await a.click(); await page.waitForTimeout(2500);
    const h = await page.evaluate(() => location.hash); must(h === '#/p/' + b.bg, b.id + ': sponsor link opened ' + h);
    const info = await page.evaluate(() => ({ n: ((document.querySelector('#app .hero h1') || {}).textContent || '').trim(), img: !!document.querySelector('#app .hero img'), ini: !!document.querySelector('#app .hero .ini') }));
    must(info.n, b.bg + ': no name'); must(info.img || info.ini, b.bg + ': no photo or initials');
    await page.click('#app .ptabs a:has-text("In office")'); await page.waitForTimeout(2000);
    must(/in congress/i.test(await text()), b.bg + ': In office tab has no In Congress terms');
    await page.click('#app .ptabs a:has-text("Positions")'); await page.waitForTimeout(2500);
    const pt = await text(); must(/Written by AI from public sources/i.test(pt), b.bg + ': Positions tab missing the AI label');
    let h2 = '', k = 0; for (; k < 4; k++) { await page.click('#back'); await page.waitForTimeout(1800); h2 = await page.evaluate(() => location.hash); if (/^#\/bill\//.test(h2)) break; }
    must(h2 === '#/bill/' + encodeURIComponent(b.id) || h2 === '#/bill/' + b.id, b.bg + ': Back went to ' + h2);
    seen.push(info.n + (info.img ? '' : ' (initials)'));
  }
  return 'checked ' + seen.join(', ');
});

// KUS-SPONSORS 3: state bills — the sponsor taps through to the state legislator's page (Open States person id),
// with name, photo or initials, "In the legislature" on In office, the bill itself on Positions; Back returns to the bill.
await newPage();
await test('State bill sponsors: random state bills -> legislator page (name, photo, In the legislature, bill listed on Positions); Back returns to the bill', async () => {
  await go('#/bills', 3000);
  const pick = await page.evaluate(async () => {
    const meta = await (await fetch('data/bills/state-sponsors/meta.json')).json().catch(() => null);
    const sts = ['CA', 'TX', 'NY', 'FL', 'PA', 'IL', 'OH', 'WY', 'MA', 'WA', 'GA', 'MI'];
    const out = []; let n = 0, linked = 0;
    for (const st of sts) {
      const m = await (await fetch('data/bills/state-sponsors/' + st + '.json')).json().catch(() => null); if (!m) continue;
      const l = await (await fetch('data/bills/' + st + '.json')).json();
      const have = l.bills.filter(b => b.sponsor); n += have.length;
      const ok = have.filter(b => m.bills[b.id] && m.bills[b.id].s && m.people[m.bills[b.id].s]); linked += ok.length;
      if (ok.length) { const b = ok[Math.floor(Math.random() * ok.length)]; const e = m.bills[b.id]; out.push({ id: b.id, st, u: e.s, ok: [e.s, e.f].concat(Object.values(e.p || {}), Object.values(e.c || {})).filter(Boolean) }); }
    }
    return { n, linked, ids: out.sort(() => Math.random() - .5).slice(0, 8) };
  });
  must(pick.ids.length >= 6 && pick.linked / pick.n > 0.6, 'too few state bills resolve to a legislator: ' + pick.linked + '/' + pick.n);
  const seen = [];
  for (const b of pick.ids) {
    await page.evaluate(id => { location.hash = '#/bill/' + encodeURIComponent(id); }, b.id); await page.waitForTimeout(2500);
    const a = await page.$('#app .bdfacts a.splink'); must(a, b.id + ': Sponsor is not a link');
    await a.click(); await page.waitForTimeout(2500);
    const h = decodeURIComponent(await page.evaluate(() => location.hash)); must(b.ok.some(x => h === '#/p/sl-' + b.st + '-' + x), b.id + ': sponsor link opened ' + h);
    const info = await page.evaluate(() => ({ n: ((document.querySelector('#app .hero h1') || {}).textContent || '').trim(), ph: !!document.querySelector('#app .hero img, #app .hero .ini') }));
    must(info.n, b.id + ': no name'); must(info.ph, b.id + ': no photo or initials');
    await page.click('#app .ptabs a:has-text("In office")'); await page.waitForTimeout(1500);
    must(/In the legislature/i.test(await text()), b.id + ': In office has no legislature box (' + info.n + ')');
    await page.click('#app .ptabs a:has-text("Positions")'); await page.waitForTimeout(2500);
    const hasBill = await page.evaluate(id => !!document.querySelector('#app a[href="#/bill/' + encodeURIComponent(id) + '"]'), b.id);
    must(/Bills sponsored/i.test(await text()) && hasBill, b.id + ': Positions does not list the bill (' + info.n + ')');
    let h2 = '', k = 0; for (; k < 4; k++) { await page.click('#back'); await page.waitForTimeout(1800); h2 = await page.evaluate(() => location.hash); if (/^#\/bill\//.test(h2)) break; }
    must(decodeURIComponent(h2) === '#/bill/' + b.id, b.id + ': Back went to ' + h2);
    seen.push(info.n + ' (' + b.st + ')');
  }
  must(page.__errs.length === 0, 'page errors: ' + page.__errs.slice(0, 2).join(' | '));
  return pick.linked + '/' + pick.n + ' sampled state bills link their sponsor; checked ' + seen.join(', ');
});

// KUS-SPONSORS 4: a state legislator's Positions lists their roll-call votes on KnowUS bills (Open States person IDs), count = data file.
await test('State legislator votes: Positions shows Recorded votes matching the data file, each tapping to its bill', async () => {
  const seen = [];
  for (const st of ['VA', 'WA', 'NY', 'TX', 'WY']) {
    const ps = await page.evaluate(async st => { const j = await (await fetch('data/people-state/' + st + '.json')).json(); return Object.keys(j.people); }, st);
    let got = null;
    for (const u of ps.sort(() => Math.random() - .5).slice(0, 12)) {
      const n = await page.evaluate(async a => { const r = await fetch('data/people-state-votes/' + a[0] + '/' + a[1] + '.json'); if (!r.ok) return 0; return ((await r.json()).v || []).length; }, [st, u]);
      if (n) { got = { u, n }; break; }
    }
    if (!got) continue;
    await page.evaluate(h => { location.hash = h; }, '#/p/sl-' + st + '-' + got.u + '/positions'); await page.waitForTimeout(3000);
    const t = await text(); const m = /Recorded votes\s*\((\d+)\)/i.exec(t);
    must(m && +m[1] === got.n, st + ': Recorded votes count ' + (m && m[1]) + ' vs file ' + got.n);
    const a = await page.$('#app ul.slvotes a[href^="#/bill/"]'); must(a, st + ': no vote links to a bill');
    await a.click(); await page.waitForTimeout(2500); must(/^#\/bill\//.test(await page.evaluate(() => location.hash)), st + ': vote link did not open a bill');
    seen.push(st + ' ' + got.n);
  }
  must(seen.length >= 3, 'too few legislators with votes: ' + seen.join(', '));
  must(page.__errs.length === 0, 'page errors: ' + page.__errs.slice(0, 2).join(' | '));
  return 'checked ' + seen.join(', ');
});
// v87: the header Back arrow restores the spot even when the previous in-tab page is not the previous history entry (profile Overview → Positions, then Back to the bill)
await newPage();
await test('v87: header Back after a profile sub-tab (Overview → Positions) returns to the bill at the same spot', async () => {
  const out = [];
  for (const id of ['US-119-HR9815', 'WY-2026-SF101']) {
    await go('#/bill/' + id, 3500);
    const sel = '#app .bdfacts a[href^="#/p/"]'; const a = await page.$(sel); must(a, id + ': Sponsor is not a link');
    const href = await a.getAttribute('href');
    await page.evaluate(s => document.querySelector(s).scrollIntoView({ block: 'center' }), sel); await page.waitForTimeout(400);
    const y0 = await page.evaluate(() => window.scrollY);
    await a.click(); await page.waitForTimeout(2500);
    await page.evaluate(h => { location.hash = h; }, href + '/positions'); await page.waitForTimeout(2500);
    await page.click('#back'); await page.waitForTimeout(3000);
    const h = await page.evaluate(() => location.hash); must(h === '#/bill/' + id, id + ': Back went to ' + h);
    const y1 = await page.evaluate(() => window.scrollY); must(Math.abs(y1 - y0) <= 40, id + ': not at the same spot: ' + y1 + ' vs ' + y0);
    await page.goBack(); await page.waitForTimeout(2500);
    out.push(id + ' y ' + y0 + '→' + y1);
  }
  must(page.__errs.length === 0, 'page errors: ' + page.__errs.slice(0, 2).join(' | '));
  return out.join(' · ');
});


await newPage();
await test('v86 live: sponsor link → profile → Back returns to the bill at the same spot (delegate, former member, Graham, 3 random)', async () => {
  const IDS = ["US-119-HR9815", "US-119-HR3490", "US-119-S4671", "US-119-S4618", "US-119-S4661", "US-119-HR10939"]; const out = [];
  for (const id of IDS) {
    await go('#/bill/' + id, 3500);
    const a = await page.$('#app .bdfacts a.splink'); must(a, id + ': Sponsor is not a link');
    const label = (await a.textContent()).trim(); const href = await a.getAttribute('href');
    await page.evaluate(() => { const l = document.querySelector('#app .bdfacts a.splink'); l.scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(400);
    const y0 = await page.evaluate(() => window.scrollY);
    await a.click(); await page.waitForTimeout(3000);
    must(await page.evaluate(() => location.hash) === href, id + ': link went to ' + await page.evaluate(() => location.hash));
    const t = await text(); const last = label.replace(/,.*$/, '').trim().split(/\s+/).pop();
    must(t.indexOf(last) >= 0, id + ': profile does not show ' + label);
    const img = await page.evaluate(() => { const i = document.querySelector('#app .hero img'); return i ? (i.complete && i.naturalWidth > 0) : null; });
    await page.click('#back'); await page.waitForTimeout(3000);
    const h = await page.evaluate(() => location.hash); must(h === '#/bill/' + id, id + ': Back went to ' + h);
    const y1 = await page.evaluate(() => window.scrollY); must(Math.abs(y1 - y0) <= 40, id + ': Back did not return to the same spot: scrollY ' + y1 + ' vs ' + y0);
    out.push(id + ' ' + label + (img ? ' (photo)' : img === null ? ' (initials)' : ' (photo not loaded)') + ' y ' + y0 + '→' + y1);
  }
  const wide = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1); must(wide, 'horizontal overflow');
  return out.join(' · ');
});


await newPage();
await test('v87 live: state-bill sponsor → state legislator page → Back returns to the bill at the same spot (WY SF101, CA, TX, NY, OH)', async () => {
  const IDS = ["WY-2026-SF101", "CA-2025-SB503", "CA-2025-SB1365", "TX-2025892-SR80", "TX-2025892-SR55", "NY-2025-A7366", "NY-2025-S9890", "OH-2025-SB482", "OH-2025-SB276"]; const out = [];
  for (const id of IDS) {
    await go('#/bill/' + id, 3500);
    const a = await page.$('#app .bdfacts a[href^="#/p/"]'); must(a, id + ': Sponsor is not a link');
    const label = (await a.textContent()).trim(); const href = await a.getAttribute('href');
    await page.evaluate(() => { const l = document.querySelector('#app .bdfacts a[href^="#/p/"]'); l.scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(400);
    const y0 = await page.evaluate(() => window.scrollY);
    await a.click(); await page.waitForTimeout(3000);
    must(await page.evaluate(() => location.hash) === href, id + ': link went to ' + await page.evaluate(() => location.hash));
    const t = await text(); const last = label.replace(/,.*$/, '').trim().split(/\s+/).pop();
    must(t.indexOf(last) >= 0, id + ': profile does not show ' + label);
    const img = await page.evaluate(() => { const i = document.querySelector('#app .hero img'); return i ? (i.complete && i.naturalWidth > 0) : null; });
    await page.click('#back'); await page.waitForTimeout(3000);
    const h = await page.evaluate(() => location.hash); must(h === '#/bill/' + id, id + ': Back went to ' + h);
    const y1 = await page.evaluate(() => window.scrollY); must(Math.abs(y1 - y0) <= 40, id + ': Back did not return to the same spot: scrollY ' + y1 + ' vs ' + y0);
    out.push(id + ' ' + label + (img ? ' (photo)' : img === null ? ' (initials)' : ' (photo not loaded)') + ' y ' + y0 + '→' + y1);
  }
  const wide = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1); must(wide, 'horizontal overflow');
  return out.join(' · ');
});


await newPage();
await test('v87 live: state-bill sponsor → profile → Positions "Recorded votes (N)" → tap a vote opens that bill → Back returns to the votes, Back again to the first bill (CA, TX, NY, OH)', async () => {
  const IDS = [["CA-2025-AB1539", 151], ["TX-2025892-SB11", 50], ["NY-2025-S10722", 58], ["OH-2025-HB455", 41]]; const out = [];
  for (const [id, n] of IDS) {
    await go('#/bill/' + id, 3500);
    const a = await page.$('#app .bdfacts a[href^="#/p/sl-"]'); must(a, id + ': Sponsor is not a state legislator link');
    const label = (await a.textContent()).trim(); const href = await a.getAttribute('href');
    await page.evaluate(() => { document.querySelector('#app .bdfacts a[href^="#/p/sl-"]').scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(400);
    const y0 = await page.evaluate(() => window.scrollY);
    await a.click(); await page.waitForTimeout(3000);
    must(await page.evaluate(() => location.hash) === href, id + ': sponsor link went to ' + await page.evaluate(() => location.hash));
    const pt = await page.$('#app a[href="' + href + '/positions"]');
    if (pt) { await pt.click(); } else { await page.evaluate(h => { location.hash = h; }, href + '/positions'); }
    await page.waitForTimeout(3000);
    const t = await text(); const m = /Recorded votes\s*\((\d+)\)/i.exec(t);
    must(m && +m[1] === n, id + ': Recorded votes ' + (m && m[1]) + ' vs data ' + n);
    const v = await page.$('#app ul.slvotes a[href^="#/bill/"]'); must(v, id + ': no vote links to a bill');
    const vh = await v.getAttribute('href');
    await page.evaluate(() => { document.querySelector('#app ul.slvotes a[href^="#/bill/"]').scrollIntoView({ block: 'center' }); }); await page.waitForTimeout(400);
    const pY = await page.evaluate(() => window.scrollY); const pH = await page.evaluate(() => location.hash);
    await v.click(); await page.waitForTimeout(3000);
    must(await page.evaluate(() => location.hash) === vh, id + ': vote link went to ' + await page.evaluate(() => location.hash));
    must(/Sponsor|Status|Details/.test(await text()), id + ': voted bill page did not render');
    await page.click('#back'); await page.waitForTimeout(3000);
    const h1 = await page.evaluate(() => location.hash); must(h1 === pH, id + ': Back from the voted bill went to ' + h1 + ' not ' + pH);
    const y1 = await page.evaluate(() => window.scrollY); must(Math.abs(y1 - pY) <= 40, id + ': votes list not at same spot ' + y1 + ' vs ' + pY);
    let h2 = h1, presses = 0;
    while (h2 !== '#/bill/' + id && presses < 3) { await page.click('#back'); await page.waitForTimeout(2500); presses++; h2 = await page.evaluate(() => location.hash); }
    must(h2 === '#/bill/' + id, id + ': Back did not return to the first bill, at ' + h2);
    const y2 = await page.evaluate(() => window.scrollY); must(Math.abs(y2 - y0) <= 40, id + ': first bill not at same spot ' + y2 + ' vs ' + y0);
    out.push(id + ' ' + label + ' votes ' + m[1] + ' → ' + vh.slice(7) + ' → Back votes y ' + pY + '→' + y1 + ' → Back×' + presses + ' bill y ' + y0 + '→' + y2);
  }
  must(page.__errs.length === 0, 'page errors: ' + page.__errs.slice(0, 2).join(' | '));
  return out.join(' · ');
});

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
