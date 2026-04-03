"""
Backup & Restore API  (replaces stale restore_db_from_backup.py + rehydration_api.py)
=======================================================================================

Gaps closed vs. old rehydration_api.py:
  ✅  CustomerConfig  — pillar weights, KPI weights, signal_type_weights, Wizard C calibrations
  ✅  FeatureToggles  — per-customer feature flags
  ✅  ContextNodes + ContextEdges  — full context graph
  ✅  HealthScores    — including kpi_only_score and composite_score
  ✅  JSON format     — no dependency on Excel/openpyxl
  ✅  ActivityLog     — every export/import event is audited
  ✅  Integrity check  — verify endpoint counts rows after import

Endpoints:
  POST  /api/backup/export          — export all customer data as JSON download
  POST  /api/backup/import          — restore from JSON export (replace mode)
  GET   /api/backup/verify          — integrity check: row counts per table
  GET   /api/backup/history         — list past export/import events (ActivityLog)
"""

import json
import io
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, Response
from sqlalchemy import text

from extensions import db
from auth_middleware import get_current_customer_id, get_current_user_id
from models import (
    Customer, CustomerConfig, Account, FeatureToggle, ActivityLog,
)

logger = logging.getLogger(__name__)

backup_restore_api = Blueprint('backup_restore_api', __name__, url_prefix='/api/backup')

# Schema version — bump when export format changes
_SCHEMA_VERSION = '2.0'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_event(customer_id, action_type, description, status='success', details=None):
    """Persist an export/import event to ActivityLog."""
    try:
        user_id = get_current_user_id()
        db.session.add(ActivityLog(
            customer_id=customer_id,
            user_id=user_id,
            action_type=action_type,
            action_category='backup',
            action_description=description,
            resource_type='customer',
            resource_id=str(customer_id),
            status=status,
            details=details or {},
            ip_address=request.remote_addr,
        ))
        db.session.commit()
    except Exception as e:
        logger.warning(f"[backup] activity log failed (non-fatal): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _row_to_dict(row):
    """Convert a SQLAlchemy Row or model instance to a plain dict."""
    if hasattr(row, '__table__'):
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}
    return dict(row._mapping)


def _safe_float(val):
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# POST /api/backup/export
# ---------------------------------------------------------------------------

@backup_restore_api.route('/export', methods=['POST'])
def export_customer_data():
    """Export all customer data as a JSON file download.

    Covers:
      - Customer metadata
      - CustomerConfig (weights, KPI weights, signal weights)
      - FeatureToggles
      - Accounts
      - health_scores (kpi_only_score, composite_score)
      - dc2s_kpis (KPI measurements)
      - context_nodes + context_edges

    Body (JSON): { "customer_id": <int> }  — required for super-admins.
    Falls back to the session customer_id for regular users.
    """
    body = request.get_json(silent=True) or {}
    # Super-admins pass customer_id in the body; regular users use their session
    customer_id = body.get('customer_id') or get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    try:
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        payload = {
            'schema_version': _SCHEMA_VERSION,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
        }

        # ── Customer metadata ──────────────────────────────────────────
        payload['customer'] = {
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name,
            'domain': getattr(customer, 'domain', None),
            'industry': getattr(customer, 'industry', None),
            'vertical': getattr(customer, 'vertical', None),
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
        }

        # ── CustomerConfig (weights + DNA) ─────────────────────────────
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        payload['customer_config'] = None
        if config:
            payload['customer_config'] = {
                'dc2s_pillar_weights': config.dc2s_pillar_weights,
                'dc2s_kpi_weights': config.dc2s_kpi_weights,
                'signal_type_weights': getattr(config, 'signal_type_weights', None),
                'wizard_c_last_run': (
                    getattr(config, 'wizard_c_last_run', None).isoformat()
                    if getattr(config, 'wizard_c_last_run', None) else None
                ),
                'dc2s_config': getattr(config, 'dc2s_config', None),
            }

        # ── FeatureToggles ─────────────────────────────────────────────
        toggles = FeatureToggle.query.filter_by(customer_id=customer_id).all()
        payload['feature_toggles'] = [
            {
                'feature_name': t.feature_name,
                'is_enabled': t.enabled,
                'updated_at': t.updated_at.isoformat() if hasattr(t, 'updated_at') and t.updated_at else None,
            }
            for t in toggles
        ]

        # ── Accounts ──────────────────────────────────────────────────
        accounts_rows = db.session.execute(
            text("SELECT * FROM accounts WHERE customer_id = :cid ORDER BY account_id"),
            {'cid': customer_id}
        ).fetchall()
        payload['accounts'] = [dict(r._mapping) for r in accounts_rows]

        # ── HealthScores (incl. kpi_only_score, composite_score) ──────
        hs_rows = db.session.execute(
            text("""
                SELECT hs.*
                FROM health_scores hs
                JOIN accounts a ON hs.account_id = a.account_id
                WHERE a.customer_id = :cid
                ORDER BY hs.account_id, hs.measurement_month
            """),
            {'cid': customer_id}
        ).fetchall()
        payload['health_scores'] = []
        for r in hs_rows:
            d = dict(r._mapping)
            # Coerce Decimal → float for JSON serialisation
            for key in ('health_score', 'kpi_only_score', 'composite_score',
                        'p1_score', 'p2_score', 'p3_score', 'p4_score', 'p5_score'):
                if key in d:
                    d[key] = _safe_float(d[key])
            payload['health_scores'].append(d)

        # ── KPI Measurements ──────────────────────────────────────────
        kpi_rows = db.session.execute(
            text("""
                SELECT k.*
                FROM dc2s_kpis k
                JOIN accounts a ON k.account_id = a.account_id
                WHERE a.customer_id = :cid
                ORDER BY k.account_id, k.measured_at
            """),
            {'cid': customer_id}
        ).fetchall()
        payload['kpi_measurements'] = [dict(r._mapping) for r in kpi_rows]

        # ── Context Graph Nodes ────────────────────────────────────────
        try:
            cn_rows = db.session.execute(
                text("""
                    SELECT cn.*
                    FROM context_nodes cn
                    JOIN accounts a ON cn.account_id = a.account_id
                    WHERE a.customer_id = :cid
                    ORDER BY cn.id
                """),
                {'cid': customer_id}
            ).fetchall()
            payload['context_nodes'] = [dict(r._mapping) for r in cn_rows]
        except Exception:
            db.session.rollback()
            payload['context_nodes'] = []

        # ── Context Graph Edges ────────────────────────────────────────
        try:
            ce_rows = db.session.execute(
                text("""
                    SELECT ce.*
                    FROM context_edges ce
                    JOIN context_nodes cn ON ce.source_node_id = cn.id
                    JOIN accounts a ON cn.account_id = a.account_id
                    WHERE a.customer_id = :cid
                    ORDER BY ce.id
                """),
                {'cid': customer_id}
            ).fetchall()
            payload['context_edges'] = [dict(r._mapping) for r in ce_rows]
        except Exception:
            db.session.rollback()
            payload['context_edges'] = []

        # ── Serialise datetimes ────────────────────────────────────────
        def _default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        json_bytes = json.dumps(payload, default=_default, indent=2).encode('utf-8')

        _log_event(
            customer_id, 'backup_export',
            f"Exported {len(payload['accounts'])} accounts, "
            f"{len(payload['health_scores'])} health scores, "
            f"{len(payload['context_nodes'])} graph nodes",
            details={
                'accounts': len(payload['accounts']),
                'health_scores': len(payload['health_scores']),
                'kpi_measurements': len(payload['kpi_measurements']),
                'context_nodes': len(payload['context_nodes']),
                'context_edges': len(payload['context_edges']),
            }
        )

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cspulse_backup_cid{customer_id}_{ts}.json"
        return Response(
            io.BytesIO(json_bytes),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )

    except Exception as e:
        logger.error(f"[backup] export failed for customer {customer_id}: {e}", exc_info=True)
        _log_event(customer_id, 'backup_export', f"Export FAILED: {str(e)[:200]}", status='error')
        return jsonify({'error': 'Export failed. Please try again or contact support.'}), 500


# ---------------------------------------------------------------------------
# POST /api/backup/import
# ---------------------------------------------------------------------------

@backup_restore_api.route('/import', methods=['POST'])
def import_customer_data():
    """Restore customer data from a JSON export (replace mode).

    Security: validates that the export's customer_id matches the authenticated
    user's customer_id (prevents cross-tenant restore).

    Restores:
      - CustomerConfig (weights)
      - FeatureToggles
      - Accounts
      - HealthScores (including kpi_only_score)
      - KPI measurements
      - Context graph nodes + edges
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded. Attach the JSON backup as form field "file".'}), 400

    f = request.files['file']
    if not f.filename.endswith('.json'):
        return jsonify({'error': 'File must be a .json backup export'}), 400

    try:
        data = json.load(f)
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {e}'}), 400

    # ── Cross-tenant guard ─────────────────────────────────────────────────
    export_cid = data.get('customer_id')
    if export_cid and int(export_cid) != customer_id:
        return jsonify({
            'error': f'Export belongs to customer {export_cid}, not {customer_id}. '
                     'Cannot restore across customers.'
        }), 403

    schema_version = data.get('schema_version', '1.0')
    if schema_version not in ('2.0',):
        return jsonify({'error': f'Unsupported backup schema version: {schema_version}. '
                                 f'Expected 2.0'}), 400

    counts = {}
    try:
        # ── CustomerConfig ─────────────────────────────────────────────
        cfg_data = data.get('customer_config') or {}
        if cfg_data:
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if not config:
                config = CustomerConfig(customer_id=customer_id)
                db.session.add(config)
            config.dc2s_pillar_weights = cfg_data.get('dc2s_pillar_weights')
            config.dc2s_kpi_weights = cfg_data.get('dc2s_kpi_weights')
            if hasattr(config, 'signal_type_weights'):
                config.signal_type_weights = cfg_data.get('signal_type_weights')
            if hasattr(config, 'dc2s_config'):
                config.dc2s_config = cfg_data.get('dc2s_config')
            db.session.flush()
            counts['customer_config'] = 'restored'

        # ── FeatureToggles ─────────────────────────────────────────────
        toggles_data = data.get('feature_toggles', [])
        FeatureToggle.query.filter_by(customer_id=customer_id).delete()
        for t in toggles_data:
            db.session.add(FeatureToggle(
                customer_id=customer_id,
                feature_name=t['feature_name'],
                enabled=t.get('is_enabled', False),
            ))
        db.session.flush()
        counts['feature_toggles'] = len(toggles_data)

        # ── Accounts ──────────────────────────────────────────────────
        accounts_data = data.get('accounts', [])
        # Build id map: old account_id → new after upsert
        existing_account_ids = {
            r[0] for r in db.session.execute(
                text("SELECT account_id FROM accounts WHERE customer_id = :cid"),
                {'cid': customer_id}
            ).fetchall()
        }
        import_account_ids = {a['account_id'] for a in accounts_data if 'account_id' in a}
        # Delete accounts not in the export
        to_delete = existing_account_ids - import_account_ids
        if to_delete:
            db.session.execute(
                text("DELETE FROM accounts WHERE account_id IN :ids"),
                {'ids': tuple(to_delete) if len(to_delete) > 1 else f"({next(iter(to_delete))})"}
            )
        # Upsert accounts
        for acc in accounts_data:
            cols = ', '.join(acc.keys())
            placeholders = ', '.join(f':{k}' for k in acc.keys())
            updates = ', '.join(f'{k}=EXCLUDED.{k}' for k in acc.keys() if k != 'account_id')
            db.session.execute(
                text(f"""
                    INSERT INTO accounts ({cols})
                    VALUES ({placeholders})
                    ON CONFLICT (account_id) DO UPDATE SET {updates}
                """),
                acc
            )
        db.session.flush()
        counts['accounts'] = len(accounts_data)

        # ── HealthScores ───────────────────────────────────────────────
        hs_data = data.get('health_scores', [])
        if hs_data:
            # Delete existing health scores for this customer's accounts
            db.session.execute(
                text("""
                    DELETE FROM health_scores
                    WHERE account_id IN (
                        SELECT account_id FROM accounts WHERE customer_id = :cid
                    )
                """),
                {'cid': customer_id}
            )
            for hs in hs_data:
                cols = [c for c in hs.keys() if c != 'id']
                col_str = ', '.join(cols)
                ph_str = ', '.join(f':{c}' for c in cols)
                db.session.execute(
                    text(f"INSERT INTO health_scores ({col_str}) VALUES ({ph_str})"),
                    {c: hs[c] for c in cols}
                )
        db.session.flush()
        counts['health_scores'] = len(hs_data)

        # ── KPI Measurements ──────────────────────────────────────────
        kpi_data = data.get('kpi_measurements', [])
        if kpi_data:
            db.session.execute(
                text("""
                    DELETE FROM dc2s_kpis
                    WHERE account_id IN (
                        SELECT account_id FROM accounts WHERE customer_id = :cid
                    )
                """),
                {'cid': customer_id}
            )
            for row in kpi_data:
                cols = [c for c in row.keys() if c != 'id']
                col_str = ', '.join(cols)
                ph_str = ', '.join(f':{c}' for c in cols)
                db.session.execute(
                    text(f"INSERT INTO dc2s_kpis ({col_str}) VALUES ({ph_str})"),
                    {c: row[c] for c in cols}
                )
        db.session.flush()
        counts['kpi_measurements'] = len(kpi_data)

        # ── Context Graph ──────────────────────────────────────────────
        nodes_data = data.get('context_nodes', [])
        edges_data = data.get('context_edges', [])
        try:
            db.session.execute(
                text("""
                    DELETE FROM context_edges
                    WHERE source_node_id IN (
                        SELECT cn.id FROM context_nodes cn
                        JOIN accounts a ON cn.account_id = a.account_id
                        WHERE a.customer_id = :cid
                    )
                """),
                {'cid': customer_id}
            )
            db.session.execute(
                text("""
                    DELETE FROM context_nodes
                    WHERE account_id IN (
                        SELECT account_id FROM accounts WHERE customer_id = :cid
                    )
                """),
                {'cid': customer_id}
            )
            for node in nodes_data:
                cols = [c for c in node.keys() if c != 'id']
                col_str = ', '.join(cols)
                ph_str = ', '.join(f':{c}' for c in cols)
                db.session.execute(
                    text(f"INSERT INTO context_nodes ({col_str}) VALUES ({ph_str})"),
                    {c: node[c] for c in cols}
                )
            for edge in edges_data:
                cols = [c for c in edge.keys() if c != 'id']
                col_str = ', '.join(cols)
                ph_str = ', '.join(f':{c}' for c in cols)
                db.session.execute(
                    text(f"INSERT INTO context_edges ({col_str}) VALUES ({ph_str})"),
                    {c: edge[c] for c in cols}
                )
            counts['context_nodes'] = len(nodes_data)
            counts['context_edges'] = len(edges_data)
        except Exception as ctx_err:
            logger.warning(f"[backup] context graph restore skipped: {ctx_err}")
            counts['context_nodes'] = 'skipped'
            counts['context_edges'] = 'skipped'

        db.session.commit()

        _log_event(
            customer_id, 'backup_import',
            f"Restored {counts.get('accounts', 0)} accounts, "
            f"{counts.get('health_scores', 0)} health scores from {f.filename}",
            details={'counts': counts, 'source_file': f.filename}
        )

        return jsonify({
            'status': 'success',
            'message': 'Restore complete',
            'counts': counts,
            'exported_at': data.get('exported_at'),
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"[backup] import failed for customer {customer_id}: {e}", exc_info=True)
        _log_event(customer_id, 'backup_import', f"Import FAILED: {str(e)[:200]}", status='error')
        return jsonify({'error': f'Restore failed: {str(e)[:300]}'}), 500


# ---------------------------------------------------------------------------
# GET /api/backup/verify
# ---------------------------------------------------------------------------

@backup_restore_api.route('/verify', methods=['GET'])
def verify_customer_data():
    """Integrity check: row counts per table for the current customer.

    Query param: customer_id (required for super-admins, else session value used).
    """
    customer_id = request.args.get('customer_id', type=int) or get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    try:
        def count(q, params=None):
            return db.session.execute(text(q), params or {}).scalar() or 0

        results = {
            'accounts': count(
                "SELECT COUNT(*) FROM accounts WHERE customer_id = :cid",
                {'cid': customer_id}
            ),
            'health_scores': count(
                """SELECT COUNT(*) FROM health_scores hs
                   JOIN accounts a ON hs.account_id = a.account_id
                   WHERE a.customer_id = :cid""",
                {'cid': customer_id}
            ),
            'kpi_measurements': count(
                """SELECT COUNT(*) FROM dc2s_kpis k
                   JOIN accounts a ON k.account_id = a.account_id
                   WHERE a.customer_id = :cid""",
                {'cid': customer_id}
            ),
            'context_nodes': 0,
            'context_edges': 0,
        }

        try:
            results['context_nodes'] = count(
                """SELECT COUNT(*) FROM context_nodes cn
                   JOIN accounts a ON cn.account_id = a.account_id
                   WHERE a.customer_id = :cid""",
                {'cid': customer_id}
            )
            results['context_edges'] = count(
                """SELECT COUNT(*) FROM context_edges ce
                   JOIN context_nodes cn ON ce.source_node_id = cn.id
                   JOIN accounts a ON cn.account_id = a.account_id
                   WHERE a.customer_id = :cid""",
                {'cid': customer_id}
            )
        except Exception:
            # context_graph tables may not exist — rollback to keep session healthy
            db.session.rollback()

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        results['customer_config'] = {
            'has_pillar_weights': bool(config and config.dc2s_pillar_weights),
            'has_kpi_weights': bool(config and config.dc2s_kpi_weights),
        }
        results['feature_toggles'] = count(
            "SELECT COUNT(*) FROM feature_toggles WHERE customer_id = :cid",
            {'cid': customer_id}
        )

        # kpi_only_score coverage
        results['kpi_only_score_coverage'] = count(
            """SELECT COUNT(*) FROM health_scores hs
               JOIN accounts a ON hs.account_id = a.account_id
               WHERE a.customer_id = :cid AND hs.kpi_only_score IS NOT NULL""",
            {'cid': customer_id}
        )

        return jsonify({
            'status': 'ok',
            'customer_id': customer_id,
            'counts': results,
            'verified_at': datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        logger.error(f"[backup] verify failed: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/backup/history
# ---------------------------------------------------------------------------

@backup_restore_api.route('/history', methods=['GET'])
def backup_history():
    """List past export/import events for a customer.

    Query param: customer_id (required for super-admins, else session value used).
    """
    customer_id = request.args.get('customer_id', type=int) or get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    limit = request.args.get('limit', 20, type=int)

    try:
        logs = (
            ActivityLog.query
            .filter_by(customer_id=customer_id, action_category='backup')
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .all()
        )
        events = [
            {
                'id': l.id,
                'action_type': l.action_type,
                'description': l.action_description,
                'status': l.status,
                'details': l.details or {},
                'created_at': l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
        return jsonify({'events': events, 'total': len(events)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
