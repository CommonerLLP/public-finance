"""Core Sankey domain tests — no data files, just the port + builders.

Locks the ports/adapters refactor: classify() ranges and the two payload
builders must behave identically regardless of which state/adapter fed them.
"""

import unittest

from viz.sankey import core
from viz.sankey.model import (
    BalanceModel, Beneficiary, ExpenditureLine, Flow, OffBudgetModel, SectorModel,
)


class TestClassify(unittest.TestCase):
    def test_functional_ranges(self):
        self.assertEqual(core.classify("2202")[0], "social")    # education
        self.assertEqual(core.classify("4202")[0], "social")    # capital education -> revenue twin
        self.assertEqual(core.classify("2210")[0], "social")    # health
        self.assertEqual(core.classify("2401")[0], "economic")  # agriculture
        self.assertEqual(core.classify("2048")[0], "general")   # interest payments
        self.assertEqual(core.classify("6003")[0], "debt")      # internal debt
        self.assertEqual(core.classify("3601")[0], "grants")    # grants to local bodies


class TestSectorBuilder(unittest.TestCase):
    def test_rollup_and_dual(self):
        model = SectorModel(
            state="Testland", fy="2024-25", basis="Budget Estimate",
            lines=[
                ExpenditureLine("2210", 100.0),   # health (social)
                ExpenditureLine("2215", 40.0),    # water (social)
                ExpenditureLine("2048", 70.0),    # interest (general)
                ExpenditureLine("6003", 10.0),    # public debt repayment (debt)
            ],
            source="unit test", caveat="unit test",
        )
        payload = core.build_sector(model)
        self.assertEqual(payload["meta"]["total_cr"], 220.0)
        self.assertEqual(payload["meta"]["dual"]["health"], 100.0)
        self.assertEqual(payload["meta"]["dual"]["water"], 40.0)
        self.assertEqual(payload["meta"]["dual"]["interest"], 70.0)


class TestBalanceBuilder(unittest.TestCase):
    def test_balanced_identity(self):
        model = BalanceModel(
            state="Testland", fy="2024-25",
            sources=[Flow("Own tax", 60, "own", "#000"), Flow("Net borrowing", 40, "borrow", "#f00")],
            uses=[Flow("Social Services", 100, "use", "#0f0")],
            source="unit test", caveat="unit test",
        )
        payload = core.build_balance(model)
        self.assertEqual(payload["meta"]["total_cr"], 100)

    def test_unbalanced_rejected(self):
        model = BalanceModel(
            state="Testland", fy="2024-25",
            sources=[Flow("Own tax", 60, "own", "#000")],
            uses=[Flow("Social Services", 100, "use", "#0f0")],
            source="unit test", caveat="unit test",
        )
        with self.assertRaises(AssertionError):
            core.build_balance(model)


class TestOffBudgetBuilder(unittest.TestCase):
    def _model(self, **kw):
        base = dict(
            jurisdiction="Testland", jtype="state", fy="2024-25",
            ceiling_cr=1000.0, outstanding_cr=500.0,
            beneficiaries=[Beneficiary("PSU A", 300.0, "psu_power", ""),
                           Beneficiary("ULB B", 100.0, "ulb", "")],
            series_cr={"2023-24": 480.0, "2024-25": 500.0},
            source="unit test", caveat="unit test", pct_of=2.5,
        )
        base.update(kw)
        return OffBudgetModel(**base)

    def test_residual_and_reconciliation(self):
        payload = core.build_offbudget(self._model())
        # named 300 + 100, outstanding 500 -> "Other" residual of 100
        other = [l for l in payload["links"]
                 if payload["nodes"][l["target"]]["name"].startswith("Other")]
        self.assertEqual(round(other[0]["value"], 1), 100.0)
        self.assertEqual(round(sum(l["value"] for l in payload["links"]), 1), 500.0)
        self.assertEqual(payload["meta"]["total_cr"], 500.0)
        self.assertEqual(payload["meta"]["headroom_cr"], 500.0)  # 1000 ceiling - 500

    def test_no_residual_when_named_equals_total(self):
        payload = core.build_offbudget(self._model(outstanding_cr=400.0, ceiling_cr=None))
        names = [n["name"] for n in payload["nodes"]]
        self.assertFalse(any(n.startswith("Other") for n in names))
        self.assertIsNone(payload["meta"]["headroom_cr"])

    def test_measure_drives_headline(self):
        payload = core.build_offbudget(
            self._model(measure="off-budget borrowing", pct_label="GSDP"))
        self.assertIn("off-budget borrowing", payload["meta"]["headline"])
        self.assertIn("GSDP", payload["meta"]["headline"])


if __name__ == "__main__":
    unittest.main()
