"""
Contractor Access API (Standalone)
===================================
Endpoints for contractor/tester user management and API key operations.
Works with models available on the main branch (no starter-ux dependencies).

Routes:
  POST   /api/admin-ui/customers/<cid>/contractor-access  - Create contractor user
  PUT    /api/admin-ui/contractor-access/<uid>/revoke      - Revoke contractor access
  GET    /api/admin-ui/customers/<cid>/contractors         - List contractors
  GET    /api/admin-ui/customers/<cid>/api-keys            - List API keys
  POST   /api/admin-ui/customers/<cid>/api-keys            - Create API key
  POST   /api/admin-ui/api-keys/<kid>/revoke               - Revoke API key
"""

import re
import logging
from datetime import datetime, timedelta

from functools import wraps
from flask import Blueprint, request, jsonify, session as flask_session
from werkzeug.security import generate_password_hash

from extensions import db
from models import Customer, User, ActivityLog
from activity_logging import ActivityLogger


def super_admin_required(f):
    """Decorator: requires super_admin or admin role via session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = flask_session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        role = getattr(user, 'role', None)
        if role not in ('super_admin', 'admin'):
            return jsonify({"error": "Super admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

logger = logging.getLogger(__name__)
contractor_access_bp = Blueprint("contractor_access_bp", __name__)

activity_logger = ActivityLogger()


def _log(action, description, customer_id=None, resource_type=None, resource_id=None):
    """Log security action via ActivityLogger."""
    try:
        user_id = flask_session.get('user_id')
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:200]
        activity_logger.log_activity(
            customer_id=customer_id,
            user_id=user_id,
            action_type=action,
            action_description=f"{description} [IP: {ip}]",
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            status='success',
            details={'category': 'security', 'ip_address': ip, 'user_agent': user_agent},
        )
    except Exception as e:
        logger.warning(f"Failed to log security action: {e}")


def _validate_email(email):
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def _validate_password(password):
    """Password strength validation: 8+ chars, upper, lower, digit."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    return True, "OK"


# ===================================================================
# Contractor / Tester User Management
# ===================================================================

@contractor_access_bp.route("/api/admin-ui/customers/<int:cid>/contractor-access", methods=["POST"])
@super_admin_required
def create_contractor_access(cid):
    """Create a contractor user with time-limited, account-restricted access."""
    try:
        data = request.get_json(force=True)
        contractor_name = data.get("contractor_name", "").strip()
        contractor_email = data.get("contractor_email", "").strip()
        password = data.get("password", "").strip()
        role = data.get("role", "viewer")
        duration_days = int(data.get("duration_days", 90))
        allowed_account_ids = data.get("allowed_account_ids")
        allowed_customer_ids = data.get("allowed_customer_ids")
        notes = data.get("notes", "")

        # Validate inputs
        if not contractor_name or not contractor_email or not password:
            return jsonify({"error": "Name, email, and password are required"}), 400

        if not _validate_email(contractor_email):
            return jsonify({"error": "Invalid email format"}), 400

        pw_ok, pw_msg = _validate_password(password)
        if not pw_ok:
            return jsonify({"error": pw_msg}), 400

        if role not in ('viewer', 'csm', 'tester'):
            return jsonify({"error": f"Invalid role: {role}. Must be viewer, csm, or tester"}), 400

        # Check customer exists
        customer = db.session.get(Customer, cid)
        if not customer:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        # Check duplicate email
        existing = User.query.filter_by(email=contractor_email).first()
        if existing:
            return jsonify({"error": f"User with email {contractor_email} already exists"}), 409

        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=duration_days)

        # Create user
        new_user = User(
            customer_id=cid,
            user_name=contractor_name,
            email=contractor_email,
            password_hash=generate_password_hash(password),
            role=role,
            active=True,
            vertical='dc2_s',
        )

        # Set RBAC fields if available on User model
        if hasattr(new_user, 'is_contractor'):
            new_user.is_contractor = True
        if hasattr(new_user, 'expires_at'):
            new_user.expires_at = expires_at
        if hasattr(new_user, 'allowed_account_ids') and allowed_account_ids:
            new_user.allowed_account_ids = allowed_account_ids
        if hasattr(new_user, 'allowed_customer_ids') and allowed_customer_ids:
            new_user.allowed_customer_ids = allowed_customer_ids

        db.session.add(new_user)
        db.session.commit()

        _log(
            "contractor_access_create",
            f"Contractor '{contractor_name}' ({contractor_email}) created for customer #{cid}",
            customer_id=cid,
            resource_type="user",
            resource_id=new_user.user_id,
        )

        return jsonify({
            "status": "success",
            "user_id": new_user.user_id,
            "email": new_user.email,
            "expires_at": expires_at.isoformat(),
            "allowed_account_ids": allowed_account_ids,
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("create_contractor_access failed")
        return jsonify({"error": f"Failed to create contractor access: {str(e)}"}), 500


@contractor_access_bp.route("/api/admin-ui/contractor-access/<int:user_id>/revoke", methods=["PUT"])
@super_admin_required
def revoke_contractor_access(user_id):
    """Revoke contractor access — deactivate user."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": f"User {user_id} not found"}), 404

        user.active = False
        db.session.commit()

        _log(
            "contractor_access_revoke",
            f"Contractor '{user.user_name}' ({user.email}) access revoked",
            customer_id=user.customer_id,
            resource_type="user",
            resource_id=user.user_id,
        )

        return jsonify({
            "status": "success",
            "message": f"Contractor {user.email} has been deactivated",
            "keys_revoked": 0,
        })

    except Exception as e:
        db.session.rollback()
        logger.exception("revoke_contractor_access failed")
        return jsonify({"error": f"Failed to revoke contractor access: {str(e)}"}), 500


@contractor_access_bp.route("/api/admin-ui/customers/<int:cid>/contractors", methods=["GET"])
@super_admin_required
def list_contractors(cid):
    """List contractor and tester users for a customer."""
    try:
        query = User.query.filter_by(customer_id=cid)

        # Filter for contractors/testers
        contractors = []
        for user in query.all():
            is_contractor = getattr(user, 'is_contractor', False)
            is_tester = getattr(user, 'role', '') == 'tester'
            if is_contractor or is_tester:
                contractors.append({
                    "user_id": user.user_id,
                    "user_name": user.user_name,
                    "email": user.email,
                    "role": getattr(user, 'role', 'viewer'),
                    "active": user.active,
                    "is_contractor": is_contractor,
                    "expires_at": user.expires_at.isoformat() if hasattr(user, 'expires_at') and user.expires_at else None,
                    "allowed_account_ids": getattr(user, 'allowed_account_ids', None),
                    "allowed_customer_ids": getattr(user, 'allowed_customer_ids', None),
                    "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                })

        return jsonify({"contractors": contractors})

    except Exception as e:
        logger.exception("list_contractors failed")
        return jsonify({"error": str(e)}), 500


# ===================================================================
# API Key Management (simplified — works without CustomerApiKey model)
# ===================================================================

@contractor_access_bp.route("/api/admin-ui/customers/<int:cid>/api-keys", methods=["GET"])
@super_admin_required
def list_api_keys(cid):
    """List API keys for a customer."""
    try:
        # Try to use CustomerApiKey model if available
        try:
            from models import CustomerApiKey
            keys = CustomerApiKey.query.filter_by(customer_id=cid).all()
            result = []
            for k in keys:
                result.append({
                    "id": k.id,
                    "key_prefix": k.key_prefix,
                    "name": k.name,
                    "scopes": k.scopes if k.scopes else [],
                    "is_active": k.is_active,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                    "created_at": k.created_at.isoformat() if k.created_at else None,
                    "expires_at": k.expires_at.isoformat() if hasattr(k, 'expires_at') and k.expires_at else None,
                    "partner_tier": getattr(k, 'partner_tier', None),
                    "allowed_account_ids": getattr(k, 'allowed_account_ids', None),
                })
            return jsonify({"api_keys": result})
        except ImportError:
            return jsonify({"api_keys": []})

    except Exception as e:
        logger.exception("list_api_keys failed")
        return jsonify({"error": str(e)}), 500


@contractor_access_bp.route("/api/admin-ui/customers/<int:cid>/api-keys", methods=["POST"])
@super_admin_required
def create_api_key(cid):
    """Create a new API key for a customer."""
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        scopes = data.get("scopes", ["read"])
        duration_days = data.get("duration_days")
        allowed_account_ids = data.get("allowed_account_ids")

        if not name:
            return jsonify({"error": "Key name is required"}), 400

        expires_at = None
        if duration_days:
            expires_at = datetime.utcnow() + timedelta(days=int(duration_days))

        # Try using api_key_service if available
        try:
            from api_key_service import generate_api_key as gen_key
            result = gen_key(
                customer_id=cid,
                name=name,
                scopes=scopes,
                expires_at=expires_at,
                allowed_account_ids=allowed_account_ids,
            )
            _log("api_key_create", f"API key '{name}' created for customer #{cid}",
                 customer_id=cid, resource_type="api_key")
            return jsonify(result), 201
        except ImportError:
            return jsonify({"error": "API key service not available on this branch"}), 501

    except Exception as e:
        logger.exception("create_api_key failed")
        return jsonify({"error": str(e)}), 500


@contractor_access_bp.route("/api/admin-ui/api-keys/<int:key_id>/revoke", methods=["POST"])
@super_admin_required
def revoke_api_key_endpoint(key_id):
    """Revoke an API key."""
    try:
        try:
            from api_key_service import revoke_api_key as do_revoke
            result = do_revoke(key_id)
            _log("api_key_revoke", f"API key #{key_id} revoked",
                 resource_type="api_key", resource_id=key_id)
            return jsonify({"status": "success", "message": f"Key {key_id} revoked"})
        except ImportError:
            return jsonify({"error": "API key service not available"}), 501

    except Exception as e:
        logger.exception("revoke_api_key failed")
        return jsonify({"error": str(e)}), 500


# ===================================================================
# Security Log
# ===================================================================

@contractor_access_bp.route("/api/admin-ui/activity-log", methods=["GET"])
@super_admin_required
def get_activity_log():
    """Get activity log entries, optionally filtered by category."""
    try:
        category = request.args.get("category")
        customer_id = request.args.get("customer_id", type=int)
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)

        query = ActivityLog.query.order_by(ActivityLog.created_at.desc())

        if category:
            query = query.filter(ActivityLog.action_category == category)
        if customer_id:
            query = query.filter(ActivityLog.customer_id == customer_id)

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        logs = []
        for log in paginated.items:
            logs.append({
                "id": log.id,
                "customer_id": log.customer_id,
                "user_id": log.user_id,
                "action_type": log.action_type,
                "action_category": getattr(log, 'action_category', None),
                "action_description": log.action_description,
                "resource_type": getattr(log, 'resource_type', None),
                "resource_id": getattr(log, 'resource_id', None),
                "status": log.status,
                "ip_address": getattr(log, 'ip_address', None),
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        return jsonify({
            "activity_logs": logs,
            "pagination": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            },
        })

    except Exception as e:
        logger.exception("get_activity_log failed")
        return jsonify({"error": str(e)}), 500
