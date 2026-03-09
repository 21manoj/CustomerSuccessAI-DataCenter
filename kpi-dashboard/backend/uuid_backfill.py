"""
UUID Backfill Script

Generates UUIDs for all existing Customer, Account, and User records
that don't already have one. Idempotent — safe to run multiple times.

Usage:
    # As standalone script (inside Docker container)
    python uuid_backfill.py

    # As API endpoint
    POST /api/admin/uuid-backfill

    # On container startup (auto-run)
    Called from init_db.py or app startup
"""

import logging
import sys

logger = logging.getLogger(__name__)


def backfill_uuids(app=None):
    """
    Generate UUIDs for all records missing them.

    Args:
        app: Flask app instance (for app context). If None, uses current app context.

    Returns:
        dict with counts of records updated per entity type
    """
    from extensions import db
    from models import Customer, Account, User
    from uuid_utils import ensure_uuid, ensure_customer_uuid_on_account

    stats = {
        'customers_updated': 0,
        'accounts_updated': 0,
        'users_updated': 0,
        'errors': [],
    }

    # ---- 1. Customers without UUID ----
    try:
        customers = Customer.query.filter(
            (Customer.uuid == None) | (Customer.uuid == '')  # noqa: E711
        ).all()
        logger.info(f"Found {len(customers)} customers without UUID")

        for customer in customers:
            try:
                vertical = getattr(customer, 'vertical', None) or 'dc'
                ensure_uuid(customer, vertical)
                stats['customers_updated'] += 1
            except Exception as e:
                msg = f"Failed to generate UUID for customer {customer.customer_id}: {e}"
                logger.warning(msg)
                stats['errors'].append(msg)

        if customers:
            db.session.flush()
            logger.info(f"Generated UUIDs for {stats['customers_updated']} customers")
    except Exception as e:
        msg = f"Customer UUID backfill failed: {e}"
        logger.error(msg)
        stats['errors'].append(msg)

    # ---- 2. Accounts without UUID ----
    try:
        accounts = Account.query.filter(
            (Account.uuid == None) | (Account.uuid == '')  # noqa: E711
        ).all()
        logger.info(f"Found {len(accounts)} accounts without UUID")

        for account in accounts:
            try:
                vertical = getattr(account, 'vertical', None) or 'dc'
                ensure_uuid(account, vertical)
                stats['accounts_updated'] += 1
            except Exception as e:
                msg = f"Failed to generate UUID for account {account.account_id}: {e}"
                logger.warning(msg)
                stats['errors'].append(msg)

        if accounts:
            db.session.flush()
            logger.info(f"Generated UUIDs for {stats['accounts_updated']} accounts")
    except Exception as e:
        msg = f"Account UUID backfill failed: {e}"
        logger.error(msg)
        stats['errors'].append(msg)

    # ---- 3. Accounts without customer_uuid ----
    try:
        accounts_no_cuuid = Account.query.filter(
            (Account.customer_uuid == None) | (Account.customer_uuid == '')  # noqa: E711
        ).all()
        cuuid_count = 0
        for account in accounts_no_cuuid:
            try:
                customer = db.session.get(Customer, account.customer_id)
                if customer and customer.uuid:
                    ensure_customer_uuid_on_account(account, customer)
                    cuuid_count += 1
            except Exception as e:
                logger.warning(f"Failed to set customer_uuid on account {account.account_id}: {e}")

        if cuuid_count:
            db.session.flush()
            logger.info(f"Set customer_uuid on {cuuid_count} accounts")
    except Exception as e:
        logger.error(f"Account customer_uuid backfill failed: {e}")

    # ---- 4. Users without UUID ----
    try:
        users = User.query.filter(
            (User.uuid == None) | (User.uuid == '')  # noqa: E711
        ).all()
        logger.info(f"Found {len(users)} users without UUID")

        for user in users:
            try:
                vertical = getattr(user, 'vertical', None) or 'dc'
                ensure_uuid(user, vertical)

                # Also set customer_uuid if missing
                if not getattr(user, 'customer_uuid', None) and user.customer_id:
                    customer = db.session.get(Customer, user.customer_id)
                    if customer and customer.uuid:
                        user.customer_uuid = customer.uuid

                stats['users_updated'] += 1
            except Exception as e:
                msg = f"Failed to generate UUID for user {user.user_id}: {e}"
                logger.warning(msg)
                stats['errors'].append(msg)

        if users:
            db.session.flush()
            logger.info(f"Generated UUIDs for {stats['users_updated']} users")
    except Exception as e:
        msg = f"User UUID backfill failed: {e}"
        logger.error(msg)
        stats['errors'].append(msg)

    # ---- Commit all changes ----
    try:
        db.session.commit()
        total = stats['customers_updated'] + stats['accounts_updated'] + stats['users_updated']
        logger.info(f"UUID backfill complete: {total} records updated")
    except Exception as e:
        db.session.rollback()
        msg = f"UUID backfill commit failed: {e}"
        logger.error(msg)
        stats['errors'].append(msg)

    return stats


def backfill_uuids_safe(app=None):
    """
    Safe wrapper that catches all exceptions and logs them.
    Used for startup backfill where we don't want to crash the app.
    """
    try:
        return backfill_uuids(app)
    except Exception as e:
        logger.error(f"UUID backfill failed (non-fatal): {e}")
        return {'customers_updated': 0, 'accounts_updated': 0, 'users_updated': 0, 'errors': [str(e)]}


# Allow running as standalone script
if __name__ == '__main__':
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from app_v3_minimal import app
    with app.app_context():
        stats = backfill_uuids()
        print(f"Backfill results: {stats}")
