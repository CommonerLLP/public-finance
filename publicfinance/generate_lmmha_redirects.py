import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_base_2001.json"
LOD_DIR = REPO_ROOT / "references" / "lmmha" / "lod"


def safe_anchor(code):
    return f"lmmha_{code}"


def redirect_html(code, title):
    target = f"/index.html#{safe_anchor(code)}"
    escaped_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escaped_title}</title>
  <link rel="canonical" href="{target}">
  <meta http-equiv="refresh" content="0; url={target}">
</head>
<body>
  <p><a href="{target}">{escaped_title}</a></p>
</body>
</html>
"""


def write_redirect(root, parts, code, title):
    path = root.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(redirect_html(code, title), encoding="utf-8")


def alias_kind(type_value):
    if type_value == "Major Head":
        return "major"
    if type_value == "Sub-Major Head":
        return "submajor"
    if type_value == "Minor Head":
        return "minor"
    raise ValueError(f"Unsupported LMMHA type: {type_value!r}")


def generate_redirects(input_path=BASE_JSON, output_dir=LOD_DIR):
    with Path(input_path).open("r", encoding="utf-8") as f:
        heads = json.load(f)

    output_dir = Path(output_dir)
    uri_root = output_dir / "ontology" / "lmmha"

    for head in heads:
        code = head["code"]
        title = head.get("description") or head.get("label") or code
        write_redirect(uri_root, [code], code, title)
        write_redirect(uri_root, [alias_kind(head["type"]), code], code, title)

    print(f"Generated {len(heads) * 2} LMMHA URI redirect pages under {uri_root}.")


if __name__ == "__main__":
    generate_redirects()
