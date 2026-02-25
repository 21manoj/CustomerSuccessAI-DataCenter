#!/usr/bin/env python3
"""
Phase 2: Backfill UUIDs for all Customer, Account, and User records

Finds records where uuid IS NULL and generates a prefixed UUID v7.
Safe to re-run (idempotent) — only fills NULL uuid fields.

Usage:
    cd kpi-dashboard/backend
    python3 scripts/phase2_backfill_uuids.py              # Dry-run (report only)
    python3 scripts/phase2_backfill_uuids.py --apply       # Actually write UUIDs
    python3 scripts/phase2_backfill_uuids.py --apply --verbose
"""

import sys
import os
import argparse
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app_v3_minimal import app, db
from models import Customer, Account, User
from id_generator import generate_id

logger = logging.getLogger('uuid_backfill')


def backfill_customers(apply: bool, verbose: bool) -> int:
    """Backfill UUIDs for Customer records with NULL uuid"""
    customers = Customer.query.filter(Customer.uuid.is_(None)).all()
    count = len(customers)

    if count == 0:
        logger.info("  Customers: all records already have UUIDs")
        return 0

    logger.info(f"  Customers: {count} records need UUIDs")

    for c in customers:
        # Determine vertical from existing data
        vertical = c.vertical or 'dc'
        if vertical not in ('dc', 'saas', 'msp'):
            vertical = 'dc'

        new_uuid = generate_id(vertical, 'customer')

        if verbose:
            logger.info(f"    customer_id={c.customer_id} → uuid={new_uuid}, vertical={vertical}")

        if apply:
            c.uuid = new_uuid
            if not c.vertical:
                c.vertical = vertical

    if apply:
        db.session.commit()
        logger.info(f"  Customers: {count} UUIDs written")
    else:
        logger.info(f"  Customers: {count} UUIDs would be written (dry-run)")

    return count


def backfill_accounts(apply: bool, verbose: bool) -> int:
    """Backfill UUIDs for Account records with NULL uuid"""
    accounts = Account.query.filter(Account.uuid.is_(None)).all()
    count = len(accounts)

    if count == 0:
        logger.info("  Accounts: all records already have UUIDs")
        return 0

    logger.info(f"  Accounts: {count} records need UUIDs")

    # Pre-load customer UUID lookup
    customer_uuids = {
        c.customer_id: c.uuid
        for c in Customer.query.filter(Customer.uuid.isnot(None)).all()
    }

    for a in accounts:
        # Determine vertical from account or parent customer
        vertical = a.vertical or 'dc'
        if vertical.startswith('dc'):
            vertical = 'dc'
        elif vertical not in ('saas', 'msp'):
            vertical = 'dc'

        new_uuid = generate_id(vertical, 'account')

        if verbose:
            logger.info(f"    account_id={a.account_id} → uuid={new_uuid}")

        if apply:
            a.uuid = new_uuid
            # Also set customer_uuid cross-reference
            if hasattr(a, 'customer_uuid') and not a.customer_uuid:
                parent_uuid = customer_uuids.get(a.customer_id)
                if parent_uuid:
                    a.customer_uuid = parent_uuid

    if apply:
        db.session.commit()
        logger.info(f"  Accounts: {count} UUIDs written")
    else:
        logger.info(f"  Accounts: {count} UUIDs would be written (dry-run)")

    return count


def backfill_users(apply: bool, verbose: bool) -> int:
    """Backfill UUIDs for User records with NULL uuid"""
    users = User.query.filter(User.uuid.is_(None)).all()
    count = len(users)

    if count == 0:
        logger.info("  Users: all records already have UUIDs")
        return 0

    logger.info(f"  Users: {count} records need UUIDs")

    # Pre-load customer UUID lookup
    customer_uuids = {
        c.customer_id: c.uuid
        for c in Customer.query.filter(Customer.uuid.isnot(None)).all()
    }

    for u in users:
        vertical = getattr(u, 'vertical', None) or 'dc'
        if vertical.startswith('dc'):
            vertical = 'dc'
        elif vertical not in ('saas', 'msp'):
            vertical = 'dc'

        new_uuid = generate_id(vertical, 'user')

        if verbose:
            logger.info(f"    user_id={u.user_id} → uuid={new_uuid}")

        if apply:
            u.uuid = new_uuid
            if hasattr(u, 'customer_uuid') and not u.customer_uuid:
                parent_uuid = customer_uuids.get(u.customer_id)
                if parent_uuid:
                    u.customer_uuid = parent_uuid

    if apply:
        db.session.commit()
        logger.info(f"  Users: {count} UUIDs written")
    else:
        logger.info(f"  Users: {count} UUIDs would be written (dry-run)")

    return count


def report_uuid_coverage():
    """Print a coverage report of UUID population across tables"""
    tables = [
        ('customers', Customer, 'customer_id'),
        ('accounts', Account, 'account_id'),
        ('users', User, 'user_id'),
    ]

    logger.info("\n=== UUID Coverage Report ===")
    for name, model, pk_field in tables:
        total = model.query.count()
        with_uuid = model.query.filter(model.uuid.isnot(None)).count()
        without_uuid = total - with_uuid
        pct = (with_uuid / total * 100) if total else 100

        status = "✅" if without_uuid == 0 else "❌"
        logger.info(f"  {status} {name}: {with_uuid}/{total} ({pct:.0f}%) have UUIDs — {without_uuid} missing")


def main():
    parser = argparse.ArgumentParser(description='Backfill UUIDs for existing records')
    parser.add_argument('--apply', action='store_true', help='Actually write UUIDs (default: dry-run)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show each record')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    with app.app_context():
        mode = "APPLY" if args.apply else "DRY-RUN"
        logger.info(f"\n{'='*50}")
        logger.info(f"Phase 2: UUID Backfill ({mode})")
        logger.info(f"{'='*50}\n")

        # Report before
        report_uuid_coverage()
        logger.info("")

        # Backfill
        total = 0
        total += backfill_customers(args.apply, args.verbose)
        total += backfill_accounts(args.apply, args.verbose)
        total += backfill_users(args.apply, args.verbose)

        logger.info(f"\nTotal records {'updated' if args.apply else 'to update'}: {total}")

        # Report after (if applied)
        if args.apply and total > 0:
            logger.info("\n--- After backfill ---")
            report_uuid_coverage()

        if not args.apply and total > 0:
            logger.info(f"\n💡 Run with --apply to write {total} UUIDs")


if __name__ == '__main__':
    main()
