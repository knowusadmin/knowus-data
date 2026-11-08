#!/usr/bin/env python3
"""Writes data/bills/index.json for KnowUS from the per-jurisdiction files in the same folder."""
import json, os, sys, glob, datetime as dt
out = sys.argv[1] if len(sys.argv) > 1 else "site/data/bills"
idx = {"generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "jurisdictions": {}}
for f in sorted(glob.glob(os.path.join(out, "*.json"))):
    k = os.path.basename(f)[:-5]
    if k == "index" or len(k) != 2: continue
    d = json.load(open(f))
    b = d.get("bills") or []
    if not b: continue
    idx["jurisdictions"][k] = {"name": d.get("name"), "session": d.get("session"), "count": len(b), "generatedAt": d.get("generatedAt"),
                               "newest": max((x.get("date") or "") for x in b) or None, "source": d.get("source"), "sourceUrl": d.get("sourceUrl")}
json.dump(idx, open(os.path.join(out, "index.json"), "w"), indent=1)
print("index:", ", ".join("%s %d" % (k, v["count"]) for k, v in idx["jurisdictions"].items()))
