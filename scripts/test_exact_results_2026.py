"""Synthetic regressions for candidate identity, race scope, and read-only checks."""
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import exact_results_2026 as exact
import official_audit as audit
import watchdog


AK = """Page: 1 of 2                                                              11/17/2026 5:46:56 PM
                        2026 GENERAL ELECTION
                        November 3, 2026
                        UNOFFICIAL RESULTS

U.S. Senator
Precincts Reported: 401 of 401 (100.00%)

Candidate                            Party           Total
Peltola, Mary                        DEM              1,334        54.88%
Sullivan, Daniel J. Jr.                                  24         0.99%
Sullivan, Dan S.                     REP              1,056        43.44%
Write-in                                                 17         0.70%
Total Votes                                           2,431

U.S. Representative
Candidate                            Party           Total
Sullivan, Dan S.                     REP              9,999       100.00%
Total Votes                                           9,999
"""


def la_exports():
    parish, precinct = io.StringIO(), io.StringIO()
    p, c = csv.writer(parish), csv.writer(precinct)
    head = ['John Day (DEM)', 'Candidate Opponent (REP)']
    p.writerow(['Office', 'Parish', *head])
    c.writerow(['Office', 'Parish', 'Ward', 'Precinct', *head])
    for name in sorted(exact.LA03_PARISHES):
        root = [exact.LA03_OFFICE, name]
        p.writerow([*root, 100, 200])
        c.writerow([*root, '01', '04', 24, 60])
        c.writerow([*root, 'Early Voting', '', 76, 140])
    return parish.getvalue(), precinct.getvalue()


class TestExactResults(unittest.TestCase):
    def test_alaska_distinguishes_both_sullivans_and_uses_first_choice(self):
        counts, time = exact.ak_senate_first_choice(AK)
        self.assertEqual(exact.compare(counts, [('Dan S. Sullivan', 900), ('Daniel J. Sullivan Jr.', 20),
                                               ('Mary Peltola', 1334), ('Write-in', 11)]),
                         {'Dan S. Sullivan': (900, 1056), 'Daniel J. Sullivan Jr.': (20, 24), 'Write-in': (11, 17)})
        self.assertEqual(time, '11/17/2026 5:46:56 PM')

    def test_alaska_rejects_another_election_or_round_or_unbalanced_total(self):
        for bad in (AK.replace('November 3', 'November 4'), AK.replace('U.S. Senator', 'State Senator'),
                    AK.replace('UNOFFICIAL RESULTS', 'Round 2'), AK.replace('2,431', '2,430')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                exact.ak_senate_first_choice(bad)

    def test_alaska_requires_the_full_slate(self):
        counts, _ = exact.ak_senate_first_choice(AK)
        with self.assertRaises(ValueError):
            exact.compare(counts, [('Dan S. Sullivan', 900)])

    def test_louisiana_uses_complete_district_not_one_precinct(self):
        p, c = la_exports()
        self.assertEqual(exact.la03_totals(p, c), {'john day': 1100, 'candidate opponent': 2200})
        with patch.object(audit, 'get', side_effect=[Mock(text=p), Mock(text=c)]):
            findings = audit.audit_exact('LA', audit.CHECKS['LA'][0],
                                         {'cands': [('John Day', 1100), ('Candidate Opponent', 2200)]})
        self.assertEqual(findings['kind'], 'OK')
        self.assertIn('house:3', audit.CHECKS['LA'][1]['exclude'])

    def test_louisiana_rejects_wrong_contest_duplicate_and_non_reconciling_exports(self):
        p, c = la_exports()
        for bad in (c.replace('3rd Congressional', '2nd Congressional', 1),
                    c + c.splitlines(keepends=True)[1], c.replace(',24,60', ',23,60', 1),
                    c.replace('Vermilion', 'Other parish')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                exact.la03_totals(p, bad)

    def test_uncertainty_and_exact_discrepancies_do_not_write(self):
        chk = audit.CHECKS['AK'][0]
        race = {'cands': [('Dan S. Sullivan', 900), ('Daniel J. Sullivan Jr.', 20), ('Mary Peltola', 1334)]}
        with patch.object(audit, 'pdf_text', return_value=AK):
            mismatch = audit.audit_exact('AK', chk, race)
        with patch.object(audit, 'pdf_text', return_value='not a report'):
            unreadable = audit.audit_exact('AK', chk, race)
        self.assertEqual(mismatch['kind'], 'MISMATCH')
        self.assertIn('Dan S. Sullivan: app 900 vs official 1,056', mismatch['detail'])
        self.assertEqual(unreadable['kind'], 'UNREADABLE')
        self.assertNotIn('refresh', mismatch)
        # Even an accidentally supplied write payload for an exact report is ignored.
        mismatch['refresh'] = {'Dan S. Sullivan': 24}
        with tempfile.TemporaryDirectory() as temp:
            old = Path(temp) / 'election-official.json'
            old.write_text('last verified snapshot')
            self.assertEqual(watchdog.refresh_counts('https://example.invalid', [mismatch, unreadable], temp), [])
            self.assertEqual(list(Path(temp).iterdir()), [old])
            self.assertEqual(old.read_text(), 'last verified snapshot')
