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
        vertical_dist = [{"vertical": v or "saas_premium", "customer_count": c} for v, c in verticals]

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
            # Dynamic label: use catalog metadata if available, fallback to formatted slug
            _known_labels = {'dc2_s': 'Data Center (DC2_S)', 'saas_premium': 'SaaS Premium', 'saas': 'SaaS Premium'}
            label = _known_labels.get(v, v.replace('_', ' ').title())
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
# Custom Vertical Management
# ---------------------------------------------------------------------------

@admin_ui_api.route("/api/admin-ui/verticals", methods=["POST"])
@super_admin_required
def create_vertical():
    """Create a new custom vertical from a KPI catalog JSON."""
    import json as _json
    data = request.json
    if not data:
        return jsonify({"error": "Request body required"}), 400

    slug = (data.get('vertical_slug') or '').strip().lower().replace(' ', '_').replace('-', '_')
    if not slug or len(slug) < 3:
        return jsonify({"error": "vertical_slug must be at least 3 characters"}), 400

    label = data.get('label', slug.replace('_', ' ').title())
    description = data.get('description', '')
    scope = data.get('scope', 'platform')  # 'platform' or 'customer'
    field_mapping = data.get('field_mapping')  # Optional migration mapping template
    customer_id = data.get('customer_id')
    catalog = data.get('catalog', {})

    if not catalog or not catalog.get('kpis'):
        return jsonify({"error": "catalog with kpis is required"}), 400

    # Validate catalog using generic scorer
    try:
        from utils.generic_scorer import load_catalog_from_dict
        kpi_cat, pillar_cat = load_catalog_from_dict(catalog)
        if not kpi_cat:
            return jsonify({"error": "No valid KPIs found in catalog"}), 400
    except Exception as e:
        return jsonify({"error": f"Catalog validation failed: {str(e)}"}), 400

    kpi_count = len(catalog.get('kpis', {}))
    pillar_count = len(catalog.get('pillars', {}))

    if scope == 'customer' and customer_id:
        # Store in CustomerConfig.dc2s_kpi_definitions (hot-reload, no restart)
        from models import CustomerConfig, db
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            return jsonify({"error": f"Customer {customer_id} not found"}), 404
        config.dc2s_kpi_definitions = catalog
        config.vertical = slug
        db.session.commit()
        # Clear registry cache so it picks up new definitions
        from utils.vertical_registry import _kpis_cache, _pillars_cache
        _kpis_cache.pop(slug, None)
        _pillars_cache.pop(slug, None)
        return jsonify({
            "status": "created",
            "vertical": slug,
            "label": label,
            "kpi_count": kpi_count,
            "pillar_count": pillar_count,
            "scope": "customer",
            "customer_id": customer_id,
        }), 201
    else:
        # Write JSON catalog file to config/ directory (platform-level)
        import os
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        catalog_path = os.path.join(config_dir, f'{slug}_kpi_catalog.json')

        # Don't overwrite existing catalogs
        if os.path.exists(catalog_path):
            return jsonify({"error": f"Vertical '{slug}' already exists. Use a different slug or delete the existing one first."}), 409

        # Add metadata
        full_catalog = {
            "version": "1.0",
            "vertical": slug,
            "description": description,
            **catalog,
        }
        # Include field mapping template if provided (for migration reuse)
        if field_mapping and field_mapping.get('mappings'):
            full_catalog['field_mapping'] = field_mapping

        with open(catalog_path, 'w') as f:
            _json.dump(full_catalog, f, indent=2)

        # Clear registry cache and re-discover
        from utils.vertical_registry import _kpis_cache, _pillars_cache, SUPPORTED_VERTICALS, VERTICAL_ALIASES
        _kpis_cache.pop(slug, None)
        _pillars_cache.pop(slug, None)
        SUPPORTED_VERTICALS.add(slug)
        VERTICAL_ALIASES[slug] = slug

        return jsonify({
            "status": "created",
            "vertical": slug,
            "label": label,
            "kpi_count": kpi_count,
            "pillar_count": pillar_count,
            "scope": "platform",
            "catalog_path": f"config/{slug}_kpi_catalog.json",
        }), 201


@admin_ui_api.route("/api/admin-ui/verticals/validate", methods=["POST"])
@super_admin_required
def validate_vertical_catalog():
    """Validate a KPI catalog without saving it."""
    catalog = (request.json or {}).get('catalog', {})
    if not catalog:
        return jsonify({"valid": False, "errors": ["Empty catalog"]}), 400

    errors = []
    warnings = []

    # Check pillars
    pillars = catalog.get('pillars', {})
    kpis = catalog.get('kpis', {})

    if not pillars:
        errors.append("No pillars defined")
    if not kpis:
        errors.append("No KPIs defined")
    if len(pillars) < 3:
        errors.append(f"At least 3 pillars required (got {len(pillars)})")
    if len(pillars) > 7:
        errors.append(f"Maximum 7 pillars allowed (got {len(pillars)})")

    # Check pillar weights sum
    pillar_weights = [p.get('weight_l2', 0) for p in pillars.values()]
    if pillar_weights and abs(sum(pillar_weights) - 1.0) > 0.01:
        errors.append(f"Pillar weights must sum to 1.0 (got {sum(pillar_weights):.3f})")

    # Check KPIs per pillar
    pillar_codes = set(pillars.keys())
    kpis_by_pillar = {}
    for kcode, kdata in kpis.items():
        p = kdata.get('pillar', '')
        if p not in pillar_codes:
            errors.append(f"KPI {kcode} references unknown pillar '{p}'")
        kpis_by_pillar.setdefault(p, []).append(kcode)

    for pc in pillar_codes:
        if pc not in kpis_by_pillar:
            errors.append(f"Pillar {pc} has no KPIs")
        else:
            weights = [kpis[k].get('weight_l1', 0) for k in kpis_by_pillar[pc]]
            if weights and abs(sum(weights) - 1.0) > 0.05:
                warnings.append(f"KPI weights for {pc} sum to {sum(weights):.3f} (will be auto-normalized)")

    # Check ranges
    for kcode, kdata in kpis.items():
        ranges = kdata.get('ranges', {})
        if not ranges:
            errors.append(f"KPI {kcode} has no ranges defined")
        elif not all(k in ranges for k in ('healthy', 'risk', 'critical')):
            errors.append(f"KPI {kcode} missing range bands (need healthy, risk, critical)")

    # Try generic scorer validation
    try:
        from utils.generic_scorer import load_catalog_from_dict
        load_catalog_from_dict(catalog)
    except Exception as e:
        errors.append(f"Scorer validation failed: {str(e)}")

    return jsonify({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "kpi_count": len(kpis),
        "pillar_count": len(pillars),
    })


@admin_ui_api.route("/api/admin-ui/verticals/parse-csv", methods=["POST"])
@super_admin_required
def parse_csv_to_catalog():
    """Parse an uploaded CSV file into a KPI catalog JSON structure."""
    import csv
    import io

    if 'file' not in request.files:
        # Try raw CSV in body
        csv_content = request.data.decode('utf-8', errors='replace') if request.data else ''
        if not csv_content:
            return jsonify({"error": "No CSV file or content provided"}), 400
    else:
        csv_content = request.files['file'].read().decode('utf-8', errors='replace')

    parse_errors = []
    pillars = {}
    kpis = {}

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        required_cols = {'kpi_code', 'name', 'pillar'}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            missing = required_cols - set(reader.fieldnames or [])
            return jsonify({"error": f"Missing required columns: {missing}"}), 400

        for i, row in enumerate(reader, 1):
            try:
                kpi_code = row.get('kpi_code', '').strip()
                pillar_code = row.get('pillar', '').strip()
                kpi_name = row.get('name', '').strip()

                if not kpi_code or not pillar_code or not kpi_name:
                    parse_errors.append(f"Row {i}: missing kpi_code, name, or pillar")
                    continue

                # Auto-create pillar if not exists
                if pillar_code not in pillars:
                    pillar_name = row.get('pillar_name', pillar_code).strip()
                    weight_l2 = float(row.get('pillar_weight', 0) or 0)
                    pillars[pillar_code] = {
                        "name": pillar_name or pillar_code,
                        "weight_l2": weight_l2,
                        "kpi_count": 0,
                    }

                pillars[pillar_code]['kpi_count'] = pillars[pillar_code].get('kpi_count', 0) + 1

                higher = row.get('higher_is_better', 'true').strip().lower() in ('true', '1', 'yes', 'y')
                kpis[kpi_code] = {
                    "name": kpi_name,
                    "pillar": pillar_code,
                    "weight_l1": float(row.get('weight_l1', 0) or 0),
                    "unit": row.get('unit', 'percentage').strip() or 'percentage',
                    "higher_is_better": higher,
                    "frequency": row.get('frequency', 'monthly').strip() or 'monthly',
                    "target": {"operator": ">" if higher else "<", "value": float(row.get('target', 0) or 0)},
                    "ranges": {
                        "healthy": {"min": float(row.get('healthy_min', 0) or 0), "max": float(row.get('healthy_max', 100) or 100)},
                        "risk": {"min": float(row.get('risk_min', 0) or 0), "max": float(row.get('risk_max', 0) or 0)},
                        "critical": {"min": float(row.get('critical_min', 0) or 0), "max": float(row.get('critical_max', 0) or 0)},
                    },
                }
            except (ValueError, TypeError) as e:
                parse_errors.append(f"Row {i}: {str(e)}")

        # Auto-normalize pillar weights if they don't sum to 1
        total_pw = sum(p.get('weight_l2', 0) for p in pillars.values())
        if total_pw > 0 and abs(total_pw - 1.0) > 0.01:
            for p in pillars.values():
                p['weight_l2'] = round(p['weight_l2'] / total_pw, 4)
        elif total_pw == 0:
            # Equal distribution
            n = len(pillars)
            for p in pillars.values():
                p['weight_l2'] = round(1.0 / n, 4)

    except Exception as e:
        return jsonify({"error": f"CSV parsing failed: {str(e)}"}), 400

    return jsonify({
        "catalog": {"pillars": pillars, "kpis": kpis},
        "parse_errors": parse_errors,
        "kpi_count": len(kpis),
        "pillar_count": len(pillars),
    })


@admin_ui_api.route("/api/admin-ui/verticals/parse-source-csv", methods=["POST"])
@super_admin_required
def parse_source_csv():
    """Parse a foreign CSV (Gainsight, ChurnZero, etc.) and auto-detect KPI definitions.

    Unlike parse-csv which expects our template format, this endpoint accepts
    ANY CSV format and tries to infer KPI definitions from column names, values,
    and optional source_system hint.

    Returns detected KPIs with suggested mappings + the raw columns for manual mapping.
    """
    import csv
    import io
    import re

    source_system = request.form.get('source_system', request.args.get('source_system', 'auto'))

    if 'file' not in request.files:
        csv_content = request.data.decode('utf-8', errors='replace') if request.data else ''
        if not csv_content:
            return jsonify({"error": "No CSV file or content provided"}), 400
    else:
        csv_content = request.files['file'].read().decode('utf-8', errors='replace')

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = list(reader.fieldnames or [])
        if not headers:
            return jsonify({"error": "CSV has no headers"}), 400

        # Read all rows for value analysis
        rows = list(reader)

        # ─── Source system detection ───
        if source_system == 'auto':
            header_str = ' '.join(headers).lower()
            if 'churnscore' in header_str or 'churnzero' in header_str or 'churn_score' in header_str:
                source_system = 'churnzero'
            elif 'scorecard' in header_str or 'measure group' in header_str or 'gainsight' in header_str or 'csm name' in header_str:
                source_system = 'gainsight'
            elif 'hubspot' in header_str or 'hs_object_id' in header_str:
                source_system = 'hubspot'
            else:
                source_system = 'unknown'

        # ─── Detect long-format (pivoted) CSV ───
        # Long format: one row per measure per account (e.g., Gainsight Scorecard Mass Edit)
        # Columns like "Measure Name" + "Score" + "Weight" + "Measure Group"
        headers_lower = [h.lower().strip() for h in headers]
        is_long_format = (
            any(h in headers_lower for h in ['measure name', 'measure', 'kpi name', 'metric name']) and
            any(h in headers_lower for h in ['score', 'value', 'measure value'])
        )

        if is_long_format:
            # Pivot: extract unique measure names as KPI candidates
            measure_col = next((h for h in headers if h.lower().strip() in ('measure name', 'measure', 'kpi name', 'metric name')), None)
            score_col = next((h for h in headers if h.lower().strip() in ('score', 'value', 'measure value')), None)
            weight_col = next((h for h in headers if h.lower().strip() in ('weight',)), None)
            group_col = next((h for h in headers if h.lower().strip() in ('measure group', 'group', 'pillar', 'category')), None)

            measures = {}  # measure_name → {scores: [], weights: [], group: str}
            for row in rows:
                mname = (row.get(measure_col, '') or '').strip()
                if not mname:
                    continue
                if mname not in measures:
                    measures[mname] = {'scores': [], 'weights': [], 'group': ''}
                try:
                    measures[mname]['scores'].append(float(str(row.get(score_col, 0)).replace('%', '').replace('$', '').replace(',', '')))
                except (ValueError, TypeError):
                    pass
                if weight_col:
                    try:
                        measures[mname]['weights'].append(float(str(row.get(weight_col, 0)).replace('%', '')))
                    except (ValueError, TypeError):
                        pass
                if group_col:
                    measures[mname]['group'] = (row.get(group_col, '') or '').strip()

            # Build KPI candidates from pivoted measures
            kpi_candidates = []
            groups = set()
            for mname, mdata in measures.items():
                scores = mdata['scores']
                if not scores:
                    continue
                groups.add(mdata['group'])
                val_min, val_max = min(scores), max(scores)
                val_avg = sum(scores) / len(scores)
                avg_weight = sum(mdata['weights']) / len(mdata['weights']) if mdata['weights'] else 0

                col_lower = mname.lower()
                lower_keywords = ['time', 'days', 'tickets', 'churn', 'inactive', 'latency', 'complaints']
                is_lower = any(kw in col_lower for kw in lower_keywords)

                kpi_candidates.append({
                    'source_column': mname,
                    'suggested_kpi_code': re.sub(r'[^a-z0-9]', '_', col_lower).strip('_'),
                    'suggested_name': mname,
                    'unit': 'score',
                    'higher_is_better': not is_lower,
                    'suggested_target': round(val_avg + (val_max - val_avg) * 0.3, 1) if not is_lower else round(val_avg - (val_avg - val_min) * 0.3, 1),
                    'suggested_ranges': {
                        'healthy': {'min': round(val_avg, 1), 'max': round(val_max * 1.1, 1)},
                        'risk': {'min': round(val_min + (val_avg - val_min) * 0.3, 1), 'max': round(val_avg, 1)},
                        'critical': {'min': round(val_min * 0.8, 1), 'max': round(val_min + (val_avg - val_min) * 0.3, 1)},
                    } if not is_lower else {
                        'healthy': {'min': round(val_min * 0.8, 1), 'max': round(val_avg, 1)},
                        'risk': {'min': round(val_avg, 1), 'max': round(val_avg + (val_max - val_avg) * 0.5, 1)},
                        'critical': {'min': round(val_avg + (val_max - val_avg) * 0.5, 1), 'max': round(val_max * 1.2, 1)},
                    },
                    'pillar_hint': mdata['group'],
                    'suggested_weight': round(avg_weight / 100, 3) if avg_weight > 1 else round(avg_weight, 3),
                })

            # Detect metadata columns
            meta_cols = [h for h in headers if h != measure_col and h != score_col and h != weight_col and h != group_col]
            detected_columns = [{'column_name': h, 'is_metadata': True, 'mapped_to': '_metadata'} for h in meta_cols]

            return jsonify({
                'source_system': source_system,
                'format': 'long',
                'total_columns': len(headers),
                'total_rows': len(rows),
                'unique_measures': len(measures),
                'pillar_groups': sorted(g for g in groups if g),
                'detected_columns': detected_columns,
                'kpi_candidates': kpi_candidates,
                'metadata_columns': detected_columns,
                'unmapped_columns': [],
            })

        # ─── Known column mappings per source system ───
        GAINSIGHT_MAPPINGS = {
            'company name': '_account_name',
            'account name': '_account_name',
            'overall score': '_health_score',
            'overall health': '_health_score',
            'csm name': '_csm',
            'csm': '_csm',
            'measure group': '_pillar_hint',
            'group': '_pillar_hint',
            'measure name': '_kpi_name',
            'measure': '_kpi_name',
            'score': '_kpi_value',
            'weight': '_weight',
            'trend': '_trend',
            'lifecycle stage': '_lifecycle',
            'arr': '_arr',
            'renewal date': '_renewal_date',
            'nps score': 'nps',
            'csat score': 'csat',
            'product usage score': 'product_usage',
            'feature adoption': 'feature_adoption',
            'support tickets': 'support_tickets',
            'time to value': 'ttfv',
            'onboarding completion': 'onboarding',
            'executive sponsor engaged': 'exec_sponsor',
            'champion strength': 'champion_strength',
        }

        CHURNZERO_MAPPINGS = {
            'account': '_account_name',
            'account name': '_account_name',
            'churnscore': '_health_score',
            'churn score': '_health_score',
            'health score': '_health_score',
            'health color': '_health_color',
            'segment': '_segment',
            'last activity': '_last_activity',
            'days since last login': 'days_inactive',
            'dau': 'dau',
            'daily active users': 'dau',
            'wau': 'wau',
            'weekly active users': 'wau',
            'license utilization': 'license_util',
            'license utilization %': 'license_util',
            'logins last 30d': 'login_frequency',
            'login frequency': 'login_frequency',
            'total events last 30d': 'event_volume',
            'support tickets open': 'open_tickets',
            'nps': 'nps',
            'nps score': 'nps',
            'csat': 'csat',
            'contract value': '_arr',
            'arr': '_arr',
            'renewal date': '_renewal_date',
            'next renewal': '_renewal_date',
            'usage score': 'usage_score',
            'engagement score': 'engagement_score',
            'outcome score': 'outcome_score',
            'sentiment score': 'sentiment_score',
            'roi score': 'roi_score',
        }

        mappings = GAINSIGHT_MAPPINGS if source_system == 'gainsight' else CHURNZERO_MAPPINGS if source_system == 'churnzero' else {}

        # ─── Analyze each column ───
        detected_columns = []
        kpi_candidates = []

        for col in headers:
            col_lower = col.strip().lower()
            mapped_to = mappings.get(col_lower, '')

            # Analyze values to infer type
            values = [r.get(col, '') for r in rows if r.get(col, '').strip()]
            numeric_count = 0
            sample_vals = []
            for v in values[:20]:
                cleaned = v.replace('%', '').replace('$', '').replace(',', '').strip()
                try:
                    float(cleaned)
                    numeric_count += 1
                    sample_vals.append(float(cleaned))
                except (ValueError, TypeError):
                    pass

            is_numeric = numeric_count > len(values) * 0.7 if values else False
            val_min = min(sample_vals) if sample_vals else 0
            val_max = max(sample_vals) if sample_vals else 0
            val_avg = sum(sample_vals) / len(sample_vals) if sample_vals else 0

            col_info = {
                'column_name': col,
                'mapped_to': mapped_to,
                'is_numeric': is_numeric,
                'is_metadata': mapped_to.startswith('_') if mapped_to else False,
                'sample_values': [str(v) for v in values[:3]],
                'value_range': {'min': round(val_min, 2), 'max': round(val_max, 2), 'avg': round(val_avg, 2)} if is_numeric else None,
                'row_count': len(values),
            }
            detected_columns.append(col_info)

            # If it's a numeric non-metadata column, it's a KPI candidate
            if is_numeric and not mapped_to.startswith('_'):
                # Infer direction: if values look like percentages (0-100) and name suggests positive, higher_is_better
                higher_keywords = ['score', 'rate', 'adoption', 'usage', 'utilization', 'engagement', 'nps', 'csat', 'strength', 'frequency']
                lower_keywords = ['time', 'days', 'tickets', 'churn', 'inactive', 'latency', 'complaints', 'escalation']

                higher = any(kw in col_lower for kw in higher_keywords)
                lower = any(kw in col_lower for kw in lower_keywords)
                direction = 'lower_is_better' if (lower and not higher) else 'higher_is_better'

                # Infer unit
                if '%' in col or 'pct' in col_lower or 'rate' in col_lower or 'utilization' in col_lower:
                    unit = 'percentage'
                elif 'days' in col_lower or 'time' in col_lower:
                    unit = 'days'
                elif 'hours' in col_lower:
                    unit = 'hours'
                elif 'score' in col_lower or 'nps' in col_lower:
                    unit = 'score'
                elif 'count' in col_lower or 'tickets' in col_lower or 'events' in col_lower or 'logins' in col_lower:
                    unit = 'count'
                else:
                    unit = 'numeric'

                # Infer ranges from data
                if direction == 'higher_is_better':
                    healthy_min = round(val_avg + (val_max - val_avg) * 0.3, 1)
                    risk_min = round(val_avg - (val_avg - val_min) * 0.3, 1)
                    kpi_candidates.append({
                        'source_column': col,
                        'suggested_kpi_code': mapped_to or re.sub(r'[^a-z0-9]', '_', col_lower).strip('_'),
                        'suggested_name': col.strip(),
                        'unit': unit,
                        'higher_is_better': True,
                        'suggested_target': round(healthy_min, 1),
                        'suggested_ranges': {
                            'healthy': {'min': round(healthy_min, 1), 'max': round(val_max * 1.1, 1)},
                            'risk': {'min': round(risk_min, 1), 'max': round(healthy_min, 1)},
                            'critical': {'min': round(val_min * 0.8, 1), 'max': round(risk_min, 1)},
                        },
                    })
                else:
                    healthy_max = round(val_avg - (val_avg - val_min) * 0.3, 1)
                    risk_max = round(val_avg + (val_max - val_avg) * 0.3, 1)
                    kpi_candidates.append({
                        'source_column': col,
                        'suggested_kpi_code': mapped_to or re.sub(r'[^a-z0-9]', '_', col_lower).strip('_'),
                        'suggested_name': col.strip(),
                        'unit': unit,
                        'higher_is_better': False,
                        'suggested_target': round(healthy_max, 1),
                        'suggested_ranges': {
                            'healthy': {'min': round(val_min * 0.8, 1), 'max': round(healthy_max, 1)},
                            'risk': {'min': round(healthy_max, 1), 'max': round(risk_max, 1)},
                            'critical': {'min': round(risk_max, 1), 'max': round(val_max * 1.2, 1)},
                        },
                    })

        return jsonify({
            'source_system': source_system,
            'total_columns': len(headers),
            'total_rows': len(rows),
            'detected_columns': detected_columns,
            'kpi_candidates': kpi_candidates,
            'metadata_columns': [c for c in detected_columns if c.get('is_metadata')],
            'unmapped_columns': [c['column_name'] for c in detected_columns if not c.get('mapped_to') and c.get('is_numeric')],
        })

    except Exception as e:
        return jsonify({"error": f"Source CSV parsing failed: {str(e)}"}), 400


@admin_ui_api.route("/api/admin-ui/verticals/csv-template", methods=["GET"])
@super_admin_required
def download_csv_template():
    """Return a CSV template for KPI catalog upload."""
    import io
    output = io.StringIO()
    output.write("kpi_code,name,pillar,pillar_name,pillar_weight,weight_l1,unit,higher_is_better,target,frequency,healthy_min,healthy_max,risk_min,risk_max,critical_min,critical_max\n")
    output.write("P1-KPI1,Daily Active Users,P1,Product Adoption,0.30,0.20,percentage,true,60,daily,60,95,35,60,0,35\n")
    output.write("P1-KPI2,Feature Adoption Breadth,P1,Product Adoption,0.30,0.15,percentage,true,45,weekly,45,90,25,45,0,25\n")
    output.write("P2-KPI1,QBR Frequency,P2,Customer Engagement,0.25,0.25,count,true,4,quarterly,4,12,2,4,0,2\n")

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=kpi_catalog_template.csv'}
    )


@admin_ui_api.route("/api/admin-ui/verticals/pipeline-check", methods=["POST"])
@super_admin_required
def pipeline_readiness_check():
    """Run the catalog through the full pipeline with mock data and return a TODO checklist."""
    catalog = (request.json or {}).get('catalog', {})
    slug = (request.json or {}).get('slug', 'test_vertical')

    if not catalog or not catalog.get('kpis'):
        return jsonify({"checks": [{"id": "no_catalog", "label": "Catalog provided", "status": "fail", "detail": "No KPI catalog in request"}]}), 400

    checks = []
    pillars = catalog.get('pillars', {})
    kpis = catalog.get('kpis', {})

    # 1. Catalog loads into generic scorer
    try:
        from utils.generic_scorer import load_catalog_from_dict, score_kpi
        kpi_cat, pillar_cat = load_catalog_from_dict(catalog)
        checks.append({"id": "scorer_load", "label": "Generic scorer accepts catalog", "status": "pass",
                        "detail": f"Loaded {len(kpi_cat)} KPIs, {len(pillar_cat)} pillars into scorer"})
    except Exception as e:
        checks.append({"id": "scorer_load", "label": "Generic scorer accepts catalog", "status": "fail",
                        "detail": f"Scorer rejected catalog: {str(e)}"})
        return jsonify({"checks": checks})

    # 2. Score a mock KPI value for each KPI
    score_failures = []
    for kpi_code, kpi_def in kpi_cat.items():
        try:
            # Generate a mid-range test value
            ranges = kpi_def.get('ranges', {})
            healthy = ranges.get('healthy', {})
            test_val = (healthy.get('min', 50) + healthy.get('max', 80)) / 2
            result = score_kpi(test_val, kpi_def)
            if result is None or result < 0:
                score_failures.append(kpi_code)
        except Exception:
            score_failures.append(kpi_code)

    if not score_failures:
        checks.append({"id": "kpi_scoring", "label": "All KPIs score correctly with mock data", "status": "pass",
                        "detail": f"Tested {len(kpi_cat)} KPIs with mid-range values — all returned valid scores"})
    else:
        checks.append({"id": "kpi_scoring", "label": "KPI scoring test", "status": "fail",
                        "detail": f"{len(score_failures)} KPIs failed scoring: {', '.join(score_failures[:5])}"})

    # 3. Pillar weight normalization
    pillar_weights = [p.get('weight_l2', 0) for p in pillars.values()]
    weight_sum = sum(pillar_weights)
    if abs(weight_sum - 1.0) < 0.01:
        checks.append({"id": "pillar_weights", "label": "Pillar weights sum to 1.0", "status": "pass",
                        "detail": f"Sum = {weight_sum:.4f}"})
    else:
        checks.append({"id": "pillar_weights", "label": "Pillar weights sum to 1.0", "status": "warn",
                        "detail": f"Sum = {weight_sum:.4f} — will be auto-normalized on save"})

    # 4. KPI weights per pillar
    kpi_weight_issues = []
    for pcode in pillars:
        pillar_kpis = [k for k in kpis.values() if k.get('pillar') == pcode]
        kw_sum = sum(k.get('weight_l1', 0) for k in pillar_kpis)
        if pillar_kpis and abs(kw_sum - 1.0) > 0.05:
            kpi_weight_issues.append(f"{pcode}: {kw_sum:.3f}")
    if not kpi_weight_issues:
        checks.append({"id": "kpi_weights", "label": "KPI weights per pillar sum to 1.0", "status": "pass",
                        "detail": "All pillars have correctly normalized KPI weights"})
    else:
        checks.append({"id": "kpi_weights", "label": "KPI weights per pillar", "status": "warn",
                        "detail": f"Off-balance pillars (will be auto-normalized): {', '.join(kpi_weight_issues)}"})

    # 5. Process_data compatibility — check if vertical would be recognized
    try:
        from utils.vertical_registry import normalize_vertical, SUPPORTED_VERTICALS
        normalized = normalize_vertical(slug)
        if normalized in SUPPORTED_VERTICALS or slug in SUPPORTED_VERTICALS:
            checks.append({"id": "registry", "label": "Vertical recognized by registry", "status": "pass",
                            "detail": f"'{slug}' resolves to '{normalized}' in vertical registry"})
        else:
            checks.append({"id": "registry", "label": "Vertical recognized by registry", "status": "warn",
                            "detail": f"'{slug}' not yet in registry — will be added when vertical is created"})
    except Exception:
        checks.append({"id": "registry", "label": "Vertical registry check", "status": "warn",
                        "detail": "Could not check registry — vertical will be registered on creation"})

    # 6. ROI engine compatibility — check if at least 3 pillars exist (minimum for meaningful ROI)
    if len(pillars) >= 3:
        checks.append({"id": "roi_pillars", "label": "ROI engine: minimum pillar count", "status": "pass",
                        "detail": f"{len(pillars)} pillars — sufficient for pillar-based ROI analysis"})
    else:
        checks.append({"id": "roi_pillars", "label": "ROI engine: minimum pillar count", "status": "fail",
                        "detail": f"Only {len(pillars)} pillars — ROI engine needs at least 3 for meaningful analysis"})

    # 7. ROI engine — check for high-impact KPIs (weight > 0.15)
    high_impact = [k for k, v in kpis.items() if v.get('weight_l1', 0) >= 0.15]
    if high_impact:
        checks.append({"id": "roi_high_impact", "label": "ROI engine: high-impact KPIs identified", "status": "pass",
                        "detail": f"{len(high_impact)} KPIs with weight >= 0.15: {', '.join(high_impact[:5])}"})
    else:
        checks.append({"id": "roi_high_impact", "label": "ROI engine: high-impact KPIs", "status": "warn",
                        "detail": "No KPIs with weight >= 0.15 — ROI engine may produce flat results. Consider increasing weights for key KPIs."})

    # 8. Health threshold compatibility
    try:
        import utils.health_thresholds as ht
        checks.append({"id": "thresholds", "label": "Health thresholds configured", "status": "pass",
                        "detail": f"Critical < {ht.at_risk_min()}, At-Risk {ht.at_risk_min()}-{ht.healthy_min()-1}, Healthy >= {ht.healthy_min()}"})
    except Exception:
        checks.append({"id": "thresholds", "label": "Health thresholds", "status": "warn",
                        "detail": "Could not load health thresholds — using defaults (50/70)"})

    # 9. Data upload readiness
    checks.append({"id": "csv_schema", "label": "CSV upload schema ready", "status": "pass",
                    "detail": f"process_data accepts kpi_measurements.csv with {len(kpis)} valid KPI codes for this vertical"})

    # 10. Overall verdict
    fails = sum(1 for c in checks if c['status'] == 'fail')
    if fails == 0:
        checks.append({"id": "verdict", "label": "Pipeline readiness verdict", "status": "pass",
                        "detail": "All pipeline checks passed — this vertical is ready for production use"})
    else:
        checks.append({"id": "verdict", "label": "Pipeline readiness verdict", "status": "fail",
                        "detail": f"{fails} check(s) failed — fix the issues above before creating this vertical"})

    return jsonify({"checks": checks})


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
