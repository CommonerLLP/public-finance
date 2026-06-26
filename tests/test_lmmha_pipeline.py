import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, SKOS, XSD

from publicfinance import extract_correction_slips, inject_search, lmmha_history, lmmha_notes, lmmha_skos_exporter, parse_base_lmmha


class LMMHAPipelineTests(unittest.TestCase):
    def test_base_parser_preserves_submajor_in_minor_identity(self):
        html = """
        <html><body>
        <table>
          <tr><td>MAJOR / SUB-MAJOR HEADS</td><td></td><td>MINOR HEADS</td><td></td></tr>
          <tr><td><p><b><i>4202</i></b></p></td><td><p><b><i>Capital Outlay on Education, Sports, Art and Culture</i></b></p></td><td></td><td></td></tr>
          <tr><td></td><td><p><i>02 Technical Education</i></p></td><td></td><td></td></tr>
          <tr><td></td><td></td><td><p>105</p></td><td><p>Engineering Technical Colleges and Institutes</p></td></tr>
          <tr><td></td><td><p><i>04 Art and Culture</i></p></td><td><p>105</p></td><td><p>Public Libraries (1)</p></td></tr>
          <tr><td><p><b><i>2205</i></b></p></td><td><p><b><i>Art and Culture</i></b></p></td><td></td><td></td></tr>
          <tr><td></td><td></td><td><p>105</p></td><td><p>Public Libraries</p></td></tr>
          <tr><td><p><b><i>0575</i></b></p></td><td colspan="3"><p><b><i>Other Special Areas programmes</i></b></p></td></tr>
          <tr><td></td><td><p><i>01 Dangs District</i></p></td><td></td><td></td></tr>
          <tr><td><p><b><i>1055</i></b></p></td><td><p><b><i>Road Transport</i></b></p></td><td colspan="2"><p>Each Departmental undertaking will be a minor head</p></td></tr>
          <tr><td></td><td></td><td><p>101</p></td><td><p>Receipts under Rail Road Coordination</p></td></tr>
          <tr><td><p><b><i>2235</i></b></p></td><td><p><b><i>Social Security and Welfare</i></b></p></td><td></td><td></td></tr>
          <tr><td></td><td><p><i>01 Rehabilitation (1)</i></p></td><td><p>101</p></td><td><p>Dandakamaya Development Scheme</p></td></tr>
          <tr><td></td><td><p><i>02-Social Welfare (3)</i></p></td><td></td><td></td></tr>
          <tr><td></td><td></td><td><p>101</p></td><td><p>Welfare of handicapped</p></td></tr>
        </table>
        </body></html>
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)
            output_path = input_dir / "lmmha_base_2001.json"
            (input_dir / "part-test.htm").write_text(html, encoding="utf-8")

            heads = parse_base_lmmha.parse_html_files(input_dir=input_dir, output_path=output_path)
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        by_code = {head["code"]: head for head in heads}
        self.assertEqual(by_code["4202-02-105"]["description"], "Engineering Technical Colleges and Institutes")
        self.assertEqual(by_code["4202-04-105"]["description"], "Public Libraries")
        self.assertEqual(by_code["2205-00-105"]["description"], "Public Libraries")
        self.assertEqual(by_code["4202-04"]["type"], "Sub-Major Head")
        self.assertEqual(by_code["4202-04-105"]["parent_code"], "4202-04")
        self.assertEqual(by_code["2205-00-105"]["parent_code"], "2205")
        self.assertEqual(by_code["0575-01"]["description"], "Dangs District")
        self.assertNotIn("2205-01", by_code)
        self.assertEqual(by_code["1055-00-101"]["description"], "Receipts under Rail Road Coordination")
        self.assertNotIn("0575-00-101", by_code)
        self.assertEqual(by_code["2235-01-101"]["description"], "Dandakamaya Development Scheme")
        self.assertEqual(by_code["2235-02-101"]["description"], "Welfare of handicapped")
        self.assertEqual(len(by_code), len(heads))

        self.assertEqual(saved, heads)

    def test_correction_slip_normalization_preserves_submajor_context(self):
        minor_change = {
            "action": "INSERT",
            "major_head": "4202",
            "sub_major_head": "04",
            "minor_head": "105",
            "label": "Public Libraries",
        }
        direct_minor_change = {
            "action": "INSERT",
            "major_head": "2205",
            "minor_head": "105",
            "label": "Public Libraries",
        }

        self.assertEqual(
            extract_correction_slips.normalise_change(minor_change),
            {
                "action": "INSERT",
                "code": "4202-04-105",
                "parent_code": "4202-04",
                "type": "Minor Head",
                "label": "Public Libraries",
                "is_receipt": 0,
                "is_expenditure": 1,
            },
        )
        self.assertEqual(
            extract_correction_slips.normalise_change(direct_minor_change)["code"],
            "2205-00-105",
        )

    def test_skos_graph_uses_submajor_hierarchy(self):
        graph = lmmha_skos_exporter.build_graph(
            active_rows=[
                {"code": "4202", "parent_code": None, "type": "Major Head", "label": "Capital Outlay on Education, Sports, Art and Culture"},
                {"code": "4202-04", "parent_code": "4202", "type": "Sub-Major Head", "label": "Art and Culture"},
                {"code": "4202-04-105", "parent_code": "4202-04", "type": "Minor Head", "label": "Public Libraries"},
            ],
            timeline=[],
            base_uri="https://data.commonerllp.org/ontology/lmmha/",
        )

        base = "https://data.commonerllp.org/ontology/lmmha/"
        major_uri = URIRef(base + "4202")
        submajor_uri = URIRef(base + "4202-04")
        minor_uri = URIRef(base + "4202-04-105")
        self.assertIn((submajor_uri, SKOS.broader, major_uri), graph)
        self.assertIn((minor_uri, SKOS.broader, submajor_uri), graph)
        self.assertNotIn((minor_uri, SKOS.broader, major_uri), graph)

    def test_exporter_rows_from_base_json_preserve_parent_codes(self):
        rows = lmmha_skos_exporter.rows_from_base_json([
            {"code": "4202", "parent_code": None, "type": "Major Head", "description": "Capital Outlay"},
            {"code": "4202-04", "parent_code": "4202", "type": "Sub-Major Head", "description": "Art and Culture"},
            {"code": "4202-04-105", "parent_code": "4202-04", "type": "Minor Head", "description": "Public Libraries"},
        ])

        self.assertEqual(
            rows[2],
            {"code": "4202-04-105", "parent_code": "4202-04", "type": "Minor Head", "label": "Public Libraries"},
        )

    def test_dolt_diff_rows_become_timeline_changes(self):
        modified = {
            "to_code": "0020",
            "to_parent_code": None,
            "to_type": "Major Head",
            "to_label": "Corporate Tax",
            "from_code": "0020",
            "from_parent_code": None,
            "from_type": "Major Head",
            "from_label": "Corporation Tax",
            "diff_type": "modified",
        }
        added = {
            "to_code": "0075-109",
            "to_parent_code": "0075",
            "to_type": "Minor Head",
            "to_label": "Penal Guarantee Fees",
            "from_code": None,
            "from_parent_code": None,
            "from_type": None,
            "from_label": None,
            "diff_type": "added",
        }
        removed = {
            "to_code": None,
            "to_parent_code": None,
            "to_type": None,
            "to_label": None,
            "from_code": "3053-01-191",
            "from_parent_code": "3053-01",
            "from_type": "Minor Head",
            "from_label": "Schemes for NE Region",
            "diff_type": "removed",
        }

        self.assertEqual(
            lmmha_history.change_from_diff_row(modified),
            {
                "action": "RENAME",
                "code": "0020",
                "parent_code": None,
                "type": "Major Head",
                "label": "Corporate Tax",
                "old_label": "Corporation Tax",
            },
        )
        self.assertEqual(lmmha_history.change_from_diff_row(added)["action"], "INSERT")
        self.assertEqual(lmmha_history.change_from_diff_row(removed)["action"], "DELETE")

    def test_history_extracts_government_correction_slip_numbers(self):
        self.assertEqual(
            lmmha_history.extract_slip_numbers(
                "Correction Slip: Correction Slip Number 1106 dated 09 06 2026 to the LMMHA 1963"
            ),
            ["1106"],
        )
        self.assertEqual(
            lmmha_history.extract_slip_numbers(
                "Correction Slip: Correction Slip Numbers from 1102 to 1105 dated 22 May 2026 1962"
            ),
            ["1102", "1103", "1104", "1105"],
        )
        self.assertEqual(
            lmmha_history.extract_slip_numbers("Correction Slip: Correction Slips No 655 662 389"),
            ["655", "656", "657", "658", "659", "660", "661", "662"],
        )
        self.assertEqual(
            lmmha_history.slip_label("Correction Slip: Correction Slips No 655 662 389"),
            "Correction Slip Nos. 655-662",
        )
        self.assertEqual(
            lmmha_history.slip_label("Correction Slip: Corrigendum to Correction Slip No 1027 Dated 7th February 2024 1882"),
            "Corrigendum to Correction Slip No. 1027",
        )
        self.assertEqual(
            lmmha_history.extract_slip_numbers("Correction Slip: Regarding CS 730   734 420"),
            ["730", "734"],
        )
        self.assertEqual(
            lmmha_history.slip_label("Correction Slip: Regarding CS 730   734 420"),
            "Correction Slip Nos. 730, 734",
        )
        self.assertEqual(
            lmmha_history.source_entry_label("Correction Slip: Transactory and Parking Heads 381"),
            "Transactory and Parking Heads",
        )
        self.assertEqual(
            lmmha_history.public_event_message("Correction Slip: Correction Slips No 655 662 389"),
            "Correction Slip Nos. 655-662",
        )

    def test_skos_graph_includes_timeline_metadata(self):
        graph = lmmha_skos_exporter.build_graph(
            active_rows=[
                {"code": "0020", "parent_code": None, "type": "Major Head", "label": "Corporation Tax"},
                {"code": "0075", "parent_code": None, "type": "Major Head", "label": "Miscellaneous General Services"},
            ],
            timeline=[
                {
                    "date": "2026-05-22",
                    "message": "Correction Slip: rename 0020",
                    "changes": [
                        {
                            "action": "RENAME",
                            "code": "0020",
                            "parent_code": None,
                            "type": "Major Head",
                            "label": "Corporate Tax",
                            "old_label": "Corporation Tax",
                        }
                    ],
                },
                {
                    "date": "2026-06-09",
                    "message": "Correction Slip: add 0075-109",
                    "changes": [
                        {
                            "action": "INSERT",
                            "code": "0075-109",
                            "parent_code": "0075",
                            "type": "Minor Head",
                            "label": "Penal Guarantee Fees",
                        }
                    ],
                },
                {
                    "date": "2026-03-27",
                    "message": "Correction Slip: retire 3053-01-191",
                    "changes": [
                        {
                            "action": "DELETE",
                            "code": "3053-01-191",
                            "parent_code": "3053-01",
                            "type": "Minor Head",
                            "label": "Schemes for NE Region",
                        }
                    ],
                },
            ],
            base_uri="https://data.commonerllp.org/ontology/lmmha/",
        )

        base = "https://data.commonerllp.org/ontology/lmmha/"
        renamed_uri = URIRef(base + "0020")
        added_uri = URIRef(base + "0075-109")
        removed_uri = URIRef(base + "3053-01-191")

        self.assertIn((renamed_uri, SKOS.prefLabel, Literal("Corporate Tax", lang="en")), graph)
        self.assertIn((renamed_uri, SKOS.altLabel, Literal("Corporation Tax", lang="en")), graph)
        self.assertIn((added_uri, DCTERMS.created, Literal("2026-06-09", datatype=XSD.date)), graph)
        self.assertIn((removed_uri, OWL.deprecated, Literal(True)), graph)

    def test_skos_graph_includes_scope_notes(self):
        graph = lmmha_skos_exporter.build_graph(
            active_rows=[
                {"code": "2205", "parent_code": None, "type": "Major Head", "label": "Art and Culture"},
                {"code": "2205-00-105", "parent_code": "2205", "type": "Minor Head", "label": "Public Libraries"},
            ],
            timeline=[],
            scope_notes=[
                {
                    "code": "2205-00-105",
                    "note_number": "5",
                    "note": "This minor head will include expenditure on public libraries.",
                    "source": "part2b.htm",
                }
            ],
            base_uri="https://data.commonerllp.org/ontology/lmmha/",
        )

        self.assertIn(
            (
                URIRef("https://data.commonerllp.org/ontology/lmmha/2205-00-105"),
                SKOS.scopeNote,
                Literal("This minor head will include expenditure on public libraries.", lang="en"),
            ),
            graph,
        )

    def test_scope_note_parser_attaches_numbered_notes_to_codes(self):
        html = """
        <html><body>
        <table>
          <tr><td>MAJOR / SUB-MAJOR HEADS</td><td></td><td>MINOR HEADS</td><td></td></tr>
          <tr><td><p><b><i>2205</i></b></p></td><td><p><b><i>Art and Culture (1)</i></b></p></td><td></td><td></td></tr>
          <tr><td></td><td></td><td><p>101</p></td><td><p>Fine Arts Education (2)</p></td></tr>
          <tr><td></td><td></td><td><p>103</p></td><td><p>Archaeology (4)</p></td></tr>
          <tr><td></td><td></td><td><p>105</p></td><td><p>Public Libraries (5)</p></td></tr>
          <tr><td></td><td></td><td><p>106</p></td><td><p>Archaeological Survey (4)</p></td></tr>
        </table>
        <p><b>Notes:</b></p>
        <p>(1) This major head will record transactions connected with promotion of art and culture.</p>
        <p>(2) This minor head will record expenditure on government institutions for fine arts education.</p>
        <p>(4) Archaeology records State Government archaeology; Archaeological Survey records ASI expenditure.</p>
        <p>(5) This minor head will include expenditure on public libraries.</p>
        </body></html>
        """

        notes = lmmha_notes.parse_html_string(html, source_name="part-test.htm")
        by_code_number = {(note["code"], note["note_number"]): note["note"] for note in notes}

        self.assertIn(("2205", "1"), by_code_number)
        self.assertIn(("2205-00-101", "2"), by_code_number)
        self.assertIn(("2205-00-103", "4"), by_code_number)
        self.assertIn(("2205-00-106", "4"), by_code_number)
        self.assertEqual(
            by_code_number[("2205-00-105", "5")],
            "This minor head will include expenditure on public libraries.",
        )

    def test_inject_search_adds_visible_change_history(self):
        html = "<html><body><ul id=\"toc\"></ul><h1>LMMHA</h1></body></html>"
        timeline = {
            "generated_by": "publicfinance/lmmha_history.py",
            "events": [
                {
                    "date": "2026-05-22",
                    "message": "Correction Slip: rename 0020",
                    "changes": [
                        {
                            "action": "RENAME",
                            "code": "0020",
                            "label": "Corporate Tax",
                            "old_label": "Corporation Tax",
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "index.html"
            timeline_path = Path(tmpdir) / "lmmha_timeline.json"
            html_path.write_text(html, encoding="utf-8")
            timeline_path.write_text(json.dumps(timeline), encoding="utf-8")

            inject_search.inject_search(html_path, timeline_path=timeline_path)
            output = html_path.read_text(encoding="utf-8")

        self.assertIn('id="change-history"', output)
        self.assertIn("Correction Slip: rename 0020", output)
        self.assertIn("Corporation Tax", output)
        self.assertIn("Corporate Tax", output)

    def test_inject_search_uses_official_correction_slip_label(self):
        html = "<html><body><ul id=\"toc\"></ul><h1>LMMHA</h1></body></html>"
        timeline = {
            "generated_by": "publicfinance/lmmha_history.py",
            "events": [
                {
                    "date": "2026-05-22",
                    "message": "Correction Slip: Correction Slip Numbers from 1102 to 1105 dated 22 May 2026 to the LMMHA for change in nomenclature of MH 0020 Corporation Tax to 0020 Corporate Tax 1962",
                    "slip_numbers": ["1102", "1103", "1104", "1105"],
                    "slip_label": "Correction Slip Nos. 1102-1105",
                    "changes": [
                        {
                            "action": "RENAME",
                            "code": "0020",
                            "label": "Corporate Tax",
                            "old_label": "Corporation Tax",
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "index.html"
            timeline_path = Path(tmpdir) / "lmmha_timeline.json"
            html_path.write_text(html, encoding="utf-8")
            timeline_path.write_text(json.dumps(timeline), encoding="utf-8")

            inject_search.inject_search(html_path, timeline_path=timeline_path)
            output = html_path.read_text(encoding="utf-8")

        self.assertIn("Correction Slip Nos. 1102-1105", output)

    def test_inject_search_adds_reader_guide_and_scope_notes(self):
        html = "<html><body><ul id=\"toc\"></ul><h1>LMMHA</h1></body></html>"
        notes_payload = {
            "generated_by": "publicfinance/lmmha_notes.py",
            "notes": [
                {
                    "code": "2205-00-105",
                    "note_number": "5",
                    "note": "This minor head will include expenditure on public libraries.",
                    "source": "part2b.htm",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "index.html"
            notes_path = Path(tmpdir) / "lmmha_scope_notes_2001.json"
            html_path.write_text(html, encoding="utf-8")
            notes_path.write_text(json.dumps(notes_payload), encoding="utf-8")

            inject_search.inject_search(html_path, scope_notes_path=notes_path)
            output = html_path.read_text(encoding="utf-8")

        self.assertIn('id="how-to-read-lmmha"', output)
        self.assertIn("LMMHA = List of Major and Minor Heads of Account", output)
        self.assertIn("first digit", output)
        self.assertIn("sub-head", output)
        self.assertIn("Formal correction-slip approval", output)
        self.assertIn('id="scope-notes"', output)
        self.assertIn("2205-00-105", output)
        self.assertIn("public libraries", output)

    def test_public_lmmha_about_page_cites_constitutional_finance_frame(self):
        html_path = Path("references/lmmha/lod/index.html")
        output = html_path.read_text(encoding="utf-8")

        self.assertIn('id="a-constitutional-finance"', output)
        self.assertIn("Consolidated Fund of India", output)
        self.assertIn("Articles 112", output)
        self.assertIn("Articles 266", output)
        self.assertIn("Article 280", output)
        self.assertIn("Finance Commission", output)
        self.assertIn("constitutional morality", output)
        self.assertIn("small public-interest layer", output)
        self.assertIn("whether States are reporting", output)
        self.assertIn('id="a-1987-archive"', output)
        self.assertIn("https://elibrary.sansad.in/handle/123456789/53283", output)
        self.assertIn("Sansad Library", output)
        self.assertNotIn("eLibrary Sansad", output)
        self.assertNotIn(">eLibrary", output)
        self.assertIn('class="external-link"', output)
        self.assertIn('target="_blank"', output)
        self.assertIn('rel="noopener noreferrer"', output)
        self.assertIn("The first LMMHA edition is preserved", output)
        self.assertIn("basic transparency problem", output)
        self.assertIn("1 April 1974", output)
        self.assertIn("1 April 1987", output)
        self.assertIn("three digits to four digits", output)
        self.assertIn("Article 150", output)
        self.assertIn("88,944,846", output)
        self.assertIn("21b6ed7bf7712b6f4b78bb3f2cbcb4a0", output)
        self.assertIn("BAWS Vol. 6", output)
        self.assertIn("BAWS Vol. 13", output)
        self.assertIn('class="external-link" href="https://www.legislative.gov.in/constitution-of-india" target="_blank" rel="noopener noreferrer"', output)

    def test_public_timeline_tab_has_correction_action_filters(self):
        script = Path("references/lmmha/lod/app.js").read_text(encoding="utf-8")

        self.assertIn("timelineAction", script)
        self.assertIn('timelineFilterButton("Insertions", "INSERT"', script)
        self.assertIn('timelineFilterButton("Renames", "RENAME"', script)
        self.assertIn('timelineFilterButton("Deletions", "DELETE"', script)
        self.assertIn("showYearEvents(year, events, actionFilter", script)
        self.assertIn('data-action="${esc(ch.action)}"', script)
        self.assertIn("const latestYear = years[years.length - 1]", script)


if __name__ == "__main__":
    unittest.main()
