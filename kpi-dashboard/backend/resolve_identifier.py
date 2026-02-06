"""
Identifier Resolution Utility for UUID Migration

During the migration period, IDs can be either:
  - Legacy integers (e.g., 1, 9, 42)
  - New prefixed UUIDs (e.g., "dc_cust_019471a3-b5c2-7def-...")

This module provides helpers that accept EITHER format, enabling gradual
migration of API endpoints without breaking existing callers.

Usage:
    from resolve_identifier import resolve_customer, resolve_account

    # Both work:
    customer = resolve_customer(db, 1)                                    # legacy int
    customer = resolve_customer(db, "dc_cust_019471a3-b5c2-7def-...")    # new UUID
"""

from models import Customer, Account, Product, User, KPIUpload
from id_generator import is_valid_prefixed_id
import logging

logger = logging.getLogger(__name__)


def _is_legacy_int(identifier) -> bool:
    """Check if an identifier is a legacy integer (or string that looks like one)."""
    if isinstance(identifier, int):
        return True
    if isinstance(identifier, str):
        try:
            int(identifier)
            return True
        except (ValueError, TypeError):
            return False
    return False


def resolve_customer(db, identifier):
    """
    Resolve a customer by legacy integer ID or UUID.

    Args:
        db: SQLAlchemy db instance
        identifier: int, string-int, or prefixed UUID

    Returns:
        Customer object or None
    """
    if identifier is None:
        return None

    if _is_legacy_int(identifier):
        return db.session.get(Customer, int(identifier))

    # Try UUID lookup
    return Customer.query.filter_by(uuid=str(identifier)).first()


def resolve_account(db, identifier):
    """
    Resolve an account by legacy integer ID or UUID.

    Args:
        db: SQLAlchemy db instance
        identifier: int, string-int, or prefixed UUID

    Returns:
        Account object or None
    """
    if identifier is None:
        return None

    if _is_legacy_int(identifier):
        return db.session.get(Account, int(identifier))

    return Account.query.filter_by(uuid=str(identifier)).first()


def resolve_product(db, identifier):
    """Resolve a product by legacy integer ID or UUID."""
    if identifier is None:
        return None
    if _is_legacy_int(identifier):
        return db.session.get(Product, int(identifier))
    return Product.query.filter_by(uuid=str(identifier)).first()


def resolve_user(db, identifier):
    """Resolve a user by legacy integer ID or UUID."""
    if identifier is None:
        return None
    if _is_legacy_int(identifier):
        return db.session.get(User, int(identifier))
    return User.query.filter_by(uuid=str(identifier)).first()


def resolve_customer_id(db, identifier) -> int:
    """
    Resolve any customer identifier to the legacy integer customer_id.

    Useful during migration: callers pass UUID but downstream code still needs int.

    Args:
        db: SQLAlchemy db instance
        identifier: int, string-int, or prefixed UUID

    Returns:
        Integer customer_id, or None if not found
    """
    if identifier is None:
        return None

    if _is_legacy_int(identifier):
        return int(identifier)

    # UUID lookup
    customer = Customer.query.filter_by(uuid=str(identifier)).first()
    return customer.customer_id if customer else None


def get_customer_vertical(db, customer_id) -> str:
    """
    Get the vertical for a customer.

    Args:
        db: SQLAlchemy db instance
        customer_id: integer customer_id or UUID

    Returns:
        Vertical string ('saas', 'dc', 'msp') or None
    """
    customer = resolve_customer(db, customer_id)
    if customer is None:
        return None

    # Try the vertical column first
    vertical = getattr(customer, 'vertical', None)
    if vertical:
        return vertical

    # Fallback: try to extract from uuid
    uuid = getattr(customer, 'uuid', None)
    if uuid and is_valid_prefixed_id(uuid):
        from id_generator import extract_vertical
        return extract_vertical(uuid)

    return None
