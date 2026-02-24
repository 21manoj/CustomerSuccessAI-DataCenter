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
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False
from extensions import db
from utils.logging_config import initialize_logging

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

# Database configuration - USE POSTGRESQL (no more SQLite!)
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"✅ Using PostgreSQL database: {database_url[:50]}..." if len(database_url) > 50 else f"✅ Using PostgreSQL database: {database_url}")
else:
    raise ValueError(
        "❌ ERROR: DATABASE_URL environment variable is required.\n"
        "Please set DATABASE_URL to a PostgreSQL connection string.\n"
        "Example: postgresql://user:password@localhost:5432/dbname"
    )

# Enable CORS with credentials support
# Allow both common frontend ports
default_origins = ['http://localhost:3000', 'http://localhost:8005', 'http://127.0.0.1:3000', 'http://127.0.0.1:8005']
CORS(app, supports_credentials=True, origins=app.config.get('CORS_ORIGINS', default_origins))

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Initialize rate limiter (optional - degrades gracefully if flask-limiter not installed)
if HAS_LIMITER:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per minute"],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        enabled=app.config.get('RATELIMIT_ENABLED', True)
    )
else:
    limiter = None
    print("⚠️  flask-limiter not installed, rate limiting disabled")

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
# Initialize structured logging FIRST
logger = initialize_logging()
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    from models import User
    try:
        user = db.session.get(User, int(user_id))
        if user:
            # Refresh to ensure we have latest data from database (including customer_id)
            db.session.refresh(user)
        return user
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

# Initialize global authentication middleware
from auth_middleware import init_auth_middleware, get_current_customer_id, get_current_user_id

# Initialize event system for automatic snapshot creation
try:
    from event_system import event_manager
    event_manager.start()
    print("✅ Event system started - Account snapshot auto-creation enabled")
except Exception as e:
    print(f"⚠️  Warning: Event system not available: {e}")
    print("   Account snapshots will need to be created manually")
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
import models_action_interface  # Phase 1 — Action Interface tables
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

# Product Analytics API - Initialize flag first
PRODUCT_ANALYTICS_AVAILABLE = False
try:
    from product_analytics_api import product_analytics_api
    PRODUCT_ANALYTICS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Product Analytics API not available: {e}")
from workflow_config_api import workflow_config_api
from export_api import export_api
from rehydration_api import rehydration_api
from data_quality_api import data_quality_api
from customer_profile_api import customer_profile_api
from enhanced_upload_api import enhanced_upload_api
from enhanced_rag_openai_api import enhanced_rag_openai_api
from secure_file_api import secure_file_api
from master_file_api import master_file_api
from account_snapshot_api import account_snapshot_api
from wizard_blueprint import wizard_bp
# Config-aware onboarding API (V2)
try:
    from onboarding_api_v2_config_aware import onboarding_api as onboarding_api_v2
    ONBOARDING_API_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Config-aware Onboarding API V2 not available: {e}")
    ONBOARDING_API_V2_AVAILABLE = False
    onboarding_api_v2 = None

# Legacy onboarding_api removed — use onboarding_api_v2_config_aware instead

# Config-aware upload API (V2)
try:
    from upload_api_v2_config_aware import upload_api as upload_api_v2
    UPLOAD_API_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Config-aware Upload API V2 not available: {e}")
    UPLOAD_API_V2_AVAILABLE = False
    upload_api_v2 = None

# Improved upload API (V3) with duplicate handling
try:
    from upload_api_v3_improved_duplicates import upload_api_v3_improved
    UPLOAD_API_V3_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Upload API V3 (improved duplicates) not available: {e}")
    UPLOAD_API_V3_AVAILABLE = False
    upload_api_v3_improved = None

# Revenue Intelligence API (Power of 1)
try:
    from revenue_intelligence_api import revenue_intelligence_api
    HAS_REVENUE_INTELLIGENCE_API = True
except ImportError as e:
    print(f"⚠️  Warning: Revenue Intelligence API not available: {e}")
    HAS_REVENUE_INTELLIGENCE_API = False

# Signal Analyst Agent API
try:
    from agents.signal_analyst_api import signal_analyst_api
    HAS_SIGNAL_ANALYST_API = True
except ImportError as e:
    print(f"⚠️  Warning: Signal Analyst API not available: {e}")
    HAS_SIGNAL_ANALYST_API = False

# DC2_S Vertical API
try:
    from verticals.dc2_s.api_routes import dc2s_api
    HAS_DC2S_API = True
except ImportError as e:
    print(f"⚠️  Warning: DC2_S API not available: {e}")
    HAS_DC2S_API = False


# Optional RAG APIs - only register if dependencies are available
try:
    from enhanced_rag_historical_api import enhanced_rag_historical_api
    HAS_HISTORICAL_RAG = True
except Exception as e:
    print(f"⚠️  Warning: enhanced_rag_historical_api not available: {e}")
    HAS_HISTORICAL_RAG = False

try:
    from enhanced_rag_temporal_api import enhanced_rag_temporal_api
    HAS_TEMPORAL_RAG = True
except Exception as e:
    print(f"⚠️  Warning: enhanced_rag_temporal_api not available: {e}")
    HAS_TEMPORAL_RAG = False

try:
    from enhanced_rag_qdrant_api import enhanced_rag_qdrant_api
    HAS_QDRANT_RAG = True
except ImportError as e:
    print(f"⚠️  Warning: enhanced_rag_qdrant_api not available: {e}")
    HAS_QDRANT_RAG = False

# Register upload API (V3 improved duplicates takes precedence, then V2, then legacy)
# IMPORTANT: V3 supports multi-file-type uploads with duplicate handling
# V2 and legacy are KPI-only and should NOT be registered if V3 is available
if UPLOAD_API_V3_AVAILABLE:
    app.register_blueprint(upload_api_v3_improved, url_prefix='/api')
    print("✅ Registered Upload API V3 (Improved Duplicates): /api/upload/*")
    print("   - Multi-file-type support (kpis, signals, accounts, products, profiles, customers)")
    print("   - Duplicate handling strategies (skip, update, error, replace)")
    print("   - Config-aware filtering for KPIs")
elif UPLOAD_API_V2_AVAILABLE:
    app.register_blueprint(upload_api_v2, url_prefix='/api')
    print("⚠️  Registered Config-Aware Upload API V2: /api/upload/* (V3 not available, using V2)")
else:
    app.register_blueprint(upload_api)
    print("⚠️  Registered Upload API (legacy) - V3 and V2 not available")
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
app.register_blueprint(account_snapshot_api)

# Product Analytics API
if PRODUCT_ANALYTICS_AVAILABLE:
    app.register_blueprint(product_analytics_api)
    print("✅ Registered product_analytics_api")

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

# Register Revenue Intelligence API if available
if HAS_REVENUE_INTELLIGENCE_API:
    app.register_blueprint(revenue_intelligence_api)
    print("✅ Registered Revenue Intelligence API: /api/revenue-intelligence/*")

# Register Portfolio API (multi-company integration layer)
try:
    from portfolio_api import portfolio_api
    app.register_blueprint(portfolio_api)
    print("✅ Registered Portfolio API: /api/portfolio/*")
except ImportError as e:
    print(f"⚠️  Warning: Portfolio API not available: {e}")

# Register Outcome ROI API (Historical + Forward outcome-focused ROI)
try:
    from outcome_roi_api import outcome_roi_api
    app.register_blueprint(outcome_roi_api)
    print("✅ Registered Outcome ROI API: /api/outcome-roi/*")
except ImportError as e:
    print(f"⚠️  Warning: Outcome ROI API not available: {e}")

# Register Signal Analyst Agent API if available
if HAS_SIGNAL_ANALYST_API:
    app.register_blueprint(signal_analyst_api)
    print("✅ Registered Signal Analyst API: /api/signal-analyst/*")

# Register DC2_S API if available
if HAS_DC2S_API:
    app.register_blueprint(dc2s_api, url_prefix='/api/dc2s')
    print("✅ Registered DC2_S API: /api/dc2s/*")

# Register DC2_S Config API (Phase 1 Migration)
try:
    from dc2s_config_api import dc2s_config_api
    # Blueprint already has url_prefix='/api/dc2s/config', so don't add it again
    app.register_blueprint(dc2s_config_api)
    print("✅ Registered DC2_S Config API: /api/dc2s/config/*")
except ImportError as e:
    print(f"⚠️  Warning: DC2_S Config API not available: {e}")

# Register DC2_S Scores API (Phase 2 Migration)
try:
    from dc2s_scores_api import dc2s_scores_api
    app.register_blueprint(dc2s_scores_api)
    print("✅ Registered DC2_S Scores API: /api/dc2s/scores/*")
except ImportError as e:
    print(f"⚠️  Warning: DC2_S Scores API not available: {e}")

# Dynamic Journey API - Works for ALL customers automatically!
# No hardcoding required - discovers journey files based on account ID
try:
    from journey_api_dynamic import register_dynamic_journey_api
    register_dynamic_journey_api(app)
except ImportError as e:
    print(f"⚠️  Warning: Dynamic Journey API not available: {e}")
    print("   Journey endpoints will not be available")

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


# Rate limiting for expensive POST endpoints
# These limits apply per-IP to prevent abuse of compute-heavy operations
if limiter:
    # Apply rate limits to specific endpoints
    with app.app_context():
        # Expensive compute operations
        limiter.limit("5 per minute")(app.view_functions.get('product_analytics_api.recalculate_product_health', lambda: None))
        limiter.limit("5 per minute")(app.view_functions.get('enhanced_rag_openai_api.enhanced_query', lambda: None))
        limiter.limit("5 per minute")(app.view_functions.get('enhanced_rag_openai_api.build_enhanced_knowledge_base', lambda: None))
        # Upload operations
        limiter.limit("10 per minute")(app.view_functions.get('upload_api.upload_csv', lambda: None))
        limiter.limit("10 per minute")(app.view_functions.get('enhanced_upload_api.upload_enhanced', lambda: None))
        limiter.limit("10 per minute")(app.view_functions.get('secure_file_api.upload_file', lambda: None))
        limiter.limit("10 per minute")(app.view_functions.get('corporate_api.upload_corporate_data', lambda: None))

# Load persisted data on startup
@app.before_request
def initialize_data_once():
    """Load persisted data from database on first request"""
    if not hasattr(app, '_data_initialized'):
        try:
            from playbook_execution_api import load_executions_from_db
            from playbook_reports_api import load_reports_from_db
            load_executions_from_db()
            load_reports_from_db()
            print("✓ Initialized persisted data from DB (executions + reports)")
            app._data_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize persisted data: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
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


@app.route('/api/login', methods=['POST'])
def login():
    """
    User login endpoint with session creation.
    
    SECURITY: Uses Flask-Login to create secure server-side sessions.
    No more X-Customer-ID headers - session handles authentication.
    """
    try:
        # Ensure clean transaction (e.g. if a prior before_request left it aborted)
        try:
            db.session.rollback()
        except Exception:
            pass
        data = request.json or {}
        email = data.get('email') or (data.get('username') if isinstance(data.get('username'), str) else None)
        password = data.get('password') or data.get('passwd')  # accept 'password' or 'passwd'
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
        try:
            customer = db.session.get(Customer, user.customer_id)
        except Exception as customer_error:
            # If customer lookup fails, continue with None (shouldn't happen but handle gracefully)
            print(f"Warning: Could not load customer {user.customer_id}: {customer_error}")
            customer = None
            db.session.rollback()  # Reset transaction
        
        # Map database vertical to frontend vertical
        # Database: 'DC2_S', 'dc2_s', 'dc2-s', 'saas', None
        # Frontend: 'datacenter', 'saas'
        user_vertical = user.vertical if hasattr(user, 'vertical') and user.vertical else None
        
        # Handle case-insensitive mapping: DC2_S, dc2_s, dc2-s -> datacenter
        if user_vertical:
            user_vertical_normalized = user_vertical.lower().replace('-', '_').replace(' ', '_')
            if user_vertical_normalized in ['dc2_s', 'dc2s', 'datacenter']:
                frontend_vertical = 'datacenter'
            elif user_vertical_normalized == 'saas':
                frontend_vertical = 'saas'
            else:
                # Default to datacenter if it looks like a DC vertical variant
                frontend_vertical = 'datacenter' if 'dc' in user_vertical_normalized or 'datacenter' in user_vertical_normalized else 'saas'
        else:
            # If no vertical set, check the selected vertical from request
            selected_vertical = data.get('vertical', 'saas')
            frontend_vertical = 'datacenter' if selected_vertical == 'datacenter' else 'saas'
        
        # Debug logging
        print(f"🔍 Login vertical mapping: DB='{user_vertical}' -> Frontend='{frontend_vertical}'")
        
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
                'customer_name': customer.customer_name if customer else 'Unknown',
                # UUID migration: include UUIDs alongside integer IDs
                'customer_uuid': getattr(customer, 'uuid', None) if customer else None,
                'user_uuid': getattr(user, 'uuid', None),
                'vertical': getattr(customer, 'vertical', None) if customer else None,
            },
            'vertical': frontend_vertical,  # Return mapped vertical
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
        user = db.session.get(User, current_user.user_id)
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
# ========================================
# GLOBAL ERROR HANDLERS
# ========================================
from sqlalchemy.exc import SQLAlchemyError

# Configure logging with centralized config
from logging_config import configure_logging, get_logger
import logging
import os

# Configure logging based on environment
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file = os.getenv('LOG_FILE', 'backend.log')
configure_logging(
    level=getattr(logging, log_level, logging.INFO),
    log_file=log_file if log_file else None,
    console=True,
    file_handler=bool(log_file)
)
logger = get_logger(__name__)

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    db.session.rollback()
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.',
        'status': 500
    }), 500

@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    """Handle database errors"""
    db.session.rollback()
    logger.error(f"Database error: {error}", exc_info=True)
    return jsonify({
        'error': 'Database error',
        'message': 'A database error occurred. Please try again.',
        'status': 500
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
    db.session.rollback()
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please contact support.',
        'status': 500
    }), 500

# Request logging
@app.before_request
def log_request_info():
    """Log incoming requests"""
    if request.path.startswith('/api/'):
        logger.info(f"API Request: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    """Log API responses"""
    if request.path.startswith('/api/'):
        logger.info(f"API Response: {request.method} {request.path} -> {response.status_code}")
    return response
# Register Wizard A Blueprint (last to avoid conflicts)
app.register_blueprint(wizard_bp)
print("✅ Wizard A blueprint registered")

# Register Onboarding API (V2 config-aware only — legacy onboarding_api removed)
if ONBOARDING_API_V2_AVAILABLE:
    app.register_blueprint(onboarding_api_v2, url_prefix='/api/onboarding')
    print("✅ Registered Config-Aware Onboarding API V2: /api/onboarding/*")
else:
    print("⚠️  Onboarding API V2 not available and legacy onboarding_api has been removed")

# Admin API (Wizard B & C endpoints)
try:
    from admin_api import admin_bp
    app.register_blueprint(admin_bp)
    print("✅ Registered Admin API: /api/admin/*")
except ImportError as e:
    print(f"⚠️  Warning: Admin API not available: {e}")

# Action Interface API (Phases 4, 5, 7 — bindings, credentials, callbacks)
try:
    from action_interface_api import action_interface_api
    app.register_blueprint(action_interface_api)
    print("✅ Registered Action Interface API: /api/action-bindings/*, /api/credentials/*, /api/webhooks/*")
except ImportError as e:
    print(f"⚠️  Warning: Action Interface API not available: {e}")

# Roadmap Scenario & Ingest API (Step 6)
try:
    from roadmap_scenario_ingest import roadmap_scenario_api
    app.register_blueprint(roadmap_scenario_api)
    print("✅ Registered Roadmap Scenario API: /api/roadmap/*")
except ImportError as e:
    print(f"⚠️  Warning: Roadmap Scenario API not available: {e}")

# Observability API (Phase 8)
try:
    from observability import observability_api
    app.register_blueprint(observability_api)
    print("✅ Registered Observability API: /api/observability/*")
except ImportError as e:
    print(f"⚠️  Warning: Observability API not available: {e}")

try:
    from agent_memory_api import agent_memory_api
    app.register_blueprint(agent_memory_api)
    print("✅ Registered Agent Memory API: /api/memory/*")
except ImportError as e:
    print(f"⚠️  Warning: Agent Memory API not available: {e}")

# Register Approval Queue API (human-in-the-loop for agent actions)
try:
    from approval_queue import approval_api
    app.register_blueprint(approval_api)
    print("✅ Registered Approval Queue API: /api/approvals/*")
except ImportError as e:
    print(f"⚠️  Warning: Approval Queue API not available: {e}")

# Initialize Agent Tool Registry at startup
try:
    from agent_tool_registry import register_all_tools
    registry = register_all_tools()
    print("✅ Initialized Agent Tool Registry")

    # Bridge MCP tools into the registry
    try:
        from mcp_tool_bridge import MCPToolBridge
        mcp_bridge = MCPToolBridge(registry)
        mcp_bridge.register_mcp_tools()
        print("✅ MCP Tool Bridge initialized (with fallback)")
    except ImportError as e:
        print(f"⚠️  Warning: MCP Tool Bridge not available: {e}")
except ImportError as e:
    print(f"⚠️  Warning: Agent Tool Registry not available: {e}")

# Register Report Generation API
try:
    from report_generation_agent import report_generation_api
    app.register_blueprint(report_generation_api)
    print("✅ Registered Report Generation API: /api/reports/*")
except ImportError as e:
    print(f"⚠️  Warning: Report Generation API not available: {e}")

@app.route('/debug/routes')
def list_routes():
    """Debug endpoint to see all registered routes"""
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        line = urllib.parse.unquote(f"{rule.endpoint:50s} {methods:20s} {rule.rule}")
        output.append(line)
    
    return '<br>'.join(sorted(output))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Option 1: Production-ready - no auto-reload (code changes require manual restart)
    app.run(host='0.0.0.0', port=5059, debug=False)
