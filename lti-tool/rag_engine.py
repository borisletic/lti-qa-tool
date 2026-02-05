"""
RAG Engine - Retrieval Augmented Generation
Koristi Ollama + ChromaDB + Sentence Transformers (sve besplatno)
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
import requests


class RAGEngine:
    """
    RAG sistem za Q&A nad nastavnim materijalima
    """
    
    def __init__(self, course_id: str):
        """
        Initialize RAG engine za određeni kurs
        
        Args:
            course_id: ID kursa
        """
        self.course_id = course_id
        self.ollama_host = os.environ.get('OLLAMA_HOST', 'http://ollama:11434')
        
        # Sentence Transformer za embeddings (besplatno, lokalno)
        print(f"Loading embedding model...")
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # ChromaDB client
        try:
            self.chroma_client = chromadb.HttpClient(
                host=os.environ.get('CHROMA_HOST', 'chroma'),
                port=int(os.environ.get('CHROMA_PORT', 8000)),
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except Exception as e:
            print(f"ChromaDB connection error: {e}")
            # Fallback na PersistentClient (lokalni fajlovi)
            import chromadb.config
            self.chroma_client = chromadb.PersistentClient(
                path=f"/app/data/chroma_db"
            )
        
        # Collection za kurs
        self.collection_name = f"course_{course_id}"
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Error creating collection: {e}")
            self.collection = None
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None):
        """
        Dodaje dokument u vector store
        
        Args:
            text: Tekst dokumenta
            metadata: Dodatni metapodaci (filename, page, etc.)
        """
        if not self.collection:
            return False
        
        try:
            # Podijeli na chunk-ove (500 karaktera)
            chunks = self._chunk_text(text, chunk_size=500, overlap=50)
            
            for i, chunk in enumerate(chunks):
                # Generiši embedding
                embedding = self.embedder.encode(chunk).tolist()
                
                # Dodaj u ChromaDB
                chunk_id = f"{metadata.get('filename', 'doc')}_{i}"
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[metadata or {}]
                )
            
            print(f"✓ Added {len(chunks)} chunks to vector store")
            return True
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def retrieve_relevant_chunks(self, question: str, top_k: int = 3) -> List[Dict]:
        """
        Pronalazi relevantne chunk-ove za pitanje
        
        Args:
            question: Korisničko pitanje
            top_k: Broj chunk-ova za vraćanje
            
        Returns:
            Lista relevantnih chunk-ova sa metadata
        """
        if not self.collection:
            return []
        
        try:
            # Generiši embedding pitanja
            question_embedding = self.embedder.encode(question).tolist()
            
            # Pretraži ChromaDB
            results = self.collection.query(
                query_embeddings=[question_embedding],
                n_results=top_k
            )
            
            # Formatiraj rezultate
            chunks = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    chunks.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None
                    })
            
            return chunks
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def generate_answer(self, question: str, context_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Generiše odgovor koristeći Ollama LLM
        
        Args:
            question: Korisničko pitanje
            context_chunks: Relevantni chunk-ovi iz RAG
            
        Returns:
            Dict sa answer, confidence, sources
        """
        # Sastavi kontekst
        context = "\n\n".join([chunk['content'] for chunk in context_chunks])
        
        # POBOLJŠAN PROMPT - stroža instrukcija
        prompt = f"""Ti si obrazovni asistent. Tvoj zadatak je da odgovoriš na pitanje ISKLJUČIVO na osnovu datog konteksta.

PRAVILA:
- Odgovori SAMO na osnovu informacija iz konteksta ispod
- Ako informacija NIJE u kontekstu, odgovori: "Ne mogu odgovoriti na osnovu dostupnih materijala"
- NE izmišljaj informacije
- Odgovaraj NA SRPSKOM JEZIKU
- Budi precizan i koncizan

KONTEKST IZ NASTAVNIH MATERIJALA:
{context}

PITANJE STUDENTA: {question}

ODGOVOR (samo na osnovu konteksta iznad):"""
        
        try:
            # Pozovi Ollama API
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 512
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                answer = response.json().get('response', '')
                
                # Procijeni confidence na osnovu retrieved chunks
                avg_distance = sum(c.get('distance', 1.0) for c in context_chunks) / len(context_chunks) if context_chunks else 1.0
                confidence = max(0.0, min(1.0, 1.0 - avg_distance))
                
                return {
                    'answer': answer.strip(),
                    'confidence': confidence,
                    'sources': context_chunks
                }
            else:
                return {
                    'answer': 'Greška pri generisanju odgovora.',
                    'confidence': 0.0,
                    'sources': []
                }
        except Exception as e:
            print(f"Error generating answer: {e}")
            return {
                'answer': f'Došlo je do greške: {str(e)}',
                'confidence': 0.0,
                'sources': []
            }
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        Glavni RAG pipeline: retrieve + generate
        
        Args:
            question: Korisničko pitanje
            
        Returns:
            Dict sa answer, confidence, sources
        """
        # Retrieve
        chunks = self.retrieve_relevant_chunks(question, top_k=3)
        
        if not chunks:
            return {
                'answer': 'Nisam pronašao relevantne informacije u nastavnim materijalima. Molim postavite pitanje vezano za sadržaj kursa.',
                'confidence': 0.0,
                'sources': []
            }
        
        # Generate
        return self.generate_answer(question, chunks)
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Dijeli tekst na chunk-ove
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Vraća statistiku o dokumentima u kolekciji
        """
        if not self.collection:
            return {'count': 0}
        
        try:
            return {
                'count': self.collection.count(),
                'name': self.collection_name
            }
        except:
            return {'count': 0}


# Singleton instances za kurseve (cache)
_rag_engines = {}

def get_rag_engine(course_id: str) -> RAGEngine:
    """
    Factory funkcija - vraća RAG engine za kurs (sa caching-om)
    """
    if course_id not in _rag_engines:
        _rag_engines[course_id] = RAGEngine(course_id)
    return _rag_engines[course_id]
