// KnowUS "user bot" (Shmuel, Nov 10 2026 10:50 PM: "set up bots along the way to test fix any issues or bugs on old and new features").
// Uses the LIVE site the way a person on a phone does: a 390x844 touch screen, real taps, typing in the search and address boxes.
// Every step fails on: an uncaught JS error, a console error from our own scripts, a failed request for one of our own files
// (the site or the knowus-data repo), or a blank screen. A screenshot is saved for every failing step.
//   node audit/user-bot.mjs [--site https://knowus.sites.tab.bot/] [--out out/user-bot]
// Read-only: never signs in, never creates an account (captcha rule), never writes to Firebase. The sign-in gate is set aside
// the same way the app tests do (kus_session + hiding #gate) so the public pages behind it can be used.
// Exit 1 when any step fails. Results: <out>/results.json + results.md + <out>/shots/*.png
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(process.env.PW_CORE || 'playwright-core')); }
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const SITE = arg('site', process.env.KNOWUS_SITE || 'https://knowus.sites.tab.bot/').replace(/\/?$/, '/');
const OUT = arg('out', 'out/user-bot'); const SHOTS = path.join(OUT, 'shots');
const ONLY = (arg('only', process.env.USER_BOT_ONLY || '') || '').split(',').filter(Boolean);
fs.mkdirSync(SHOTS, { recursive: true });
const ORIGIN = new URL(SITE).origin;
// "our own files": the site itself and the knowus-data repo it reads at run time
const OURS = u => u.startsWith(ORIGIN + '/') || /^https:\/\/raw\.githubusercontent\.com\/knowusadmin\/knowus-data\//.test(u) || /^https:\/\/(api\.github\.com\/repos|[^/]*\.github\.io\/)knowusadmin/.test(u);
// third-party noise a phone user never sees (analytics, reCAPTCHA / App Check without a real device, storage-access prompts)
const NOISE = /requestStorageAccess|app-?check|recaptcha|google-analytics|googletagmanager|firebaseinstallations|ERR_BLOCKED_BY_CLIENT/i;

// Sample addresses with a verified full official ballot (one each), and one in a county that only has the label + button.
const BALLOTS = [
  ['NC', 'Mecklenburg County, NC (Charlotte)', '600 E 4th St, Charlotte, NC 28202'],
  ['PA', 'Philadelphia, PA', '1400 John F Kennedy Blvd, Philadelphia, PA 19107'],
  ['OH-Cuyahoga', 'Cuyahoga County, OH (University Heights)', '2301 Milton Rd, Cleveland, OH 44118'],
  ['OH-Hamilton', 'Hamilton County, OH (Cincinnati)', '801 Plum St, Cincinnati, OH 45202'],
  ['OH-Montgomery', 'Montgomery County, OH (Dayton)', '101 W 3rd St, Dayton, OH 45402'],
  ['FL-PalmBeach', 'Palm Beach County, FL (West Palm Beach)', '301 N Olive Ave, West Palm Beach, FL 33401'],
];
const LABELLED = ['TX-Harris', 'Harris County, TX (Houston)', '901 Bagby St, Houston, TX 77002'];

const results = []; let browser, ctx, page, cur = null;
async function newPage() {
  if (ctx) await ctx.close().catch(() => {});
  ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, serviceWorkers: 'block', acceptDownloads: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36' });
  await ctx.addInitScript(() => {
    window.__ub = { printed: 0, dialogs: [] };
    window.print = () => { window.__ub.printed++; };
    window.alert = q => { window.__ub.dialogs.push('alert: ' + q); };
    window.confirm = q => { window.__ub.dialogs.push('confirm: ' + q); return false; };
    try { localStorage.setItem('kus_session', '1'); } catch (e) {}
  });
  page = await ctx.newPage();
  page.on('pageerror', e => cur && cur.errs.push('JS error: ' + String(e && e.message || e).slice(0, 300)));
  page.on('console', m => { if (!cur || m.type() !== 'error') return; const t = m.text(); const loc = (m.location() || {}).url || '';
    if (NOISE.test(t) || NOISE.test(loc)) return;
    if (/Failed to load resource/i.test(t)) return; // the network listeners below report our own failed files with their URL
    if (!loc || OURS(loc)) cur.errs.push('console error: ' + t.slice(0, 300) + (loc ? ' (' + loc.replace(ORIGIN, '').slice(0, 80) + ')' : ''));
  });
  page.on('requestfailed', r => { if (!cur) return; const u = r.url(); const f = (r.failure() || {}).errorText || '';
    if (!OURS(u) || /ERR_ABORTED/.test(f)) return; cur.errs.push('request failed: ' + u.replace(ORIGIN, '').slice(0, 160) + ' (' + f + ')'); });
  page.on('response', r => { if (!cur) return; const u = r.url(); if (!OURS(u) || r.status() < 400) return;
    cur.errs.push('HTTP ' + r.status() + ': ' + u.replace(ORIGIN, '').slice(0, 160)); });
  return page;
}
const ungate = () => page.evaluate(() => { document.documentElement.classList.remove('gated'); const g = document.getElementById('gate'); if (g) g.style.display = 'none'; });
const go = async (hash, wait = 2500) => { await page.goto(SITE + (hash || '#/'), { waitUntil: 'domcontentloaded', timeout: 45000 }); await page.waitForTimeout(wait); await ungate(); };
const hash = () => page.evaluate(() => location.hash);
const text = () => page.evaluate(() => (document.getElementById('app') || document.body).innerText);
async function notBlank(where) {
  const r = await page.evaluate(() => { const a = document.getElementById('app'); const t = (a ? a.innerText : '').trim();
    const vis = a ? [...a.querySelectorAll('*')].filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; }).length : 0;
    return { len: t.length, vis, err: /something went wrong|failed to load|undefined|NaN|\[object Object\]/.test(t) ? (t.match(/.{0,40}(something went wrong|failed to load|undefined|NaN|\[object Object\]).{0,40}/i) || [''])[0] : '' }; });
  if (r.len < 40 || r.vis < 5) throw new Error('blank screen on ' + where + ' (' + r.len + ' characters, ' + r.vis + ' visible elements)');
  if (r.err) throw new Error('broken text on ' + where + ': "' + r.err + '"');
}
// a real tap in the middle of an element (touchscreen, not a synthetic click)
async function tap(sel, where) {
  const el = typeof sel === 'string' ? await page.$(sel) : sel; if (!el) throw new Error('nothing to tap: ' + sel + (where ? ' on ' + where : ''));
  await el.evaluate(e => e.scrollIntoView({ block: 'center', inline: 'center' })).catch(() => {}); await page.waitForTimeout(250); // centre it: the fixed tab bar covers the bottom of the screen
  const b = await el.boundingBox(); if (!b) throw new Error('not visible, cannot tap: ' + sel);
  await page.touchscreen.tap(b.x + b.width / 2, b.y + b.height / 2);
}
const must = (c, m) => { if (!c) throw new Error(m); };
async function step(id, name, fn) {
  if (ONLY.length && !ONLY.some(o => id.startsWith(o))) return;
  const t0 = Date.now(); cur = { errs: [] }; let ok = true, msg = '', shot = '';
  try { msg = (await fn()) || ''; } catch (e) { ok = false; msg = String(e && e.message || e).split('\n')[0].slice(0, 500); }
  await page.waitForTimeout(300).catch(() => {});
  try { const d = await page.evaluate(() => window.__ub && window.__ub.dialogs); if (d && d.length) { ok = false; msg += (msg ? ' · ' : '') + 'opened a browser dialog: ' + d.join(' | '); await page.evaluate(() => { window.__ub.dialogs = []; }); } } catch {}
  const errs = [...new Set(cur.errs)]; cur = null;
  if (errs.length) { ok = false; msg += (msg ? ' · ' : '') + errs.slice(0, 6).join(' | ') + (errs.length > 6 ? ' (+' + (errs.length - 6) + ' more)' : ''); }
  if (!ok) { shot = id.replace(/[^\w-]+/g, '-') + '.png'; try { await page.screenshot({ path: path.join(SHOTS, shot), timeout: 15000 }); } catch { shot = ''; } }
  let at = ''; try { at = await hash(); } catch {}
  results.push({ id, name, ok, ms: Date.now() - t0, msg, shot, at });
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (msg ? ' — ' + msg : ''));
}

browser = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined, args: ['--no-sandbox'] });
await newPage();

// 1) every bottom tab, tapped
await step('tabs', 'Bottom tabs: tap each one, it opens its page and lights up', async () => {
  await go('#/', 3000); await notBlank('#/');
  const tabs = await page.$$eval('.tabbar a[data-tab]', a => a.map(x => ({ t: x.dataset.tab, href: x.getAttribute('href'), label: x.textContent.trim() })));
  must(tabs.length >= 6, 'expected 6 bottom tabs, found ' + tabs.length + ': ' + tabs.map(t => t.label).join(', '));
  const seen = [];
  for (const t of tabs) {
    await tap('.tabbar a[data-tab="' + t.t + '"]'); await page.waitForTimeout(1800);
    const h = await hash(); const want = t.href === '#/' ? /^#\/?$/ : new RegExp('^' + t.href.replace(/[/#]/g, '\\$&'));
    must(want.test(h), 'tapping "' + t.label + '" went to ' + h + ' (expected ' + t.href + ')');
    must(await page.evaluate(n => document.querySelector('.tabbar a[data-tab="' + n + '"]').getAttribute('aria-current') === 'page', t.t), '"' + t.label + '" tab is not lit after tapping it');
    await notBlank('the ' + t.label + ' tab'); seen.push(t.label);
  }
  return seen.join(', ');
});

// 2) Learn: the hub, each document and every civics lesson
await step('learn', 'Learn: the hub, the Constitution, Declaration, Federalist and every civics lesson open', async () => {
  await go('#/founding', 2000); await notBlank('Learn');
  const rows = await page.$$eval('#app a[href^="#/"]', a => [...new Set(a.map(x => x.getAttribute('href')))]);
  must(rows.length >= 4, 'Learn hub lists ' + rows.length + ' sections');
  const done = [];
  for (const h of rows) {
    await go('#/founding', 1200); await tap('#app a[href="' + h + '"]'); await page.waitForTimeout(1800);
    must((await hash()).startsWith(h), 'tapping ' + h + ' went to ' + await hash()); await notBlank(h); done.push(h);
  }
  await go('#/learn', 1500);
  const lessons = await page.$$eval('#app a[href^="#/learn/"]', a => [...new Set(a.map(x => x.getAttribute('href')))]);
  must(lessons.length >= 5, 'Civics lessons lists only ' + lessons.length + ' lessons');
  for (const h of lessons) {
    await go('#/learn', 1000); await tap('#app a[href="' + h + '"]'); await page.waitForTimeout(1500);
    must((await hash()).startsWith(h), 'tapping lesson ' + h + ' went to ' + await hash()); await notBlank(h);
    must((await text()).length > 300, h + ' lesson has almost no text'); done.push(h);
  }
  await go('#/federalist/10', 2000); await notBlank('#/federalist/10');
  return done.length + ' pages: ' + done.join(' ');
});

// 3) bills and executive orders, opened from the lists
async function openBillFromList(listHash, where, n) {
  await go(listHash, 3500);
  const ids = await page.$$eval('#app a[href^="#/bill/"]', a => [...new Set(a.map(x => x.getAttribute('href')))]);
  must(ids.length, 'the ' + where + ' list shows no bills');
  const out = [];
  for (const h of ids.slice(0, n)) {
    await go(listHash, 2500); await tap('#app a[href="' + h + '"]'); await page.waitForTimeout(2500);
    must((await hash()) === h, 'tapping ' + h + ' went to ' + await hash()); await notBlank(h);
    const r = await page.evaluate(() => { const c = document.querySelector('#app .bdsum'); const hs = [...document.querySelectorAll('#app h2')].map(x => x.textContent.trim());
      return { has: !!c, txt: c ? c.innerText.trim() : '', h2: hs }; });
    must(r.has && r.h2.includes('What it does'), h + ': no "What it does" box (headings: ' + r.h2.join(', ') + ')');
    must(r.txt.length > 15, h + ': the "What it does" box is empty');
    out.push({ h, summary: !/No official summary yet/i.test(r.txt) && !/official title above describes/i.test(r.txt), len: r.txt.length, ai: r.h2.includes('AI summary') });
    if (out[out.length - 1].summary) break;
  }
  return out;
}
await step('bill-federal', 'Federal bill: open one from the Passed list, its official summary shows', async () => {
  const r = await openBillFromList('#/bills/passed', 'federal Passed', 8);
  const s = r.find(x => x.summary); must(s, 'none of ' + r.length + ' federal bills opened shows an official summary (' + r.map(x => x.h).join(' ') + ')');
  return s.h + ': summary ' + s.len + ' characters' + (s.ai ? ', AI summary box too' : '') + ' (' + r.length + ' opened)';
});
await step('bill-state', 'State bill: pick a state, open a bill, its summary shows', async () => {
  const tried = [];
  for (const ab of ['OH', 'PA', 'NC', 'FL']) {
    await go('#/bills', 3000);
    await page.selectOption('#scOT', ab); await page.waitForTimeout(4000);
    const ids = await page.$$eval('#app a[href^="#/bill/"]', a => [...new Set(a.map(x => x.getAttribute('href')))]);
    must(ids.length, 'choosing ' + ab + ' in Bills shows no bills');
    must(ids.every(h => !/^#\/bill\/US-/.test(h)), 'choosing ' + ab + ' still lists federal bills');
    for (const h of ids.slice(0, 5)) {
      await tap('#app a[href="' + h + '"]'); await page.waitForTimeout(2500);
      must((await hash()) === h, 'tapping ' + h + ' went to ' + await hash()); await notBlank(h);
      const t = await page.evaluate(() => { const c = document.querySelector('#app .bdsum'); return c ? c.innerText.trim() : null; });
      must(t !== null, h + ': no "What it does" box'); must(t.length > 15, h + ': the "What it does" box is empty');
      tried.push(h);
      if (!/No official summary yet/i.test(t)) return h + ': ' + t.slice(0, 90).replace(/\s+/g, ' ') + '…';
      await page.goBack(); await page.waitForTimeout(2500); await ungate();
    }
  }
  throw new Error('no state bill opened shows a summary (' + tried.join(' ') + ')');
});
await step('eo', 'Executive order: open one from Exec Orders, status and official text show', async () => {
  await go('#/bills/eo', 3500); await notBlank('Exec Orders');
  const h = await page.$eval('#app a[href^="#/bills/eo/"]', a => a.getAttribute('href')).catch(() => null);
  must(h, 'the Exec Orders list shows no orders');
  await tap('#app a[href="' + h + '"]'); await page.waitForTimeout(2500);
  must((await hash()) === h, 'tapping ' + h + ' went to ' + await hash()); await notBlank(h);
  const r = await page.evaluate(() => { const hs = [...document.querySelectorAll('#app h2')].map(x => x.textContent.trim()); const c = document.querySelector('#app .bdsum'); return { hs, txt: c ? c.innerText.trim() : '', t: document.getElementById('app').innerText }; });
  must(r.hs.some(x => /Official summary|What the order says/.test(x)), h + ': no "Official summary" / "What the order says" section (' + r.hs.join(', ') + ')');
  must(r.txt.length > 60, h + ': the order\'s summary box is empty');
  must(/Status/.test(r.t) && /Federal Register/.test(r.t), h + ': no status from the Federal Register');
  return h + ': ' + r.txt.slice(0, 80).replace(/\s+/g, ' ') + '…';
});

// 4) search a person, open Overview, In office and Positions
await step('person', 'Search a person, open Overview, In office and Positions (#/p/<id>/positions)', async () => {
  await go('#/', 3000);
  await tap('#q'); await page.keyboard.type('Sanders', { delay: 60 }); await page.waitForTimeout(1500);
  const hit = (await page.$('#results a[href="#/p/S000033"]')) || (await page.$('#results a[href^="#/p/"]'));
  must(hit, 'searching "Sanders" shows no person');
  const href = await hit.getAttribute('href'); await tap(hit); await page.waitForTimeout(3000);
  const id = (await hash()).match(/^#\/p\/([^/?]+)/); must(id, 'tapping the result went to ' + await hash()); await notBlank('person page');
  const tabs = await page.$$eval('.ptabs a', a => a.map(x => x.textContent.trim()));
  must(['Overview', 'In office', 'Positions'].every(t => tabs.includes(t)), 'person tabs are ' + JSON.stringify(tabs));
  await tap('.ptabs a:has-text("In office")'); await page.waitForTimeout(2500);
  must(/\/office$/.test(await hash()), 'In office tab went to ' + await hash()); await notBlank('In office');
  await tap('.ptabs a:has-text("Positions")'); await page.waitForTimeout(2500);
  must(/\/positions$/.test(await hash()), 'Positions tab went to ' + await hash()); await notBlank('Positions');
  must(/position/i.test(await text()), 'Positions page shows no positions');
  await tap('.ptabs a:has-text("Overview")'); await page.waitForTimeout(2000);
  must(!/\/(office|positions)$/.test(await hash()), 'Overview tab did not go back'); await notBlank('Overview');
  await go('#/p/' + id[1] + '/positions', 3000); await notBlank('#/p/' + id[1] + '/positions');
  must(/positions/i.test(await page.$eval('.ptabs [aria-selected="true"]', x => x.textContent).catch(() => '')), 'opening #/p/' + id[1] + '/positions directly does not select Positions');
  return href + ' (' + tabs.join(' / ') + ')';
});
// people type the name they know ("Bernie Sanders", "Bob Casey"), first name + last name
await step('search-name', 'Search by the name people use: "Bernie Sanders" finds Sen. Bernard Sanders', async () => {
  await go('#/', 3000);
  await tap('#q'); await page.keyboard.type('Bernie Sanders', { delay: 50 }); await page.waitForTimeout(1500);
  const ok = await page.$('#results a[href="#/p/S000033"]');
  must(ok, 'typing "Bernie Sanders" shows "' + (await page.$eval('#results', e => e.innerText.trim().slice(0, 80)).catch(() => '')) + '" (the app lists him as "Bernard Sanders"; search only matches the exact name)');
  return 'found #/p/S000033';
});

// 5) ballot lookup, typed into the Voter tab like a person
async function lookup(addr) {
  await go('#/voter', 2500);
  await tap('#vaddr'); await page.fill('#vaddr', ''); await page.keyboard.type(addr, { delay: 15 });
  const before = await page.evaluate(() => { const b = document.getElementById('vbbtn'); return b ? b.outerHTML : ''; });
  await tap('#vgo');
  // the "See my sample ballot" button appears once the Census lookup has answered
  await page.waitForFunction(() => { const b = document.getElementById('vbbtn'); const r = b && b.getBoundingClientRect(); const t = document.getElementById('app').innerText;
    return (r && r.width > 0 && r.height > 0 && !document.querySelector('#vgo[disabled]')) || /No match found|Couldn.t reach the Census/.test(t); }, null, { timeout: 60000 });
  const bad = await page.evaluate(() => (document.getElementById('app').innerText.match(/No match found[^\n]*|Couldn.t reach the Census[^\n]*/) || [''])[0]);
  must(!bad, 'address lookup: ' + bad);
  await page.waitForTimeout(800);
  await tap('#vbbtn'); await page.waitForTimeout(3000);
  must(/^#\/voter\/ballot/.test(await hash()), '"See my sample ballot" went to ' + await hash());
  await page.waitForSelector('section.bal [data-pdfblank]', { timeout: 60000 }); await page.waitForTimeout(1000);
  const r = await page.evaluate(() => { const s = document.querySelector('section.bal'); return { conf: !!s.querySelector('.bconfh'), confTxt: (s.querySelector('.bconfh') || {}).textContent || '',
    blue: [...s.querySelectorAll('a.bbigfull')].map(a => ({ t: a.textContent.trim(), bg: getComputedStyle(a).backgroundColor, href: a.href })),
    official: [...s.querySelectorAll('a.bfull')].map(a => a.href), prec: (s.querySelector('.bprec') || {}).textContent || '', addr: (s.querySelector('.bad') || {}).textContent || '' }; });
  const num = addr.split(' ')[0];
  must(r.addr.includes(num), 'the ballot shown is for "' + r.addr.trim() + '", not ' + addr);
  return r;
}
for (const [id, where, addr] of BALLOTS) {
  await step('ballot-' + id, 'Ballot lookup, ' + where + ': a full official ballot appears', async () => {
    const r = await lookup(addr);
    must(!r.conf, addr + ' shows "' + r.confTxt.trim() + '" instead of the full official ballot');
    await page.evaluate(() => { location.hash = '#/voter/ballot/fill'; }); await page.waitForTimeout(3000);
    await page.waitForSelector('section.bal[data-b] .bopt[data-c]', { timeout: 45000 });
    const c = await page.evaluate(() => { const s = document.querySelector('section.bal[data-b]'); const opts = s.querySelectorAll('.bopt[data-c]').length;
      const races = new Set([...s.querySelectorAll('.bopt[data-c]')].map(o => (o.closest('[data-ci],.bc,.bcon,li,div') || {}).outerHTML ? o.closest('[data-ci],.bc,.bcon,li,div') : o)).size;
      return { opts, races, count: (s.querySelector('[data-count]') || {}).textContent || '' }; });
    must(c.opts >= 6, addr + ': the full ballot has only ' + c.opts + ' choices');
    return (r.prec ? r.prec.replace(/\s+/g, ' ').slice(0, 70) + ' · ' : '') + c.opts + ' ovals, ' + c.count.trim();
  });
}
await step('ballot-labelled', 'Ballot lookup, ' + LABELLED[1] + ': labelled "Races we\'ve confirmed…" with the blue official button', async () => {
  const r = await lookup(LABELLED[2]);
  must(r.conf && /Races we.ve confirmed/.test(r.confTxt), 'no "Races we\'ve confirmed…" heading for ' + LABELLED[2]);
  must(r.blue.length, 'no blue official button for ' + LABELLED[2]);
  const m = (r.blue[0].bg.match(/\d+/g) || []).map(Number); must(m[2] > m[0] + 40, 'the official button is not blue: ' + r.blue[0].bg);
  return r.confTxt.trim().slice(0, 80) + ' · button "' + r.blue[0].t.slice(0, 50) + '"';
});

// 6) Save PDF downloads a file and never opens the print dialog
await step('pdf', 'Save PDF on the fillable ballot downloads a PDF with no print dialog', async () => {
  if (!/#\/voter\/ballot/.test(await hash())) await lookup(BALLOTS[2][2]);
  await page.evaluate(() => { location.hash = '#/voter/ballot/fill'; }); await page.waitForTimeout(3000);
  await page.waitForSelector('section.bal[data-b] [data-pdf]', { timeout: 45000 });
  await page.evaluate(() => { window.__ub.printed = 0; });
  const dlp = page.waitForEvent('download', { timeout: 20000 }).catch(() => null);
  await tap('section.bal[data-b] [data-pdf]'); const dl = await dlp; await page.waitForTimeout(1500);
  must((await page.evaluate(() => window.__ub.printed)) === 0, 'Save PDF opened the print dialog');
  must(dl, 'Save PDF did not download anything');
  must(/\.pdf$/i.test(dl.suggestedFilename()), 'Save PDF downloaded ' + dl.suggestedFilename());
  const p = await dl.path().catch(() => null); const head = p ? fs.readFileSync(p).subarray(0, 5).toString() : '';
  must(head === '%PDF-', 'the downloaded file is not a PDF');
  return dl.suggestedFilename() + ', ' + fs.statSync(p).size + ' bytes';
});

// 7) Elections tab: totals and legends
const hexOf = c => { const m = String(c).match(/\d+/g); if (!m) return String(c).toLowerCase(); return '#' + m.slice(0, 3).map(x => (+x).toString(16).padStart(2, '0')).join(''); };
await newPage();
await step('elec-totals', 'Elections: Senate, House, Governor and Mayor totals add up to 100, 435, 50 and the mayor count', async () => {
  await go('#/', 2500); await tap('.tabbar a[data-tab="election"]'); await page.waitForTimeout(4000); await notBlank('Election');
  const bars = await page.$$eval('.tot', t => t.map(x => ({ n: x.getAttribute('data-tot'), total: +((x.querySelector('.bar[data-total]') || { getAttribute: () => NaN }).getAttribute('data-total')), sum: +((x.querySelector('.bar[data-sum]') || { getAttribute: () => NaN }).getAttribute('data-sum')),
    shown: [...x.querySelectorAll('.nums > span')].reduce((a, s) => a + (s.textContent.match(/\d+/g) || []).reduce((q, n) => q + +n, 0), 0) })));
  const want = { Senate: 100, House: 435, Governors: 50 }; const out = [];
  for (const k of Object.keys(want)) { const b = bars.find(x => x.n === k); must(b, 'no ' + k + ' card');
    must(b.total === want[k] && b.sum === want[k], k + ' adds up to ' + b.sum + ' (should be ' + want[k] + ')');
    out.push(k + ' ' + b.sum); }
  await tap('#app a[href="#/election/mayor"]'); await page.waitForTimeout(3500);
  must(/^#\/election\/mayor/.test(await hash()), 'Mayor tab went to ' + await hash()); await notBlank('Mayor');
  const data = await (await ctx.request.get(SITE + 'data/mayors.json?x=' + Date.now())).json();
  const n = (data.cities || []).length; must(n > 0, 'data/mayors.json lists no cities');
  const m = await page.evaluate(() => ({ dots: document.querySelectorAll('.usmap circle.cdot').length, rows: new Set([...document.querySelectorAll('#app a[href^="#/election/mayor/"]')].map(a => a.getAttribute('href'))).size }));
  must(m.dots === n, 'the mayor map shows ' + m.dots + ' cities but there are ' + n + ' mayor races');
  must(m.rows === n, 'the mayor list shows ' + m.rows + ' cities but there are ' + n + ' mayor races');
  const won = data.cities.filter(c => c.status === 'won').length, counting = n - won;
  out.push('Mayor ' + n + ' (' + won + ' won + ' + counting + ' not final)');
  return out.join(' · ');
});
for (const mode of ['senate', 'house', 'gov', 'mayor']) {
  await step('legend-' + mode, 'Elections map (' + mode + '): every colour on the map is in the legend', async () => {
    await go('#/election/' + mode, 4000); await notBlank('#/election/' + mode);
    const r = await page.evaluate((mode) => {
      const sel = mode === 'mayor' ? '.usmap circle.cdot' : '.usmap path[data-st], .usmap circle[data-st]:not(.hit)';
      const fills = [...document.querySelectorAll(sel)].map(e => (e.getAttribute('fill') || '').toLowerCase());
      const leg = document.querySelector('.mlegend'); const sw = leg ? [...leg.querySelectorAll('i')].map(i => getComputedStyle(i).backgroundColor) : [];
      return { fills, sw, legTxt: leg ? leg.innerText : '' };
    }, mode);
    must(r.fills.length, 'no map shapes found');
    const sw = new Set(r.sw.map(hexOf)); let bad = [...new Set(r.fills)].filter(f => !sw.has(f));
    if (mode === 'house' && /darker = bigger share/i.test(r.legTxt)) bad = bad.filter(f => { const m = f.match(/[0-9a-f]{2}/g).map(x => parseInt(x, 16)); return !(m[2] > m[0] + 20 || m[0] > m[2] + 20); });
    must(!bad.length, 'colours on the map the legend does not explain: ' + bad.join(', ') + ' (legend: ' + [...sw].join(', ') + ')');
    return new Set(r.fills).size + ' colours, all in the legend';
  });
}

// 8) slide-up panels close on swipe down, tap outside and Back
await step('sheet', 'Slide-up panel: closes on swipe down, on a tap outside, and on Back', async () => {
  const open = async () => { await go('#/election/senate', 3500); await tap('.usmap path[data-st="OH"]').catch(async () => { await page.evaluate(() => { location.hash = '#/election/senate/OH'; }); }); await page.waitForTimeout(1500); return page.evaluate(() => !!document.querySelector('#sheet.open')); };
  const isOpen = () => page.evaluate(() => !!document.querySelector('#sheet.open'));
  must(await open(), 'tapping Ohio on the Senate map did not open its panel');
  await notBlank('the Ohio panel');
  const cdp = await ctx.newCDPSession(page);
  const g = await page.$eval('#sheet .grab', e => { const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  const tp = (type, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: g.x, y }] });
  await tp('touchStart', g.y); for (let k = 1; k <= 12; k++) { await tp('touchMove', g.y + k * 40); await page.waitForTimeout(16); } await tp('touchEnd', 0);
  await page.waitForTimeout(900); must(!(await isOpen()), 'swiping down did not close the panel');
  must(await open(), 'the panel did not reopen');
  const top = await page.$eval('#sheet', e => e.getBoundingClientRect().top);
  await page.touchscreen.tap(195, Math.max(10, Math.min(30, top - 10))); await page.waitForTimeout(900);
  must(!(await isOpen()), 'tapping outside the panel did not close it');
  must(await open(), 'the panel did not reopen (Back)');
  await page.goBack(); await page.waitForTimeout(1000);
  must(!(await isOpen()), 'Back did not close the panel');
  must(/^#\/election\/senate/.test(await hash()), 'Back left the Senate map for ' + await hash());
  return 'swipe, tap outside and Back all close it';
});

await browser.close();
const failed = results.filter(r => !r.ok);
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ site: SITE, at: new Date().toISOString(), failed: failed.length, results }, null, 1));
let md = `## KnowUS user bot: ${failed.length ? failed.length + ' problem' + (failed.length > 1 ? 's' : '') + ' found' : 'all ' + results.length + ' steps pass'}\n\n${SITE} on a 390×844 touch phone · ${new Date().toISOString()}\n\n`;
for (const r of results) md += `- ${r.ok ? '✅' : '❌'} **${r.name}**${r.msg ? ' — ' + r.msg : ''}\n`;
fs.writeFileSync(path.join(OUT, 'results.md'), md);
console.log(failed.length + ' of ' + results.length + ' steps failed');
process.exit(failed.length ? 1 : 0);
