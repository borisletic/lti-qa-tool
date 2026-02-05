from rdflib import Graph
import requests

g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'Loaded {len(g)} triples')

triples = list(g)
chunk_size = 50

for i in range(0, len(triples), chunk_size):
    chunk = triples[i:i+chunk_size]
    insert_triples = []
    
    for s, p, o in chunk:
        insert_triples.append(f'{s.n3()} {p.n3()} {o.n3()} .')
    
    insert_query = 'INSERT DATA { ' + ' '.join(insert_triples) + ' }'
    
    resp = requests.post(
        'http://fuseki:3030/lms-tools/update',
        data={'update': insert_query},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if resp.status_code < 400:
        print(f'✓ Chunk {i//chunk_size + 1} ({len(chunk)} triples)')
    else:
        print(f'✗ Error: {resp.status_code}')
        break

query_resp = requests.post('http://fuseki:3030/lms-tools/query', data={'query': 'SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }'})
count = query_resp.json()['results']['bindings'][0]['count']['value']
print(f'\n✅ Total: {count} triples')
