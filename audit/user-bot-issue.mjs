// Opens, updates or closes the ONE "User bot: N problems found" issue from out/user-bot/results.json (run by user-bot.yml).
// Needs GH_TOKEN, GITHUB_REPOSITORY, RC, RUN_URL; optional ART_URL (screenshots artifact) and SHOT_BASE (raw URL of the screenshots branch).
import fs from 'node:fs';
const repo = process.env.GITHUB_REPOSITORY, tok = process.env.GH_TOKEN, RUN = process.env.RUN_URL || '';
const api = async (p, o = {}) => { const r = await fetch('https://api.github.com/repos/' + repo + p, { ...o, headers: { authorization: 'Bearer ' + tok, accept: 'application/vnd.github+json', 'content-type': 'application/json' }, signal: AbortSignal.timeout(30000) });
  if (!r.ok) throw new Error(p + ' -> HTTP ' + r.status + ' ' + (await r.text()).slice(0, 300)); return r.status === 204 ? null : r.json(); };
let res = null; try { res = JSON.parse(fs.readFileSync(process.argv[2] || 'out/user-bot/results.json', 'utf8')); } catch {}
const rc = String(process.env.RC || '');
const failed = res ? res.results.filter(r => !r.ok) : [];
const n = res ? failed.length : 1;
const pass = res && rc === '0' && !failed.length;
const list = await api('/issues?state=all&per_page=100&sort=created&direction=desc');
const mine = list.filter(i => !i.pull_request && /^User bot:/.test(i.title));
const open = mine.find(i => i.state === 'open');
if (pass) {
  if (open) {
    await api('/issues/' + open.number + '/comments', { method: 'POST', body: JSON.stringify({ body: '✅ All ' + res.results.length + ' user-bot steps pass now. Closing.\n\nRun: ' + RUN }) });
    await api('/issues/' + open.number, { method: 'PATCH', body: JSON.stringify({ state: 'closed', state_reason: 'completed' }) });
    console.log('closed #' + open.number);
  } else console.log('all pass; no open issue');
  process.exit(0);
}
const title = 'User bot: ' + n + ' problem' + (n === 1 ? '' : 's') + ' found';
let body = '**' + title + '** on ' + (res ? res.site : 'the live site') + ' (390×844 touch phone), ' + (res ? res.at : new Date().toISOString()) + '\n\nRun: ' + RUN + '\n\n';
if (!res) body += 'The bot stopped before it wrote any results (exit ' + rc + '). Open the run log.\n';
for (const f of failed) {
  body += '### ❌ ' + f.name + '\n' + (f.at ? 'Page: `' + f.at + '`\n\n' : '') + 'Error: ' + f.msg.replace(/\n/g, ' ') + '\n\n';
  if (f.shot) body += process.env.SHOT_BASE ? '<img src="' + process.env.SHOT_BASE + '/' + f.shot + '" width="260" alt="' + f.shot + '">\n\nScreenshot: ' + process.env.SHOT_BASE + '/' + f.shot + '\n\n'
    : 'Screenshot: `' + f.shot + '` in ' + (process.env.ART_URL || RUN) + '\n\n';
}
if (res) body += '<details><summary>Steps that passed (' + (res.results.length - failed.length) + ')</summary>\n\n' + res.results.filter(r => r.ok).map(r => '- ✅ ' + r.name + (r.msg ? ' — ' + r.msg : '')).join('\n') + '\n</details>\n';
body += '\n_Opened by .github/workflows/user-bot.yml. Updated on every failing run; closed when a run passes._';
if (open) {
  await api('/issues/' + open.number, { method: 'PATCH', body: JSON.stringify({ title, body }) });
  await api('/issues/' + open.number + '/comments', { method: 'POST', body: JSON.stringify({ body: '❌ ' + title + ' — ' + RUN + '\n\n' + failed.map(f => '- ' + f.name + ': ' + f.msg.slice(0, 200)).join('\n') }) });
  console.log('updated #' + open.number);
} else {
  const i = await api('/issues', { method: 'POST', body: JSON.stringify({ title, body }) });
  console.log('opened #' + i.number);
}
