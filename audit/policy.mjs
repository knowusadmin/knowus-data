// KnowUS source policy for the audit (same rule as the app's sources.js and scripts/sources_policy.py).
// The rule lives in data/sources-policy.json.
export function makePolicy(P) {
  const PATS = (P.official_patterns || []).map(s => new RegExp(s));
  const dom = u => { try { return new URL(u).hostname.toLowerCase().replace(/^www\./, ''); } catch { return ''; } };
  const inner = u => { const m = /^https?:\/\/web\.archive\.org\/web\/[^/]+\/(.*)$/.exec(u || ''); return m ? (/^https?:/.test(m[1]) ? m[1] : 'http://' + m[1]) : u; };
  const ends = (h, d) => h === d || h.endsWith('.' + d);
  const G = new Set();
  for (const [g, on] of Object.entries(P.groups_kept || {})) { if (g.startsWith('_') || !on) continue; for (const d of (P[g] || [])) G.add(d); }
  const inG = h => { const p = h.split('.'); for (let i = 0; i < p.length; i++) if (G.has(p.slice(i).join('.'))) return true; return false; };
  return function cls(url, own = []) {
    const h = dom(inner(url)); if (!h) return 'none';
    for (const [d, v] of Object.entries(P.pending || {})) { if (d.startsWith('_')) continue; if (ends(h, d)) return v === 'ban' ? 'banned' : 'pending'; }
    if ((P.news_banned || []).some(d => ends(h, d))) return 'banned';
    if ((P.news_allowed || []).some(d => ends(h, d))) return 'allowed';
    if (PATS.some(p => p.test(h))) return 'allowed';
    if (own.some(o => o && ends(h, o))) return 'allowed';
    if (inG(h)) return 'allowed';
    return 'banned';
  };
}
