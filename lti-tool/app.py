"""
LTI Q&A Tool - Flask Application
Inteligentni Q&A Agent integrisan sa Canvas/Moodle preko IMS LTI 1.3
"""

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.registration import Registration
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
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

# Custom prompt template for educational Q&A
QA_PROMPT_TEMPLATE = """Ti si stručni obrazovni asistent koji pomaže studentima da razumeju nastavni materijal.

Kontekst iz nastavnih materijala:
{context}

Pitanje studenta: {question}

Uputstva:
- Daj jasan, precizan i razumljiv odgovor baziran na priloženom kontekstu
- Ako odgovor nije u kontekstu, iskreno to navedi
- Koristi primere gde je to moguće
- Odgovori na srpskom jeziku
- Budi prijateljski nastrojen ali profesionalan

Odgovor:"""

QA_PROMPT = PromptTemplate(
    template=QA_PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)


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
    LTI Launch endpoint - prijem i validacija LTI launch zahteva
    """
    flask_request = FlaskRequest()
    launch = FlaskMessageLaunch(
        flask_request,
        tool_conf,
        launch_data_storage=get_launch_data_storage()
    )
    
    # Validate launch request
    launch_data = launch.get_launch_data()
    
    # Extract context information
    user_id = launch_data.get('sub')
    user_name = launch_data.get('name', 'Student')
    user_email = launch_data.get('email', '')
    
    context = launch_data.get('https://purl.imsglobal.org/spec/lti/claim/context', {})
    course_id = context.get('id', 'default')
    course_label = context.get('label', 'Course')
    course_title = context.get('title', 'Unknown Course')
    
    roles = launch_data.get('https://purl.imsglobal.org/spec/lti/claim/roles', [])
    is_instructor = any('Instructor' in role for role in roles)
    
    # Store session data
    session['user_id'] = user_id
    session['user_name'] = user_name
    session['course_id'] = course_id
    session['course_title'] = course_title
    session['is_instructor'] = is_instructor
    
    # Log launch to semantic layer
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


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    API endpoint za postavljanje pitanja
    """
    try:
        data = request.json
        question = data.get('question', '').strip()
        course_id = session.get('course_id', 'default')
        user_id = session.get('user_id', 'anonymous')
        
        if not question:
            return jsonify({'error': 'Pitanje ne može biti prazno'}), 400
        
        # Check for similar questions in semantic layer
        similar_questions = semantic_layer.find_similar_questions(question, course_id)
        
        if similar_questions and similar_questions[0]['confidence'] > 0.85:
            # Return cached answer with high confidence
            cached = similar_questions[0]
            return jsonify({
                'answer': cached['answer'],
                'confidence': cached['confidence'],
                'cached': True,
                'sources': []
            })
        
        # Load course materials from vector database
        vector_db_path = f"./data/courses/{course_id}"
        
        if not os.path.exists(vector_db_path):
            return jsonify({
                'error': 'Nastavni materijali za ovaj kurs još nisu učitani. Molimo kontaktirajte predavača.',
                'answer': None
            }), 404
        
        # Initialize retriever
        embeddings = OpenAIEmbeddings(
            openai_api_key=os.environ.get('OPENAI_API_KEY')
        )
        vectorstore = Chroma(
            persist_directory=vector_db_path,
            embedding_function=embeddings
        )
        
        # Create QA chain
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.2,
            openai_api_key=os.environ.get('OPENAI_API_KEY')
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": QA_PROMPT}
        )
        
        # Generate answer
        result = qa_chain({"query": question})
        answer = result['result']
        source_docs = result['source_documents']
        
        # Extract sources
        sources = []
        for doc in source_docs:
            sources.append({
                'content': doc.page_content[:200] + '...',
                'metadata': doc.metadata
            })
        
        # Calculate confidence (simple heuristic)
        confidence = min(0.95, 0.6 + (len(answer) / 500) * 0.3)
        
        # Log to semantic layer
        semantic_layer.register_qa_session(
            question_text=question,
            answer_text=answer,
            course_id=course_id,
            user_id=user_id,
            confidence=confidence
        )
        
        return jsonify({
            'answer': answer,
            'confidence': confidence,
            'cached': False,
            'sources': sources
        })
        
    except Exception as e:
        app.logger.error(f"Error processing question: {str(e)}")
        return jsonify({
            'error': 'Došlo je do greške pri obradi pitanja. Molimo pokušajte ponovo.',
            'details': str(e) if app.debug else None
        }), 500


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
    Factory function for launch data storage
    U produkciji koristiti Redis ili database
    """
    from pylti1p3.session import FlaskSessionService
    return FlaskSessionService(request)


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
