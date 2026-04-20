#!/usr/bin/env python3
"""
CLI audit tool — run all context-graph invariants against a customer.

Usage (in the cspulse-platform container):
    python3 scripts/audit_context_graph.py --customer-id 385
    python3 scripts/audit_context_graph.py --customer-id 385 --json > audit.json
    python3 scripts/audit_context_graph.py --customer-id 385 --only I1,I9

Exits non-zero if any `error`-severity violation is found.
Warnings-only result exits 0 so this can run in a daily cron without
tripping pager unless genuine data-integrity errors appear.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend/ to path so we can import the Flask app + utils.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit CS Pulse context graph invariants')
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument(
        '--only',
        type=str,
        default=None,
        help='Comma-separated invariant IDs to run (e.g. I1,I4,I9). Default: all.',
    )
    parser.add_argument('--json', action='store_true', help='Emit JSON to stdout')
    args = parser.parse_args()

    # Flask app + DB context
    from app_v3_minimal import app  # noqa: PLC0415
    from utils.context_graph_invariants import (  # noqa: PLC0415
        INVARIANTS_REGISTRY,
        log_violations_summary,
        run_all_invariants,
        run_invariant,
    )

    with app.app_context():
        if args.only:
            wanted = [s.strip() for s in args.only.split(',') if s.strip()]
            unknown = [w for w in wanted if w not in INVARIANTS_REGISTRY]
            if unknown:
                print(f'ERROR: unknown invariants: {unknown}', file=sys.stderr)
                return 2
            violations = []
            for inv_id in wanted:
                violations.extend(run_invariant(inv_id, args.customer_id))
        else:
            violations = run_all_invariants(args.customer_id)

    summary = {
        'customer_id': args.customer_id,
        'total': len(violations),
        'by_invariant': {},
        'by_severity': {'error': 0, 'warning': 0},
        'violations': [v.to_dict() for v in violations],
    }
    for v in violations:
        summary['by_invariant'][v.invariant_id] = summary['by_invariant'].get(v.invariant_id, 0) + 1
        summary['by_severity'][v.severity] = summary['by_severity'].get(v.severity, 0) + 1

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"\nContext graph audit — customer {args.customer_id}")
        print('=' * 60)
        if not violations:
            print('✓ Clean (0 violations)')
        else:
            print(f"Total violations: {summary['total']} "
                  f"(errors: {summary['by_severity']['error']}, "
                  f"warnings: {summary['by_severity']['warning']})")
            print()
            print('By invariant:')
            for inv_id in sorted(summary['by_invariant']):
                print(f"  {inv_id}: {summary['by_invariant'][inv_id]}")
            print()
            print('Examples (up to 5 per invariant):')
            seen_inv: dict = {}
            for v in violations:
                n = seen_inv.get(v.invariant_id, 0)
                if n >= 5:
                    continue
                seen_inv[v.invariant_id] = n + 1
                print(f"  [{v.invariant_id}] ({v.severity}) acct={v.account_id}  {v.message}")
        print()

    # Exit code: non-zero only if any error-severity violations.
    return 1 if summary['by_severity']['error'] > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
