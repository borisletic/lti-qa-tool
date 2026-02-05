import sys
sys.path.insert(0, '/app')

from rag_engine import get_rag_engine

rag = get_rag_engine('1')

question = 'Kako funkcionise RAG arhitektura?'
chunks = rag.retrieve_relevant_chunks(question, top_k=5)

print(f'Retrieved {len(chunks)} chunks:')
print()
for i, chunk in enumerate(chunks, 1):
    distance = chunk.get('distance', 0)
    filename = chunk['metadata'].get('filename', 'unknown')
    content = chunk['content'][:200]
    print(f'--- Chunk {i} (distance: {distance:.3f}) ---')
    print(f'Source: {filename}')
    print(f'Content: {content}...')
    print()
