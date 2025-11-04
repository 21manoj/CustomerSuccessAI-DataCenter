#!/usr/bin/env python3
"""
Authentication Decorators and Helper Functions
Provides secure authentication for all API endpoints
"""

from functools import wraps
from flask import request, jsonify, session
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


def login_required(f):
    """
    Custom authentication decorator for API endpoints.
    
    Checks if user is authenticated via Flask-Login session.
    Returns 401 Unauthorized if not authenticated.
    
    Usage:
        @app.route('/api/accounts')
        @login_required
        def get_accounts():
            customer_id = get_current_customer_id()
            # ... your code ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning(f"Unauthorized access attempt to {request.path} from {request.remote_addr}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please log in to access this resource',
                'status': 'unauthorized'
            }), 401
        
        # Check if user account is active
        if not current_user.is_active():
            logger.warning(f"Inactive user {current_user.email} attempted to access {request.path}")
            return jsonify({
                'error': 'Account inactive',
                'message': 'Your account has been deactivated. Contact support.',
                'status': 'forbidden'
            }), 403
        
        # Update last activity timestamp
        session['last_activity'] = str(datetime.utcnow().isoformat())
        session.modified = True  # Mark session as modified to refresh expiry
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_customer_id():
    """
    Get customer ID from authenticated user session.
    
    SECURITY: This replaces the vulnerable request.headers.get('X-Customer-ID')
    
    Returns:
        int: customer_id from current_user session
        None: if not authenticated
    """
    if not current_user.is_authenticated:
        logger.error("get_current_customer_id() called but user not authenticated")
        return None
    
    return current_user.customer_id


def get_current_user_id():
    """
    Get user ID from authenticated user session.
    
    SECURITY: Replaces the vulnerable request.headers.get('X-User-ID')
    
    Returns:
        int: user_id from current_user session
        None: if not authenticated
    """
    if not current_user.is_authenticated:
        logger.error("get_current_user_id() called but user not authenticated")
        return None
    
    return current_user.user_id


def get_current_user():
    """
    Get current authenticated user object.
    
    Returns:
        User: current_user object with all fields
        None: if not authenticated
    """
    if not current_user.is_authenticated:
        return None
    
    return current_user


def admin_required(f):
    """
    Decorator for admin-only endpoints.
    
    Usage:
        @app.route('/api/admin/users')
        @login_required
        @admin_required
        def list_all_users():
            # Only admins can access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if user is admin (you may need to add is_admin field to User model)
        if not getattr(current_user, 'is_admin', False):
            logger.warning(f"Non-admin user {current_user.email} attempted to access admin endpoint {request.path}")
            return jsonify({
                'error': 'Admin access required',
                'message': 'You do not have permission to access this resource',
                'status': 'forbidden'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


# Import datetime for last_activity tracking
from datetime import datetime

