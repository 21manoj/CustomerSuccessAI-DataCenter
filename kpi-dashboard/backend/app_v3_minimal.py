#!/usr/bin/env python3
"""
Minimal V3 App for Testing
Only includes essential APIs without heavy dependencies
"""

from flask import Flask, request, jsonify, session
from flask_migrate import Migrate
from flask_cors import CORS
from flask_session import Session
from flask_login import LoginManager, current_user
from extensions import db
import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load configuration
import os
env = os.getenv('FLASK_ENV', 'development')
if env == 'production':
    app.config.from_object('config.ProductionConfig')
elif env == 'testing':
    app.config.from_object('config.TestingConfig')
else:
    app.config.from_object('config.DevelopmentConfig')

# Use local path for development, Docker path for production
if os.path.exists('/app/instance'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/kpi_dashboard.db'
else:
    # Local development
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

# Enable CORS with credentials support
CORS(app, supports_credentials=True, origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']))

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Session (database-backed sessions)
app.config['SESSION_SQLALCHEMY'] = db
Session(app)

# Initialize Flask-Login (user session management)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    from models import User
    return User.query.get(int(user_id))

# Initialize global authentication middleware
from auth_middleware import init_auth_middleware, get_current_customer_id, get_current_user_id
init_auth_middleware(app)

import models
from models import Customer, User, Account, KPIUpload, KPI, CustomerConfig

# Register only essential APIs
from upload_api import upload_api
from kpi_api import kpi_api
from download_api import download_api
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
from direct_rag_api import direct_rag_api

app.register_blueprint(upload_api)
app.register_blueprint(kpi_api)
app.register_blueprint(download_api)
app.register_blueprint(data_management_api)
app.register_blueprint(corporate_api)
app.register_blueprint(time_series_api)
app.register_blueprint(cleanup_api)
app.register_blueprint(health_trend_api)
app.register_blueprint(health_status_api)
# Don't register kpi_reference_api - it's been replaced by kpi_reference_ranges_api
# app.register_blueprint(kpi_reference_api)
# Don't register reference_ranges_api - it has swapped values
# app.register_blueprint(reference_ranges_api)
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
app.register_blueprint(direct_rag_api)

@app.route('/')
def home():
    """Root endpoint for health check and timestamp."""
    # Use local timezone for timestamp
    local_tz = datetime.datetime.now().astimezone().tzinfo
    now = datetime.datetime.now(local_tz).isoformat()
    return f"KPI Dashboard V3 Backend is running! Timestamp: {now}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': 'V3',
        'timestamp': datetime.datetime.now().isoformat(),
        'message': 'KPI Dashboard V3 Backend is running'
    })

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """
    Get accounts for the customer.
    
    SECURITY: Requires authentication. Uses customer_id from session.
    """
    # SECURITY FIX: Require authentication
    if not current_user.is_authenticated:
        return jsonify({
            'error': 'Authentication required',
            'message': 'Please log in to access this resource'
        }), 401
    
    try:
        # SECURITY FIX: Get customer_id from authenticated user session (not headers!)
        customer_id = current_user.customer_id
        
        # Get accounts from database
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Import models needed for health score calculation
        from backend.models import KPI, HealthTrend
        
        result = []
        for account in accounts:
            # First try to get health score from health_trends table
            latest_trend = HealthTrend.query.filter_by(
                account_id=account.account_id,
                customer_id=customer_id
            ).order_by(
                HealthTrend.year.desc(),
                HealthTrend.month.desc()
            ).first()
            
            health_score = None
            if latest_trend and latest_trend.overall_health_score:
                health_score = float(latest_trend.overall_health_score)
            else:
                # Calculate health score on-the-fly from KPIs
                from backend.playbook_recommendations_api import calculate_health_score_proxy
                health_score = calculate_health_score_proxy(account.account_id)
            
            result.append({
                'account_id': account.account_id,
                'customer_id': account.customer_id,
                'account_name': account.account_name,
                'revenue': account.revenue,
                'status': account.status,
                'industry': account.industry,
                'region': account.region,
                'health_score': health_score,
                'account_status': account.status,
                'created_at': account.created_at.isoformat() if account.created_at else None
            })
        
        return jsonify({
            'status': 'success',
            'accounts': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch accounts: {str(e)}'
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """
    User login endpoint with session creation.
    
    SECURITY: Uses Flask-Login to create secure server-side sessions.
    No more X-Customer-ID headers - session handles authentication.
    """
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)  # Remember me checkbox
        
        if not email or not password:
            return jsonify({
                'status': 'error',
                'message': 'Email and password are required'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Check if user account is active
        if not user.active:
            return jsonify({
                'status': 'error',
                'message': 'Account is inactive. Contact support.'
            }), 403
        
        # Get customer info
        customer = Customer.query.get(user.customer_id)
        
        # Log in user - Flask-Login creates secure session
        from flask_login import login_user
        login_user(user, remember=remember)
        
        # Store additional session data for quick access
        session['customer_id'] = user.customer_id
        session['user_id'] = user.user_id
        session['login_time'] = datetime.datetime.utcnow().isoformat()
        session['ip_address'] = request.remote_addr
        session['user_agent'] = request.headers.get('User-Agent', '')[:500]
        session.permanent = True  # Enable session timeout
        
        # Update user's last login
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'user_name': user.user_name,
                'customer_id': user.customer_id,
                'customer_name': customer.customer_name if customer else 'Unknown'
            },
            'session_expires': (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).isoformat() if not remember else None
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Login failed: {str(e)}'
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """
    User logout endpoint - destroys session.
    
    SECURITY: Properly destroys server-side session.
    """
    try:
        from flask_login import logout_user, login_required
        
        # Check if user is logged in
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'success',
                'message': 'Already logged out'
            }), 200
        
        # Logout user (destroys Flask-Login session)
        logout_user()
        
        # Clear session data
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Logout failed: {str(e)}'
        }), 500

@app.route('/api/session/status', methods=['GET'])
def session_status():
    """Check if user is authenticated"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'user_id': current_user.user_id,
                'email': current_user.email,
                'customer_id': current_user.customer_id
            }
        }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 401

@app.route('/api/session/refresh', methods=['POST'])
def session_refresh():
    """Refresh session on user activity"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    
    session.modified = True  # Mark session as modified to update expiry
    session['last_activity'] = datetime.datetime.utcnow().isoformat()
    
    return jsonify({
        'status': 'success',
        'expires_at': (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).isoformat()
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5059, debug=False)
