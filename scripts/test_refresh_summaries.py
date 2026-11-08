#!/usr/bin/env python3
"""Offline unit test for refresh_summaries.py: fakes one newly published federal summary and one state abstract
and checks they replace the official-title stand-in, that meta counts update, and that unchanged files are skipped.
run: python3 scripts/test_refresh_summaries.py"""
import os, sys, json, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import refresh_summaries as RS, fetch_descriptions as FD, fetch_state_bulk_details as FS

d = tempfile.mkdtemp(); det = os.path.join(d, "detail"); os.makedirs(det)
us = {"id": "US-119-HR9034", "title": "Offshore Leasing Standards and Accountability Act of 2026", "url": "https://www.congress.gov/bill/119th-congress/house-bill/9034",
      "description": "To amend the Outer Continental Shelf Lands Act ...", "descriptionLabel": "From the bill's official title",
      "descriptionSource": "Official title as introduced", "descriptionUrl": "https://www.congress.gov/x/titles"}
us2 = {"id": "US-119-HR1", "title": "Has one", "summary": "Existing CRS summary.", "summarySource": "CRS"}
oh = {"id": "OH-2025-HB96", "title": "Make operating appropriations"}
ma = {"id": "MA-2025-H1", "title": "An Act relative to the red line extension in the town of Arlington"}
json.dump({"bills": {us["id"]: us, us2["id"]: us2}}, open(os.path.join(det, "US-0.json"), "w"))
json.dump({"bills": {oh["id"]: oh}}, open(os.path.join(det, "OH-0.json"), "w"))
json.dump({"bills": {ma["id"]: ma}}, open(os.path.join(det, "MA-0.json"), "w"))
json.dump({"generatedAt": "2026-11-05T00:00:00Z", "jurisdictions": {"US": {"chunks": 1, "withSummary": 1, "withDescription": 1},
           "OH": {"chunks": 1, "withSummary": 0}, "MA": {"chunks": 1, "withSummary": 0}}}, open(os.path.join(det, "meta.json"), "w"))

calls = []
RS.listing = lambda cong, t: {"BILLSTATUS-119hr9034.xml": "06-Nov-2026 10:00|5000", "BILLSTATUS-119hr1.xml": "x|1"}
def fake_one(rec):
    calls.append(rec["id"])
    return rec["id"], {"summary": "This bill requires offshore operators to show fitness to operate and fund decommissioning escrow.",
                       "summarySource": "Congressional Research Service summary (Introduced in House, 2026-07-01)"}, None
FD.us_one = fake_one

class FakeDump:
    last_modified = "Sun, 01 Dec 2026 00:00:00 GMT"
    def __init__(self, url): self.url = url
    def rows(self, tag, key=None, keys=None, sel=None):
        if tag == "opencivicdata_jurisdiction": return [{"id": "ocd-jurisdiction/country:us/state:oh/government", "name": "Ohio"},
                                                        {"id": "ocd-jurisdiction/country:us/state:ma/government", "name": "Massachusetts"}]
        if tag == "opencivicdata_legislativesession": return [
            {"id": "s1", "jurisdiction_id": "ocd-jurisdiction/country:us/state:oh/government", "identifier": "136", "name": "136th General Assembly", "start_date": "2025-01-06", "end_date": "", "classification": "primary"},
            {"id": "s2", "jurisdiction_id": "ocd-jurisdiction/country:us/state:ma/government", "identifier": "194th", "name": "194th", "start_date": "2025-01-01", "end_date": "", "classification": "primary"}]
        if tag == "opencivicdata_bill": return [{"id": "b1", "identifier": "HB 96", "legislative_session_id": "s1", "first_action_date": "2025-02-01"},
                                                {"id": "b2", "identifier": "H 1", "legislative_session_id": "s2", "first_action_date": "2025-02-01"}]
        if tag == "opencivicdata_billabstract": return [
            {"bill_id": "b1", "abstract": "To make operating appropriations for the biennium beginning July 1, 2025, and ending June 30, 2027, and to provide authorization and conditions for the operation of state programs.", "note": "summary"},
            {"bill_id": "b2", "abstract": "By Representative Garballey of Arlington, a petition of Sean Garballey relative to the red line extension in the town of Arlington. Transportation.", "note": "summary"}]
        return []
FS.Dump = FakeDump; FS.latest_dump_url = lambda: "https://data.openstates.org/postgres/monthly/2026-12-public.pgdump"
import fetch_openstates as FO
_bid = FO.bill_id
FO.bill_id = lambda ab, sess, ident, names: {"OH": "OH-2025-HB96", "MA": "MA-2025-H1"}[ab]

def run(*extra):
    sys.argv = ["refresh_summaries.py", det] + list(extra); RS.main()

run()
c = json.load(open(os.path.join(det, "US-0.json")))["bills"]
r = c["US-119-HR9034"]
assert r["summary"].startswith("This bill requires"), r
assert "description" not in r and "descriptionLabel" not in r and "descriptionUrl" not in r, r
assert c["US-119-HR1"]["summary"] == "Existing CRS summary.", "bills with a summary are never touched"
assert calls == ["US-119-HR9034"], calls
o = json.load(open(os.path.join(det, "OH-0.json")))["bills"]["OH-2025-HB96"]
assert o["summary"].startswith("To make operating appropriations"), o
assert o["summarySource"].startswith("Official abstract"), o
m = json.load(open(os.path.join(det, "MA-0.json")))["bills"]["MA-2025-H1"]
assert "summary" not in m, "MA docket line restating the title must not become a summary"
meta = json.load(open(os.path.join(det, "meta.json")))
assert meta["jurisdictions"]["US"]["withSummary"] == 2 and meta["jurisdictions"]["US"]["withDescription"] == 0, meta
assert meta["jurisdictions"]["OH"]["withSummary"] == 1, meta
assert meta["generatedAt"] > "2026-11-05T00:00:00Z" and meta.get("summariesCheckedAt"), meta
st = json.load(open(os.path.join(d, ".summary-refresh-state.json")))
assert st["statesDump"].endswith("2026-12-public.pgdump"), st

# second run: nothing new, nothing re-downloaded, state pass skipped (same monthly export)
calls.clear(); gen = meta["generatedAt"]
json.dump({"bills": {**json.load(open(os.path.join(det, "US-0.json")))["bills"],
           "US-119-HR2": {"id": "US-119-HR2", "title": "Unchanged", "description": "To do x."}}}, open(os.path.join(det, "US-0.json"), "w"))
RS.listing = lambda cong, t: {"BILLSTATUS-119hr2.xml": "01-Jan-2026 00:00|10"}
st["federal"]["US-119-HR2"] = "01-Jan-2026 00:00|10"; json.dump(st, open(os.path.join(d, ".summary-refresh-state.json"), "w"))
run()
assert calls == [], "unchanged BILLSTATUS files must not be re-downloaded: %s" % calls
assert json.load(open(os.path.join(det, "meta.json")))["generatedAt"] == gen, "generatedAt moves only when something changed"
shutil.rmtree(d)
print("ALL TESTS PASSED")
