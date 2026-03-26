#!/usr/bin/env python3
"""
Layer C — Context Graph Urgent Pre-emption Scanner
===================================================

Scans ContextEdge records for high-confidence edges pointing to OUTCOME nodes
with large negative revenue impact AND an imminent renewal date.

Triggered:
  - After ingest_context_graph_csvs() completes
  - Optionally after _process_data_impl() health score write

Logic per account:
  1. Fetch ContextEdge rows where confidence >= CONFIDENCE_MIN for the account.
  2. For each edge, check if to_node is an OUTCOME node with revenue_impact < -REVENUE_RISK_MIN.
  3. Check account.profile_metadata.renewal_date; skip gracefully if NULL.
  4. Compute urgency = abs(revenue_impact) * confidence / max(days_to_renewal, 1).
  5. If urgency > URGENCY_THRESHOLD: create Notification(type='urgent_alert', priority='critical').

Errors are fully contained — never crash the calling pipeline.
"""

import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# ── Calibration constants ──
URGENCY_THRESHOLD = 5_000   # urgency score above which we alert
CONFIDENCE_MIN    = 0.85    # minimum edge confidence to consider
REVENUE_RISK_MIN  = 50_000  # $50K minimum revenue_impact (absolute) to alert
RENEWAL_WINDOW    = 60      # days — renewal within this window multiplies urgency


def scan_for_urgent_signals(customer_id: int, account_id: int) -> list:
    """
    Scan context graph edges for high-urgency revenue risk signals for one account.

    Args:
        customer_id: Customer scope.
        account_id:  Account to scan.

    Returns:
        List of alert payload dicts for each Notification created.
        Returns [] on any error (never raises).
    """
    alerts_created = []

    try:
        from models import ContextEdge, ContextNode, Notification, Account, db

        # ── 1. Get renewal date from account profile_metadata ──
        account = db.session.get(Account, account_id)
        renewal_date: Optional[date] = None
        days_to_renewal: Optional[int] = None

        if account:
            meta = account.profile_metadata or {}
            rd_raw = meta.get('renewal_date') or meta.get('contract_renewal_date')
            if rd_raw:
                try:
                    if isinstance(rd_raw, (date, datetime)):
                        renewal_date = rd_raw if isinstance(rd_raw, date) else rd_raw.date()
                    else:
                        renewal_date = datetime.strptime(str(rd_raw)[:10], '%Y-%m-%d').date()
                    days_to_renewal = (renewal_date - date.today()).days
                except (ValueError, TypeError, AttributeError):
                    pass  # NULL renewal_date — handled below

        # ── 2. Fetch high-confidence edges for this account ──
        # Join to to_node inline — avoid N+1 with explicit node fetch
        edges = (
            ContextEdge.query
            .filter(
                ContextEdge.customer_id == customer_id,
                ContextEdge.confidence >= CONFIDENCE_MIN,
            )
            .join(
                ContextNode,
                ContextEdge.to_node_id == ContextNode.node_id,
            )
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'OUTCOME',
                ContextNode.revenue_impact.isnot(None),
                ContextNode.revenue_impact < -REVENUE_RISK_MIN,
            )
            .all()
        )

        if not edges:
            return []

        for edge in edges:
            try:
                to_node = db.session.get(ContextNode, edge.to_node_id)
                if not to_node:
                    continue

                revenue_impact = float(to_node.revenue_impact)
                confidence     = float(edge.confidence) if edge.confidence else 0.0

                # ── 3. Urgency formula ──
                # When renewal_date is unknown, use RENEWAL_WINDOW as denominator
                # (treats account as "always in the renewal window").
                denom = max(days_to_renewal, 1) if (days_to_renewal is not None) else RENEWAL_WINDOW
                urgency = abs(revenue_impact) * confidence / denom

                if urgency <= URGENCY_THRESHOLD:
                    continue

                # ── 4. Build alert payload ──
                account_name = account.account_name if account else f"Account {account_id}"
                payload = {
                    'account_id':       account_id,
                    'account_name':     account_name,
                    'edge_id':          edge.edge_id,
                    'edge_type':        edge.edge_type,
                    'confidence':       confidence,
                    'revenue_impact':   revenue_impact,
                    'days_to_renewal':  days_to_renewal,
                    'renewal_date':     renewal_date.isoformat() if renewal_date else None,
                    'urgency_score':    round(urgency, 1),
                    'outcome_title':    to_node.title or f'Outcome node {to_node.node_id}',
                    'outcome_subtype':  to_node.node_subtype,
                    'detected_at':      datetime.utcnow().isoformat(),
                }

                # ── 5. Store Notification ──
                notification = Notification(
                    customer_id=customer_id,
                    account_id=account_id,
                    type='urgent_alert',
                    priority='critical',
                    payload=payload,
                )
                db.session.add(notification)
                db.session.commit()

                alerts_created.append(payload)

                logger.warning(
                    f"urgent_signal_scanner: ALERT customer={customer_id} "
                    f"account={account_id} ({account_name}) "
                    f"revenue_impact={revenue_impact:,.0f} "
                    f"confidence={confidence:.2f} "
                    f"days_to_renewal={days_to_renewal} "
                    f"urgency={urgency:.1f}"
                )

            except Exception as edge_err:
                logger.error(
                    f"urgent_signal_scanner: error processing edge {edge.edge_id}: {edge_err}",
                    exc_info=True,
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass

    except Exception as e:
        logger.error(
            f"urgent_signal_scanner: scan failed for account {account_id}: {e}",
            exc_info=True,
        )
        try:
            from extensions import db as _db
            _db.session.rollback()
        except Exception:
            pass

    return alerts_created
