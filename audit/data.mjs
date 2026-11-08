// KnowUS site audit: data + outbound link checks (no browser). Reads the LIVE site's data files and the GitHub data.
// Usage: node audit/data.mjs --out audit/out/data
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const OUT = args.out || 'audit/out/data';
const SITE = (process.env.AUDIT_SITE || 'https://knowus.sites.tab.bot/').replace(/\/?$/, '/');
const RAW = 'https://raw.githubusercontent.com/knowusadmin/knowus-data/main/';
const REPO = process.env.GITHUB_REPOSITORY || 'knowusadmin/knowus-data';
const SEED = process.env.AUDIT_SEED || new Date().toISOString().slice(0, 13);
const LINKS = +(process.env.AUDIT_LINKS || 200);
fs.mkdirSync(OUT, { recursive: true });
const T0 = Date.now();
const issues = []; const coverage = {};
const add = o => issues.push({ severity: o.severity, type: o.type, route: o.route || '', viewport: null, element: (o.element || '').slice(0, 200), error: (o.error || '').slice(0, 500), screenshot: null, shard: 'data' });
const cover = (k, n = 1) => { coverage[k] = (coverage[k] || 0) + n; };
function rng(s) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return () => { h += 0x6D2B79F5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const R = rng(SEED + ':data');
const pick = (arr, n) => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, n); };
const bust = () => '?audit=' + Date.now();
async function get(u, { json = false, timeout = 30000 } = {}) {
  const ac = new AbortController(); const t = setTimeout(() => ac.abort(), timeout);
  try { const r = await fetch(u, { signal: ac.signal, headers: { 'user-agent': 'KnowUS-SiteAudit/1.0 (+https://github.com/' + REPO + ')' } }); if (!r.ok) return { status: r.status, body: null }; return { status: r.status, body: json ? await r.json() : await r.text() }; }
  catch (e) { return { status: 0, body: null, err: String(e.message || e) }; } finally { clearTimeout(t); }
}

// ---------- wording: banned labels in AI-written text ----------
const BANNED = ['racist', 'racism', 'extremist', 'extremism', 'far-right', 'far-left', 'authoritarian', 'controversial', 'divisive', 'baseless', 'debunked', 'conspiracy', 'false claims', 'falsely claimed', 'falsely claims'];
const bannedRe = new RegExp('(^|[^a-z])(' + BANNED.map(w => w.replace('-', '[- ]?')).join('|') + ')(?=[^a-z]|$)', 'i');
function titleUse(t, i, len) {
  // an official title (an executive order, bill or law name) is quoted, not an AI label: Title Case words around the match, or inside quotes
  const w = t.slice(i, i + len); if (!/^[A-Z]/.test(w)) return false;
  const before = t.slice(Math.max(0, i - 60), i).trim().split(/\s+/).slice(-3), after = t.slice(i + len, i + len + 60).trim().split(/\s+/).slice(0, 3);
  const cap = x => /^[A-Z0-9“"'(]/.test(x) || /^(and|of|the|to|for|from|in|on|a|an|by|with)$/.test(x);
  const run = [...before, ...after].filter(Boolean); return run.length >= 2 && run.filter(cap).length >= run.length - 1;
}
function scanText(t, route, who, field) {
  if (typeof t !== 'string') return;
  const m = t.match(bannedRe); if (!m) return;
  if (titleUse(t, m.index + m[1].length, m[2].length)) return;
  add({ severity: 'high', type: 'Banned label in AI text', route, element: `${who} — "${m[2]}" (${field})`, error: t.slice(0, 300) });
}

const links = new Map(); // url -> where
const addLink = (u, where) => { if (typeof u !== 'string' || !/^https?:\/\//.test(u)) return; if (!links.has(u)) links.set(u, where); };

// officials data (what the app shows)
const dj = await get(SITE + 'data.js' + bust());
let G = null;
if (dj.body) { const ctx = { window: {} }; vm.runInNewContext(dj.body, ctx, { timeout: 5000 }); G = ctx.window.GOV_DATA; }
else add({ severity: 'high', type: 'Site file missing', route: 'data.js', error: 'HTTP ' + dj.status });
if (G) for (const [id, p] of Object.entries(G.people)) { addLink(p.u, '#/p/' + id); if (p.w && p.w.startsWith('~')) addLink('https://en.wikipedia.org/wiki/' + p.w.slice(1), '#/p/' + id); else addLink(p.w, '#/p/' + id); }

// short AI profiles
const pj = await get(SITE + 'data/profiles.json' + bust(), { json: true });
if (pj.body && pj.body.people) {
  for (const [id, p] of Object.entries(pj.body.people)) {
    cover('AI profiles scanned');
    (p.positions || []).forEach(t => scanText(t, '#/p/' + id, p.n, 'Key positions'));
    (p.inOffice || []).forEach(t => scanText(t, '#/p/' + id, p.n, 'In office'));
    (p.src || []).forEach(u => addLink(u, '#/p/' + id));
  }
} else add({ severity: 'high', type: 'Site file missing', route: 'data/profiles.json', error: 'HTTP ' + pj.status });

// full profiles (positions pages), when the site has them
const fi = await get(SITE + 'data/profiles-full/index.json' + bust(), { json: true });
if (fi.body) {
  const ids = Array.isArray(fi.body) ? fi.body : Array.isArray(fi.body.ids) ? fi.body.ids : Object.keys(fi.body.people || fi.body);
  const sample = Array.from(new Set(['pr47', ...(process.env.AUDIT_FULL_ALL ? ids : pick(ids, 150))])).filter(i => ids.includes(i));
  await Promise.all(sample.map(async id => {
    const r = await get(SITE + 'data/profiles-full/' + id + '.json', { json: true });
    if (!r.body) { add({ severity: 'high', type: 'Site file missing', route: '#/p/' + id + '/positions', error: 'profiles-full/' + id + '.json → HTTP ' + r.status }); return; }
    cover('full profiles scanned');
    const walk = (o, k) => { if (typeof o === 'string') { if (!/^(q|quote|quotes|u|url|src|source|link|href|id|via)$/i.test(k || '') && !/^https?:\/\//.test(o)) scanText(o, '#/p/' + id + '/positions', r.body.n || id, k || 'text'); else if (/^(u|url|src|source|link|via)$/i.test(k) || /^https?:\/\//.test(o)) addLink(o, '#/p/' + id + '/positions'); } else if (Array.isArray(o)) o.forEach(x => walk(x, k)); else if (o && typeof o === 'object') for (const [kk, v] of Object.entries(o)) walk(v, kk); };
    walk(r.body, '');
  }));
} else cover('full profiles: not on the site yet');

// local officials + their AI text
const states = G ? Object.keys(G.states) : [];
await Promise.all(states.map(async ab => {
  const [loc, ai] = await Promise.all([get(SITE + 'data/local/' + ab + '.json', { json: true }), get(SITE + 'data/local-ai/' + ab + '.json', { json: true })]);
  if (!loc.body) { if (loc.status !== 404 || ab !== 'DC') add({ severity: 'high', type: 'Site file missing', route: `#/s/${ab}/local`, error: `data/local/${ab}.json → HTTP ${loc.status}` }); return; }
  const J = loc.body; cover('local states scanned');
  const placeRoute = pk => { const e = J.places[pk]; return e ? `#/s/${ab}/local/${e.c[0]}/${pk}` : `#/s/${ab}/local`; };
  for (const c of J.counties || []) { addLink(c.w, `#/s/${ab}/local/${c.f}`); (c.o || []).forEach(o => addLink(o.u, `#/s/${ab}/local/${c.f}`)); }
  for (const [pk, e] of Object.entries(J.places || {})) { addLink(e.w, placeRoute(pk)); (e.o || []).forEach(o => addLink(o.u, placeRoute(pk))); }
  if (ai.body && ai.body.people) for (const [k, p] of Object.entries(ai.body.people)) {
    cover('local AI profiles scanned');
    const pk = k.split('-')[0]; const rt = J.places[pk] ? placeRoute(pk) : `#/s/${ab}/local/${pk.replace(/^c/, '')}`;
    for (const f of ['pos', 'rec']) (p[f] || []).forEach(x => { scanText(x.t, rt, `${p.n} (${k})`, f === 'pos' ? 'Key positions' : 'Record'); addLink(x.u, rt); });
  }
}));

// ---------- election vote totals must be whole numbers ----------
const ed = await get(SITE + 'election-data.js' + bust());
if (ed.body) {
  const ctx = { window: {} }; try { vm.runInNewContext(ed.body, ctx, { timeout: 5000 }); } catch {}
  let bad = 0, n = 0;
  const walk = (o, k, p) => { if (typeof o === 'number' && /^(v|votes?|totalVotes|total)$/i.test(k || '')) { n++; if (!Number.isInteger(o)) { bad++; if (bad <= 20) add({ severity: 'medium', type: 'Vote total not a whole number', route: '#/election', element: p, error: String(o) }); } } else if (Array.isArray(o)) o.forEach((x, i) => walk(x, k, p + '[' + i + ']')); else if (o && typeof o === 'object') for (const [kk, v] of Object.entries(o)) walk(v, kk, p + '.' + kk); };
  walk(ctx.window.KUS_ELECTION_SNAPSHOT, '', 'snapshot'); cover('vote totals checked', n);
}

// ---------- freshness of the hourly data ----------
const meta = await get(RAW + 'data/officials-meta.json' + bust(), { json: true });
if (meta.body && meta.body.checkedAt) { const age = (Date.now() - Date.parse(meta.body.checkedAt)) / 3600000; coverage['officials data age (hours)'] = Math.round(age); if (age > 48) add({ severity: 'high', type: 'Stale data', route: '#/', element: 'officials-meta.json checkedAt ' + meta.body.checkedAt, error: `The app's "Updated" time is ${Math.round(age)} hours old (limit 48)` }); }
else add({ severity: 'high', type: 'Stale data', route: '#/', error: 'officials-meta.json unreadable (HTTP ' + meta.status + ')' });
const runs = await get(`https://api.github.com/repos/${REPO}/actions/workflows/refresh.yml/runs?per_page=6`, { json: true });
if (runs.body && runs.body.workflow_runs) {
  const done = runs.body.workflow_runs.filter(r => r.status === 'completed');
  const ok = done.find(r => r.conclusion === 'success');
  if (!ok) add({ severity: 'high', type: 'Hourly refresh failing', route: '(GitHub Actions)', element: 'refresh.yml', error: `Last ${done.length} runs did not succeed` });
  else { const age = (Date.now() - Date.parse(ok.updated_at)) / 3600000; coverage['last good hourly refresh (hours ago)'] = +age.toFixed(1); if (age > 6) add({ severity: 'high', type: 'Hourly refresh failing', route: '(GitHub Actions)', element: 'refresh.yml', error: `Last successful run was ${Math.round(age)} hours ago` }); }
}
const bi = await get(RAW + 'data/bills/index.json' + bust(), { json: true });
if (bi.body) { const ts = bi.body.generatedAt || bi.body.updated || bi.body.checkedAt; if (ts) { const age = (Date.now() - Date.parse(ts)) / 3600000; coverage['bills index age (hours)'] = Math.round(age); if (age > 48) add({ severity: 'medium', type: 'Stale data', route: '#/bills', element: 'bills/index.json ' + ts, error: `Bills index is ${Math.round(age)} hours old` }); } }

// ---------- outbound source links: sample, HEAD then GET ----------
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
async function probe(u) {
  const once = async (method) => { const ac = new AbortController(); const t = setTimeout(() => ac.abort(), 20000); try { const r = await fetch(u, { method, redirect: 'follow', signal: ac.signal, headers: { 'user-agent': UA, accept: 'text/html,application/xhtml+xml,*/*;q=0.8', 'accept-language': 'en-US,en;q=0.9' } }); try { await r.body?.cancel(); } catch {} return r.status; } catch (e) { return 0; } finally { clearTimeout(t); } };
  let s = await once('HEAD');
  if (s === 0 || s === 405 || s === 403 || s === 400 || s === 501 || s >= 500 || s === 404) s = await once('GET');
  if (s >= 500 || s === 0) { await new Promise(r => setTimeout(r, 3000)); s = await once('GET'); }
  return s;
}
const all = Array.from(links.keys());
// known dead links from earlier runs are re-checked every run (they drop off the list once they answer again)
let known = [];
try { known = JSON.parse(fs.readFileSync(process.env.AUDIT_DEAD_FILE || 'audit/reports/dead-links.json', 'utf8')).links || []; } catch {}
const knownSet = new Set(known.map(k => k.url));
const kinds = (process.env.AUDIT_LINK_KINDS || '').split(',').filter(Boolean);
const pool = kinds.length ? all.filter(u => kinds.some(k => (links.get(u) || '').includes(k === 'person' ? '#/p/' : k === 'local' ? '/local' : k))) : all;
const recheck = known.slice().sort((a, b) => String(a.lastSeen).localeCompare(String(b.lastSeen))).slice(0, +(process.env.AUDIT_RECHECK || 300)).map(k => k.url);
const sample = Array.from(new Set([...(process.env.AUDIT_LINKS === 'all' ? pool : pick(pool.filter(u => !knownSet.has(u)), LINKS)), ...recheck]));
cover('outbound links known', all.length);
const results = []; let i = 0;
await Promise.all(Array.from({ length: +(process.env.AUDIT_LINK_CONC || 12) }, async () => { while (i < sample.length) { const u = sample[i++]; const s = await probe(u); results.push([u, s]); } }));
const byHost = {};
for (const [u, s] of results) {
  const where = links.get(u) || (known.find(k => k.url === u) || {}).route || '';
  if (s === 404 || s === 410) add({ severity: 'medium', type: 'Broken source link', route: where, element: u, error: 'HTTP ' + s });
  else if (s >= 500) add({ severity: 'medium', type: 'Source link server error', route: where, element: u, error: 'HTTP ' + s + ' (twice)' });
  else if (s === 0) { byHost[new URL(u).host] = (byHost[new URL(u).host] || 0) + 1; add({ severity: 'low', type: 'Source link unreachable', route: where, element: u, error: 'No answer within 20 s (may block automated checks)' }); }
}
cover('outbound links checked', results.length);
// the running list of dead source links (404/410/5xx), kept between runs
const prev = new Map(known.map(k => [k.url, k]));
const dead = results.filter(([, s]) => s === 404 || s === 410 || s >= 500).map(([u, s]) => ({ url: u, status: s, route: links.get(u) || (prev.get(u) || {}).route || '', firstSeen: (prev.get(u) || {}).firstSeen || new Date().toISOString().slice(0, 10), lastSeen: new Date().toISOString().slice(0, 10) }));
// known dead links that were not re-checked this run (should not happen) stay on the list
for (const k of known) if (!results.some(([u]) => u === k.url)) dead.push(k);
dead.sort((a, b) => a.route.localeCompare(b.route));
fs.writeFileSync(path.join(OUT, 'dead-links.json'), JSON.stringify({ updated: new Date().toISOString(), note: 'Source and website links that answered 404/410 or a server error (5xx). Re-checked every audit run; a link drops off when it answers again.', count: dead.length, links: dead }, null, 1));
cover('dead links on the running list', dead.length);
cover('outbound links OK', results.filter(([, s]) => s > 0 && s < 400).length);
cover('outbound links refused bots (401/403/429, not counted as broken)', results.filter(([, s]) => [401, 403, 429, 999].includes(s)).length);

fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify({ shard: 'data', width: null, site: SITE, seed: SEED, startedAt: new Date(T0).toISOString(), seconds: Math.round((Date.now() - T0) / 1000), pages: 0, coverage, issues }, null, 1));
console.log(`data: ${issues.length} issues, ${results.length} links, ${Math.round((Date.now() - T0) / 1000)}s`);
