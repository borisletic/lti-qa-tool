from rdflib import Graph
import requests
from requests.auth import HTTPBasicAuth

g = Graph()
g.parse('/app/ontology/lms-tools.ttl', format='turtle')
print(f'Loaded {len(g)} triples')

ttl = g.serialize(format='turtle')

# Pravilna URL za data upload
url = 'http://fuseki:3030/lms-tools/data?default'

resp = requests.post(url, data=ttl, headers={'Content-Type': 'text/turtle'})
print(f'No auth: {resp.status_code}')

if resp.status_code >= 400:
    resp2 = requests.post(url, data=ttl, headers={'Content-Type': 'text/turtle'}, auth=HTTPBasicAuth('admin', 'fuseki_admin_123'))
    print(f'With auth: {resp2.status_code}')
    
    if resp2.status_code < 400:
        print('✅ Success!')
    else:
        # Probaj SPARQL UPDATE umjesto POST
        from SPARQLWrapper import SPARQLWrapper, POST
        sparql = SPARQLWrapper('http://fuseki:3030/lms-tools/update')
        sparql.setHTTPAuth('BASIC')
        sparql.setCredentials('admin', 'fuseki_admin_123')
        sparql.setMethod(POST)
        
        # Bulk insert
        insert = 'INSERT DATA { ' + ttl + ' }'
        sparql.setQuery(insert)
        
        try:
            sparql.query()
            print('✅ Success via SPARQL UPDATE!')
        except Exception as e:
            print(f'SPARQL error: {e}')
