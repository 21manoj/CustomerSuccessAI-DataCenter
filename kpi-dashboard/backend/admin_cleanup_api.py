#!/usr/bin/env python3
"""
Admin Cleanup API
Post-load-test cleanup endpoints for purging customer data

Endpoints:
  POST /api/admin/cleanup/customer/<customer_id> - Complete customer data deletion
  POST /api/accounts/<account_id>/archive - Soft delete (mark archived)
  POST /api/accounts/<account_id>/delete - Hard delete with cascade verification
"""

from flask import Blueprint, request, jsonify
from models import db, Customer, Account, User, AccountNote, AccountSnapshot
from models import KPI, KPIScore, PillarScore, HealthScore, DC2SKPI
from models import QualitativeSignal, HealthTrend, KPIUpload
from models import PlaybookTrigger, PlaybookExecution, PlaybookReport
from models import Product, ActivityLog, CustomerConfig
from models import CustomerWorkflowConfig, FeatureToggle
from models import ContextNode, ContextEdge
# V2 models added post-initial (may not exist in all deployments)
try:
    from models import PlaybookExecutionV2
    HAS_PB_V2 = True
except ImportError:
    HAS_PB_V2 = False
try:
    from models import PlaybookTask
    HAS_PB_TASK = True
except ImportError:
    HAS_PB_TASK = False
try:
    from models import Notification
    HAS_NOTIFICATION = True
except ImportError:
    HAS_NOTIFICATION = False
from auth_middleware import get_current_customer_id
from sqlalchemy import and_, or_, func, text
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Optional imports
try:
    from models import QueryAudit
    HAS_QUERY_AUDIT = True
except ImportError:
    HAS_QUERY_AUDIT = False

try:
    from models import KPIReferenceRange
    HAS_KPI_REFERENCE_RANGE = True
except ImportError:
    HAS_KPI_REFERENCE_RANGE = False

try:
    from models import ActionEconomics
    HAS_ACTION_ECONOMICS = True
except ImportError:
    HAS_ACTION_ECONOMICS = False

logger = logging.getLogger(__name__)

admin_cleanup_api = Blueprint('admin_cleanup_api', __name__)


@admin_cleanup_api.route('/api/admin/cleanup/customer/<int:customer_id>', methods=['POST'])
def cleanup_customer(customer_id):
    """
    Complete customer data deletion (FK-safe order)

    Request body:
    {
        "dry_run": true/false,
        "confirm": true  # Required for actual deletion
    }

    Returns:
    {
        "status": "success",
        "tables_deleted": 15,
        "rows_deleted": 2145,
        "duration_seconds": 12.5,
        "verification": {
            "orphan_rows": 0,
            "orphan_details": {}
        }
    }
    """
    try:
        data = request.json or {}
        dry_run = data.get('dry_run', False)
        confirm = data.get('confirm', False)

        # Require confirmation for actual deletion
        if not dry_run and not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Actual deletion requires confirm: true in request body'
            }), 400

        logger.info(f"🧹 Cleanup customer {customer_id} (dry_run={dry_run})")

        start_time = datetime.now()
        deletion_count = {}
        errors = []

        # ================================================================
        # GET CUSTOMER + ACCOUNTS FIRST (for verification)
        # ================================================================
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': f'Customer {customer_id} not found'}), 404

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.account_id for a in accounts]
        logger.info(f"  Found {len(accounts)} accounts to clean")

        # ================================================================
        # DELETION ORDER (FK-safe)
        # ================================================================
        deletions = []

        if HAS_QUERY_AUDIT:
            deletions.append(('query_audits', lambda: QueryAudit.query.filter_by(customer_id=customer_id)))

        deletions.extend([
            ('account_notes', lambda: AccountNote.query.filter_by(customer_id=customer_id)),
            ('account_snapshots', lambda: AccountSnapshot.query.filter_by(customer_id=customer_id)),
        ])

        if HAS_ACTION_ECONOMICS:
            deletions.append(('action_economics', lambda: ActionEconomics.query.filter_by(customer_id=customer_id)))

        # V2 models (FK to customers — must delete before customer record)
        if HAS_PB_V2:
            deletions.append(('playbook_executions_v2', lambda: PlaybookExecutionV2.query.filter_by(customer_id=customer_id)))
        if HAS_PB_TASK:
            deletions.append(('playbook_tasks', lambda: PlaybookTask.query.filter_by(customer_id=customer_id)))
        if HAS_NOTIFICATION:
            deletions.append(('notifications', lambda: Notification.query.filter_by(customer_id=customer_id)))
        # API keys — raw SQL (no ORM model, just purge before customer delete)
        try:
            db.session.execute(text("DELETE FROM customer_api_keys WHERE customer_id = :cid"), {"cid": customer_id})
        except Exception:
            pass

        deletions.extend([
            ('playbook_reports', lambda: PlaybookReport.query.filter_by(customer_id=customer_id)),
            ('playbook_executions', lambda: PlaybookExecution.query.filter_by(customer_id=customer_id)),
            ('playbook_triggers', lambda: PlaybookTrigger.query.filter_by(customer_id=customer_id)),
            ('customer_workflow_configs', lambda: CustomerWorkflowConfig.query.filter_by(customer_id=customer_id)),
            ('feature_toggles', lambda: FeatureToggle.query.filter_by(customer_id=customer_id)),
        ])

        if HAS_KPI_REFERENCE_RANGE:
            deletions.append(('kpi_reference_ranges', lambda: KPIReferenceRange.query.filter_by(customer_id=customer_id)))

        if account_ids:
            deletions.extend([
                ('health_scores', lambda: HealthScore.query.filter(HealthScore.account_id.in_(account_ids))),
                ('pillar_scores', lambda: PillarScore.query.filter(PillarScore.account_id.in_(account_ids))),
                ('kpi_scores', lambda: KPIScore.query.filter(KPIScore.account_id.in_(account_ids))),
                ('qualitative_signals', lambda: QualitativeSignal.query.filter(QualitativeSignal.account_id.in_(account_ids))),
                ('dc2s_kpis', lambda: DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids))),
                ('kpis', lambda: KPI.query.filter(KPI.account_id.in_(account_ids))),
            ])

        # Context graph: edges FK to nodes, nodes FK to accounts — delete before accounts
        deletions.extend([
            ('context_edges', lambda: ContextEdge.query.filter_by(customer_id=customer_id)),
            ('context_nodes', lambda: ContextNode.query.filter_by(customer_id=customer_id)),
        ])

        deletions.extend([
            ('health_trends', lambda: HealthTrend.query.filter_by(customer_id=customer_id)),
            ('kpi_uploads', lambda: KPIUpload.query.filter_by(customer_id=customer_id)),
            ('products', lambda: Product.query.filter_by(customer_id=customer_id)),
            ('accounts', lambda: Account.query.filter_by(customer_id=customer_id)),
            ('activity_logs', lambda: ActivityLog.query.filter_by(customer_id=customer_id)),
            ('users', lambda: User.query.filter_by(customer_id=customer_id)),
            ('customer_configs', lambda: CustomerConfig.query.filter_by(customer_id=customer_id)),
        ])

        # Execute deletions
        for table_info in deletions:
            if table_info is None:
                continue

            table_name, query_func = table_info
            try:
                query = query_func()
                if query is None:
                    continue

                count = query.count()
                deletion_count[table_name] = count

                if count > 0:
                    if not dry_run:
                        query.delete()
                        logger.info(f"  ✓ Deleted {count} rows from {table_name}")
                    else:
                        logger.info(f"  (DRY RUN) Would delete {count} rows from {table_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  Error deleting from {table_name}: {e}")
                errors.append(f"{table_name}: {str(e)}")

        # Catch-all: delete from ALL tables with FK to customers or accounts.
        # Queries information_schema so new tables are handled automatically.
        if not dry_run:
            # Get account IDs for account-level FK cleanup
            acct_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()]

            # Account-level FK tables (reference accounts.account_id)
            if acct_ids:
                try:
                    acct_fk_tables = db.session.execute(text("""
                        SELECT DISTINCT tc.table_name, kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage ccu
                          ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND ccu.table_name = 'accounts'
                          AND tc.table_name != 'accounts'
                    """)).fetchall()
                    aid_list = ",".join(str(a) for a in acct_ids)
                    for tbl, col in acct_fk_tables:
                        try:
                            r = db.session.execute(text(f"DELETE FROM {tbl} WHERE {col} IN ({aid_list})"))
                            if r.rowcount > 0:
                                logger.info(f"  ✓ FK catch-all (account): deleted {r.rowcount} from {tbl}")
                        except Exception:
                            pass
                except Exception:
                    pass

            # Customer-level FK tables (reference customers.customer_id)
            try:
                cust_fk_tables = db.session.execute(text("""
                    SELECT DISTINCT tc.table_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                      ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND ccu.table_name = 'customers'
                      AND tc.table_name != 'customers'
                """)).fetchall()
                for (tbl,) in cust_fk_tables:
                    try:
                        r = db.session.execute(
                            text(f"DELETE FROM {tbl} WHERE customer_id = :cid"),
                            {"cid": customer_id}
                        )
                        if r.rowcount > 0:
                            logger.info(f"  ✓ FK catch-all: deleted {r.rowcount} from {tbl}")
                    except Exception:
                        pass
            except Exception as fk_err:
                logger.warning(f"  FK catch-all scan failed: {fk_err}")

        # Delete customer itself (raw SQL — ORM .delete() can trigger FK cascade errors)
        if not dry_run:
            db.session.execute(text(
                "DELETE FROM customers WHERE customer_id = :cid"
            ), {"cid": customer_id})
            logger.info(f"  ✓ Deleted customer {customer_id}")

        # Commit if not dry-run
        if not dry_run:
            try:
                db.session.commit()
                logger.info(f"✅ Cleanup committed")
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Commit failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': 'Commit failed',
                    'error': str(e)
                }), 500
        else:
            db.session.rollback()  # Rollback dry-run changes

        # ================================================================
        # FILESYSTEM CLEANUP (journey files, CSVs, generated scripts)
        # ================================================================
        files_removed = False
        verticals_base = Path(__file__).parent / 'verticals'
        # Customer directories follow pattern: customer{id}-dc2_s
        for pattern in [f'customer{customer_id}-*', f'customer{customer_id}_*']:
            for cust_dir in verticals_base.glob(pattern):
                if cust_dir.is_dir():
                    if dry_run:
                        logger.info(f"  (DRY RUN) Would remove directory: {cust_dir}")
                        deletion_count['filesystem'] = deletion_count.get('filesystem', 0) + 1
                    else:
                        try:
                            shutil.rmtree(cust_dir)
                            logger.info(f"  ✓ Removed customer directory: {cust_dir}")
                            deletion_count['filesystem'] = deletion_count.get('filesystem', 0) + 1
                            files_removed = True
                        except Exception as e:
                            logger.warning(f"  Failed to remove {cust_dir}: {e}")
                            errors.append(f"Filesystem cleanup: {e}")

        # ================================================================
        # VERIFICATION (Check for orphans)
        # ================================================================
        orphan_rows = 0
        orphan_details = {}

        # Only verify if actual deletion happened
        if not dry_run and account_ids:
            # Check for any remaining rows with these account_ids
            try:
                dc2s_orphans = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).count()
                if dc2s_orphans > 0:
                    orphan_details['dc2s_kpis'] = dc2s_orphans
                    orphan_rows += dc2s_orphans

                health_orphans = HealthScore.query.filter(HealthScore.account_id.in_(account_ids)).count()
                if health_orphans > 0:
                    orphan_details['health_scores'] = health_orphans
                    orphan_rows += health_orphans

                logger.info(f"  Verification: {orphan_rows} orphan rows found")
            except Exception as e:
                logger.warning(f"  Verification error: {e}")

        duration = (datetime.now() - start_time).total_seconds()
        total_rows = sum(deletion_count.values())

        return jsonify({
            'status': 'success',
            'message': f"{'DRY RUN: ' if dry_run else ''}Cleanup complete",
            'dry_run': dry_run,
            'customer_id': customer_id,
            'tables': list(deletion_count.keys()),
            'tables_deleted': len(deletion_count),
            'rows_deleted': total_rows,
            'rows_by_table': deletion_count,
            'duration_seconds': round(duration, 2),
            'errors': errors,
            'verification': {
                'status': 'clean' if orphan_rows == 0 else 'orphans_found',
                'orphan_rows': orphan_rows,
                'orphan_details': orphan_details
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@admin_cleanup_api.route('/api/accounts/<int:account_id>/archive', methods=['POST'])
def archive_account(account_id):
    """
    Soft-delete account (mark as archived)

    Sets account_status = 'archived', keeps data for auditing
    """
    try:
        customer_id = get_current_customer_id()
        account = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        account.account_status = 'archived'
        account.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"✓ Archived account {account_id}")

        return jsonify({
            'status': 'success',
            'message': f'Account {account_id} archived',
            'account_id': account_id,
            'archived_at': account.updated_at.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"❌ Archive error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_cleanup_api.route('/api/accounts/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """
    Hard-delete account and all related data

    Requires:
    {
        "confirm": true
    }
    """
    try:
        data = request.json or {}
        if not data.get('confirm'):
            return jsonify({
                'error': 'Confirmation required',
                'message': 'Send {"confirm": true} to delete'
            }), 400

        customer_id = get_current_customer_id()
        account = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Delete all account data in FK order
        deletion_count = {}

        # Context graph: edges don't have account_id, so delete via node IDs
        node_ids = db.session.query(ContextNode.node_id).filter_by(account_id=account_id).all()
        node_id_list = [n[0] for n in node_ids]
        if node_id_list:
            edge_count = ContextEdge.query.filter(
                or_(ContextEdge.from_node_id.in_(node_id_list),
                    ContextEdge.to_node_id.in_(node_id_list))
            ).delete(synchronize_session='fetch')
            if edge_count:
                deletion_count['context_edges'] = edge_count
        node_count = ContextNode.query.filter_by(account_id=account_id).delete()
        if node_count:
            deletion_count['context_nodes'] = node_count

        # Standard tables in FK order
        tables_to_delete = [
            ('kpi_scores', KPIScore),
            ('pillar_scores', PillarScore),
            ('health_scores', HealthScore),
            ('dc2s_kpis', DC2SKPI),
            ('qualitative_signals', QualitativeSignal),
            ('health_trends', HealthTrend),
            ('kpis', KPI),
            ('products', Product),
            ('account_notes', AccountNote),
            ('account_snapshots', AccountSnapshot),
        ]

        for table_name, model in tables_to_delete:
            count = model.query.filter_by(account_id=account_id).delete()
            if count > 0:
                deletion_count[table_name] = count

        # Delete account last
        db.session.delete(account)
        deletion_count['accounts'] = 1

        db.session.commit()
        logger.info(f"✓ Deleted account {account_id} and {sum(deletion_count.values())} related rows")

        return jsonify({
            'status': 'success',
            'message': f'Account {account_id} deleted',
            'account_id': account_id,
            'rows_deleted': sum(deletion_count.values()),
            'rows_by_table': deletion_count
        }), 200

    except Exception as e:
        logger.error(f"❌ Delete error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
