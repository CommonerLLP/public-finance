import json
import tempfile
import unittest
from pathlib import Path

from rdflib import URIRef
from rdflib.namespace import SKOS

from publicfinance import extract_correction_slips, lmmha_skos_exporter, parse_base_lmmha


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


if __name__ == "__main__":
    unittest.main()
