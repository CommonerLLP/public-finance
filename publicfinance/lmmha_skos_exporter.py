import json
import os
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF, DCTERMS

def export_to_skos(json_path, output_dir):
    # Initialize Graph
    g = Graph()
    
    # Define our namespace
    LMMHA = Namespace("https://data.commonerllp.org/ontology/lmmha/")
    g.bind("lmmha", LMMHA)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)

    # Create the overall Concept Scheme
    scheme_uri = LMMHA["scheme"]
    g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((scheme_uri, DCTERMS.title, Literal("List of Major and Minor Heads of Account (LMMHA)", lang="en")))
    g.add((scheme_uri, DCTERMS.publisher, Literal("Controller General of Accounts, India", lang="en")))

    with open(json_path, 'r') as f:
        data = json.load(f)

    for major_code, major_data in data.items():
        major_uri = LMMHA[f"major/{major_code}"]
        g.add((major_uri, RDF.type, SKOS.Concept))
        g.add((major_uri, SKOS.prefLabel, Literal(major_data['name'], lang="en")))
        g.add((major_uri, SKOS.notation, Literal(major_code)))
        g.add((major_uri, SKOS.inScheme, scheme_uri))
        g.add((scheme_uri, SKOS.hasTopConcept, major_uri))

        # Handle Sub-Majors
        for sub_code, sub_data in major_data.get('submajors', {}).items():
            sub_uri = LMMHA[f"submajor/{major_code}-{sub_code}"]
            g.add((sub_uri, RDF.type, SKOS.Concept))
            g.add((sub_uri, SKOS.prefLabel, Literal(sub_data['name'], lang="en")))
            g.add((sub_uri, SKOS.notation, Literal(sub_code)))
            g.add((sub_uri, SKOS.inScheme, scheme_uri))
            g.add((sub_uri, SKOS.broader, major_uri))
            g.add((major_uri, SKOS.narrower, sub_uri))

            # Handle Minors under Sub-Majors
            for minor_code, minor_name in sub_data.get('minors', {}).items():
                minor_uri = LMMHA[f"minor/{major_code}-{sub_code}-{minor_code}"]
                g.add((minor_uri, RDF.type, SKOS.Concept))
                g.add((minor_uri, SKOS.prefLabel, Literal(minor_name, lang="en")))
                g.add((minor_uri, SKOS.notation, Literal(minor_code)))
                g.add((minor_uri, SKOS.inScheme, scheme_uri))
                g.add((minor_uri, SKOS.broader, sub_uri))
                g.add((sub_uri, SKOS.narrower, minor_uri))

        # Handle Minors directly under Majors
        for minor_code, minor_name in major_data.get('minors', {}).items():
            minor_uri = LMMHA[f"minor/{major_code}-00-{minor_code}"]
            g.add((minor_uri, RDF.type, SKOS.Concept))
            g.add((minor_uri, SKOS.prefLabel, Literal(minor_name, lang="en")))
            g.add((minor_uri, SKOS.notation, Literal(minor_code)))
            g.add((minor_uri, SKOS.inScheme, scheme_uri))
            g.add((minor_uri, SKOS.broader, major_uri))
            g.add((major_uri, SKOS.narrower, minor_uri))

    # Add specific Wikidata links for demonstration (5-Star requirement)
    # GST mapping
    igst_uri = LMMHA["major/0008"]
    WD = Namespace("http://www.wikidata.org/entity/")
    g.add((igst_uri, SKOS.exactMatch, WD.Q5583000)) # Goods and Services Tax in India
    g.add((igst_uri, SKOS.broader, WD.Q8161)) # Tax

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Save to Turtle
    turtle_path = os.path.join(output_dir, 'lmmha.ttl')
    g.serialize(destination=turtle_path, format='turtle')

    # Save to JSON-LD
    jsonld_path = os.path.join(output_dir, 'lmmha.jsonld')
    g.serialize(destination=jsonld_path, format='json-ld', indent=2)

    print(f"✅ Successfully exported {len(data)} Major Heads to SKOS (Turtle & JSON-LD)")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    json_path = 'references/lmmha/lmmha_clean.json'
    output_dir = 'references/lmmha/lod'
    export_to_skos(json_path, output_dir)
