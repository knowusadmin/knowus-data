// KnowUS officials refresh (runs hourly in GitHub Actions; no AI, no keys).
// Runs the app's own live.js (the same code phones run) in Node against the app's baked data.js, so the
// result has exactly the app's shapes. Sources (all public): unitedstates/congress-legislators (Congress),
// Wikipedia current-officeholder tables (governors, lieutenant governors, attorneys general, secretaries of
// state, Cabinet), Wikidata (backup), Wikipedia page summaries (descriptions/photos for new people).
// Writes:
//   data/officials.json          = window.GOV_DATA after the live merge (identical shape to data.js)
//   data/officials-overlay.json  = the overlay live.js caches on phones (localStorage 'wio-live-v1:'+asOf)
//   data/officials-meta.json     = run metadata (which sources answered, what changed, base used)
import { JSDOM } from 'jsdom';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const SITE = process.env.KNOWUS_SITE || 'https://knowus.sites.tab.bot/';
const UA = 'KnowUS-data-refresh/1.0 (https://github.com/knowusadmin/knowus-data; knowusadmin@gmail.com)';
const BASE_DIR = path.join(ROOT, 'base');
const OUT = path.join(ROOT, 'data');

async function getText(url) {
  const r = await fetch(url + (url.includes('?') ? '&' : '?') + 'x=' + Date.now(), { headers: { 'user-agent': UA }, signal: AbortSignal.timeout(30000) });
  if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url);
  return r.text();
}

// 1) base = the app's current data.js + live.js from the live site; the committed copy in base/ is the fallback
async function base(name, check) {
  const file = path.join(BASE_DIR, name);
  try {
    const t = await getText(SITE + name);
    check(t);
    if (!fs.existsSync(file) || fs.readFileSync(file, 'utf8') !== t) fs.writeFileSync(file, t);
    return { text: t, from: SITE + name };
  } catch (e) {
    console.log('site copy of', name, 'unavailable (' + e.message + '); using base/' + name);
    return { text: fs.readFileSync(file, 'utf8'), from: 'base/' + name };
  }
}
const dataJs = await base('data.js', t => { if (!/^window\.GOV_DATA=\{/.test(t) || !t.includes('"people"')) throw new Error('unexpected data.js'); });
const liveJs = await base('live.js', t => { if (!t.includes('GOV_LIVE') || !t.includes('function refresh')) throw new Error('unexpected live.js'); });

// 2) a minimal browser for live.js
const dom = new JSDOM('<!doctype html><html><body></body></html>', { url: SITE, runScripts: 'outside-only' });
const w = dom.window;
w.fetch = (url, opt = {}) => {
  const o = { ...opt, headers: { ...(opt.headers || {}), 'user-agent': UA } };
  delete o.cache; delete o.credentials;
  return fetch(url, o);
};
w.AbortController = globalThis.AbortController;
w.eval(dataJs.text);
const asOf = w.GOV_DATA.asOf;
w.eval(liveJs.text);
const L = w.GOV_LIVE;
if (!L || typeof L.refresh !== 'function') throw new Error('live.js did not start');
await new Promise(r => setTimeout(r, 200));
await L.refresh(true);
const KEY = 'wio-live-v1:' + asOf;
const overlay = JSON.parse(w.localStorage.getItem(KEY) || 'null');
const parts = (overlay && overlay.parts) || L.parts || {};
console.log('state:', L.state, 'error:', L.error || '-', 'parts:', JSON.stringify(parts));
if (L.state !== 'live' || !overlay) { console.error('::error::officials refresh failed: ' + (L.error || L.state)); process.exit(1); }
const failed = Object.keys(parts).filter(k => parts[k] === 'failed');
if (!Object.keys(parts).length || failed.length) {
  // a source that did not answer would put the app's older baked copy back for that group; keep the previous files instead
  console.error('::error::officials source(s) failed: ' + (failed.join(', ') || 'none answered') + ' (previous files kept)'); process.exit(1);
}

// 3) write (stable: no timestamps inside officials.json, so it only changes when an official changes)
const D = JSON.parse(JSON.stringify(w.GOV_DATA));
const ppl = Object.keys(D.people).length;
if (ppl < 1000 || Object.keys(D.states).length !== 50) { console.error('::error::merged data looks wrong: people', ppl); process.exit(1); }
// sanity guard: a group that shrinks by more than 10% (or empties) against the last committed file is a broken parse
function counts(G) {
  const st = Object.values(G.states);
  const sum = k => st.reduce((n, s) => n + (s[k] || []).length, 0);
  const gov = st.filter(s => (s.exec || []).some(id => G.people[id] && /^Governor of /.test(G.people[id].r))).length;
  return { senators: sum('sen'), representatives: sum('rep'), stateExecutives: sum('exec'), governors: gov,
           cabinet: G.fed.cabinet.filter(id => G.people[id]).length, president: G.people[G.fed.president] ? 1 : 0, vp: G.people[G.fed.vp] ? 1 : 0,
           people: Object.keys(G.people).length };
}
const now = counts(D);
const prevFile = path.join(OUT, 'officials.json');
if (fs.existsSync(prevFile)) {
  const prev = counts(JSON.parse(fs.readFileSync(prevFile, 'utf8')));
  const bad = Object.keys(prev).filter(k => prev[k] > 0 && (now[k] === 0 || now[k] < prev[k] * 0.9));
  if (bad.length) { console.error('::error::officials sanity guard: ' + bad.map(k => k + ' ' + prev[k] + '->' + now[k]).join(', ') + ' (previous files kept)'); process.exit(1); }
}
for (const [k, v] of Object.entries(now)) if (!v) { console.error('::error::officials sanity guard: ' + k + ' is empty'); process.exit(1); }
console.log('counts', JSON.stringify(now));
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'officials.json'), JSON.stringify(D));
fs.writeFileSync(path.join(OUT, 'officials-overlay.json'), JSON.stringify(overlay));
fs.writeFileSync(path.join(OUT, 'officials-meta.json'), JSON.stringify({
  checkedAt: new Date(overlay.checkedAt).toISOString(), sources: { congress: 'https://unitedstates.github.io/congress-legislators/legislators-current.json', governors: 'https://en.wikipedia.org/wiki/List_of_current_United_States_governors', lieutenantGovernors: 'https://en.wikipedia.org/wiki/List_of_current_United_States_lieutenant_governors', attorneysGeneral: 'https://en.wikipedia.org/wiki/State_attorney_general', secretariesOfState: 'https://en.wikipedia.org/wiki/Secretary_of_state_(U.S._state_government)', cabinetAndVP: 'https://en.wikipedia.org/wiki/Cabinet_of_the_United_States', backup: 'Wikidata (query.wikidata.org)', president: 'Wikidata (next numbered presidency only)' }, asOf, parts, changes: overlay.changes || [],
  base: { dataJs: dataJs.from, liveJs: liveJs.from },
  counts: { ...now, liveOverrides: Object.keys(overlay.people || {}).length },
  fed: { president: D.people[D.fed.president] && D.people[D.fed.president].n, vp: D.people[D.fed.vp] && D.people[D.fed.vp].n,
         cabinet: D.fed.cabinet.map(id => D.people[id] ? D.people[id].r + ': ' + D.people[id].n : id) }
}, null, 1));
console.log('people', ppl, 'live overrides', Object.keys(overlay.people || {}).length, 'changes', (overlay.changes || []).length);
console.log('cabinet:', D.fed.cabinet.map(id => D.people[id] && D.people[id].n).join(', '));
process.exit(0);
