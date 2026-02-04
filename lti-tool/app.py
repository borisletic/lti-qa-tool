"""
LTI Q&A Tool - Flask Application
Inteligentni Q&A Agent integrisan sa Canvas/Moodle preko IMS LTI 1.3
"""

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.registration import Registration

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
    API endpoint - MOCK verzija
    """
    try:
        data = request.json
        question = data.get('question', '').strip()
        course_id = session.get('course_id', 'default')
        user_id = session.get('user_id', 'anonymous')
        
        if not question:
            return jsonify({'error': 'Pitanje ne može biti prazno'}), 400
        
        # Simple mock
        if 'lti' in question.lower():
            answer = "LTI (Learning Tools Interoperability) je standard za integraciju eksternih alata u LMS platforme. Canvas koristi LTI 1.1 verziju."
            confidence = 0.9
        else:
            answer = f"Primio sam pitanje: '{question}'. Sistem je trenutno u test modu."
            confidence = 0.6
        
        return jsonify({
            'answer': answer,
            'confidence': confidence,
            'cached': False,
            'sources': []
        })
        
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
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


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
