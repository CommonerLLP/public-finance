"""Tests for CAG Finance Accounts Vol-II public-library head extraction.

The synthetic page text mirrors the live Gujarat 2023-24 Vol-II layout captured
2026-07-23: receipts (0202-04-102) and revenue (2205-00-105) carry their figure
inline; capital (4202-04-105) carries it on the following sub-head line. Column
order is current-year, then two trailing columns (previous-year/expenditure-to-
end, then increase/decrease per-cent), so the wanted value is third-from-last.
No PDF is read — parse_pages is exercised with canned pages.
"""

from __future__ import annotations

import unittest

from publicfinance import cag_finance_accounts as cfa

# Faithful trim of the real Gujarat Vol-II layout (spacing compressed).
RECEIPTS_PAGE = """
0202-Education, Sports, Art and Culture
   04- Art and Culture-
   101- Archives and Museums                 335.68     203.96   (+)64.58
   102- Public Libraries                     20.11      11.47    (+)75.33
"""

REVENUE_PAGE = """
2205-Art and Culture - Concld.
      104 Archives              1,058.49   ..   1,058.49    369.34   (+)186.58
      105 Public Libraries      3,950.87   ..   3,950.87   2,894.78   (+)36.48
      107 Museums               4,366.95   ..   4,366.95   4,299.06   (+)1.58
"""

CAPITAL_PAGE = """
4202- Capital Outlay on Education Sports Art and Culture - Concld.
   04 Art and Culture - Concld.
 105- Public Libraries
      Other Works each Costing Rs 10 crore and less   85.50   28.70   ..   28.70   885.10   (-)66.44
 800- Other Expenditure
      Some scheme                                      10.00   10.00   ..   10.00    50.00   (+)0.00
"""

# A 105 "Public Libraries"-shaped line under an UNRELATED major must not be read
# as revenue — classification is scoped to the major head.
WRONG_MAJOR_PAGE = """
2202-General Education
      105 Public Libraries decoy   999.99   ..   999.99   1.00   (-)99.00
"""


def _pages(*texts):
    return list(enumerate(texts, start=1))


class ExtractLibraryHeadsTests(unittest.TestCase):
    def test_all_three_heads_gujarat_shape(self):
        heads = cfa.parse_pages(_pages(RECEIPTS_PAGE, REVENUE_PAGE, CAPITAL_PAGE), unit="lakh")
        self.assertIsNotNone(heads.revenue)
        self.assertIsNotNone(heads.capital)
        self.assertIsNotNone(heads.receipts)
        self.assertAlmostEqual(heads.revenue.value_lakh, 3950.87, places=2)
        self.assertAlmostEqual(heads.capital.value_lakh, 28.70, places=2)
        self.assertAlmostEqual(heads.receipts.value_lakh, 20.11, places=2)
        # loans head absent from these pages
        self.assertIsNone(heads.loans)

    def test_lakh_to_crore_conversion(self):
        heads = cfa.parse_pages(_pages(REVENUE_PAGE), unit="lakh")
        self.assertAlmostEqual(heads.revenue.value_crore, 39.5087, places=4)

    def test_capital_amount_read_from_subhead_line(self):
        heads = cfa.parse_pages(_pages(CAPITAL_PAGE), unit="lakh")
        self.assertAlmostEqual(heads.capital.value_lakh, 28.70, places=2)
        self.assertIn("Other Works", heads.capital.raw_line)
        self.assertIn("sub-head", heads.capital.note)

    def test_capital_codes_are_right(self):
        heads = cfa.parse_pages(_pages(REVENUE_PAGE, CAPITAL_PAGE), unit="lakh")
        self.assertEqual(heads.revenue.code, "2205-00-105")
        self.assertEqual(heads.capital.code, "4202-04-105")

    def test_nil_capital_records_zero_not_none(self):
        nil_capital = (
            "4202- Capital Outlay on Education Sports Art and Culture\n"
            "   04 Art and Culture\n"
            " 105- Public Libraries\n"
            " 800- Other Expenditure\n"
            "      Some scheme   1.00   ..   1.00   2.00   (+)0.00\n"
        )
        heads = cfa.parse_pages(_pages(nil_capital), unit="lakh")
        self.assertIsNotNone(heads.capital)
        self.assertEqual(heads.capital.value_lakh, 0.0)
        self.assertIn("NIL", heads.capital.note)

    def test_wrong_major_not_classified_as_revenue(self):
        heads = cfa.parse_pages(_pages(WRONG_MAJOR_PAGE), unit="lakh")
        self.assertIsNone(heads.revenue)

    def test_as_row_shape(self):
        heads = cfa.parse_pages(_pages(RECEIPTS_PAGE, REVENUE_PAGE, CAPITAL_PAGE), unit="lakh")
        row = heads.as_row()
        self.assertAlmostEqual(row["lib_rev_exp_cr"], 39.5087, places=4)
        self.assertAlmostEqual(row["lib_cap_exp_cr"], 0.2870, places=4)
        self.assertIsNone(row["lib_loans_cr"])


class ColumnRuleTests(unittest.TestCase):
    def test_current_year_self_validates_against_pct_revenue_order(self):
        # revenue row: current(3950.87), .., total, previous(2894.78), %(36.48)
        v, sv = cfa._pick_current_year([3950.87, 3950.87, 2894.78, 36.48])
        self.assertEqual(v, 3950.87)
        self.assertTrue(sv)

    def test_current_year_self_validates_against_pct_capital_order(self):
        # capital row: previous(85.50), current(28.70), .., total, to-end, %(66.44)
        # column order is DIFFERENT from revenue, but the per-cent still resolves it.
        v, sv = cfa._pick_current_year([85.50, 28.70, 28.70, 885.10, 66.44])
        self.assertEqual(v, 28.70)
        self.assertTrue(sv)

    def test_unsigned_pct_still_resolves(self):
        # UP revenue prints the per-cent without a sign: 852.16 vs 791.79 -> 7.62
        v, sv = cfa._pick_current_year([852.16, 0.00, 852.16, 791.79, 7.62])
        self.assertEqual(v, 852.16)
        self.assertTrue(sv)

    def test_amounts_ignore_bare_codes(self):
        # "105" and "2205" have no decimal, so they are never read as amounts.
        self.assertEqual(cfa._amounts("105 Public Libraries 3,950.87 .. 3,950.87"), [3950.87, 3950.87])

    def test_unresolvable_row_flagged_not_validated(self):
        v, sv = cfa._pick_current_year([12.34, 56.78])
        self.assertFalse(sv)


if __name__ == "__main__":
    unittest.main()
