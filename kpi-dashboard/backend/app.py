from flask import Flask
from auth_middleware import get_current_customer_id, get_current_user_id
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
from flask import request, jsonify
import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

# Load environment variables - explicitly load from backend directory
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Database configuration - REQUIRE PostgreSQL via DATABASE_URL
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if database_url:
    # Ensure it's PostgreSQL
    if not database_url.startswith('postgresql://') and not database_url.startswith('postgres://'):
        raise ValueError(
            f"❌ ERROR: DATABASE_URL must be PostgreSQL. Got: {database_url[:50]}...\n"
            "Please set DATABASE_URL to a PostgreSQL connection string.\n"
            "Example: postgresql://user:password@localhost:5432/dbname"
        )
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"✅ Using PostgreSQL database: {database_url[:50]}..." if len(database_url) > 50 else f"✅ Using PostgreSQL database: {database_url}")
else:
    raise ValueError(
        "❌ ERROR: DATABASE_URL environment variable is required.\n"
        "Please set DATABASE_URL to a PostgreSQL connection string.\n"
        "Example: postgresql://user:password@localhost:5432/dbname"
    )
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CORS configuration - allow frontend on port 8005
CORS(app, origins=['http://localhost:8005', 'http://localhost:3000'], supports_credentials=True)

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
from simple_rag_api import simple_rag_api
from simple_working_rag_api import simple_working_rag_api
from direct_rag_api import direct_rag_api
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
from analytics_api import analytics_api
from unified_query_api import unified_query_api
from cache_api import cache_api
from playbook_triggers_api import playbook_triggers_api
from playbook_execution_api import playbook_execution_api
from playbook_reports_api import playbook_reports_api
from playbook_recommendations_api import playbook_recommendations_api
from feature_toggle_api import feature_toggle_api
from registration_api import registration_api
from kpi_reference_ranges_api import kpi_reference_ranges_api
from customer_performance_summary_api import customer_perf_summary_api
from api_routes_dc import api_routes_dc
from agents.signal_analyst_api import signal_analyst_api

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
app.register_blueprint(simple_rag_api)
app.register_blueprint(simple_working_rag_api)
app.register_blueprint(direct_rag_api)
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
app.register_blueprint(analytics_api)
app.register_blueprint(unified_query_api)
app.register_blueprint(cache_api)
app.register_blueprint(playbook_triggers_api)
app.register_blueprint(playbook_execution_api)
app.register_blueprint(playbook_reports_api)
app.register_blueprint(playbook_recommendations_api)
app.register_blueprint(feature_toggle_api)
app.register_blueprint(registration_api)
app.register_blueprint(kpi_reference_ranges_api)
app.register_blueprint(customer_perf_summary_api)
app.register_blueprint(api_routes_dc)
app.register_blueprint(signal_analyst_api)

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

@app.route('/api/accounts-working', methods=['GET'])
def get_accounts_working():
    """Working accounts endpoint that returns mock data."""
    customer_id = get_current_customer_id()
    accounts = [
        {"account_id": 1, "customer_id": int(customer_id), "account_name": "TechCorp Solutions", "revenue": 2500000, "status": "active", "industry": "Technology"},
        {"account_id": 2, "customer_id": int(customer_id), "account_name": "Global Manufacturing Inc", "revenue": 8500000, "status": "active", "industry": "Manufacturing"},
        {"account_id": 3, "customer_id": int(customer_id), "account_name": "Healthcare Systems Ltd", "revenue": 4200000, "status": "active", "industry": "Healthcare"},
        {"account_id": 4, "customer_id": int(customer_id), "account_name": "Financial Services Group", "revenue": 15000000, "status": "active", "industry": "Financial Services"},
        {"account_id": 5, "customer_id": int(customer_id), "account_name": "Retail Chain Corp", "revenue": 6800000, "status": "active", "industry": "Retail"}
    ]
    return jsonify(accounts)

@app.route('/api/kpis-working', methods=['GET'])
def get_kpis_working():
    """Working KPIs endpoint that returns mock data."""
    customer_id = get_current_customer_id()
    kpis = [
        {"kpi_id": 1, "account_id": 1, "kpi_name": "Monthly Recurring Revenue", "current_value": 2500000, "target_value": 3000000, "status": "below_target", "trend": "increasing"},
        {"kpi_id": 2, "account_id": 1, "kpi_name": "Customer Acquisition Cost", "current_value": 150, "target_value": 120, "status": "above_target", "trend": "decreasing"},
        {"kpi_id": 3, "account_id": 2, "kpi_name": "Production Efficiency", "current_value": 85, "target_value": 90, "status": "below_target", "trend": "stable"},
        {"kpi_id": 4, "account_id": 3, "kpi_name": "Patient Satisfaction", "current_value": 4.2, "target_value": 4.5, "status": "below_target", "trend": "increasing"},
        {"kpi_id": 5, "account_id": 4, "kpi_name": "Net Interest Margin", "current_value": 3.2, "target_value": 3.0, "status": "above_target", "trend": "stable"}
    ]
    return jsonify(kpis)

@app.route('/api/health-scores-working', methods=['GET'])
def get_health_scores_working():
    """Working health scores endpoint that returns mock data."""
    customer_id = get_current_customer_id()
    health_scores = [
        {"account_id": 1, "account_name": "TechCorp Solutions", "overall_score": 75, "financial_score": 80, "operational_score": 70, "growth_score": 75},
        {"account_id": 2, "account_name": "Global Manufacturing Inc", "overall_score": 85, "financial_score": 90, "operational_score": 80, "growth_score": 85},
        {"account_id": 3, "account_name": "Healthcare Systems Ltd", "overall_score": 70, "financial_score": 75, "operational_score": 65, "growth_score": 70},
        {"account_id": 4, "account_name": "Financial Services Group", "overall_score": 90, "financial_score": 95, "operational_score": 85, "growth_score": 90},
        {"account_id": 5, "account_name": "Retail Chain Corp", "overall_score": 65, "financial_score": 70, "operational_score": 60, "growth_score": 65}
    ]
    return jsonify(health_scores)

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
    vertical = data.get('vertical', 'saas')  # Default to 'saas' if not provided
    
    # Validate vertical
    valid_verticals = ['saas', 'datacenter']
    if vertical not in valid_verticals:
        return jsonify({'message': f'Invalid vertical. Must be one of: {", ".join(valid_verticals)}'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    # Get customer to check/store vertical preference
    customer = Customer.query.filter_by(customer_id=user.customer_id).first()
    
    # Store vertical preference in customer if not already set (optional - can be stored in session only)
    # For now, we'll just return it in the response
    
    return jsonify({
        'customer_id': user.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email,
        'vertical': vertical,
        'user': {
            'customer_id': user.customer_id,
            'user_id': user.user_id,
            'user_name': user.user_name,
            'email': user.email,
            'customer_name': customer.customer_name if customer else 'Unknown'
        }
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('FLASK_RUN_PORT', os.getenv('PORT', 8001)))
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host=host, port=port) 