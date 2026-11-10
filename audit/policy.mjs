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
  const D = P.democratic_sources || null; let DT = /$^/; try { DT = new RegExp((D && D.name_token_pattern) || '$^'); } catch {}
  const SOC = /^https?:\/\/(?:www\.|mobile\.|m\.)?(twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com)\/(?:@)?([A-Za-z0-9_.\-]+)/, SK = { 'twitter.com': 'twitter', 'x.com': 'twitter', 'facebook.com': 'facebook', 'instagram.com': 'instagram', 'youtube.com': 'youtube' };
  const dem = url => { if (!D || D.rule !== 'ban') return null; const u = inner(url); const m = SOC.exec(u || ''); if (m) { const b = (D.social_accounts || {})[SK[m[1]] + ':' + m[2].toLowerCase()]; if (b) return [b]; }
    const h = dom(u); if (!h) return null; if ((D.member_sites || {})[h]) return D.member_sites[h];
    for (const g of ['officeholder_sites', 'campaign_sites']) for (const [d, o] of Object.entries(D[g] || {})) if (ends(h, d)) return o;
    let co = []; for (const [d, o] of Object.entries(D.caucus_hosted_own_pages || {})) if (ends(h, d)) co = o;
    if ((D.party_org_sites || []).some(d => ends(h, d))) return co; if (h.split(/[.\-]/).some(t => t !== 'tandem' && DT.test(t))) return co; return null; };
  const SA = P.social_accounts || null, SARE = /^https?:\/\/(?:www\.|mobile\.|m\.)?([a-z.]+)\/(?:@|profile\/|in\/|user\/|c\/)?([A-Za-z0-9_.\-]+)/i;
  const soc = url => { if (!SA) return null; const m = SARE.exec(inner(url) || ''); if (!m) return null; const h = m[1].toLowerCase().replace(/^www\./, ''); if (!(SA.hosts || []).includes(h)) return null;
    const k = ({ 'twitter.com': 'twitter', 'x.com': 'twitter', 'mobile.twitter.com': 'twitter' })[h] || h.split('.')[0]; return (SA.own || {})[k + ':' + m[2].toLowerCase()] || []; };
  // narrow exceptions (v44, owner Nov 10 2026 12:34 AM ET: AP "Sure but only in the elections tab" for House calls):
  // a host in narrow_exceptions stays banned except for the one use named by only_for, passed as ctx.
  const NX = Object.entries(P.narrow_exceptions || {}).filter(([k, v]) => !k.startsWith('_') && v && typeof v === 'object');
  return function cls(url, own = [], who = [], ctx = null) {
    const h = dom(inner(url)); if (!h) return 'none';
    if (ctx && NX.some(([d, x]) => ends(h, d) && x.only_for === ctx)) return 'allowed';
    const ds = dem(url); if (ds) return D.allow_own_site_for_dems && (ds.some(x => who.includes(x)) || own.some(o => o && ends(h, o))) ? 'allowed' : 'banned';
    const so = soc(url); if (so) return so.some(x => who.includes(x)) ? 'allowed' : 'banned';
    for (const [d, v] of Object.entries(P.pending || {})) { if (d.startsWith('_')) continue; if (ends(h, d)) return v === 'ban' ? 'banned' : 'pending'; }
    if ((P.news_banned || []).some(d => ends(h, d))) return 'banned';
    if ((P.news_allowed || []).some(d => ends(h, d))) return 'allowed';
    if (PATS.some(p => p.test(h))) return 'allowed';
    if (own.some(o => o && ends(h, o))) return 'allowed';
    if (inG(h)) return 'allowed';
    return 'banned';
  };
}
