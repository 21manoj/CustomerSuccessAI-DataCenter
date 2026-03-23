"""
Admin UI API — Super Admin Console Backend
============================================
Full CRUD endpoints for the standalone Super Admin Console.

Routes:
  GET    /api/admin-ui/dashboard/stats           - Platform overview stats
  GET    /api/admin-ui/customers                  - List customers (paginated, searchable)
  GET    /api/admin-ui/customers/<cid>            - Customer detail (config, license, users)
  POST   /api/admin-ui/customers                  - Create new customer (onboarding)
  PUT    /api/admin-ui/customers/<cid>            - Update customer
  POST   /api/admin-ui/customers/<cid>/deactivate - Deactivate customer
  POST   /api/admin-ui/customers/<cid>/reactivate - Reactivate customer
  GET    /api/admin-ui/customers/<cid>/users      - List users for customer
  POST   /api/admin-ui/customers/<cid>/users      - Create user for customer
  PUT    /api/admin-ui/users/<uid>                - Update user
  GET    /api/admin-ui/customers/<cid>/license    - License & seat usage
  PUT    /api/admin-ui/customers/<cid>/license    - Update license
  GET    /api/admin-ui/license/warnings           - License expiry warnings
  GET    /api/admin-ui/verticals                  - List available verticals
  GET    /api/admin-ui/verticals/<v>/templates    - Vertical config templates
  GET    /api/admin-ui/customers/<cid>/config     - Customer config overrides
  PUT    /api/admin-ui/customers/<cid>/config/<t> - Update customer config
  DELETE /api/admin-ui/customers/<cid>/config/<t> - Delete customer config override

Also re-exports contractor_access_bp endpoints (api-keys, contractors, activity-log).
"""

import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, session as flask_session
from werkzeug.security import generate_password_hash

from extensions import db
from models import Customer, CustomerConfig, Account, User, FeatureToggle, ActivityLog

logger = logging.getLogger(__name__)

admin_ui_api = Blueprint("admin_ui_api", __name__)


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def super_admin_required(f):
    """Require super_admin or admin role via session."""
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


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/dashboard/stats", methods=["GET"])
@super_admin_required
def dashboard_stats():
    """Platform overview: customer count, active users, seat/license warnings."""
    try:
        total_customers = Customer.query.count()
        active_customers = Customer.query.filter(
            Customer.customer_id.in_(
                db.session.query(Account.customer_id).filter_by(account_status='active').distinct()
            )
        ).count()
        total_users = User.query.filter_by(active=True).count()
        total_accounts = Account.query.filter_by(account_status='active').count()

        # Vertical distribution
        verticals = db.session.query(
            Customer.vertical, db.func.count(Customer.customer_id)
        ).group_by(Customer.vertical).all()
        vertical_dist = [{"vertical": v or "saas", "customer_count": c} for v, c in verticals]

        # Seat warnings (customers with >80% seat usage) — simplified
        seat_warnings = []
        license_warnings = []

        return jsonify({
            "overview": {
                "total_customers": total_customers,
                "active_customers": active_customers,
                "total_active_users": total_users,
                "total_active_accounts": total_accounts,
            },
            "seat_warnings": {"count": len(seat_warnings), "customers": seat_warnings},
            "license_expiry_warnings": {"count": 0, "customers": []},
            "expired_licenses": {"count": 0, "customers": []},
            "vertical_distribution": vertical_dist,
        })
    except Exception as e:
        logger.exception("dashboard_stats failed")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Customers CRUD
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/customers", methods=["GET"])
@super_admin_required
def list_customers():
    """List customers with search, vertical filter, and pagination."""
    try:
        search = request.args.get("search", "").strip()
        vertical = request.args.get("vertical", "").strip()
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)

        query = Customer.query.order_by(Customer.customer_id.desc())

        if search:
            query = query.filter(Customer.customer_name.ilike(f"%{search}%"))
        if vertical:
            query = query.filter(Customer.vertical == vertical)

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        customers = []
        for c in paginated.items:
            account_count = Account.query.filter_by(customer_id=c.customer_id, account_status='active').count()
            user_count = User.query.filter_by(customer_id=c.customer_id, active=True).count()
            customers.append({
                "customer_id": c.customer_id,
                "customer_name": c.customer_name,
                "domain": c.domain or "",
                "vertical": c.vertical or "saas",
                "email": c.email or "",
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "is_reference": False,
                "account_count": account_count,
                "user_count": user_count,
            })

        return jsonify({
            "customers": customers,
            "pagination": {
                "page": paginated.page,
                "per_page": paginated.per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            },
        })
    except Exception as e:
        logger.exception("list_customers failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>", methods=["GET"])
@super_admin_required
def get_customer(cid):
    """Customer detail with config, license info, accounts."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        config = CustomerConfig.query.filter_by(customer_id=cid).first()
        accounts = Account.query.filter_by(customer_id=cid).order_by(Account.account_id).all()
        users = User.query.filter_by(customer_id=cid).all()

        # Get tier from feature toggles
        tier_toggle = FeatureToggle.query.filter_by(
            customer_id=cid, feature_name='subscription_tier'
        ).first()
        tier = 'starter'
        if tier_toggle and tier_toggle.config:
            tier = tier_toggle.config.get('tier', 'starter')

        return jsonify({
            "customer": {
                "customer_id": c.customer_id,
                "customer_name": c.customer_name,
                "domain": c.domain or "",
                "email": c.email or "",
                "vertical": c.vertical or "saas",
                "uuid": c.uuid or "",
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "is_reference": False,
            },
            "config": {
                "vertical": config.vertical if config else "saas",
                "enabled_kpis": config.dc2s_enabled_kpis if config else None,
                "pillar_weights": config.dc2s_pillar_weights if config else None,
                "kpi_weights": config.dc2s_kpi_weights if config else None,
                "kpi_overrides": config.dc2s_kpi_overrides if config else None,
                "config_version": config.config_version if config else "1.0",
            } if config else None,
            "accounts": [{
                "account_id": a.account_id,
                "account_name": a.account_name,
                "status": a.account_status,
                "industry": a.industry,
                "region": a.region,
                "revenue": float(a.revenue) if a.revenue else 0,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            } for a in accounts],
            "users": [{
                "user_id": u.user_id,
                "user_name": u.user_name,
                "email": u.email,
                "role": getattr(u, 'role', 'viewer'),
                "active": u.active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "is_contractor": getattr(u, 'is_contractor', False),
                "expires_at": u.expires_at.isoformat() if hasattr(u, 'expires_at') and u.expires_at else None,
            } for u in users],
            "license": {
                "license": {
                    "license_type": tier,
                    "max_seats": 50 if tier == 'enterprise' else (20 if tier == 'professional' else 5),
                    "max_accounts": None,
                    "license_start": c.created_at.isoformat() if c.created_at else None,
                    "license_end": (c.created_at + timedelta(days=365)).isoformat() if c.created_at else None,
                    "auto_renew": True,
                },
                "seat_usage": {
                    "used": len([u for u in users if u.active]),
                    "max": 50 if tier == 'enterprise' else (20 if tier == 'professional' else 5),
                    "available": max(0, (50 if tier == 'enterprise' else (20 if tier == 'professional' else 5)) - len([u for u in users if u.active])),
                    "utilisation_pct": round(len([u for u in users if u.active]) / max(1, 50 if tier == 'enterprise' else (20 if tier == 'professional' else 5)) * 100, 1),
                },
                "warnings": [],
                "is_valid": True,
                "is_expired": False,
                "days_to_expiry": 365,
            },
            "tier": tier,
        })
    except Exception as e:
        logger.exception("get_customer failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers", methods=["POST"])
@super_admin_required
def create_customer():
    """Create a new customer with admin user and default config."""
    try:
        data = request.get_json(force=True)
        company_name = data.get("company_name", "").strip()
        admin_email = data.get("admin_email", "").strip()
        admin_name = data.get("admin_name", "").strip() or "Admin"
        password = data.get("password", "").strip()
        vertical = data.get("vertical", "dc2_s").strip()
        tier = data.get("tier", "starter")
        domain = data.get("domain", "").strip()

        if not company_name or not admin_email or not password:
            return jsonify({"error": "company_name, admin_email, and password are required"}), 400

        # Check duplicate
        existing = Customer.query.filter(
            (Customer.customer_name == company_name) | (Customer.email == admin_email)
        ).first()
        if existing:
            return jsonify({"error": f"Customer or email already exists (id={existing.customer_id})"}), 409

        # Create customer
        customer = Customer(
            customer_name=company_name,
            email=admin_email,
            domain=domain or None,
            vertical=vertical,
        )
        db.session.add(customer)
        db.session.flush()

        # Create admin user
        admin_user = User(
            customer_id=customer.customer_id,
            user_name=admin_name,
            email=admin_email,
            password_hash=generate_password_hash(password),
            role='admin',
            active=True,
            vertical=vertical,
        )
        db.session.add(admin_user)

        # Create default config
        config = CustomerConfig(
            customer_id=customer.customer_id,
            vertical=vertical,
        )
        db.session.add(config)

        # Set tier
        ft = FeatureToggle(
            customer_id=customer.customer_id,
            feature_name='subscription_tier',
            enabled=True,
            config={'tier': tier},
            description=f'{tier} tier subscription',
        )
        db.session.add(ft)

        # Create default accounts (3)
        num_accounts = data.get("num_accounts", 3)
        envs = ['Production', 'Staging', 'Development', 'DR', 'QA', 'Lab', 'Edge', 'GPU-Cluster', 'HPC', 'Archive']
        accounts_created = []
        for i in range(min(num_accounts, 10)):
            acct = Account(
                account_id=customer.customer_id * 1000 + i + 1,
                customer_id=customer.customer_id,
                account_name=f"{company_name} - {envs[i % len(envs)]}",
                industry=data.get("industry", "Technology"),
                vertical=vertical,
                region='us-west-2',
                account_status='active',
            )
            db.session.add(acct)
            accounts_created.append({"account_id": acct.account_id, "account_name": acct.account_name})

        db.session.commit()

        return jsonify({
            "customer_id": customer.customer_id,
            "customer_name": customer.customer_name,
            "admin_user_id": admin_user.user_id,
            "accounts": accounts_created,
            "tier": tier,
            "message": f"Customer '{company_name}' created successfully",
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("create_customer failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>", methods=["PUT"])
@super_admin_required
def update_customer(cid):
    """Update customer fields."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        data = request.get_json(force=True)
        if "customer_name" in data:
            c.customer_name = data["customer_name"]
        if "domain" in data:
            c.domain = data["domain"]
        if "email" in data:
            c.email = data["email"]
        if "vertical" in data:
            c.vertical = data["vertical"]

        db.session.commit()
        return jsonify({
            "customer_id": c.customer_id,
            "customer_name": c.customer_name,
            "domain": c.domain,
            "vertical": c.vertical,
        })
    except Exception as e:
        db.session.rollback()
        logger.exception("update_customer failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/deactivate", methods=["POST"])
@super_admin_required
def deactivate_customer(cid):
    """Deactivate all accounts and users for a customer."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        Account.query.filter_by(customer_id=cid).update({"account_status": "inactive"})
        User.query.filter_by(customer_id=cid).update({"active": False})
        db.session.commit()
        return jsonify({"status": "success", "message": f"Customer {cid} deactivated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/reactivate", methods=["POST"])
@super_admin_required
def reactivate_customer(cid):
    """Reactivate all accounts and users for a customer."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        Account.query.filter_by(customer_id=cid).update({"account_status": "active"})
        User.query.filter_by(customer_id=cid).update({"active": True})
        db.session.commit()
        return jsonify({"status": "success", "message": f"Customer {cid} reactivated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/purge", methods=["DELETE"])
@super_admin_required
def purge_customer(cid):
    """Hard-delete a customer and ALL related data (cascade). Irreversible."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        customer_name = c.customer_name
        from sqlalchemy import text

        # Get account IDs for this customer (needed for account_id-only tables)
        account_ids = [
            r[0] for r in db.session.execute(
                text("SELECT account_id FROM accounts WHERE customer_id = :cid"),
                {"cid": cid}
            ).fetchall()
        ]

        deleted = {}

        # 1. Delete from account_id-only tables
        # Use SAVEPOINTs so a missing table doesn't abort the entire transaction
        if account_ids:
            aid_list = ','.join(str(a) for a in account_ids)
            for tbl in ['dc2s_kpis', 'health_scores', 'kpi_scores', 'kpis',
                        'pillar_scores', 'qualitative_signals']:
                try:
                    db.session.execute(text("SAVEPOINT sp_del"))
                    r = db.session.execute(
                        text(f"DELETE FROM {tbl} WHERE account_id IN ({aid_list})")
                    )
                    deleted[tbl] = r.rowcount
                    db.session.execute(text("RELEASE SAVEPOINT sp_del"))
                except Exception:
                    db.session.execute(text("ROLLBACK TO SAVEPOINT sp_del"))

        # 2. Delete from customer_id tables (order: children first)
        customer_id_tables = [
            'context_edges', 'context_nodes', 'webhook_events',
            'playbook_webhook_logs', 'playbook_webhook_triggers',
            'integration_sync_logs', 'integration_credentials', 'integration_connectors',
            'approval_requests', 'agent_memory', 'activity_logs',
            'action_economics', 'account_notes', 'account_snapshots',
            'crm_field_mappings', 'customer_action_bindings', 'customer_contacts',
            'customer_insights', 'customer_workflow_configs',
            'feature_toggles', 'financial_projections', 'health_trends',
            'journey_data', 'kpi_reference_ranges', 'kpi_time_series', 'kpi_uploads',
            'playbook_executions', 'playbook_reports', 'playbook_triggers',
            'portfolio_memberships',
            'product_aggregate_trends', 'product_catalog', 'product_trends', 'products',
            'query_audits', 'rag_knowledge_base', 'rag_query_log',
            'roi_snapshots', 'weight_calibration_history', 'wizard_runs',
            'customer_api_keys', 'users', 'accounts',
            'customer_configs',
        ]
        for tbl in customer_id_tables:
            try:
                db.session.execute(text("SAVEPOINT sp_del"))
                r = db.session.execute(
                    text(f"DELETE FROM {tbl} WHERE customer_id = :cid"),
                    {"cid": cid}
                )
                if r.rowcount > 0:
                    deleted[tbl] = r.rowcount
                db.session.execute(text("RELEASE SAVEPOINT sp_del"))
            except Exception:
                db.session.execute(text("ROLLBACK TO SAVEPOINT sp_del"))

        # 3. Delete the customer record itself
        db.session.execute(
            text("DELETE FROM customers WHERE customer_id = :cid"),
            {"cid": cid}
        )
        deleted['customers'] = 1

        # 4. Clean up filesystem (verticals/customer{id}-*)
        import shutil, glob
        vert_dir = glob.glob(f'verticals/customer{cid}-*')
        for d in vert_dir:
            shutil.rmtree(d, ignore_errors=True)
            deleted['filesystem'] = d

        db.session.commit()

        logger.info(f"PURGED customer {cid} ({customer_name}): {deleted}")
        return jsonify({
            "status": "success",
            "message": f"Customer {cid} ({customer_name}) permanently deleted",
            "deleted": deleted,
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Purge customer {cid} failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/bulk-purge", methods=["POST"])
@super_admin_required
def bulk_purge_customers():
    """Bulk-delete multiple customers. Body: {"customer_ids": [1, 2, 3]}"""
    try:
        data = request.get_json() or {}
        cids = data.get('customer_ids', [])
        if not cids:
            return jsonify({"error": "customer_ids required"}), 400

        # Safety: never delete customer_id=1 (CS Pulse Admin)
        cids = [int(c) for c in cids if int(c) != 1]

        results = []
        for cid in cids:
            c = db.session.get(Customer, cid)
            if not c:
                results.append({"customer_id": cid, "status": "not_found"})
                continue

            # Delegate to single purge logic (inline for transaction efficiency)
            from sqlalchemy import text
            customer_name = c.customer_name
            account_ids = [
                r[0] for r in db.session.execute(
                    text("SELECT account_id FROM accounts WHERE customer_id = :cid"),
                    {"cid": cid}
                ).fetchall()
            ]
            if account_ids:
                aid_list = ','.join(str(a) for a in account_ids)
                for tbl in ['dc2s_kpis', 'health_scores', 'kpi_scores', 'kpis',
                            'pillar_scores', 'qualitative_signals']:
                    try:
                        db.session.execute(text("SAVEPOINT sp_bulk"))
                        db.session.execute(text(f"DELETE FROM {tbl} WHERE account_id IN ({aid_list})"))
                        db.session.execute(text("RELEASE SAVEPOINT sp_bulk"))
                    except Exception:
                        db.session.execute(text("ROLLBACK TO SAVEPOINT sp_bulk"))

            for tbl in ['context_edges', 'context_nodes', 'webhook_events',
                        'playbook_webhook_logs', 'playbook_webhook_triggers',
                        'integration_sync_logs', 'integration_credentials', 'integration_connectors',
                        'approval_requests', 'agent_memory', 'activity_logs',
                        'action_economics', 'account_notes', 'account_snapshots',
                        'crm_field_mappings', 'customer_action_bindings', 'customer_contacts',
                        'customer_insights', 'customer_workflow_configs',
                        'feature_toggles', 'financial_projections', 'health_trends',
                        'journey_data', 'kpi_reference_ranges', 'kpi_time_series', 'kpi_uploads',
                        'playbook_executions', 'playbook_reports', 'playbook_triggers',
                        'portfolio_memberships',
                        'product_aggregate_trends', 'product_catalog', 'product_trends', 'products',
                        'query_audits', 'rag_knowledge_base', 'rag_query_log',
                        'roi_snapshots', 'weight_calibration_history', 'wizard_runs',
                        'customer_api_keys', 'users', 'accounts', 'customer_configs']:
                try:
                    db.session.execute(text("SAVEPOINT sp_bulk"))
                    db.session.execute(text(f"DELETE FROM {tbl} WHERE customer_id = :cid"), {"cid": cid})
                    db.session.execute(text("RELEASE SAVEPOINT sp_bulk"))
                except Exception:
                    db.session.execute(text("ROLLBACK TO SAVEPOINT sp_bulk"))

            db.session.execute(text("DELETE FROM customers WHERE customer_id = :cid"), {"cid": cid})

            import shutil, glob
            for d in glob.glob(f'verticals/customer{cid}-*'):
                shutil.rmtree(d, ignore_errors=True)

            results.append({"customer_id": cid, "name": customer_name, "status": "purged"})

        db.session.commit()
        logger.info(f"BULK PURGE: {len(results)} customers processed")
        return jsonify({"status": "success", "results": results, "purged": len([r for r in results if r['status'] == 'purged'])})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk purge failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/orphans", methods=["GET"])
@super_admin_required
def detect_orphans():
    """Detect orphaned customers: 0 accounts, 0 KPIs, or no login in 7+ days."""
    try:
        from sqlalchemy import text
        rows = db.session.execute(text("""
            SELECT c.customer_id, c.customer_name, c.created_at,
                   count(DISTINCT a.account_id) as account_count,
                   count(DISTINCT u.user_id) as user_count,
                   max(u.last_login) as last_login
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            LEFT JOIN users u ON c.customer_id = u.customer_id
            WHERE c.customer_id != 1
            GROUP BY c.customer_id, c.customer_name, c.created_at
            ORDER BY c.created_at DESC
        """)).fetchall()

        orphans = []
        for r in rows:
            reasons = []
            if r[3] == 0:
                reasons.append("no_accounts")
            if r[4] == 0:
                reasons.append("no_users")
            if r[5] is None:
                reasons.append("never_logged_in")
            elif (datetime.utcnow() - r[5]).days > 7:
                reasons.append("inactive_7d+")

            orphans.append({
                "customer_id": r[0],
                "name": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "accounts": r[3],
                "users": r[4],
                "last_login": r[5].isoformat() if r[5] else None,
                "reasons": reasons,
                "is_orphan": len(reasons) > 0,
            })

        return jsonify({
            "total": len(orphans),
            "orphans": [o for o in orphans if o['is_orphan']],
            "healthy": [o for o in orphans if not o['is_orphan']],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/users", methods=["GET"])
@super_admin_required
def list_users(cid):
    """List all users for a customer."""
    try:
        users = User.query.filter_by(customer_id=cid).all()
        return jsonify({
            "users": [{
                "user_id": u.user_id,
                "user_name": u.user_name,
                "email": u.email,
                "role": getattr(u, 'role', 'viewer'),
                "active": u.active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "is_contractor": getattr(u, 'is_contractor', False),
                "expires_at": u.expires_at.isoformat() if hasattr(u, 'expires_at') and u.expires_at else None,
                "allowed_account_ids": getattr(u, 'allowed_account_ids', None),
                "allowed_customer_ids": getattr(u, 'allowed_customer_ids', None),
            } for u in users]
        })
    except Exception as e:
        logger.exception("list_users failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/users", methods=["POST"])
@super_admin_required
def create_user(cid):
    """Create a new user for a customer."""
    try:
        data = request.get_json(force=True)
        user_name = data.get("user_name", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        role = data.get("role", "viewer")

        if not user_name or not email or not password:
            return jsonify({"error": "user_name, email, and password are required"}), 400

        existing = User.query.filter_by(email=email).first()
        if existing:
            return jsonify({"error": f"User with email {email} already exists"}), 409

        user = User(
            customer_id=cid,
            user_name=user_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            active=True,
            vertical=Customer.query.get(cid).vertical if Customer.query.get(cid) else 'dc2_s',
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "user_id": user.user_id,
            "user_name": user.user_name,
            "email": user.email,
            "role": role,
            "active": True,
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.exception("create_user failed")
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/users/<int:uid>", methods=["PUT"])
@super_admin_required
def update_user(uid):
    """Update user fields."""
    try:
        user = db.session.get(User, uid)
        if not user:
            return jsonify({"error": f"User {uid} not found"}), 404

        data = request.get_json(force=True)
        if "user_name" in data:
            user.user_name = data["user_name"]
        if "role" in data:
            user.role = data["role"]
        if "active" in data:
            user.active = data["active"]

        db.session.commit()
        return jsonify({
            "user_id": user.user_id,
            "user_name": user.user_name,
            "role": user.role,
            "active": user.active,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# License (tier-based)
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/license", methods=["GET"])
@super_admin_required
def get_license(cid):
    """Get license/tier info for a customer."""
    try:
        c = db.session.get(Customer, cid)
        if not c:
            return jsonify({"error": f"Customer {cid} not found"}), 404

        tier_toggle = FeatureToggle.query.filter_by(
            customer_id=cid, feature_name='subscription_tier'
        ).first()
        tier = tier_toggle.config.get('tier', 'starter') if tier_toggle and tier_toggle.config else 'starter'
        max_seats = 50 if tier == 'enterprise' else (20 if tier == 'professional' else 5)
        active_users = User.query.filter_by(customer_id=cid, active=True).count()

        return jsonify({
            "license": {
                "license_type": tier,
                "max_seats": max_seats,
                "max_accounts": None,
                "license_start": c.created_at.isoformat() if c.created_at else None,
                "license_end": (c.created_at + timedelta(days=365)).isoformat() if c.created_at else None,
                "auto_renew": True,
            },
            "seat_usage": {
                "used": active_users,
                "max": max_seats,
                "available": max(0, max_seats - active_users),
                "utilisation_pct": round(active_users / max(1, max_seats) * 100, 1),
            },
            "warnings": [],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/license", methods=["PUT"])
@super_admin_required
def update_license(cid):
    """Update customer tier."""
    try:
        data = request.get_json(force=True)
        new_tier = data.get("license_type", "starter")

        ft = FeatureToggle.query.filter_by(customer_id=cid, feature_name='subscription_tier').first()
        if ft:
            ft.config = {'tier': new_tier}
        else:
            ft = FeatureToggle(
                customer_id=cid,
                feature_name='subscription_tier',
                enabled=True,
                config={'tier': new_tier},
            )
            db.session.add(ft)

        db.session.commit()
        return jsonify({"status": "success", "tier": new_tier})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/license/warnings", methods=["GET"])
@super_admin_required
def license_warnings():
    """License expiry/seat warnings across all customers."""
    return jsonify({"warnings": []})


# ---------------------------------------------------------------------------
# Verticals & Templates
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/verticals", methods=["GET"])
@super_admin_required
def list_verticals():
    """List available verticals with KPI/pillar counts from the registry."""
    from utils.vertical_registry import get_pillars, get_kpis, SUPPORTED_VERTICALS

    verticals = []
    for v in sorted(SUPPORTED_VERTICALS):
        try:
            pillars = get_pillars(v)
            kpis = get_kpis(v)
            label = {
                'dc2_s': 'Data Center (DC2_S)',
                'saas_premium': 'SaaS Premium',
            }.get(v, v)
            verticals.append({
                "vertical": v,
                "label": label,
                "pillar_count": len(pillars),
                "kpi_count": len(kpis),
                "pillar_names": {pid: p.get('name', pid) for pid, p in pillars.items()},
                "default_weights": {pid: p.get('weight_l2', 0.2) for pid, p in pillars.items()},
            })
        except Exception:
            verticals.append({"vertical": v, "label": v, "pillar_count": 0, "kpi_count": 0})
    return jsonify({"verticals": verticals})


@admin_ui_api.route("/api/admin-ui/verticals/<vertical>/templates", methods=["GET"])
@super_admin_required
def get_vertical_templates(vertical):
    """Get KPI catalog and pillar config for a vertical."""
    from utils.vertical_registry import get_pillars, get_kpis, normalize_vertical

    v = normalize_vertical(vertical)
    try:
        pillars = get_pillars(v)
        kpis = get_kpis(v)
    except ValueError:
        return jsonify({"error": f"Unknown vertical: {vertical}"}), 404

    # Build pillar summary with KPI list per pillar
    pillar_details = {}
    for pid, pdata in pillars.items():
        pillar_kpis = {k: kd for k, kd in kpis.items() if kd.get('pillar') == pid}
        pillar_details[pid] = {
            "name": pdata.get('name', pid),
            "weight_l2": pdata.get('weight_l2', 0.2),
            "kpi_count": len(pillar_kpis),
            "kpis": {
                code: {
                    "name": kd.get('name', code),
                    "weight_l1": kd.get('weight_l1', 0),
                    "unit": kd.get('unit', 'numeric'),
                    "higher_is_better": kd.get('higher_is_better', True),
                    "target": kd.get('target', {}),
                    "ranges": kd.get('ranges', {}),
                    "frequency": kd.get('frequency', 'monthly'),
                }
                for code, kd in sorted(pillar_kpis.items())
            },
        }

    return jsonify({
        "vertical": v,
        "pillar_count": len(pillars),
        "kpi_count": len(kpis),
        "pillars": pillar_details,
    })


# ---------------------------------------------------------------------------
# Customer Config
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/config", methods=["GET"])
@super_admin_required
def get_customer_config(cid):
    """Get customer config overrides."""
    try:
        config = CustomerConfig.query.filter_by(customer_id=cid).first()
        if not config:
            return jsonify({"overrides": []})

        overrides = []
        if config.dc2s_pillar_weights:
            overrides.append({
                "config_type": "pillar_weights",
                "config": config.dc2s_pillar_weights,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            })
        if config.dc2s_enabled_kpis:
            overrides.append({
                "config_type": "enabled_kpis",
                "config": config.dc2s_enabled_kpis,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            })
        return jsonify({"overrides": overrides})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/config/<config_type>", methods=["PUT"])
@super_admin_required
def update_customer_config(cid, config_type):
    """Update a specific config for a customer."""
    try:
        data = request.get_json(force=True)
        config = CustomerConfig.query.filter_by(customer_id=cid).first()
        if not config:
            config = CustomerConfig(customer_id=cid, vertical='dc2_s')
            db.session.add(config)

        new_config = data.get("config", data)
        if config_type == "pillar_weights":
            config.dc2s_pillar_weights = new_config
        elif config_type == "enabled_kpis":
            config.dc2s_enabled_kpis = new_config
        elif config_type == "kpi_weights":
            config.dc2s_kpi_weights = new_config
        else:
            return jsonify({"error": f"Unknown config type: {config_type}"}), 400

        db.session.commit()
        return jsonify({"status": "success", "config_type": config_type})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_ui_api.route("/api/admin-ui/customers/<int:cid>/config/<config_type>", methods=["DELETE"])
@super_admin_required
def delete_customer_config(cid, config_type):
    """Reset a config to template defaults."""
    try:
        config = CustomerConfig.query.filter_by(customer_id=cid).first()
        if not config:
            return "", 204

        if config_type == "pillar_weights":
            config.dc2s_pillar_weights = None
        elif config_type == "enabled_kpis":
            config.dc2s_enabled_kpis = None
        elif config_type == "kpi_weights":
            config.dc2s_kpi_weights = None

        db.session.commit()
        return "", 204
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Re-register contractor_access_bp routes on this blueprint
# ---------------------------------------------------------------------------
# The contractor endpoints (api-keys, contractors, activity-log) are registered
# via contractor_access_bp as a fallback. When admin_ui_api loads, both blueprints
# coexist. No duplication needed here.
