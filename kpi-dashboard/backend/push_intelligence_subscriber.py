#!/usr/bin/env python3
"""
Push Intelligence Subscriber
=============================

Wires the three "push" layers into the event bus so they fire automatically:

  Layer A  – Signal Analyst  (already wired via OnboardingCompleteSubscriber)
  Layer B  – Arc → Playbook auto-dispatch  (NEW — this file)
  Layer C  – Urgent Revenue Scanner        (NEW — this file)

Event triggers:
  HEALTH_SCORES_UPDATED  →  Layer C immediate scan  (revenue at-risk)
  HEALTH_SCORES_UPDATED  →  Layer B arc→playbook     (if arc detected + auto_trigger_on_arc)

Also provides a DailyScheduler that calls process_data once every 24 h
for every active customer with fresh data.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  Layer C — Urgent Scanner Subscriber  (fires IMMEDIATELY on CG update)
# ─────────────────────────────────────────────────────────────────────

class UrgentScannerSubscriber:
    """
    Listens to HEALTH_SCORES_UPDATED.
    For each account whose health changed, runs the Layer C urgent
    scanner right away — no waiting for cron.

    Debounce: max once per account per 5 minutes.
    """

    def __init__(self, cooldown_seconds: int = 300):
        self._cooldown = cooldown_seconds
        self._last_scan: dict[int, float] = {}  # account_id → timestamp
        self._lock = threading.Lock()

    def handle_event(self, event) -> None:
        try:
            customer_id = event.customer_id
            data = event.data or {}
            account_id = data.get('account_id')
            if not account_id:
                return

            # Cooldown per account
            with self._lock:
                now = time.time()
                last = self._last_scan.get(account_id, 0)
                if now - last < self._cooldown:
                    return
                self._last_scan[account_id] = now

            # Non-blocking scan in background thread
            t = threading.Thread(
                target=self._scan,
                args=(customer_id, account_id),
                name=f"urgent-scan-{account_id}",
                daemon=True,
            )
            t.start()

        except Exception as e:
            logger.error(f"UrgentScannerSubscriber error: {e}", exc_info=True)

    def _scan(self, customer_id: int, account_id: int) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            # No app context — get it from the global
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("UrgentScannerSubscriber: no Flask app available")
                return

        with app.app_context():
            try:
                from utils.urgent_signal_scanner import scan_for_urgent_signals
                alerts = scan_for_urgent_signals(customer_id, account_id)
                if alerts:
                    logger.info(
                        f"Layer C: {len(alerts)} urgent alert(s) for "
                        f"customer {customer_id} / account {account_id}"
                    )
            except Exception as e:
                logger.debug(f"Layer C scan skipped for {account_id}: {e}")


# ─────────────────────────────────────────────────────────────────────
#  Layer B — Arc → Playbook Auto-Dispatch Subscriber
# ─────────────────────────────────────────────────────────────────────

class ArcPlaybookSubscriber:
    """
    Listens to HEALTH_SCORES_UPDATED.
    When an account's health crosses a boundary (e.g. healthy→at_risk),
    checks for arc classifications and triggers playbook validation via
    the Layer B validator.

    If confidence > 0.8 → auto-approve → publish PLAYBOOK_AUTO_TRIGGERED.
    If 0.4 ≤ confidence ≤ 0.8 → queue for CSM manual review.
    If confidence < 0.4 → auto-reject.
    """

    # Mapping from arc_type → recommended playbook_id
    ARC_PLAYBOOK_MAP = {
        'crisis':           'PB-DC-01',   # Emergency intervention
        'champion_loss':    'PB-DC-02',   # Stakeholder re-engagement
        'budget_pressure':  'PB-DC-03',   # ROI demonstration
        'silent_churn':     'PB-DC-04',   # Re-engagement campaign
        'expansion':        'PB-DC-05',   # Expansion nurture
        'recovery':         'PB-DC-06',   # Recovery playbook
        'onboarding':       'PB-DC-01',   # Onboarding acceleration
        'stable':           None,         # No playbook needed
    }

    def __init__(self, cooldown_seconds: int = 600):
        self._cooldown = cooldown_seconds
        self._last_eval: dict[int, float] = {}  # account_id → timestamp
        self._lock = threading.Lock()

    def handle_event(self, event) -> None:
        try:
            import utils.push_intelligence_config as pic
            if not pic.layer_b_enabled():
                return
            if not pic.auto_trigger_on_arc():
                return

            customer_id = event.customer_id
            data = event.data or {}
            account_id = data.get('account_id')
            new_score = data.get('score') or data.get('health_score')
            if not account_id or new_score is None:
                return

            # Only trigger for at-risk or critical accounts
            from utils.health_thresholds import classify
            cls = classify(float(new_score))
            if cls == 'healthy':
                return

            # Cooldown per account
            with self._lock:
                now = time.time()
                last = self._last_eval.get(account_id, 0)
                if now - last < self._cooldown:
                    return
                self._last_eval[account_id] = now

            # Evaluate in background thread
            t = threading.Thread(
                target=self._evaluate,
                args=(customer_id, account_id, float(new_score)),
                name=f"arc-playbook-{account_id}",
                daemon=True,
            )
            t.start()

        except Exception as e:
            logger.error(f"ArcPlaybookSubscriber error: {e}", exc_info=True)

    def _evaluate(self, customer_id: int, account_id: int, health_score: float) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("ArcPlaybookSubscriber: no Flask app available")
                return

        with app.app_context():
            try:
                self._do_evaluate(customer_id, account_id, health_score)
            except Exception as e:
                logger.debug(f"Layer B eval skipped for {account_id}: {e}")

    def _do_evaluate(self, customer_id: int, account_id: int, health_score: float) -> None:
        from models import ContextNode, Account, PlaybookExecution, db
        from datetime import datetime
        import uuid

        # 1. Find the latest arc detection for this account
        arc_node = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'SIGNAL',
                ContextNode.node_subtype == 'arc_detection',
            )
            .order_by(ContextNode.occurred_at.desc())
            .first()
        )

        if not arc_node:
            return

        arc_type = (arc_node.properties or {}).get('arc_type', 'unknown')
        arc_confidence = (arc_node.properties or {}).get('confidence', 0.0)
        playbook_id = self.ARC_PLAYBOOK_MAP.get(arc_type)

        if not playbook_id:
            logger.debug(f"Arc type '{arc_type}' has no mapped playbook — skipping")
            return

        # 2. Check if we already have a recent execution for this account+playbook
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        existing = (
            PlaybookExecution.query
            .filter(
                PlaybookExecution.account_id == account_id,
                PlaybookExecution.playbook_id == playbook_id,
                PlaybookExecution.started_at > recent_cutoff,
                PlaybookExecution.status.in_(['in-progress', 'completed']),
            )
            .first()
        )
        if existing:
            logger.debug(
                f"Playbook {playbook_id} already running/completed for "
                f"account {account_id} within 7d — skipping"
            )
            return

        account = db.session.get(Account, account_id)
        account_name = account.account_name if account else f"Account {account_id}"

        # 3. Try LLM-based validation (Layer B), fall back to rule-based
        decision = 'auto_approved'
        confidence = arc_confidence
        reasoning = f"Arc '{arc_type}' detected with confidence {arc_confidence:.2f}"

        try:
            from playbook_trigger_validator import PlaybookTriggerValidator
            validator = PlaybookTriggerValidator()
            result = validator.validate_trigger(
                account_id=str(account_id),
                customer_id=customer_id,
                playbook_id=playbook_id,
                trigger_context={
                    'arc_type': arc_type,
                    'arc_confidence': arc_confidence,
                    'health_score': health_score,
                    'source': 'arc_detection',
                },
                account_name=account_name,
                health_score=health_score,
            )
            decision = result.decision.value if hasattr(result.decision, 'value') else str(result.decision)
            confidence = result.confidence
            reasoning = result.reasoning
        except Exception as e:
            # Fallback: use arc confidence directly
            logger.debug(f"LLM validation unavailable, using rule-based: {e}")
            if health_score < 50 and arc_confidence >= 0.7:
                decision = 'auto_approved'
                confidence = arc_confidence
            elif health_score < 70:
                decision = 'pending_manual_approval'
                confidence = arc_confidence * 0.8
            else:
                decision = 'auto_rejected'
                confidence = arc_confidence * 0.5

        # 4. Act on decision
        if decision == 'auto_approved':
            execution = PlaybookExecution(
                execution_id=str(uuid.uuid4()),
                customer_id=customer_id,
                account_id=account_id,
                playbook_id=playbook_id,
                status='in-progress',
                started_at=datetime.utcnow(),
                execution_mode='auto_trigger',
                trigger_context={
                    'arc_type': arc_type,
                    'arc_confidence': arc_confidence,
                    'health_score': health_score,
                    'decision': decision,
                    'confidence': confidence,
                    'reasoning': reasoning,
                },
                llm_validation_result={
                    'decision': decision,
                    'confidence': confidence,
                    'reasoning': reasoning,
                },
            )
            db.session.add(execution)
            db.session.commit()

            logger.info(
                f"✅ Layer B AUTO-APPROVED: playbook {playbook_id} for "
                f"account {account_name} (arc={arc_type}, "
                f"confidence={confidence:.2f}, health={health_score:.1f})"
            )

            # Publish event for downstream PlaybookAutoTriggerSubscriber
            try:
                from event_system import event_manager, EventType
                event_manager.publisher.publish(
                    EventType.PLAYBOOK_AUTO_TRIGGERED,
                    customer_id,
                    {
                        'account_id': account_id,
                        'playbook_id': playbook_id,
                        'execution_id': execution.execution_id,
                        'arc_type': arc_type,
                        'trigger_source': 'arc_auto_dispatch',
                    },
                    priority=1,
                )
            except Exception as pub_err:
                logger.debug(f"Event publish failed (non-fatal): {pub_err}")

        elif decision == 'pending_manual_approval':
            logger.info(
                f"⏳ Layer B PENDING REVIEW: playbook {playbook_id} for "
                f"account {account_name} (arc={arc_type}, "
                f"confidence={confidence:.2f})"
            )
            # Create a notification for CSM review
            try:
                from models import Notification
                notif = Notification(
                    customer_id=customer_id,
                    account_id=account_id,
                    type='playbook_approval_needed',
                    priority='high',
                    payload={
                        'playbook_id': playbook_id,
                        'arc_type': arc_type,
                        'health_score': health_score,
                        'confidence': confidence,
                        'reasoning': reasoning,
                        'detected_at': datetime.utcnow().isoformat(),
                    },
                )
                db.session.add(notif)
                db.session.commit()
            except Exception:
                pass  # non-fatal

        else:
            logger.debug(
                f"Layer B REJECTED: playbook {playbook_id} for "
                f"account {account_name} (confidence={confidence:.2f})"
            )


# ─────────────────────────────────────────────────────────────────────
#  Daily Scheduler — runs process_data for all active customers
# ─────────────────────────────────────────────────────────────────────

class DailyProcessDataScheduler:
    """
    Background thread that fires process_data for every active customer
    once every interval (default 24 hours).

    - Runs as a daemon thread so it dies with the process.
    - Skips customers with no accounts or no recent data.
    - Fully non-blocking — errors never crash the app.
    """

    def __init__(self, interval_hours: int = 24):
        self._interval = interval_hours * 3600
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="daily-process-data",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            f"✅ Daily process_data scheduler started "
            f"(interval={self._interval // 3600}h)"
        )

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        # Wait 60s on startup to let the app fully initialize
        time.sleep(60)

        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"DailyScheduler cycle error: {e}", exc_info=True)

            # Sleep in 60s increments so we can stop quickly
            remaining = self._interval
            while remaining > 0 and self._running:
                time.sleep(min(remaining, 60))
                remaining -= 60

    def _run_cycle(self) -> None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except RuntimeError:
            try:
                from app_v3_minimal import app
            except ImportError:
                logger.debug("DailyScheduler: no Flask app available")
                return

        with app.app_context():
            from models import Customer, Account, db

            # Get all customers that have accounts (Customer model has no status column)
            customer_ids_rows = (
                db.session.query(Account.customer_id)
                .distinct()
                .all()
            )
            customer_ids_list = [r[0] for r in customer_ids_rows]
            customers = Customer.query.filter(
                Customer.customer_id.in_(customer_ids_list)
            ).all() if customer_ids_list else []

            if not customers:
                customer_ids = customer_ids_rows
                customer_ids = [c[0] for c in customer_ids]
            else:
                customer_ids = [c.customer_id for c in customers]

            logger.info(
                f"DailyScheduler: processing {len(customer_ids)} customers"
            )

            for cid in customer_ids:
                try:
                    self._process_customer(cid)
                except Exception as e:
                    logger.warning(f"DailyScheduler: customer {cid} failed: {e}")

    def _process_customer(self, customer_id: int) -> None:
        """Run health score recalculation for a single customer."""
        from models import Account, HealthScore, DC2SKPI, db
        from datetime import datetime, date

        # Only process if there's recent KPI data (within last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_kpi = (
            DC2SKPI.query
            .filter(
                DC2SKPI.customer_id == customer_id,
                DC2SKPI.uploaded_at >= week_ago,
            )
            .first()
        )

        if not recent_kpi:
            logger.debug(f"DailyScheduler: customer {customer_id} has no recent data — skipping")
            return

        # Recalculate health scores for all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        recalculated = 0

        for account in accounts:
            try:
                # Get previous health score for delta detection
                prev_score = None
                prev_hs = (
                    HealthScore.query
                    .filter_by(account_id=account.account_id)
                    .order_by(HealthScore.calculated_at.desc())
                    .first()
                )
                if prev_hs and prev_hs.health_score is not None:
                    prev_score = float(prev_hs.health_score)

                from utils.score_calculator import calculate_health_score
                score_result = calculate_health_score(account.account_id, customer_id)
                if score_result:
                    recalculated += 1
                    new_score = score_result.get('health_score')

                    # Publish health score update event → triggers Layer C + Layer B
                    try:
                        from event_system import event_manager, EventType
                        event_manager.publisher.publish(
                            EventType.HEALTH_SCORES_UPDATED,
                            customer_id,
                            {
                                'account_id': account.account_id,
                                'score': new_score,
                                'source': 'daily_scheduler',
                            },
                            priority=2,
                        )
                    except Exception:
                        pass

                    # Layer A: trigger Signal Analyst if health dropped >10pts
                    if (prev_score is not None and new_score is not None
                            and prev_score - new_score >= 10):
                        try:
                            from utils.signal_analyst import check_and_analyze
                            check_and_analyze(
                                customer_id=customer_id,
                                account_id=account.account_id,
                                health_before=prev_score,
                                health_after=float(new_score),
                            )
                            logger.info(
                                f"Layer A: health drop {prev_score:.0f}→{new_score:.0f} "
                                f"for account {account.account_id} — Signal Analyst triggered"
                            )
                        except Exception as sa_err:
                            logger.debug(f"Layer A skipped for {account.account_id}: {sa_err}")

            except Exception as e:
                logger.debug(f"DailyScheduler: account {account.account_id} recalc failed: {e}")

        if recalculated:
            logger.info(
                f"DailyScheduler: customer {customer_id} — "
                f"recalculated {recalculated}/{len(accounts)} accounts"
            )
