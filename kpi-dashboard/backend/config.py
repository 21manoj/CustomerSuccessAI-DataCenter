#!/usr/bin/env python3
"""
Configuration for KPI Dashboard
Handles environment-specific settings and feature toggles
"""

import os
import secrets
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

def _get_secret_key(environment='development'):
    """Get secret key with environment-specific fail-safe"""
    secret_key = os.environ.get('SECRET_KEY')
    
    if secret_key:
        # Validate length
        if len(secret_key) < 32:
            raise ValueError(
                f"SECRET_KEY too short ({len(secret_key)} chars). "
                "Must be at least 32 characters!"
            )
        return secret_key
    
    # DEVELOPMENT: Auto-generate temporary key with warning
    if environment == 'development':
        temp_key = secrets.token_hex(32)
        logger.warning(
            "⚠️  SECRET_KEY not set. Using auto-generated temporary key for development. "
            "Run 'python backend/generate_secret_key.py' to create persistent key."
        )
        print("⚠️  WARNING: Using temporary SECRET_KEY (will change on restart)")
        print("⚠️  Run: python backend/generate_secret_key.py")
        return temp_key
    
    # PRODUCTION: Fail hard
    raise ValueError(
        "❌ CRITICAL: SECRET_KEY not set in production! "
        "Application cannot start without secret key. "
        "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

class Config:
    """Base configuration"""
    
    # Database - REQUIRE PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError(
            "❌ ERROR: DATABASE_URL environment variable is required.\n"
            "Please set DATABASE_URL to a PostgreSQL connection string.\n"
            "Example: postgresql://user:password@localhost:5432/dbname"
        )
    if not database_url.startswith('postgresql://') and not database_url.startswith('postgres://'):
        raise ValueError(
            f"❌ ERROR: DATABASE_URL must be PostgreSQL. Got: {database_url[:50]}...\n"
            "Please set DATABASE_URL to a PostgreSQL connection string."
        )
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security - Secret Key with Fail-Safe
    SECRET_KEY = _get_secret_key(os.environ.get('FLASK_ENV', 'development'))
    
    # Flask-Session Configuration
    SESSION_TYPE = 'sqlalchemy'  # Database-backed sessions
    SESSION_SQLALCHEMY_TABLE = 'sessions'  # Table name
    SESSION_PERMANENT = True  # Enable session timeout
    SESSION_USE_SIGNER = True  # Sign session cookies
    SESSION_KEY_PREFIX = 'cs_session:'  # Namespace for sessions
    
    # Session Cookie Configuration
    SESSION_COOKIE_NAME = 'cs_session'
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access (XSS protection)
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    
    # Session Durations
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # Active session: 8 hours
    REMEMBER_COOKIE_NAME = 'cs_remember'  # Remember me cookie
    REMEMBER_COOKIE_DURATION = timedelta(days=7)  # Remember me: 7 days
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    
    # Idle Timeout
    SESSION_IDLE_TIMEOUT = timedelta(minutes=30)  # 30 minutes idle = logout
    
    # Flask-Login Configuration
    LOGIN_DISABLED = False
    SESSION_PROTECTION = 'strong'  # Detect session hijacking
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    
    # RAG System
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    
    # Feature Toggles (can be overridden by environment variables)
    FEATURE_FORMAT_DETECTION = os.getenv('FEATURE_FORMAT_DETECTION', 'false').lower() == 'true'
    FEATURE_EVENT_DRIVEN_RAG = os.getenv('FEATURE_EVENT_DRIVEN_RAG', 'false').lower() == 'true'
    FEATURE_CONTINUOUS_LEARNING = os.getenv('FEATURE_CONTINUOUS_LEARNING', 'false').lower() == 'true'
    FEATURE_REAL_TIME_INGESTION = os.getenv('FEATURE_REAL_TIME_INGESTION', 'false').lower() == 'true'
    FEATURE_ENHANCED_UPLOAD = os.getenv('FEATURE_ENHANCED_UPLOAD', 'false').lower() == 'true'
    FEATURE_TEMPORAL_ANALYSIS = os.getenv('FEATURE_TEMPORAL_ANALYSIS', 'true').lower() == 'true'
    FEATURE_MULTI_FORMAT_SUPPORT = os.getenv('FEATURE_MULTI_FORMAT_SUPPORT', 'false').lower() == 'true'
    
    # Hot Reload
    ENABLE_HOT_RELOAD = os.getenv('ENABLE_HOT_RELOAD', 'false').lower() == 'true'
    WATCH_DIRECTORY = os.getenv('WATCH_DIRECTORY', os.path.dirname(os.path.abspath(__file__)))
    
    # Performance
    RAG_SIMILARITY_THRESHOLD = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.3'))
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
    MAX_QUERY_LENGTH = int(os.getenv('MAX_QUERY_LENGTH', '1000'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'backend.log')
    
    # Caching
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    
    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8005').split(',')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    REMEMBER_COOKIE_SECURE = False
    
    # Enable all features in development
    FEATURE_FORMAT_DETECTION = True
    FEATURE_EVENT_DRIVEN_RAG = True
    FEATURE_CONTINUOUS_LEARNING = True
    FEATURE_REAL_TIME_INGESTION = True
    FEATURE_ENHANCED_UPLOAD = True
    FEATURE_TEMPORAL_ANALYSIS = True
    FEATURE_MULTI_FORMAT_SUPPORT = True
    ENABLE_HOT_RELOAD = True

class ProductionConfig(Config):
    """Production configuration with strict security"""
    DEBUG = False
    TESTING = False
    
    # Validate SECRET_KEY at runtime (not at class definition)
    @staticmethod
    def validate_secret_key():
        """Validate SECRET_KEY when ProductionConfig is actually used"""
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError(
                "❌ CRITICAL: SECRET_KEY not set in production! "
                "Set SECRET_KEY environment variable before starting."
            )
        if len(secret_key) < 32:
            raise ValueError(f"SECRET_KEY too short ({len(secret_key)} chars). Minimum 32 required!")
        return secret_key
    
    # Security settings (HTTPS required)
    SESSION_COOKIE_SECURE = True  # HTTPS only
    REMEMBER_COOKIE_SECURE = True  # HTTPS only
    SESSION_PROTECTION = 'strong'  # Maximum protection
    
    # Performance settings
    RAG_SIMILARITY_THRESHOLD = 0.4  # Higher threshold for production
    RAG_TOP_K = 10  # More results in production
    
    # Logging
    LOG_LEVEL = 'WARNING'
    
    # Disable hot reload in production
    ENABLE_HOT_RELOAD = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable features for testing
    FEATURE_FORMAT_DETECTION = False
    FEATURE_EVENT_DRIVEN_RAG = False
    FEATURE_CONTINUOUS_LEARNING = False
    FEATURE_REAL_TIME_INGESTION = False
    FEATURE_ENHANCED_UPLOAD = False
    ENABLE_HOT_RELOAD = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, config['default'])

# Environment variable documentation
ENVIRONMENT_VARIABLES = {
    'DATABASE_URL': 'Database connection string',
    'SECRET_KEY': 'Flask secret key for sessions',
    'OPENAI_API_KEY': 'OpenAI API key for RAG system',
    'QDRANT_URL': 'Qdrant vector database URL',
    'QDRANT_API_KEY': 'Qdrant API key',
    'FLASK_ENV': 'Flask environment (development/production/testing)',
    'FEATURE_FORMAT_DETECTION': 'Enable format detection (true/false)',
    'FEATURE_EVENT_DRIVEN_RAG': 'Enable event-driven RAG (true/false)',
    'FEATURE_CONTINUOUS_LEARNING': 'Enable continuous learning (true/false)',
    'FEATURE_REAL_TIME_INGESTION': 'Enable real-time ingestion (true/false)',
    'FEATURE_ENHANCED_UPLOAD': 'Enable enhanced upload (true/false)',
    'FEATURE_TEMPORAL_ANALYSIS': 'Enable temporal analysis (true/false)',
    'FEATURE_MULTI_FORMAT_SUPPORT': 'Enable multi-format support (true/false)',
    'ENABLE_HOT_RELOAD': 'Enable hot reload system (true/false)',
    'WATCH_DIRECTORY': 'Directory to watch for hot reload',
    'RAG_SIMILARITY_THRESHOLD': 'RAG similarity threshold (0.0-1.0)',
    'RAG_TOP_K': 'Number of top results to return',
    'MAX_QUERY_LENGTH': 'Maximum query length',
    'LOG_LEVEL': 'Logging level (DEBUG/INFO/WARNING/ERROR)',
    'LOG_FILE': 'Log file path',
    'CACHE_TYPE': 'Cache type (simple/redis/memcached)',
    'CACHE_DEFAULT_TIMEOUT': 'Cache timeout in seconds',
    'RATELIMIT_ENABLED': 'Enable rate limiting (true/false)',
    'RATELIMIT_STORAGE_URL': 'Rate limiting storage URL',
    'CORS_ORIGINS': 'CORS allowed origins (comma-separated)',
    'SESSION_COOKIE_SECURE': 'Secure session cookies (true/false)'
}

if __name__ == "__main__":
    print("⚙️ KPI Dashboard Configuration")
    print("=" * 50)
    
    # Show current configuration
    current_config = get_config()
    print(f"Environment: {os.getenv('FLASK_ENV', 'default')}")
    print(f"Debug: {current_config.DEBUG}")
    print(f"Database: {current_config.SQLALCHEMY_DATABASE_URI}")
    
    print("\n🔧 Feature Toggles:")
    features = [
        'FEATURE_FORMAT_DETECTION',
        'FEATURE_EVENT_DRIVEN_RAG', 
        'FEATURE_CONTINUOUS_LEARNING',
        'FEATURE_REAL_TIME_INGESTION',
        'FEATURE_ENHANCED_UPLOAD',
        'FEATURE_TEMPORAL_ANALYSIS',
        'FEATURE_MULTI_FORMAT_SUPPORT'
    ]
    
    for feature in features:
        value = getattr(current_config, feature, False)
        status_icon = "✅" if value else "❌"
        print(f"{status_icon} {feature}: {value}")
    
    print(f"\n🔥 Hot Reload: {'Enabled' if current_config.ENABLE_HOT_RELOAD else 'Disabled'}")
    
    print("\n📋 Environment Variables:")
    for var, description in ENVIRONMENT_VARIABLES.items():
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value} - {description}")
