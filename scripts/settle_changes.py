#!/usr/bin/env python3
"""Keep only real data changes before committing.
A JSON file whose only differences from the last commit are timestamps (generatedAt, checkedAt, ...) is put back,
so the repo does not grow by a copy of every file every hour. The bills index is kept whenever any bill list changed
(the app switches to the remote copy only when the remote index's generatedAt is newer than its built-in one).
Prints what will be committed."""
import json, subprocess, sys, os
VOLATILE = {"generatedAt", "checkedAt", "summariesCheckedAt", "fetchedAt", "builtAt", "savedAt", "started"}
def git(*a): return subprocess.run(["git", *a], capture_output=True, text=True, check=False).stdout
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list): return [strip(v) for v in o]
    return o
changed = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all", "--", "data", "base").splitlines() if l[:2] in (" M", "M ", "MM")]
real, reverted = [], []
for f in changed:
    if f == "data/last-check.json":  # the hourly heartbeat: always committed so the app can show when sources were last checked
        real.append(f); continue
    if not f.endswith(".json") or f == "data/bills/index.json":
        real.append(f); continue
    if f.startswith("data/bills/_"):  # Open States bookkeeping (_progress/_usage/_report): rides along only with real data
        continue
    try:
        old = json.loads(git("show", "HEAD:" + f)); new = json.load(open(f))
        if strip(old) == strip(new): reverted.append(f); continue
    except Exception:
        pass
    real.append(f)
lists = [f for f in real if f.startswith("data/bills/") and f.count("/") == 2 and len(os.path.basename(f)) == 7]
if "data/bills/index.json" in real and not lists:
    real.remove("data/bills/index.json"); reverted.append("data/bills/index.json")
book = [f for f in changed if f.startswith("data/bills/_")]
# Open States progress must persist so the next hour continues with the next states; keep it when it changed
for f in book:
    try:
        if strip(json.loads(git("show", "HEAD:" + f))) != strip(json.load(open(f))): real.append(f)
        else: reverted.append(f)
    except Exception: real.append(f)
for f in reverted: git("checkout", "--", f)
new_files = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all", "--", "data", "base").splitlines() if l.startswith("??")]
print("timestamp-only (not committed):", len(reverted))
print("changed:", ", ".join(real) or "none")
print("new:", ", ".join(new_files) or "none")
