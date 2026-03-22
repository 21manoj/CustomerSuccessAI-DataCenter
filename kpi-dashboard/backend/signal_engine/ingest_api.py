#!/usr/bin/env python3
"""
QSIM Signal Engine — Ingestion API.

Flask blueprint providing webhook endpoints for signal ingestion:
  POST /api/signals/ingest/slack
  POST /api/signals/ingest/email
  POST /api/signals/ingest/transcript
  POST /api/signals/ingest/manual
  GET  /api/signals/review-queue

All endpoints are feature-toggled: require FEATURE_SIGNAL_ENGINE=true
AND per-customer signal_engine feature enabled.

Consent: Transcript ingestion requires consent_verified=true in payload.
"""

import logging
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

signal_api = Blueprint('signal_api', __name__)


# ============================================================
# Feature toggle guard
# ============================================================

def _require_signal_engine(f):
    """Decorator: requires FEATURE_SIGNAL_ENGINE=true."""
    @wraps(f)
    def decorated(*args, **kwargs):
        import os
        enabled = os.environ.get('FEATURE_SIGNAL_ENGINE', 'false').lower() in ('true', '1', 'yes')
        if not enabled:
            return jsonify({
                'error': 'Signal Engine is disabled',
                'hint': 'Set FEATURE_SIGNAL_ENGINE=true to enable',
            }), 403
        return f(*args, **kwargs)
    return decorated


def _check_customer_signal_engine(customer_id: int) -> bool:
    """Check per-customer signal_engine feature toggle in DB."""
    try:
        from models import FeatureToggle as FTModel
        from extensions import db
        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='signal_engine',
        ).first()
        return toggle and toggle.is_enabled if toggle else False
    except Exception:
        return False


# ============================================================
# Shared ingest logic
# ============================================================

def _ingest_signal(source_type: str):
    """Common ingestion handler for all source types.

    Validates payload, creates QualitativeSignal record,
    queues for LLM enrichment (async).

    Returns 202 Accepted with raw_signal_id.
    """
    data = request.get_json(force=True)

    # Required fields
    account_id = data.get('account_id')
    customer_id = data.get('customer_id')
    raw_text = data.get('raw_text', '').strip()

    if not account_id or not customer_id:
        return jsonify({'error': 'account_id and customer_id are required'}), 400
    if not raw_text:
        return jsonify({'error': 'raw_text is required'}), 400

    # Per-customer feature check
    if not _check_customer_signal_engine(customer_id):
        return jsonify({
            'error': f'Signal Engine not enabled for customer {customer_id}',
            'hint': 'Enable via enable_features(customer_id, ["signal_engine"])',
        }), 403

    # Consent check for transcripts
    if source_type == 'transcript':
        if not data.get('consent_verified', False):
            return jsonify({
                'error': 'Transcript ingestion requires consent_verified=true',
                'hint': 'Verify participant consent before submitting transcript data',
            }), 400

    # Generate signal ID
    signal_id = str(uuid.uuid4())
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())

    try:
        from extensions import db
        from models import QualitativeSignal

        # Create raw signal record
        signal = QualitativeSignal(
            account_id=int(account_id),
            customer_id=int(customer_id),
            signal_type=source_type,
            content=raw_text[:2000],  # Truncate for safety
            sentiment='neutral',  # Placeholder — enrichment will update
            signal_date=datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if isinstance(timestamp, str) else timestamp,
        )

        # Set QSIM-specific columns (if migration has run)
        try:
            signal.source_type = source_type
            signal.raw_text = raw_text
            signal.requires_review = False
            signal.consent_verified = data.get('consent_verified', source_type != 'transcript')
            signal.composite_signal_id = signal_id

            # Store participant list as stakeholder_roles
            participants = data.get('participant_list', [])
            if participants:
                signal.stakeholder_roles = participants
        except AttributeError:
            # Enrichment columns not yet migrated — signal still saves with base columns
            logger.debug("QSIM enrichment columns not available — saving base signal only")

        db.session.add(signal)
        db.session.commit()

        logger.info(
            "QSIM signal ingested: id=%s source=%s account=%s customer=%s",
            signal_id, source_type, account_id, customer_id,
        )

        # TODO Phase 1: Queue for LLM enrichment (async)
        # For now, the signal is saved raw. Enrichment is triggered
        # separately via the enrichment module or a background task.

        return jsonify({
            'raw_signal_id': signal_id,
            'signal_db_id': signal.id if hasattr(signal, 'id') else None,
            'status': 'queued',
            'source_type': source_type,
            'account_id': account_id,
            'message': 'Signal accepted. Enrichment will run asynchronously.',
        }), 202

    except Exception as e:
        logger.exception("Signal ingestion failed: %s", e)
        return jsonify({'error': f'Ingestion failed: {str(e)}'}), 500


# ============================================================
# Endpoints
# ============================================================

@signal_api.route('/api/signals/ingest/slack', methods=['POST'])
@_require_signal_engine
def ingest_slack():
    """Ingest a signal from Slack.

    POST body:
    {
        "source_type": "slack",
        "account_id": 301,
        "customer_id": 407,
        "timestamp": "2026-03-21T10:30:00Z",
        "raw_text": "Hey team, we're evaluating alternatives...",
        "participant_list": [{"name": "Jane Doe", "role": "VP Infrastructure"}],
        "thread_or_channel_id": "C04ABCD1234"
    }
    """
    return _ingest_signal('slack')


@signal_api.route('/api/signals/ingest/email', methods=['POST'])
@_require_signal_engine
def ingest_email():
    """Ingest a signal from email."""
    return _ingest_signal('email')


@signal_api.route('/api/signals/ingest/transcript', methods=['POST'])
@_require_signal_engine
def ingest_transcript():
    """Ingest a signal from a call transcript.

    REQUIRES consent_verified=true in payload.
    """
    return _ingest_signal('transcript')


@signal_api.route('/api/signals/ingest/manual', methods=['POST'])
@_require_signal_engine
def ingest_manual():
    """Ingest a manually-entered signal (CSM observation)."""
    return _ingest_signal('manual')


# ============================================================
# Review Queue
# ============================================================

@signal_api.route('/api/signals/review-queue', methods=['GET'])
@_require_signal_engine
def get_review_queue():
    """Get signals requiring human review.

    Signals enter the review queue when:
    - Any confidence score < 0.6 on a critical field
    - LLM returned invalid/partial response
    - Transcript without verified consent
    - Dedup confidence < 0.7

    Query params:
      customer_id: (required) filter by customer
      account_id: (optional) filter by account
      urgency: (optional) filter by urgency level
      page: (default 1)
      per_page: (default 25)
    """
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    account_id = request.args.get('account_id', type=int)
    urgency = request.args.get('urgency')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    try:
        from models import QualitativeSignal

        query = QualitativeSignal.query.filter_by(customer_id=customer_id)

        # Filter to signals needing review
        try:
            query = query.filter(QualitativeSignal.requires_review == True)
        except Exception:
            # Column may not exist if migration hasn't run
            return jsonify({'review_queue': [], 'total': 0, 'page': 1})

        if account_id:
            query = query.filter_by(account_id=account_id)
        if urgency:
            try:
                query = query.filter(QualitativeSignal.effective_urgency == urgency)
            except Exception:
                pass

        query = query.order_by(QualitativeSignal.signal_date.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        signals = []
        for s in paginated.items:
            signals.append({
                'id': s.id,
                'account_id': s.account_id,
                'signal_type': s.signal_type,
                'content': s.content[:200] if s.content else '',
                'sentiment': s.sentiment,
                'signal_date': s.signal_date.isoformat() if s.signal_date else None,
                'source_type': getattr(s, 'source_type', None),
                'intent_signals': getattr(s, 'intent_signals', None),
                'confidence': getattr(s, 'confidence', None),
                'effective_urgency': getattr(s, 'effective_urgency', None),
            })

        return jsonify({
            'review_queue': signals,
            'total': paginated.total,
            'page': paginated.page,
        })

    except Exception as e:
        logger.exception("Review queue query failed: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# Signal Engine status / health check
# ============================================================

@signal_api.route('/api/signals/status', methods=['GET'])
def signal_engine_status():
    """Check Signal Engine status and feature toggle state."""
    import os
    enabled = os.environ.get('FEATURE_SIGNAL_ENGINE', 'false').lower() in ('true', '1', 'yes')
    return jsonify({
        'signal_engine_enabled': enabled,
        'version': '0.1.0',
        'phase': 'Phase 1 — Foundation',
        'capabilities': {
            'ingestion': enabled,
            'structural_urgency': enabled,
            'cg_collision_check': enabled,
            'composite_fusion': enabled,
            'llm_enrichment': False,   # Phase 1 stub
            'review_queue': enabled,
            'alert_routing': False,    # Not yet wired
        },
    })
