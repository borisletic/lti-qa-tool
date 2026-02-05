import requests

# Query 1: Sve OWL klase
query1 = '''
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?class ?label WHERE {
  ?class rdf:type owl:Class .
  OPTIONAL { ?class rdfs:label ?label }
}
LIMIT 10
'''

resp = requests.post('http://fuseki:3030/lms-tools/query', data={'query': query1})
print('=== OWL KLASE ===')
for binding in resp.json()['results']['bindings']:
    label = binding.get('label', {}).get('value', 'N/A')
    print(f'  {label}')

# Query 2: Object Properties
query2 = '''
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?prop ?label WHERE {
  ?prop rdf:type owl:ObjectProperty .
  OPTIONAL { ?prop rdfs:label ?label }
}
LIMIT 10
'''

resp2 = requests.post('http://fuseki:3030/lms-tools/query', data={'query': query2})
print('\n=== OBJECT PROPERTIES ===')
for binding in resp2.json()['results']['bindings']:
    label = binding.get('label', {}).get('value', 'N/A')
    print(f'  {label}')

# Query 3: LTI Standards
query3 = '''
PREFIX lms: <http://example.org/lms-tools#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?standard ?version ?auth WHERE {
  ?standard rdf:type lms:LTIStandard .
  OPTIONAL { ?standard lms:versionNumber ?version }
  OPTIONAL { ?standard lms:usesAuthentication ?auth }
}
'''

resp3 = requests.post('http://fuseki:3030/lms-tools/query', data={'query': query3})
print('\n=== LTI STANDARDS ===')
for binding in resp3.json()['results']['bindings']:
    version = binding.get('version', {}).get('value', 'N/A')
    auth = binding.get('auth', {}).get('value', 'N/A')
    print(f'  LTI {version}: {auth}')
