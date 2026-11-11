// Browser pass for sources that wall plain fetches (data/capture/needs-browser.json). Free: Playwright's Chromium on the
// Actions runner. For each queued source of an election 0-45 days out: open the page like a person would, collect the
// links the registry's linkRegex names (or the file itself), and save each file with the page's own cookies.
// Output: <out>/<key-slug>/files/* + list.json ({url, file, status}); capture.py ingest turns that into a manifest.
// Usage: node scripts/capture/browser_fetch.mjs data/capture <outdir> [maxFilesPerSource]
import fs from 'node:fs'; import path from 'node:path';
let chromium; try { ({ chromium } = await import('playwright')); } catch { ({ chromium } = await import('playwright-core')); }
const [cap, out, maxArg] = process.argv.slice(2); const MAX = +(maxArg || 3000);
const queue = JSON.parse(fs.readFileSync(path.join(cap, 'needs-browser.json'), 'utf8'));
const reg = JSON.parse(fs.readFileSync(path.join(cap, 'sources.json'), 'utf8'));
const today = new Date(); const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 90);
const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}); const ctx = await browser.newContext({ locale: 'en-US' }); const page = await ctx.newPage();
const findEntry = (st, name) => { const r = (reg.states || {})[st] || {}; for (const e of [...(r.statewide || []), ...(r.counties || [])]) {
  const nm = ((e.county || e.town) ? (e.county || e.town) + ': ' : '') + (e.what || e.format || 'source'); if (nm === name) return e; } return null; };
for (const [key, q] of Object.entries(queue)) {
  const days = (new Date(q.election) - today) / 864e5; if (days < -1 || days > 46 || q.browserDone) continue;
  const e = findEntry(q.state, q.source) || {}; const fe = e.fetch || {}; const dir = path.join(out, slug(key)); fs.mkdirSync(path.join(dir, 'files'), { recursive: true });
  const list = []; let links = [];
  try {
    const resp = await page.goto(q.url, { waitUntil: 'load', timeout: 60000 }); await page.waitForTimeout(3000);
    const ct = (resp && resp.headers()['content-type']) || '';
    if (fe.type === 'index' && !/pdf|zip|octet/.test(ct)) {
      const rx = new RegExp(fe.linkRegex || '\\.pdf($|\\?)', 'i');
      const hrefs = async () => (await page.$$eval('a[href]', as => as.map(a => [a.innerText.trim(), a.href])));
      let pages = [q.url];
      if (fe.followRegex) {   // a listing whose items open their own page (e.g. Miami-Dade's per-election pages)
        const frx = new RegExp(fe.followRegex, 'i'); const ftx = fe.followText ? new RegExp(fe.followText, 'i') : null;
        pages = [...new Set((await hrefs()).filter(([t, h]) => frx.test(h) && (!ftx || ftx.test(t))).map(([t, h]) => h))].slice(0, 300);
      }
      const got = new Set();
      for (const p of pages) {
        if (p !== q.url) { try { await page.goto(p, { waitUntil: 'load', timeout: 60000 }); await page.waitForTimeout(2500); } catch (err) { continue; } }
        for (const [t, h] of await hrefs()) if (rx.test(h)) got.add(h);
      }
      const need = fe.mustContain ? fe.mustContain.replace('{date}', q.election).toLowerCase() : null;
      links = [...got].filter(h => !need || decodeURIComponent(h).toLowerCase().includes(need)).slice(0, MAX);
    } else links = [q.url];
    for (const [i, u] of links.entries()) {
      try { const r = await ctx.request.get(u, { timeout: 60000 }); const b = await r.body();
        const f = String(i).padStart(5, '0') + '-' + decodeURIComponent(u.split('?')[0].split('/').pop() || 'file').replace(/[^A-Za-z0-9._-]+/g, '_').slice(-120);
        if (r.status() === 200) fs.writeFileSync(path.join(dir, 'files', f), b);
        list.push({ url: u, file: r.status() === 200 ? f : null, status: r.status(), type: r.headers()['content-type'] || '' });
        await page.waitForTimeout(500);
      } catch (err) { list.push({ url: u, file: null, status: null, error: String(err).slice(0, 200) }); }
    }
  } catch (err) { list.push({ url: q.url, file: null, status: null, error: String(err).slice(0, 200) }); }
  fs.writeFileSync(path.join(dir, 'list.json'), JSON.stringify({ key, queued: q, links: links.length, files: list }, null, 1));
  console.log(key, links.length, 'links', list.filter(x => x.file).length, 'saved');
}
await browser.close();
