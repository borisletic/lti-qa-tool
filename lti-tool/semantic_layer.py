"""
Semantic Layer Module
Integracija sa OWL ontologijom i RDF grafom
"""

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
from datetime import datetime
import uuid
import os


class SemanticLayer:
    """
    Upravlja semantičkim slojem aplikacije koristeći RDF/OWL
    """
    
    def __init__(self, ontology_file='ontology/lms-tools.ttl', sparql_endpoint=None):
        """
        Initialize semantic layer
        
        Args:
            ontology_file: Path to OWL ontology file
            sparql_endpoint: Optional SPARQL endpoint URL (e.g., Apache Jena Fuseki)
        """
        self.graph = Graph()
        self.sparql_endpoint = sparql_endpoint
        
        # Load ontology
        if os.path.exists(ontology_file):
            self.graph.parse(ontology_file, format='turtle')
        else:
            print(f"Warning: Ontology file {ontology_file} not found. Starting with empty graph.")
        
        # Define namespaces
        self.ns = Namespace("http://example.org/lms-tools#")
        self.graph.bind("lms", self.ns)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        
    def register_qa_session(self, question_text, answer_text, course_id, user_id, confidence):
        """
        Registruje Q&A sesiju u semantičkom grafu
        
        Args:
            question_text: Tekst pitanja
            answer_text: Tekst odgovora
            course_id: ID kursa
            user_id: ID korisnika
            confidence: Poverenje u odgovor (0-1)
        """
        # Generate URIs
        question_id = str(uuid.uuid4())
        answer_id = str(uuid.uuid4())
        
        question_uri = URIRef(f"http://example.org/questions/{question_id}")
        answer_uri = URIRef(f"http://example.org/answers/{answer_id}")
        course_uri = URIRef(f"http://example.org/courses/{course_id}")
        user_uri = URIRef(f"http://example.org/users/{user_id}")
        
        # Add Question triples
        self.graph.add((question_uri, RDF.type, self.ns.Question))
        self.graph.add((question_uri, self.ns.questionText, Literal(question_text, lang='sr')))
        self.graph.add((question_uri, self.ns.askedBy, user_uri))
        self.graph.add((question_uri, self.ns.relatedToCourse, course_uri))
        self.graph.add((question_uri, self.ns.timestamp, 
                       Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        
        # Add Answer triples
        self.graph.add((answer_uri, RDF.type, self.ns.Answer))
        self.graph.add((answer_uri, self.ns.answerText, Literal(answer_text, lang='sr')))
        self.graph.add((answer_uri, self.ns.answersQuestion, question_uri))
        self.graph.add((answer_uri, self.ns.confidenceScore, 
                       Literal(confidence, datatype=XSD.float)))
        self.graph.add((answer_uri, self.ns.generatedAt, 
                       Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        
        # Persist changes
        self._persist_graph()
        
        return question_id, answer_id
    
    def log_tool_launch(self, tool_uri, course_uri, user_uri):
        """
        Loguje pokretanje LTI alata
        """
        launch_uri = URIRef(f"http://example.org/launches/{uuid.uuid4()}")
        
        self.graph.add((launch_uri, RDF.type, self.ns.ToolLaunch))
        self.graph.add((launch_uri, self.ns.launchedTool, URIRef(tool_uri)))
        self.graph.add((launch_uri, self.ns.inCourse, URIRef(course_uri)))
        self.graph.add((launch_uri, self.ns.byUser, URIRef(user_uri)))
        self.graph.add((launch_uri, self.ns.timestamp, 
                       Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        
        self._persist_graph()
    
    def find_similar_questions(self, question_text, course_id, limit=5):
        """
        Pronalazi slična pitanja iz istorije koristeći SPARQL
        
        Returns:
            List of dicts with question, answer, and confidence
        """
        # Extract keywords from question (simple word-based approach)
        keywords = [word.lower() for word in question_text.split() if len(word) > 4]
        
        if not keywords:
            return []
        
        # Build FILTER clause for keyword matching
        filter_conditions = " || ".join([f'CONTAINS(LCASE(?qtext), "{kw}")' for kw in keywords[:3]])
        
        query = f"""
        PREFIX lms: <http://example.org/lms-tools#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?question ?answer ?confidence WHERE {{
            ?q rdf:type lms:Question .
            ?q lms:questionText ?qtext .
            ?q lms:relatedToCourse <http://example.org/courses/{course_id}> .
            
            ?ans lms:answersQuestion ?q .
            ?ans lms:answerText ?answer .
            ?ans lms:confidenceScore ?confidence .
            
            FILTER({filter_conditions})
        }}
        ORDER BY DESC(?confidence)
        LIMIT {limit}
        """
        
        try:
            results = self.graph.query(query)
            similar = []
            
            for row in results:
                similar.append({
                    'question': str(row.qtext) if hasattr(row, 'qtext') else '',
                    'answer': str(row.answer),
                    'confidence': float(row.confidence)
                })
            
            return similar
        except Exception as e:
            print(f"Error querying similar questions: {e}")
            return []
    
    def get_course_statistics(self, course_id):
        """
        Vraća statistiku za kurs
        """
        query = f"""
        PREFIX lms: <http://example.org/lms-tools#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT (COUNT(?q) as ?total_questions) 
               (AVG(?conf) as ?avg_confidence) WHERE {{
            ?q rdf:type lms:Question .
            ?q lms:relatedToCourse <http://example.org/courses/{course_id}> .
            
            ?ans lms:answersQuestion ?q .
            ?ans lms:confidenceScore ?conf .
        }}
        """
        
        results = self.graph.query(query)
        for row in results:
            return {
                'total_questions': int(row.total_questions) if row.total_questions else 0,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0
            }
        
        return {'total_questions': 0, 'avg_confidence': 0.0}
    
    def add_feedback(self, question_id, rating, comment=''):
        """
        Dodaje feedback studenta
        """
        feedback_uri = URIRef(f"http://example.org/feedback/{uuid.uuid4()}")
        question_uri = URIRef(f"http://example.org/questions/{question_id}")
        
        self.graph.add((feedback_uri, RDF.type, self.ns.Feedback))
        self.graph.add((feedback_uri, self.ns.forQuestion, question_uri))
        self.graph.add((feedback_uri, self.ns.rating, Literal(rating, datatype=XSD.integer)))
        if comment:
            self.graph.add((feedback_uri, self.ns.comment, Literal(comment)))
        self.graph.add((feedback_uri, self.ns.timestamp, 
                       Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        
        self._persist_graph()
    
    def export_to_fuseki(self, fuseki_url, dataset='lms-tools'):
        """
        Eksportuje graf u Apache Jena Fuseki SPARQL endpoint
        """
        try:
            import requests
            
            # Serialize graph to Turtle
            ttl_data = self.graph.serialize(format='turtle')
            
            # Upload to Fuseki
            url = f"{fuseki_url}/{dataset}/data"
            headers = {'Content-Type': 'text/turtle'}
            
            response = requests.post(url, data=ttl_data, headers=headers)
            response.raise_for_status()
            
            print(f"Successfully exported {len(self.graph)} triples to Fuseki")
            return True
        except Exception as e:
            print(f"Error exporting to Fuseki: {e}")
            return False
    
    def _persist_graph(self):
        """
        Persists the graph to file
        """
        output_file = 'data/semantic-graph.ttl'
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        self.graph.serialize(destination=output_file, format='turtle')
    
    def get_ontology_stats(self):
        """
        Vraća statistiku o ontologiji
        """
        query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT 
            (COUNT(DISTINCT ?class) as ?num_classes)
            (COUNT(DISTINCT ?objProp) as ?num_object_properties)
            (COUNT(DISTINCT ?dataProp) as ?num_data_properties)
            (COUNT(*) as ?total_triples)
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
        
        results = self.graph.query(query)
        for row in results:
            return {
                'classes': int(row.num_classes) if row.num_classes else 0,
                'object_properties': int(row.num_object_properties) if row.num_object_properties else 0,
                'data_properties': int(row.num_data_properties) if row.num_data_properties else 0,
                'total_triples': len(self.graph)
            }
        
        return {
            'classes': 0,
            'object_properties': 0,
            'data_properties': 0,
            'total_triples': len(self.graph)
        }


if __name__ == '__main__':
    # Test semantic layer
    sl = SemanticLayer()
    
    # Register sample Q&A
    sl.register_qa_session(
        question_text="Šta je IMS LTI standard?",
        answer_text="IMS Learning Tools Interoperability (LTI) je standard za integraciju eksternih alata u LMS platforme.",
        course_id="COURSE_001",
        user_id="user123",
        confidence=0.92
    )
    
    # Get stats
    stats = sl.get_ontology_stats()
    print(f"Ontology statistics: {stats}")
    
    # Find similar questions
    similar = sl.find_similar_questions("LTI standard", "COURSE_001")
    print(f"Found {len(similar)} similar questions")
