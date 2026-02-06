from rdflib import Graph
import requests
import time

print('=== FUSEKI ONTOLOGY UPLOAD ===\n')

# Učitaj ontologiju
print('1. Učitavanje ontologije...')
g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'   ✓ Učitano {len(g)} triples\n')

# Podeli na chunks
triples = list(g)
chunk_size = 10
total_chunks = (len(triples) + chunk_size - 1) // chunk_size

print(f'2. Upload u {total_chunks} chunk-ova...')

success = 0
failed = 0

for i in range(0, len(triples), chunk_size):
    chunk = triples[i:i+chunk_size]
    chunk_num = i // chunk_size + 1
    
    # Napravi INSERT DATA query
    triples_str = []
    for s, p, o in chunk:
        try:
            triple = f'{s.n3()} {p.n3()} {o.n3()} .'
            triples_str.append(triple)
        except:
            pass
    
    if not triples_str:
        continue
    
    query = 'INSERT DATA { ' + ' '.join(triples_str) + ' }'
    
    # POST na Fuseki
    resp = requests.post(
        'http://fuseki:3030/lms-tools/update',
        data={'update': query},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if resp.status_code < 400:
        success += 1
        print(f'   ✓ Chunk {chunk_num}/{total_chunks}')
    else:
        failed += 1
        print(f'   ✗ Chunk {chunk_num}/{total_chunks} - Error {resp.status_code}')
    
    time.sleep(0.05)

print(f'\n3. Rezultat:')
print(f'   Uspešno: {success} chunks')
print(f'   Neuspešno: {failed} chunks')

# Verifikuj
query = 'SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }'
resp = requests.post(
    'http://fuseki:3030/lms-tools/query',
    data={'query': query},
    headers={'Accept': 'application/sparql-results+json'}
)

if resp.status_code == 200:
    count = resp.json()['results']['bindings'][0]['count']['value']
    print(f'\n✅ UKUPNO U BAZI: {count} triples')
else:
    print(f'\n⚠ Verifikacija neuspešna')