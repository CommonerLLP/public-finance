import json
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_base_2001.json"
LOD_DIR = REPO_ROOT / "references" / "lmmha" / "lod"
TIMELINE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_timeline.json"
SCOPE_NOTES_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_scope_notes_2001.json"
BASE_URI = "https://data.commonerllp.org/ontology/lmmha/"


def rows_from_base_json(heads):
    rows = []
    seen = {}

    for head in heads:
        code = str(head.get("code") or "").strip()
        parent_code = head.get("parent_code")
        if parent_code == "":
            parent_code = None

        row = {
            "code": code,
            "parent_code": parent_code,
            "type": str(head.get("type") or "").strip(),
            "label": str(head.get("label") or head.get("description") or "").strip(),
        }

        if not row["code"] or not row["type"] or not row["label"]:
            raise ValueError(f"Incomplete LMMHA row: {head!r}")

        existing = seen.get(row["code"])
        if existing:
            if existing != row:
                raise ValueError(f"Conflicting LMMHA code {row['code']}: {existing!r} != {row!r}")
            continue

        rows.append(row)
        seen[row["code"]] = row

    codes = set(seen)
    missing_parents = sorted({row["parent_code"] for row in rows if row["parent_code"] and row["parent_code"] not in codes})
    if missing_parents:
        raise ValueError(f"Missing parent LMMHA codes: {missing_parents}")

    return rows


def load_base_rows(path=BASE_JSON):
    with Path(path).open("r", encoding="utf-8") as f:
        return rows_from_base_json(json.load(f))


def load_json_payload(path):
    if not path:
        return []
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def payload_items(payload, key):
    if isinstance(payload, dict):
        return payload.get(key, [])
    return payload or []


def load_timeline(path=TIMELINE_JSON):
    return payload_items(load_json_payload(path), "events")


def load_scope_notes(path=SCOPE_NOTES_JSON):
    return payload_items(load_json_payload(path), "notes")


def build_graph(active_rows, timeline=None, scope_notes=None, base_uri=BASE_URI):
    timeline = payload_items(timeline, "events")
    scope_notes = payload_items(scope_notes, "notes")
    graph = Graph()
    prov = URIRef("http://www.w3.org/ns/prov#")
    prov_namespace = "http://www.w3.org/ns/prov#"

    graph.bind("lmmha", base_uri)
    graph.bind("skos", SKOS)
    graph.bind("dct", DCTERMS)
    graph.bind("owl", OWL)
    graph.bind("prov", prov_namespace)

    scheme_uri = URIRef(base_uri + "scheme")
    graph.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme_uri, DCTERMS.title, Literal("List of Major and Minor Heads of Account (LMMHA) - India, 2001 Base Edition", lang="en")))
    graph.add((
        scheme_uri,
        DCTERMS.description,
        Literal(
            "Machine-readable SKOS export of the Indian List of Major and Minor Heads of Account, with correction-slip history and source notes where available.",
            lang="en",
        ),
    ))

    cga_uri = URIRef("https://cga.nic.in")
    graph.add((scheme_uri, DCTERMS.publisher, cga_uri))
    graph.add((cga_uri, RDF.type, URIRef("http://xmlns.com/foaf/0.1/Organization")))
    graph.add((cga_uri, RDFS.label, Literal("Controller General of Accounts, Ministry of Finance", lang="en")))

    seen_codes = set()

    def concept_uri(code):
        return URIRef(base_uri + code)

    def add_concept(code, label, type_value, parent_code=None):
        uri = concept_uri(code)
        if code not in seen_codes:
            graph.add((uri, RDF.type, SKOS.Concept))
            graph.add((uri, SKOS.inScheme, scheme_uri))
            graph.add((uri, SKOS.prefLabel, Literal(label, lang="en")))
            graph.add((uri, DCTERMS.identifier, Literal(code)))
            if type_value:
                graph.add((uri, DCTERMS.type, Literal(type_value, lang="en")))
            if not parent_code:
                graph.add((scheme_uri, SKOS.hasTopConcept, uri))
                graph.add((uri, SKOS.topConceptOf, scheme_uri))
            seen_codes.add(code)

        if parent_code:
            parent_uri = concept_uri(parent_code)
            graph.add((uri, SKOS.broader, parent_uri))
            graph.add((parent_uri, SKOS.narrower, uri))

    for row in active_rows:
        add_concept(row["code"], row["label"], row["type"], row.get("parent_code"))

    for event in timeline:
        date_str = event["date"]
        message = event.get("message") or "correction slip"

        for change in event.get("changes", []):
            code = change["code"]
            uri = concept_uri(code)

            if code not in seen_codes:
                add_concept(code, change["label"], change["type"], change.get("parent_code"))

            if change["action"] == "INSERT":
                graph.add((uri, DCTERMS.created, Literal(date_str, datatype=XSD.date)))
                graph.add((uri, URIRef(str(prov) + "wasGeneratedBy"), Literal(f"Inserted via {message}", lang="en")))
            elif change["action"] == "DELETE":
                graph.add((uri, OWL.deprecated, Literal(True, datatype=XSD.boolean)))
                graph.add((uri, DCTERMS.modified, Literal(date_str, datatype=XSD.date)))
                graph.add((uri, URIRef(str(prov) + "wasInvalidatedBy"), Literal(f"Deleted via {message}", lang="en")))
            elif change["action"] == "RENAME":
                old_label = change.get("old_label")
                if old_label:
                    graph.add((uri, SKOS.altLabel, Literal(old_label, lang="en")))

                note = f"Renamed from '{old_label}' to '{change['label']}' on {date_str} via {message}"
                graph.add((uri, SKOS.historyNote, Literal(note, lang="en")))
                graph.add((uri, DCTERMS.modified, Literal(date_str, datatype=XSD.date)))
                graph.remove((uri, SKOS.prefLabel, None))
                graph.add((uri, SKOS.prefLabel, Literal(change["label"], lang="en")))
            elif change["action"] == "UPDATE":
                graph.add((uri, DCTERMS.modified, Literal(date_str, datatype=XSD.date)))
                graph.add((uri, SKOS.historyNote, Literal(f"Updated on {date_str} via {message}", lang="en")))

    for note in scope_notes:
        code = note.get("code")
        note_text = note.get("note")
        if not code or not note_text or code not in seen_codes:
            continue

        uri = concept_uri(code)
        graph.add((uri, SKOS.scopeNote, Literal(note_text, lang="en")))
        if note.get("source") or note.get("note_number"):
            source = f"LMMHA note {note.get('note_number', '').strip()}".strip()
            if note.get("source"):
                source = f"{source}, {note['source']}"
            graph.add((uri, DCTERMS.source, Literal(source, lang="en")))

    return graph


def export_skos(input_path=BASE_JSON, output_dir=LOD_DIR, timeline_path=TIMELINE_JSON, scope_notes_path=SCOPE_NOTES_JSON):
    active_rows = load_base_rows(input_path)
    timeline = load_timeline(timeline_path)
    scope_notes = load_scope_notes(scope_notes_path)
    graph = build_graph(active_rows, timeline, scope_notes)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ttl_path = output_dir / "lmmha.ttl"
    jsonld_path = output_dir / "lmmha.jsonld"
    graph.serialize(destination=ttl_path, format="turtle")
    graph.serialize(destination=jsonld_path, format="json-ld")

    print(f"Exported {len(active_rows)} LMMHA concepts to {ttl_path} and {jsonld_path}.")
    print(f"Graph contains {len(graph)} triples.")
    return graph


if __name__ == "__main__":
    export_skos()
