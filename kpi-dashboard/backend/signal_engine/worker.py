#!/usr/bin/env python3
"""
QSIM Signal Engine — Background Enrichment Worker.

Daemon thread that polls for un-enriched signals and runs the
Qdrant->Claude RAG enrichment pipeline on each.

Architecture:
  - Polls every 30 seconds (configurable)
  - Can be woken immediately via threading.Event from ingest_api
  - Respects per-customer/account rate limits in enrichment.py
  - Runs collision detection after enrichment
  - Creates ContextNode for signals without CG equivalents
  - Non-blocking — errors never crash the app

Usage:
    from signal_engine.worker import SignalEnrichmentWorker
    worker = SignalEnrichmentWorker()
    worker.start()  # Call once at app startup
"""

import logging
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Worker config
POLL_INTERVAL_SECONDS = 30
BATCH_SIZE = 10
MAX_CONSECUTIVE_ERRORS = 5


# Module-level event for immediate wake from ingest_api
_wake_event = threading.Event()


def notify_new_signal():
    """Wake the enrichment worker immediately (called from ingest_api after 202)."""
    _wake_event.set()


class SignalEnrichmentWorker:
    """Background daemon thread that enriches queued QSIM signals.

    Lifecycle:
        1. Poll for un-enriched signals (source_type set, intent_signals NULL)
        2. For each signal, call enrich_signal() (Qdrant->Claude RAG)
        3. Run collision detection against context graph
        4. Create ContextNode if signal has intents without CG equivalents
        5. Sleep until next poll or wake event
    """

    def __init__(self, poll_interval: int = POLL_INTERVAL_SECONDS, batch_size: int = BATCH_SIZE):
        self._interval = poll_interval
        self._batch_size = batch_size
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._consecutive_errors = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name='signal-enrichment-worker',
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Signal enrichment worker started (poll=%ds, batch=%d)",
            self._interval, self._batch_size,
        )

    def stop(self) -> None:
        self._running = False
        _wake_event.set()  # Wake immediately so thread can exit

    def _loop(self) -> None:
        # Wait 30s on startup to let the app fully initialize
        time.sleep(30)

        while self._running:
            try:
                count = self._process_batch()
                self._consecutive_errors = 0

                if count > 0:
                    # More signals may be waiting — short sleep then re-poll
                    time.sleep(2)
                    continue

            except Exception as e:
                self._consecutive_errors += 1
                logger.error(
                    "Signal enrichment worker error (%d/%d): %s",
                    self._consecutive_errors, MAX_CONSECUTIVE_ERRORS, e,
                    exc_info=True,
                )
                if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(
                        "Signal enrichment worker: too many consecutive errors — "
                        "backing off to 5 minutes"
                    )
                    _wake_event.wait(timeout=300)
                    _wake_event.clear()
                    self._consecutive_errors = 0
                    continue

            # Wait for next poll or immediate wake
            _wake_event.wait(timeout=self._interval)
            _wake_event.clear()

    def _process_batch(self) -> int:
        """Process a batch of un-enriched signals. Returns count processed."""
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("Signal enrichment worker: no Flask app available")
                return 0

        with app.app_context():
            return self._do_process_batch()

    def _do_process_batch(self) -> int:
        """Actual batch processing (inside app context)."""
        from extensions import db
        from models import QualitativeSignal, Account

        # Find un-enriched QSIM signals
        # source_type IS NOT NULL = ingested via QSIM webhook
        # intent_signals IS NULL = not yet enriched
        try:
            signals = (
                QualitativeSignal.query
                .filter(
                    QualitativeSignal.source_type.isnot(None),
                    QualitativeSignal.intent_signals.is_(None),
                )
                .order_by(QualitativeSignal.signal_date.desc())
                .limit(self._batch_size)
                .all()
            )
        except Exception as e:
            # source_type column may not exist yet (migration pending)
            logger.debug("Signal enrichment worker: query failed (migration pending?): %s", e)
            return 0

        if not signals:
            return 0

        logger.info("Signal enrichment worker: processing %d un-enriched signals", len(signals))

        enriched_count = 0
        for i, sig in enumerate(signals):
            try:
                enriched_count += self._enrich_one(sig, db)
            except Exception as e:
                logger.warning(
                    "Signal enrichment failed for %s: %s",
                    sig.signal_id, e,
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass
            # Throttle: ~40 req/min to stay under Anthropic's 50 RPM limit
            if i < len(signals) - 1:
                time.sleep(1.5)

        if enriched_count:
            logger.info("Signal enrichment worker: enriched %d/%d signals", enriched_count, len(signals))

        return enriched_count

    def _enrich_one(self, sig, db) -> int:
        """Enrich a single signal. Returns 1 if enriched, 0 if skipped."""
        from signal_engine.enrichment import enrich_signal
        from signal_engine.collision import check_cg_collision, should_create_qualitative_node

        raw = sig.raw_text or sig.content or ''
        if not raw.strip():
            return 0

        # Resolve customer_id from account
        from models import Account
        account = db.session.get(Account, sig.account_id)
        customer_id = account.customer_id if account else 0
        if not customer_id:
            return 0

        # Resolve vertical
        vertical = 'dc2_s'
        try:
            from utils.vertical_registry import get_vertical_for_customer
            vertical = get_vertical_for_customer(customer_id)
        except Exception:
            pass

        # Step 1: Enrich via Qdrant->Claude RAG
        result = enrich_signal(
            signal_id=sig.signal_id,
            raw_text=raw,
            account_id=sig.account_id,
            customer_id=customer_id,
            vertical=vertical,
        )

        # Step 2: Apply enrichment to signal record
        for field in (
            'sentiment_score', 'relationship_sentiment', 'product_sentiment',
            'urgency_score', 'escalation_probability', 'intent_signals',
            'stakeholder_roles', 'suggested_action', 'confidence',
            'requires_review', 'llm_model_version', 'is_duplicate',
        ):
            if field in result:
                try:
                    setattr(sig, field, result[field])
                except Exception:
                    pass

        # Map sentiment score to label
        score = result.get('sentiment_score', 0)
        if score > 0.2:
            sig.sentiment = 'positive'
        elif score < -0.2:
            sig.sentiment = 'negative'
        else:
            sig.sentiment = 'neutral'

        # Step 3: Run structural urgency classifier
        try:
            from signal_engine.urgency import (
                classify_structural_urgency, resolve_effective_urgency,
                AccountContext, SignalContext,
            )
            acct_ctx = AccountContext(account_id=sig.account_id)
            sig_ctx = SignalContext(
                intent_signals=result.get('intent_signals', []),
                health_delta=0,
                llm_urgency_score=result.get('urgency_score', 0.5),
                escalation_probability=result.get('escalation_probability', 0),
            )
            structural = classify_structural_urgency(sig_ctx, acct_ctx)
            effective = resolve_effective_urgency(
                structural,
                result.get('urgency_score', 0.5),
                result.get('escalation_probability', 0),
            )
            sig.structural_urgency = structural
            sig.effective_urgency = effective
        except Exception as e:
            logger.debug("Urgency classification skipped: %s", e)

        # Step 4: Collision detection
        intent_signals = result.get('intent_signals', [])
        collision = None
        if intent_signals:
            collision = check_cg_collision(sig.account_id, intent_signals)

        if collision:
            logger.info(
                "Signal %s: CG collision detected — %s",
                sig.signal_id, collision.get('reason', ''),
            )
            try:
                sig.alert_suppressed = True
                sig.composite_signal_id = str(collision['cg_node_id'])
            except Exception:
                pass
        else:
            # Step 5: Create ContextNode for intents without CG equivalents
            if should_create_qualitative_node(intent_signals):
                self._create_qualitative_cg_node(
                    sig, customer_id, intent_signals, result,
                )

        db.session.commit()
        return 1

    def _create_qualitative_cg_node(self, sig, customer_id, intent_signals, enrichment):
        """Create a new ContextNode for QSIM signals without CG equivalents."""
        try:
            from models import ContextNode
            from extensions import db

            intents_str = ', '.join(intent_signals[:3])
            node = ContextNode(
                account_id=sig.account_id,
                customer_id=customer_id,
                node_type='SIGNAL',
                source='system',
                node_subtype='qualitative_signal',
                title=f'QSIM: {intents_str}',
                properties={
                    'signal_id': sig.signal_id,
                    'intent_signals': intent_signals,
                    'sentiment_score': enrichment.get('sentiment_score'),
                    'urgency_score': enrichment.get('urgency_score'),
                    'source_type': sig.source_type,
                    'suggested_action': enrichment.get('suggested_action'),
                    'auto_created': True,
                },
                tier=2,
                occurred_at=sig.signal_date or datetime.utcnow(),
                source_platform='qsim_enrichment',
            )
            db.session.add(node)
            db.session.flush()

            logger.info(
                "Signal %s: created ContextNode %d (qualitative_signal) for intents: %s",
                sig.signal_id, node.node_id, intents_str,
            )
        except Exception as e:
            logger.warning("Failed to create qualitative CG node for %s: %s", sig.signal_id, e)
