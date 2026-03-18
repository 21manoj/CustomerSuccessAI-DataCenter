#!/usr/bin/env python3
"""
API Key Service
===============

Manages API key lifecycle for customer integrations:
  - generate_api_key  : create a new key (returns full key only once)
  - validate_api_key  : look up + verify a raw key against stored hash
  - revoke_api_key    : soft-delete (deactivate) a key

Key format:  csp_{scope}_{random40}
Storage:     SHA-256 hash only (full key is never persisted)
"""

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional, Tuple

from extensions import db
from models import CustomerApiKey

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_KEY_PREFIX_LEN = 12      # Characters of the key stored as prefix for lookup
_RANDOM_BYTES = 30        # secrets.token_urlsafe(30) -> ~40 URL-safe chars
VALID_SCOPES = {'read', 'write', 'admin'}
VALID_PARTNER_TIERS = {
    'direct_enterprise',
    'reseller',
    'technology_partner',
    'referral',
}

# ---------------------------------------------------------------------------
# Rate Limiting — IP-prefix-based failure tracking
# ---------------------------------------------------------------------------
# Track validation failures by IP prefix to block brute-force attacks.
# 5 failures within RATE_LIMIT_WINDOW_SEC → blocked for RATE_LIMIT_BLOCK_SEC.
_RATE_LIMIT_MAX_FAILURES = 5
_RATE_LIMIT_WINDOW_SEC = 300      # 5 minutes
_RATE_LIMIT_BLOCK_SEC = 60        # 60 seconds block after exceeding threshold
_RATE_LIMIT_CLEANUP_INTERVAL = 600  # Lazy cleanup every 10 minutes

# { ip_prefix: [timestamp, timestamp, ...] }
_fail_tracker: dict = defaultdict(list)
_last_cleanup: float = 0.0


def _get_caller_ip() -> str:
    """Extract the caller's IP address (or 'unknown' outside request context)."""
    try:
        from flask import request as flask_request
        return flask_request.remote_addr or 'unknown'
    except RuntimeError:
        return 'unknown'


def _cleanup_stale_entries():
    """Remove stale entries from _fail_tracker (lazy, periodic)."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _RATE_LIMIT_CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    cutoff = now - _RATE_LIMIT_WINDOW_SEC
    stale_keys = [
        ip for ip, timestamps in _fail_tracker.items()
        if not timestamps or timestamps[-1] < cutoff
    ]
    for ip in stale_keys:
        del _fail_tracker[ip]


def _is_rate_limited(ip: str) -> bool:
    """Check if an IP is currently rate-limited due to excessive failures."""
    _cleanup_stale_entries()
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW_SEC
    # Prune old entries for this IP
    _fail_tracker[ip] = [t for t in _fail_tracker[ip] if t > cutoff]
    if len(_fail_tracker[ip]) >= _RATE_LIMIT_MAX_FAILURES:
        # Check if the most recent failure was within the block window
        last_fail = _fail_tracker[ip][-1]
        if now - last_fail < _RATE_LIMIT_BLOCK_SEC:
            return True
    return False


def _record_failure(ip: str):
    """Record a validation failure for rate limiting."""
    _fail_tracker[ip].append(time.time())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _hash_key(raw_key: str) -> str:
    """Return the hex-encoded SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def _build_key(scope: str) -> str:
    """
    Build a new API key string.
    Format: csp_{scope}_{random}
    """
    random_part = secrets.token_urlsafe(_RANDOM_BYTES)
    return f"csp_{scope}_{random_part}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_api_key(
    customer_id: int,
    created_by: int,
    name: str,
    scopes: list = None,
    expires_at: datetime = None,
    allowed_account_ids: list = None,
    partner_tier: str = None,
) -> tuple:
    """
    Generate a new API key for a customer.

    Parameters
    ----------
    customer_id : int
        The customer this key belongs to.
    created_by : int
        The user_id of the person creating the key.
    name : str
        Human-readable label for the key (e.g. "CI Pipeline").
    scopes : list, optional
        List of scope strings (default: ['read']).
        Valid values: 'read', 'write', 'admin'.
    expires_at : datetime, optional
        When the key should expire.  None = never.
    allowed_account_ids : list, optional
        List of account IDs this key can access. None = all accounts.
        Use this to restrict a partner key to specific accounts
        (e.g. [354001, 354003] for 2 accounts out of 8).
    partner_tier : str, optional
        Partner classification for P4 access patterns.
        Valid values: 'direct_enterprise', 'reseller',
        'technology_partner', 'referral'. None = not a partner key.

    Returns
    -------
    tuple (full_key: str, key_record: CustomerApiKey)
        full_key is shown to the user exactly once.
        key_record is the persisted DB row (hash only).

    Raises
    ------
    ValueError
        If scopes contain invalid values, name is empty, or partner_tier invalid.
    """
    if not name or not name.strip():
        raise ValueError("API key name is required")

    if scopes is None:
        scopes = ['read']

    # Validate scopes
    invalid = set(scopes) - VALID_SCOPES
    if invalid:
        raise ValueError(f"Invalid scopes: {invalid}. Valid scopes: {VALID_SCOPES}")

    # Validate partner_tier
    if partner_tier is not None and partner_tier not in VALID_PARTNER_TIERS:
        raise ValueError(
            f"Invalid partner_tier '{partner_tier}'. "
            f"Valid values: {sorted(VALID_PARTNER_TIERS)}"
        )

    # Determine primary scope for key format
    if 'admin' in scopes:
        primary_scope = 'admin'
    elif 'write' in scopes:
        primary_scope = 'write'
    else:
        primary_scope = 'read'

    # Build the full key
    full_key = _build_key(primary_scope)
    key_prefix = full_key[:_KEY_PREFIX_LEN]
    key_hash = _hash_key(full_key)

    # Persist
    key_record = CustomerApiKey(
        customer_id=customer_id,
        created_by=created_by,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=name.strip(),
        scopes=scopes,
        allowed_account_ids=allowed_account_ids,
        is_active=True,
        expires_at=expires_at,
        partner_tier=partner_tier,
    )
    db.session.add(key_record)
    db.session.commit()

    logger.info(
        "API key created: id=%s prefix=%s customer=%s name='%s' scopes=%s "
        "accounts=%s partner_tier=%s",
        key_record.id, key_prefix, customer_id, name, scopes,
        allowed_account_ids or 'ALL', partner_tier or 'N/A',
    )

    return full_key, key_record


def validate_api_key(raw_key: str) -> Optional[CustomerApiKey]:
    """
    Validate a raw API key string against stored hashes.

    Steps:
      0. Check rate limit (IP-prefix-based).
      1. Extract the 12-char prefix for a fast DB lookup.
      2. Hash the full key and compare against stored hash.
      3. Check is_active and expiry.
      4. Update last_used_at / last_used_ip.
      5. On failure, record for rate limiting.

    Parameters
    ----------
    raw_key : str
        The full API key provided by the caller.

    Returns
    -------
    CustomerApiKey or None
        The matching key record if valid, else None.
    """
    if not raw_key or len(raw_key) < _KEY_PREFIX_LEN:
        return None

    # Rate limit check
    caller_ip = _get_caller_ip()
    if _is_rate_limited(caller_ip):
        logger.warning("Rate limited: IP=%s (too many failed attempts)", caller_ip)
        return None

    prefix = raw_key[:_KEY_PREFIX_LEN]
    candidate_hash = _hash_key(raw_key)

    # Lookup by prefix first (indexed), then verify hash
    candidates = (
        CustomerApiKey.query
        .filter_by(key_prefix=prefix, is_active=True)
        .all()
    )

    for candidate in candidates:
        if candidate.key_hash == candidate_hash:
            # Check expiry
            if candidate.expires_at and candidate.expires_at < datetime.utcnow():
                logger.info("API key id=%s has expired", candidate.id)
                return None

            # Update usage tracking
            candidate.last_used_at = datetime.utcnow()
            try:
                from flask import request as flask_request
                candidate.last_used_ip = flask_request.remote_addr
            except RuntimeError:
                # Outside request context (e.g. testing)
                pass

            db.session.commit()

            logger.debug("API key validated: id=%s customer=%s", candidate.id, candidate.customer_id)
            return candidate

    # No match — record failure for rate limiting
    _record_failure(caller_ip)
    logger.info("API key validation failed: prefix=%s ip=%s", prefix, caller_ip)
    return None


def revoke_api_key(key_id: int) -> bool:
    """
    Revoke (deactivate) an API key by its database ID.

    Parameters
    ----------
    key_id : int
        The primary key of the CustomerApiKey record.

    Returns
    -------
    bool
        True if the key was found and revoked, False otherwise.
    """
    key_record = db.session.get(CustomerApiKey, key_id)
    if not key_record:
        logger.warning("Attempted to revoke non-existent API key id=%s", key_id)
        return False

    if not key_record.is_active:
        logger.info("API key id=%s is already revoked", key_id)
        return True

    key_record.is_active = False
    db.session.commit()

    logger.info(
        "API key revoked: id=%s prefix=%s customer=%s",
        key_record.id, key_record.key_prefix, key_record.customer_id,
    )
    return True


def list_api_keys(customer_id: int, include_revoked: bool = False) -> list:
    """
    List all API keys for a customer.

    Parameters
    ----------
    customer_id : int
    include_revoked : bool
        If True, include inactive/revoked keys.

    Returns
    -------
    list of dict
        Each dict is the to_dict() representation of a CustomerApiKey.
    """
    query = CustomerApiKey.query.filter_by(customer_id=customer_id)
    if not include_revoked:
        query = query.filter_by(is_active=True)
    return [k.to_dict() for k in query.order_by(CustomerApiKey.created_at.desc()).all()]
