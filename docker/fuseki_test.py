import requests

query = """
PREFIX lms: <http://example.org/lms-tools#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

INSERT DATA {
  <http://example.org/questions/Q1> rdf:type lms:Question .
  <http://example.org/questions/Q1> lms:questionText "Sta je IMS LTI standard?"@sr .
  <http://example.org/answers/A1> rdf:type lms:Answer .
  <http://example.org/answers/A1> lms:answerText "LTI je standard za integraciju eksternih alata u LMS platforme."@sr .
  <http://example.org/answers/A1> lms:answersQuestion <http://example.org/questions/Q1> .
  <http://example.org/answers/A1> lms:confidenceScore "0.92"^^xsd:float .
  <http://example.org/questions/Q2> rdf:type lms:Question .
  <http://example.org/questions/Q2> lms:questionText "Kako funkcionise RAG arhitektura?"@sr .
  <http://example.org/answers/A2> rdf:type lms:Answer .
  <http://example.org/answers/A2> lms:answerText "RAG kombinuje pretragu relevantnih dokumenata sa generisanjem odgovora pomocu LLM modela."@sr .
  <http://example.org/answers/A2> lms:answersQuestion <http://example.org/questions/Q2> .
  <http://example.org/answers/A2> lms:confidenceScore "0.85"^^xsd:float .
}
"""

r = requests.post(
    'http://fuseki:3030/lms-tools/update',
    data={'update': query},
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)
print('Status:', r.status_code)
if r.status_code == 204:
    print('SUCCESS! Tripli dodani u Fuseki.')
else:
    print('Error:', r.text[:500])
