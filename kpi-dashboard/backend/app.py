from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
from flask import request, jsonify
import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kpi_dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app)

db.init_app(app)
migrate = Migrate(app, db)

import models
from models import Customer, User, Account, KPIUpload, KPI, CustomerConfig
from upload_api import upload_api
from kpi_api import kpi_api
from download_api import download_api
from rag_api import rag_api
from export_api import export_api
from enhanced_rag_api import enhanced_rag_api
from enhanced_rag_openai_api import enhanced_rag_openai_api
from enhanced_rag_qdrant_api import enhanced_rag_qdrant_api
from enhanced_rag_historical_api import enhanced_rag_historical_api
# from test_api import test_api
# from enhanced_rag_temporal_api import enhanced_rag_temporal_api
from data_management_api import data_management_api
from corporate_api import corporate_api
from time_series_api import time_series_api
from cleanup_api import cleanup_api
from health_trend_api import health_trend_api
from health_status_api import health_status_api
from kpi_reference_api import kpi_reference_api
from reference_ranges_api import reference_ranges_api
from financial_projections_api import financial_projections_api
from best_practices_api import best_practices_api

# Initialize Chroma client and collection for KPI VDB (lazy loading)
global_chroma_client = None
global_kpi_collection = None
embedding_model = None

def get_chroma_client():
    global global_chroma_client, global_kpi_collection
    if global_chroma_client is None:
        import chromadb
        from chromadb.config import Settings
        global_chroma_client = chromadb.Client(Settings(persist_directory="./chroma_db"))
        global_kpi_collection = global_chroma_client.get_or_create_collection("kpis")
    return global_chroma_client, global_kpi_collection

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return embedding_model

app.register_blueprint(upload_api)
app.register_blueprint(kpi_api)
app.register_blueprint(download_api)
app.register_blueprint(rag_api)
app.register_blueprint(export_api)
app.register_blueprint(enhanced_rag_api)
app.register_blueprint(enhanced_rag_openai_api)
app.register_blueprint(enhanced_rag_qdrant_api)
app.register_blueprint(enhanced_rag_historical_api)
# app.register_blueprint(test_api)
# app.register_blueprint(enhanced_rag_temporal_api)
app.register_blueprint(data_management_api)
app.register_blueprint(corporate_api)
app.register_blueprint(time_series_api)
app.register_blueprint(cleanup_api)
from master_file_api import master_file_api
app.register_blueprint(master_file_api)
app.register_blueprint(health_trend_api)
app.register_blueprint(health_status_api)
app.register_blueprint(kpi_reference_api)
app.register_blueprint(reference_ranges_api)
app.register_blueprint(financial_projections_api)
app.register_blueprint(best_practices_api)

@app.route('/')
def home():
    """Root endpoint for health check and timestamp."""
    # Use local timezone for timestamp
    local_tz = datetime.datetime.now().astimezone().tzinfo
    now = datetime.datetime.now(local_tz).isoformat()
    return f"KPI Dashboard Backend is running! Timestamp: {now}"

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint that doesn't require database access."""
    return jsonify({
        'status': 'success',
        'message': 'Backend is working correctly',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/chroma/add_kpi', methods=['POST'])
def add_kpi_to_chroma():
    """Add a KPI to the Chroma vector database for semantic search."""
    data = request.json
    kpi_id = data['kpi_id']
    upload_id = data['upload_id']
    kpi_text = data['kpi_text']

    # Get Chroma client and embedding model (lazy loading)
    chroma_client, kpi_collection = get_chroma_client()
    embedding_model = get_embedding_model()

    # Generate embedding automatically
    embedding = embedding_model.encode([kpi_text])[0].tolist()

    kpi_collection.add(
        embeddings=[embedding],
        documents=[kpi_text],
        metadatas=[{"kpi_id": kpi_id, "upload_id": upload_id}],
        ids=[f"kpi_{kpi_id}"]
    )
    return jsonify({"success": True})

@app.route('/api/chroma/query', methods=['POST'])
def query_chroma():
    """Query the Chroma vector database for similar KPIs using semantic search."""
    data = request.json
    query_text = data['query']
    n_results = data.get('n_results', 5)

    # Get Chroma client and embedding model (lazy loading)
    chroma_client, kpi_collection = get_chroma_client()
    embedding_model = get_embedding_model()

    # Generate embedding for the query
    query_embedding = embedding_model.encode([query_text])[0].tolist()

    results = kpi_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return jsonify(results)

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new customer and user account."""
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    if not all([name, email, phone, password]):
        return jsonify({'message': 'All fields are required'}), 400
    if Customer.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400
    customer = Customer(customer_name=name, email=email, phone=phone)
    db.session.add(customer)
    db.session.flush()  # get customer_id
    user = User(customer_id=customer.customer_id, user_name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({
        'customer_id': customer.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate a user and return session info."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401
    return jsonify({
        'customer_id': user.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email
    }), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5059) 