"""
Customer Playbook Library API
===============================

CRUD for per-customer playbook definitions.  System playbooks (from
PLAYBOOK_CONFIG) are seeded on first access; custom playbooks are created
by the customer or generated via Claude Skills MCP tool.

Endpoints:
  GET    /api/playbooks/library           — list customer's playbooks
  POST   /api/playbooks/library           — create custom playbook
  PUT    /api/playbooks/library/<id>       — edit playbook
  DELETE /api/playbooks/library/<id>       — delete custom (cannot delete system)
  POST   /api/playbooks/library/<id>/test  — dry-run against current accounts
"""

import logging
from flask import Blueprint, request, jsonify
from extensions import db
from auth_middleware import get_current_customer_id

logger = logging.getLogger(__name__)

customer_playbook_api = Blueprint('customer_playbook_api', __name__)


def _seed_system_playbooks(customer_id: int) -> None:
    """Seed system playbooks from PLAYBOOK_CONFIG if not yet seeded."""
    from models import CustomerPlaybook

    existing = CustomerPlaybook.query.filter_by(
        customer_id=customer_id, is_system=True
    ).count()
    if existing > 0:
        return  # already seeded

    try:
        from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG
    except ImportError:
        return

    for pb_id, cfg in PLAYBOOK_CONFIG.items():
        conditions = []
        for kpi_code, cond in (cfg.get('trigger_conditions') or {}).items():
            conditions.append({
                'kpi_code': kpi_code,
                'operator': cond.get('operator', 'less_than'),
                'threshold': cond.get('value'),
            })

        actions = []
        for i, sc in enumerate(cfg.get('sub_components') or [], 1):
            actions.append({
                'step': i,
                'description': sc.get('name', ''),
                'owner_role': 'csm',
                'estimated_hours': sc.get('estimated_hours', 0),
            })

        playbook = CustomerPlaybook(
            customer_id=customer_id,
            playbook_id=pb_id,
            name=cfg.get('name', pb_id),
            description=cfg.get('description', ''),
            is_system=True,
            trigger_conditions=conditions,
            trigger_logic=cfg.get('trigger_logic', 'OR'),
            actions=actions,
            auto_trigger_enabled=False,
            cooldown_hours=168,
            created_by='system',
        )
        db.session.add(playbook)

    db.session.commit()
    logger.info(f"Seeded {len(PLAYBOOK_CONFIG)} system playbooks for customer {customer_id}")


@customer_playbook_api.route('/api/playbooks/library', methods=['GET'])
def list_playbooks():
    """List customer's playbooks (system + custom)."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    from models import CustomerPlaybook
    _seed_system_playbooks(customer_id)

    playbooks = CustomerPlaybook.query.filter_by(
        customer_id=customer_id
    ).order_by(CustomerPlaybook.is_system.desc(), CustomerPlaybook.playbook_id).all()

    return jsonify({
        'status': 'success',
        'playbooks': [p.to_dict() for p in playbooks],
        'total': len(playbooks),
        'system_count': sum(1 for p in playbooks if p.is_system),
        'custom_count': sum(1 for p in playbooks if not p.is_system),
    })


@customer_playbook_api.route('/api/playbooks/library', methods=['POST'])
def create_playbook():
    """Create a custom playbook."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    data = request.json or {}
    required = ['name', 'trigger_conditions', 'actions']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    from models import CustomerPlaybook

    # Auto-generate playbook_id
    custom_count = CustomerPlaybook.query.filter(
        CustomerPlaybook.customer_id == customer_id,
        CustomerPlaybook.playbook_id.like('PB-CUSTOM-%'),
    ).count()
    playbook_id = data.get('playbook_id') or f'PB-CUSTOM-{custom_count + 1:02d}'

    playbook = CustomerPlaybook(
        customer_id=customer_id,
        playbook_id=playbook_id,
        name=data['name'],
        description=data.get('description', ''),
        is_system=False,
        trigger_conditions=data['trigger_conditions'],
        trigger_logic=data.get('trigger_logic', 'OR'),
        actions=data['actions'],
        auto_trigger_enabled=data.get('auto_trigger_enabled', False),
        cooldown_hours=data.get('cooldown_hours', 168),
        created_by=data.get('created_by', 'user'),
    )
    db.session.add(playbook)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Playbook {playbook_id} created',
        'playbook': playbook.to_dict(),
    }), 201


@customer_playbook_api.route('/api/playbooks/library/<playbook_id>', methods=['PUT'])
def update_playbook(playbook_id):
    """Edit a playbook. System playbooks: can override thresholds only."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    from models import CustomerPlaybook
    playbook = CustomerPlaybook.query.filter_by(
        customer_id=customer_id, playbook_id=playbook_id
    ).first()
    if not playbook:
        return jsonify({'error': f'Playbook {playbook_id} not found'}), 404

    data = request.json or {}

    if playbook.is_system:
        # System playbooks: only allow threshold and toggle changes
        if 'trigger_conditions' in data:
            playbook.trigger_conditions = data['trigger_conditions']
        if 'auto_trigger_enabled' in data:
            playbook.auto_trigger_enabled = data['auto_trigger_enabled']
        if 'cooldown_hours' in data:
            playbook.cooldown_hours = data['cooldown_hours']
    else:
        # Custom playbooks: allow full edit
        for field in ['name', 'description', 'trigger_conditions', 'trigger_logic',
                      'actions', 'auto_trigger_enabled', 'cooldown_hours']:
            if field in data:
                setattr(playbook, field, data[field])

    db.session.commit()
    return jsonify({'status': 'success', 'playbook': playbook.to_dict()})


@customer_playbook_api.route('/api/playbooks/library/<playbook_id>', methods=['DELETE'])
def delete_playbook(playbook_id):
    """Delete a custom playbook. Cannot delete system playbooks."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    from models import CustomerPlaybook
    playbook = CustomerPlaybook.query.filter_by(
        customer_id=customer_id, playbook_id=playbook_id
    ).first()
    if not playbook:
        return jsonify({'error': f'Playbook {playbook_id} not found'}), 404
    if playbook.is_system:
        return jsonify({'error': 'Cannot delete system playbooks. Use PUT to override thresholds.'}), 403

    db.session.delete(playbook)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Playbook {playbook_id} deleted'})


@customer_playbook_api.route('/api/playbooks/library/<playbook_id>/test', methods=['POST'])
def test_playbook(playbook_id):
    """Dry-run a playbook against current accounts. Returns which accounts would trigger."""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    customer_id = int(customer_id)

    from models import CustomerPlaybook, Account, HealthScore

    playbook = CustomerPlaybook.query.filter_by(
        customer_id=customer_id, playbook_id=playbook_id
    ).first()
    if not playbook:
        return jsonify({'error': f'Playbook {playbook_id} not found'}), 404

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    would_trigger = []

    for account in accounts:
        latest_hs = (
            HealthScore.query.filter_by(account_id=account.account_id)
            .order_by(HealthScore.measurement_month.desc()).first()
        )
        health = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else None

        # Simple condition evaluation
        conditions = playbook.trigger_conditions or []
        logic = playbook.trigger_logic or 'OR'
        matched = []

        for cond in conditions:
            metric = cond.get('kpi_code', '')
            if metric == 'health_score' and health is not None:
                val = health
            else:
                val = None  # would need KPI lookup for full evaluation

            if val is not None:
                threshold = float(cond.get('threshold', 0))
                op = cond.get('operator', 'less_than')
                if op in ('less_than', '<') and val < threshold:
                    matched.append(cond)
                elif op in ('greater_than', '>') and val > threshold:
                    matched.append(cond)

        triggered = (len(matched) > 0 and logic == 'OR') or (len(matched) == len(conditions) and logic == 'AND')

        if triggered:
            would_trigger.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'health_score': health,
                'arr': float(account.revenue or 0),
                'matched_conditions': matched,
            })

    return jsonify({
        'status': 'success',
        'playbook_id': playbook_id,
        'playbook_name': playbook.name,
        'accounts_tested': len(accounts),
        'accounts_would_trigger': len(would_trigger),
        'triggers': would_trigger,
    })
