#!/usr/bin/env python3
"""KUS-SPONSORS 3: state bill sponsors -> Open States person IDs + state legislator profiles, from Open States' monthly
public PostgreSQL dump (streamed by HTTP range, nothing big on disk; same reader as fetch_state_bulk_details.py).
usage: state_sponsors.py <repo_dir> <out_dir>
Writes <out_dir>/data/bills/state-sponsor-ids.json and <out_dir>/data/people-state/<ST>.json.
Matching is by the dump's own sponsorship.person_id (Open States' resolution of the legislature's sponsor record to a
person), never by name. Sponsors with no person_id (committees, bills newer than the dump) stay plain text and are counted."""
import sys, os, re, json, glob, time, datetime
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
repo, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(repo, "scripts"))
import fetch_state_bulk_details as F
FO = F.FO
t0 = time.time()
url = F.latest_dump_url(); D = F.Dump(url); print("dump", url, D.last_modified, flush=True)
snap = {}
for f in sorted(glob.glob(os.path.join(repo, "data/bills/[A-Z][A-Z].json"))):
    ab = os.path.basename(f)[:2]
    if ab == "US": continue
    for b in json.load(open(f))["bills"]: snap[b["id"]] = (ab, b)
# detail records (cosponsor names in the order the app shows them)
det = {}
for f in glob.glob(os.path.join(repo, "data/bills/detail/*.json")):
    if os.path.basename(f).startswith("US") or os.path.basename(f) == "meta.json": continue
    try: j = json.load(open(f))
    except Exception: continue
    bb = j.get("bills") or {}
    for k, v in (bb.items() if isinstance(bb, dict) else []): det[k] = v
print("snapshot bills", len(snap), "detail", len(det), flush=True)
juris = D.rows("opencivicdata_jurisdiction", sel=["id", "name"]); jid = {}
for j in juris:
    m = re.fullmatch(r"ocd-jurisdiction/country:us/(state|district):([a-z]{2})/government", j["id"])
    if m: jid[m.group(2).upper()] = j["id"]
ab_of = {v: k for k, v in jid.items()}
sessions = {s["id"]: s for s in D.rows("opencivicdata_legislativesession")}
orgs = {o["id"]: o for o in D.rows("opencivicdata_organization", sel=["id", "name", "classification", "jurisdiction_id"])}
names = {}
for s in sessions.values():
    ab = ab_of.get(s["jurisdiction_id"])
    if ab: names["%s|%s" % (FO.STATES.get(ab), s["identifier"])] = {"name": s["name"], "start": (s["start_date"] or "")[:4] or None, "cls": s["classification"]}
want = {jid[ab] for ab in {v[0] for v in snap.values()} if ab in jid}
sess_ok = {sid for sid, s in sessions.items() if s["jurisdiction_id"] in want}
bills = {}
for r in D.rows("opencivicdata_bill", key="legislative_session_id", keys=sess_ok, sel=["id", "identifier", "legislative_session_id"]):
    s = sessions[r["legislative_session_id"]]; ab = ab_of[s["jurisdiction_id"]]
    oid = FO.bill_id(ab, s["identifier"], r["identifier"], names)
    if oid in snap: bills[r["id"]] = (oid, ab)
print("matched bills", len(bills), "%.0fs" % (time.time() - t0), flush=True)
SP = D.rows("opencivicdata_billsponsorship", key="bill_id", keys=set(bills), sel=["name", "entity_type", "primary", "classification", "bill_id", "person_id"])
pids = {s["person_id"] for s in SP if s["person_id"]}
print("sponsorships", len(SP), "people", len(pids), "%.0fs" % (time.time() - t0), flush=True)
jobs = [("opencivicdata_person", "id"), ("opencivicdata_personlink", "person_id"), ("opencivicdata_personsource", "person_id"),
        ("openstates_personoffice", "person_id"), ("opencivicdata_membership", "person_id")]
T = {}
with ThreadPoolExecutor(3) as ex:
    for tag, res in zip([j[0] for j in jobs], ex.map(lambda j: D.rows(j[0], key=j[1], keys=pids), jobs)): T[tag] = res
print("people tables", {k: len(v) for k, v in T.items()}, "%.0fs" % (time.time() - t0), flush=True)
by = defaultdict(lambda: defaultdict(list))
for tag in jobs[1:]:
    for r in T[tag[0]]: by[tag[0]][r["person_id"]].append(r)
short = lambda p: p.split("/", 1)[1] if p and "/" in p else p
# bill -> sponsor ids
spm = defaultdict(list)
for s in SP: spm[s["bill_id"]].append(s)
BL = {}; cnt = Counter(); sponsored = defaultdict(list); cosponsored = defaultdict(list)
for bid, (oid, ab) in bills.items():
    S = spm.get(bid, [])
    prim = [s for s in S if s["primary"] == "t"] or [s for s in S if s["classification"] in ("primary", "author", "sponsor")]
    e = {}
    lsp = (snap[oid][1].get("sponsor") or "").strip()
    pm_ = {F.clean(s["name"], 120): short(s["person_id"]) for s in prim if s["person_id"]}
    if len(prim) > 1 and pm_: e["p"] = pm_          # several primary sponsors: the card links the one it names
    if len(prim) > 1 and lsp and lsp in pm_ and pm_[lsp] != short(prim[0]["person_id"] or ""): cnt["card_sponsor_not_first_primary"] += 1
    allm = {F.clean(s["name"], 120): short(s["person_id"]) for s in S if s["person_id"]}
    if lsp and lsp in allm: e["f"] = allm[lsp]                  # the list card's sponsor, matched to its own sponsorship row
    if prim and prim[0]["person_id"]:
        e["s"] = short(prim[0]["person_id"]); sponsored[prim[0]["person_id"]].append(oid); cnt["sponsor_linked"] += 1
    elif prim: cnt["sponsor_no_person (committee or unresolved)"] += 1
    else: cnt["no_sponsorship_rows"] += 1
    cm = {}
    for s in S:
        if prim and s is prim[0]: continue
        if s["person_id"]:
            nm = F.clean(s["name"], 120)
            if nm and nm not in cm: cm[nm] = short(s["person_id"]); cosponsored[s["person_id"]].append(oid)
    if cm: e["c"] = cm
    if e: BL[oid] = e
for oid, (ab, b) in snap.items():
    if b.get("sponsor") and oid not in {v[0] for v in []}: pass
inv = {v[0] for v in bills.values()}
cnt["list_bills_with_sponsor"] = sum(1 for oid, (ab, b) in snap.items() if b.get("sponsor"))
cnt["list_bills_not_in_dump (newer than %s)" % D.last_modified] = sum(1 for oid in snap if oid not in inv)
# people
def host(u): m = re.match(r"https?://([^/]+)", u or ""); return m.group(1).lower() if m else ""
import sources_policy as SPOL   # the app's own source rule (data/sources-policy.json)
def official(u):
    """Only government sites the owner's source policy calls official (no party/caucus, campaign or news hosts)."""
    if not u or not u.startswith("http"): return False
    st, grp = SPOL.classify(u)
    return st == "allowed" and grp in ("official", "official_extra", "local_gov_sites")
PEO = defaultdict(dict)
for p in T["opencivicdata_person"]:
    ab = ab_of.get(p["current_jurisdiction_id"])
    if not ab:
        # former legislators: state from the bills they sponsored
        bs = sponsored.get(p["id"]) or cosponsored.get(p["id"]) or []
        ab = snap[bs[0]][0] if bs else None
    if not ab: continue
    cr = F.jload(p["current_role"], {}) or {}
    links = [l["url"] for l in by["opencivicdata_personlink"][p["id"]] if official(l["url"])]
    srcs = [l["url"] for l in by["opencivicdata_personsource"][p["id"]] if official(l["url"])]
    offs = []
    for o in by["openstates_personoffice"][p["id"]]:
        x = {k: F.clean(o[k], 300) for k in ("classification", "name", "address", "voice", "fax") if o.get(k)}
        if x.get("address") or x.get("voice"): offs.append(x)
    terms = []
    for m in by["opencivicdata_membership"][p["id"]]:
        o = orgs.get(m["organization_id"]) or {}
        if o.get("classification") in ("upper", "lower", "legislature") and o.get("jurisdiction_id") == jid.get(ab):
            terms.append({"org": o.get("name"), "role": m["role"], "s": (m["start_date"] or "")[:10] or None, "e": (m["end_date"] or "")[:10] or None})
    img = p["image"] if official(p["image"]) else None
    cur = p["current_jurisdiction_id"] == jid.get(ab) and bool(cr)
    rec = {"n": F.clean(p["name"], 120), "p": p["primary_party"] or None, "cur": 1 if cur else 0,
           "ch": {"upper": "U", "lower": "L", "legislature": "L"}.get(cr.get("org_classification")) if cur else None,
           "d": str(cr.get("district")) if cur and cr.get("district") not in (None, "") else None,
           "t": cr.get("title") if cur else None, "e": p["email"] or None, "img": img, "off": offs, "links": links[:4], "src": srcs[:4],
           "terms": terms, "sp": sorted(set(sponsored.get(p["id"], []))), "cs": sorted(set(cosponsored.get(p["id"], [])))}
    if p.get("death_date"): rec["dd"] = p["death_date"][:10]
    PEO[ab][short(p["id"])] = {k: v for k, v in rec.items() if v not in (None, [], "")} | {"cur": rec["cur"]}
os.makedirs(os.path.join(out, "data/people-state"), exist_ok=True); os.makedirs(os.path.join(out, "data/bills"), exist_ok=True)
for ab, d in PEO.items():
    json.dump({"st": ab, "source": url, "dumpDate": D.last_modified, "people": d}, open(os.path.join(out, "data/people-state", ab + ".json"), "w"), ensure_ascii=False, separators=(",", ":"))
import unicodedata
def _nk(s): return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
for oid, v in BL.items():
    if "f" in v or "s" not in v: continue
    ab = oid.split("-")[0]; lsp = _nk(snap[oid][1].get("sponsor")); pn = _nk((PEO[ab].get(v["s"]) or {}).get("n"))
    toks = [t for t in re.split(r"[^a-z]+", lsp) if len(t) > 2 and t not in ("representative", "senator", "rep", "sen", "the", "del", "delegate")]
    if toks and pn and any(t in pn for t in toks): v["f"] = v["s"]
    elif lsp: cnt["card_name_differs_from_detail_sponsor (card not linked)"] += 1
os.makedirs(os.path.join(out, "data/bills/state-sponsors"), exist_ok=True)
gen = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
perst = defaultdict(dict)
for oid, v in BL.items(): perst[oid.split("-")[0]][oid] = v
for ab, bl in perst.items():
    ids = {v["s"] for v in bl.values() if v.get("s")} | {u for v in bl.values() for u in (v.get("c") or {}).values()}
    pm = {u: {k: PEO[ab][u][k] for k in ("n", "p", "ch", "d") if k in PEO[ab].get(u, {})} for u in ids if u in PEO[ab]}
    json.dump({"st": ab, "generatedAt": gen, "source": url, "bills": bl, "people": pm},
              open(os.path.join(out, "data/bills/state-sponsors", ab + ".json"), "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"generatedAt": gen, "source": url, "dumpDate": D.last_modified, "counts": dict(cnt), "people": sum(len(v) for v in PEO.values()),
           "states": sorted(perst)}, open(os.path.join(out, "data/bills/state-sponsors/meta.json"), "w"), indent=1)
print("counts", dict(cnt), "people", {k: len(v) for k, v in PEO.items()}, "%.0fs" % (time.time() - t0), flush=True)
print("DONE", flush=True)
