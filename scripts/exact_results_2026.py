"""Contest-scoped Nov 3, 2026 checks. No generic candidate-name scraping."""
import csv
import io
import re
from collections import Counter


AK_PDF = "https://www.elections.alaska.gov/enr/26GENR/results/ElectionSummaryReportRPT.pdf"
LA_CSV = "https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data?blob=20261103/csv/"
# The SOS election race index (20261103/ElectionRaces.htm) assigns 70197 to LA-03.
LA03_PARISH = LA_CSV + "ByParish_70197.csv"
LA03_PRECINCT = LA_CSV + "ByPrecinct_70197.csv"
LA03_OFFICE = "U. S. Representative -- 3rd Congressional District"
LA03_PARISHES = frozenset(("Acadia", "Calcasieu", "Cameron", "Iberia", "Jefferson Davis",
                          "Lafayette", "St. Landry", "St. Martin", "St. Mary", "Terrebonne", "Vermilion"))


def _name(name):
    # Canonicalize punctuation/spacing, not given names, initials, suffixes or nicknames.
    return " ".join(re.findall(r"[\w]+", name.casefold()))


def ak_senate_first_choice(text):
    """Read the sole U.S. Senator table in the ENR summary, not an RCV tabulation.

    Alaska labels this summary as first-choice totals. Keep candidate rows and the
    aggregate write-in row separate; every row must reconcile with Total Votes.
    """
    page = text.split("\f", 1)[0]
    if not re.search(r"(?m)^\s*2026 GENERAL ELECTION[ \t]*$", page) or not re.search(
            r"(?m)^[ \t]*November 3, 2026[ \t]*$", page):
        raise ValueError("Alaska: wrong election or report header")
    if re.search(r"(?im)round[ \t]+[2-9]|round-by-round|final round", page):
        raise ValueError("Alaska: this is not the first-choice summary")
    sections = re.split(r"(?m)^[ \t]*U\.S\. Senator[ \t]*$", page)
    if len(sections) != 2:
        raise ValueError("Alaska: missing or duplicate U.S. Senator section")
    senate = sections[1]
    header = re.search(r"(?m)^Candidate[ \t]+Party[ \t]+Total[ \t]*$", senate)
    total = re.search(r"(?m)^Total Votes[ \t]+([\d,]+)[ \t]*$", senate)
    stamp = re.search(r"(?m)^Page: 1 of \d+[ \t]+(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M)[ \t]*$", page)
    if not (header and total and stamp and header.end() < total.start()):
        raise ValueError("Alaska: incomplete Senate table or report timestamp")
    rows = {}
    for line in senate[header.end():total.start()].splitlines():
        if not line.strip():
            continue
        row = re.fullmatch(r"(.+?)[ \t]{2,}(?:[A-Z]{2,4}[ \t]{2,})?([\d,]+)[ \t]{2,}\d+(?:\.\d+)?%[ \t]*", line)
        if not row:
            raise ValueError("Alaska: unexpected row in Senate table")
        name = row[1].strip()
        if "," in name:  # e.g. Sullivan, Dan S. -> Dan S. Sullivan, NOT Daniel J. Sullivan Jr.
            last, given = name.split(",", 1)
            pieces = given.split()
            suffix = pieces.pop() if pieces and pieces[-1].lower().rstrip(".") in {"jr", "sr", "ii", "iii", "iv"} else ""
            name = " ".join([*pieces, last] + ([suffix] if suffix else []))
        key = _name(name)
        if key in rows or not key:
            raise ValueError("Alaska: ambiguous candidate row")
        rows[key] = int(row[2].replace(",", ""))
    if len(rows) < 3 or _name("Write-in") not in rows or sum(rows.values()) != int(total[1].replace(",", "")):
        raise ValueError("Alaska: incomplete Senate table or results do not sum to Total Votes")
    return rows, stamp[1]


def _la03_table(text, precinct=False):
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")), strict=True)
    geography = ["Office", "Parish"] + (["Ward", "Precinct"] if precinct else [])
    head = next(reader, [])
    cols = len(geography)
    if head[:cols] != geography or len(head[cols:]) < 2:
        raise ValueError("Louisiana: wrong export columns")
    names = []
    for cell in head[cols:]:
        name = re.fullmatch(r"(.+?) \([A-Z]+\)", cell)
        if not name:
            raise ValueError("Louisiana: malformed candidate column")
        names.append(_name(name[1]))
    if len(set(names)) != len(names):
        raise ValueError("Louisiana: ambiguous candidate columns")
    totals, seen = {}, set()
    for row in reader:
        if len(row) != len(head) or row[0] != LA03_OFFICE or row[1] not in LA03_PARISHES:
            raise ValueError("Louisiana: wrong district, geography or malformed export row")
        key = tuple(row[1:cols])
        valid_key = all(key) or (precinct and key[1] in ("Early Voting", "Provisional Votes") and key[2] == "")
        if not valid_key or key in seen or any(not re.fullmatch(r"[0-9]+", val) for val in row[cols:]):
            raise ValueError("Louisiana: duplicate geography or non-integer count")
        seen.add(key)
        totals.setdefault(row[1], Counter()).update(dict(zip(names, map(int, row[cols:]))))
    if totals.keys() != LA03_PARISHES:
        raise ValueError("Louisiana: parish coverage incomplete")
    return totals


def la03_totals(parish_text, precinct_text):
    parish, precinct = _la03_table(parish_text), _la03_table(precinct_text, precinct=True)
    if parish != precinct:
        raise ValueError("Louisiana: parish totals do not reconcile with precincts")
    total = Counter()
    for counts in parish.values():
        total.update(counts)
    return dict(total)


def compare(rows, candidates):
    """Require the full slate (only Alaska's separate write-in aggregate is optional)."""
    app = {_name(name): (name, count) for name, count in candidates}
    expected = set(rows)
    if _name("Write-in") not in app:
        expected.discard(_name("Write-in"))
    if len(app) != len(candidates) or set(app) != expected:
        raise ValueError("the app and the exact official contest do not have the same candidate rows")
    return {name: (count, rows[key]) for key, (name, count) in app.items() if count != rows[key]}
