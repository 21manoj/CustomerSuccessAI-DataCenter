#!/usr/bin/env python3
"""
V5 Production App
Includes all essential APIs with session-based authentication and multi-tenant support
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

# Enable debug mode for better error messages
app.config['DEBUG'] = True

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

# Ensure sessions table exists before initializing Flask-Session
with app.app_context():
    db.create_all()  # This will create the sessions table if it doesn't exist

# Initialize Flask-Session (database-backed sessions)
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
try:
    Session(app)
except Exception as e:
    print(f"⚠️  Warning: Flask-Session initialization issue: {e}")
    print("   Sessions will still work, but cleanup may be disabled")

# Initialize Flask-Login (user session management)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    from models import User
    try:
        user = User.query.get(int(user_id))
        if user:
            # Refresh to ensure we have latest data from database (including customer_id)
            db.session.refresh(user)
        return user
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

# Initialize global authentication middleware
from auth_middleware import init_auth_middleware, get_current_customer_id, get_current_user_id
# Activity logging - optional, only import if ActivityLog model exists
try:
    from activity_logging import activity_logger
except ImportError:
    # Create a dummy logger if ActivityLog model doesn't exist
    class DummyActivityLogger:
        def log_login(self, *args, **kwargs): pass
        def log_logout(self, *args, **kwargs): pass
        def log_settings_change(self, *args, **kwargs): pass
        def log_data_upload(self, *args, **kwargs): pass
        def log_query(self, *args, **kwargs): pass
    activity_logger = DummyActivityLogger()
init_auth_middleware(app)

# Validate OpenAI API key support on startup
try:
    from validate_openai_key_support import validate_openai_key_support
    errors, warnings = validate_openai_key_support()
    if errors:
        print("\n" + "="*70)
        print("❌ OPENAI API KEY SUPPORT VALIDATION FAILED")
        print("="*70)
        for error in errors:
            print(f"   ❌ {error}")
        print("\n💡 Fix these errors before using OpenAI API key features!")
        print("   Run: python backend/migrate_add_openai_key.py")
        print("="*70 + "\n")
    elif warnings:
        print("\n" + "="*70)
        print("⚠️  OPENAI API KEY SUPPORT WARNINGS")
        print("="*70)
        for warning in warnings:
            print(f"   ⚠️  {warning}")
        print("="*70 + "\n")
    else:
        print("✅ OpenAI API key support validated successfully")
except Exception as e:
    print(f"⚠️  Could not validate OpenAI API key support: {e}")
    print("   Continuing startup, but OpenAI features may not work correctly")

import models
from models import Customer, User, Account, KPIUpload, KPI, CustomerConfig

# Register only essential APIs
from upload_api import upload_api
from kpi_api import kpi_api
from download_api import download_api
from data_management_api import data_management_api
from corporate_api import corporate_api
from openai_key_api import openai_key_api
from time_series_api import time_series_api
from cleanup_api import cleanup_api
from health_trend_api import health_trend_api
from health_status_api import health_status_api
# kpi_reference_api and reference_ranges_api are deprecated - not registered
# from kpi_reference_api import kpi_reference_api
# from reference_ranges_api import reference_ranges_api
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
from customer_performance_summary_api import customer_perf_summary_api
from workflow_config_api import workflow_config_api
from export_api import export_api
from rehydration_api import rehydration_api
from data_quality_api import data_quality_api
from customer_profile_api import customer_profile_api
from enhanced_upload_api import enhanced_upload_api
from enhanced_rag_openai_api import enhanced_rag_openai_api
from secure_file_api import secure_file_api
from master_file_api import master_file_api

# Optional RAG APIs - only register if dependencies are available
try:
    from enhanced_rag_historical_api import enhanced_rag_historical_api
    HAS_HISTORICAL_RAG = True
except ImportError as e:
    print(f"⚠️  Warning: enhanced_rag_historical_api not available: {e}")
    HAS_HISTORICAL_RAG = False

try:
    from enhanced_rag_temporal_api import enhanced_rag_temporal_api
    HAS_TEMPORAL_RAG = True
except ImportError as e:
    print(f"⚠️  Warning: enhanced_rag_temporal_api not available: {e}")
    HAS_TEMPORAL_RAG = False

try:
    from enhanced_rag_qdrant_api import enhanced_rag_qdrant_api
    HAS_QDRANT_RAG = True
except ImportError as e:
    print(f"⚠️  Warning: enhanced_rag_qdrant_api not available: {e}")
    HAS_QDRANT_RAG = False

app.register_blueprint(upload_api)
app.register_blueprint(enhanced_upload_api)
app.register_blueprint(kpi_api)
app.register_blueprint(download_api)
app.register_blueprint(secure_file_api)
app.register_blueprint(data_management_api)
app.register_blueprint(corporate_api)
app.register_blueprint(time_series_api)
app.register_blueprint(cleanup_api)
app.register_blueprint(health_trend_api)
app.register_blueprint(health_status_api)
# Deprecated APIs - not registered (replaced by kpi_reference_ranges_api)
# kpi_reference_api - replaced by kpi_reference_ranges_api
# reference_ranges_api - has swapped values, deprecated
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
app.register_blueprint(customer_perf_summary_api)
app.register_blueprint(workflow_config_api)
app.register_blueprint(export_api)
app.register_blueprint(rehydration_api)

# Activity log API - optional if ActivityLog model doesn't exist
try:
    from activity_log_api import activity_log_api
    app.register_blueprint(activity_log_api)
    print("✅ Registered activity_log_api")
except ImportError as e:
    print(f"⚠️  Warning: activity_log_api not available: {e}")
    print("   Skipped activity_log_api (ActivityLog model may not exist)")

# Governance RAG API - uses standard OpenAI (required dependency)
try:
    from governance_rag_api import governance_rag_api
    app.register_blueprint(governance_rag_api)
    print("✅ Registered governance_rag_api")
except ImportError as e:
    print(f"⚠️  Warning: governance_rag_api not available: {e}")
    print("   Skipped governance_rag_api")
app.register_blueprint(openai_key_api)
app.register_blueprint(data_quality_api)
app.register_blueprint(customer_profile_api)
app.register_blueprint(enhanced_rag_openai_api)
app.register_blueprint(master_file_api)

# Register optional RAG APIs only if available
if HAS_HISTORICAL_RAG:
    app.register_blueprint(enhanced_rag_historical_api)
    print("✅ Registered enhanced_rag_historical_api")
else:
    print("⚠️  Skipped enhanced_rag_historical_api (qdrant_client not available)")

if HAS_TEMPORAL_RAG:
    app.register_blueprint(enhanced_rag_temporal_api)
    print("✅ Registered enhanced_rag_temporal_api")
else:
    print("⚠️  Skipped enhanced_rag_temporal_api (dependencies not available)")

if HAS_QDRANT_RAG:
    app.register_blueprint(enhanced_rag_qdrant_api)
    print("✅ Registered enhanced_rag_qdrant_api")
else:
    print("⚠️  Skipped enhanced_rag_qdrant_api (qdrant_client not available)")

# Load persisted data on startup
@app.before_request
def initialize_data_once():
    """Load persisted data from database on first request"""
    if not hasattr(app, '_data_initialized'):
        try:
            from playbook_execution_api import load_executions_from_db
            load_executions_from_db()
            print("✓ Initialized persisted data on startup")
            app._data_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize persisted data: {e}")
            app._data_initialized = True  # Prevent repeated attempts

@app.route('/')
def home():
    """Root endpoint for health check and timestamp."""
    # Use local timezone for timestamp
    local_tz = datetime.datetime.now().astimezone().tzinfo
    now = datetime.datetime.now(local_tz).isoformat()
    return f"KPI Dashboard V5 Backend is running! Timestamp: {now}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': 'V5',
        'timestamp': datetime.datetime.now().isoformat(),
        'message': 'KPI Dashboard V5 Backend is running'
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
        from models import KPI, HealthTrend
        
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
                from playbook_recommendations_api import calculate_health_score_proxy
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
        
        if not user:
            # Log failed login attempt (user not found)
            try:
                # Try to find customer by email domain or use default
                customer_id = 1  # Default, will be logged as unknown user
                activity_logger.log_login(
                    customer_id=customer_id,
                    user_id=None,
                    status='failure',
                    error_message='User not found'
                )
            except:
                pass
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Check password hash (handle None case)
        if not user.password_hash:
            # Log failed login attempt
            try:
                activity_logger.log_login(
                    customer_id=user.customer_id,
                    user_id=user.user_id,
                    status='failure',
                    error_message='User account has no password set'
                )
            except:
                pass
            return jsonify({
                'status': 'error',
                'message': 'User account has no password set. Please contact support.'
            }), 401
        
        if not check_password_hash(user.password_hash, password):
            # Log failed login attempt (wrong password)
            try:
                activity_logger.log_login(
                    customer_id=user.customer_id,
                    user_id=user.user_id,
                    status='failure',
                    error_message='Invalid password'
                )
            except:
                pass
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Check if user account is active (handle None as active for backwards compatibility)
        if user.active is False:
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
        
        # Log successful login
        try:
            activity_logger.log_login(
                customer_id=user.customer_id,
                user_id=user.user_id,
                status='success'
            )
        except Exception as log_error:
            print(f"Warning: Failed to log login activity: {log_error}")
        
        # Refresh user from database to ensure we have latest data
        db.session.refresh(user)
        
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
        import traceback
        error_traceback = traceback.format_exc()
        traceback.print_exc()  # Print full traceback to console
        return jsonify({
            'status': 'error',
            'message': f'Login failed: {str(e)}',
            'traceback': error_traceback  # Always include for debugging
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """
    User logout endpoint - destroys session.
    
    SECURITY: Properly destroys server-side session.
    """
    try:
        from flask_login import logout_user, login_required
        
        # Get user info before logout
        user_id = session.get('user_id')
        customer_id = session.get('customer_id')
        
        # Check if user is logged in
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'success',
                'message': 'Already logged out'
            }), 200
        
        # Log logout before destroying session
        if user_id and customer_id:
            try:
                activity_logger.log_logout(
                    customer_id=customer_id,
                    user_id=user_id
                )
            except Exception as log_error:
                print(f"Warning: Failed to log logout activity: {log_error}")
        
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

@app.route('/api/session', methods=['GET'])
def session_info():
    """
    Backwards-compat endpoint for frontend session check.
    Mirrors /api/session/status shape with user details when authenticated.
    """
    if current_user.is_authenticated:
        from models import User, Customer
        user = User.query.get(current_user.user_id)
        return jsonify({
            'authenticated': True,
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'user_name': user.user_name,
                'customer_id': user.customer_id
            }
        }), 200
    return jsonify({'authenticated': False}), 401

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
    # Option 1: Production-ready - no auto-reload (code changes require manual restart)
    app.run(host='0.0.0.0', port=5059, debug=False)
