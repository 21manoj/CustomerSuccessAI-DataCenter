#!/usr/bin/env python3
"""
Agent Memory REST API
======================
Endpoints for persisting, recalling, and managing agent memories.
Blueprint: agent_memory_api
"""

from flask import Blueprint, request, jsonify
from agent_memory import (
    MemoryStore, MemoryEntry, MemoryType, MemoryScope,
    get_memory_store, get_account_context, memory_stats_to_dict,
    remember_analysis_result, remember_playbook_outcome,
)

agent_memory_api = Blueprint('agent_memory_api', __name__)


def _get_customer_id() -> int:
    try:
        from auth_middleware import get_current_customer_id
        return get_current_customer_id()
    except Exception:
        return request.args.get('customer_id', 0, type=int)


# ============================================================
# REMEMBER  (write)
# ============================================================

@agent_memory_api.route('/api/memory/remember', methods=['POST'])
def remember():
    """Store a new memory entry."""
    cid = _get_customer_id()
    data = request.get_json(force=True)

    entry = MemoryEntry(
        memory_type=MemoryType(data.get('memory_type', 'short_term')),
        scope=MemoryScope(data.get('scope', 'account')),
        content=data['content'],
        customer_id=cid,
        account_id=data.get('account_id'),
        agent_id=data.get('agent_id'),
        namespace=data.get('namespace'),
        key=data.get('key'),
        metadata=data.get('metadata'),
        importance=data.get('importance', 0.5),
        ttl_hours=data.get('ttl_hours'),
    )

    store = get_memory_store()
    record_id = store.remember(entry)

    return jsonify({'id': record_id, 'status': 'stored'}), 201


@agent_memory_api.route('/api/memory/entity', methods=['POST'])
def remember_entity():
    """Upsert a named-entity fact (e.g. ARR, CSM name, tier)."""
    cid = _get_customer_id()
    data = request.get_json(force=True)

    store = get_memory_store()
    record_id = store.remember_entity(
        customer_id=cid,
        account_id=data['account_id'],
        entity_key=data['key'],
        value=data['value'],
        metadata=data.get('metadata'),
    )

    return jsonify({'id': record_id, 'status': 'upserted'}), 200


@agent_memory_api.route('/api/memory/analysis', methods=['POST'])
def store_analysis():
    """Store an analysis result as episodic memory."""
    cid = _get_customer_id()
    data = request.get_json(force=True)

    record_id = remember_analysis_result(
        customer_id=cid,
        account_id=data['account_id'],
        analysis_type=data['analysis_type'],
        result_summary=data['result_summary'],
        metadata=data.get('metadata'),
        importance=data.get('importance', 0.7),
    )

    return jsonify({'id': record_id, 'status': 'stored'}), 201


@agent_memory_api.route('/api/memory/playbook-outcome', methods=['POST'])
def store_playbook_outcome():
    """Store a playbook execution outcome."""
    cid = _get_customer_id()
    data = request.get_json(force=True)

    record_id = remember_playbook_outcome(
        customer_id=cid,
        account_id=data['account_id'],
        playbook_id=data['playbook_id'],
        outcome=data['outcome'],
        kpi_improvements=data.get('kpi_improvements'),
        importance=data.get('importance', 0.8),
    )

    return jsonify({'id': record_id, 'status': 'stored'}), 201


# ============================================================
# RECALL  (read)
# ============================================================

@agent_memory_api.route('/api/memory/recall', methods=['GET'])
def recall():
    """Recall memories by structured filters."""
    cid = _get_customer_id()
    store = get_memory_store()

    mt = request.args.get('memory_type')
    results = store.recall(
        customer_id=cid,
        account_id=request.args.get('account_id'),
        memory_type=MemoryType(mt) if mt else None,
        namespace=request.args.get('namespace'),
        key=request.args.get('key'),
        limit=request.args.get('limit', 20, type=int),
        min_importance=request.args.get('min_importance', 0.0, type=float),
    )

    return jsonify({
        'count': len(results),
        'memories': [
            {
                'content': r.content,
                'memory_type': r.memory_type,
                'scope': r.scope,
                'namespace': r.namespace,
                'key': r.key,
                'metadata': r.metadata,
                'importance': r.importance,
                'similarity': r.similarity,
                'created_at': r.created_at,
            }
            for r in results
        ],
    })


@agent_memory_api.route('/api/memory/entities/<account_id>', methods=['GET'])
def recall_entities(account_id: str):
    """Get all entity facts for an account."""
    cid = _get_customer_id()
    store = get_memory_store()
    entities = store.recall_entities(cid, account_id)
    return jsonify({'account_id': account_id, 'entities': entities})


@agent_memory_api.route('/api/memory/context/<account_id>', methods=['GET'])
def account_context(account_id: str):
    """Get full memory context for an account (entities + episodes + short-term)."""
    cid = _get_customer_id()
    ctx = get_account_context(cid, account_id)
    return jsonify({'account_id': account_id, 'context': ctx})


# ============================================================
# MANAGE  (lifecycle)
# ============================================================

@agent_memory_api.route('/api/memory/<int:record_id>', methods=['DELETE'])
def forget(record_id: int):
    """Archive (soft-delete) a memory record."""
    store = get_memory_store()
    ok = store.forget(record_id)
    return jsonify({'deleted': ok}), 200 if ok else 404


@agent_memory_api.route('/api/memory/prune', methods=['POST'])
def prune():
    """Archive all expired memories."""
    store = get_memory_store()
    count = store.prune_expired()
    return jsonify({'pruned': count})


@agent_memory_api.route('/api/memory/consolidate', methods=['POST'])
def consolidate():
    """Run memory consolidation (promote important short-term to episodic)."""
    cid = _get_customer_id()
    data = request.get_json(force=True) if request.is_json else {}
    store = get_memory_store()
    promoted = store.consolidate(
        customer_id=cid,
        account_id=data.get('account_id'),
        max_short_term=data.get('max_short_term', 50),
    )
    return jsonify({'promoted_to_episodic': promoted})


@agent_memory_api.route('/api/memory/stats', methods=['GET'])
def stats():
    """Get memory usage statistics for the current customer."""
    cid = _get_customer_id()
    return jsonify(memory_stats_to_dict(cid))


# ============================================================
# AGENT STATE  (scratchpad)
# ============================================================

@agent_memory_api.route('/api/memory/agent-state', methods=['POST'])
def save_agent_state():
    """Save agent state for multi-step reasoning."""
    cid = _get_customer_id()
    data = request.get_json(force=True)

    from agent_memory import AgentState

    state = AgentState(
        agent_id=data['agent_id'],
        customer_id=cid,
        account_id=data.get('account_id'),
        step=data.get('step', 0),
        reasoning_chain=data.get('reasoning_chain', []),
        intermediate_results=data.get('intermediate_results', {}),
        status=data.get('status', 'idle'),
    )

    store = get_memory_store()
    record_id = store.save_agent_state(state)
    return jsonify({'id': record_id, 'status': 'saved'}), 200


@agent_memory_api.route('/api/memory/agent-state/<agent_id>', methods=['GET'])
def load_agent_state(agent_id: str):
    """Load the most recent agent state."""
    cid = _get_customer_id()
    store = get_memory_store()
    state = store.load_agent_state(
        agent_id=agent_id,
        customer_id=cid,
        account_id=request.args.get('account_id'),
    )

    if state is None:
        return jsonify({'error': 'No state found', 'agent_id': agent_id}), 404

    from dataclasses import asdict
    return jsonify(asdict(state))
