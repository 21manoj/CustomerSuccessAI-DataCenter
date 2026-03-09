#!/usr/bin/env python3
"""
Context Graph Regeneration Subscriber

Automatically regenerates context graph data when account health scores
cross classification boundaries (Critical <50 / At-Risk 50-69 / Healthy 70+).

This ensures:
  - Story arcs match current health profiles (churn arcs for critical,
    expansion arcs for healthy)
  - Wizard B milestone logic stays consistent (churn milestones for
    critical accounts, expansion milestones for healthy accounts)
  - Graph Overview and Story Arcs UI show coherent, matching data

Event chain:
    KPI Upload → HealthScoreRollupSubscriber → HEALTH_SCORES_UPDATED
    → ContextGraphRegenerationSubscriber (this) → regenerate arcs
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from event_system import Event, EventType

logger = logging.getLogger(__name__)


# Health classification boundaries (matches health_thresholds.json)
def _classify(score: float) -> str:
    """Classify health score. Critical <50, At-Risk 50-69, Healthy 70+."""
    if score < 50:
        return 'critical'
    elif score < 70:
        return 'at_risk'
    return 'healthy'


class ContextGraphRegenerationSubscriber:
    """Regenerates context graph data when account health crosses thresholds.

    Listens to HEALTH_SCORES_UPDATED events. When an account's health
    classification changes (e.g., at_risk → healthy), triggers a full
    context graph regeneration for the customer. All accounts get their
    arcs re-assigned based on current health scores, ensuring consistency
    with Wizard B milestones.

    Features:
    - In-memory health classification cache (populated on first events)
    - Per-customer cooldown prevents regeneration thrashing
    - Background thread for regeneration (doesn't block event queue)
    - Feature toggle check (skips if context graph disabled)
    - Idempotent: re-running is safe (old data is cleared before insert)
    """

    def __init__(self, cooldown_seconds: int = 300):
        """
        Args:
            cooldown_seconds: Minimum time between regenerations per customer.
                              Default 300s (5 minutes). Set to 0 to disable.
        """
        self._health_cache: Dict[int, str] = {}  # account_id → classification
        self._cooldown = cooldown_seconds
        self._last_regen: Dict[int, float] = {}  # customer_id → timestamp
        self._lock = threading.Lock()
        self._pending_regens: set = set()  # customer_ids with regen in progress
        logger.info(
            f"ContextGraphRegenerationSubscriber initialized "
            f"(cooldown={cooldown_seconds}s)"
        )

    def handle_event(self, event: Event):
        """Handle HEALTH_SCORES_UPDATED events.

        Checks if the account's health classification has changed.
        If so, triggers context graph regeneration for the customer.
        """
        if event.event_type != EventType.HEALTH_SCORES_UPDATED:
            return

        try:
            account_id = event.data.get('account_id')
            new_score = event.data.get('overall_health_score')
            customer_id = event.customer_id

            if account_id is None or new_score is None:
                return

            # Ensure numeric types
            account_id = int(account_id)
            new_score = float(new_score)
            new_class = _classify(new_score)
            old_class = self._health_cache.get(account_id)

            # Update cache
            self._health_cache[account_id] = new_class

            if old_class is None:
                # First time seeing this account — seed cache, don't regenerate
                logger.debug(
                    f"Context graph: cached initial health for account "
                    f"{account_id}: {new_class} ({new_score:.1f})"
                )
                return

            if old_class == new_class:
                # No classification change — nothing to do
                return

            # ── Classification changed! ──────────────────────────────────

            # Check feature toggle
            if not self._is_context_graph_enabled(customer_id):
                logger.debug(
                    f"Context graph not enabled for customer {customer_id}, "
                    f"skipping regeneration"
                )
                return

            # Check cooldown
            with self._lock:
                last = self._last_regen.get(customer_id, 0)
                elapsed = time.time() - last
                if elapsed < self._cooldown:
                    logger.info(
                        f"Context graph regen for customer {customer_id} "
                        f"skipped (cooldown: {self._cooldown - elapsed:.0f}s remaining)"
                    )
                    return

                # Check if regen already in progress
                if customer_id in self._pending_regens:
                    logger.info(
                        f"Context graph regen for customer {customer_id} "
                        f"already in progress, skipping"
                    )
                    return

                # Mark regen in progress and update timestamp
                self._pending_regens.add(customer_id)
                self._last_regen[customer_id] = time.time()

            logger.info(
                f"Context graph: account {account_id} health changed "
                f"{old_class} → {new_class} (score={new_score:.1f}). "
                f"Triggering regeneration for customer {customer_id}."
            )

            # Spawn background thread for the heavy lifting
            regen_thread = threading.Thread(
                target=self._regenerate_customer,
                args=(customer_id,),
                name=f"context-graph-regen-{customer_id}",
                daemon=True,
            )
            regen_thread.start()

        except Exception as e:
            logger.error(
                f"Error in ContextGraphRegenerationSubscriber: {e}",
                exc_info=True,
            )

    def _is_context_graph_enabled(self, customer_id: int) -> bool:
        """Check if context graph feature toggle is on for this customer."""
        try:
            from feature_toggles import is_context_graph_enabled
            return is_context_graph_enabled(customer_id)
        except ImportError:
            return False

    def _regenerate_customer(self, customer_id: int):
        """Regenerate context graph data for a customer.

        Runs in a background thread. Uses Flask app context for DB access.

        Steps:
        1. Query current health scores for all accounts
        2. Build per-account arc assignment map
        3. Generate 9 context graph CSVs
        4. Clear old context graph data from DB
        5. Ingest new data into DB
        """
        start_time = time.time()
        try:
            # Get Flask app for DB context
            from app_v3_minimal import app

            with app.app_context():
                self._do_regeneration(customer_id)

            duration = time.time() - start_time
            logger.info(
                f"Context graph regeneration completed for customer "
                f"{customer_id} in {duration:.1f}s"
            )

            # Update the health cache for all accounts (so we have fresh state)
            self._refresh_cache(customer_id)

        except Exception as e:
            logger.error(
                f"Context graph regeneration failed for customer "
                f"{customer_id}: {e}",
                exc_info=True,
            )
        finally:
            with self._lock:
                self._pending_regens.discard(customer_id)

    def _do_regeneration(self, customer_id: int):
        """Core regeneration logic (must run within Flask app context)."""
        from scripts.generate_context_graph_data import (
            ContextGraphGenerator,
            build_health_arc_map,
            _query_health_scores,
        )
        from extensions import db

        # Step 1: Query current health scores
        health_scores = _query_health_scores(customer_id, num_accounts=10)
        if not health_scores:
            logger.warning(
                f"No health scores found for customer {customer_id}, "
                f"skipping context graph regeneration"
            )
            return

        # Step 2: Build per-account arc map
        arc_map = build_health_arc_map(
            customer_id=customer_id,
            num_accounts=len(health_scores),
            health_scores=health_scores,
            seed=42,
        )

        # Log assignments
        from scripts.generate_context_graph_data import classify_health
        for acct_id in sorted(arc_map.keys()):
            score = health_scores.get(acct_id, 65.0)
            cls = classify_health(score)
            logger.info(
                f"  Arc assignment: {acct_id} health={score:.1f} "
                f"({cls}) → {arc_map[acct_id]}"
            )

        # Step 3: Generate 9 CSVs
        backend_dir = Path(__file__).parent
        output_dir = str(
            backend_dir / 'verticals' /
            f'customer{customer_id}-dc2_s' / 'data' / 'context_graph'
        )

        gen = ContextGraphGenerator(
            customer_id=customer_id,
            num_accounts=len(health_scores),
            seed=42,
            account_arc_map=arc_map,
        )
        files = gen.generate_all(output_dir)
        logger.info(
            f"Generated {len(files)} context graph CSV files in {output_dir}"
        )

        # Save arc assignments for reference
        assignments_file = Path(output_dir) / '_arc_assignments.json'
        assignments_data = {
            'customer_id': customer_id,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'trigger': 'health_threshold_crossing',
            'seed': 42,
            'accounts': {
                str(acct_id): {
                    'arc_id': arc_map[acct_id],
                    'health_score': health_scores.get(acct_id, 65.0),
                    'health_class': classify_health(
                        health_scores.get(acct_id, 65.0)
                    ),
                }
                for acct_id in sorted(arc_map.keys())
            }
        }
        assignments_file.write_text(json.dumps(assignments_data, indent=2))

        # Step 4 & 5: Clear old data and ingest new CSVs
        data_dir = Path(output_dir)
        engine = db.engine

        from onboarding_api_v2_config_aware import ingest_context_graph_csvs
        result = ingest_context_graph_csvs(customer_id, data_dir, engine)

        logger.info(
            f"Context graph ingestion: "
            f"{result['nodes_inserted']} nodes, "
            f"{result['edges_inserted']} edges, "
            f"{len(result['files_loaded'])} files"
        )
        if result['errors']:
            for err in result['errors'][:5]:
                logger.warning(f"  Ingestion warning: {err}")

    def _refresh_cache(self, customer_id: int):
        """Refresh the health classification cache for all accounts.

        Called after regeneration to ensure the cache matches DB state.
        """
        try:
            from app_v3_minimal import app
            with app.app_context():
                from scripts.generate_context_graph_data import _query_health_scores
                scores = _query_health_scores(customer_id, num_accounts=10)
                for acct_id, score in scores.items():
                    self._health_cache[acct_id] = _classify(score)
                logger.debug(
                    f"Refreshed health cache for {len(scores)} accounts "
                    f"(customer {customer_id})"
                )
        except Exception as e:
            logger.warning(f"Could not refresh health cache: {e}")

    def get_status(self) -> Dict:
        """Return subscriber status for observability."""
        return {
            'cached_accounts': len(self._health_cache),
            'pending_regenerations': list(self._pending_regens),
            'cooldown_seconds': self._cooldown,
            'last_regenerations': {
                str(cid): datetime.fromtimestamp(ts).isoformat()
                for cid, ts in self._last_regen.items()
            },
            'cache': {
                str(acct_id): cls
                for acct_id, cls in sorted(self._health_cache.items())
            },
        }
