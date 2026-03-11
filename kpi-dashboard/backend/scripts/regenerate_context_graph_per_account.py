#!/usr/bin/env python3
"""
Regenerate Context Graph Data with Per-Account Arc Assignment

Assigns different story arcs to each account based on health scores,
ensuring context graph data is consistent with:
  - Account health classifications (Critical/At-Risk/Healthy)
  - Wizard B milestone logic (churn milestones for critical accounts,
    expansion milestones for healthy accounts)

Mapping:
  - Critical (<50):  arc_silent_churn, arc_crisis_recovery
  - At-Risk (50-69): arc_competitive_displacement, arc_stalled_deployment,
                     arc_exec_sponsor_change
  - Healthy (70+):   arc_expansion_champion, arc_land_and_expand,
                     arc_seasonal_surge

Usage:
    # From backend/ directory:
    python scripts/regenerate_context_graph_per_account.py --customer-id 291
    python scripts/regenerate_context_graph_per_account.py --customer-id 292
    python scripts/regenerate_context_graph_per_account.py --customer-id 291 --ingest

    # Both Sacme + Tacme:
    python scripts/regenerate_context_graph_per_account.py --all-demo
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from scripts.generate_context_graph_data import (
    ContextGraphGenerator,
    build_health_arc_map,
    classify_health,
    HEALTH_ARC_POOLS,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def get_health_scores_from_db(customer_id: int, num_accounts: int = 10):
    """Query account health scores using Flask app context."""
    from app_v3_minimal import app

    with app.app_context():
        from scripts.generate_context_graph_data import _query_health_scores
        scores = _query_health_scores(customer_id, num_accounts)
        return scores


def regenerate_for_customer(
    customer_id: int,
    num_accounts: int = 10,
    seed: int = 42,
    do_ingest: bool = False,
):
    """Generate context graph CSVs with per-account arc assignment.

    Returns:
        Dict with generation results and arc assignments.
    """
    print(f"\n{'=' * 70}")
    print(f"  Context Graph Regeneration — Customer {customer_id}")
    print(f"{'=' * 70}")

    # ── Step 1: Get health scores ─────────────────────────────────────
    print("\n[1/4] Querying account health scores from DB...")
    try:
        health_scores = get_health_scores_from_db(customer_id, num_accounts)
    except Exception as e:
        print(f"  WARNING: DB query failed ({e}), using default (at-risk)")
        health_scores = {}

    if not health_scores:
        # No health scores — try to at least get real account IDs from DB
        print("  No health scores from DB. Querying real account IDs...")
        try:
            from app_v3_minimal import app
            with app.app_context():
                from models import Account
                accounts = Account.query.filter_by(
                    customer_id=customer_id, vertical='dc2_s'
                ).all()
                if accounts:
                    health_scores = {a.account_id: 65.0 for a in accounts}
                    print(f"  Found {len(accounts)} real accounts, defaulting health to 65.0 (at-risk)")
        except Exception as e2:
            print(f"  WARNING: Account query also failed ({e2})")

        if not health_scores:
            print(f"  ERROR: No accounts found in DB for customer {customer_id}.")
            print(f"  Run onboarding first (Scenario 1), then retry.")
            return {'error': f'No accounts found for customer {customer_id}'}

    # Print health summary
    print(f"\n  {'Account':<8} {'Name':<25} {'Health':>7} {'Class':>10}")
    print(f"  {'-'*8} {'-'*25} {'-'*7} {'-'*10}")

    try:
        from app_v3_minimal import app
        with app.app_context():
            from models import Account
            for acct_id in sorted(health_scores.keys()):
                acct = Account.query.filter_by(account_id=acct_id).first()
                name = acct.account_name if acct else f"Account-{acct_id}"
                health = health_scores[acct_id]
                cls = classify_health(health)
                print(f"  {acct_id:<8} {name:<25} {health:>7.1f} {cls:>10}")
    except Exception:
        for acct_id in sorted(health_scores.keys()):
            health = health_scores[acct_id]
            cls = classify_health(health)
            print(f"  {acct_id:<8} {'?':<25} {health:>7.1f} {cls:>10}")

    # ── Step 2: Build per-account arc map ─────────────────────────────
    print("\n[2/4] Assigning story arcs based on health...")
    arc_map = build_health_arc_map(
        customer_id=customer_id,
        num_accounts=num_accounts,
        health_scores=health_scores,
        seed=seed,
    )

    # Print assignments
    print(f"\n  {'Account':<8} {'Health':>7} {'Class':>10} {'Arc':>35}")
    print(f"  {'-'*8} {'-'*7} {'-'*10} {'-'*35}")
    for acct_id in sorted(arc_map.keys()):
        health = health_scores.get(acct_id, 65.0)
        cls = classify_health(health)
        arc = arc_map[acct_id]
        print(f"  {acct_id:<8} {health:>7.1f} {cls:>10} {arc:>35}")

    # Count by classification
    counts = {'critical': 0, 'at_risk': 0, 'healthy': 0}
    for acct_id in arc_map:
        counts[classify_health(health_scores.get(acct_id, 65.0))] += 1
    print(f"\n  Summary: {counts['critical']} critical, {counts['at_risk']} at-risk, {counts['healthy']} healthy")

    # ── Step 3: Generate CSVs ─────────────────────────────────────────
    # Output to the customer's data/context_graph/ directory
    # (where process-data reads from)
    output_dir = str(
        Path(backend_dir) / 'verticals' /
        f'customer{customer_id}-dc2_s' / 'data' / 'context_graph'
    )

    print(f"\n[3/4] Generating 9 context graph CSVs...")
    print(f"  Output: {output_dir}")

    gen_start = time.time()
    gen = ContextGraphGenerator(
        customer_id=customer_id,
        num_accounts=num_accounts,
        seed=seed,
        account_arc_map=arc_map,
    )
    files = gen.generate_all(output_dir)
    gen_duration = time.time() - gen_start

    print(f"  Generated {len(files)} files in {gen_duration:.1f}s:")
    for name in sorted(files.keys()):
        # Show line count
        line_count = sum(1 for _ in open(files[name])) - 1  # minus header
        print(f"    {name:<40} {line_count:>5} rows")

    # ── Step 4: Optionally ingest into DB ─────────────────────────────
    if do_ingest:
        print(f"\n[4/4] Ingesting into database via process-data API...")
        _ingest_via_api(customer_id)
    else:
        print(f"\n[4/4] Skipped ingestion (use --ingest to auto-ingest)")
        print(f"  To ingest manually:")
        print(f"    curl -s -b /tmp/cookie.txt -X POST \\")
        print(f"      'http://localhost:5059/api/onboarding/process-data' \\")
        print(f"      -H 'Content-Type: application/json' \\")
        print(f"      -d '{{\"customer_id\": {customer_id}}}'")

    # Save arc assignments for reference
    assignments_file = Path(output_dir) / '_arc_assignments.json'
    assignments_data = {
        'customer_id': customer_id,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'seed': seed,
        'accounts': {
            str(acct_id): {
                'arc_id': arc_map[acct_id],
                'health_score': health_scores.get(acct_id, 65.0),
                'health_class': classify_health(health_scores.get(acct_id, 65.0)),
            }
            for acct_id in sorted(arc_map.keys())
        }
    }
    assignments_file.write_text(json.dumps(assignments_data, indent=2))
    print(f"\n  Arc assignments saved to: {assignments_file}")

    return {
        'customer_id': customer_id,
        'arc_assignments': arc_map,
        'health_scores': health_scores,
        'files_generated': len(files),
        'output_dir': output_dir,
    }


def _ingest_via_api(customer_id: int):
    """Trigger process-data endpoint to ingest context graph CSVs."""
    import requests

    base_url = os.environ.get('CS_PULSE_URL', 'http://localhost:5059')

    # Determine login credentials from customer ID
    creds = {
        291: ('admin@sacme.com', 'test123'),
        292: ('admin@tacme.com', 'test123'),
    }
    email, password = creds.get(customer_id, (f'admin@customer{customer_id}.com', 'test123'))

    session = requests.Session()

    # Login
    resp = session.post(f'{base_url}/api/login', json={'email': email, 'password': password})
    if resp.status_code != 200:
        print(f"  ERROR: Login failed ({resp.status_code})")
        return

    # Trigger process-data
    print(f"  Triggering process-data for customer {customer_id}...")
    resp = session.post(
        f'{base_url}/api/onboarding/process-data',
        json={'customer_id': customer_id},
        timeout=300,
    )

    if resp.status_code == 200:
        data = resp.json()
        cg = data.get('context_graph', {})
        print(f"  OK: {cg.get('nodes_inserted', '?')} nodes, {cg.get('edges_inserted', '?')} edges")
        if data.get('errors'):
            for err in data['errors'][:5]:
                print(f"  WARNING: {err}")
    else:
        print(f"  ERROR: process-data failed ({resp.status_code}): {resp.text[:200]}")


def main():
    parser = argparse.ArgumentParser(
        description='Regenerate context graph data with per-account arc assignment'
    )
    parser.add_argument('--customer-id', type=int, default=None,
                        help='Customer ID (e.g., 291 for Sacme, 292 for Tacme)')
    parser.add_argument('--num-accounts', type=int, default=10,
                        help='Number of accounts (default: 10)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--ingest', action='store_true',
                        help='Auto-ingest into DB via process-data API after generation')
    parser.add_argument('--all-demo', action='store_true',
                        help='Regenerate for both Sacme (291) and Tacme (292)')

    args = parser.parse_args()

    if args.all_demo:
        for cid in [291, 292]:
            regenerate_for_customer(
                customer_id=cid,
                num_accounts=args.num_accounts,
                seed=args.seed,
                do_ingest=args.ingest,
            )
    elif args.customer_id:
        regenerate_for_customer(
            customer_id=args.customer_id,
            num_accounts=args.num_accounts,
            seed=args.seed,
            do_ingest=args.ingest,
        )
    else:
        parser.error("Provide --customer-id or --all-demo")


if __name__ == '__main__':
    main()
