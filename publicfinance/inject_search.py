import os
import sys

def inject_search(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Search widget HTML + JS
    search_code = """
    <!-- SEARCH WIDGET INJECTED -->
    <style>
        #lmmha-search-container {
            position: fixed;
            top: 20px;
            right: 200px; /* Left of the TOC */
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

        /* Hide the PyLODE watermark universally */
        #pylode {
            display: none !important; 
        }

        /* Responsive overrides for PyLODE */
        @media screen and (max-width: 800px) {
            body {
                padding-right: 10px !important;
                margin: 10px !important;
                padding-top: 70px !important; /* space for search bar */
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
            
            // Build index from all h3 elements with ids
            const h3Elements = Array.from(document.querySelectorAll('h3[id]'));
            const index = h3Elements.map(h3 => {
                let text = h3.innerText.trim();
                let uriTr = h3.nextElementSibling;
                let iri = '';
                if (uriTr && uriTr.tagName.toLowerCase() === 'table') {
                    let codeNode = uriTr.querySelector('code');
                    if (codeNode) {
                        let iriText = codeNode.innerText.trim();
                        // Extract code from the end of the IRI (e.g. 2205-00-105)
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
                        // Highlight briefly
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
    
    # Insert right before </body>
    if '</body>' in html:
        html = html.replace('</body>', search_code + '\n</body>')
    else:
        # Fallback just append
        html += search_code
        
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    print(f"Search widget injected into {html_path}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        inject_search(sys.argv[1])
    else:
        inject_search('references/lmmha/lod/index.html')
