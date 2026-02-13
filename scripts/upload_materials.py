#!/usr/bin/env python3
"""
Upload Materials Script
Učitava nastavne materijale u ChromaDB vector database
"""

import os
import argparse
from pathlib import Path
from langchain.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_document(file_path):
    """
    Učitava dokument na osnovu ekstenzije fajla
    """
    file_ext = Path(file_path).suffix.lower()
    
    loaders = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader,
        '.docx': Docx2txtLoader,
    }
    
    if file_ext not in loaders:
        raise ValueError(f"Nepodržana ekstenzija fajla: {file_ext}")
    
    loader = loaders[file_ext](file_path)
    return loader.load()


def process_materials(course_id, materials_dir, chunk_size=1000, chunk_overlap=200):
    """
    Procesira sve materijale iz direktorijuma i dodaje ih u vector database
    
    Args:
        course_id: ID kursa
        materials_dir: Putanja do direktorijuma sa materijalima
        chunk_size: Veličina chunk-a za text splitting
        chunk_overlap: Preklapanje između chunk-ova
    """
    materials_path = Path(materials_dir)
    
    if not materials_path.exists():
        raise FileNotFoundError(f"Direktorijum {materials_dir} ne postoji")
    
    # Pronađi sve podržane fajlove
    supported_extensions = ['.pdf', '.txt', '.md', '.docx']
    files = []
    for ext in supported_extensions:
        files.extend(materials_path.glob(f'**/*{ext}'))
    
    if not files:
        print(f"Nijedan fajl nije pronađen u {materials_dir}")
        return
    
    print(f"Pronađeno {len(files)} fajlova za procesiranje")
    
    # Učitaj sve dokumente
    all_documents = []
    for file_path in files:
        try:
            print(f"Učitavam: {file_path.name}")
            docs = load_document(str(file_path))
            
            # Dodaj metadata
            for doc in docs:
                doc.metadata['source'] = file_path.name
                doc.metadata['course_id'] = course_id
            
            all_documents.extend(docs)
            print(f"   ✓ Učitano {len(docs)} stranica/sekcija")
        except Exception as e:
            print(f"Greška pri učitavanju {file_path.name}: {e}")
    
    if not all_documents:
        print("Nijedan dokument nije uspešno učitan")
        return
    
    print(f"\nUkupno učitano: {len(all_documents)} dokumenata")
    
    # Text splitting
    print(f"Deljenje teksta na chunk-ove...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_documents(all_documents)
    print(f"   ✓ Kreirano {len(chunks)} chunk-ova")
    
    # Kreiranje embeddings i skladištenje u ChromaDB
    print(f"Kreiranje embeddings sa OpenAI...")
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ.get('OPENAI_API_KEY')
    )
    
    # Persist directory
    persist_directory = f"./data/courses/{course_id}"
    os.makedirs(persist_directory, exist_ok=True)
    
    # Kreiranje/ažuriranje Chroma collection
    print(f"Skladištenje u ChromaDB ({persist_directory})...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    vectorstore.persist()
    
    print(f"\nUspešno procesiran kurs {course_id}")
    print(f"   - Fajlova: {len(files)}")
    print(f"   - Dokumenata: {len(all_documents)}")
    print(f"   - Chunk-ova: {len(chunks)}")
    print(f"   - Lokacija: {persist_directory}")


def test_retrieval(course_id, query="Šta je LTI?", k=3):
    """
    Testira pretragu u vector database
    """
    persist_directory = f"./data/courses/{course_id}"
    
    if not os.path.exists(persist_directory):
        print(f"Vector database za kurs {course_id} ne postoji")
        return
    
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ.get('OPENAI_API_KEY')
    )
    
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    
    print(f"\nTest pretraga: '{query}'")
    results = vectorstore.similarity_search(query, k=k)
    
    print(f"\nPronađeno {len(results)} rezultata:")
    for i, doc in enumerate(results, 1):
        print(f"\n--- Rezultat {i} ---")
        print(f"Izvor: {doc.metadata.get('source', 'Unknown')}")
        print(f"Sadržaj: {doc.page_content[:200]}...")


def main():
    parser = argparse.ArgumentParser(
        description="Upload nastavnih materijala u vector database"
    )
    parser.add_argument(
        '--course-id',
        required=True,
        help='ID kursa (npr. COURSE_001)'
    )
    parser.add_argument(
        '--materials',
        required=True,
        help='Putanja do direktorijuma sa materijalima'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Veličina chunk-a (default: 1000)'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=200,
        help='Overlap između chunk-ova (default: 200)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Testiraj pretragu nakon upload-a'
    )
    parser.add_argument(
        '--test-query',
        default='Šta je LTI?',
        help='Upit za test pretragu'
    )
    
    args = parser.parse_args()
    
    # Check OpenAI API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("OPENAI_API_KEY environment varijabla nije postavljena")
        print("   Postavite je u .env fajlu ili environment-u")
        return
    
    try:
        process_materials(
            course_id=args.course_id,
            materials_dir=args.materials,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        
        if args.test:
            test_retrieval(args.course_id, args.test_query)
            
    except Exception as e:
        print(f"\nGreška: {e}")
        raise


if __name__ == '__main__':
    main()
