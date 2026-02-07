"""
LTI Q&A Tool - Flask Application
Inteligentni Q&A Agent integrisan sa Canvas/Moodle preko IMS LTI 1.3
"""

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.registration import Registration
from rag_engine import get_rag_engine

import os
import uuid
from datetime import datetime
from semantic_layer import SemanticLayer

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)

# LTI Configuration
PAGE_TITLE = 'Inteligentni Q&A Asistent'
tool_conf = ToolConfJsonFile('configs/lti-config.json')

# Initialize Semantic Layer
semantic_layer = SemanticLayer('ontology/lms-tools.ttl')






@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'LTI Q&A Tool',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/jwks', methods=['GET'])
def get_jwks():
    """Public JWKS endpoint for LTI platform"""
    return jsonify(tool_conf.get_jwks())


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    OIDC Login endpoint - prvi korak LTI launch flow-a
    """
    target_link_uri = request.args.get('target_link_uri', request.form.get('target_link_uri'))
    if not target_link_uri:
        return 'Missing target_link_uri parameter', 400
    
    flask_request = FlaskRequest()
    oidc_login = FlaskOIDCLogin(flask_request, tool_conf, launch_data_storage=get_launch_data_storage())
    
    return oidc_login.redirect(target_link_uri)


@app.route('/launch', methods=['POST'])
def launch():
    """
    LTI 1.1 Launch endpoint (Canvas stable ne podržava LTI 1.3)
    """
    try:
        from flask import request as flask_request
        
        # Extract LTI 1.1 parameters
        user_id = flask_request.form.get('user_id', 'unknown')
        user_name = flask_request.form.get('lis_person_name_full', 'Student')
        user_email = flask_request.form.get('lis_person_contact_email_primary', '')
        
        course_id = flask_request.form.get('custom_canvas_course_id') or flask_request.form.get('context_id', 'default')
        course_title = flask_request.form.get('context_title', 'Unknown Course')
        
        roles = flask_request.form.get('roles', '').split(',')
        is_instructor = any('Instructor' in role for role in roles)
        
        # Store session
        session['user_id'] = user_id
        session['user_name'] = user_name
        session['course_id'] = course_id
        session['course_title'] = course_title
        session['is_instructor'] = is_instructor
        
        # Log launch
        semantic_layer.log_tool_launch(
            tool_uri=f"http://example.org/tools/{uuid.uuid4()}",
            course_uri=f"http://example.org/courses/{course_id}",
            user_uri=f"http://example.org/users/{user_id}"
        )
        
        return render_template(
            'qa_interface.html',
            user_name=user_name,
            course_title=course_title,
            course_id=course_id,
            is_instructor=is_instructor
        )
        
    except Exception as e:
        app.logger.error(f"Launch error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    API endpoint za postavljanje pitanja - RAG sa Ollama
    """
    try:
        app.logger.info(f"=== Q&A REQUEST ===")
        app.logger.info(f"Session data: {dict(session)}")
        app.logger.info(f"Course ID: {session.get('course_id', 'default')}")
        data = request.json
        question = data.get('question', '').strip()
        course_id = data.get('course_id', 'default')  # ← IZ REQUEST BODY
        user_id = session.get('user_id', 'anonymous')
        
        if not question:
            return jsonify({'error': 'Pitanje ne može biti prazno'}), 400
        
        # Dobij RAG engine za ovaj kurs
        rag = get_rag_engine(course_id)
        
        # Pozovi RAG pipeline
        result = rag.ask(question)
        
        # Log u semantic layer
        semantic_layer.register_qa_session(
            question_text=question,
            answer_text=result['answer'],
            course_id=course_id,
            user_id=user_id,
            confidence=result['confidence']
        )
        
        return jsonify({
            'answer': result['answer'],
            'confidence': result['confidence'],
            'cached': False,
            'sources': result['sources']
        })
        
    except Exception as e:
        app.logger.error(f"Error processing question: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Došlo je do greške pri obradi pitanja.',
            'details': str(e)
        }), 500


@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    """Debug endpoint - prikazuje session data"""
    return jsonify({
        'session': dict(session),
        'keys': list(session.keys()),
        'course_id': session.get('course_id', 'NOT_SET')
    })

@app.route('/api/admin/upload-document', methods=['POST'])
def upload_document():
    """
    Admin endpoint za upload nastavnih materijala
    Dostupno samo instruktorima
    """
    if not session.get('is_instructor', False):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Očekuje se text content u JSON
        data = request.json
        text = data.get('text', '')
        filename = data.get('filename', 'document.txt')
        course_id = session.get('course_id', 'default')
        
        if not text:
            return jsonify({'error': 'Prazan dokument'}), 400
        
        # Dodaj u RAG engine
        rag = get_rag_engine(course_id)
        success = rag.add_document(text, metadata={'filename': filename})
        
        if success:
            stats = rag.get_collection_stats()
            return jsonify({
                'status': 'success',
                'message': f'Dokument {filename} uspješno upload-ovan',
                'stats': stats
            })
        else:
            return jsonify({'error': 'Greška pri upload-u'}), 500
            
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """
    API endpoint za feedback studenta o odgovoru
    """
    data = request.json
    rating = data.get('rating')  # 1-5
    question_id = data.get('question_id')
    comment = data.get('comment', '')
    
    # Store feedback in semantic layer
    semantic_layer.add_feedback(question_id, rating, comment)
    
    return jsonify({'status': 'success'})


@app.route('/api/admin/materials', methods=['POST'])
def upload_materials():
    """
    Admin endpoint za upload nastavnih materijala
    Dostupno samo instruktorima
    """
    if not session.get('is_instructor', False):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Handle file upload and vectorization
    # TODO: Implement material processing
    
    return jsonify({'status': 'Materials uploaded successfully'})


def get_launch_data_storage():
    """
    Factory function for launch data storage - compatible with PyLTI1p3 v2.0.0
    """
    from flask import session
    
    class SimpleLaunchDataStorage:
        _storage = {}
        
        def __init__(self):
            self._request = None
        
        def set_request(self, flask_request):
            self._request = flask_request
        
        def get_session_cookie_name(self):
            return 'session'
        
        def get_launch_data(self, key):
            return session.get(f'lti_{key}') or self._storage.get(key)
        
        def save_launch_data(self, key, value):
            session[f'lti_{key}'] = value
            self._storage[key] = value
            return True
        
        def check_nonce(self, nonce):
            return True
    
    return SimpleLaunchDataStorage()

@app.route('/api/upload-material', methods=['POST'])
def upload_material():
    """
    Upload nastavnog materijala direktno iz UI-ja
    Podržava: TXT, MD, PDF, DOCX
    """
    #if not session.get('is_instructor', False):
     #   return jsonify({'error': 'Unauthorized - samo instruktori mogu upload-ovati materijale'}), 403
    
    try:
        # Proveri da li fajl postoji
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        course_id = request.form.get('course_id', 'default')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = file.filename
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        app.logger.info(f"Upload attempt: {filename} (ext: {ext})")
        
        # Procesiranje fajla na osnovu tipa
        content = None
        
        if ext in ['txt', 'md']:
            # Plain text
            content = file.read().decode('utf-8', errors='ignore')
        
        elif ext == 'pdf':
            # PDF processing
            try:
                from PyPDF2 import PdfReader
                import io
                
                pdf_bytes = file.read()
                pdf = PdfReader(io.BytesIO(pdf_bytes))
                
                pages_text = []
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            pages_text.append(text)
                    except Exception as e:
                        app.logger.warning(f"Error extracting page {page_num}: {e}")
                
                content = '\n\n'.join(pages_text)
                
                if not content.strip():
                    return jsonify({'error': 'PDF je prazan ili nije mogao biti pročitan'}), 400
                
            except Exception as e:
                app.logger.error(f"PDF processing error: {e}")
                return jsonify({'error': f'PDF greška: {str(e)}'}), 400
        
        elif ext == 'docx':
            # DOCX processing
            try:
                from docx import Document
                import io
                
                docx_bytes = file.read()
                doc = Document(io.BytesIO(docx_bytes))
                
                paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                content = '\n\n'.join(paragraphs)
                
                if not content.strip():
                    return jsonify({'error': 'DOCX je prazan'}), 400
                
            except Exception as e:
                app.logger.error(f"DOCX processing error: {e}")
                return jsonify({'error': f'DOCX greška: {str(e)}'}), 400
        
        else:
            return jsonify({'error': f'Nepodržan format: {ext}'}), 400
        
        # Provera da sadržaj nije prazan
        if not content or not content.strip():
            return jsonify({'error': 'Fajl je prazan ili nečitljiv'}), 400
        
        # Upload u ChromaDB
        rag = get_rag_engine(course_id)
        success = rag.add_document(content, {
            'filename': filename,
            'course_id': course_id,
            'file_type': ext
        })
        
        if success:
            # Izračunaj broj chunks
            chunks_count = len(content) // 800 + 1
            
            app.logger.info(f"Upload success: {filename} ({chunks_count} chunks)")
            
            return jsonify({
                'success': True,
                'filename': filename,
                'chunks': chunks_count,
                'size': len(content)
            })
        else:
            return jsonify({'error': 'Upload u ChromaDB nije uspeo'}), 500
            
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Server greška: {str(e)}'}), 500

@app.route('/api/materials', methods=['GET'])
def list_materials():
    """
    Lista svih materijala u ChromaDB
    """
    try:
        course_id = request.args.get('course_id', '1')
        
        app.logger.info(f"Fetching materials for course {course_id}")
        
        # Get RAG engine
        rag = get_rag_engine(course_id)
        
        if not rag.collection:
            return jsonify({
                'total_files': 0,
                'total_chunks': 0,
                'files': []
            })
        
        # Get all items from collection
        collection = rag.collection
        results = collection.get()
        
        if not results['ids']:
            return jsonify({
                'total_files': 0,
                'total_chunks': 0,
                'files': []
            })
        
        # Group by filename
        files = {}
        for chunk_id in results['ids']:
            # Extract filename from chunk_id (format: "filename_N")
            parts = chunk_id.rsplit('_', 1)
            if len(parts) == 2:
                filename = parts[0]
                metadata = results['metadatas'][results['ids'].index(chunk_id)] if results.get('metadatas') else {}
                
                if filename not in files:
                    files[filename] = {
                        'chunks': 0,
                        'type': metadata.get('file_type', 'unknown')
                    }
                files[filename]['chunks'] += 1
        
        # Format response
        files_list = [
            {
                'filename': name,
                'chunks': info['chunks'],
                'type': info['type']
            }
            for name, info in sorted(files.items())
        ]
        
        return jsonify({
            'total_files': len(files),
            'total_chunks': len(results['ids']),
            'files': files_list
        })
        
    except Exception as e:
        app.logger.error(f"Error listing materials: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-material', methods=['POST'])
def delete_material():
    """
    Briše specifičan materijal iz ChromaDB
    """
    try:
        data = request.json
        filename = data.get('filename')
        course_id = data.get('course_id', '1')
        
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        app.logger.info(f"Deleting material: {filename} from course {course_id}")
        
        rag = get_rag_engine(course_id)
        
        if not rag.collection:
            return jsonify({'error': 'Collection not found'}), 404
        
        collection = rag.collection
        
        # Find all chunk IDs for this file
        results = collection.get()
        ids_to_delete = [
            chunk_id for chunk_id in results['ids']
            if chunk_id.startswith(filename + '_')
        ]
        
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            
            app.logger.info(f"Deleted {len(ids_to_delete)} chunks for {filename}")
            
            return jsonify({
                'success': True,
                'deleted_chunks': len(ids_to_delete),
                'filename': filename
            })
        else:
            return jsonify({'error': 'File not found in database'}), 404
            
    except Exception as e:
        app.logger.error(f"Error deleting material: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
