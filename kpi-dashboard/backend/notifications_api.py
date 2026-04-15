#!/usr/bin/env python3
"""
Notifications API
=================

Endpoints for the Actions Pipeline Push notification feed.

Routes:
    GET  /api/notifications/unread              — unread count + notification list
    PUT  /api/notifications/<id>/read           — mark a notification as read
    GET  /api/notifications/                    — paginated list with optional ?type= filter
    GET  /api/config/push-intelligence          — return push intelligence thresholds
    PUT  /api/config/push-intelligence          — update thresholds (live reload, no restart)
"""

import json
import os

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
# POST /api/notifications/seed — Generate initial notifications from current state
# ---------------------------------------------------------------------------

@notifications_api.route('/api/notifications/seed', methods=['POST'])
def seed_notifications():
    """
    Generate notifications from current at-risk conditions if none exist.
    Idempotent: skips if customer already has unread notifications.
    Call this on first dashboard load to populate the notification bell.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Skip if already has unread notifications
        existing = Notification.query.filter_by(
            customer_id=int(customer_id),
        ).filter(Notification.read_at.is_(None)).count()

        if existing > 0:
            return jsonify({'seeded': 0, 'reason': f'Already has {existing} unread notifications'})

        from models import Account, HealthScore
        import utils.health_thresholds as ht
        from datetime import datetime as dt, date as _date

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        seeded = 0

        for acct in accounts:
            meta = acct.profile_metadata or {}
            # Get latest health score
            latest_hs = (
                HealthScore.query
                .filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.desc())
                .first()
            )
            health = float(latest_hs.health_score) if latest_hs else None
            if health is None:
                continue

            arr = float(acct.revenue or 0)
            acct_name = acct.account_name

            # Critical health notification
            if health < ht.at_risk_min():
                notif = Notification(
                    customer_id=int(customer_id),
                    account_id=acct.account_id,
                    type='urgent_alert',
                    priority='critical',
                    payload={
                        'title': f'Critical Health: {acct_name}',
                        'summary': f'Health score dropped to {health:.0f} (critical threshold: {ht.at_risk_min()}). '
                                   f'${arr:,.0f} ARR at risk. Immediate intervention recommended.',
                        'account_name': acct_name,
                        'health_score': health,
                        'arr': arr,
                    },
                )
                db.session.add(notif)
                seeded += 1

            # At-risk notification
            elif health < ht.healthy_min():
                notif = Notification(
                    customer_id=int(customer_id),
                    account_id=acct.account_id,
                    type='signal_insight',
                    priority='high',
                    payload={
                        'title': f'At-Risk: {acct_name}',
                        'summary': f'Health score at {health:.0f} (at-risk range). '
                                   f'Monitor closely and consider proactive outreach.',
                        'account_name': acct_name,
                        'health_score': health,
                        'arr': arr,
                    },
                )
                db.session.add(notif)
                seeded += 1

            # Renewal approaching with non-healthy status
            rd_str = meta.get('renewal_date') or meta.get('contract_renewal_date')
            if rd_str and health < ht.healthy_min():
                try:
                    rd = dt.strptime(str(rd_str)[:10], '%Y-%m-%d').date()
                    days_until = (rd - _date.today()).days
                    if 0 <= days_until <= 90:
                        notif = Notification(
                            customer_id=int(customer_id),
                            account_id=acct.account_id,
                            type='urgent_alert',
                            priority='critical' if days_until <= 30 else 'high',
                            payload={
                                'title': f'Renewal Risk: {acct_name}',
                                'summary': f'Renewal in {days_until} days with health {health:.0f}. '
                                           f'${arr:,.0f} ARR. Run renewal safeguard playbook.',
                                'account_name': acct_name,
                                'days_until_renewal': days_until,
                                'health_score': health,
                                'arr': arr,
                            },
                        )
                        db.session.add(notif)
                        seeded += 1
                except (ValueError, TypeError):
                    pass

        if seeded > 0:
            db.session.commit()

        return jsonify({'seeded': seeded})

    except Exception as e:
        logger.error(f"Error seeding notifications: {e}", exc_info=True)
        return jsonify({'error': 'Failed to seed notifications'}), 500


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


# ---------------------------------------------------------------------------
# GET /api/config/push-intelligence
# ---------------------------------------------------------------------------

@notifications_api.route('/api/config/push-intelligence', methods=['GET'])
def get_push_intelligence_config():
    """Return current push intelligence thresholds."""
    try:
        import utils.push_intelligence_config as pic
        return jsonify(pic._load())
    except Exception as e:
        logger.error(f"Error fetching push intelligence config: {e}", exc_info=True)
        return jsonify({'error': 'Failed to load push intelligence config'}), 500


# ---------------------------------------------------------------------------
# PUT /api/config/push-intelligence
# ---------------------------------------------------------------------------

@notifications_api.route('/api/config/push-intelligence', methods=['PUT'])
def update_push_intelligence_config():
    """Update push intelligence thresholds and reload cache immediately."""
    try:
        import utils.push_intelligence_config as pic

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Deep merge incoming data into existing config
        current = pic._load().copy()
        for section, values in data.items():
            if section.startswith('_'):
                continue  # skip comment/version keys
            if section in current and isinstance(current[section], dict):
                current[section].update(values)
            else:
                current[section] = values

        # Write back to file
        config_path = os.path.join(
            os.path.dirname(__file__), 'config', 'push_intelligence_config.json'
        )
        with open(config_path, 'w') as f:
            json.dump(current, f, indent=2)

        # Reload cache immediately — no restart needed
        pic.reload()
        logger.info(f"Push intelligence config updated: {list(data.keys())}")
        return jsonify({'success': True, 'config': pic._load()})

    except Exception as e:
        logger.error(f"Error updating push intelligence config: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update push intelligence config'}), 500
