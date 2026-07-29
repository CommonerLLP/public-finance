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

    def test_small_change_previous_first_resolved_by_repetition(self):
        # capital order (previous first) with a small change: the backward ratio
        # also fits the tolerance, but only the current-year figure repeats
        # (voted + total), so repetition must resolve it to 28.70, not 30.00.
        v, sv = cfa._pick_current_year([30.00, 28.70, 28.70, 885.10, 4.33])
        self.assertEqual(v, 28.70)
        self.assertTrue(sv)

    def test_small_change_resolved_by_printed_sign(self):
        # same shape but nothing repeats; the printed (-) must pick the smaller.
        v, sv = cfa._pick_current_year([30.00, 28.70, 885.10, 4.33], pct_sign="-")
        self.assertEqual(v, 28.70)
        self.assertTrue(sv)

    def test_small_change_no_disambiguator_is_flagged(self):
        v, sv = cfa._pick_current_year([30.00, 28.70, 885.10, 4.33])
        self.assertFalse(sv)

    def test_small_change_resolved_by_state_central_sum(self):
        # Kerala 2023-24 revenue row (live): state, central, total, previous, pct.
        # Unsigned small pct leaves {total, previous} ambiguous; the total is the
        # one that equals state + central.
        v, sv = cfa._pick_current_year([2344.90, 133.25, 2478.15, 2370.94, 4.52])
        self.assertEqual(v, 2478.15)
        self.assertTrue(sv)

    def test_zero_is_not_a_candidate_for_near_100_pct(self):
        # Jharkhand 2024-25 revenue row (live): a 0.00 charged column is exactly
        # -100 against ANY previous figure, so a printed 100.09 must not
        # validate 0.0 — the real current-year figure is 117.37.
        v, sv = cfa._pick_current_year([117.37, 0.0, 0.0, 117.37, 58.66, 100.09])
        self.assertEqual(v, 117.37)
        self.assertTrue(sv)

    def test_lone_cumulative_figure_never_returned_as_capital(self):
        # Haryana 2023-24 shape (page-verified): in-year columns are dots and
        # the only decimal on the 105 line is the cumulative "upto" column.
        # 2,267.11 must not come back as the in-year figure.
        page = (
            "4202 Capital Outlay on Education, Sports, Art and Culture-\n"
            "  04  Art and Culture-\n"
            "105 Public Libraries                            ..    ..    ..    2,267.11    ..\n"
            "106 Museums                                     ..    ..    ..    1,124.46    ..\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertIsNone(heads.capital.value_lakh)
        self.assertFalse(heads.capital.self_validated)

    def test_minus_100_pct_is_a_validated_zero(self):
        # Haryana 2022-23 shape (page-verified): in-year columns are dots and
        # the row prints prior-year, cumulative, and (-)100.00 — which proves
        # the current year is exactly zero.
        v, sv = cfa._pick_current_year([1760.57, 2267.11, 100.00], pct_sign="-")
        self.assertEqual(v, 0.0)
        self.assertTrue(sv)

    def test_total_105_with_wrapped_figures(self):
        # Assam 2023-24 shape (page-verified): "Total 105" carries its figures
        # on the next line; prior 498.29 -> current 52,536.15 is (+)10443.
        page = (
            "4202 Capital Outlay on Education, Sports,Art and Culture - Contd.\n"
            "  04  Art and Culture- Contd.\n"
            "105 Public Libraries                       ...   ...   ...   231.73   ...\n"
            "District Library Auditorium Silchar     190.00  171.00  ...  171.00  371.71  (-)10\n"
            "Total 105\n"
            "     498.29   52,536.15   ...   52,536.15   54,266.18   (+)10443\n"
            "106 Museums                                ...   ...   ...   289.55   ...\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertAlmostEqual(heads.capital.value_lakh, 52536.15, places=2)
        # the printed per-cent is a bare integer ("(+)10443"), which the
        # decimal-only amount rule ignores — so this read resolves via the
        # repeated-value fallback and stays flagged for review.
        self.assertFalse(heads.capital.self_validated)

    def test_wrapped_total_does_not_absorb_next_numeric_head(self):
        # "Total 105" followed directly by "106 Museums ..." (numeric-led): the
        # museums figures must not be parsed as head-105 capital.
        page = (
            "4202 Capital Outlay on Education, Sports,Art and Culture\n"
            "  04  Art and Culture\n"
            "105 Public Libraries                       ...   ...   ...   231.73   ...\n"
            "Total 105\n"
            "106 Museums        564.35   174.48  ...  174.48   1,130.17   (-)69.08\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertNotEqual(heads.capital.value_lakh, 174.48)
        self.assertFalse(heads.capital.self_validated)

    def test_wrapped_bare_amount_is_not_a_head_boundary(self):
        # A wrapped continuation starting "117.37" must not read as head 117 —
        # its figure still vetoes the confident NIL.
        page = (
            "4202 Capital Outlay on Education, Sports,Art and Culture\n"
            "  04  Art and Culture\n"
            " 105- Public Libraries\n"
            "117.37   ..   ..   2,267.11   ..\n"
            " 800- Other Expenditure\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertIsNone(heads.capital.value_lakh)
        self.assertFalse(heads.capital.self_validated)

    def test_rejected_lone_total_still_vetoes_nil(self):
        # Total-105 carrying only the cumulative figure: the lone-figure veto
        # rejects it as a value, but it must NOT fall through to a proven NIL.
        page = (
            "4202 Capital Outlay on Education, Sports,Art and Culture\n"
            "  04  Art and Culture\n"
            " 105- Public Libraries\n"
            "Total 105                                  2,267.11\n"
            " 800- Other Expenditure\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertIsNone(heads.capital.value_lakh)
        self.assertFalse(heads.capital.self_validated)

    def test_mixed_subhead_block_is_not_a_validated_sum(self):
        # One validated + one unvalidated multi-figure sub-head: a partial sum
        # must not ship as self-validated capital.
        page = (
            "4202 Capital Outlay on Education, Sports,Art and Culture\n"
            "  04  Art and Culture\n"
            " 105- Public Libraries\n"
            "      Scheme A   100.00   50.00   ..   50.00   500.00   (-)50.00\n"
            "      Scheme B   77.10   88.20\n"
            " 800- Other Expenditure\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertFalse(heads.capital.self_validated)
        self.assertIsNone(heads.capital.value_lakh)
        self.assertIn("mixed block", heads.capital.note)

    def test_wrapped_figure_line_vetoes_confident_nil(self):
        # the head's figure sits on a numeric-only wrapped line: must NOT be
        # recorded as a confident NIL — flag for review instead.
        page = (
            "4202- Capital Outlay on Education Sports Art and Culture\n"
            "   04 Art and Culture\n"
            " 105- Public Libraries\n"
            "      45.00   ..   45.00   40.00   (+)12.50\n"
            " 800- Other Expenditure\n"
            "      Some scheme   1.00   ..   1.00   2.00   (+)0.00\n"
        )
        heads = cfa.parse_pages([(1, page)], unit="lakh")
        self.assertIsNone(heads.capital.value_lakh)
        self.assertFalse(heads.capital.self_validated)
        self.assertIn("manual review", heads.capital.note)


if __name__ == "__main__":
    unittest.main()
