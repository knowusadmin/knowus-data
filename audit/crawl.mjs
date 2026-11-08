// KnowUS site audit: crawler. Opens the LIVE site like a phone user and records problems.
// Usage: node audit/crawl.mjs --shard A|B|C --width 390 --out audit/out/A-390
// Read-only: no sign-in, no Firebase writes, no form submits. Buttons that could save/track/sign in are never tapped.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const SHARD = args.shard || 'A';
const WIDTH = +(args.width || 390);
const OUT = args.out || `audit/out/${SHARD}-${WIDTH}`;
const SITE = (args.site || process.env.AUDIT_SITE || 'https://knowus.sites.tab.bot/').replace(/\/?$/, '/');
const SEED = args.seed || process.env.AUDIT_SEED || new Date().toISOString().slice(0, 13); // changes every run hour
const BUDGET_MS = +(process.env.AUDIT_BUDGET_MIN || 15) * 60000;
const MAX_SHOTS = 80;
const T0 = Date.now();
fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });

// ---------- deterministic random ----------
function rng(seedStr) { let h = 2166136261; for (const c of seedStr) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return () => { h += 0x6D2B79F5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const R = rng(SEED + ':' + SHARD);
const pick = (arr, n) => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, n); };

// ---------- playwright ----------
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(process.env.PW_CORE || 'playwright-core')); }

const issues = [];
const visited = [];
const coverage = {};
const internalHrefs = new Map(); // href -> first route seen on
let shots = 0;
let curRoute = '(start)';
const seenKeys = new Set();
function addIssue(o) {
  const key = [o.type, o.route, o.element, o.error].join('|');
  if (seenKeys.has(key)) return null;
  seenKeys.add(key);
  const it = { severity: o.severity, type: o.type, route: o.route || curRoute, viewport: WIDTH, element: (o.element || '').slice(0, 200), error: (o.error || '').slice(0, 500), screenshot: o.screenshot || null, shard: SHARD };
  issues.push(it); return it;
}
const cover = (k, n = 1) => { coverage[k] = (coverage[k] || 0) + n; };
const timeLeft = () => BUDGET_MS - (Date.now() - T0);

const IGNORE_HOSTS = /(google-analytics|googletagmanager|doubleclick|firebaseinstallations|firebaselogging|identitytoolkit|securetoken|gstatic\.com\/recaptcha)/;
const SITE_HOST = new URL(SITE).host;

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined, args: ['--no-sandbox'] });
const context = await browser.newContext({
  viewport: { width: WIDTH, height: 800 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
  userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36 KnowUS-SiteAudit',
  serviceWorkers: 'block',
});
// keep the audit from ever opening real windows; count the attempts instead
// The app shows a sign-in gate to signed-out visitors. The audit never signs in: it hides the gate on its own copy of the page
// (no account, no Firebase writes) so it can read the screens behind it. The gate itself is checked separately in shard C.
await context.addInitScript(() => {
  const fix = () => { if (document.documentElement.classList.contains('gated')) document.documentElement.classList.remove('gated'); };
  const st = document.createElement('style'); st.textContent = '#gate{display:none!important}';
  const arm = () => { if (!document.documentElement || arm.done) return; arm.done = 1; new MutationObserver(fix).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] }); fix(); };
  const iv = setInterval(() => { arm(); fix(); if (document.head && !st.isConnected) document.head.appendChild(st); }, 30);
  setTimeout(() => clearInterval(iv), 20000);
  document.addEventListener('DOMContentLoaded', () => { arm(); fix(); document.head.appendChild(st); });
});
await context.addInitScript(() => {
  window.__auditOpened = 0; window.open = function () { window.__auditOpened++; return null; };
  // a tap that opens an outside page (target=_blank link, even one clicked by script) counts as "did something"; the page itself is not opened
  document.addEventListener('click', e => { const a = e.target && e.target.closest && e.target.closest('a[href]'); if (a && (a.target === '_blank' || /^https?:/.test(a.getAttribute('href')) && !a.href.startsWith(location.origin))) { window.__auditOpened++; e.preventDefault(); } }, true);
});
let popups = 0;
const page = await context.newPage();
context.on('page', async p => { if (p === page) return; popups++; try { await p.close(); } catch {} });
let inflight = 0;
page.on('request', () => { inflight++; });
page.on('requestfinished', () => { inflight = Math.max(0, inflight - 1); });
page.on('requestfailed', req => {
  inflight = Math.max(0, inflight - 1);
  const f = req.failure() && req.failure().errorText || '';
  const u = req.url();
  if (/ERR_ABORTED|ERR_BLOCKED_BY_CLIENT/.test(f) || IGNORE_HOSTS.test(u)) return;
  if (req.resourceType() === 'image' && !u.includes(SITE_HOST)) return; // broken images are judged on the page (the app has photo fallbacks)
  const own = u.includes(SITE_HOST) || u.includes('knowusadmin/knowus-data');
  addIssue({ severity: own ? 'high' : 'low', type: 'Failed network request', route: curRoute, element: u, error: f });
});
page.on('response', res => {
  const s = res.status(); if (s < 400) return;
  const u = res.url(); const req = res.request();
  if (IGNORE_HOSTS.test(u)) return;
  if (req.resourceType() === 'image' && !u.includes(SITE_HOST)) return;
  const own = u.includes(SITE_HOST) || u.includes('knowusadmin/knowus-data');
  if (!own && /wikipedia\.org\/w\/api|wikidata/.test(u) && s === 429) return;
  addIssue({ severity: own ? 'high' : 'low', type: 'Failed network request', route: curRoute, element: u, error: 'HTTP ' + s });
});
page.on('pageerror', err => { addIssue({ severity: 'high', type: 'JavaScript error', route: curRoute, element: '', error: String(err && err.message || err).split('\n')[0] }); });
page.on('console', msg => {
  if (msg.type() !== 'error') return; const t = msg.text();
  if (/Failed to load resource|net::ERR|favicon|firestore|Firebase|WebChannel|analytics/i.test(t)) return;
  addIssue({ severity: 'low', type: 'Console error', route: curRoute, element: '', error: t.split('\n')[0] });
});

// ---------- navigation ----------
async function settle(maxMs = 8000) {
  const end = Date.now() + maxMs; let last = '', stableSince = Date.now();
  await page.waitForTimeout(60);
  while (Date.now() < end) {
    let sig;
    try { sig = await page.evaluate(() => { const a = document.getElementById('app'); const t = a ? a.innerText : ''; return (a ? a.innerHTML.length : 0) + '|' + /Loading|Checking for updates…|Loading counties/.test(t.slice(0, 600)); }); } catch { sig = 'x'; }
    if (sig !== last) { last = sig; stableSince = Date.now(); }
    else if (Date.now() - stableSince > 350 && inflight <= 0 && !sig.endsWith('true')) return true;
    else if (Date.now() - stableSince > 1500 && !sig.endsWith('true')) return true;
    await page.waitForTimeout(80);
  }
  return false;
}
async function go(route) {
  curRoute = route;
  await page.evaluate(h => { window.__auditOpened = 0; if (location.hash === h) window.dispatchEvent(new HashChangeEvent('hashchange')); else location.hash = h; }, route);
  const ok = await settle();
  if (!ok) addIssue({ severity: 'medium', type: 'Page never finished loading', route, element: '', error: 'Still showing "Loading…" or changing after 8 s' });
  return ok;
}
async function shot(name, highlightId) {
  if (shots >= MAX_SHOTS) return null;
  shots++;
  const file = `shots/${SHARD}-${WIDTH}-${String(shots).padStart(3, '0')}-${name.replace(/[^a-z0-9]+/gi, '-').slice(0, 40)}.jpg`;
  try {
    if (highlightId) await page.evaluate(id => { const e = document.querySelector(`[data-audit-id="${id}"]`); if (e) { e.scrollIntoView({ block: 'center' }); e.style.outline = '4px solid #ff00aa'; e.style.outlineOffset = '-2px'; } }, highlightId);
    await page.screenshot({ path: path.join(OUT, file), type: 'jpeg', quality: 55 });
    if (highlightId) await page.evaluate(id => { const e = document.querySelector(`[data-audit-id="${id}"]`); if (e) { e.style.outline = ''; e.style.outlineOffset = ''; } }, highlightId);
  } catch { return null; }
  return file;
}

// ---------- in-page checks ----------
const BANNED = ['racist', 'racism', 'extremist', 'extremism', 'far-right', 'far right', 'far-left', 'far left', 'authoritarian', 'controversial', 'divisive', 'baseless', 'debunked', 'conspiracy theor', 'conspiracy', 'false claims', 'falsely claimed', 'falsely claims'];
function titleUse(t, i, len) {
  // an official title (an executive order, bill or law name) is quoted, not an AI label: Title Case words around the match, or inside quotes
  const w = t.slice(i, i + len); if (!/^[A-Z]/.test(w)) return false;
  const before = t.slice(Math.max(0, i - 60), i).trim().split(/\s+/).slice(-3), after = t.slice(i + len, i + len + 60).trim().split(/\s+/).slice(0, 3);
  const cap = x => /^[A-Z0-9“"'(]/.test(x) || /^(and|of|the|to|for|from|in|on|a|an|by|with)$/.test(x);
  const run = [...before, ...after].filter(Boolean); return run.length >= 2 && run.filter(cap).length >= run.length - 1;
}
async function checkPage() {
  return page.evaluate(({ BANNED, TODAY, TITLE }) => {
    const titleUse = new Function('return ' + TITLE)();
    const out = { hscroll: null, tokens: [], empty: [], dups: [], notFound: false, termPast: [], banned: [], votes: [], cands: [], hrefs: [], aiBlocks: 0, text: '' };
    const app = document.getElementById('app') || document.body;
    const vw = document.documentElement.clientWidth;
    const vis = e => { const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false; const s = getComputedStyle(e); return s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
    const desc = e => { const t = (e.getAttribute('aria-label') || e.innerText || e.getAttribute('alt') || '').replace(/\s+/g, ' ').trim(); return (e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).join('.') : '') + (t ? ' "' + t.slice(0, 90) + '"' : '')); };
    const appText = app.innerText || '';
    out.text = appText.slice(0, 300);
    out.notFound = /That page doesn.t exist|^\s*(Not found|Page not found)\b|\bnot found\.\s*(Back|All counties)/i.test(appText.slice(0, 400));
    // sideways scroll
    const sw = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
    if (sw > vw + 1) {
      const offenders = [];
      for (const e of document.querySelectorAll('body *')) {
        const r = e.getBoundingClientRect(); if (r.right <= vw + 1 || r.width < 1) continue;
        let p = e.parentElement, clipped = false; while (p && p !== document.body) { const s = getComputedStyle(p); if (/(auto|scroll|hidden|clip)/.test(s.overflowX)) { const pr = p.getBoundingClientRect(); if (pr.right <= vw + 1) { clipped = true; break; } } p = p.parentElement; }
        if (!clipped) offenders.push(e);
      }
      const leaves = offenders.filter(e => !offenders.some(o => o !== e && e.contains(o)));
      out.hscroll = { width: sw, vw, els: leaves.slice(0, 3).map(desc) };
    }
    // walk visible text nodes
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n; const tokRe = /\[object Object\]|\bNaN\b|\bInvalid Date\b/;
    while ((n = tw.nextNode())) {
      const t = n.nodeValue; if (!t || !t.trim()) continue;
      const pe = n.parentElement; if (!pe || /SCRIPT|STYLE|NOSCRIPT|TEXTAREA/.test(pe.tagName) || !pe.getClientRects().length) continue;
      const tt = t.trim();
      let bad = tt.match(tokRe);
      if (!bad) { const m = tt.match(/(^|[:·|(,]\s*)(undefined|null)(?=$|\s*[·|),:])/); if (m && (tt.length < 60 || m[1])) bad = [m[2]]; }
      if (bad) out.tokens.push({ token: bad[0], text: tt.slice(0, 120), el: desc(pe).slice(0, 120) });
    }
    // empty boxes
    for (const e of app.querySelectorAll('.card, .list, .row, .tile, li, .box, .fedcard, .bdai, .aiprof, td')) {
      if (!vis(e)) continue;
      if ((e.innerText || '').trim()) continue;
      if (e.querySelector('img, svg, canvas, input, select, iframe, video')) continue;
      out.empty.push(desc(e) + (e.previousElementSibling && /^H[1-4]$/.test(e.previousElementSibling.tagName) ? ' under "' + e.previousElementSibling.innerText.trim().slice(0, 60) + '"' : ''));
    }
    for (const h of app.querySelectorAll('h2, h3')) { if (!vis(h)) continue; const nx = h.nextElementSibling; if (nx && vis(nx) && !(nx.innerText || '').trim() && !nx.querySelector('img,svg,canvas,input,select,iframe')) out.empty.push('section "' + h.innerText.trim().slice(0, 60) + '" has nothing under it'); }
    // duplicates in a list
    for (const L of app.querySelectorAll('.list, ul, ol')) {
      const seen = new Map();
      for (const r of L.children) {
        if (!vis(r)) continue;
        const a = r.matches('a[href]') ? r : null;
        const nm = (r.querySelector('.nm') || r).innerText.replace(/\s+/g, ' ').trim();
        const keys = [];
        if (a && /^#\/(p|s)\//.test(a.getAttribute('href'))) keys.push('href:' + a.getAttribute('href'));
        if (r.querySelector('.nm')) keys.push('txt:' + r.innerText.replace(/\s+/g, ' ').trim());
        for (const k of keys) { if (seen.has(k)) { out.dups.push({ name: nm.slice(0, 80), key: k.slice(0, 120), list: (L.previousElementSibling && L.previousElementSibling.innerText || '').trim().slice(0, 60) }); break; } seen.set(k, 1); }
      }
    }
    // term already ended but shown as current
    const MONTHS = 'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec';
    const dRe = new RegExp('term ends?:?\\s*((?:' + MONTHS + ')[a-z]*\\.? \\d{1,2},? \\d{4})', 'ig');
    const scan = (app.innerText || '').replace(/\n/g, ' ');
    let m; while ((m = dRe.exec(scan))) { const d = new Date(m[1].replace('.', '')); if (!isNaN(d) && d < new Date(TODAY)) out.termPast.push(m[0]); }
    for (const li of app.querySelectorAll('ul.facts li')) { const s = li.querySelectorAll('span'); if (s.length >= 2 && /Term ends/i.test(s[0].innerText)) { const v = s[1].innerText.trim(); const d = new Date(v); if (/\d{4}/.test(v) && !isNaN(d) && /[A-Za-z]+ \d{1,2}, \d{4}/.test(v) && d < new Date(TODAY)) out.termPast.push('Term ends ' + v); } }
    // AI text: banned labels
    const aiRoots = new Set();
    for (const f of app.querySelectorAll('.aiflag, .aiprof, .aibox, [class*="posn"], [class*="positions"]')) aiRoots.add(f.closest('.card') || f);
    for (const e of app.querySelectorAll('p, small, span')) { if (/Written by AI from public sources/.test(e.textContent || '') && !e.querySelector('p, div')) { const root = e.closest('.card, .aibox, section'); if (root && root !== app) aiRoots.add(root); } }
    const posPage = /\/positions/.test(location.hash);
    if (posPage) aiRoots.add(app);
    out.loaded = [];
    // person pages: the same labels anywhere else on the page (e.g. a Wikipedia bio line), reported separately
    if (/^#\/(p\/|s\/[A-Z]{2}\/local\/.*\/(o|leg)\/)/.test(location.hash) && !posPage) {
      const t = Array.from(app.querySelectorAll('.card, .bio, .hero, p')).filter(e => ![...aiRoots].some(r => r && r.contains(e))).map(e => e.innerText).join('\n');
      for (const w of BANNED) { const re = new RegExp('(^|[^a-z])(' + w.replace('-', '[- ]?') + ')(?=[^a-z]|$)', 'ig'); let mm; while ((mm = re.exec(t))) { const i = mm.index + mm[1].length; if (!titleUse(t, i, mm[2].length)) { out.loaded.push({ word: w, ctx: t.slice(Math.max(0, i - 80), i + 80).replace(/\s+/g, ' ') }); break; } } }
    }
    out.aiBlocks = aiRoots.size;
    for (const r of aiRoots) {
      if (!r) continue;
      const t = (r.innerText || '').replace(/Written by AI from public sources[^\n]*/g, '');
      for (const w of BANNED) { const re = new RegExp('(^|[^a-z])(' + w.replace('-', '[- ]?') + ')(?=[^a-z]|$)', 'ig'); let mm, hit = null; while ((mm = re.exec(t))) { const i = mm.index + mm[1].length; if (!titleUse(t, i, mm[2].length)) { hit = i; break; } } if (hit != null) { out.banned.push({ word: w, ctx: t.slice(Math.max(0, hit - 80), hit + 80).replace(/\s+/g, ' ') }); break; } }
    }
    // election vote totals that are not whole numbers
    for (const mm of (app.innerText || '').matchAll(/(\d[\d,]*\.\d+)\s*votes?\b/gi)) out.votes.push(mm[0]);
    // ---- tappable candidates ----
    let id = 0;
    document.querySelectorAll('[data-audit-id]').forEach(e => e.removeAttribute('data-audit-id'));
    const NATIVE = 'a[href], button, summary, select, input, textarea, label';
    const seenEls = new Set();
    const add = (e, kind, why) => { if (seenEls.has(e) || !vis(e)) return; seenEls.add(e); e.setAttribute('data-audit-id', String(++id)); out.cands.push({ id: String(id), kind, why, desc: desc(e), href: e.getAttribute && e.getAttribute('href') || '', target: e.getAttribute && e.getAttribute('target') || '', text: (e.innerText || e.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 80) }); };
    const scope = document.body;
    for (const e of scope.querySelectorAll('a[href]')) add(e, 'link', 'link');
    for (const e of scope.querySelectorAll('button, summary')) if (!e.disabled) add(e, 'button', 'button');
    for (const e of scope.querySelectorAll('[role="link"], [role="button"], [data-href], [onclick], [tabindex="0"]')) if (!e.closest('a[href], button')) add(e, 'pseudo', e.getAttribute('role') ? 'role=' + e.getAttribute('role') : e.hasAttribute('data-href') ? 'data-href' : e.hasAttribute('onclick') ? 'onclick' : 'tabindex');
    // looks tappable: chevron / › / pointer cursor, not inside a real control
    for (const e of app.querySelectorAll('.row, .card, .tile, li, .box, div, section')) {
      if (e.closest(NATIVE) || e.querySelector(':scope > a[href]:only-child')) continue;
      const own = Array.from(e.childNodes).filter(c => c.nodeType === 3).map(c => c.nodeValue).join('').trim();
      const chev = e.querySelector(':scope > svg.chev, :scope > .chev, :scope > .abgo, :scope > .go') || /›\s*$/.test(own);
      if (chev) add(e, 'pseudo', 'shows ›');
      else if (getComputedStyle(e).cursor === 'pointer' && !e.parentElement.closest('[data-audit-id]')) add(e, 'pseudo', 'pointer cursor');
    }
    // boxes Shmuel expects to open something
    const named = /^(Positions and record|Key positions|About (this|the) role|Role)$/i;
    for (const h of app.querySelectorAll('h2, h3')) {
      if (!named.test(h.innerText.trim())) continue;
      let box = h.tagName === 'H2' ? h.nextElementSibling : (h.closest('[data-href], .abrole, .aibox, .card') || h.parentElement);
      if (h.tagName === 'H2' && box && box.matches('.card') && box.querySelector('.abrole, .aibox')) box = box.querySelector('.abrole') || box;
      if (box && !box.closest('a[href], button')) add(box, 'box', 'named box "' + h.innerText.trim() + '"');
    }
    for (const e of app.querySelectorAll('.aibox, .abrole')) if (!e.closest('a[href], button')) add(e, 'box', 'named box (' + e.className + ')');
    // an open sheet/dialog covering the screen: only what is inside it can be tapped right now (the page behind is meant to be covered)
    let layer = null, lz = -1;
    for (const e of document.querySelectorAll('body *')) { const st = getComputedStyle(e); if (st.position !== 'fixed' || st.pointerEvents === 'none' || st.visibility === 'hidden' || st.display === 'none') continue; const r = e.getBoundingClientRect(); if (r.width >= innerWidth * 0.9 && r.height >= innerHeight * 0.7) { const z = +st.zIndex || 0; if (z >= lz) { lz = z; layer = e; } } }
    out.layer = layer ? desc(layer).slice(0, 60) : '';
    const inertUI = e => { let x = e; while (x && x !== document.body) { if (x.hidden || x.inert || x.getAttribute('aria-hidden') === 'true') return true; x = x.parentElement; } const pe = getComputedStyle(e).pointerEvents; return pe === 'none' && e.parentElement && getComputedStyle(e.parentElement).pointerEvents === 'none'; };
    out.cands = out.cands.filter(c => { const e = document.querySelector(`[data-audit-id="${c.id}"]`); if (!e) return false; if (layer && !layer.contains(e)) { e.removeAttribute('data-audit-id'); return false; } if (inertUI(e)) { e.removeAttribute('data-audit-id'); return false; } return true; });
    // hit test: can a finger actually reach it?
    for (const c of out.cands) {
      const e = document.querySelector(`[data-audit-id="${c.id}"]`); if (!e) continue;
      if (c.kind === 'link' && out.cands.length > 220 && +c.id % 4) continue; // big lists: sample
      e.scrollIntoView({ block: 'center' });
      const r = e.getBoundingClientRect();
      const pts = []; for (const fy of [0.5, 0.3, 0.7]) for (const fx of [0.5, 0.2, 0.8, 0.08]) pts.push([r.left + r.width * fx, r.top + r.height * fy]);
      let okPt = null, hitDesc = '';
      for (const [x, y] of pts) {
        if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
        const h = document.elementFromPoint(x, y); if (!h) continue;
        if (e === h || e.contains(h) || (h.contains(e) && h.closest('a[href],button'))) {
          // for boxes, prefer a point that is not on a link inside the box
          if ((c.kind === 'box' || c.kind === 'pseudo') && h !== e && h.closest('a[href], button, input, select') && e.contains(h.closest('a[href], button, input, select'))) { if (!okPt) okPt = { x, y, inner: true }; continue; }
          okPt = { x, y }; break;
        }
        hitDesc = desc(h);
      }
      c.pt = okPt; c.covered = okPt ? '' : (hitDesc || 'off-screen');
      const s = getComputedStyle(e); if (s.pointerEvents === 'none') c.covered = 'pointer-events:none';
    }
    window.scrollTo(0, 0);
    out.hrefs = Array.from(new Set(out.cands.filter(c => c.kind === 'link' && /^#\//.test(c.href)).map(c => c.href)));
    out.imgs = Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0 && !/^data:/.test(i.currentSrc || i.src) && (i.currentSrc || i.src) && getComputedStyle(i).display !== 'none').map(i => ({ src: (i.currentSrc || i.src).slice(0, 200), alt: i.alt }));
    return out;
  }, { BANNED, TODAY: new Date().toISOString().slice(0, 10), TITLE: titleUse.toString() });
}

async function stateSig() {
  return page.evaluate(() => {
    const s = (document.getElementById('app') || document.body).innerHTML + '|' + Array.from(document.querySelectorAll('[aria-expanded],[open],dialog,.sheet,[class*="sheet"]')).map(e => (e.getAttribute('aria-expanded') || '') + (e.open ? 'o' : '') + (e.hidden ? 'h' : '') + e.className).join(',');
    let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return { hash: location.hash, sig: h, opened: window.__auditOpened || 0, y: Math.round(scrollY) };
  });
}

const RISKY = /password|forgot|track|untrack|follow|sign|log ?in|log ?out|save|delete|remove|submit|send|create|register|google|apple|subscribe|notif|share|copy|download|print|install|refresh|reload|retry|admin|vote|clear|reset|allow|location|use my|account|pdf|email|call/i;
const clickedSigs = new Map();
async function tapTest(route, c) {
  // returns true when the tap did something
  const before = await stateSig(); const pop0 = popups;
  const pt = await page.evaluate(id => { const e = document.querySelector(`[data-audit-id="${id}"]`); if (!e) return null; e.scrollIntoView({ block: 'center' }); const r = e.getBoundingClientRect();
    for (const fy of [0.5, 0.3, 0.7, 0.15]) for (const fx of [0.5, 0.25, 0.75, 0.1]) { const x = r.left + r.width * fx, y = r.top + r.height * fy; const h = document.elementFromPoint(x, y); if (h && (h === e || e.contains(h)) && !(h !== e && h.closest('a[href],button,input,select') && e.contains(h.closest('a[href],button,input,select')))) return { x, y }; }
    for (const fy of [0.5, 0.3, 0.7]) for (const fx of [0.5, 0.25, 0.75]) { const x = r.left + r.width * fx, y = r.top + r.height * fy; const h = document.elementFromPoint(x, y); if (h && (h === e || e.contains(h))) return { x, y, inner: 1 }; }
    return null; }, c.id);
  if (!pt) return { ok: false, why: 'could not be reached by a tap (covered or off-screen)' };
  const b2 = await stateSig();
  await page.mouse.click(pt.x, pt.y);
  await page.waitForTimeout(150); await settle(3000);
  const after = await stateSig();
  const changed = after.hash !== b2.hash || after.sig !== b2.sig || after.opened > b2.opened || popups > pop0 || page.url().split('#')[0] !== SITE.replace(/#.*$/, '') && !page.url().startsWith(SITE);
  let destBad = null;
  if (after.hash !== b2.hash) { const nf = await page.evaluate(() => /That page doesn.t exist|^\s*(Not found|Page not found)\b|\bnot found\.\s*(Back|All counties)/i.test(((document.getElementById('app') || document.body).innerText || '').slice(0, 400))); if (nf) destBad = after.hash; }
  if (!page.url().startsWith(SITE.split('#')[0])) { await page.goto(SITE + route, { waitUntil: 'domcontentloaded' }); await settle(); }
  return { ok: changed, why: changed ? '' : 'tapping it does nothing (no page change, no new view)', dest: after.hash, destBad, inner: !!pt.inner };
}

async function audit(route, opts = {}) {
  if (timeLeft() < 20000) { cover('skipped (time budget)'); return null; }
  await go(route);
  visited.push(route);
  if (visited.length % 25 === 0) console.log(`  ${SHARD}@${WIDTH}: ${visited.length} pages, ${issues.length} issues, ${Math.round((Date.now() - T0) / 1000)}s`);
  let r;
  try { r = await checkPage(); } catch (e) { addIssue({ severity: 'medium', type: 'Audit could not read page', route, error: String(e.message || e).slice(0, 200) }); return null; }
  if (r.notFound) addIssue({ severity: 'high', type: 'Page not found', route, element: r.text.slice(0, 100), error: 'Route shows the "doesn\'t exist / not found" message', screenshot: await shot('notfound') });
  if (r.hscroll) addIssue({ severity: 'high', type: 'Sideways scroll', route, element: r.hscroll.els.join(' | '), error: `Page is ${r.hscroll.width}px wide on a ${r.hscroll.vw}px screen`, screenshot: await shot('hscroll') });
  for (const t of r.tokens) addIssue({ severity: 'high', type: 'Bad value shown', route, element: t.el, error: `"${t.token}" visible: ${t.text}`, screenshot: await shot('token') });
  for (const e of r.empty) addIssue({ severity: 'medium', type: 'Empty box', route, element: e, error: 'Visible box with nothing in it', screenshot: await shot('empty') });
  for (const d of r.dups) addIssue({ severity: 'medium', type: 'Duplicate in list', route, element: `${d.name}${d.list ? ' (list: ' + d.list + ')' : ''}`, error: 'Same entry appears twice in one list' });
  for (const t of r.termPast) { const k = ['Term already ended but shown as current', route, t].join('|'); if (![...seenKeys].some(x => x.startsWith(k))) addIssue({ severity: 'high', type: 'Term already ended but shown as current', route, element: t, error: 'End date is in the past' }); }
  for (const b of r.banned) addIssue({ severity: 'high', type: 'Banned label in AI text', route, element: `"${b.word}"`, error: b.ctx, screenshot: await shot('wording') });
  for (const b of (r.loaded || [])) addIssue({ severity: 'medium', type: 'Loaded label in non-AI text', route, element: `"${b.word}"`, error: b.ctx });
  for (const v of r.votes) addIssue({ severity: 'medium', type: 'Vote total not a whole number', route, element: v, error: 'Vote counts must be integers' });
  for (const i of r.imgs) addIssue({ severity: 'medium', type: 'Broken image', route, element: i.alt || '', error: i.src });
  for (const h of r.hrefs) if (!internalHrefs.has(h)) internalHrefs.set(h, route);
  if (r.aiBlocks) cover('pages with AI text checked');
  // unreachable controls
  for (const c of r.cands) {
    if (c.covered && c.kind !== 'link') addIssue({ severity: 'high', type: 'Dead tap', route, element: `${c.desc}`, error: `Looks tappable (${c.why}) but a tap can't reach it: ${c.covered}`, screenshot: await shot('covered', c.id) });
    else if (c.covered && c.kind === 'link' && !/off-screen/.test(c.covered)) addIssue({ severity: 'high', type: 'Dead tap', route, element: `${c.desc}`, error: `Link is covered by another element: ${c.covered}`, screenshot: await shot('covered', c.id) });
    if (c.kind === 'link' && (c.href === '#' || /^javascript:/i.test(c.href) || c.href === '')) addIssue({ severity: 'high', type: 'Dead tap', route, element: c.desc, error: `Link goes nowhere (href="${c.href}")` });
  }
  // tap tests: everything that is not a plain link
  const toTapAll = r.cands.filter(c => c.kind !== 'link');
  if (process.env.AUDIT_DEBUG) console.log(route, r.text.slice(0,80), JSON.stringify(r.cands.filter(c=>c.kind==='link').map(c=>c.desc.slice(0,50))), 'cands', r.cands.length, 'nonlink', JSON.stringify(toTapAll.map(c => [c.kind, c.why, c.covered, c.desc.slice(0, 60)])));
  let tested = 0;
  const toTap = r.cands.filter(c => !c.covered && (c.kind === 'box' || c.kind === 'pseudo' || (c.kind === 'button' && !RISKY.test(c.text + ' ' + c.desc))));
  for (const c of toTap) {
    if (timeLeft() < 30000) break;
    const sigKey = route.replace(/\/[^/]*\d[^/]*$/, '/*') + '|' + c.desc.replace(/"[^"]*"/, '').slice(0, 80) + (c.kind === 'box' ? '|' + route : '');
    if (c.kind === 'button' || c.why === 'pointer cursor') { const n = clickedSigs.get(sigKey) || 0; if (n >= 2) continue; clickedSigs.set(sigKey, n + 1); }
    if (tested >= (opts.maxTaps || 8)) break;
    tested++; cover('taps tested');
    // tags are lost after a re-render; re-check the page so ids are fresh
    if (tested > 1) { await go(route); await checkPage(); }
    const res = await tapTest(route, c);
    if (!res.ok) addIssue({ severity: 'high', type: 'Dead tap', route, element: c.desc, error: `Looks tappable (${c.why}) but ${res.why}`, screenshot: await shot('deadtap', c.id) });
    else if (res.destBad) addIssue({ severity: 'high', type: 'Tap leads to a missing page', route, element: c.desc, error: `Opens ${res.destBad}, which shows "not found"`, screenshot: await shot('tapnotfound') });
  }
  if (tested) await go(route); // leave the page as the visitor would see it, for whatever reads it next
  return r;
}

const qsHrefs = async (re) => page.evaluate(src => { const re = new RegExp(src); return Array.from(new Set(Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href')).filter(h => re.test(h)))); }, re.source);

// ---------- start ----------
for (let i = 0; ; i++) { try { await page.goto(SITE, { waitUntil: 'load', timeout: 60000 }); break; } catch (e) { if (i >= 3) throw e; console.log('retry start:', String(e.message).split('\n')[0]); await page.waitForTimeout(3000); } }
await settle(15000);
// wait for the hourly data to be applied (status line says "Updated …")
for (let i = 0; i < 40; i++) { const t = await page.evaluate(() => (document.getElementById('asof') || {}).innerText || ''); if (/Updated|Live data|Saved copy/.test(t) && !/Checking/.test(t)) break; await page.waitForTimeout(250); }
const meta = await page.evaluate(() => ({ status: (document.getElementById('asof') || {}).innerText || '', gh: window.GOV_LIVE && (window.GOV_LIVE.ghCheckedAt || window.GOV_LIVE.checkedAt) || null, via: window.GOV_LIVE && window.GOV_LIVE.via, state: window.GOV_LIVE && window.GOV_LIVE.state, sw: null }));
const D = await page.evaluate(() => { const G = window.GOV_DATA; const st = {}; for (const [k, s] of Object.entries(G.states)) st[k] = { name: s.name, exec: s.exec, sen: s.sen, rep: s.rep }; return { fed: G.fed, states: st, people: Object.fromEntries(Object.entries(G.people).map(([k, p]) => [k, { n: p.n, r: p.r, te: p.te, current: p.current, grp: p.grp }])) }; });

if (SHARD === 'A') {
  // run-level checks done once
  if (/Saved copy/.test(meta.status)) addIssue({ severity: 'high', type: 'Stale data', route: '#/', element: meta.status, error: 'App is not showing the hourly "Updated …" line (it fell back to a saved copy)' });
  if (meta.gh) { const age = (Date.now() - meta.gh) / 3600000; if (age > 48) addIssue({ severity: 'high', type: 'Stale data', route: '#/', element: meta.status, error: `"Updated" time is ${age.toFixed(0)} hours old (limit 48)` }); }
  const cur = new Set([D.fed.president, D.fed.vp, ...D.fed.cabinet]); for (const s of Object.values(D.states)) [...s.exec, ...s.sen, ...s.rep].forEach(x => cur.add(x));
  for (const id of cur) { const p = D.people[id]; if (!p || !p.te) continue; const m = String(p.te).match(/^([A-Z][a-z]+ \d{1,2}, \d{4})/); if (m && new Date(m[1]) < new Date(new Date().toISOString().slice(0, 10))) addIssue({ severity: 'high', type: 'Term already ended but shown as current', route: '#/p/' + id, element: `Term ends ${p.te}`, error: `${p.n} (${p.r}): end date is in the past` }); }
  // dup people across the whole officials data (same name twice in one state's list)
  for (const [ab, s] of Object.entries(D.states)) { const names = [...s.sen, ...s.rep].map(i => D.people[i] && D.people[i].n); const d = names.filter((n, i) => n && names.indexOf(n) !== i); for (const n of d) addIssue({ severity: 'medium', type: 'Duplicate in list', route: `#/s/${ab}/leg`, element: n, error: 'Same person listed twice in this state\'s Congress delegation' }); }
  for (const r of ['#/', '#/federal', '#/federal/presidents']) await audit(r, { maxTaps: 6 });
  const fedIds = [D.fed.president, D.fed.vp, ...D.fed.cabinet];
  for (const id of fedIds) { await audit('#/p/' + id); cover('federal people'); }
  for (const id of pick(D.fed.presidents.filter(x => x !== D.fed.president), 3)) { await audit('#/p/' + id); cover('past presidents'); }
  const sens = Object.values(D.states).flatMap(s => s.sen);
  for (const id of sens) { await audit('#/p/' + id, { maxTaps: 4 }); cover('senators'); }
  for (const ab of ['OH', ...pick(Object.keys(D.states).filter(x => x !== 'OH'), 2)]) for (const br of ['exec', 'leg', 'jud']) { await audit(`#/s/${ab}/${br}`, { maxTaps: 4 }); cover('state pages'); }
  // election tab
  await audit('#/election', { maxTaps: 6 });
  for (const m of ['senate', 'house', 'gov', 'mayor']) { await audit('#/election/' + m, { maxTaps: 4 }); cover('election views'); const sheets = (await qsHrefs(new RegExp('^#/election/' + m + '/[A-Za-z0-9-]+'))); for (const h of pick(sheets, 2)) { await audit(h, { maxTaps: 3 }); cover('election sheets'); } }
}
if (SHARD === 'B') {
  const reps = Object.values(D.states).flatMap(s => s.rep);
  for (const id of pick(reps, 60)) { await audit('#/p/' + id, { maxTaps: 4 }); cover('house members'); }
  const govs = Object.values(D.states).map(s => s.exec.find(i => /^Governor of/.test(D.people[i] && D.people[i].r || ''))).filter(Boolean);
  for (const id of govs) { await audit('#/p/' + id, { maxTaps: 4 }); cover('governors'); }
  // Local: Ohio -> Cuyahoga -> University Heights always, plus 5 random states
  const states = ['OH', ...pick(Object.keys(D.states).filter(x => x !== 'OH'), 5)];
  for (const ab of states) {
    await audit(`#/s/${ab}/local`, { maxTaps: 3 }); cover('local states');
    const counties = await qsHrefs(new RegExp(`^#/s/${ab}/local/[0-9A-Za-z]+$`));
    const cf = ab === 'OH' ? (counties.find(h => h.endsWith('/39035')) || counties[0]) : pick(counties, 1)[0];
    if (!cf) { addIssue({ severity: 'high', type: 'Local tab empty', route: `#/s/${ab}/local`, error: 'No counties listed' }); continue; }
    await audit(cf, { maxTaps: 3 }); cover('counties');
    // county officials (if any) -> one
    const cOff = (await qsHrefs(new RegExp(`^${cf.replace(/[/#]/g, m => '\\' + m)}/o/\\d+$`)));
    for (const h of pick(cOff, 1)) { await audit(h, { maxTaps: 4 }); cover('local officials'); }
    const places = await page.evaluate(cf => Array.from(document.querySelectorAll('a.row[href]')).filter(a => a.getAttribute('href').startsWith(cf + '/') && !/\/o\/|\/leg\//.test(a.getAttribute('href'))).map(a => ({ h: a.getAttribute('href'), mayor: /Mayor|Council|Trustee|Supervisor/i.test(a.innerText), n: a.innerText.split('\n')[0] })), cf);
    let pl = ab === 'OH' ? places.find(p => /University Heights/.test(p.n)) : null;
    if (!pl) pl = pick(places.filter(p => p.mayor), 1)[0] || pick(places, 1)[0];
    if (!pl) { addIssue({ severity: 'medium', type: 'Local tab empty', route: cf, error: 'County shows no cities or towns' }); continue; }
    await audit(pl.h, { maxTaps: 4 }); cover('cities');
    const offs = await qsHrefs(new RegExp(`^${pl.h.replace(/[/#]/g, m => '\\' + m)}/(o|leg)/`));
    const sel = ab === 'OH' ? [offs[0], ...pick(offs.slice(1), 2)].filter(Boolean) : pick(offs, 3);
    for (const h of sel) { await audit(h, { maxTaps: 4 }); cover('local officials'); }
    // the federal/state reps on the city page must link to their pages
    const repRows = await qsHrefs(/^#\/p\//); for (const h of pick(repRows, 1)) { await audit(h, { maxTaps: 3 }); cover('city → rep pages'); }
  }
  await audit('#/voter', { maxTaps: 4 });
}
if (SHARD === 'T') {
  // on-demand: just the routes given (comma separated) in AUDIT_ROUTES
  for (const r of (process.env.AUDIT_ROUTES || '#/').split(',').map(x => x.trim()).filter(Boolean)) await audit(r, { maxTaps: 12 });
}
if (SHARD === 'C') {
  // the sign-in screen, exactly as a signed-out visitor sees it (loaded only; nothing is typed or tapped)
  {
    const gctx = await browser.newContext({ viewport: { width: WIDTH, height: 800 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
    const gp = await gctx.newPage(); const gerr = [];
    gp.on('pageerror', e => gerr.push(String(e.message || e).split('\n')[0]));
    curRoute = '(sign-in screen)';
    try {
      await gp.goto(SITE, { waitUntil: 'load', timeout: 60000 }); await gp.waitForTimeout(3500);
      const g = await gp.evaluate(() => { const gate = document.getElementById('gate'); const vw = document.documentElement.clientWidth; const sw = document.documentElement.scrollWidth;
        return { shown: !!gate && getComputedStyle(gate).display !== 'none', text: gate ? gate.innerText.slice(0, 200) : '', hs: sw > vw + 1 ? sw : 0, vw, broken: Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0 && i.src && !/^data:/.test(i.src)).map(i => i.src), loading: !!gate && /Loading…/.test(gate.innerText), hasForm: !!(gate && gate.querySelector('form, input[type=email]')) }; });
      cover('sign-in screen checked');
      if (!g.shown) addIssue({ severity: 'medium', type: 'Sign-in screen', route: '(sign-in screen)', error: 'Signed-out visitors did not see the sign-in screen' });
      else if (g.loading || !g.hasForm) addIssue({ severity: 'high', type: 'Sign-in screen', route: '(sign-in screen)', element: g.text.replace(/\s+/g, ' ').slice(0, 120), error: 'Sign-in form never appeared (stuck on "Loading…" or an error) after 3.5 s', screenshot: null });
      if (g.hs) addIssue({ severity: 'high', type: 'Sideways scroll', route: '(sign-in screen)', error: `Sign-in screen is ${g.hs}px wide on a ${g.vw}px screen` });
      for (const b of g.broken) addIssue({ severity: 'medium', type: 'Broken image', route: '(sign-in screen)', error: b });
      for (const e of gerr) addIssue({ severity: 'high', type: 'JavaScript error', route: '(sign-in screen)', error: e });
    } catch (e) { addIssue({ severity: 'high', type: 'Sign-in screen', route: '(sign-in screen)', error: 'Could not load: ' + String(e.message || e).slice(0, 150) }); }
    await gctx.close();
  }
  await audit('#/more', { maxTaps: 6 });
  await audit('#/constitution', { maxTaps: 4 });
  const cons = await qsHrefs(/^#\/constitution\/[^?]+$/);
  for (const h of cons) { await audit(h, { maxTaps: 3 }); cover('constitution pages'); }
  await audit('#/declaration', { maxTaps: 4 }); cover('declaration');
  await audit('#/federalist', { maxTaps: 4 });
  const fed = await qsHrefs(/^#\/federalist\/\d+$/);
  if (fed.length !== 85) addIssue({ severity: 'medium', type: 'Missing content', route: '#/federalist', element: `${fed.length} papers listed`, error: 'Expected 85 Federalist Papers' });
  for (const h of pick(fed, 10)) { await audit(h, { maxTaps: 3 }); cover('federalist papers'); }
  await audit('#/learn', { maxTaps: 4 });
  const learn = await qsHrefs(/^#\/learn\/.+/);
  for (const h of pick(learn, 8)) { await audit(h, { maxTaps: 3 }); cover('learn/role pages'); }
  for (const r of ['#/about', '#/account', '#/bills/tracked']) await audit(r, { maxTaps: 2 });
  await audit('#/bills', { maxTaps: 4 });
  const bills = await qsHrefs(/^#\/bill\//);
  if (!bills.length) addIssue({ severity: 'high', type: 'Missing content', route: '#/bills', error: 'Bills list shows no bills' });
  for (const h of pick(bills, 10)) { await audit(h, { maxTaps: 3 }); cover('bills'); }
  await audit('#/bills/passed', { maxTaps: 3 });
  const passed = await qsHrefs(/^#\/bill\//); for (const h of pick(passed, 2)) { await audit(h, { maxTaps: 2 }); cover('bills'); }
  // Executive Orders: only once the tab exists
  await go('#/bills');
  const eoTab = await page.evaluate(() => { const a = Array.from(document.querySelectorAll('a[href], button')).find(e => /exec(utive)?\.? ?orders?/i.test(e.innerText || '')); return a ? (a.getAttribute('href') || '') : null; });
  if (eoTab === null) cover('exec orders: tab not on the site yet (skipped)');
  else {
    if (eoTab.startsWith('#/')) await audit(eoTab, { maxTaps: 4 });
    else { await page.evaluate(() => { const a = Array.from(document.querySelectorAll('a[href], button')).find(e => /exec(utive)?\.? ?orders?/i.test(e.innerText || '')); a.click(); }); await settle(); }
    const eos = await page.evaluate(() => Array.from(new Set(Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href')).filter(h => /^#\/(eo|bill\/eo|executive|exec)/i.test(h)))));
    if (!eos.length) addIssue({ severity: 'medium', type: 'Missing content', route: eoTab || '#/bills', error: 'Exec Orders tab shows no orders' });
    for (const h of pick(eos, 5)) { await audit(h, { maxTaps: 3 }); cover('exec orders'); }
  }
}

// ---------- in-app links seen but not visited: do they open a real page? ----------
const vset = new Set(visited);
const extra = pick(Array.from(internalHrefs.keys()).filter(h => !vset.has(h) && !/^#\/(account|admin)/.test(h)), 40);
for (const h of extra) {
  if (timeLeft() < 25000) break;
  await go(h); cover('in-app links spot-checked');
  const nf = await page.evaluate(() => /That page doesn.t exist|^\s*(Not found|Page not found)\b|\bnot found\.\s*(Back|All counties)/i.test(((document.getElementById('app') || document.body).innerText || '').slice(0, 400)));
  if (nf) addIssue({ severity: 'high', type: 'Broken in-app link', route: internalHrefs.get(h), element: h, error: `Link opens a "not found" page`, screenshot: await shot('brokenlink') });
}

const result = { shard: SHARD, width: WIDTH, site: SITE, seed: SEED, startedAt: new Date(T0).toISOString(), seconds: Math.round((Date.now() - T0) / 1000), pages: visited.length, coverage, status: meta, issues };
fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(result, null, 1));
console.log(`shard ${SHARD} @${WIDTH}px: ${visited.length} pages, ${issues.length} issues, ${result.seconds}s`);
await browser.close();
