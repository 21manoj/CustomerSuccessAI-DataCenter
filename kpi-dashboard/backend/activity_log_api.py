#!/usr/bin/env python3
"""
Activity Log API
Query and manage activity logs for governance
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id, _is_admin_user
from extensions import db
from models import ActivityLog, User, Customer
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc
import logging

logger = logging.getLogger(__name__)

activity_log_api = Blueprint('activity_log_api', __name__)

@activity_log_api.route('/api/activity-logs', methods=['GET'])
def get_activity_logs():
    """Get activity logs for the current customer with filtering options"""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get query parameters
        action_type = request.args.get('action_type')
        action_category = request.args.get('action_category')
        resource_type = request.args.get('resource_type')
        resource_id = request.args.get('resource_id')
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        # Build query
        query = ActivityLog.query.filter_by(customer_id=customer_id)
        
        # Apply filters
        if action_type:
            query = query.filter(ActivityLog.action_type == action_type)
        if action_category:
            query = query.filter(ActivityLog.action_category == action_category)
        if resource_type:
            query = query.filter(ActivityLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(ActivityLog.resource_id == str(resource_id))
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if status:
            query = query.filter(ActivityLog.status == status)
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(ActivityLog.created_at >= start_dt)
            except:
                pass
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(ActivityLog.created_at <= end_dt)
            except:
                pass
        
        # Order by most recent first
        query = query.order_by(desc(ActivityLog.created_at))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        logs = query.limit(limit).offset(offset).all()
        
        # Serialize logs
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'customer_id': log.customer_id,
                'user_id': log.user_id,
                'user_name': log.user.user_name if log.user else None,
                'action_type': log.action_type,
                'action_category': log.action_category,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'action_description': log.action_description,
                'details': log.details or {},
                'changed_fields': log.changed_fields or [],
                'before_values': log.before_values or {},
                'after_values': log.after_values or {},
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'session_id': log.session_id,
                'status': log.status,
                'error_message': log.error_message,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            })
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching activity logs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch activity logs. Please try again or contact support.'
        }), 500

@activity_log_api.route('/api/activity-logs/summary', methods=['GET'])
def get_activity_summary():
    """Get summary statistics of activity logs"""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get date range
        days = request.args.get('days', type=int, default=30)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        query = ActivityLog.query.filter(
            and_(
                ActivityLog.customer_id == customer_id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            )
        )
        
        # Total activities
        total_activities = query.count()
        
        # By action type
        action_types = db.session.query(
            ActivityLog.action_type,
            db.func.count(ActivityLog.id).label('count')
        ).filter(
            and_(
                ActivityLog.customer_id == customer_id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            )
        ).group_by(ActivityLog.action_type).all()
        
        # By action category
        action_categories = db.session.query(
            ActivityLog.action_category,
            db.func.count(ActivityLog.id).label('count')
        ).filter(
            and_(
                ActivityLog.customer_id == customer_id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            )
        ).group_by(ActivityLog.action_category).all()
        
        # By status
        status_counts = db.session.query(
            ActivityLog.status,
            db.func.count(ActivityLog.id).label('count')
        ).filter(
            and_(
                ActivityLog.customer_id == customer_id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            )
        ).group_by(ActivityLog.status).all()
        
        # By user
        user_counts = db.session.query(
            ActivityLog.user_id,
            User.user_name,
            db.func.count(ActivityLog.id).label('count')
        ).join(User, ActivityLog.user_id == User.user_id).filter(
            and_(
                ActivityLog.customer_id == customer_id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            )
        ).group_by(ActivityLog.user_id, User.user_name).order_by(desc('count')).limit(10).all()
        
        return jsonify({
            'success': True,
            'summary': {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_activities': total_activities,
                'by_action_type': {action_type: count for action_type, count in action_types},
                'by_action_category': {category: count for category, count in action_categories},
                'by_status': {status: count for status, count in status_counts},
                'top_users': [{'user_id': user_id, 'user_name': user_name, 'count': count} 
                             for user_id, user_name, count in user_counts],
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching activity summary: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch activity summary. Please try again or contact support.'
        }), 500

@activity_log_api.route('/api/activity-logs/export', methods=['GET'])
def export_activity_logs():
    """Export activity logs to CSV"""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get query parameters (same as get_activity_logs)
        action_type = request.args.get('action_type')
        action_category = request.args.get('action_category')
        resource_type = request.args.get('resource_type')
        resource_id = request.args.get('resource_id')
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int, default=10000)
        
        # Build query (same as get_activity_logs)
        query = ActivityLog.query.filter_by(customer_id=customer_id)
        
        if action_type:
            query = query.filter(ActivityLog.action_type == action_type)
        if action_category:
            query = query.filter(ActivityLog.action_category == action_category)
        if resource_type:
            query = query.filter(ActivityLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(ActivityLog.resource_id == str(resource_id))
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if status:
            query = query.filter(ActivityLog.status == status)
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(ActivityLog.created_at >= start_dt)
            except:
                pass
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(ActivityLog.created_at <= end_dt)
            except:
                pass
        
        query = query.order_by(desc(ActivityLog.created_at)).limit(limit)
        logs = query.all()
        
        # Generate CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Timestamp', 'User', 'Action Type', 'Action Category', 
            'Resource Type', 'Resource ID', 'Description', 'Status', 
            'Changed Fields', 'IP Address'
        ])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.isoformat() if log.created_at else '',
                log.user.user_name if log.user else 'System',
                log.action_type,
                log.action_category,
                log.resource_type or '',
                log.resource_id or '',
                log.action_description,
                log.status,
                ', '.join(log.changed_fields) if log.changed_fields else '',
                log.ip_address or '',
            ])
        
        # Return CSV
        from flask import Response
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=activity_logs_{timestamp}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting activity logs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to export activity logs. Please try again or contact support.'
        }), 500


# ─── Frontend Click Tracking ────────────────────────────────────────────────

@activity_log_api.route('/api/activity-logs/track', methods=['POST'])
def track_ui_event():
    """
    Log granular UI interactions (page views, clicks, dashboard switches).
    Called by the frontend tracker utility on every significant user action.

    Body:
        event_type: 'page_view' | 'click' | 'dashboard_switch' | 'filter_change' | 'export'
        target: what was clicked/viewed (e.g., 'cro_dashboard', 'account_card_424001')
        details: optional JSON with extra context (e.g., {account_id: 424001, view: 'context_graph'})
    """
    try:
        customer_id = get_current_customer_id()
        user_id = get_current_user_id()
        if not customer_id:
            return jsonify({'status': 'ok'})  # Silent fail for unauthenticated

        data = request.get_json(silent=True) or {}
        event_type = data.get('event_type', 'click')
        target = data.get('target', 'unknown')
        details = data.get('details', {})

        # Map event types to action categories
        category_map = {
            'page_view': 'navigation',
            'click': 'interaction',
            'dashboard_switch': 'navigation',
            'filter_change': 'interaction',
            'export': 'export',
            'account_drill': 'interaction',
            'playbook_action': 'playbook',
            'mcp_query': 'query',
        }

        log_entry = ActivityLog(
            customer_id=customer_id,
            user_id=user_id,
            action_type=event_type,
            action_category=category_map.get(event_type, 'interaction'),
            resource_type=data.get('resource_type', 'ui'),
            resource_id=target,
            action_description=f"{event_type}: {target}",
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255],
            session_id=data.get('session_id', ''),
            status='success',
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.debug(f"UI tracking error (non-fatal): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'status': 'ok'})  # Never fail the UI for tracking errors


# ============================================================================
# S2.3: Cross-Tenant Activity Audit (Super Admin / Server Key)
# ============================================================================

def _require_super_admin():
    """Check if caller is super admin (admin role or server API key).
    Returns True if authorized, or a (response, status_code) tuple if not.
    """
    # Server API key → customer_id is None → super admin
    api_key_cid = getattr(request, '_api_key_customer_id', 'NOT_SET')
    if api_key_cid is None:
        return True

    # Admin role check
    if _is_admin_user():
        return True

    return jsonify({'error': 'Super admin or server API key required'}), 403


@activity_log_api.route('/api/admin/activity-logs', methods=['GET'])
def get_cross_tenant_logs():
    """Search activity logs across ALL customers.

    Super admin only — requires admin role or server API key.

    Query params:
        customer_id: (optional) filter to specific customer
        action_type: (optional) filter by action type
        action_category: (optional) filter by category
        resource_type: (optional) filter by resource type
        user_id: (optional) filter by user
        status: (optional) filter by status
        search: (optional) free-text search in action_description
        start_date: (optional) ISO date
        end_date: (optional) ISO date
        limit: (default 100, max 1000)
        offset: (default 0)
    """
    auth = _require_super_admin()
    if auth is not True:
        return auth

    try:
        customer_id = request.args.get('customer_id', type=int)
        action_type = request.args.get('action_type')
        action_category = request.args.get('action_category')
        resource_type = request.args.get('resource_type')
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(request.args.get('limit', type=int, default=100), 1000)
        offset = request.args.get('offset', type=int, default=0)

        query = ActivityLog.query

        if customer_id:
            query = query.filter(ActivityLog.customer_id == customer_id)
        if action_type:
            query = query.filter(ActivityLog.action_type == action_type)
        if action_category:
            query = query.filter(ActivityLog.action_category == action_category)
        if resource_type:
            query = query.filter(ActivityLog.resource_type == resource_type)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if status:
            query = query.filter(ActivityLog.status == status)
        if search:
            query = query.filter(
                or_(
                    ActivityLog.action_description.ilike(f'%{search}%'),
                    ActivityLog.resource_id.ilike(f'%{search}%'),
                )
            )
        if start_date:
            try:
                query = query.filter(ActivityLog.created_at >= datetime.fromisoformat(start_date.replace('Z', '+00:00')))
            except Exception:
                pass
        if end_date:
            try:
                query = query.filter(ActivityLog.created_at <= datetime.fromisoformat(end_date.replace('Z', '+00:00')))
            except Exception:
                pass

        query = query.order_by(desc(ActivityLog.created_at))
        total_count = query.count()
        logs = query.limit(limit).offset(offset).all()

        # Build customer name lookup
        cust_ids = list({log.customer_id for log in logs if log.customer_id})
        cust_names = {}
        if cust_ids:
            custs = Customer.query.filter(Customer.customer_id.in_(cust_ids)).all()
            cust_names = {c.customer_id: c.customer_name for c in custs}

        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'customer_id': log.customer_id,
                'customer_name': cust_names.get(log.customer_id, f'Customer {log.customer_id}'),
                'user_id': log.user_id,
                'user_name': log.user.user_name if log.user else 'System',
                'action_type': log.action_type,
                'action_category': log.action_category,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'action_description': log.action_description,
                'details': log.details or {},
                'status': log.status,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            })

        return jsonify({
            'success': True,
            'cross_tenant': True,
            'logs': logs_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'filters_applied': {
                k: v for k, v in {
                    'customer_id': customer_id, 'action_type': action_type,
                    'action_category': action_category, 'search': search or None,
                }.items() if v is not None
            },
        }), 200

    except Exception as e:
        logger.error(f"Cross-tenant audit log error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@activity_log_api.route('/api/admin/activity-logs/summary', methods=['GET'])
def get_cross_tenant_summary():
    """Cross-tenant activity summary — aggregate stats across all customers.

    Super admin only. Shows activity volume per customer, top action types,
    error rates, and most active users across the platform.

    Query params:
        days: lookback period (default 30, max 90)
    """
    auth = _require_super_admin()
    if auth is not True:
        return auth

    try:
        days = min(request.args.get('days', type=int, default=30), 90)
        cutoff = datetime.utcnow() - timedelta(days=days)

        base = ActivityLog.query.filter(ActivityLog.created_at >= cutoff)

        total = base.count()

        # Per-customer breakdown
        per_customer = db.session.query(
            ActivityLog.customer_id,
            db.func.count(ActivityLog.id).label('count'),
        ).filter(ActivityLog.created_at >= cutoff).group_by(
            ActivityLog.customer_id,
        ).order_by(desc('count')).all()

        cust_ids = [c[0] for c in per_customer if c[0]]
        cust_names = {}
        if cust_ids:
            custs = Customer.query.filter(Customer.customer_id.in_(cust_ids)).all()
            cust_names = {c.customer_id: c.customer_name for c in custs}

        # Top action types
        top_actions = db.session.query(
            ActivityLog.action_type,
            db.func.count(ActivityLog.id).label('count'),
        ).filter(ActivityLog.created_at >= cutoff).group_by(
            ActivityLog.action_type,
        ).order_by(desc('count')).limit(15).all()

        # Error rate
        errors = base.filter(ActivityLog.status == 'error').count()

        # Most active users (cross-tenant)
        top_users = db.session.query(
            ActivityLog.user_id,
            ActivityLog.customer_id,
            User.user_name,
            db.func.count(ActivityLog.id).label('count'),
        ).outerjoin(User, ActivityLog.user_id == User.user_id).filter(
            ActivityLog.created_at >= cutoff,
        ).group_by(
            ActivityLog.user_id, ActivityLog.customer_id, User.user_name,
        ).order_by(desc('count')).limit(20).all()

        return jsonify({
            'success': True,
            'cross_tenant': True,
            'period_days': days,
            'total_activities': total,
            'error_count': errors,
            'error_rate_pct': round(errors / max(total, 1) * 100, 1),
            'per_customer': [
                {
                    'customer_id': cid,
                    'customer_name': cust_names.get(cid, f'Customer {cid}'),
                    'activity_count': count,
                }
                for cid, count in per_customer
            ],
            'top_action_types': {atype: count for atype, count in top_actions},
            'top_users': [
                {
                    'user_id': uid,
                    'customer_id': cid,
                    'customer_name': cust_names.get(cid, f'Customer {cid}'),
                    'user_name': uname or 'System',
                    'activity_count': count,
                }
                for uid, cid, uname, count in top_users
            ],
        }), 200

    except Exception as e:
        logger.error(f"Cross-tenant summary error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

