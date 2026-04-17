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

# DEBUG: from env; default true in development, false in production
_default_debug = 'true' if os.getenv('FLASK_ENV') != 'production' else 'false'
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', _default_debug).lower() == 'true'

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
# Origins from env var (comma-separated) or fallback to common dev ports
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001,http://localhost:8005,http://127.0.0.1:3000,http://127.0.0.1:8005').split(',')
CORS(app, supports_credentials=True, origins=app.config.get('CORS_ORIGINS', _cors_origins))

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

# Ensure sessions table (and all app tables) exist before initializing Flask-Session
with app.app_context():
    from models import JourneyData  # ensure journey_data table is created by create_all
    db.create_all()  # This will create the sessions table if it doesn't exist

    # Idempotent migration: add customer_id to qualitative_signals (fixes PK collision)
    try:
        from migrations.add_customer_id_to_qualitative_signals import run_migration as _run_signal_migration
        _run_signal_migration(db.session)
    except Exception as _e:
        print(f"   ⚠️  qualitative_signals migration skipped: {_e}")

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

# Security headers on all responses
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Don't add HSTS in dev (breaks localhost)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
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
from models import Customer, User, Account, KPIUpload, KPI, CustomerConfig, HealthScore

# Register only essential APIs (legacy upload_api may be absent; V2/V3 used when available)
try:
    from upload_api import upload_api as upload_api_legacy
    HAS_LEGACY_UPLOAD_API = True
except ImportError:
    upload_api_legacy = None
    HAS_LEGACY_UPLOAD_API = False
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
from customer_playbook_api import customer_playbook_api
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
from backup_restore_api import backup_restore_api
from rehydration_api import rehydration_api
from async_jobs_api import async_jobs_bp
from data_quality_api import data_quality_api
from customer_profile_api import customer_profile_api
from enhanced_upload_api import enhanced_upload_api
try:
    from enhanced_rag_openai_api import enhanced_rag_openai_api
    HAS_ENHANCED_RAG_OPENAI_API = True
except ImportError as e:
    enhanced_rag_openai_api = None
    HAS_ENHANCED_RAG_OPENAI_API = False
    print(f"⚠️  enhanced_rag_openai_api not available (e.g. faiss missing): {e}")
from secure_file_api import secure_file_api
from master_file_api import master_file_api
from account_snapshot_api import account_snapshot_api
from admin_cleanup_api import admin_cleanup_api
try:
    from wizard_blueprint import wizard_bp
    HAS_WIZARD_BP = True
except ImportError as e:
    wizard_bp = None
    HAS_WIZARD_BP = False
    print(f"⚠️  wizard_blueprint not available (e.g. celery missing): {e}")
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
elif HAS_LEGACY_UPLOAD_API:
    app.register_blueprint(upload_api_legacy)
    print("⚠️  Registered Upload API (legacy) - V3 and V2 not available")
else:
    print("⚠️  No upload API module found (V3/V2/legacy); upload routes may be missing")
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
app.register_blueprint(customer_playbook_api)
app.register_blueprint(playbook_reports_api)
app.register_blueprint(playbook_recommendations_api)
app.register_blueprint(feature_toggle_api)
app.register_blueprint(registration_api)
app.register_blueprint(kpi_reference_ranges_api)
app.register_blueprint(direct_rag_api)
app.register_blueprint(customer_perf_summary_api)
app.register_blueprint(workflow_config_api)
app.register_blueprint(export_api)
app.register_blueprint(backup_restore_api)
app.register_blueprint(rehydration_api)
app.register_blueprint(async_jobs_bp)
app.register_blueprint(account_snapshot_api)
app.register_blueprint(admin_cleanup_api)

# Data Ingestion API — Ring 1 generic endpoints for n8n / external integrations
try:
    from data_ingestion_api import data_ingestion_api
    app.register_blueprint(data_ingestion_api)
    print("✅ Registered Data Ingestion API: /api/data-ingestion/*")
    print("   - POST /api/data-ingestion/kpis (source-agnostic KPI ingest)")
    print("   - POST /api/data-ingestion/signals (qualitative signals)")
    print("   - POST /api/data-ingestion/contacts (champion/contact updates)")
except ImportError as e:
    print(f"⚠️  data_ingestion_api not available: {e}")

# Test Runner API — NOW runs as a separate server on port 5099
# See backend/test_runner_server.py (own auth, own session, own credentials)
# Proxy: setupProxy.js routes /api/test-runner/* → port 5099
# Removed from main app to enforce complete isolation.

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
if HAS_ENHANCED_RAG_OPENAI_API:
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

# Register Executive Dashboard API (CRO + CFO aggregated views)
try:
    from executive_dashboard_api import executive_dashboard_api
    app.register_blueprint(executive_dashboard_api)
    print("✅ Registered Executive Dashboard API: /api/executive/*")
except ImportError as e:
    print(f"⚠️  Warning: Executive Dashboard API not available: {e}")

# Register Context Graph API (graph traversal + revenue intelligence)
try:
    from context_graph_api import context_graph_api
    app.register_blueprint(context_graph_api)
    print("✅ Registered Context Graph API: /api/context-graph/*")
except ImportError as e:
    print(f"⚠️  Warning: Context Graph API not available: {e}")


# Register Story Arc API (story arc manifests for revenue intelligence)
try:
    from story_arc_api import story_arc_api
    app.register_blueprint(story_arc_api)
    print("✅ Registered Story Arc API: /api/story-arcs/*")
except ImportError as e:
    print(f"⚠️  Warning: Story Arc API not available: {e}")

# Register Notifications API (Actions Pipeline Push)
try:
    from notifications_api import notifications_api
    app.register_blueprint(notifications_api)
    print("✅ Registered Notifications API: /api/notifications/*")
except ImportError as e:
    print(f"⚠️  Warning: Notifications API not available: {e}")

# Register Signal Analyst Agent API if available
if HAS_SIGNAL_ANALYST_API:
    app.register_blueprint(signal_analyst_api)
    print("✅ Registered Signal Analyst API: /api/signal-analyst/*")

# Register DC2_S API if available
if HAS_DC2S_API:
    app.register_blueprint(dc2s_api, url_prefix='/api/dc2s')
    print("✅ Registered DC2_S API: /api/dc2s/*")

# Register Vertical-Agnostic API v1 (proxies to DC2S handlers with vertical context)
try:
    from api_v1_routes import api_v1
    app.register_blueprint(api_v1)
    print("✅ Registered API v1 (vertical-agnostic): /api/v1/*")
except Exception as e:
    print(f"⚠️  API v1 not available: {e}")

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
        if HAS_ENHANCED_RAG_OPENAI_API:
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
    """Load persisted data from database on first request.

    NOTE: Playbook executions are now DB-first (PlaybookExecutionV2) — no in-memory cache.
    Only reports still use in-memory loading.
    """
    if not hasattr(app, '_data_initialized'):
        try:
            from playbook_reports_api import load_reports_from_db
            load_reports_from_db()
            print("✓ Initialized persisted data from DB (reports)")
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

_SERVER_STARTED_AT = datetime.datetime.now(datetime.timezone.utc)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint — includes server_started_at for stale process detection."""
    uptime = (datetime.datetime.now(datetime.timezone.utc) - _SERVER_STARTED_AT).total_seconds()
    return jsonify({
        'status': 'healthy',
        'version': 'V5',
        'timestamp': datetime.datetime.now().isoformat(),
        'server_started_at': _SERVER_STARTED_AT.isoformat(),
        'uptime_seconds': int(uptime),
        'cwd': os.getcwd(),
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
                'message': 'Account is inactive. Contact your administrator.'
            }), 403

        # Check if user access has expired (contractors/testers with time-limited access)
        if hasattr(user, 'expires_at') and user.expires_at is not None:
            import datetime as dt_mod
            if dt_mod.datetime.utcnow() > user.expires_at:
                return jsonify({
                    'status': 'error',
                    'message': 'Your access has expired. Contact your administrator to renew.'
                }), 403
        
        # Get customer info
        try:
            customer = db.session.get(Customer, user.customer_id)
        except Exception as customer_error:
            # If customer lookup fails, continue with None (shouldn't happen but handle gracefully)
            print(f"Warning: Could not load customer {user.customer_id}: {customer_error}")
            customer = None
            db.session.rollback()  # Reset transaction
        
        # Resolve vertical from DB — data-driven, no hardcoded whitelist.
        # Returns raw vertical (e.g. 'dc2_s', 'saas_premium', 'msp') + dashboard_family ('datacenter' or 'saas')
        # for frontend routing. New verticals work without code changes.
        DC_VERTICALS = {'dc2_s', 'dc2s', 'dc', 'datacenter'}
        user_vertical = user.vertical if hasattr(user, 'vertical') and user.vertical else None

        if user_vertical:
            user_vertical_normalized = user_vertical.lower().replace('-', '_').replace(' ', '_')
        else:
            user_vertical_normalized = 'saas_premium'  # default for new users

        frontend_vertical = user_vertical_normalized
        dashboard_family = 'datacenter' if user_vertical_normalized in DC_VERTICALS else 'saas'

        # Debug logging
        print(f"🔍 Login vertical: DB='{user_vertical}' -> vertical='{frontend_vertical}', family='{dashboard_family}'")
        
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

        # Resolve tier + entitlements for the customer
        try:
            from entitlements import get_customer_tier, get_customer_entitlements
            customer_tier = get_customer_tier(user.customer_id)
            customer_entitlements = get_customer_entitlements(user.customer_id)
        except Exception as tier_err:
            print(f"Warning: Could not resolve tier/entitlements: {tier_err}")
            customer_tier = 'enterprise'  # default
            customer_entitlements = {}

        # Detect onboarding state: fresh / data_uploaded / active
        # 'fresh' = 0 accounts; 'data_uploaded' = has accounts but no health scores;
        # 'active' = has accounts with real health scores in health_scores table
        onboarding_state = 'fresh'
        try:
            account_count = Account.query.filter_by(customer_id=user.customer_id).count()
            if account_count > 0:
                # Check if any health score record exists for this customer's accounts
                has_real_scores = db.session.query(HealthScore).join(
                    Account, HealthScore.account_id == Account.account_id
                ).filter(
                    Account.customer_id == user.customer_id,
                    HealthScore.health_score.isnot(None)
                ).first() is not None
                onboarding_state = 'active' if has_real_scores else 'data_uploaded'
        except Exception as ob_err:
            print(f"Warning: Could not detect onboarding state: {ob_err}")

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
                'role': getattr(user, 'role', None),
                'tier': customer_tier,
                'entitlements': customer_entitlements,
                'onboarding_state': onboarding_state,
                # RBAC fields for contractors/testers
                'allowed_account_ids': getattr(user, 'allowed_account_ids', None),
                'allowed_customer_ids': getattr(user, 'allowed_customer_ids', None),
                'is_contractor': getattr(user, 'is_contractor', False),
                'expires_at': user.expires_at.isoformat() if hasattr(user, 'expires_at') and user.expires_at else None,
            },
            'vertical': frontend_vertical,  # Raw vertical from DB (e.g. 'saas_premium', 'dc2_s')
            'dashboard_family': dashboard_family,  # Routing hint: 'datacenter' or 'saas'
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

# ============================================================
# MAGIC LINK (Passwordless Login)
# ============================================================

@app.route('/api/auth/magic-link', methods=['POST'])
def request_magic_link():
    """Request a magic link for passwordless login.

    Generates a one-time token, stores SHA-256 hash in DB,
    and logs the magic link URL to console (dev mode).
    Always returns success to prevent email enumeration.
    """
    import secrets
    import hashlib

    data = request.get_json(force=True)
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    # Always return success (don't leak whether email exists)
    success_response = jsonify({
        'status': 'success',
        'message': 'If an account exists for this email, a magic link has been sent.'
    })

    user = User.query.filter_by(email=email).first()
    if not user:
        return success_response, 200

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Store hash + expiry (15 minutes)
    user.magic_link_token = token_hash
    user.magic_link_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    db.session.commit()

    # Build magic link URL
    host = request.host_url.rstrip('/')
    magic_url = f"{host}/auth/verify?token={raw_token}"

    # Dev mode: log to console (replace with SendGrid/SES in production)
    print(f"\n{'='*60}")
    print(f"  MAGIC LINK for {email}")
    print(f"  {magic_url}")
    print(f"  Expires: {user.magic_link_expires_at.isoformat()}")
    print(f"{'='*60}\n")

    return success_response, 200


@app.route('/api/auth/verify-magic-link', methods=['GET'])
def verify_magic_link():
    """Verify a magic link token and create a session.

    Called when user clicks the magic link. Validates token,
    creates Flask session, returns user data (same as /api/login).
    """
    import hashlib
    from flask_login import login_user

    raw_token = request.args.get('token', '').strip()
    if not raw_token:
        return jsonify({'status': 'error', 'message': 'Token is required'}), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    user = User.query.filter_by(magic_link_token=token_hash).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Invalid or expired magic link'}), 401

    # Check expiry
    if user.magic_link_expires_at and user.magic_link_expires_at < datetime.datetime.utcnow():
        # Clear expired token
        user.magic_link_token = None
        user.magic_link_expires_at = None
        db.session.commit()
        return jsonify({'status': 'error', 'message': 'Magic link has expired. Request a new one.'}), 401

    # Clear token (single-use)
    user.magic_link_token = None
    user.magic_link_expires_at = None
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()

    # Create Flask session (same as password login)
    login_user(user)
    session['user_id'] = user.user_id
    session['customer_id'] = user.customer_id
    session['email'] = user.email

    # Resolve vertical + dashboard routing
    customer = db.session.get(Customer, user.customer_id)
    vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
    dashboard_family = 'saas' if 'saas' in vertical.lower() else 'datacenter'

    return jsonify({
        'status': 'success',
        'message': 'Magic link verified. You are now logged in.',
        'user': {
            'user_id': user.user_id,
            'email': user.email,
            'user_name': user.user_name,
            'customer_id': user.customer_id,
            'customer_name': customer.customer_name if customer else 'Unknown',
            'customer_uuid': getattr(customer, 'uuid', None) if customer else None,
            'vertical': vertical,
            'role': getattr(user, 'role', None),
        },
        'vertical': vertical,
        'dashboard_family': dashboard_family,
    })


# ============================================================
# SELF-SERVICE API KEY MANAGEMENT
# ============================================================
# Customer-facing endpoints (session auth, not super_admin).
# Reuses api_key_service functions — same logic as admin endpoints
# but scoped to the logged-in user's customer_id.

@app.route('/api/settings/api-keys', methods=['GET'])
def list_my_api_keys():
    """List API keys for the logged-in user's customer."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    cid = current_user.customer_id
    try:
        from models import CustomerApiKey
        keys = CustomerApiKey.query.filter_by(customer_id=cid).order_by(CustomerApiKey.created_at.desc()).all()
        return jsonify({
            'api_keys': [
                {
                    'id': k.id,
                    'key_prefix': k.key_prefix,
                    'name': k.name,
                    'scopes': k.scopes or [],
                    'is_active': k.is_active,
                    'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
                    'created_at': k.created_at.isoformat() if k.created_at else None,
                    'expires_at': k.expires_at.isoformat() if k.expires_at else None,
                }
                for k in keys
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/api-keys', methods=['POST'])
def create_my_api_key():
    """Create a new API key for the logged-in user's customer.

    Body: { "name": "My Integration Key", "scopes": ["read", "write"] }
    Returns the full key ONCE — it cannot be retrieved again.
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    cid = current_user.customer_id
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    scopes = data.get('scopes', ['read', 'write'])

    if not name:
        return jsonify({'error': 'Key name is required'}), 400

    try:
        from api_key_service import generate_api_key
        full_key, key_record = generate_api_key(
            customer_id=cid,
            created_by=current_user.user_id,
            name=name,
            scopes=scopes,
        )
        return jsonify({
            'api_key': full_key,
            'api_key_note': 'Save this key — it is shown only once.',
            'key_info': {
                'id': key_record.id,
                'key_prefix': key_record.key_prefix,
                'name': key_record.name,
                'scopes': key_record.scopes or [],
                'created_at': key_record.created_at.isoformat() if key_record.created_at else None,
            },
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/api-keys/<int:key_id>/revoke', methods=['POST'])
def revoke_my_api_key(key_id):
    """Revoke an API key (soft-delete). Only keys owned by the logged-in customer."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    cid = current_user.customer_id
    try:
        from models import CustomerApiKey
        key = CustomerApiKey.query.filter_by(id=key_id, customer_id=cid).first()
        if not key:
            return jsonify({'error': 'Key not found'}), 404
        key.is_active = False
        db.session.commit()
        return jsonify({'status': 'revoked', 'key_id': key_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/status', methods=['GET'])
def session_status():
    """Check if user is authenticated — includes UUIDs for external identification"""
    if current_user.is_authenticated:
        from models import User, Customer
        user = db.session.get(User, current_user.user_id)
        customer = db.session.get(Customer, current_user.customer_id) if current_user.customer_id else None
        return jsonify({
            'authenticated': True,
            'user': {
                'user_id': current_user.user_id,
                'email': current_user.email,
                'customer_id': current_user.customer_id,
                # UUID fields
                'customer_uuid': getattr(customer, 'uuid', None) if customer else None,
                'user_uuid': getattr(user, 'uuid', None) if user else None,
                'vertical': getattr(customer, 'vertical', None) if customer else None,
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
    Includes UUIDs for external identification.
    """
    if current_user.is_authenticated:
        from models import User, Customer
        user = db.session.get(User, current_user.user_id)
        customer = db.session.get(Customer, current_user.customer_id) if current_user.customer_id else None
        return jsonify({
            'authenticated': True,
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'user_name': user.user_name,
                'customer_id': user.customer_id,
                # UUID fields
                'customer_uuid': getattr(customer, 'uuid', None) if customer else None,
                'user_uuid': getattr(user, 'uuid', None) if user else None,
                'vertical': getattr(customer, 'vertical', None) if customer else None,
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
# UUID BACKFILL ADMIN ENDPOINT
# ========================================
@app.route('/api/admin/uuid-backfill', methods=['POST'])
def trigger_uuid_backfill():
    """
    Admin endpoint to backfill UUIDs for all existing records.
    Idempotent — safe to run multiple times.
    """
    try:
        from uuid_backfill import backfill_uuids
        stats = backfill_uuids()
        return jsonify({
            'status': 'success',
            'message': 'UUID backfill complete',
            'stats': stats
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': f'UUID backfill failed: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

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

# Request logging: every API request/response to application log (method, path, status; user when available)
@app.before_request
def log_request_info():
    """Log incoming API requests (method, path)."""
    if request.path.startswith('/api/'):
        logger.info(f"API Request: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    """Log API responses (method, path, status) and user when authenticated."""
    if request.path.startswith('/api/'):
        user_part = ""
        try:
            is_auth = current_user.is_authenticated() if callable(getattr(current_user, "is_authenticated", None)) else bool(getattr(current_user, "is_authenticated", False))
            if is_auth:
                user_part = f" user={getattr(current_user, 'email', None) or getattr(current_user, 'user_id', '')}"
        except Exception:
            pass
        logger.info(f"API Response: {request.method} {request.path} -> {response.status_code}{user_part}")
    return response
# Register Wizard A Blueprint (last to avoid conflicts)
if HAS_WIZARD_BP:
    app.register_blueprint(wizard_bp)
    print("✅ Wizard A blueprint registered")
else:
    print("⚠️  Wizard A blueprint skipped (celery/wizard_tasks not available)")

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

# Admin UI API (Super Admin Console) + Contractor Access API (api-keys, contractors, activity-log)
try:
    from admin_ui_api import admin_ui_api
    app.register_blueprint(admin_ui_api)
    print("✅ Registered Admin UI API: /api/admin-ui/* (Super Admin Console)")
except (ImportError, Exception) as e:
    print(f"⚠️  Admin UI API not fully available ({e})")

try:
    from contractor_access_api import contractor_access_bp
    app.register_blueprint(contractor_access_bp)
    print("✅ Registered Contractor Access API: /api/admin-ui/ (api-keys, contractors, activity-log)")
except (ImportError, Exception) as e:
    print(f"⚠️  Contractor Access API not available ({e})")

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

# Register Onboarding Agent API (AI-powered activation for new customers)
try:
    from agents.onboarding_agent_api import onboarding_agent_api
    app.register_blueprint(onboarding_agent_api)
    print("✅ Registered Onboarding Agent API: /api/onboarding-agent/*")
except ImportError as e:
    print(f"⚠️  Warning: Onboarding Agent API not available: {e}")

# Register Entitlement API (tier-based feature gating)
try:
    from entitlements import entitlement_api
    app.register_blueprint(entitlement_api)
    print("✅ Registered Entitlement API: /api/entitlements/*")
except ImportError as e:
    print(f"⚠️  Warning: Entitlement API not available: {e}")

# Journey Intelligence API (3-line health graph: KPI-only, KPI-decayed, Signal-DNA)
try:
    from journey_intelligence_api import journey_intelligence_api
    app.register_blueprint(journey_intelligence_api)
    print("✅ Registered Journey Intelligence API: /api/journey-intelligence/*")
except ImportError as e:
    print(f"⚠️  Warning: Journey Intelligence API not available: {e}")

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

# ====================================================================
# Integration Framework API (SFDC, HubSpot, Zendesk, n8n)
# ====================================================================
try:
    from integration_api import integration_api
    from playbook_webhook_engine import playbook_webhook_api
    app.register_blueprint(integration_api)
    app.register_blueprint(playbook_webhook_api)
    print("✅ Registered Integration API: /api/integrations/*")
except ImportError as e:
    print(f"⚠️  Warning: Integration API not available: {e}")

# ====================================================================
# QSIM Signal Engine API (feature-toggled)
# ====================================================================
try:
    import os as _os
    _signal_engine_enabled = _os.environ.get('FEATURE_SIGNAL_ENGINE', 'false').lower() in ('true', '1', 'yes')
    if _signal_engine_enabled:
        from signal_engine.ingest_api import signal_api
        app.register_blueprint(signal_api)
        print("✅ Registered Signal Engine API: /api/signals/* (FEATURE_SIGNAL_ENGINE=true)")

        from signal_engine.email_receiver import email_receiver_api
        app.register_blueprint(email_receiver_api)
        print("   ✅ Registered Email Receiver: /api/signals/ingest/email/parse")

        from signal_engine.slack_events import slack_events_api
        app.register_blueprint(slack_events_api)
        print("   ✅ Registered Slack Events: /api/signals/ingest/slack/events")

        # Run idempotent schema migration for enrichment columns
        try:
            from signal_engine.models import ensure_enrichment_columns, ensure_alert_records_table
            with app.app_context():
                ensure_enrichment_columns(db.engine)
                ensure_alert_records_table(db.engine)
            print("   Signal Engine DB schema ensured")
        except Exception as _e:
            print(f"   ⚠️  Signal Engine DB migration skipped: {_e}")

        # Start background enrichment worker
        try:
            from signal_engine.worker import SignalEnrichmentWorker
            _enrichment_worker = SignalEnrichmentWorker()
            _enrichment_worker.start()
            print("   ✅ Signal Enrichment Worker started (background daemon)")
        except Exception as _e:
            print(f"   ⚠️  Signal Enrichment Worker failed to start: {_e}")
    else:
        print("ℹ️  Signal Engine disabled (FEATURE_SIGNAL_ENGINE=false)")
        # Purge any orphaned QSIM data when toggle is OFF
        try:
            from signal_engine.cleanup import purge_all_qsim_signals
            with app.app_context():
                purged = purge_all_qsim_signals()
                if purged > 0:
                    print(f"   Cleaned up {purged} orphaned QSIM signals")
        except Exception:
            pass  # Cleanup is best-effort
except ImportError as e:
    print(f"⚠️  Warning: Signal Engine not available: {e}")

# ====================================================================
# SaaS Premium Vertical API
# ====================================================================
try:
    from verticals.saas_premium.api_routes import saas_premium_api
    app.register_blueprint(saas_premium_api, url_prefix='/api/saas')
    print("✅ Registered SaaS Premium API: /api/saas/*")
except ImportError as e:
    print(f"⚠️  Warning: SaaS Premium API not available: {e}")

# ====================================================================
# Admin UI API (Super-Admin only) — already registered above (line ~1017)
# ====================================================================

# LLM Usage API — budget controller & usage summary
try:
    from llm_usage_api import llm_usage_api
    app.register_blueprint(llm_usage_api)
    print("✅ Registered LLM Usage API: /api/llm-usage/*")
except ImportError as e:
    print(f"⚠️  Warning: LLM Usage API not available: {e}")

# Ask AI v2 — Claude-powered assistant with tool_use (behind feature flag)
try:
    from feature_toggles import feature_toggles, FeatureToggle
    if feature_toggles.is_enabled(FeatureToggle.ASK_AI_V2):
        from ask_ai_endpoint import ask_ai_v2_api
        app.register_blueprint(ask_ai_v2_api)
        print("✅ Ask AI v2 enabled: /api/executive/ask-v2 (FEATURE_ASK_AI_V2=true)")
    else:
        print("ℹ️  Ask AI v2 disabled (set FEATURE_ASK_AI_V2=true to enable)")
except Exception as _e:
    print(f"⚠️  Ask AI v2 init error: {_e}")

# MCP Server status (inbound — external LLMs call into CS Pulse)
try:
    from feature_toggles import feature_toggles, FeatureToggle
    if feature_toggles.is_enabled(FeatureToggle.MCP_SERVER):
        print("✅ MCP Server enabled — external LLMs can connect via stdio or HTTP")
        print("   Run: python backend/mcp_server/cs_pulse_mcp_server.py")
    else:
        print("ℹ️  MCP Server disabled (set FEATURE_MCP_SERVER=true to enable)")
except Exception:
    pass

# ====================================================================
# Startup Validation: Ensure REQUIRED blueprints are registered
# ====================================================================
# These blueprints are essential for platform operation. If any failed
# to import silently, crash now with a clear message rather than
# serving requests with missing functionality.
_REQUIRED_BLUEPRINTS = {
    'onboarding_api_v2': ONBOARDING_API_V2_AVAILABLE,
    'dc2s_api': HAS_DC2S_API,
    'revenue_intelligence_api': HAS_REVENUE_INTELLIGENCE_API,
}
# At least one upload API must be available
_REQUIRED_BLUEPRINTS['upload_api (V2 or V3)'] = (
    UPLOAD_API_V2_AVAILABLE or UPLOAD_API_V3_AVAILABLE
)
# Inline-registered REQUIRED blueprints: check they exist in the app's blueprint registry
for _bp_name in [
    'data_ingestion_api', 'outcome_roi_api', 'executive_dashboard_api',
    'context_graph_api', 'notifications_api',
]:
    _REQUIRED_BLUEPRINTS[_bp_name] = _bp_name in app.blueprints

_missing = [name for name, avail in _REQUIRED_BLUEPRINTS.items() if not avail]
if _missing:
    print("\n" + "=" * 60)
    print("FATAL: Required blueprints failed to load:")
    for m in _missing:
        print(f"  ✗ {m}")
    print("=" * 60)
    raise RuntimeError(
        f"Cannot start: missing required blueprints: {', '.join(_missing)}. "
        f"Check import errors above."
    )
print(f"✅ All {len(_REQUIRED_BLUEPRINTS)} required blueprints verified")


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
    import os, argparse
    _cwd = os.getcwd()
    _verticals_dir = os.path.join(_cwd, 'verticals')
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '5059')))
    args, _ = parser.parse_known_args()

    print(f"\n{'='*60}")
    print(f"  CS Pulse Backend Server")
    print(f"  CWD:       {_cwd}")
    print(f"  Verticals: {_verticals_dir}")
    print(f"  Port:      {args.port}")
    print(f"  DB:        {os.getenv('DATABASE_URL', 'NOT SET')[:60]}...")
    print(f"  CG toggle: {os.getenv('FEATURE_CONTEXT_GRAPH', 'false')}")
    print(f"{'='*60}\n")

    # Sanity check: warn if verticals dir doesn't exist
    if not os.path.isdir(_verticals_dir):
        print(f"⚠️  WARNING: verticals directory not found at {_verticals_dir}")
        print(f"   Server may not find customer data. Check your CWD.")

    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=args.port, debug=False)
