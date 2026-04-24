"""
LTI Q&A Tool - Flask Application
Inteligentni Q&A Agent integrisan sa Canvas/Moodle preko IMS LTI.

Nastavni materijali se NE upload-uju direktno u ovaj tool. Umesto toga,
tool ih povlaci iz Canvas kursa preko Canvas Files API-ja, cime se
postize prava LMS integracija (nastavnik radi samo u Canvas-u).
"""

import os
import uuid
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS

from rag_engine import get_rag_engine
from semantic_layer import SemanticLayer
import sync_manager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO)

# Semantic layer
semantic_layer = SemanticLayer('ontology/lms-tools.ttl')


# ============================================================
# Health & metadata
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'LTI Q&A Tool',
        'timestamp': datetime.utcnow().isoformat()
    })


# ============================================================
# LTI 1.1 launch
# ============================================================

@app.route('/launch', methods=['POST'])
def launch():
    """
    LTI 1.1 launch. Canvas stable ne podrzava LTI 1.3 pouzdano,
    pa koristimo 1.1 oauth signed POST.
    """
    try:
        user_id = request.form.get('user_id', 'unknown')
        user_name = request.form.get('lis_person_name_full', 'Student')

        course_id = (
            request.form.get('custom_canvas_course_id')
            or request.form.get('context_id', 'default')
        )
        course_title = request.form.get('context_title', 'Unknown Course')

        roles = request.form.get('roles', '').split(',')
        is_instructor = any('Instructor' in role or 'Teacher' in role for role in roles)

        session['user_id'] = user_id
        session['user_name'] = user_name
        session['course_id'] = course_id
        session['course_title'] = course_title
        session['is_instructor'] = is_instructor

        # Log launch event u RDF graf
        semantic_layer.log_tool_launch(
            tool_uri=f"http://example.org/tools/{uuid.uuid4()}",
            course_uri=f"http://example.org/courses/{course_id}",
            user_uri=f"http://example.org/users/{user_id}",
        )

        # Auto-sync pri prvom launch-u kursa
        auto_sync_info = None
        if not sync_manager.has_been_synced(course_id):
            app.logger.info(f"First launch za kurs {course_id} - pokrecem auto-sync...")
            try:
                result = sync_manager.sync_course(course_id, force=False)
                auto_sync_info = sync_manager.summarize(result)
                app.logger.info(f"Auto-sync gotov: {auto_sync_info}")
            except Exception as e:
                app.logger.exception("Auto-sync failed")
                auto_sync_info = f"Auto-sync neuspesan: {e}"

        return render_template(
            'qa_interface.html',
            user_name=user_name,
            course_title=course_title,
            course_id=course_id,
            is_instructor=is_instructor,
            auto_sync_info=auto_sync_info,
        )

    except Exception as e:
        app.logger.exception("Launch error")
        return jsonify({'error': str(e)}), 500


# ============================================================
# Q&A
# ============================================================

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """RAG pipeline nad Canvas materijalima."""
    try:
        data = request.json or {}
        question = data.get('question', '').strip()
        course_id = data.get('course_id') or session.get('course_id', 'default')
        user_id = session.get('user_id', 'anonymous')

        if not question:
            return jsonify({'error': 'Pitanje ne moze biti prazno'}), 400

        rag = get_rag_engine(course_id)
        result = rag.ask(question)

        semantic_layer.register_qa_session(
            question_text=question,
            answer_text=result['answer'],
            course_id=course_id,
            user_id=user_id,
            confidence=result['confidence'],
        )

        return jsonify({
            'answer': result['answer'],
            'confidence': result['confidence'],
            'cached': False,
            'sources': result['sources'],
        })

    except Exception as e:
        app.logger.exception("Error processing question")
        return jsonify({'error': 'Greska pri obradi pitanja.', 'details': str(e)}), 500


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json or {}
    semantic_layer.add_feedback(
        data.get('question_id'),
        data.get('rating'),
        data.get('comment', ''),
    )
    return jsonify({'status': 'success'})


# ============================================================
# Canvas sync
# ============================================================

@app.route('/api/sync-canvas-materials', methods=['POST'])
def sync_canvas_materials():
    """
    Manual trigger sinhronizacije Canvas -> ChromaDB.
    Nastavnik klikne 'Sinhronizuj' dugme u UI-ju.

    Body (JSON):
        { "course_id": "...", "force": false }
    """
    try:
        data = request.json or {}
        course_id = data.get('course_id') or session.get('course_id')
        force = bool(data.get('force', False))

        if not course_id:
            return jsonify({'error': 'course_id je obavezan'}), 400

        app.logger.info(f"Manual sync zahtevan za kurs {course_id} (force={force})")
        result = sync_manager.sync_course(course_id, force=force)

        return jsonify({
            'success': True,
            'summary': sync_manager.summarize(result),
            'details': result,
        })

    except Exception as e:
        app.logger.exception("Sync failed")
        return jsonify({'error': str(e)}), 500


@app.route('/api/canvas-status', methods=['GET'])
def canvas_status():
    """Test konekcije sa Canvas API-jem (korisno za debug)."""
    try:
        from canvas_client import CanvasClient
        client = CanvasClient()
        ok, message = client.test_connection()
        return jsonify({'ok': ok, 'message': message})
    except ValueError as e:
        return jsonify({'ok': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Greska: {e}'}), 500


# ============================================================
# Read-only materials inspection
# ============================================================

@app.route('/api/materials', methods=['GET'])
def list_materials():
    """
    Lista materijale koji su trenutno u ChromaDB za kurs.
    Koristi se u UI-ju za prikaz 'sta je tool indeksirao'.
    """
    try:
        course_id = request.args.get('course_id') or session.get('course_id', '1')
        rag = get_rag_engine(course_id)

        if not rag.collection:
            return jsonify({'total_files': 0, 'total_chunks': 0, 'files': []})

        results = rag.collection.get()
        if not results.get('ids'):
            return jsonify({'total_files': 0, 'total_chunks': 0, 'files': []})

        files = {}
        ids = results['ids']
        metadatas = results.get('metadatas') or [{}] * len(ids)

        for chunk_id, md in zip(ids, metadatas):
            parts = chunk_id.rsplit('_', 1)
            if len(parts) != 2:
                continue
            filename_key = parts[0]
            # display_name je u metadata ako potice iz Canvas-a
            display = (md or {}).get('display_name', filename_key)
            file_type = (md or {}).get('file_type', 'unknown')
            source = (md or {}).get('source', 'unknown')

            entry = files.setdefault(filename_key, {
                'display_name': display,
                'chunks': 0,
                'type': file_type,
                'source': source,
            })
            entry['chunks'] += 1

        files_list = [
            {
                'filename': info['display_name'],
                'chunks': info['chunks'],
                'type': info['type'],
                'source': info['source'],
            }
            for info in sorted(files.values(), key=lambda x: x['display_name'])
        ]

        return jsonify({
            'total_files': len(files),
            'total_chunks': len(ids),
            'files': files_list,
        })

    except Exception as e:
        app.logger.exception("Error listing materials")
        return jsonify({'error': str(e)}), 500


# ============================================================
# Debug
# ============================================================

@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'course_id': session.get('course_id', 'NOT_SET'),
    })


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development',
    )
