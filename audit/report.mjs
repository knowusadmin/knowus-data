// KnowUS site audit: merge shard results -> audit/reports/latest.md, latest.json, history/<stamp>.md, issue body.
// Usage: node audit/report.mjs <results dir> [run url]
import fs from 'node:fs';
import path from 'node:path';

const IN = process.argv[2] || 'audit/out';
const RUN_URL = process.argv[3] || process.env.RUN_URL || '';
const REP = 'audit/reports';
fs.mkdirSync(path.join(REP, 'history'), { recursive: true });
const files = [];
(function walk(d) { if (!fs.existsSync(d)) return; for (const f of fs.readdirSync(d)) { const p = path.join(d, f); if (fs.statSync(p).isDirectory()) walk(p); else if (f === 'result.json') files.push(p); } })(IN);
const shards = files.map(f => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } }).filter(Boolean);
const SEV = { high: 0, medium: 1, low: 2 };

// merge the same problem seen at 390 and 360 into one entry
const merged = new Map();
for (const s of shards) for (const it of s.issues) {
  const k = [it.severity, it.type, it.route, it.element.replace(/data-audit-id="\d+"/, ''), it.error].join('|');
  const m = merged.get(k);
  if (m) { if (it.viewport && !m.viewports.includes(it.viewport)) m.viewports.push(it.viewport); if (!m.screenshot && it.screenshot) m.screenshot = it.screenshot; }
  else merged.set(k, { severity: it.severity, type: it.type, route: it.route, element: it.element, error: it.error, viewports: it.viewport ? [it.viewport] : [], screenshot: it.screenshot ? `screenshots/${it.screenshot.replace(/^shots\//, '')}` : null });
}
const issues = Array.from(merged.values()).sort((a, b) => SEV[a.severity] - SEV[b.severity] || a.type.localeCompare(b.type) || a.route.localeCompare(b.route));
const counts = { high: 0, medium: 0, low: 0 }; for (const i of issues) counts[i.severity]++;
const coverage = {}; let pages = 0, secs = 0;
for (const s of shards) { pages += s.pages || 0; secs = Math.max(secs, s.seconds || 0); for (const [k, v] of Object.entries(s.coverage || {})) { if (/\(hours\)|hours ago/.test(k)) coverage[k] = v; else coverage[k] = (coverage[k] || 0) + v; } }
const expected = ['A-390', 'A-360', 'B-390', 'B-360', 'C-390', 'C-360', 'data'];
const got = shards.map(s => s.shard === 'data' ? 'data' : `${s.shard}-${s.width}`);
const missing = expected.filter(e => !got.includes(e));
const now = new Date();
const stamp = now.toISOString().slice(0, 16).replace(':', '');
const status = shards.find(s => s.status && s.status.status);
let deadLinks = null;
for (const f of files) { const dl = path.join(path.dirname(f), 'dead-links.json'); if (fs.existsSync(dl)) { deadLinks = JSON.parse(fs.readFileSync(dl, 'utf8')); fs.writeFileSync(path.join(REP, 'dead-links.json'), JSON.stringify(deadLinks, null, 1)); } }
if (!deadLinks && fs.existsSync(path.join(REP, 'dead-links.json'))) deadLinks = JSON.parse(fs.readFileSync(path.join(REP, 'dead-links.json'), 'utf8'));
const summary = { generatedAt: now.toISOString(), site: shards[0] && shards[0].site, run: RUN_URL, pagesChecked: pages, longestShardSeconds: secs, shardsMissing: missing, counts, coverage, appStatusLine: status ? status.status.status : null, issues, deadLinks: deadLinks ? deadLinks.links : [] };
fs.writeFileSync(path.join(REP, 'latest.json'), JSON.stringify(summary, null, 1));

// ---------- markdown ----------
const esc = s => String(s || '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const groups = {}; for (const i of issues) (groups[i.severity] ||= {}, groups[i.severity][i.type] ||= []).push(i);
let md = `# KnowUS site audit — ${now.toISOString().replace('T', ' ').slice(0, 16)} UTC\n\n`;
md += `**${counts.high} high · ${counts.medium} medium · ${counts.low} low** — ${pages} page visits at 390 px and 360 px phone widths${RUN_URL ? ` · [this run](${RUN_URL}) (screenshots are in the run's artifacts)` : ''}\n\n`;
if (missing.length) md += `> ⚠️ Parts of the audit did not report: ${missing.join(', ')} — see the run log.\n\n`;
md += `Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).\n\n`;
if (!issues.length) md += `✅ No problems found.\n\n`;
for (const sev of ['high', 'medium', 'low']) {
  if (!groups[sev]) continue;
  md += `## ${sev[0].toUpperCase() + sev.slice(1)} (${counts[sev]})\n\n`;
  for (const [type, list] of Object.entries(groups[sev])) {
    md += `### ${type} — ${list.length}\n\n| Route | Element | Problem | Width | Screenshot |\n|---|---|---|---|---|\n`;
    const cap = sev === 'low' ? 25 : 60;
    for (const i of list.slice(0, cap)) md += `| \`${esc(i.route)}\` | ${esc(i.element).slice(0, 140)} | ${esc(i.error).slice(0, 220)} | ${i.viewports.join('/') || '—'} | ${i.screenshot ? '`' + i.screenshot + '`' : ''} |\n`;
    if (list.length > cap) md += `\n…and ${list.length - cap} more (all in \`latest.json\`).\n`;
    md += '\n';
  }
}
if (deadLinks && deadLinks.links.length) md += `## Dead source links on the running list (${deadLinks.links.length})\n\nEvery link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: \`audit/reports/dead-links.json\`.\n\n` + deadLinks.links.slice(0, 80).map(l => `- \`${l.route}\` → ${l.url} (HTTP ${l.status}, since ${l.firstSeen})`).join('\n') + (deadLinks.links.length > 80 ? `\n- …and ${deadLinks.links.length - 80} more` : '') + '\n\n';
md += `## What was covered\n\n` + Object.entries(coverage).map(([k, v]) => `- ${k}: ${v}`).join('\n') + '\n';
if (summary.appStatusLine) md += `- app status line: "${summary.appStatusLine}"\n`;
md += `\n_Live site: ${summary.site} · generated by \`.github/workflows/site-audit.yml\`_\n`;
fs.writeFileSync(path.join(REP, 'latest.md'), md);
fs.writeFileSync(path.join(REP, 'history', `${stamp}.md`), md);
// keep history small: last 120 reports (~30 days at 4 a day)
const hist = fs.readdirSync(path.join(REP, 'history')).filter(f => f.endsWith('.md')).sort();
for (const f of hist.slice(0, Math.max(0, hist.length - 120))) fs.unlinkSync(path.join(REP, 'history', f));
// index of runs
const idxP = path.join(REP, 'history.csv');
if (!fs.existsSync(idxP)) fs.writeFileSync(idxP, 'utc,high,medium,low,pages,run\n');
fs.appendFileSync(idxP, `${now.toISOString()},${counts.high},${counts.medium},${counts.low},${pages},${RUN_URL}\n`);

// ---------- GitHub issue body (high only, grouped) ----------
const hi = issues.filter(i => i.severity === 'high');
let body = `The scheduled site audit found **${hi.length} high-severity problem${hi.length === 1 ? '' : 's'}** on ${summary.site} (${counts.medium} medium, ${counts.low} low).\n\n`;
const hg = {}; for (const i of hi) (hg[i.type] ||= []).push(i);
for (const [t, list] of Object.entries(hg)) {
  body += `### ${t} (${list.length})\n`;
  for (const i of list.slice(0, 25)) body += `- \`${i.route}\` — ${esc(i.element).slice(0, 120)}: ${esc(i.error).slice(0, 200)}\n`;
  if (list.length > 25) body += `- …and ${list.length - 25} more\n`;
  body += '\n';
}
body += `Full report: [audit/reports/latest.md](https://github.com/${process.env.GITHUB_REPOSITORY || 'knowusadmin/knowus-data'}/blob/main/audit/reports/latest.md)${RUN_URL ? ` · [run + screenshots](${RUN_URL})` : ''}\n\nThis issue is updated by every audit run and closes itself when a run comes back clean.\n`;
fs.writeFileSync('audit-issue.md', body);
const outF = process.env.GITHUB_OUTPUT; if (outF) fs.appendFileSync(outF, `high=${hi.length}\ntotal=${issues.length}\nmedium=${counts.medium}\nlow=${counts.low}\nmissing=${missing.length}\n`);
console.log(`report: ${counts.high} high, ${counts.medium} medium, ${counts.low} low; missing shards: ${missing.join(',') || 'none'}`);
