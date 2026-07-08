from __future__ import annotations

import unittest

from publicfinance import account_code_extract as ace


class UnitConversionTests(unittest.TestCase):
    def test_thousand_to_crore(self) -> None:
        # 168010 thousand-rupees = ₹16.801 crore (Rajasthan library BE 2026-27)
        self.assertAlmostEqual(ace.to_crore(168010, "thousand"), 16.801, places=4)

    def test_lakh_to_crore(self) -> None:
        # 3950.87 lakh = ₹39.5087 crore (Gujarat CAG 2205-105 seed value)
        self.assertAlmostEqual(ace.to_crore(3950.87, "lakh"), 39.5087, places=4)

    def test_unknown_unit_raises(self) -> None:
        with self.assertRaises(ValueError):
            ace.to_crore(100, "furlong")


class MinorHeadStateMachineTests(unittest.TestCase):
    """The load-bearing behaviour: minor code 105 recurs under many majors, so it
    must resolve only inside the correct major/submajor block."""

    def _patch_pages(self, pages):
        def fake(pdf_path, first=None, last=None):
            yield from pages
        ace.iter_pdf_pages = fake

    def setUp(self):
        self._orig = ace.iter_pdf_pages

    def tearDown(self):
        ace.iter_pdf_pages = self._orig

    def test_105_resolves_to_correct_major(self) -> None:
        # CAG Statement-15-style page: a 2202-01-105 line (school libraries) and a
        # 2205-00-105 line (public libraries). Only the latter is the target.
        page = "\n".join([
            "2202  General Education",
            "2202-01-105  Assistance to schools        1,00,00      2,00,00      3,00,00",
            "2205  Art and Culture",
            "2205-00-105  Public Libraries               806.38          ..        806.38",
        ])
        self._patch_pages([(101, page)])
        res = ace.extract_minor_head_rows(
            None, ["2205-00-105"], unit="lakh"
        )
        self.assertIn("2205-00-105", res)
        m = res["2205-00-105"]
        self.assertEqual(m.selected_token, "806.38")
        # 806.38 lakh -> 8.0638 crore (UP FA Vol-II 2024-25 seed anchor)
        self.assertAlmostEqual(m.value_crore, 8.0638, places=4)
        self.assertEqual(m.physical_page, 101)

    def test_wrong_major_not_matched(self) -> None:
        page = "2202-01-105  Assistance to schools   9,99,99   ..   9,99,99"
        self._patch_pages([(5, page)])
        res = ace.extract_minor_head_rows(None, ["2205-00-105"], unit="lakh")
        self.assertNotIn("2205-00-105", res)


class MajorTotalTests(unittest.TestCase):
    def _patch_pages(self, pages):
        def fake(pdf_path, first=None, last=None):
            yield from pages
        ace.iter_pdf_pages = fake

    def setUp(self):
        self._orig = ace.iter_pdf_pages

    def tearDown(self):
        ace.iter_pdf_pages = self._orig

    def test_hindi_major_total_last_column(self) -> None:
        # Rajasthan Vol 2d 2026-27 line for major head 2852 (garbled Devanagari label).
        page = "\n".join([
            ("1,50,47,07      67,00,00        1,60,97,72            6          "
             "1,74,02,04      17,18,00      - श ष-2852 - ोग द   1,83,11,73   5   1,83,11,78"),
            "     https://ifms.rajasthan.gov.in                 (271)          श ष : 2852",
        ])
        self._patch_pages([(275, page)])
        res = ace.extract_major_head_totals(None, ["2852"], unit="thousand")
        self.assertIn("2852", res)
        m = res["2852"]
        self.assertEqual(m.selected_token, "1,83,11,78")   # योग/total column
        self.assertAlmostEqual(m.value_crore, 183.1178, places=4)
        self.assertEqual(m.printed_page, "271")


if __name__ == "__main__":
    unittest.main()
