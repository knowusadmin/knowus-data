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
const MT = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webmanifest': 'application/manifest+json' };
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
await test('Trump page: Overview, In office record', async () => {
  await go('#/p/pr47');
  must(/about the role/i.test(await text()), 'no About the role');
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
  await page.click('section.bal .bbig a.bbtn'); await page.waitForTimeout(3000);
  must(/#\/voter\/ballot\/fill/.test(await page.evaluate(() => location.hash)), 'Fillable sample ballot did not open #/voter/ballot/fill');
  return 'blank PDF ' + k.lastSave.len + ' base64 chars, ' + k.lastSave.name;
});
await test('Fillable sample ballot: fill, Clear all, Print / Save PDF (app bridge)', async () => {
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
  const k = await kus(); must(k.lastSave, 'Print / Save PDF did not call the app bridge (saveFile)');
  must(k.lastSave.pdf && k.lastSave.mime === 'application/pdf' && /\.pdf$/.test(k.lastSave.name), 'bridge got a bad file: ' + JSON.stringify(k.lastSave));
  must(/saved to your downloads/i.test(await text()), 'no "Saved to your Downloads" message');
  return 'PDF ' + k.lastSave.len + ' base64 chars, ' + k.lastSave.name;
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
      const want = r.called ? r.winner : r.leader;
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
await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, local: LOCAL || null, width: W, at: new Date().toISOString(), results }, null, 1));
let md = `## KnowUS app tests — ${failed.length ? failed.length + ' failing' : 'all passing'}\n\n${SITE} at ${W}px, as the Android app 1.3 (mock bridge, no browser dialogs) · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
process.exit(failed.length ? 1 : 0);
