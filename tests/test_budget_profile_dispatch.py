"""Tests for budget profile dispatch and observed parser-memory materialization outputs."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from publicfinance import budget_document_profiles as profiles
from publicfinance import observed_state_profiles as parser_state_profiles


class BudgetProfileDispatchTests(unittest.TestCase):
    def test_state_profile_summary_counts(self) -> None:
        summary = profiles.state_profile_summary("Rajasthan", "2025-26")
        self.assertEqual(summary["state"], "Rajasthan")
        self.assertEqual(summary["fy"], "2025-26")
        self.assertEqual(summary["document_count"], 37)
        self.assertIsInstance(summary["supports_be_re"], list)
        self.assertIn("budget_statement_capital_expenditure", summary["supports_be_re"])

    def test_state_profile_summary_covers_full_rajasthan_span(self) -> None:
        earliest = profiles.state_profile_summary("Rajasthan", "2013-14")
        latest = profiles.state_profile_summary("Rajasthan", "2026-27")
        self.assertEqual(earliest["state"], "Rajasthan")
        self.assertEqual(earliest["fy"], "2013-14")
        self.assertGreater(earliest["document_count"], 0)
        self.assertEqual(latest["state"], "Rajasthan")
        self.assertEqual(latest["fy"], "2026-27")
        self.assertGreater(latest["document_count"], 0)
        self.assertGreater(len(parser_state_profiles.profile_for("Rajasthan", "2013-14").documents), 0)
        self.assertGreater(len(parser_state_profiles.profile_for("Rajasthan", "2026-27").documents), 0)

    def test_state_profile_summary_normalizes_state(self) -> None:
        summary = profiles.state_profile_summary("RAJASTHAN", "2025-26")
        same_case = profiles.state_profile_summary("Rajasthan", "2025-26")
        self.assertEqual(summary["document_count"], same_case["document_count"])

    def test_dispatch_intent_codes_filters_to_budgets(self) -> None:
        payload = profiles.document_profiles_for_dispatch(
            "Rajasthan",
            "2025-26",
            intent="codes",
            document_families="budget_book",
        )
        self.assertTrue(payload)
        self.assertTrue(all(p.document_family == "budget_book" for p in payload))
        self.assertTrue(all(p.can_extract_codes for p in payload))
        document_types = {p.document_type for p in payload}
        self.assertIn("summary_budget", document_types)

    def test_dispatch_by_document_type_and_requirements(self) -> None:
        payload = profiles.document_profiles_for_state(
            "Rajasthan",
            "2025-26",
            document_types=("budget_statement_capital_expenditure", "budget_statement_revenue_social_services"),
            require_be_re=True,
        )
        self.assertEqual(
            {p.document_type for p in payload},
            {"budget_statement_capital_expenditure", "budget_statement_revenue_social_services"},
        )

    def test_dispatch_invalid_intent(self) -> None:
        with self.assertRaises(ValueError):
            profiles.document_profiles_for_intent("Rajasthan", "2025-26", intent="not_valid")

    def test_dispatch_state_with_no_match_returns_empty(self) -> None:
        payload = profiles.document_profiles_for_state("Rajasthan", "1999-00")
        self.assertEqual(payload, tuple())


class ProfileDispatchCLITests(unittest.TestCase):
    def test_profile_dispatch_summary_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "publicfinance.profile_dispatch",
                "--state",
                "Rajasthan",
                "--fy",
                "2025-26",
                "--summary",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = cast(dict, json.loads(completed.stdout))
        self.assertEqual(payload["state"], "Rajasthan")
        self.assertEqual(payload["fy"], "2025-26")
        self.assertEqual(payload["document_count"], 37)

    def test_profile_dispatch_intent_output(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "publicfinance.profile_dispatch",
                "--state",
                "Rajasthan",
                "--fy",
                "2025-26",
                "--intent",
                "codes",
                "--document-families",
                "budget_book",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = cast(dict, json.loads(completed.stdout))
        self.assertEqual(payload["intent"], "codes")
        self.assertEqual(payload["document_families"], ["budget_book"])
        self.assertTrue(all(isinstance(item, str) for item in payload["document_types"]))
        self.assertTrue(len(payload["profiles"]) > 0)

    def test_profile_dispatch_invalid_state_fails(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "publicfinance.profile_dispatch",
                "--state",
                "Nowhere",
                "--fy",
                "2025-26",
                "--summary",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        payload = cast(dict, json.loads(completed.stdout))
        self.assertEqual(payload["document_count"], 0)

    def test_profile_dispatch_invalid_intent_argument_fails(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "publicfinance.profile_dispatch",
                "--state",
                "Rajasthan",
                "--fy",
                "2025-26",
                "--intent",
                "bad",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)

    def test_profile_dispatch_intent_and_document_types_filter(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "publicfinance.profile_dispatch",
                "--state",
                "Rajasthan",
                "--fy",
                "2025-26",
                "--intent",
                "codes",
                "--document-types",
                "summary_budget",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = cast(dict, json.loads(completed.stdout))
        self.assertEqual(payload["intent"], "codes")
        self.assertEqual(payload["document_types"], ["summary_budget"])



class ParserMemoryMaterializationTests(unittest.TestCase):
    def test_materialize_parser_memory_writes_json_jsonl_csv(self) -> None:
        pdf_window = profiles.PdfWindow(
            code_family="2205",
            target_codes=("2205-00-105",),
            source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 2c _ Revenue Expenditure-Social Services.pdf",
            page_start=95,
            page_end=96,
            unit="lakh",
            parser_hint="test",
            notes=("unit test",),
        )
        profile = parser_state_profiles.StateObservedProfile(
            state="Rajasthan",
            fy="2025-26",
            layout="unit-test",
            currency_unit="lakh",
            parsing_rules=("test",),
            documents=(
                profiles.BudgetDocumentProfile(
                    state="Rajasthan",
                    fy="2025-26",
                    document_type="budget_statement_revenue_social_services",
                    source_relpath=pdf_window.source_relpath,
                    document_family="budget_book",
                    ocr=profiles.OCRConfig(
                        source_type="pdf_text",
                        extraction_mode="pdftotext",
                        languages=("English",),
                    ),
                    parser=profiles.ParserConfig(
                        strategy="lmmha_code_window",
                        unit="lakh",
                        code_axis="major-submajor-minor",
                        amount_columns="budget_estimate_2025_26",
                    ),
                    can_extract_be_re=True,
                    can_extract_codes=True,
                    can_extract_scheme_info=False,
                    windows=(pdf_window,),
                ),
            ),
            windows=(pdf_window,),
            notes=("unit test",),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "parser_memory.json"
            out_jsonl = Path(tmpdir) / "parser_memory.jsonl"
            out_csv = Path(tmpdir) / "parser_memory.csv"

            with patch.object(
                parser_state_profiles,
                "_extract_window_text",
                return_value="Parsed text line",
            ):
                materialized = parser_state_profiles.materialize_parser_memory(
                    profile,
                    refresh=True,
                    out_path=out_path,
                    out_jsonl_path=out_jsonl,
                    out_csv_path=out_csv,
                )

            manifest = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(materialized, out_path)
            self.assertEqual(manifest["profile"]["state"], "Rajasthan")
            self.assertEqual(manifest["profile"]["fy"], "2025-26")
            self.assertEqual(manifest["profile"]["currency_unit"], "lakh")

            jsonl_lines = out_jsonl.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(jsonl_lines), 1)
            jsonl_row = json.loads(jsonl_lines[0])
            self.assertEqual(jsonl_row["document_type"], "budget_statement_revenue_social_services")
            self.assertIn("text", jsonl_row)
            self.assertEqual(jsonl_row["text"], "Parsed text line")

            with out_csv.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["document_type"], "budget_statement_revenue_social_services")
            self.assertEqual(rows[0]["document_family"], "budget_book")

    def test_materialize_parser_memory_refresh_false_skips_extract(self) -> None:
        pdf_window = profiles.PdfWindow(
            code_family="2205",
            target_codes=("2205-00-105",),
            source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 2c _ Revenue Expenditure-Social Services.pdf",
            page_start=95,
            page_end=96,
            unit="lakh",
            parser_hint="test",
            notes=(),
        )
        profile = parser_state_profiles.StateObservedProfile(
            state="Rajasthan",
            fy="2025-26",
            layout="unit-test",
            currency_unit="lakh",
            parsing_rules=("test",),
            documents=(
                profiles.BudgetDocumentProfile(
                    state="Rajasthan",
                    fy="2025-26",
                    document_type="budget_statement_revenue_social_services",
                    source_relpath=pdf_window.source_relpath,
                    document_family="budget_book",
                    ocr=profiles.OCRConfig(
                        source_type="pdf_text",
                        extraction_mode="pdftotext",
                        languages=("English",),
                    ),
                    parser=profiles.ParserConfig(
                        strategy="lmmha_code_window",
                        unit="lakh",
                        code_axis="major-submajor-minor",
                        amount_columns="budget_estimate_2025_26",
                    ),
                    can_extract_be_re=True,
                    can_extract_codes=True,
                    can_extract_scheme_info=False,
                    windows=(pdf_window,),
                ),
            ),
            windows=(pdf_window,),
            notes=("unit test",),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "parser_memory.json"
            out_path.write_text("{}", encoding="utf-8")

            with patch.object(parser_state_profiles, "_extract_window_text", side_effect=RuntimeError("should not be called")):
                materialized = parser_state_profiles.materialize_parser_memory(
                    profile,
                    refresh=False,
                    out_path=out_path,
                )
            self.assertEqual(materialized, out_path)
            self.assertEqual(out_path.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
