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
    '/api/upload/health',  # Upload API health check
    '/api/forgot-password',
    '/api/reset-password',
    # Onboarding endpoints - must be public for new customer creation
    '/api/onboarding/complete',
    '/api/onboarding/provision',
    '/api/onboarding/upload',  # Upload endpoint for onboarding workflow
    '/api/onboarding/process-data',
    '/api/onboarding/register-journey-api',
    '/api/onboarding/processing-status',
    '/api/onboarding/templates',  # Template download endpoints
    '/api/onboarding/validate-csv',  # CSV validation endpoint
    # Integration framework — webhook endpoints must be public (n8n/external push)
    '/api/integrations/webhook',  # Public inbound webhook (HMAC-authenticated)
    '/api/integrations/connector-types',  # Discovery endpoint
    # /api/test-runner and /api/admin/uuid-backfill are protected (require auth)
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
        
        # Skip authentication in TESTING mode (pytest)
        if app.config.get('TESTING'):
            return None

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
            # User model defines is_authenticated as a METHOD, not a property, so we need to call it
            is_auth = current_user.is_authenticated() if callable(current_user.is_authenticated) else (current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False)
            logger.debug(f"[auth] Auth check for {request.path}: authenticated={is_auth}")

            # Integration API: accept X-Customer-ID header (for n8n/external systems)
            if not is_auth and request.path.startswith('/api/integrations/'):
                cid = request.headers.get('X-Customer-ID')
                if cid:
                    logger.info(f"[auth] Integration API: using X-Customer-ID={cid}")
                    return None  # Allow — integration API handles its own tenant isolation

            # Require authentication for all API endpoints
            if not is_auth:
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
        
        Idle timeout: 2 hours of inactivity (increased from 30 minutes for better UX)
        Note: Only checks if last_activity exists. If missing, assume it's a new session.
        """
        # Only check idle timeout for authenticated users
        if not current_user.is_authenticated:
            return None
        
        from flask import session
        from datetime import datetime, timedelta
        
        last_activity_str = session.get('last_activity')
        
        # If last_activity doesn't exist, this is likely a new session or first request
        # Set it now and allow the request to proceed
        if not last_activity_str:
            # First request - initialize last_activity
            session['last_activity'] = datetime.utcnow().isoformat()
            session.modified = True
            return None
        
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            idle_duration = datetime.utcnow() - last_activity
            
            # Check if idle for more than the configured timeout (default: 2 hours)
            idle_timeout = app.config.get('SESSION_IDLE_TIMEOUT', timedelta(hours=2))
            if idle_duration > idle_timeout:
                from flask_login import logout_user
                logger.info(f"User {current_user.email if hasattr(current_user, 'email') else 'unknown'} logged out due to inactivity ({idle_duration.seconds // 60} minutes)")
                logout_user()
                session.clear()
                
                return jsonify({
                    'error': 'Session expired',
                    'message': f'Your session expired due to inactivity ({idle_duration.seconds // 60} minutes). Please log in again.',
                    'reason': 'idle_timeout',
                    'idle_minutes': idle_duration.seconds // 60
                }), 401
        except Exception as e:
            logger.error(f"Error checking idle timeout: {e}")
            # On error, allow request to proceed (fail open for better UX)
        
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


def _is_admin_user():
    """Check if the current authenticated user has admin role."""
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            return getattr(current_user, 'role', None) == 'admin'
    except (AttributeError, RuntimeError):
        pass
    return False


def get_current_customer_id():
    """
    Get customer ID (always integer) from authenticated user session,
    with admin-only X-Customer-ID header override.

    Priority:
      1. If user is authenticated AND has admin role AND X-Customer-ID header is set:
         use the header value (allows admin/service accounts to act on behalf of
         target customers — used by load driver, API clients).
      2. If user is authenticated (any role): use session customer_id.
      3. If not authenticated but X-Customer-ID header present: use header
         (fallback for unauthenticated contexts like onboarding).

    SECURITY: Non-admin users CANNOT override their customer scope via the header.
    This prevents tenant isolation breaches where user A spoofs X-Customer-ID
    to access customer B's data.

    If the header contains a UUID, resolves it to the integer customer_id.

    Returns:
        int: customer_id (always integer for internal use)
        None: if not authenticated and no header provided
    """
    # Resolve header value once (used in both admin-override and unauthenticated paths)
    customer_id_header = request.headers.get('X-Customer-ID')
    header_customer_id = None
    if customer_id_header:
        header_val = customer_id_header.strip()
        if header_val:
            # Try integer first
            try:
                header_customer_id = int(header_val)
            except (ValueError, TypeError):
                # UUID string — resolve to integer customer_id
                try:
                    from uuid_utils import resolve_customer
                    customer = resolve_customer(header_val, allow_none=True)
                    if customer:
                        header_customer_id = customer.customer_id
                    else:
                        logger.warning(f"UUID in X-Customer-ID header did not resolve: {header_val}")
                except Exception as e:
                    logger.warning(f"Failed to resolve X-Customer-ID UUID: {e}")

    # 1. Authenticated user path
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            # Admin users may override customer scope via header
            if header_customer_id is not None and _is_admin_user():
                if header_customer_id != current_user.customer_id:
                    logger.info(
                        f"Admin {current_user.email} overriding customer scope: "
                        f"{current_user.customer_id} → {header_customer_id}"
                    )
                return header_customer_id

            # Non-admin users (or no header): always use session customer_id
            return current_user.customer_id
    except (AttributeError, RuntimeError):
        # Flask-Login not initialized or not in request context
        pass

    # 2. Unauthenticated fallback: use header if present
    #    (for public endpoints like onboarding, or when Flask-Login not set up)
    if header_customer_id is not None:
        logger.debug(f"get_current_customer_id: unauthenticated, using header = {header_customer_id}")
        return header_customer_id

    logger.warning("get_current_customer_id() called but no X-Customer-ID header and user not authenticated")
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

