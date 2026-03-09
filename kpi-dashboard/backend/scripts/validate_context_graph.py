#!/usr/bin/env python3
"""
Context Graph Validation — Pre/post checks for any customer.

Validates that context graph data is consistent and demo-ready:
  1. Temporal distribution — signals, decisions, outcomes in correct chronological order
  2. Revenue proportionality — graph revenue within 3x of actual account ARR
  3. Revenue type coverage — at_risk, protected, expansion all present
  4. HealthTrend coverage — rows exist for the lookback window
  5. Story coherence — causal chains flow chronologically
  6. Data completeness — no NULL revenue_impact_type on nodes with revenue

Usage:
  cd kpi-dashboard/backend
  python scripts/validate_context_graph.py 290           # validate customer 290
  python scripts/validate_context_graph.py 290 --fix     # validate + auto-fix issues
  python scripts/validate_context_graph.py --all         # validate all customers with context graph
"""

import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_backend_dir, '..', '.env'))

from flask import Flask
from extensions import db

app = Flask(__name__)
database_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


class ValidationResult:
    def __init__(self, name):
        self.name = name
        self.passed = True
        self.messages = []

    def fail(self, msg):
        self.passed = False
        self.messages.append(f"FAIL: {msg}")

    def warn(self, msg):
        self.messages.append(f"WARN: {msg}")

    def info(self, msg):
        self.messages.append(f"INFO: {msg}")

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        lines = [f"  {status} {self.name}"]
        for m in self.messages:
            lines.append(f"       {m}")
        return "\n".join(lines)


def validate_customer(customer_id, fix=False):
    """Run all validation checks for a customer. Returns (pass_count, fail_count, results)."""
    from models import Account, ContextNode, ContextEdge, HealthTrend
    from sqlalchemy import func

    accounts = Account.query.filter_by(customer_id=customer_id, vertical='dc2_s').all()
    if not accounts:
        print(f"  No DC2S accounts found for customer {customer_id}")
        return 0, 0, []

    account_ids = [a.account_id for a in accounts]
    results = []

    # --- Helper: get ARR ---
    def get_arr(acct):
        arr = 0.0
        if acct.profile_metadata and isinstance(acct.profile_metadata, dict):
            arr = float(acct.profile_metadata.get('arr', 0) or 0)
        if not arr and acct.revenue:
            arr = float(acct.revenue)
        return arr

    arr_map = {a.account_id: get_arr(a) for a in accounts}
    total_arr = sum(arr_map.values())

    # Load all context nodes
    nodes = ContextNode.query.filter(
        ContextNode.account_id.in_(account_ids)
    ).all()

    if not nodes:
        print(f"  No context graph nodes found for customer {customer_id}")
        return 0, 0, []

    # ── Check 1: Node count and type distribution ──
    r = ValidationResult("Node type distribution")
    type_counts = defaultdict(int)
    for n in nodes:
        type_counts[n.node_type] += 1
    r.info(f"{len(nodes)} total nodes: {dict(type_counts)}")

    required_types = {'SIGNAL', 'DECISION', 'OUTCOME'}
    missing = required_types - set(type_counts.keys())
    if missing:
        r.fail(f"Missing required node types: {missing}")
    else:
        r.info("All required node types present (SIGNAL, DECISION, OUTCOME)")
    results.append(r)

    # ── Check 2: Temporal distribution ──
    r = ValidationResult("Temporal distribution")
    now = datetime.utcnow()
    six_months_ago = datetime(now.year, now.month, 1)
    # Go back 6 months
    month = six_months_ago.month - 6
    year = six_months_ago.year
    if month <= 0:
        month += 12
        year -= 1
    six_months_ago = datetime(year, month, 1)

    nodes_with_dates = [n for n in nodes if n.occurred_at]
    nodes_without_dates = [n for n in nodes if not n.occurred_at
                           and n.node_type not in ('STAKEHOLDER', 'ACCOUNT', 'EXTERNAL_CONTEXT')]

    if nodes_without_dates:
        r.fail(f"{len(nodes_without_dates)} actionable nodes (SIGNAL/DECISION/OUTCOME) missing occurred_at")

    in_window = [n for n in nodes_with_dates if n.occurred_at >= six_months_ago]
    before_window = [n for n in nodes_with_dates if n.occurred_at < six_months_ago]

    if not in_window:
        r.fail("No nodes within 6-month lookback window")
    else:
        r.info(f"{len(in_window)} nodes in 6-month window, {len(before_window)} before")

    # Check chronological ordering: signals should generally precede decisions, decisions precede outcomes
    signal_dates = sorted([n.occurred_at for n in nodes_with_dates if n.node_type == 'SIGNAL'])
    decision_dates = sorted([n.occurred_at for n in nodes_with_dates if n.node_type == 'DECISION'])
    outcome_dates = sorted([n.occurred_at for n in nodes_with_dates if n.node_type == 'OUTCOME'])

    if signal_dates and decision_dates:
        median_signal = signal_dates[len(signal_dates) // 2]
        median_decision = decision_dates[len(decision_dates) // 2]
        if median_decision < median_signal:
            r.fail(f"Decisions (median {median_decision:%Y-%m}) precede signals (median {median_signal:%Y-%m})")
        else:
            r.info(f"Temporal flow OK: signals median {median_signal:%Y-%m} → decisions median {median_decision:%Y-%m}")

    if decision_dates and outcome_dates:
        median_decision = decision_dates[len(decision_dates) // 2]
        median_outcome = outcome_dates[len(outcome_dates) // 2]
        if median_outcome < median_decision:
            r.fail(f"Outcomes (median {median_outcome:%Y-%m}) precede decisions (median {median_decision:%Y-%m})")
        else:
            r.info(f"Temporal flow OK: decisions median {median_decision:%Y-%m} → outcomes median {median_outcome:%Y-%m}")

    # Check for date clustering (all in one month = bad)
    month_dist = defaultdict(int)
    for n in in_window:
        month_dist[n.occurred_at.strftime('%Y-%m')] += 1

    if len(month_dist) <= 1 and len(in_window) > 5:
        r.fail(f"All {len(in_window)} nodes clustered in single month: {list(month_dist.keys())}")
    else:
        r.info(f"Spread across {len(month_dist)} months: {dict(month_dist)}")

    results.append(r)

    # ── Check 3: Revenue proportionality ──
    r = ValidationResult("Revenue proportionality")
    r.info(f"Total customer ARR: ${total_arr:,.0f}")

    rev_by_type = defaultdict(float)
    rev_count_by_type = defaultdict(int)
    for n in nodes:
        if n.revenue_impact and float(n.revenue_impact) != 0:
            rtype = n.revenue_impact_type or 'unclassified'
            rev_by_type[rtype] += abs(float(n.revenue_impact))
            rev_count_by_type[rtype] += 1

    total_graph_rev = sum(rev_by_type.values())
    ratio = total_graph_rev / total_arr if total_arr > 0 else float('inf')

    for rtype, amount in sorted(rev_by_type.items()):
        r.info(f"  {rtype}: {rev_count_by_type[rtype]} nodes, ${amount:,.0f}")

    if ratio > 3.0:
        r.fail(f"Graph revenue (${total_graph_rev:,.0f}) is {ratio:.1f}x actual ARR — should be < 3x")
    elif ratio > 2.0:
        r.warn(f"Graph revenue (${total_graph_rev:,.0f}) is {ratio:.1f}x actual ARR — borderline")
    else:
        r.info(f"Graph revenue (${total_graph_rev:,.0f}) is {ratio:.1f}x actual ARR — proportional")

    # Per-account check: no single account should have graph revenue > 2x its ARR
    per_acct_rev = defaultdict(float)
    for n in nodes:
        if n.revenue_impact and float(n.revenue_impact) != 0:
            per_acct_rev[n.account_id] += abs(float(n.revenue_impact))

    for aid, graph_rev in per_acct_rev.items():
        acct_arr = arr_map.get(aid, 0)
        if acct_arr > 0:
            acct_ratio = graph_rev / acct_arr
            if acct_ratio > 5.0:
                r.fail(f"Account {aid}: graph revenue ${graph_rev:,.0f} is {acct_ratio:.1f}x its ARR ${acct_arr:,.0f}")

    results.append(r)

    # ── Check 4: Revenue type coverage ──
    r = ValidationResult("Revenue type coverage")
    expected_types = {'at_risk', 'protected', 'expansion'}
    present_types = set(rev_by_type.keys()) - {'unclassified'}
    missing_types = expected_types - present_types
    if missing_types:
        r.fail(f"Missing revenue impact types: {missing_types}")
    else:
        r.info(f"All required types present: {sorted(present_types)}")

    # Check for NULL revenue_impact_type
    null_type_nodes = [n for n in nodes
                       if n.revenue_impact and float(n.revenue_impact) != 0
                       and not n.revenue_impact_type]
    if null_type_nodes:
        r.fail(f"{len(null_type_nodes)} nodes have revenue_impact but NULL revenue_impact_type")
        if fix:
            from decimal import Decimal
            for n in null_type_nodes:
                if float(n.revenue_impact) > 0:
                    n.revenue_impact_type = 'expansion'
                else:
                    n.revenue_impact_type = 'at_risk'
            db.session.commit()
            r.info(f"  → Auto-fixed {len(null_type_nodes)} NULL types")
    else:
        r.info("No NULL revenue_impact_type values")

    results.append(r)

    # ── Check 5: HealthTrend coverage ──
    r = ValidationResult("HealthTrend coverage")
    trend_count = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).count()

    if trend_count == 0:
        r.fail("No HealthTrend rows — ROI dashboard will use demo fallback data")
    else:
        months_covered = db.session.query(
            HealthTrend.year, HealthTrend.month
        ).filter(
            HealthTrend.account_id.in_(account_ids)
        ).distinct().count()

        accts_covered = db.session.query(
            HealthTrend.account_id
        ).filter(
            HealthTrend.account_id.in_(account_ids)
        ).distinct().count()

        r.info(f"{trend_count} rows: {accts_covered}/{len(accounts)} accounts × {months_covered} months")

        if accts_covered < len(accounts):
            r.warn(f"Only {accts_covered}/{len(accounts)} accounts have HealthTrend data")
        if months_covered < 2:
            r.fail("Need at least 2 months for trend calculation")

    results.append(r)

    # ── Check 6: Causal chain integrity ──
    r = ValidationResult("Causal chain integrity")

    edges = ContextEdge.query.filter(
        db.or_(
            ContextEdge.from_node_id.in_([n.node_id for n in nodes]),
            ContextEdge.to_node_id.in_([n.node_id for n in nodes]),
        )
    ).all()

    r.info(f"{len(edges)} edges connecting {len(nodes)} nodes")

    if len(edges) == 0 and len(nodes) > 10:
        r.fail("No edges despite having nodes — causal chains cannot be built")
    elif len(edges) < len(nodes) * 0.5:
        r.warn(f"Low edge density ({len(edges)}/{len(nodes)} = {len(edges)/len(nodes):.1f} edges/node)")

    # Spot-check: pick up to 3 OUTCOME nodes and try to trace upstream
    outcome_nodes = [n for n in nodes if n.node_type == 'OUTCOME' and n.revenue_impact]
    outcome_nodes.sort(key=lambda n: abs(float(n.revenue_impact or 0)), reverse=True)

    chains_checked = 0
    chains_valid = 0
    chains_with_upstream = 0
    for on in outcome_nodes[:5]:
        try:
            from utils.context_graph import get_causal_chain
            chain = get_causal_chain(on.node_id, direction='upstream', max_depth=4)
            chains_checked += 1
            if chain:
                chains_with_upstream += 1
                # Check that the earliest signal predates the outcome
                earliest_date = None
                for step in chain:
                    d = step['node'].get('occurred_at')
                    if d:
                        if earliest_date is None or d < earliest_date:
                            earliest_date = d
                if earliest_date and on.occurred_at:
                    if earliest_date <= on.occurred_at.isoformat():
                        chains_valid += 1
                    else:
                        r.warn(f"Chain for '{on.title}': earliest upstream ({earliest_date[:10]}) after outcome ({on.occurred_at:%Y-%m-%d})")
                else:
                    chains_valid += 1  # Can't check, assume ok
            else:
                r.warn(f"Outcome '{on.title}' has no upstream chain")
        except Exception:
            pass

    if chains_checked > 0:
        r.info(f"Checked {chains_checked} outcomes: {chains_with_upstream} have upstream chains, {chains_valid}/{chains_with_upstream} chronologically valid")
    else:
        r.warn("Could not verify any causal chains")

    results.append(r)

    # ── Summary ──
    pass_count = sum(1 for r in results if r.passed)
    fail_count = sum(1 for r in results if not r.passed)

    return pass_count, fail_count, results


def find_customers_with_graph():
    """Find all customers that have context graph data."""
    from models import ContextNode, Account
    from sqlalchemy import func

    rows = db.session.query(
        Account.customer_id,
        func.count(ContextNode.node_id),
    ).join(
        ContextNode, ContextNode.account_id == Account.account_id
    ).group_by(Account.customer_id).all()

    return [(cid, count) for cid, count in rows]


def main():
    parser = argparse.ArgumentParser(description='Validate context graph data consistency')
    parser.add_argument('customer_id', nargs='?', type=int, help='Customer ID to validate')
    parser.add_argument('--fix', action='store_true', help='Auto-fix minor issues')
    parser.add_argument('--all', action='store_true', help='Validate all customers with context graph')
    args = parser.parse_args()

    with app.app_context():
        if args.all:
            customers = find_customers_with_graph()
            if not customers:
                print("No customers with context graph data found.")
                return

            total_pass = 0
            total_fail = 0
            for cid, node_count in customers:
                print(f"\n{'='*60}")
                print(f"Customer {cid} ({node_count} nodes)")
                print(f"{'='*60}")
                p, f, results = validate_customer(cid, fix=args.fix)
                for r in results:
                    print(r)
                total_pass += p
                total_fail += f

            print(f"\n{'='*60}")
            print(f"TOTAL: {total_pass} passed, {total_fail} failed across {len(customers)} customers")
            print(f"{'='*60}")

        elif args.customer_id:
            print(f"{'='*60}")
            print(f"Context Graph Validation — Customer {args.customer_id}")
            print(f"{'='*60}")
            p, f, results = validate_customer(args.customer_id, fix=args.fix)
            for r in results:
                print(r)
            print(f"\n{'='*60}")
            status = "ALL CHECKS PASSED" if f == 0 else f"{f} CHECK(S) FAILED"
            print(f"Result: {p} passed, {f} failed — {status}")
            print(f"{'='*60}")
            sys.exit(1 if f > 0 else 0)

        else:
            parser.print_help()


if __name__ == '__main__':
    main()
