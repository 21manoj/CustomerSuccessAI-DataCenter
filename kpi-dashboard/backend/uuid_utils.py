"""
UUID Resolver Utility

Provides helpers for:
1. Resolving UUID or integer ID to a model instance
2. Auto-generating UUIDs on model creation (event hooks)
3. Enriching API responses with UUID fields

Usage:
    from uuid_utils import resolve_customer, resolve_account, enrich_response, ensure_uuid

    # In API endpoint — accept either UUID or integer
    customer = resolve_customer(some_id)  # works with int or "dc_cust_019..."

    # In model creation — auto-generate UUID if missing
    customer = Customer(customer_name="Foo")
    ensure_uuid(customer, 'dc')  # sets customer.uuid if not already set

    # In API response — add uuid fields alongside integer IDs
    response = enrich_response({"customer_id": 5, "account_id": 5001}, customer, account)
"""

import logging
from typing import Optional, Union

from extensions import db
from id_generator import (
    generate_id,
    is_valid_prefixed_id,
    extract_vertical,
    VALID_VERTICALS,
)

logger = logging.getLogger(__name__)


def resolve_customer(identifier: Union[str, int], allow_none: bool = False):
    """
    Resolve a customer by integer ID or prefixed UUID.

    Args:
        identifier: Integer customer_id or prefixed UUID string (e.g. "dc_cust_019...")
        allow_none: If True, return None instead of raising on not-found

    Returns:
        Customer model instance

    Raises:
        ValueError: if identifier format is invalid
        LookupError: if customer not found (unless allow_none=True)
    """
    from models import Customer

    if identifier is None:
        if allow_none:
            return None
        raise ValueError("Customer identifier is required")

    # Integer ID
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        customer = db.session.get(Customer, int(identifier))
        if customer:
            return customer
        if allow_none:
            return None
        raise LookupError(f"Customer not found: {identifier}")

    # Prefixed UUID
    if isinstance(identifier, str) and is_valid_prefixed_id(identifier):
        customer = Customer.query.filter_by(uuid=identifier).first()
        if customer:
            return customer
        if allow_none:
            return None
        raise LookupError(f"Customer not found by UUID: {identifier}")

    raise ValueError(f"Invalid customer identifier format: {identifier}")


def resolve_account(identifier: Union[str, int], customer_id: int = None, allow_none: bool = False):
    """
    Resolve an account by integer ID or prefixed UUID.

    Args:
        identifier: Integer account_id or prefixed UUID string
        customer_id: Optional customer_id to verify ownership
        allow_none: If True, return None instead of raising

    Returns:
        Account model instance
    """
    from models import Account

    if identifier is None:
        if allow_none:
            return None
        raise ValueError("Account identifier is required")

    account = None

    # Integer ID
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        account = db.session.get(Account, int(identifier))
    # Prefixed UUID
    elif isinstance(identifier, str) and is_valid_prefixed_id(identifier):
        account = Account.query.filter_by(uuid=identifier).first()
    else:
        raise ValueError(f"Invalid account identifier format: {identifier}")

    if account is None:
        if allow_none:
            return None
        raise LookupError(f"Account not found: {identifier}")

    # Ownership check
    if customer_id is not None and account.customer_id != customer_id:
        if allow_none:
            return None
        raise LookupError(f"Account {identifier} does not belong to customer {customer_id}")

    return account


def ensure_uuid(instance, vertical: str = 'dc') -> str:
    """
    Ensure a model instance has a UUID. Generate one if missing.

    Supports: Customer, Account, User (any model with a 'uuid' column).

    Args:
        instance: SQLAlchemy model instance
        vertical: Vertical prefix for UUID generation ('dc', 'saas', 'msp')

    Returns:
        The UUID (existing or newly generated)
    """
    if not hasattr(instance, 'uuid'):
        return None

    if instance.uuid:
        return instance.uuid

    # Determine entity type from model class name
    class_name = instance.__class__.__name__.lower()
    entity_map = {
        'customer': 'customer',
        'account': 'account',
        'user': 'user',
        'product': 'product',
        'customerconfig': 'customer_config',
    }
    entity_type = entity_map.get(class_name, class_name)

    new_uuid = generate_id(vertical, entity_type)
    instance.uuid = new_uuid

    # Also set vertical if the column exists
    if hasattr(instance, 'vertical') and not instance.vertical:
        instance.vertical = vertical

    logger.debug(f"Generated UUID for {class_name}: {new_uuid}")
    return new_uuid


def ensure_customer_uuid_on_account(account, customer):
    """
    Set account.customer_uuid from the parent Customer's uuid.

    Args:
        account: Account model instance
        customer: Customer model instance (must have uuid set)
    """
    if hasattr(account, 'customer_uuid') and customer and hasattr(customer, 'uuid'):
        if not account.customer_uuid and customer.uuid:
            account.customer_uuid = customer.uuid


def enrich_with_uuid(data: dict, model_instance=None, **overrides) -> dict:
    """
    Enrich a dict (API response) with UUID fields from a model instance.

    Example:
        response = {"account_id": 5001, "name": "Foo"}
        enriched = enrich_with_uuid(response, account)
        # → {"account_id": 5001, "name": "Foo", "uuid": "dc_acct_019...", "customer_uuid": "dc_cust_019..."}

    Args:
        data: Dict to enrich (not modified in place)
        model_instance: Model with uuid/customer_uuid/account_uuid columns
        **overrides: Additional key-value pairs to add

    Returns:
        New dict with UUID fields added
    """
    result = dict(data)

    if model_instance:
        for field in ('uuid', 'customer_uuid', 'account_uuid', 'vertical'):
            value = getattr(model_instance, field, None)
            if value and field not in result:
                result[field] = value

    result.update(overrides)
    return result


def get_id_or_uuid(request_args, param_name: str = 'id') -> Union[str, int, None]:
    """
    Extract an ID from request args/params, returning int if numeric, str if UUID.

    Usage in Flask route:
        @app.route('/api/resource/<identifier>')
        def get_resource(identifier):
            resolved_id = get_id_or_uuid_from_path(identifier)

    Args:
        request_args: Flask request.args or similar dict
        param_name: Parameter name to look for

    Returns:
        int if numeric, str if UUID-like, None if missing
    """
    value = request_args.get(param_name)
    if value is None:
        return None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def parse_path_id(identifier: str) -> Union[int, str]:
    """
    Parse a URL path segment that could be an integer ID or UUID string.

    Args:
        identifier: Path segment string

    Returns:
        int if numeric, str if UUID-like
    """
    if identifier.isdigit():
        return int(identifier)
    return identifier
