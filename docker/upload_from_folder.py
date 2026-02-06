import sys
import os
from pathlib import Path
sys.path.insert(0, '/app')

from rag_engine import get_rag_engine

# Importuj document loaders
try:
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        UnstructuredMarkdownLoader
    )
    from docx import Document as DocxDocument
except ImportError:
    print('⚠️  Instalacija dodatnih paketa...')
    os.system('pip install -q pypdf python-docx unstructured markdown')
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        UnstructuredMarkdownLoader
    )
    from docx import Document as DocxDocument

print('=== AUTOMATSKI UPLOAD MATERIJALA ===\n')

# Putanja do materijala (u Docker container-u)
materials_path = Path('/tmp/course-materials')

if not materials_path.exists():
    print(f'❌ Folder {materials_path} ne postoji!')
    print('   Mora se prvo kopirati: docker cp course-materials lti-qa-tool:/tmp/')
    sys.exit(1)

# Pronađi sve fajlove
supported_extensions = {'.txt', '.md', '.pdf', '.docx'}
files = []
for ext in supported_extensions:
    files.extend(list(materials_path.glob(f'*{ext}')))

if not files:
    print(f'❌ Nema fajlova u {materials_path}')
    sys.exit(1)

print(f'📁 Pronađeno {len(files)} fajlova:\n')
for f in files:
    print(f'   - {f.name}')

print(f'\n🚀 Pokretanje RAG engine...')
course_id = '1'  # Canvas course ID
rag = get_rag_engine(course_id)

uploaded = 0
failed = 0

print(f'\n📤 Upload fajlova u ChromaDB...\n')

for file_path in files:
    filename = file_path.name
    ext = file_path.suffix.lower()
    
    print(f'📄 {filename}... ', end='')
    
    try:
        # Učitaj sadržaj na osnovu tipa
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        elif ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        elif ext == '.pdf':
            # PyPDFLoader
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()
            text = '\n\n'.join([doc.page_content for doc in docs])
        
        elif ext == '.docx':
            # python-docx
            doc = DocxDocument(str(file_path))
            text = '\n\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        
        else:
            print('⚠️  Nepodržan format')
            failed += 1
            continue
        
        # Proveri da nije prazan
        if not text.strip():
            print('⚠️  Prazan fajl')
            failed += 1
            continue
        
        # Upload u ChromaDB
        metadata = {
            'filename': filename,
            'course_id': course_id,
            'file_type': ext
        }
        
        success = rag.add_document(text, metadata)
        
        if success:
            word_count = len(text.split())
            print(f'✅ ({word_count} reči)')
            uploaded += 1
        else:
            print('❌')
            failed += 1
    
    except Exception as e:
        print(f'❌ Greška: {str(e)[:50]}')
        failed += 1

# Statistika
print(f'\n📊 Rezultat:')
print(f'   ✅ Uspešno: {uploaded} fajlova')
print(f'   ❌ Neuspešno: {failed} fajlova')

stats = rag.get_collection_stats()
print(f'\n💾 ChromaDB statistika:')
print(f'   Collection: {stats["name"]}')
print(f'   Ukupno chunks: {stats["count"]}')

# Test retrieval
print(f'\n🔍 Test pretraga: "LTI standard"')
chunks = rag.retrieve_relevant_chunks('LTI standard', top_k=3)
print(f'   Pronađeno: {len(chunks)} relevantnih chunks')

if chunks:
    print(f'\n   Prvi rezultat:')
    print(f'   Source: {chunks[0]["metadata"].get("filename", "N/A")}')
    print(f'   Distance: {chunks[0].get("distance", 0):.3f}')
    print(f'   Content: {chunks[0]["content"][:150]}...')

print(f'\n✅ SVE GOTOVO! Materijali su spremni za Q&A.')