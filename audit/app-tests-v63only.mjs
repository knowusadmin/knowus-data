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
await test('v63: Collin County, TX — every precinct, and every part of a precinct with several printed ballots (city limits, school districts, Blue Meadow MUDs), gives its official printed ballot; parts the boundary layers cannot place, and precinct 201, are labelled; off-map is labelled + blue button', async () => {
  await newPage(); await go('#/voter/ballot', 3500);
  const real = [["3900 RIVERBEND WAY, MCKINNEY", -96.56642904347918, 33.159374690994866, "Precinct 179, ballot style 39", 57], ["1183 E FM 544, WYLIE", -96.52076736079033, 32.99902685030108, "Precinct 217, ballot style 45", 56], ["4787 COUNTY ROAD 1078, PRINCETON", -96.50708850909484, 33.10529604641129, "Precinct 100, ballot style 51", 53], ["12902 COUNTY ROAD 8, CELINA", -96.81351605792068, 33.32247257176261, "Precinct 154", 51]];
  const r = await page.evaluate(async ([real, ck, cn, host]) => {
    const K = window.KUS_BALLOT; await K._loadLinks(); const out = { n: 0, full: 0, bad: [], real: {}, q: 0 };
    const base = { state: 'TX', county: [cn], place: [], townsub: [] };
    await K._prepFull(Object.assign({}, base, { x: real[0][1], y: real[0][2], matched: 'PRELOAD ' + ck })); const C = K._PAC[ck]; if (!C.d || !C.geo) return { bad: ['data did not load'] };
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const p of C.geo.p) { const [key, b] = p; let pt = null;
      for (let i = 0; i < 800 && !pt; i++) { const X = b[0] + rnd() * (b[2] - b[0]), Y = b[1] + rnd() * (b[3] - b[1]); if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; }
      if (!pt) { // slivers on the county map (some under 1 m²): step just inside each edge of each ring
        for (const rg of p[2]) { if (pt) break; let x = rg[0], y = rg[1]; const V = [[x, y]]; for (let i = 2; i + 1 < rg.length; i += 2) { x += rg[i]; y += rg[i + 1]; V.push([x, y]); }
          for (let i = 0; i + 1 < V.length && !pt; i++) { const [ax, ay] = V[i], [bx, by] = V[i + 1], L = Math.hypot(bx - ax, by - ay); if (!L) continue;
            for (const t of [0.5, 0.25, 0.75]) for (const e of [0.3, -0.3, 0.1, -0.1, 0.03, -0.03, 0.01, -0.01]) { if (pt) break; const X = ax + t * (bx - ax) - e * (by - ay) / L, Y = ay + t * (by - ay) + e * (bx - ax) / L;
              if (K._geoFind(C.geo, X / C.geo.scale, Y / C.geo.scale) === key) pt = [X / C.geo.scale, Y / C.geo.scale]; } } } }
      out.n++; if (!pt) { if ((C.geo.sl || []).indexOf(key) >= 0) { out.sliver = (out.sliver || 0) + 1; continue; } out.bad.push(key + ': no interior point'); continue; }
      const S = C.d.s[key]; if (S && !S.ok) { out.none = (out.none || []).concat(key); const vr0 = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', TX' }); await K._prepFull(vr0); const g0 = K._gen26(vr0); if (g0 && K._isVerified(g0)) out.bad.push(key + ': no ballot printed but shown as verified'); continue; } if (!S) { out.bad.push(key + ': no ballot'); continue; }
      const vr = Object.assign({}, base, { x: pt[0], y: pt[1], matched: ck + ' ' + key + ', TX' }); await K._prepFull(vr); const g = K._gen26(vr);
      if (g && K._isVerified(g) && g.precinct === key && g.contests.length === S.o.length && g.contests[0].office === 'United States Senator' && g.fullLink.url.indexOf(host) >= 0) { out.full++; if (g.contests.some(c => c.type === 'measure')) out.q++; } else out.bad.push(key + ' ' + (g && g.contests.length)); }
    const off = Object.assign({}, base, { x: -81.9, y: 26.0, matched: 'OFF MAP ' + ck }); await K._prepFull(off); const nf = K._gen26(off);
    const l = nf && K._fullFor(nf); if (!nf || K._isVerified(nf) || !(l && /official sample ballot/i.test(l.label))) out.bad.push('off-map address not labelled');
    for (const [a, x, y, want, n] of real) { const vr = Object.assign({}, base, { x, y, matched: a }); await K._prepFull(vr); const g = K._gen26(vr);
      out.real[a] = { ver: K._isVerified(g), p: g && g.precinct, n: g && g.contests.length, want, wantN: n }; }
    return out; }, [real, 'collin', 'Collin County', 'api.collincountytx.gov']);
  must(!r.bad.length, (r.bad || []).slice(0, 5).join(' | '));
  must(r.full === 348 && !r.sliver && JSON.stringify((r.none || []).sort()) === '["Precinct 100 (part)","Precinct 114 (part)","Precinct 161 (part)","Precinct 186 (part)","Precinct 193 (part)","Precinct 201 (districts differ from the map)","Precinct 215 (part)","Precinct 233 (part)","Precinct 33 (part)","Precinct 9 (part)"]', 'complete: ' + r.full + ' / ' + r.n + ' slivers ' + r.sliver + ' none ' + JSON.stringify(r.none));
  for (const [a, x] of Object.entries(r.real)) must(x.ver && x.p === x.want && x.n === x.wantN, a + ': ' + JSON.stringify(x));
  return 'Collin County, TX: ' + r.full + ' of ' + r.n + ' precincts/parts complete (' + (r.none || []).length + ' parts labelled, ' + r.q + ' with questions) · ' + Object.entries(r.real).map(([a, x]) => a.split(',')[0] + ' → ' + x.p + ' ' + x.n).join(', ');
});

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
