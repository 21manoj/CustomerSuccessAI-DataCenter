#!/usr/bin/env python3
"""
License Service
===============

Provides license status checks, seat availability, and expiry warnings
for customer licensing and seat management.

Soft limits:
  - Warn at 80% seat utilisation
  - Warn at 30 days before license expiry
"""

import logging
from datetime import date, timedelta

from extensions import db
from models import CustomerLicense, User, Account

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (soft limits)
# ---------------------------------------------------------------------------
SEAT_WARNING_PCT = 0.80        # Warn when seat usage >= 80%
EXPIRY_WARNING_DAYS = 30       # Warn when licence expires within 30 days


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_license_status(customer_id: int) -> dict:
    """
    Return a comprehensive license status report for a customer.

    Parameters
    ----------
    customer_id : int

    Returns
    -------
    dict with keys:
        license        : dict | None  — license record (to_dict)
        seat_usage     : dict         — {used, max, available, utilisation_pct}
        account_usage  : dict | None  — {used, max, available} if max_accounts is set
        warnings       : list[str]    — human-readable warning messages
        days_to_expiry : int | None   — days until license_end (None if no license)
        is_expired     : bool
        is_valid       : bool         — True if license exists and is not expired
    """
    lic = CustomerLicense.query.filter_by(customer_id=customer_id).first()

    # No license record at all
    if not lic:
        return {
            'license': None,
            'seat_usage': {'used': 0, 'max': None, 'available': None, 'utilisation_pct': 0},
            'account_usage': None,
            'warnings': ['No license record found for this customer'],
            'days_to_expiry': None,
            'is_expired': False,
            'is_valid': False,
        }

    today = date.today()
    warnings = []

    # ------------------------------------------------------------------
    # Seat usage
    # ------------------------------------------------------------------
    active_seats = (
        User.query
        .filter_by(customer_id=customer_id, active=True)
        .count()
    )
    max_seats = lic.max_seats or 0
    available_seats = max(0, max_seats - active_seats) if max_seats else None
    utilisation_pct = (active_seats / max_seats * 100) if max_seats > 0 else 0

    if max_seats > 0 and active_seats >= max_seats:
        warnings.append(
            f"Seat limit reached: {active_seats}/{max_seats} seats in use. "
            "No new users can be added."
        )
    elif max_seats > 0 and (active_seats / max_seats) >= SEAT_WARNING_PCT:
        warnings.append(
            f"Approaching seat limit: {active_seats}/{max_seats} seats in use "
            f"({utilisation_pct:.0f}%)."
        )

    seat_usage = {
        'used': active_seats,
        'max': max_seats,
        'available': available_seats,
        'utilisation_pct': round(utilisation_pct, 1),
    }

    # ------------------------------------------------------------------
    # Account usage (if max_accounts is configured)
    # ------------------------------------------------------------------
    account_usage = None
    if lic.max_accounts is not None:
        active_accounts = (
            Account.query
            .filter_by(customer_id=customer_id, account_status='active')
            .count()
        )
        acct_available = max(0, lic.max_accounts - active_accounts)
        account_usage = {
            'used': active_accounts,
            'max': lic.max_accounts,
            'available': acct_available,
        }
        if active_accounts >= lic.max_accounts:
            warnings.append(
                f"Account limit reached: {active_accounts}/{lic.max_accounts} active accounts."
            )

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------
    days_to_expiry = (lic.license_end - today).days if lic.license_end else None
    is_expired = days_to_expiry is not None and days_to_expiry < 0

    if is_expired:
        warnings.append(
            f"License expired {abs(days_to_expiry)} day(s) ago "
            f"(ended {lic.license_end.isoformat()})."
        )
    elif days_to_expiry is not None and days_to_expiry <= EXPIRY_WARNING_DAYS:
        if lic.auto_renew:
            warnings.append(
                f"License expires in {days_to_expiry} day(s) (auto-renew enabled)."
            )
        else:
            warnings.append(
                f"License expires in {days_to_expiry} day(s). "
                "Contact sales to renew."
            )

    return {
        'license': lic.to_dict(),
        'seat_usage': seat_usage,
        'account_usage': account_usage,
        'warnings': warnings,
        'days_to_expiry': days_to_expiry,
        'is_expired': is_expired,
        'is_valid': not is_expired and lic is not None,
    }


def check_seat_availability(customer_id: int) -> tuple:
    """
    Quick check: can this customer add another user seat?

    Parameters
    ----------
    customer_id : int

    Returns
    -------
    tuple (available: bool, warning: str | None)
        available — True if at least one seat is open (or no limit is set)
        warning   — A soft warning string if approaching the limit, else None
    """
    lic = CustomerLicense.query.filter_by(customer_id=customer_id).first()
    if not lic:
        # No license record — allow by default (no enforcement)
        return True, None

    max_seats = lic.max_seats or 0
    if max_seats == 0:
        # Unlimited seats
        return True, None

    active_seats = (
        User.query
        .filter_by(customer_id=customer_id, active=True)
        .count()
    )

    if active_seats >= max_seats:
        return False, (
            f"Seat limit reached: {active_seats}/{max_seats} seats in use. "
            "Cannot add new users until seats are freed or limit is increased."
        )

    utilisation_pct = active_seats / max_seats
    if utilisation_pct >= SEAT_WARNING_PCT:
        remaining = max_seats - active_seats
        return True, (
            f"Approaching seat limit: {active_seats}/{max_seats} in use. "
            f"Only {remaining} seat(s) remaining."
        )

    return True, None


def check_account_availability(customer_id: int) -> tuple:
    """
    Quick check: can this customer add another account?

    Parameters
    ----------
    customer_id : int

    Returns
    -------
    tuple (available: bool, warning: str | None)
    """
    lic = CustomerLicense.query.filter_by(customer_id=customer_id).first()
    if not lic or lic.max_accounts is None:
        # No limit configured
        return True, None

    active_accounts = (
        Account.query
        .filter_by(customer_id=customer_id, account_status='active')
        .count()
    )

    if active_accounts >= lic.max_accounts:
        return False, (
            f"Account limit reached: {active_accounts}/{lic.max_accounts} active accounts. "
            "Cannot add new accounts until the limit is increased."
        )

    return True, None
