#!/usr/bin/env python3
"""
Fix Customer 290 Demo Data — Make ROI dashboard tell a coherent story.

Fixes three issues:
  1. No HealthTrend rows → generates 6 months of realistic health trends
  2. Context graph dates compressed to Jan-Sep 2025 → redistributes to Oct 2025-Mar 2026
  3. Context graph revenue 24x overstated vs actual ARR → scales proportional to account ARR

Run:
  cd kpi-dashboard/backend
  python scripts/fix_customer290_demo_data.py
"""

import os
import sys
import random
from datetime import datetime, date
from decimal import Decimal

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_backend_dir, '..', '.env'))

from flask import Flask
from extensions import db

# --- Minimal Flask app for DB access ---
app = Flask(__name__)
database_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

CUSTOMER_ID = 290
SEED = 42
random.seed(SEED)


# ============================================================
# FIX 1: Generate HealthTrend rows (6 months: Oct 2025 – Mar 2026)
# ============================================================
def fix_health_trends():
    """Generate 6 months of realistic, improving health trends for customer 290."""
    from models import Account, HealthTrend

    accounts = Account.query.filter_by(customer_id=CUSTOMER_ID, vertical='dc2_s').all()
    if not accounts:
        print("❌ No accounts found for customer 290")
        return

    # Delete existing health trends for this customer (if any)
    deleted = HealthTrend.query.filter(
        HealthTrend.account_id.in_([a.account_id for a in accounts])
    ).delete(synchronize_session='fetch')
    if deleted:
        print(f"  Cleaned {deleted} existing HealthTrend rows")

    # Months to generate: Oct 2025 through Mar 2026
    months = [
        (2025, 10), (2025, 11), (2025, 12),
        (2026, 1), (2026, 2), (2026, 3),
    ]

    # Each account gets a slightly different trajectory.
    # The overall story: improvement across all pillars over 6 months,
    # with some accounts improving faster (showing CS impact).
    #
    # Pillar mapping for _extract_historical_actuals:
    #   product_usage_score      → product_adoption
    #   support_score            → ticket_resolution_time
    #   customer_sentiment_score → GRR
    #   business_outcomes_score  → NRR
    #   relationship_strength_score → expansion_rate
    #
    # 10 health points change = 1% metric improvement.
    # We want ~3% NRR improvement over 6 months = 30-point business_outcomes gain.
    # That matches the story arc: expansion champion driving revenue growth.

    # Base scores at month 0 (Oct 2025) — per account archetype
    # Production/UAT: higher starting scores (mature)
    # Dev/QA/Lab: lower starting scores (growing)
    # Sandbox/Integration: mid-range
    account_profiles = {
        290001: {'base': 52, 'growth': 'strong',  'label': 'Production'},
        290002: {'base': 48, 'growth': 'moderate','label': 'Staging'},
        290003: {'base': 42, 'growth': 'strong',  'label': 'Development'},
        290004: {'base': 45, 'growth': 'moderate','label': 'QA'},
        290005: {'base': 55, 'growth': 'strong',  'label': 'UAT'},
        290006: {'base': 40, 'growth': 'slow',    'label': 'DR'},
        290007: {'base': 38, 'growth': 'slow',    'label': 'Sandbox'},
        290008: {'base': 44, 'growth': 'moderate','label': 'Integration'},
        290009: {'base': 46, 'growth': 'moderate','label': 'Performance'},
        290010: {'base': 50, 'growth': 'strong',  'label': 'Lab'},
    }

    growth_rates = {
        'strong':   {'pu': 6.0, 'su': 5.5, 'cs': 5.0, 'bo': 5.5, 'rs': 6.0},
        'moderate': {'pu': 4.0, 'su': 3.5, 'cs': 3.0, 'bo': 4.0, 'rs': 4.5},
        'slow':     {'pu': 2.5, 'su': 2.0, 'cs': 2.0, 'bo': 2.5, 'rs': 3.0},
    }

    # Pillar offsets from base (some pillars start higher/lower)
    pillar_offsets = {
        'product_usage':         +2,
        'support':               -3,
        'customer_sentiment':    -1,
        'business_outcomes':     +4,
        'relationship_strength': +0,
    }

    created = 0
    for acct in accounts:
        profile = account_profiles.get(acct.account_id)
        if not profile:
            continue

        base = profile['base']
        rates = growth_rates[profile['growth']]

        for month_idx, (year, month) in enumerate(months):
            # Progressive improvement with slight noise
            noise = lambda: random.uniform(-1.5, 1.5)
            t = month_idx  # 0-5

            pu = base + pillar_offsets['product_usage'] + rates['pu'] * t + noise()
            su = base + pillar_offsets['support'] + rates['su'] * t + noise()
            cs = base + pillar_offsets['customer_sentiment'] + rates['cs'] * t + noise()
            bo = base + pillar_offsets['business_outcomes'] + rates['bo'] * t + noise()
            rs = base + pillar_offsets['relationship_strength'] + rates['rs'] * t + noise()

            # Clamp to 0-100
            clamp = lambda v: max(0, min(100, round(v, 2)))
            pu, su, cs, bo, rs = clamp(pu), clamp(su), clamp(cs), clamp(bo), clamp(rs)

            # Overall = weighted average (matching the SaaS model weights)
            overall = round(0.30 * pu + 0.20 * su + 0.20 * cs + 0.15 * bo + 0.15 * rs, 2)

            ht = HealthTrend(
                account_id=acct.account_id,
                customer_id=CUSTOMER_ID,
                month=month,
                year=year,
                overall_health_score=Decimal(str(overall)),
                product_usage_score=Decimal(str(pu)),
                support_score=Decimal(str(su)),
                customer_sentiment_score=Decimal(str(cs)),
                business_outcomes_score=Decimal(str(bo)),
                relationship_strength_score=Decimal(str(rs)),
                total_kpis=38,
                valid_kpis=38,
            )
            db.session.add(ht)
            created += 1

    db.session.commit()
    print(f"✅ Created {created} HealthTrend rows ({len(accounts)} accounts × {len(months)} months)")

    # Print summary
    print("\n  Health trend trajectories (Oct 2025 → Mar 2026):")
    for acct in accounts[:3]:  # Show first 3 as sample
        first = HealthTrend.query.filter_by(
            account_id=acct.account_id, year=2025, month=10
        ).first()
        last = HealthTrend.query.filter_by(
            account_id=acct.account_id, year=2026, month=3
        ).first()
        if first and last:
            delta = float(last.overall_health_score) - float(first.overall_health_score)
            print(f"    {acct.account_name}: {float(first.overall_health_score):.1f} → {float(last.overall_health_score):.1f} (+{delta:.1f})")


# ============================================================
# FIX 2 & 3: Redistribute context graph dates + scale revenue
# ============================================================
def fix_context_graph():
    """Redistribute context graph dates and scale revenue to match actual ARR."""
    from models import Account, ContextNode

    accounts = Account.query.filter_by(customer_id=CUSTOMER_ID, vertical='dc2_s').all()
    account_map = {a.account_id: a for a in accounts}

    # Get actual ARR per account
    def get_arr(acct):
        arr = 0.0
        if acct.profile_metadata and isinstance(acct.profile_metadata, dict):
            arr = float(acct.profile_metadata.get('arr', 0) or 0)
        if not arr and acct.revenue:
            arr = float(acct.revenue)
        return arr

    arr_map = {a.account_id: get_arr(a) for a in accounts}
    total_arr = sum(arr_map.values())
    print(f"\n  Total customer ARR: ${total_arr:,.0f}")
    for aid, arr in sorted(arr_map.items()):
        print(f"    {aid}: ${arr:,.0f}")

    # --- Load all context nodes for customer 290 ---
    nodes = ContextNode.query.filter(
        ContextNode.account_id.in_(list(account_map.keys()))
    ).all()

    print(f"\n  Processing {len(nodes)} context graph nodes...")

    # --- Target date ranges for each node type ---
    # The story arc spans Oct 2025 – Mar 2026 (same as health trends)
    # Chronological flow: SIGNAL → DECISION → OUTCOME
    #
    # Phase 1 (Oct-Nov 2025): Signals emerge - adoption acceleration, usage spikes
    # Phase 2 (Dec 2025):     Signals escalate - capacity crunch, risk signals
    # Phase 3 (Jan 2026):     Decisions made - budget requests, expansion proposals
    # Phase 4 (Feb-Mar 2026): Outcomes realized - deals closed, ROI proven

    from dateutil.relativedelta import relativedelta

    # Per-account phase offset: stagger slightly so not all accounts hit same day
    def _rand_date_in_range(start_date, end_date):
        """Random date between start and end."""
        delta = (end_date - start_date).days
        if delta <= 0:
            return start_date
        return start_date + relativedelta(days=random.randint(0, delta))

    # Track node changes for summary
    date_updates = 0
    revenue_updates = 0

    for node in nodes:
        account_arr = arr_map.get(node.account_id, 1000000)

        # --- FIX 3: Scale revenue_impact ---
        if node.revenue_impact and float(node.revenue_impact) != 0:
            old_rev = float(node.revenue_impact)

            # Revenue scaling logic:
            # The arc's original revenue_narrative uses arr_start=$2.4M.
            # Our accounts range from $385K to $2.1M.
            # Scale each node's revenue proportional to its account's ARR / $2.4M (arc base).
            # Then apply a smaller fraction so totals are realistic:
            #   - OUTCOME expansion: ~25-40% of account ARR (big deal, but not 15x)
            #   - OUTCOME churn_averted: ~15-25% of ARR
            #   - DECISION protected: ~10-20% of ARR
            #   - SIGNAL risk: ~5-10% of ARR

            scale = account_arr / 2400000.0  # vs arc's $2.4M base

            if node.node_type == 'OUTCOME':
                if node.node_subtype == 'expansion':
                    # Expansion outcome: 25-40% of account ARR
                    pct = random.uniform(0.25, 0.40)
                    new_rev = account_arr * pct
                elif node.node_subtype == 'churn_averted':
                    # Churn averted: 15-25% of ARR
                    pct = random.uniform(0.15, 0.25)
                    new_rev = account_arr * pct
                else:
                    new_rev = old_rev * scale * 0.15
            elif node.node_type == 'DECISION':
                # Decisions: 10-20% of ARR (budget approved, risk mitigated)
                pct = random.uniform(0.10, 0.20)
                new_rev = account_arr * pct
            elif node.node_type == 'SIGNAL':
                if old_rev > 0:
                    # Positive signals: 5-10% of ARR
                    pct = random.uniform(0.05, 0.10)
                    new_rev = account_arr * pct
                else:
                    # Negative signals (risk): -(5-10%) of ARR
                    pct = random.uniform(0.05, 0.10)
                    new_rev = -(account_arr * pct)
            else:
                new_rev = old_rev * scale * 0.1

            node.revenue_impact = Decimal(str(round(new_rev, 2)))
            revenue_updates += 1

        # --- FIX 2: Redistribute dates ---
        if node.occurred_at is None:
            # STAKEHOLDER, ACCOUNT, EXTERNAL_CONTEXT: set to start of window
            if node.node_type in ('STAKEHOLDER', 'ACCOUNT', 'EXTERNAL_CONTEXT'):
                node.occurred_at = datetime(2025, 10, 1)
            continue

        # Map old dates to new 6-month window based on node type and subtype
        if node.node_type == 'SIGNAL':
            if node.node_subtype in ('engagement', 'health_change'):
                # Engagement/health signals: spread across Oct-Dec 2025 (early)
                node.occurred_at = _rand_date_in_range(
                    datetime(2025, 10, 5), datetime(2025, 12, 20)
                )
            elif node.node_subtype in ('escalation', 'incident'):
                # Escalation signals: Dec 2025 - Jan 2026 (crisis point)
                node.occurred_at = _rand_date_in_range(
                    datetime(2025, 12, 1), datetime(2026, 1, 25)
                )
            else:
                # Other signals: spread across Oct-Jan
                node.occurred_at = _rand_date_in_range(
                    datetime(2025, 10, 10), datetime(2026, 1, 15)
                )
            date_updates += 1

        elif node.node_type == 'DECISION':
            # Decisions: Jan-Feb 2026 (after signals escalate)
            node.occurred_at = _rand_date_in_range(
                datetime(2026, 1, 5), datetime(2026, 2, 20)
            )
            date_updates += 1

        elif node.node_type == 'OUTCOME':
            # Outcomes: Feb-Mar 2026 (results of decisions)
            node.occurred_at = _rand_date_in_range(
                datetime(2026, 2, 10), datetime(2026, 3, 5)
            )
            date_updates += 1

        elif node.node_type == 'EXTERNAL_CONTEXT':
            # Industry benchmarks: start of window
            node.occurred_at = datetime(2025, 10, 1)
            date_updates += 1

    # --- Also fix revenue_impact_type for signals that have revenue but NULL type ---
    null_type_signals = [n for n in nodes if n.node_type == 'SIGNAL'
                         and n.revenue_impact and float(n.revenue_impact) != 0
                         and not n.revenue_impact_type]
    for n in null_type_signals:
        if float(n.revenue_impact) > 0:
            n.revenue_impact_type = 'expansion'
        else:
            n.revenue_impact_type = 'at_risk'

    if null_type_signals:
        print(f"  Fixed {len(null_type_signals)} signals with NULL revenue_impact_type")

    # --- Fix ACCOUNT node properties.arr to match accounts table ---
    account_nodes = [n for n in nodes if n.node_type == 'ACCOUNT']
    for n in account_nodes:
        actual_arr = arr_map.get(n.account_id)
        if actual_arr and n.properties and isinstance(n.properties, dict):
            n.properties = {**n.properties, 'arr': actual_arr}
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(n, 'properties')

    # --- Add some at_risk and lost revenue diversity ---
    # Currently all nodes are expansion/protected. For a realistic demo,
    # some outcomes should be at_risk (early) and one or two "lost" (to show
    # cost-of-inaction narrative).
    # Convert ~20% of early SIGNAL revenues to at_risk
    early_signals = [n for n in nodes if n.node_type == 'SIGNAL'
                     and n.revenue_impact and float(n.revenue_impact) != 0
                     and n.occurred_at and n.occurred_at.month in (10, 11)]
    for n in random.sample(early_signals, min(len(early_signals), len(early_signals) // 3 + 1)):
        n.revenue_impact_type = 'at_risk'
        # Make the revenue negative (risk)
        n.revenue_impact = Decimal(str(-abs(float(n.revenue_impact))))

    db.session.commit()
    print(f"✅ Updated {date_updates} node dates, {revenue_updates} revenue values")

    # --- Print new revenue summary ---
    from sqlalchemy import func
    rev_summary = db.session.query(
        ContextNode.revenue_impact_type,
        func.count(ContextNode.node_id),
        func.sum(ContextNode.revenue_impact),
    ).filter(
        ContextNode.account_id.in_(list(account_map.keys())),
        ContextNode.revenue_impact.isnot(None),
        ContextNode.revenue_impact != 0,
    ).group_by(ContextNode.revenue_impact_type).all()

    print("\n  Revenue summary after fix:")
    for impact_type, count, total in rev_summary:
        print(f"    {impact_type or 'NULL'}: {count} nodes, ${float(total or 0):,.0f}")

    # Date distribution
    date_dist = db.session.query(
        func.to_char(ContextNode.occurred_at, 'YYYY-MM'),
        func.count(ContextNode.node_id),
    ).filter(
        ContextNode.account_id.in_(list(account_map.keys())),
        ContextNode.occurred_at.isnot(None),
    ).group_by(
        func.to_char(ContextNode.occurred_at, 'YYYY-MM')
    ).order_by(
        func.to_char(ContextNode.occurred_at, 'YYYY-MM')
    ).all()

    print("\n  Date distribution after fix:")
    for month, count in date_dist:
        print(f"    {month}: {count} nodes")


# ============================================================
# MAIN
# ============================================================
def main():
    with app.app_context():
        print("=" * 60)
        print("Fix Customer 290 Demo Data")
        print("=" * 60)

        print("\n[1/2] Generating HealthTrend rows...")
        fix_health_trends()

        print("\n[2/2] Fixing context graph dates and revenue...")
        fix_context_graph()

        print("\n" + "=" * 60)
        print("Done! Customer 290 demo data is now consistent.")
        print("=" * 60)


if __name__ == '__main__':
    main()
