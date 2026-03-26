#!/usr/bin/env python3
"""
Notifications API
=================

Endpoints for the Actions Pipeline Push notification feed.

Routes:
    GET  /api/notifications/unread   — unread count + notification list
    PUT  /api/notifications/<id>/read — mark a notification as read
    GET  /api/notifications/         — paginated list with optional ?type= filter
"""

from flask import Blueprint, jsonify, request
from auth_middleware import get_current_customer_id
from extensions import db
from models import Notification
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

notifications_api = Blueprint('notifications_api', __name__)


# ---------------------------------------------------------------------------
# GET /api/notifications/unread
# ---------------------------------------------------------------------------

@notifications_api.route('/api/notifications/unread', methods=['GET'])
def get_unread_notifications():
    """
    Return unread notification count and up to `limit` unread notifications.

    Query params:
        limit (int, default 20): max notifications to return

    Response:
        { count: int, notifications: [...] }
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        limit = min(int(request.args.get('limit', 20)), 100)

        unread_q = Notification.query.filter_by(
            customer_id=int(customer_id),
        ).filter(Notification.read_at.is_(None))

        count = unread_q.count()

        notifications = (
            unread_q
            .order_by(
                # Critical first, then high, then normal; within priority by recency
                db.case(
                    (Notification.priority == 'critical', 0),
                    (Notification.priority == 'high', 1),
                    else_=2,
                ),
                Notification.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

        return jsonify({
            'count': count,
            'notifications': [n.to_dict() for n in notifications],
        })

    except Exception as e:
        logger.error(f"Error fetching unread notifications: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch notifications'}), 500


# ---------------------------------------------------------------------------
# PUT /api/notifications/<notification_id>/read
# ---------------------------------------------------------------------------

@notifications_api.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id: int):
    """
    Mark a notification as read by setting read_at = utcnow().

    Returns:
        { success: true, read_at: "<ISO timestamp>" }
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        notification = Notification.query.filter_by(
            id=notification_id,
            customer_id=int(customer_id),
        ).first()

        if not notification:
            return jsonify({'error': 'Notification not found'}), 404

        if notification.read_at is None:
            notification.read_at = datetime.utcnow()
            db.session.commit()

        return jsonify({
            'success': True,
            'id': notification_id,
            'read_at': notification.read_at.isoformat(),
        })

    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to update notification'}), 500


# ---------------------------------------------------------------------------
# GET /api/notifications/
# ---------------------------------------------------------------------------

@notifications_api.route('/api/notifications/', methods=['GET'])
def list_notifications():
    """
    Paginated notification list.

    Query params:
        type   (str):  filter by notification type (signal_insight | playbook_triggered | urgent_alert)
        limit  (int):  page size, default 50, max 200
        offset (int):  skip N records (for pagination)
        unread (bool): if 'true', return only unread notifications

    Response:
        {
            notifications: [...],
            total: int,
            limit: int,
            offset: int
        }
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        limit  = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        ntype  = request.args.get('type')
        unread_only = request.args.get('unread', '').lower() == 'true'

        query = Notification.query.filter_by(customer_id=int(customer_id))

        if ntype:
            query = query.filter_by(type=ntype)

        if unread_only:
            query = query.filter(Notification.read_at.is_(None))

        total = query.count()

        notifications = (
            query
            .order_by(
                db.case(
                    (Notification.priority == 'critical', 0),
                    (Notification.priority == 'high', 1),
                    else_=2,
                ),
                Notification.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
            .all()
        )

        return jsonify({
            'notifications': [n.to_dict() for n in notifications],
            'total': total,
            'limit': limit,
            'offset': offset,
        })

    except Exception as e:
        logger.error(f"Error listing notifications: {e}", exc_info=True)
        return jsonify({'error': 'Failed to list notifications'}), 500
