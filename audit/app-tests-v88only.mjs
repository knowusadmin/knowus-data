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
await test('v88: Miami-Dade municipal run-offs — an address inside the official town boundary gets that town\'s run-off ballot (its own date, separate from Nov 3, contests as printed); just outside gets none; the Nov 3 ballot is unchanged', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  // [Census-matched address, x, y, run-offs expected (day:town)] — boundaries from Miami-Dade County GIS Municipal Boundary
  const A = [["12645 S DIXIE HWY, PINECREST, FL, 33156", -80.329897356774, 25.652827131922, { '2026-11-17': 'Pinecrest' }],
    ["11000 S RED RD, PINECREST, FL, 33156", -80.284173418132, 25.668460977578, { '2026-11-17': 'Pinecrest' }],
    ["7900 SW 120TH ST, PINECREST, FL, 33156", -80.322438022076, 25.659049713404, { '2026-11-17': 'Pinecrest' }],
    ["7535 N KENDALL DR, MIAMI, FL, 33156", -80.312653049889, 25.688792184579, {}],
    ["12645 SW 57TH AVE, PINECREST, FL, 33156", -80.284071104389, 25.655028356788, {}],
    ["8000 SW 136TH ST, PALMETTO BAY, FL, 33158", -80.324062536192, 25.644057621027, { '2026-12-01': 'Palmetto Bay' }],
    ["10720 CARIBBEAN BLVD, CUTLER BAY, FL, 33189", -80.36568456197, 25.577415531916, { '2026-12-01': 'Cutler Bay' }],
    ["16901 NE 19TH AVE, NORTH MIAMI BEACH, FL, 33162", -80.162153437874, 25.931201326228, { '2026-12-01': 'North Miami Beach' }],
    ["9705 E HIBISCUS ST, PALMETTO BAY, FL, 33157", -80.348465556378, 25.603264654007, { '2026-12-01': 'Palmetto Bay' }]];
  const WANT = { Pinecrest: [['Councilmember - Seat 4', ['Ken Fairman', 'Jill Lerner']]],
    'Cutler Bay': [['Mayor', ['Robert "B.J." Duncan', 'Suzy Lord']], ['Residential Area Council Member - Seat 1', ['Ricky Fernandez', 'Mary Ann Mixon']]],
    'North Miami Beach': [['Group 2 - Commissioner', ['Jay R. Chernoff', 'Jasmine Rivera']], ['Group 4 - Commissioner', ['Linda Joseph', 'Dayanara Torres']]],
    'Palmetto Bay': [['Mayor', ['Karen Baez-Wallis', 'Tamara Mourino']], ['Councilmember - Seat 3', ['Lasaly Changkachith', "Alan ''AlJohn'' Farquharson"]]] };
  const r = await page.evaluate(async ([A, WANT]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const bad = [], seen = []; const today = (window.KUS_ELECTIONS && KUS_ELECTIONS.today) ? KUS_ELECTIONS.today() : new Date().toISOString().slice(0, 10);
    const sig = g => g ? g.day + '|' + g.kind + '|' + g.contests.map(c => c.office + ':' + (c.candidates || []).map(x => x.name).join(',')).join(';') : 'none';
    let nov3 = null;
    for (const [a, x, y, exp] of A) {
      const vr = { state: 'FL', county: ['Miami-Dade County'], place: [], townsub: [], x, y, matched: a };
      await K._prepFull(vr); const sp = K._spBallots(vr), all = K._assemble(vr, []), g = K._gen26(vr);
      // Nov 3 unchanged: same Nov 3 ballot inside and outside every town, no municipal contest in it
      if (!g || g.day !== '2026-11-03') bad.push(a + ': no Nov 3 ballot'); else { if (nov3 === null) nov3 = sig(g); else if (sig(g) !== nov3) bad.push(a + ': Nov 3 ballot differs'); if (g.contests.some(c => /Council|Commissioner|Mayor/.test(c.office))) bad.push(a + ': run-off contest inside the Nov 3 ballot'); }
      const until = d => { const t = new Date(d + 'T12:00:00'); t.setDate(t.getDate() + 7); return t.toISOString().slice(0, 10); };
      const live = Object.keys(exp).filter(d => today <= until(d));
      if (sp.length !== live.length) bad.push(a + ': ' + sp.length + ' run-off ballots, want ' + live.length);
      for (const b of sp) {
        const town = exp[b.day]; if (!town) { bad.push(a + ': unexpected ' + b.day + ' ' + b.town); continue; }
        if (b.town !== town) bad.push(a + ': town ' + b.town + ' want ' + town);
        if (!K._isVerified(b)) bad.push(a + ': ' + town + ' not verified');
        if (!/Nov 17, 2026|Dec 1, 2026/.test(b.label) || b.id === 'kus-2026-11-03') bad.push(a + ': label/id ' + b.label + ' ' + b.id);
        if (!all.some(z => z.id === b.id) || !all.some(z => z.id === 'kus-2026-11-03')) bad.push(a + ': not shown as a separate ballot beside Nov 3');
        const w = WANT[town]; if (b.contests.length !== w.length) bad.push(a + ': contests ' + b.contests.length);
        w.forEach(([t, cs], i) => { const c = b.contests[i]; if (!c || c.office !== t || c.voteFor !== '1' || c.candidates.map(x => x.name).join('|') !== cs.join('|')) bad.push(a + ': contest ' + i + ' ' + (c && c.office)); });
        if (!/miamidade\.gov\/elections\/library\/sample-ballots\/.*run-off-sample-ballot\.pdf$/.test(b.fullLink && b.fullLink.url || '')) bad.push(a + ': no official PDF link');
        seen.push(a.split(',')[0] + ' → ' + town + ' ' + b.day + ' (' + b.contests.length + ')');
      }
      if (!sp.length) seen.push(a.split(',')[0] + ' → none');
    }
    return { bad, seen };
  }, [A, WANT]);
  must(!r.bad.length, r.bad.slice(0, 4).join(' | '));
  // the page itself: a saved Pinecrest address shows the run-off card with its date and town, and the Nov 3 card under it
  const lk = await page.evaluate(async q => { const r = await window.KUS_VOTER.lookup(q); return r ? { m: r.matched, c: r.county, x: r.x, y: r.y } : null; }, '12645 S Dixie Hwy, Pinecrest, FL 33156');
  must(lk && /DADE/i.test(String(lk.c)), 'address lookup: ' + JSON.stringify(lk));
  await go('#/voter', 2500); await go('#/voter/ballot', 7000);
  const cards = await page.evaluate(() => [...document.querySelectorAll('#app section.bal')].map(s => s.innerText.replace(/\s+/g, ' ').slice(0, 400)));
  const t0 = new Date().toISOString().slice(0, 10);
  if (t0 <= '2026-11-24') { must(cards.length >= 2 && /Pinecrest run-off election/.test(cards[0]) && /November 17, 2026/.test(cards[0]) && /Your town: Pinecrest/.test(cards[0]), 'run-off card: ' + (cards[0] || 'none').slice(0, 160) + ' / ' + (await page.evaluate(() => (document.getElementById('app') || document.body).innerText.replace(/\s+/g, ' ').slice(0, 300))));
    must(cards.some(c => /November 3, 2026/.test(c) && !/Pinecrest run-off/.test(c)), 'Nov 3 card missing or mixed'); }
  must(page.__errs.length === 0, 'page errors: ' + page.__errs.slice(0, 2).join(' | '));
  return 'lookup ' + lk.m + ' · ' + r.seen.join(' · ') + ' · page: ' + cards.length + ' cards';
});
await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
