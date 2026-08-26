from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_citation_license_matches_code_license():
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    assert "license: AGPL-3.0-only" in citation
    assert "PolyForm-Noncommercial" not in citation
    assert "ODbL" not in citation
    assert "CC BY-NC-SA" not in citation


def test_data_license_excludes_third_party_source_material():
    data_license = (ROOT / "DATA-LICENSE").read_text(encoding="utf-8")

    assert "everything under `references/`" not in data_license
    assert "Third-party and source material is excluded" in data_license
    assert "CommonerLLP grants rights only for material" in data_license


def test_readme_license_summary_matches_license_files():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "[AGPL-3.0](LICENSE)" in readme
    assert "[CC-BY-4.0](DATA-LICENSE)" in readme
