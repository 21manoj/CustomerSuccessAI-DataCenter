"""
Action Interface API — Phases 4, 5, 7
=======================================
Endpoints for:
  Phase 4: Auth credential vault CRUD
  Phase 5: Action binding admin CRUD
  Phase 7: Playbook execution callback webhook

All endpoints require customer authentication.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from resolve_identifier import resolve_customer_id
from security_utils import encrypt_credential, decrypt_credential

from models import PlaybookExecution
from models_action_interface import (
    CustomerActionBinding,
    IntegrationCredential,
    PlaybookStepLog,
)

logger = logging.getLogger(__name__)

action_interface_api = Blueprint('action_interface_api', __name__)


# ============================================================
# HELPERS
# ============================================================

def _customer_id():
    cid = get_current_customer_id()
    if not cid:
        return None
    return resolve_customer_id(db, cid)


# ============================================================
# PHASE 5 — ACTION BINDING CRUD
# ============================================================

@action_interface_api.route('/api/action-bindings', methods=['GET'])
def list_bindings():
    """List all action bindings for the current customer."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    bindings = CustomerActionBinding.query.filter_by(customer_id=cid).all()
    return jsonify({
        'bindings': [b.to_dict() for b in bindings],
        'count': len(bindings),
    })


@action_interface_api.route('/api/action-bindings', methods=['POST'])
def create_binding():
    """Create a new action binding."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    data = request.get_json()
    if not data or not data.get('action_name') or not data.get('provider'):
        return jsonify({'error': 'action_name and provider are required'}), 400

    # Check for duplicate
    existing = CustomerActionBinding.query.filter_by(
        customer_id=cid, action_name=data['action_name']
    ).first()
    if existing:
        return jsonify({'error': f"Binding for '{data['action_name']}' already exists"}), 409

    # Validate provider
    from providers.registry import get_provider
    provider = get_provider(data['provider'])
    if not provider:
        return jsonify({'error': f"Unknown provider: {data['provider']}"}), 400

    config = data.get('config', {})
    if not provider.validate_config(config):
        return jsonify({'error': 'Invalid provider config'}), 400

    binding = CustomerActionBinding(
        customer_id=cid,
        action_name=data['action_name'],
        provider=data['provider'],
        config=config,
        auth_credential_id=data.get('auth_credential_id'),
        fallback=data.get('fallback'),
        enabled=data.get('enabled', True),
    )
    db.session.add(binding)
    db.session.commit()

    return jsonify(binding.to_dict()), 201


@action_interface_api.route('/api/action-bindings/<int:binding_id>', methods=['PUT'])
def update_binding(binding_id):
    """Update an existing action binding."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    binding = CustomerActionBinding.query.filter_by(id=binding_id, customer_id=cid).first()
    if not binding:
        return jsonify({'error': 'Binding not found'}), 404

    data = request.get_json()
    if data.get('provider'):
        binding.provider = data['provider']
    if data.get('config') is not None:
        binding.config = data['config']
    if data.get('auth_credential_id') is not None:
        binding.auth_credential_id = data['auth_credential_id']
    if data.get('fallback') is not None:
        binding.fallback = data['fallback']
    if data.get('enabled') is not None:
        binding.enabled = data['enabled']

    db.session.commit()
    return jsonify(binding.to_dict())


@action_interface_api.route('/api/action-bindings/<int:binding_id>', methods=['DELETE'])
def delete_binding(binding_id):
    """Delete an action binding."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    binding = CustomerActionBinding.query.filter_by(id=binding_id, customer_id=cid).first()
    if not binding:
        return jsonify({'error': 'Binding not found'}), 404

    db.session.delete(binding)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


# ============================================================
# PHASE 4 — CREDENTIALS VAULT CRUD
# ============================================================

@action_interface_api.route('/api/credentials', methods=['GET'])
def list_credentials():
    """List credentials (metadata only — never return decrypted data)."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    creds = IntegrationCredential.query.filter_by(customer_id=cid).all()
    return jsonify({
        'credentials': [
            {
                'id': c.id,
                'provider': c.provider,
                'credential_type': c.credential_type,
                'expires_at': c.expires_at.isoformat() if c.expires_at else None,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in creds
        ],
    })


@action_interface_api.route('/api/credentials', methods=['POST'])
def create_credential():
    """
    Store a new encrypted credential.

    Body:
    {
        "provider": "jira",
        "credential_type": "api_key",
        "credential_data": {"email": "x@y.com", "api_token": "..."},
        "expires_at": "2027-01-01T00:00:00Z"  (optional)
    }
    """
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    data = request.get_json()
    if not data or not data.get('provider') or not data.get('credential_data'):
        return jsonify({'error': 'provider and credential_data are required'}), 400

    # Encrypt the credential data
    plaintext = json.dumps(data['credential_data'])
    encrypted = encrypt_credential(plaintext)

    expires = None
    if data.get('expires_at'):
        try:
            expires = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        except ValueError:
            pass

    cred = IntegrationCredential(
        customer_id=cid,
        provider=data['provider'],
        credential_type=data.get('credential_type', 'api_key'),
        encrypted_data=encrypted,
        expires_at=expires,
    )
    db.session.add(cred)
    db.session.commit()

    return jsonify({
        'id': cred.id,
        'provider': cred.provider,
        'credential_type': cred.credential_type,
        'message': 'Credential stored securely',
    }), 201


@action_interface_api.route('/api/credentials/<int:cred_id>', methods=['DELETE'])
def delete_credential(cred_id):
    """Delete a credential from the vault."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    cred = IntegrationCredential.query.filter_by(id=cred_id, customer_id=cid).first()
    if not cred:
        return jsonify({'error': 'Credential not found'}), 404

    db.session.delete(cred)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@action_interface_api.route('/api/credentials/<int:cred_id>/health', methods=['GET'])
def check_credential_health(cred_id):
    """Test that a credential is valid by calling the provider's health check."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    cred = IntegrationCredential.query.filter_by(id=cred_id, customer_id=cid).first()
    if not cred:
        return jsonify({'error': 'Credential not found'}), 404

    from providers.registry import get_provider
    provider = get_provider(cred.provider)
    if not provider:
        return jsonify({'error': f'Provider {cred.provider} not found'}), 404

    try:
        decrypted = decrypt_credential(cred.encrypted_data)
        cred_data = json.loads(decrypted) if isinstance(decrypted, str) else decrypted
        healthy = provider.health_check(cred_data)
    except Exception as e:
        return jsonify({'healthy': False, 'error': str(e)})

    return jsonify({'healthy': healthy, 'provider': cred.provider})


# ============================================================
# PHASE 7 — PLAYBOOK CALLBACK WEBHOOK
# ============================================================

@action_interface_api.route('/api/webhooks/playbook-callback', methods=['POST'])
def playbook_callback():
    """
    Receive execution callbacks from n8n or external providers.

    Body:
    {
        "execution_id": "abc-123",
        "status": "COMPLETED",
        "outcome": "resolved",
        "external_ticket_id": "JIRA-456",
        "external_ticket_url": "https://...",
        "progress_notes": "Issue resolved",
        "kpi_improvements": {"NRR": 0.5}
    }
    """
    data = request.get_json()
    if not data or not data.get('execution_id'):
        return jsonify({'error': 'execution_id is required'}), 400

    execution = PlaybookExecution.query.filter_by(
        execution_id=data['execution_id']
    ).first()
    if not execution:
        return jsonify({'error': 'Execution not found'}), 404

    from playbook_orchestrator import PlaybookOrchestrator
    orchestrator = PlaybookOrchestrator()
    orchestrator.process_callback(execution, data)

    return jsonify({
        'execution_id': data['execution_id'],
        'status': execution.status,
        'message': 'Callback processed',
    })


# ============================================================
# STEP LOG QUERY
# ============================================================

@action_interface_api.route('/api/playbook-steps/<execution_id>', methods=['GET'])
def get_step_logs(execution_id):
    """Get all step logs for an execution."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    steps = PlaybookStepLog.query.filter_by(
        execution_id=execution_id
    ).order_by(PlaybookStepLog.step_index).all()

    return jsonify({
        'execution_id': execution_id,
        'steps': [s.to_dict() for s in steps],
        'total': len(steps),
        'succeeded': sum(1 for s in steps if s.status == 'success'),
        'failed': sum(1 for s in steps if s.status == 'failed'),
    })


# ============================================================
# PROVIDER REGISTRY INFO
# ============================================================

@action_interface_api.route('/api/providers', methods=['GET'])
def list_providers():
    """List all available provider adapters."""
    from providers.registry import PROVIDER_REGISTRY

    registry = PROVIDER_REGISTRY()
    return jsonify({
        'providers': [
            {
                'name': name,
                'supported_actions': list(getattr(p, 'SUPPORTED_ACTIONS', set())),
            }
            for name, p in registry.items()
        ],
    })
