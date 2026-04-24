"""
Sync Manager
Orkestrira sinhronizaciju materijala: Canvas Files -> ChromaDB.

Kljucne odgovornosti:
  - Lista fajlove u Canvas kursu
  - Skida svaki podrzani fajl, ekstraktuje tekst
  - Ubacuje u RAG engine (ChromaDB)
  - Trackuje sta je vec sinhronizovano (po Canvas file id + updated_at)
    da bi reruns bili idempotentni

Tracking state:
  Cuva se na disku kao JSON: data/sync_state_course_<id>.json
  Format: { "canvas_files": { "<file_id>": {"updated_at": "...", "filename": "..."} } }
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from canvas_client import CanvasClient
from rag_engine import get_rag_engine

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Chunk ID konvencija
# -----------------------------------------------------------------------
# Postojeci rag_engine.add_document koristi:
#     chunk_id = f"{metadata.get('filename', 'doc')}_{i}"
# Mi cemo u filename polje upisivati "canvas_<file_id>__<display_name>"
# da bi delete po Canvas file id radio pouzdano (display_name moze
# da sadrzi specijalne karaktere).

def _canvas_chunk_prefix(file_id) -> str:
    """Prefix svih chunk-ova koji poticu od Canvas fajla sa datim id-jem."""
    return f"canvas_{file_id}__"


def _filename_for_chunks(file_id, display_name: str) -> str:
    """Vrednost za metadata['filename'] - koristi se kao chunk_id prefix."""
    # Ocistiti display_name od karaktera koji bi zbunili chunk_id parser
    safe_name = display_name.replace('/', '_').replace('\\', '_')
    return f"{_canvas_chunk_prefix(file_id)}{safe_name}"


# -----------------------------------------------------------------------
# State persistence
# -----------------------------------------------------------------------

_STATE_LOCK = threading.Lock()
_STATE_DIR = Path(os.environ.get('SYNC_STATE_DIR', '/app/data'))


def _state_path(course_id: str) -> Path:
    return _STATE_DIR / f"sync_state_course_{course_id}.json"


def _load_state(course_id: str) -> Dict:
    path = _state_path(course_id)
    if not path.exists():
        return {"canvas_files": {}}
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load sync state for course {course_id}: {e}")
        return {"canvas_files": {}}


def _save_state(course_id: str, state: Dict) -> None:
    path = _state_path(course_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def has_been_synced(course_id: str) -> bool:
    """Da li je kurs ikada uspesno sinhronizovan (bar jedan fajl)."""
    state = _load_state(course_id)
    return bool(state.get("canvas_files"))


# -----------------------------------------------------------------------
# ChromaDB helpers
# -----------------------------------------------------------------------

def _delete_chunks_for_file(rag, file_id) -> int:
    """Brise sve chunks u ChromaDB koji pripadaju Canvas fajlu."""
    if not rag.collection:
        return 0
    try:
        prefix = _canvas_chunk_prefix(file_id)
        all_items = rag.collection.get()
        ids_to_delete = [cid for cid in all_items.get('ids', []) if cid.startswith(prefix)]
        if ids_to_delete:
            rag.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    except Exception as e:
        logger.error(f"Failed to delete chunks for file {file_id}: {e}")
        return 0


# -----------------------------------------------------------------------
# Main sync routine
# -----------------------------------------------------------------------

def sync_course(course_id: str, force: bool = False) -> Dict:
    """
    Sinhronizuje Canvas fajlove u ChromaDB za dati kurs.

    Args:
        course_id: Canvas course id.
        force: Ako True, ignorise tracking state i reindeksira sve.

    Returns:
        Dict sa statistikom:
          {
            "course_id": str,
            "added": [filenames],
            "updated": [filenames],
            "skipped": [filenames],
            "unsupported": [filenames],
            "removed": [filenames],
            "errors": [ {filename, error} ],
            "total_canvas_files": int,
          }
    """
    result = {
        "course_id": course_id,
        "added": [],
        "updated": [],
        "skipped": [],
        "unsupported": [],
        "removed": [],
        "errors": [],
        "total_canvas_files": 0,
    }

    with _STATE_LOCK:
        state = _load_state(course_id)
        tracked = state.get("canvas_files", {})
        if force:
            # Zadrzavamo reference za kasnije brisanje iz ChromaDB
            tracked_snapshot = dict(tracked)
            tracked = {}
        else:
            tracked_snapshot = dict(tracked)

        # 1. Povezi se sa Canvas-om i izlistaj fajlove
        try:
            canvas = CanvasClient()
        except ValueError as e:
            result["errors"].append({"filename": "<config>", "error": str(e)})
            return result

        try:
            canvas_files = canvas.list_course_files(course_id)
        except Exception as e:
            result["errors"].append({"filename": "<canvas_api>", "error": str(e)})
            return result

        result["total_canvas_files"] = len(canvas_files)
        rag = get_rag_engine(course_id)

        # 2. Procesiraj svaki fajl
        current_file_ids = set()

        for f in canvas_files:
            file_id = str(f.get('id'))
            current_file_ids.add(file_id)
            display_name = f.get('display_name') or f.get('filename') or f"file_{file_id}"
            updated_at = f.get('updated_at', '')

            if not CanvasClient.is_supported(display_name):
                result["unsupported"].append(display_name)
                continue

            prev = tracked_snapshot.get(file_id)
            is_update = prev is not None
            unchanged = is_update and prev.get('updated_at') == updated_at

            if unchanged and not force:
                result["skipped"].append(display_name)
                # Zadrzi u tracking state
                tracked[file_id] = prev
                continue

            # Skini i procesiraj
            try:
                content_bytes = canvas.download_file(f)
                text = CanvasClient.extract_text(display_name, content_bytes)
                if not text.strip():
                    result["errors"].append({
                        "filename": display_name,
                        "error": "Ekstrahovan tekst je prazan"
                    })
                    continue

                # Ako je update, obrisi stare chunks pre dodavanja novih
                if is_update or force:
                    _delete_chunks_for_file(rag, file_id)

                metadata = {
                    "filename": _filename_for_chunks(file_id, display_name),
                    "display_name": display_name,
                    "course_id": course_id,
                    "canvas_file_id": file_id,
                    "source": "canvas",
                    "file_type": CanvasClient._extension(display_name).lstrip('.'),
                }
                ok = rag.add_document(text, metadata)
                if not ok:
                    result["errors"].append({
                        "filename": display_name,
                        "error": "add_document vratio False"
                    })
                    continue

                tracked[file_id] = {
                    "updated_at": updated_at,
                    "display_name": display_name,
                }
                if is_update:
                    result["updated"].append(display_name)
                else:
                    result["added"].append(display_name)

            except Exception as e:
                logger.exception(f"Sync failed for {display_name}")
                result["errors"].append({"filename": display_name, "error": str(e)})

        # 3. Obrisi iz ChromaDB fajlove koji vise ne postoje u Canvas-u
        stale_ids = set(tracked_snapshot.keys()) - current_file_ids
        for file_id in stale_ids:
            removed_name = tracked_snapshot[file_id].get('display_name', f"file_{file_id}")
            deleted = _delete_chunks_for_file(rag, file_id)
            if deleted:
                result["removed"].append(removed_name)
            # Ne vracaj ga u tracked

        # 4. Perzistiraj novi state
        state["canvas_files"] = tracked
        _save_state(course_id, state)

    return result


def summarize(result: Dict) -> str:
    """Kratak string summary za log ili UI."""
    return (
        f"Canvas: {result['total_canvas_files']} fajlova | "
        f"+{len(result['added'])} dodato, "
        f"~{len(result['updated'])} update-ovano, "
        f"={len(result['skipped'])} preskocceno, "
        f"-{len(result['removed'])} obrisano, "
        f"!{len(result['unsupported'])} nepodrzano, "
        f"x{len(result['errors'])} gresaka"
    )
