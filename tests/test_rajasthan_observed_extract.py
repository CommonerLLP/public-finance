from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from publicfinance import rajasthan_observed_extract as extractor


def _canonical_map() -> dict[str, str]:
    return {
        variant: canonical
        for canonical, variants in extractor.TARGET_VARIANTS.items()
        for variant in variants
    }


def _target_info() -> dict[str, dict[str, str]]:
    info = {}
    for variant in _canonical_map():
        major, sub, minor = variant.split("-")
        info[variant] = {"major": major, "submajor": sub, "minor": minor, "canonical": _canonical_map()[variant]}
    return info


class RajasthanObservedExtractorTests(unittest.TestCase):
    def test_exact_2202_code_stays_separate(self) -> None:
        line = "2202-00-105            Public Libraries                     1,234  "
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major=None,
            current_submajor=None,
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.code, "2202-00-105")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2202-00-105")

    def test_alias_submajor_total_matches_when_only_submajor_context_exists(self) -> None:
        match, _, _ = extractor.parse_target_line(
            line="00 1,234 (कुल - श ष - 105)",
            current_major="2205",
            current_submajor="00",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.code, "2205-00-105")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2205-00-105")

    def test_31_row_without_clean_label_is_still_treated_as_library_row(self) -> None:
        line = "50             ..             50           ..         50           .. 31-    तक        ए             क                  80           ..               80"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major="2205",
            current_submajor="00",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2205-00-105")

    def test_public_library_phrase_routes_to_2205(self) -> None:
        line = "sarvajanik pustakalay  31-  1,00"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major=None,
            current_submajor=None,
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint_keyword")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2205-00-105")

    def test_2013_page_114_public_library_row_uses_label_line(self) -> None:
        line = " 6,19,88         6,45         60      7,04,04        8,00            1      7,02,79        8,00       11,08 सारजनिक पुस्तकालय                         7,91,40        7,82               1         7,99,23"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major="2205",
            current_submajor="00",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint_keyword")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2205-00-105")
        self.assertEqual(match.selected_amount, 79923.0)

    def test_31_row_under_2202_is_kept_separate(self) -> None:
        line = "50             ..             50           ..         50           .. 31-    तक        ए             क                  80           ..               80"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major="2202",
            current_submajor="00",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2202-00-105")

    def test_school_university_phrase_routes_to_2202(self) -> None:
        line = "vidyalay aur vishvavidyalay pustakalay  31-  1,00"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major=None,
            current_submajor=None,
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint_keyword")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2202-00-105")

    def test_capital_library_phrase_routes_to_4202_only_in_4202_context(self) -> None:
        line = "105-स वज क            तक           30,00           ..      2,49,91           ..      4,20,68"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major="4202",
            current_submajor="04",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint_keyword")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "4202-04-105")

    def test_surya_ocr_summary_table_extracts_public_library_rows(self) -> None:
        payload = {
            "Volume 2c": [
                {
                    "blocks": [
                        {
                            "label": "SectionHeader",
                            "html": "<p><b>2205-कला एवं संस्कृति<br/>सारांश</b></p>",
                        },
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr>
                                <td>6,19,88</td><td>6,45</td><td>60</td>
                                <td>सार्वजनिक पुस्तकालय</td>
                                <td>7,91,40</td><td>7,82</td><td>1</td><td>7,99,23</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                        {
                            "label": "SectionHeader",
                            "html": "<p><b>4202- शिक्षा, खेलकूद, कला तथा संस्कृति पूंजीगत</b></p>",
                        },
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr>
                                <td></td><td></td><td></td>
                                <td>माँग संख्या- 21 105-सार्वजनिक पुस्तकालय</td>
                              </tr>
                              <tr>
                                <td>30,00</td><td>..</td><td>2,49,91</td>
                                <td>4,20,68</td><td>..</td>
                                <td>लघु शीर्ष - 105 योग</td>
                                <td>2,40,00</td><td>..</td><td>2,40,00</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "results.json"
            results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            matches = extractor._extract_surya_summary_matches_from_results(results_path)

        by_target = {match["target"]: match for match in matches}
        self.assertEqual(by_target["2205-00-105"]["status"], "surya_ocr_summary")
        self.assertEqual(by_target["2205-00-105"]["selected_amount_thousand_rupees"], 79923.0)
        self.assertEqual(by_target["4202-04-105"]["status"], "surya_ocr_summary")
        self.assertEqual(by_target["4202-04-105"]["selected_amount_thousand_rupees"], 24000.0)

    def test_surya_revenue_row_prefers_last_comma_amount_over_plain_marker(self) -> None:
        payload = {
            "Volume 2c": [
                {
                    "blocks": [
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr>
                                <td>6,81,36</td><td>4,76</td><td>11,08</td>
                                <td>7,91,40</td><td>7,82</td><td>1</td>
                                <td>9,10,56</td><td>8,50</td><td>1</td>
                                <td>सार्वजनिक पुस्तकालय</td>
                                <td>9,33,45</td><td>48,64</td><td>9,82,09</td><td>1</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "Volume 2c _ Revenue Expenditure-Social Services" / "results.json"
            results_path.parent.mkdir(parents=True)
            results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            matches = extractor._extract_surya_summary_matches_from_results(results_path)

        self.assertEqual(matches[0]["target"], "2205-00-105")
        self.assertEqual(matches[0]["selected_amount_thousand_rupees"], 98209.0)

    def test_unsafe_fallback_does_not_become_final_observed_value(self) -> None:
        results = {"4202-04-105": {"status": "not_found"}}
        extractor._replace_result_if_better(
            results,
            "4202-04-105",
            {
                "status": "submajor_total",
                "selected_amount_thousand_rupees": 25883224.0,
            },
        )

        self.assertEqual(results["4202-04-105"]["status"], "not_found")

    def test_surya_volume_3a_artifact_defaults_to_4202_context(self) -> None:
        payload = {
            "Volume 3a": [
                {
                    "blocks": [
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr><td></td><td>105-सार्वजनिक पुस्तकालय</td></tr>
                              <tr>
                                <td>..</td><td>..</td><td>1</td>
                                <td>लघु शीर्ष - 105 योग</td>
                                <td>1</td><td>..</td><td>1</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "Volume 3a _ Capital Expenditure" / "results.json"
            results_path.parent.mkdir(parents=True)
            results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            matches = extractor._extract_surya_summary_matches_from_results(results_path)

        self.assertEqual(matches[0]["target"], "4202-04-105")
        self.assertEqual(matches[0]["selected_amount_thousand_rupees"], 1.0)

    def test_surya_split_table_keeps_public_library_pending_state(self) -> None:
        payload = {
            "Volume 3a": [
                {
                    "blocks": [
                        {
                            "label": "Table",
                            "html": "<table><tbody><tr><td>105-सार्वजनिक पुस्तकालय</td></tr></tbody></table>",
                        },
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr><td>[01] भवन</td></tr>
                              <tr>
                                <td>..</td><td>..</td><td>1</td>
                                <td>लघु शीर्ष - 105 योग</td>
                                <td>1</td><td>..</td><td>1</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "Volume 3a _ Capital Expenditure" / "results.json"
            results_path.parent.mkdir(parents=True)
            results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            matches = extractor._extract_surya_summary_matches_from_results(results_path)

        self.assertEqual(matches[0]["target"], "4202-04-105")
        self.assertEqual(matches[0]["selected_amount_thousand_rupees"], 1.0)

    def test_surya_split_pages_keep_public_library_pending_state(self) -> None:
        payload = {
            "Volume 3a": [
                {
                    "blocks": [
                        {
                            "label": "Table",
                            "html": "<table><tbody><tr><td>105-सार्वजनिक पुस्तकालय</td></tr></tbody></table>",
                        },
                    ]
                },
                {
                    "blocks": [
                        {
                            "label": "Table",
                            "html": """
                            <table><tbody>
                              <tr><td>[01] भवन</td></tr>
                              <tr>
                                <td>..</td><td>..</td><td>1</td>
                                <td>लघु शीर्ष - 105 योग</td>
                                <td>1</td><td>..</td><td>1</td>
                              </tr>
                            </tbody></table>
                            """,
                        },
                    ]
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir) / "Volume 3a _ Capital Expenditure" / "results.json"
            results_path.parent.mkdir(parents=True)
            results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            matches = extractor._extract_surya_summary_matches_from_results(results_path)

        self.assertEqual(matches[0]["target"], "4202-04-105")
        self.assertEqual(matches[0]["selected_amount_thousand_rupees"], 1.0)

    def test_31_row_with_library_label_is_treated_as_library_row(self) -> None:
        line = "15             ..            1             ..              ..            .. 31- ु तकालय एवं              ध का     र             1             ..               1"
        match, _, _ = extractor.parse_target_line(
            line=line,
            current_major="2205",
            current_submajor="00",
            targets=_target_info(),
            canonical_map=_canonical_map(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.match_type, "line_hint")
        self.assertEqual(extractor._target_for_match(match, _canonical_map()), "2205-00-105")


class RepoRelativePathTests(unittest.TestCase):
    """Emitted records are tracked and public, so they must carry no absolute
    path. 115 of them did, across 18 files, and the org leak check refused
    every push from this repo until they were stripped."""

    def test_a_path_under_the_repo_becomes_relative(self):
        from publicfinance.rajasthan_observed_extract import REPO_ROOT, _repo_relative

        self.assertEqual(
            _repo_relative(REPO_ROOT / "data/state_budgets/Rajasthan/x.pdf"),
            "data/state_budgets/Rajasthan/x.pdf",
        )

    def test_the_data_symlink_does_not_defeat_it(self):
        """`data/` is a symlink to an external volume. An implementation that
        calls `resolve()` follows it, lands outside the repo root, fails the
        relative test and emits the absolute path — re-introducing the leak
        and adding the volume name to it."""
        from publicfinance.rajasthan_observed_extract import REPO_ROOT, _repo_relative

        result = _repo_relative(REPO_ROOT / "data/state_budgets/Rajasthan/x.pdf")
        # The forbidden strings are derived, never written literally: the leak
        # check reads this file too, and a test that spells out the pattern it
        # forbids blocks the very commit that fixes the leak.
        self.assertNotIn(str(Path.home()), result)
        self.assertNotIn(str(REPO_ROOT), result)
        self.assertFalse(Path(result).is_absolute())

    def test_an_already_relative_path_is_unchanged(self):
        from publicfinance.rajasthan_observed_extract import _repo_relative

        self.assertEqual(_repo_relative("data/x.pdf"), "data/x.pdf")

    def test_a_path_outside_the_repo_is_shown_not_truncated(self):
        from publicfinance.rajasthan_observed_extract import _repo_relative

        self.assertEqual(_repo_relative("/etc/hosts"), "/etc/hosts")


class ReferenceDataCarriesNoAbsolutePathTests(unittest.TestCase):
    """The committed reference JSONs are the artefact the leak check reads."""

    def test_no_observed_record_carries_a_home_path(self):
        from publicfinance.rajasthan_observed_extract import REPO_ROOT

        home = str(Path.home())
        offenders = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "references/lmmha/lod").rglob("*.json")
            if home in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])
