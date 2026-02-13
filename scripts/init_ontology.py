#!/usr/bin/env python3
"""
Initialize Ontology Script
Učitava OWL ontologiju u Apache Jena Fuseki SPARQL endpoint
"""

import argparse
import requests
from rdflib import Graph
import sys
from pathlib import Path


def load_ontology(ontology_file):
    """
    Učitava ontologiju iz Turtle fajla
    """
    print(f"Učitavam ontologiju iz {ontology_file}...")
    
    graph = Graph()
    graph.parse(ontology_file, format='turtle')
    
    print(f"   ✓ Učitano {len(graph)} triplet-a")
    
    return graph


def upload_to_fuseki(graph, fuseki_url, dataset='lms-tools', clear_existing=False):
    """
    Upload-uje graf u Apache Jena Fuseki
    
    Args:
        graph: RDFLib graf
        fuseki_url: URL Fuseki servera (npr. http://localhost:3030)
        dataset: Ime dataset-a
        clear_existing: Da li očistiti postojeće podatke
    """
    data_url = f"{fuseki_url}/{dataset}/data"
    
    # Clear existing data if requested
    if clear_existing:
        print(f"Brisanje postojećih podataka iz {dataset}...")
        try:
            response = requests.delete(f"{data_url}?default")
            if response.status_code in [200, 204, 404]:
                print("   ✓ Podaci obrisani")
            else:
                print(f"Status: {response.status_code}")
        except Exception as e:
            print(f"Greška pri brisanju: {e}")
    
    # Serialize graph to Turtle
    print(f"Upload ontologije u Fuseki ({data_url})...")
    ttl_data = graph.serialize(format='turtle')
    
    headers = {
        'Content-Type': 'text/turtle; charset=utf-8'
    }
    
    try:
        response = requests.post(data_url, data=ttl_data, headers=headers)
        response.raise_for_status()
        
        print(f"Uspešno upload-ovano {len(graph)} triplet-a")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Greška pri upload-u: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Detalji: {e.response.text}")
        return False


def test_sparql_query(fuseki_url, dataset='lms-tools'):
    """
    Testira SPARQL upit nad upload-ovanom ontologijom
    """
    query_url = f"{fuseki_url}/{dataset}/query"
    
    # Count classes query
    sparql_query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT 
        (COUNT(DISTINCT ?class) as ?num_classes)
        (COUNT(DISTINCT ?objProp) as ?num_object_properties)
        (COUNT(DISTINCT ?dataProp) as ?num_data_properties)
    WHERE {
        {
            ?class rdf:type owl:Class .
        } UNION {
            ?objProp rdf:type owl:ObjectProperty .
        } UNION {
            ?dataProp rdf:type owl:DatatypeProperty .
        }
    }
    """
    
    print(f"\nTest SPARQL upita...")
    
    try:
        response = requests.post(
            query_url,
            data={'query': sparql_query},
            headers={'Accept': 'application/sparql-results+json'}
        )
        response.raise_for_status()
        
        results = response.json()
        bindings = results['results']['bindings'][0]
        
        num_classes = int(bindings['num_classes']['value'])
        num_obj_props = int(bindings['num_object_properties']['value'])
        num_data_props = int(bindings['num_data_properties']['value'])
        
        print(f"   ✓ Klase: {num_classes}")
        print(f"   ✓ Object Properties: {num_obj_props}")
        print(f"   ✓ Data Properties: {num_data_props}")
        
        return True
    except Exception as e:
        print(f"Greška pri test upitu: {e}")
        return False


def create_sample_data(graph):
    """
    Dodaje primere instanci u graf za demonstraciju
    """
    from rdflib import Namespace, Literal, URIRef
    from rdflib.namespace import RDF, RDFS, XSD
    from datetime import datetime
    
    print(f"\nKreiranje primer podataka...")
    
    ns = Namespace("http://example.org/lms-tools#")
    
    # Sample course
    course_uri = URIRef("http://example.org/courses/SOTS_2026")
    graph.add((course_uri, RDF.type, ns.Course))
    graph.add((course_uri, ns.courseId, Literal("SOTS_2026")))
    graph.add((course_uri, ns.courseTitle, Literal("Savremene obrazovne tehnologije i standardi")))
    graph.add((course_uri, ns.courseDescription, 
               Literal("Kurs o IMS LTI, LMS platformama i obrazovnim standardima")))
    
    # Sample instructor
    instructor_uri = URIRef("http://example.org/users/prof_123")
    graph.add((instructor_uri, RDF.type, ns.Instructor))
    graph.add((instructor_uri, ns.userName, Literal("Prof. Dr. Marko Marković")))
    graph.add((instructor_uri, ns.email, Literal("marko.markovic@ftn.uns.ac.rs")))
    graph.add((instructor_uri, ns.teaches, course_uri))
    
    # Sample student
    student_uri = URIRef("http://example.org/users/student_456")
    graph.add((student_uri, RDF.type, ns.Student))
    graph.add((student_uri, ns.userName, Literal("Ana Petrović")))
    graph.add((student_uri, ns.email, Literal("ana.petrovic@student.ftn.uns.ac.rs")))
    graph.add((student_uri, ns.enrolledIn, course_uri))
    
    # Sample Q&A tool
    tool_uri = URIRef("http://example.org/tools/qa_tool_001")
    graph.add((tool_uri, RDF.type, ns.QATool))
    graph.add((tool_uri, ns.integratedWith, course_uri))
    
    # Sample LTI Provider
    provider_uri = URIRef("http://example.org/providers/qa_provider")
    graph.add((provider_uri, RDF.type, ns.LTIProvider))
    graph.add((provider_uri, ns.ltiVersion, Literal("1.3")))
    graph.add((provider_uri, ns.implementsStandard, 
               URIRef("http://example.org/lms-tools#LTI_1_3")))
    
    # Sample question
    question_uri = URIRef("http://example.org/questions/q_001")
    graph.add((question_uri, RDF.type, ns.Question))
    graph.add((question_uri, ns.questionText, 
               Literal("Šta je IMS LTI standard?", lang='sr')))
    graph.add((question_uri, ns.askedBy, student_uri))
    graph.add((question_uri, ns.relatedToCourse, course_uri))
    graph.add((question_uri, ns.timestamp, 
               Literal(datetime.utcnow(), datatype=XSD.dateTime)))
    
    # Sample answer
    answer_uri = URIRef("http://example.org/answers/a_001")
    graph.add((answer_uri, RDF.type, ns.AIAnswer))
    graph.add((answer_uri, ns.answerText, 
               Literal("IMS Learning Tools Interoperability (LTI) je standard za integraciju eksternih alata u LMS platforme.", lang='sr')))
    graph.add((answer_uri, ns.answersQuestion, question_uri))
    graph.add((answer_uri, ns.confidenceScore, Literal(0.92, datatype=XSD.float)))
    graph.add((answer_uri, ns.generatedBy, tool_uri))
    graph.add((answer_uri, ns.generatedAt, 
               Literal(datetime.utcnow(), datatype=XSD.dateTime)))
    
    print(f"   ✓ Dodato {len(graph) - 0} primer triplet-a")
    
    return graph


def main():
    parser = argparse.ArgumentParser(
        description="Inicijalizacija ontologije u Apache Jena Fuseki"
    )
    parser.add_argument(
        '--ontology',
        default='ontology/lms-tools.ttl',
        help='Putanja do ontologije fajla (default: ontology/lms-tools.ttl)'
    )
    parser.add_argument(
        '--fuseki-url',
        default='http://localhost:3030',
        help='URL Fuseki servera (default: http://localhost:3030)'
    )
    parser.add_argument(
        '--dataset',
        default='lms-tools',
        help='Ime dataset-a (default: lms-tools)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Obriši postojeće podatke pre upload-a'
    )
    parser.add_argument(
        '--sample-data',
        action='store_true',
        help='Dodaj primer podatke'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Testiraj SPARQL upit nakon upload-a'
    )
    
    args = parser.parse_args()
    
    # Check if ontology file exists
    if not Path(args.ontology).exists():
        print(f"Ontologija fajl {args.ontology} ne postoji")
        sys.exit(1)
    
    try:
        # Load ontology
        graph = load_ontology(args.ontology)
        
        # Add sample data if requested
        if args.sample_data:
            graph = create_sample_data(graph)
        
        # Upload to Fuseki
        success = upload_to_fuseki(
            graph,
            args.fuseki_url,
            args.dataset,
            args.clear
        )
        
        if not success:
            sys.exit(1)
        
        # Test query if requested
        if args.test:
            test_sparql_query(args.fuseki_url, args.dataset)
        
        print(f"\nOntologija uspešno inicijalizovana!")
        print(f"   SPARQL endpoint: {args.fuseki_url}/{args.dataset}/query")
        print(f"   Web interface: {args.fuseki_url}/dataset.html")
        
    except Exception as e:
        print(f"\nGreška: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
