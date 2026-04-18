"""
Bearer token authentication for app-to-app API access.

Tokens are validated against the customer_api_keys table.
The table stores key_hash (SHA256) and key_prefix for fast lookup.

Usage:
    from utils.api_token_auth import require_api_token

    @app.route('/api/integrations/ingest', methods=['POST'])
    @require_api_token
    def ingest():
        # g.customer_id, g.api_key_name, g.auth_method are set
        ...
"""
import functools
import hashlib
import logging
from datetime import datetime
from flask import request, jsonify, g

logger = logging.getLogger(__name__)


def _authenticate_bearer_token(token: str):
    """
    Validate a Bearer token against customer_api_keys.
    Returns the CustomerApiKey row or None.
    """
    from models import CustomerApiKey

    # key_prefix is the first 12 chars of the original token (stored on creation)
    # Must match _KEY_PREFIX_LEN in api_key_service.py
    prefix = token[:12] if len(token) >= 12 else token
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Use prefix for index-aided lookup, then verify full hash
    api_key = CustomerApiKey.query.filter_by(
        key_prefix=prefix,
        key_hash=token_hash,
        is_active=True,
    ).first()

    if api_key and api_key.expires_at and api_key.expires_at < datetime.utcnow():
        logger.info(f"API key '{api_key.name}' has expired")
        return None

    return api_key


def require_api_token(f):
    """Decorator: require valid Bearer token in Authorization header."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({
                "error": "Missing Bearer token",
                "status": "unauthorized",
            }), 401

        token = auth_header[7:]  # Strip "Bearer "
        api_key = _authenticate_bearer_token(token)
        if not api_key:
            return jsonify({
                "error": "Invalid or inactive API token",
                "status": "unauthorized",
            }), 401

        # Update last-used tracking
        try:
            from extensions import db
            api_key.last_used_at = datetime.utcnow()
            api_key.last_used_ip = request.remote_addr
            db.session.commit()
        except Exception:
            pass  # Non-fatal

        # Set request context for downstream handlers
        g.customer_id = api_key.customer_id
        g.api_key_id = api_key.id
        g.api_key_name = api_key.name
        g.api_key_scopes = api_key.scopes or ['read']
        g.auth_method = 'bearer_token'

        return f(*args, **kwargs)
    return decorated


def require_api_token_or_session(f):
    """
    Decorator: accept EITHER a valid Bearer token OR an existing session/cookie auth.
    Use this on endpoints that need to support both UI users and app-to-app callers.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        # Path 1: Bearer token
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            api_key = _authenticate_bearer_token(token)
            if not api_key:
                return jsonify({
                    "error": "Invalid or inactive API token",
                    "status": "unauthorized",
                }), 401

            try:
                from extensions import db
                api_key.last_used_at = datetime.utcnow()
                api_key.last_used_ip = request.remote_addr
                db.session.commit()
            except Exception:
                pass

            g.customer_id = api_key.customer_id
            g.api_key_id = api_key.id
            g.api_key_name = api_key.name
            g.api_key_scopes = api_key.scopes or ['read']
            g.auth_method = 'bearer_token'
            return f(*args, **kwargs)

        # Path 2: Fall through to existing session/cookie auth
        # (the endpoint's own _get_customer_id() logic handles this)
        g.auth_method = 'session'
        return f(*args, **kwargs)

    return decorated
