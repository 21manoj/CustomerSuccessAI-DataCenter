#!/usr/bin/env python3
"""
Activity Log API
Query and manage activity logs for governance
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import ActivityLog, User
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc

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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

