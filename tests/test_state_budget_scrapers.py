"""Unit tests for state budget scraper discovery helpers."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path


def _import_scrapers_module():
    if "lxml" not in sys.modules:
        lxml_mod = types.ModuleType("lxml")
        etree_mod = types.ModuleType("lxml.etree")
        etree_mod.HTML = lambda text: None
        lxml_mod.etree = etree_mod
        sys.modules["lxml"] = lxml_mod
        sys.modules["lxml.etree"] = etree_mod

    import importlib

    return importlib.import_module("publicfinance.state_budget_scrapers")


scrapers = _import_scrapers_module()


class _FakeElement:
    def __init__(self, href: str, text: str) -> None:
        self._href = href
        self._text = text

    def xpath(self, query: str):
        if query == "./@href":
            return [self._href]
        if query == ".//text()":
            return [self._text]
        return []


class _FakeDom:
    def __init__(self, elements) -> None:
        self._elements = elements

    def xpath(self, query: str):
        if query == "//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf')]":
            return self._elements
        return []


class RajasthanScraperDiscoveryTests(unittest.TestCase):
    def test_modified_budget_links_are_treated_as_2024_25_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = scrapers.RajasthanBudgetsScraper(
                out_folder=Path(tmpdir) / "out",
                db_path=Path(tmpdir) / "db.sqlite",
            )
            scraper.get_page_dom = lambda url: _FakeDom(
                [
                    _FakeElement(
                        "https://finance.rajasthan.gov.in/docs/budget/statebudget/2024-2025%20(Modified%20Budget)/Vol1.pdf",
                        "Vol1",
                    ),
                    _FakeElement(
                        "https://finance.rajasthan.gov.in/docs/budget/statebudget/2024-2025%20(Vote%20on%20Account)/Vol2.pdf",
                        "Vol2",
                    ),
                ]
            )

            documents = scraper.discover_documents(fiscal_year="2024-25")

        self.assertEqual(len(documents), 2)
        self.assertTrue(all(doc.fiscal_year == "2024-25" for doc in documents))
        self.assertTrue(all("2024-25" in str(doc.local_path) for doc in documents))
        self.assertTrue(any("Modified%20Budget" in doc.source_url for doc in documents))
        self.assertTrue(any("Vote%20on%20Account" in doc.source_url for doc in documents))

    def test_modified_budget_helpers_match_fy_2024_25(self) -> None:
        self.assertTrue(
            scrapers._rajasthan_budget_link_is_relevant(
                "https://finance.rajasthan.gov.in/docs/budget/statebudget/2024-2025 (modified budget)/vol1.pdf",
                "vol1",
            )
        )
        self.assertTrue(
            scrapers._rajasthan_budget_link_matches_year(
                "https://finance.rajasthan.gov.in/docs/budget/statebudget/vol1.pdf",
                "modified budget",
                "2024-25",
            )
        )

