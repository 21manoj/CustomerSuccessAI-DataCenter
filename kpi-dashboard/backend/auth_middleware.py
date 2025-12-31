#!/usr/bin/env python3
"""
Global Authentication Middleware
Applies authentication to all API endpoints except whitelisted public ones
"""

from flask import request, jsonify
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    '/api/login',
    '/api/register',
    '/api/health',
    '/api/forgot-password',
    '/api/reset-password',
]

# Public path prefixes (for static files)
PUBLIC_PREFIXES = [
    '/static/',
    '/favicon.ico',
    '/robots.txt',
    '/manifest.json',
]

def init_auth_middleware(app):
    """
    Initialize global authentication middleware.
    
    This function registers a before_request handler that checks authentication
    for all API endpoints except whitelisted public ones.
    
    SECURITY: This replaces the need to add @login_required to every endpoint.
    """
    
    @app.before_request
    def check_authentication():
        """
        Global authentication check for all API endpoints.
        
        Runs before every request to validate user is authenticated.
        Public endpoints are whitelisted and skip this check.
        """
        
        # Skip authentication for public endpoints
        for public_path in PUBLIC_ENDPOINTS:
            if request.path == public_path or request.path.startswith(public_path + '/'):
                return None  # Allow request to proceed
        
        # Skip for public prefixes (static files, etc.)
        for prefix in PUBLIC_PREFIXES:
            if request.path.startswith(prefix):
                return None
        
        # Check if this is an API endpoint
        if request.path.startswith('/api/'):
            # Require authentication for all API endpoints
            if not current_user.is_authenticated:
                logger.warning(f"Unauthorized API access attempt: {request.path} from {request.remote_addr}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please log in to access this resource',
                    'status': 'unauthorized',
                    'login_url': '/api/login'
                }), 401
            
            # Check if user account is active
            if not current_user.is_active():
                logger.warning(f"Inactive user {current_user.email} attempted to access {request.path}")
                return jsonify({
                    'error': 'Account inactive',
                    'message': 'Your account has been deactivated. Please contact support.',
                    'status': 'forbidden'
                }), 403
            
            # Update last activity for idle timeout tracking
            from flask import session
            from datetime import datetime
            session['last_activity'] = datetime.utcnow().isoformat()
            session.modified = True
        
        # Allow request to proceed
        return None
    
    @app.before_request
    def check_idle_timeout():
        """
        Check if user has been idle too long and log them out.
        
        Idle timeout: 30 minutes of inactivity
        """
        if not current_user.is_authenticated:
            return None
        
        from flask import session
        from datetime import datetime, timedelta
        
        last_activity_str = session.get('last_activity')
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                idle_duration = datetime.utcnow() - last_activity
                
                # Check if idle for more than 30 minutes
                idle_timeout = app.config.get('SESSION_IDLE_TIMEOUT', timedelta(minutes=30))
                if idle_duration > idle_timeout:
                    from flask_login import logout_user
                    logger.info(f"User {current_user.email} logged out due to inactivity ({idle_duration.seconds // 60} minutes)")
                    logout_user()
                    session.clear()
                    
                    return jsonify({
                        'error': 'Session expired',
                        'message': 'Your session expired due to inactivity. Please log in again.',
                        'reason': 'idle_timeout'
                    }), 401
            except Exception as e:
                logger.error(f"Error checking idle timeout: {e}")
        
        return None
    
    logger.info("✅ Authentication middleware initialized")
    logger.info(f"   Public endpoints: {PUBLIC_ENDPOINTS}")
    logger.info(f"   All other /api/* endpoints require authentication")


def is_public_endpoint(path):
    """Check if a path is a public endpoint"""
    for public_path in PUBLIC_ENDPOINTS:
        if path == public_path or path.startswith(public_path + '/'):
            return True
    
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    
    return False


def get_current_customer_id():
    """
    Get customer ID from authenticated user session or header fallback.
    
    SECURITY: Prefers Flask-Login session, falls back to X-Customer-ID header for compatibility.
    
    Returns:
        int: customer_id from current_user session or header
        None: if not authenticated and no header provided
    """
    # First try Flask-Login session (preferred)
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            return current_user.customer_id
    except (AttributeError, RuntimeError):
        # Flask-Login not initialized or not in request context
        pass
    
    # Fallback to header for compatibility (when Flask-Login not set up)
    customer_id_header = request.headers.get('X-Customer-ID')
    if customer_id_header:
        try:
            return int(customer_id_header)
        except (ValueError, TypeError):
            logger.warning(f"Invalid X-Customer-ID header value: {customer_id_header}")
            return None
    
    logger.warning("get_current_customer_id() called but user not authenticated and no X-Customer-ID header")
    return None


def get_current_user_id():
    """
    Get user ID from authenticated user session.
    
    SECURITY: Replaces all instances of request.headers.get('X-User-ID')
    
    Returns:
        int: user_id from current_user session
        None: if not authenticated
    """
    if not current_user.is_authenticated:
        logger.error("get_current_user_id() called but user not authenticated")
        return None
    
    return current_user.user_id

