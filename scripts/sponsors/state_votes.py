#!/usr/bin/env python3
"""KUS-SPONSORS 4: state legislators' recorded votes on the bills KnowUS lists, from Open States' monthly bulk dump
(opencivicdata_voteevent + opencivicdata_personvote, streamed by HTTP range). usage: state_votes.py <repo_dir> <out_dir>
Writes <out_dir>/data/people-state-votes/<ST>.json {"st","source","people":{uuid:[[bill_id,date,motion,option,result],...]}}
Only votes the dump ties to a person (personvote.voter_id); names alone are never matched."""
import sys, os, re, json, glob, time, datetime
from collections import defaultdict, Counter
repo, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(repo, "scripts"))
import fetch_state_bulk_details as F
FO = F.FO; t0 = time.time()
url = F.latest_dump_url(); D = F.Dump(url); print("dump", url, flush=True)
snap = {}
for f in sorted(glob.glob(os.path.join(repo, "data/bills/[A-Z][A-Z].json"))):
    ab = os.path.basename(f)[:2]
    if ab != "US":
        for b in json.load(open(f))["bills"]: snap[b["id"]] = ab
people = {}
for f in glob.glob(os.path.join(repo, "data/people-state/[A-Z][A-Z].json")):
    j = json.load(open(f))
    for u in j["people"]: people["ocd-person/" + u] = j["st"]
juris = D.rows("opencivicdata_jurisdiction", sel=["id", "name"]); jid = {}
for j in juris:
    m = re.fullmatch(r"ocd-jurisdiction/country:us/(state|district):([a-z]{2})/government", j["id"])
    if m: jid[m.group(2).upper()] = j["id"]
ab_of = {v: k for k, v in jid.items()}
sessions = {s["id"]: s for s in D.rows("opencivicdata_legislativesession")}
names = {}
for s in sessions.values():
    ab = ab_of.get(s["jurisdiction_id"])
    if ab: names["%s|%s" % (FO.STATES.get(ab), s["identifier"])] = {"name": s["name"], "start": (s["start_date"] or "")[:4] or None, "cls": s["classification"]}
want = {jid[ab] for ab in set(snap.values()) if ab in jid}
sess_ok = {sid for sid, s in sessions.items() if s["jurisdiction_id"] in want}
bills = {}
for r in D.rows("opencivicdata_bill", key="legislative_session_id", keys=sess_ok, sel=["id", "identifier", "legislative_session_id"]):
    s = sessions[r["legislative_session_id"]]; ab = ab_of[s["jurisdiction_id"]]
    oid = FO.bill_id(ab, s["identifier"], r["identifier"], names)
    if oid in snap: bills[r["id"]] = oid
VE = {v["id"]: v for v in D.rows("opencivicdata_voteevent", key="bill_id", keys=set(bills), sel=["id", "motion_text", "start_date", "result", "bill_id"])}
print("bills", len(bills), "vote events", len(VE), "%.0fs" % (time.time() - t0), flush=True)
PV = D.rows("opencivicdata_personvote", key="vote_event_id", keys=set(VE), sel=["option", "vote_event_id", "voter_id"])
print("person votes", len(PV), "%.0fs" % (time.time() - t0), flush=True)
OUT = defaultdict(lambda: defaultdict(list)); cnt = Counter()
for v in PV:
    pid = v["voter_id"]
    if not pid: cnt["no_person"] += 1; continue
    ab = people.get(pid)
    if not ab: cnt["person_not_in_people_state"] += 1; continue
    e = VE[v["vote_event_id"]]
    OUT[ab][pid.split("/", 1)[1]].append([bills[e["bill_id"]], (e["start_date"] or "")[:10], F.clean(e["motion_text"], 140), v["option"], e["result"]])
    cnt["kept"] += 1
os.makedirs(os.path.join(out, "data/people-state-votes"), exist_ok=True)
for ab, d in OUT.items():
    for u in d: d[u].sort(key=lambda x: x[1], reverse=True)
    json.dump({"st": ab, "source": url, "dumpDate": D.last_modified, "people": d}, open(os.path.join(out, "data/people-state-votes", ab + ".json"), "w"), ensure_ascii=False, separators=(",", ":"))

# compact per-person shards: data/people-state-votes/<ST>/<uuid>.json = {"m":[motion texts],"v":[[bill_id, date, motion_idx, option, result]]}
import shutil
def shard(out):
    base = os.path.join(out, "data/people-state-votes"); n = 0
    for f in glob.glob(os.path.join(base, "[A-Z][A-Z].json")):
        j = json.load(open(f)); ab = j["st"]; d = os.path.join(base, ab)
        if os.path.isdir(d): shutil.rmtree(d)
        os.makedirs(d)
        for u, V in j["people"].items():
            M = []; mi = {}; rows = []
            for b, dt, mo, op, rs in V:
                mo = re.sub(r"\s*:\s*$", "", mo or "").strip()
                if mo not in mi: mi[mo] = len(M); M.append(mo)
                rows.append([b, dt, mi[mo], op, rs])
            json.dump({"src": j["source"], "m": M, "v": rows}, open(os.path.join(d, u + ".json"), "w"), ensure_ascii=False, separators=(",", ":")); n += 1
        os.unlink(f)
    return n
print("shards", shard(out))
print("counts", dict(cnt), "states", len(OUT), "%.0fs" % (time.time() - t0), flush=True); print("DONE", flush=True)
