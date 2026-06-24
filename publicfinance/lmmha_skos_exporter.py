import json
import os
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF, DCTERMS, SDO

def export_to_skos(json_path, output_dir):
    # Initialize Graph
    g = Graph()
    
    # Define our namespaces
    LMMHA = Namespace("https://data.commonerllp.org/ontology/lmmha/")
    LMMHA_MAJOR = Namespace("https://data.commonerllp.org/ontology/lmmha/major/")
    LMMHA_MINOR = Namespace("https://data.commonerllp.org/ontology/lmmha/minor/")
    LMMHA_SUBMAJOR = Namespace("https://data.commonerllp.org/ontology/lmmha/submajor/")
    WD = Namespace("http://www.wikidata.org/entity/")

    g.bind("lmmha", LMMHA)
    g.bind("lmmha-major", LMMHA_MAJOR)
    g.bind("lmmha-minor", LMMHA_MINOR)
    g.bind("lmmha-submajor", LMMHA_SUBMAJOR)
    g.bind("wd", WD)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)

    # Create the overall Concept Scheme
    scheme_uri = LMMHA["scheme"]
    g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((scheme_uri, DCTERMS.title, Literal("List of Major and Minor Heads of Account (LMMHA)", lang="en")))
    cga_uri = URIRef("https://cga.nic.in/")
    g.add((scheme_uri, DCTERMS.publisher, cga_uri))
    g.add((cga_uri, RDF.type, SDO.Organization))
    g.add((cga_uri, SDO.name, Literal("Controller General of Accounts, India", lang="en")))

    with open(json_path, 'r') as f:
        data = json.load(f)

    for major_code, major_data in data.items():
        major_uri = LMMHA_MAJOR[major_code]
        g.add((major_uri, RDF.type, SKOS.Concept))
        g.add((major_uri, SKOS.prefLabel, Literal(major_data['name'].strip(), lang="en")))
        g.add((major_uri, SKOS.notation, Literal(major_code)))
        g.add((major_uri, SKOS.inScheme, scheme_uri))
        g.add((scheme_uri, SKOS.hasTopConcept, major_uri))

        # Handle Sub-Majors
        for sub_code, sub_data in major_data.get('submajors', {}).items():
            sub_uri = LMMHA_SUBMAJOR[f"{major_code}-{sub_code}"]
            g.add((sub_uri, RDF.type, SKOS.Concept))
            g.add((sub_uri, SKOS.prefLabel, Literal(sub_data['name'].strip(), lang="en")))
            g.add((sub_uri, SKOS.notation, Literal(sub_code)))
            g.add((sub_uri, SKOS.inScheme, scheme_uri))
            g.add((sub_uri, SKOS.broader, major_uri))
            g.add((major_uri, SKOS.narrower, sub_uri))

            # Handle Minors under Sub-Majors
            for minor_code, minor_name in sub_data.get('minors', {}).items():
                minor_uri = LMMHA_MINOR[f"{major_code}-{sub_code}-{minor_code}"]
                g.add((minor_uri, RDF.type, SKOS.Concept))
                g.add((minor_uri, SKOS.prefLabel, Literal(minor_name.strip(), lang="en")))
                g.add((minor_uri, SKOS.notation, Literal(minor_code)))
                g.add((minor_uri, SKOS.inScheme, scheme_uri))
                
                if major_code == "2205" and minor_code == "105":
                    wikidata_public_library = URIRef("http://www.wikidata.org/entity/Q2855589")
                    g.add((minor_uri, SKOS.exactMatch, wikidata_public_library))

                g.add((minor_uri, SKOS.broader, sub_uri))
                g.add((sub_uri, SKOS.narrower, minor_uri))

        # Handle Minors directly under Majors
        for minor_code, minor_name in major_data.get('minors', {}).items():
            minor_uri = LMMHA_MINOR[f"{major_code}-00-{minor_code}"]
            g.add((minor_uri, RDF.type, SKOS.Concept))
            g.add((minor_uri, SKOS.prefLabel, Literal(minor_name.strip(), lang="en")))
            g.add((minor_uri, SKOS.notation, Literal(minor_code)))
            g.add((minor_uri, SKOS.inScheme, scheme_uri))
            
            if major_code == "2205" and minor_code == "105":
                wikidata_public_library = URIRef("http://www.wikidata.org/entity/Q2855589")
                g.add((minor_uri, SKOS.exactMatch, wikidata_public_library))

            g.add((minor_uri, SKOS.broader, major_uri))
            g.add((major_uri, SKOS.narrower, minor_uri))

    # Add specific Wikidata links for demonstration
    igst_uri = LMMHA_MAJOR["0008"]
    g.add((igst_uri, SKOS.exactMatch, WD.Q5583000))
    g.add((igst_uri, SKOS.broader, WD.Q8161))

    os.makedirs(output_dir, exist_ok=True)
    turtle_path = os.path.join(output_dir, 'lmmha.ttl')
    g.serialize(destination=turtle_path, format='turtle')
    jsonld_path = os.path.join(output_dir, 'lmmha.jsonld')
    g.serialize(destination=jsonld_path, format='json-ld', indent=2)

    print(f"✅ Successfully exported {len(data)} Major Heads to SKOS (Turtle & JSON-LD)")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    json_path = 'references/lmmha/lmmha_clean.json'
    output_dir = 'references/lmmha/lod'
    export_to_skos(json_path, output_dir)
