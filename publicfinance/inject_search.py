import html as html_lib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TIMELINE_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_timeline.json"
SCOPE_NOTES_JSON = REPO_ROOT / "references" / "lmmha" / "lmmha_scope_notes_2001.json"


def load_items(path, key):
    payload = load_payload(path)
    if isinstance(payload, dict):
        return payload.get(key, [])
    return payload or []


def load_payload(path):
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def escape(value):
    return html_lib.escape(str(value or ""), quote=True)


def add_toc_items(html):
    items = (
        '<li><a href="#how-to-read-lmmha">How to read LMMHA</a></li>'
        '<li><a href="#change-history">Change history</a></li>'
        '<li><a href="#scope-notes">Scope notes</a></li>'
    )
    if '<ul id="toc"></ul>' in html:
        return html.replace('<ul id="toc"></ul>', f'<ul id="toc">{items}</ul>', 1)
    if '<ul id="toc">' in html:
        return html.replace('<ul id="toc">', f'<ul id="toc">{items}', 1)
    return html


def render_reader_guide():
    return """
    <section id="how-to-read-lmmha" class="lmmha-public-section">
      <h2>How to read LMMHA</h2>
      <p>
        LMMHA is the Government of India's standard chart of accounts for classifying
        receipts, expenditure, loans, capital outlay, contingency fund entries, and
        public account transactions. It is a reporting rulebook, not only a glossary.
      </p>
      <p>
        A major head has a four-digit code. The first digit indicates the account
        family: 0 or 1 for revenue receipts, 2 or 3 for revenue expenditure, 4 or 5
        for capital expenditure, 6 or 7 for loans, 4000 for capital receipt, and 8
        for the Contingency Fund and Public Account.
      </p>
      <p>
        Under a major head, a two-digit sub-major head identifies a broad programme
        area where the list prescribes one. Under that, a three-digit minor head
        represents the programme, function, or standard classification used for
        reporting. The codes on this page therefore read as a path: major head,
        sub-major head when present, then minor head.
      </p>
      <p>
        Governments may divide prescribed minor heads into local sub-heads. A
        sub-head identifies a scheme or component of a programme, and should be
        opened only when needed for local reporting. This matters when comparing
        states: a state budget line for libraries should be assessed against the
        standard Public Libraries minor head, while the state's own scheme names
        belong at sub-head level.
      </p>
      <p>
        Formal correction-slip approval is not required for every new minor head.
        The directions allow some minor heads under standing paragraphs or generic
        project guidance, but footnote-based openings and other new heads still
        require formal approval through correction slips. Later state-budget checks
        should record this distinction instead of treating every local variation as
        the same kind of deviation.
      </p>
    </section>
    """


def change_label(change):
    action = change.get("action")
    code = escape(change.get("code"))
    label = escape(change.get("label"))
    old_label = escape(change.get("old_label"))

    if action == "RENAME" and old_label:
        return f'<span class="lmmha-change-action">RENAME</span> <code>{code}</code>: <del>{old_label}</del> &rarr; <ins>{label}</ins>'
    if action == "INSERT":
        return f'<span class="lmmha-change-action">ADD</span> <code>{code}</code>: {label}'
    if action == "DELETE":
        return f'<span class="lmmha-change-action">DROP</span> <code>{code}</code>: {label}'
    return f'<span class="lmmha-change-action">{escape(action)}</span> <code>{code}</code>: {label}'


def render_change_history(events, coverage_note=""):
    coverage = f"<p>{escape(coverage_note)}</p>" if coverage_note else ""
    if not events:
        body = "<p>No correction-slip timeline JSON was available when this HTML was generated.</p>"
    else:
        entries = []
        for event in reversed(events):
            changes = "\n".join(f"<li>{change_label(change)}</li>" for change in event.get("changes", []))
            if not changes:
                changes = "<li>No row-level change was recorded for this commit.</li>"
            entries.append(
                "<li>"
                "<details>"
                f"<summary><time>{escape(event.get('date'))}</time> {escape(event.get('message'))}</summary>"
                f"<ul>{changes}</ul>"
                "</details>"
                "</li>"
            )
        body = f"<ol class=\"lmmha-history-list\">{''.join(entries)}</ol>"

    return f"""
    <section id="change-history" class="lmmha-public-section">
      <h2>Correction-slip change history</h2>
      <p>
        These events come from the Dolt ledger used for this export. They make additions, drops,
        and renames visible beside the SKOS vocabulary so the public page is not
        frozen at the base edition.
      </p>
      {coverage}
      {body}
    </section>
    """


def render_scope_notes(notes, coverage_note=""):
    coverage = f"<p>{escape(coverage_note)}</p>" if coverage_note else ""
    if not notes:
        body = "<p>No extracted scope-note JSON was available when this HTML was generated.</p>"
    else:
        entries = []
        for note in notes:
            entries.append(
                "<li>"
                f"<code>{escape(note.get('code'))}</code> "
                f"<span class=\"lmmha-note-number\">note {escape(note.get('note_number'))}</span>: "
                f"{escape(note.get('note'))}"
                "</li>"
            )
        body = (
            "<details>"
            f"<summary>Show all extracted scope notes ({len(notes)})</summary>"
            f"<ul class=\"lmmha-scope-note-list\">{chr(10).join(entries)}</ul>"
            "</details>"
        )

    return f"""
    <section id="scope-notes" class="lmmha-public-section">
      <h2>LMMHA scope notes</h2>
      <p>
        Numbered notes explain how a head should be used. They are part of the
        accounting instruction, and are especially important when later comparing
        how different governments classify the same expenditure.
      </p>
      {coverage}
      {body}
    </section>
    """


def render_public_sections(events, notes, timeline_coverage="", notes_coverage=""):
    return (
        render_reader_guide()
        + render_change_history(events, coverage_note=timeline_coverage)
        + render_scope_notes(notes, coverage_note=notes_coverage)
    )


def search_widget():
    return """
    <!-- SEARCH WIDGET INJECTED -->
    <style>
        #lmmha-search-container {
            position: fixed;
            top: 20px;
            right: 200px;
            z-index: 9999;
            width: 300px;
            font-family: sans-serif;
        }
        #lmmha-search-input {
            width: 100%;
            padding: 10px;
            border: 2px solid #005A9C;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        #lmmha-search-results {
            position: absolute;
            top: 42px;
            left: 0;
            width: 100%;
            background: white;
            border: 1px solid #ccc;
            max-height: 400px;
            overflow-y: auto;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .lmmha-search-item {
            padding: 8px 10px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }
        .lmmha-search-item:hover {
            background-color: #f0f8ff;
        }
        .lmmha-search-item strong {
            color: #005A9C;
        }
        .lmmha-public-section {
            max-width: 980px;
            margin: 28px 0;
            padding: 18px 20px;
            border-left: 4px solid #005A9C;
            background: #f8fafc;
        }
        .lmmha-public-section h2 {
            margin-top: 0;
        }
        .lmmha-history-list,
        .lmmha-scope-note-list {
            padding-left: 1.4rem;
        }
        .lmmha-history-list details {
            margin: 8px 0;
        }
        .lmmha-change-action,
        .lmmha-note-number {
            font-weight: 700;
            color: #005A9C;
        }
        #pylode {
            display: none !important;
        }
        @media screen and (max-width: 800px) {
            body {
                padding-right: 10px !important;
                margin: 10px !important;
                padding-top: 70px !important;
            }
            #toc {
                position: static !important;
                width: 100% !important;
                border: 1px solid navy !important;
                height: auto !important;
                max-height: 300px !important;
                margin-bottom: 20px !important;
                padding: 10px !important;
                box-sizing: border-box !important;
            }
            #lmmha-search-container {
                right: 10px !important;
                top: 10px !important;
                width: calc(100% - 20px) !important;
            }
            table {
                display: block !important;
                overflow-x: auto !important;
            }
            td {
                white-space: normal !important;
                word-wrap: break-word !important;
            }
        }
    </style>

    <div id="lmmha-search-container">
        <input type="text" id="lmmha-search-input" placeholder="Search concepts (e.g. Public Libraries)..." />
        <div id="lmmha-search-results"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const input = document.getElementById('lmmha-search-input');
            const resultsContainer = document.getElementById('lmmha-search-results');

            const h3Elements = Array.from(document.querySelectorAll('h3[id]'));
            const index = h3Elements.map(h3 => {
                let text = h3.innerText.trim();
                let uriTr = h3.nextElementSibling;
                let iri = '';
                if (uriTr && uriTr.tagName.toLowerCase() === 'table') {
                    let codeNode = uriTr.querySelector('code');
                    if (codeNode) {
                        let iriText = codeNode.innerText.trim();
                        let parts = iriText.split('/');
                        iri = parts[parts.length - 1];
                    }
                }
                return {
                    id: h3.id,
                    text: text,
                    code: iri,
                    searchText: (text + ' ' + iri).toLowerCase()
                };
            });

            input.addEventListener('input', function(e) {
                const query = e.target.value.trim().toLowerCase();
                if (query.length < 2) {
                    resultsContainer.style.display = 'none';
                    return;
                }

                const matches = index.filter(item => item.searchText.includes(query)).slice(0, 50);

                if (matches.length > 0) {
                    resultsContainer.innerHTML = matches.map(match =>
                        `<div class="lmmha-search-item" data-id="${match.id}">
                            <strong>${match.code}</strong> - ${match.text}
                        </div>`
                    ).join('');
                    resultsContainer.style.display = 'block';
                } else {
                    resultsContainer.innerHTML = '<div class="lmmha-search-item">No results found</div>';
                    resultsContainer.style.display = 'block';
                }
            });

            resultsContainer.addEventListener('click', function(e) {
                const item = e.target.closest('.lmmha-search-item');
                if (item && item.dataset.id) {
                    const el = document.getElementById(item.dataset.id);
                    if (el) {
                        el.scrollIntoView({behavior: 'smooth'});
                        const originalColor = el.style.backgroundColor;
                        el.style.backgroundColor = '#ffff99';
                        setTimeout(() => {
                            el.style.backgroundColor = originalColor;
                        }, 2000);
                    }
                    resultsContainer.style.display = 'none';
                    input.value = '';
                }
            });

            document.addEventListener('click', function(e) {
                if (!e.target.closest('#lmmha-search-container')) {
                    resultsContainer.style.display = 'none';
                }
            });
        });
    </script>
    """


def insert_after_first_h1(html, content):
    marker = "</h1>"
    if marker in html:
        return html.replace(marker, marker + "\n" + content, 1)
    if "<body>" in html:
        return html.replace("<body>", "<body>\n" + content, 1)
    return content + html


def inject_search(html_path, timeline_path=None, scope_notes_path=None, notes_path=None):
    html_path = Path(html_path)
    html = html_path.read_text(encoding="utf-8")

    timeline_path = TIMELINE_JSON if timeline_path is None else timeline_path
    scope_notes_path = notes_path or (SCOPE_NOTES_JSON if scope_notes_path is None else scope_notes_path)

    timeline_payload = load_payload(timeline_path)
    notes_payload = load_payload(scope_notes_path)
    events = timeline_payload.get("events", []) if isinstance(timeline_payload, dict) else timeline_payload or []
    notes = notes_payload.get("notes", []) if isinstance(notes_payload, dict) else notes_payload or []
    public_sections = render_public_sections(
        events,
        notes,
        timeline_coverage=timeline_payload.get("coverage_note", "") if isinstance(timeline_payload, dict) else "",
        notes_coverage=notes_payload.get("coverage_note", "") if isinstance(notes_payload, dict) else "",
    )

    html = add_toc_items(html)
    html = insert_after_first_h1(html, public_sections)

    widget = search_widget()
    if "</body>" in html:
        html = html.replace("</body>", widget + "\n</body>", 1)
    else:
        html += widget

    html = html.replace('<li><a href="#legend">Legend</a></li>', "")
    html = html.replace('<p style="text-align: right;">', '<p style="text-align: center;">')
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"

    html_path.write_text(html, encoding="utf-8")
    print(f"Search widget and LMMHA public sections injected into {html_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        inject_search(sys.argv[1])
    else:
        inject_search("references/lmmha/lod/index.html")
