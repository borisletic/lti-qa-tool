"""
Jednokratni cleanup: brise sve ChromaDB chunks koji NISU upload-ovani
preko Canvas sync-a. Posle ovog, samo Canvas-derived fajlovi ostaju.

Logika: chunks bez metadata.source == 'canvas' se brisu.
Equivalentno: chunks ciji chunk_id ne pocinje sa 'canvas_'.

Pokrenuti unutar lti_tool kontejnera:
    docker-compose exec lti_tool python /app/cleanup_legacy_uploads.py [course_id]

Default course_id = '1'.
"""

import sys
sys.path.insert(0, '/app')

from rag_engine import get_rag_engine


def cleanup(course_id: str):
    rag = get_rag_engine(course_id)
    if not rag.collection:
        print(f"Nema kolekcije za kurs {course_id}")
        return

    items = rag.collection.get()
    ids = items.get('ids', [])
    metadatas = items.get('metadatas') or [{}] * len(ids)

    if not ids:
        print(f"Kolekcija course_{course_id} je prazna.")
        return

    legacy_ids = []
    canvas_count = 0

    for chunk_id, md in zip(ids, metadatas):
        md = md or {}
        is_canvas = md.get('source') == 'canvas' or chunk_id.startswith('canvas_')
        if is_canvas:
            canvas_count += 1
        else:
            legacy_ids.append(chunk_id)

    print(f"Kurs {course_id}:")
    print(f"  Total chunks:        {len(ids)}")
    print(f"  Canvas-sourced:      {canvas_count}  (zadrzava se)")
    print(f"  Legacy uploads:      {len(legacy_ids)}  (brise se)")

    if not legacy_ids:
        print("Nema sta da se ocisti.")
        return

    # Pokazi koji se brisu (po jedinstvenim filename-ovima)
    legacy_files = set()
    for cid in legacy_ids:
        # chunk_id format: "<filename>_<n>"
        parts = cid.rsplit('_', 1)
        if len(parts) == 2:
            legacy_files.add(parts[0])
    print(f"  Filename-ovi za brisanje: {sorted(legacy_files)}")

    confirm = input("\nObrisati? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Odustao.")
        return

    rag.collection.delete(ids=legacy_ids)
    print(f"Obrisano {len(legacy_ids)} chunks.")


if __name__ == '__main__':
    course_id = sys.argv[1] if len(sys.argv) > 1 else '1'
    cleanup(course_id)
