import requests

queries = {
    'classes': '''
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label ?comment WHERE {
  ?class rdf:type owl:Class .
  OPTIONAL { ?class rdfs:label ?label FILTER(lang(?label) = "en") }
  OPTIONAL { ?class rdfs:comment ?comment FILTER(lang(?comment) = "en") }
}
ORDER BY ?label
''',
    'object_properties': '''
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?prop ?label ?domain ?range WHERE {
  ?prop rdf:type owl:ObjectProperty .
  OPTIONAL { ?prop rdfs:label ?label FILTER(lang(?label) = "en") }
  OPTIONAL { ?prop rdfs:domain ?domain }
  OPTIONAL { ?prop rdfs:range ?range }
}
ORDER BY ?label
''',
    'data_properties': '''
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?prop ?label ?domain ?range WHERE {
  ?prop rdf:type owl:DatatypeProperty .
  OPTIONAL { ?prop rdfs:label ?label FILTER(lang(?label) = "en") }
  OPTIONAL { ?prop rdfs:domain ?domain }
  OPTIONAL { ?prop rdfs:range ?range }
}
ORDER BY ?label
'''
}

output = []
output.append('# OWL ONTOLOGIJA - IZVJEŠTAJ\n')
output.append('## LMS Tools and LTI Integration Ontology\n\n')
output.append('**Datum**: 2026-02-05\n')
output.append('**Ukupno triples**: 304\n\n')

for section, query in queries.items():
    resp = requests.post('http://fuseki:3030/lms-tools/query', data={'query': query})
    results = resp.json()['results']['bindings']
    
    output.append(f'### {section.upper().replace("_", " ")}\n\n')
    output.append(f'**Ukupno**: {len(results)}\n\n')
    
    if section == 'classes':
        for r in results:
            label = r.get('label', {}).get('value', 'N/A')
            comment = r.get('comment', {}).get('value', '')
            output.append(f'- **{label}**\n')
            if comment:
                output.append(f'  - {comment}\n')
    
    elif section in ['object_properties', 'data_properties']:
        for r in results:
            label = r.get('label', {}).get('value', 'N/A')
            domain = r.get('domain', {}).get('value', '').split('#')[-1]
            range_val = r.get('range', {}).get('value', '').split('#')[-1]
            output.append(f'- **{label}**')
            if domain or range_val:
                output.append(f' ({domain} → {range_val})')
            output.append('\n')
    
    output.append('\n')

with open('/tmp/ontology_report.md', 'w', encoding='utf-8') as f:
    f.writelines(output)

print('✅ Izvještaj kreiran!')
