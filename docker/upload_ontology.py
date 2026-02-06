bash# Kreiraj ultra-robustan upload script
cat > docker/upload_ontology_chunks.py << 'EOF'
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS, OWL
import requests
import time

print('📚 Učitavanje ontologije...')
g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'   Učitano {len(g)} triples')

# Podeli na manje grupe
triples = list(g)
chunk_size = 10  # Manje chunks za sigurnost
total_chunks = (len(triples) + chunk_size - 1) // chunk_size

print(f'\n📤 Upload u {total_chunks} chunk-ova...')

success_count = 0
fail_count = 0

for i in range(0, len(triples), chunk_size):
    chunk = triples[i:i+chunk_size]
    chunk_num = i // chunk_size + 1
    
    # Kreiraj INSERT DATA query
    triples_str = []
    for s, p, o in chunk:
        try:
            # Formatiraj triple u N-Triples format (sigurniji)
            triple = f'{s.n3()} {p.n3()} {o.n3()} .'
            triples_str.append(triple)
        except Exception as e:
            print(f'   ⚠️  Skip problematičan triple: {e}')
            continue
    
    if not triples_str:
        continue
    
    # SPARQL UPDATE query
    query = 'INSERT DATA { ' + ' '.join(triples_str) + ' }'
    
    # POST na /update endpoint
    resp = requests.post(
        'http://fuseki:3030/lms-tools/update',
        data={'update': query},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if resp.status_code < 400:
        success_count += 1
        print(f'   ✅ Chunk {chunk_num}/{total_chunks} ({len(chunk)} triples)')
    else:
        fail_count += 1
        print(f'   ❌ Chunk {chunk_num}/{total_chunks} - Error {resp.status_code}')
        if chunk_num <= 3:  # Prikaži detalje samo za prve greške
            print(f'      {resp.text[:200]}')
    
    # Mali delay između chunk-ova
    time.sleep(0.1)

print(f'\n📊 Rezultat:')
print(f'   ✅ Uspešno: {success_count} chunks')
print(f'   ❌ Neuspešno: {fail_count} chunks')

# Verifikuj koliko je u bazi
query = 'SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }'
try:
    query_resp = requests.post(
        'http://fuseki:3030/lms-tools/query',
        data={'query': query},
        headers={'Accept': 'application/sparql-results+json'}
    )
    
    if query_resp.status_code == 200:
        count = query_resp.json()['results']['bindings'][0]['count']['value']
        print(f'\n🎉 Ukupno u Fuseki bazi: {count} triples')
    else:
        print(f'\n⚠️  Verifikacija error: {query_resp.status_code}')
except Exception as e:
    print(f'\n⚠️  Verifikacija error: {e}')