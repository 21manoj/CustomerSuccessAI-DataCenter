"""
Shared access-control helpers — per the spec's Build Prompt rule #2 and
Gotcha 2 ("NULL-means-unrestricted is easy to get backwards at a call
site"). One implementation, used everywhere, never re-implemented inline at
a call site.

DELIBERATE DEVIATION FROM THE SPEC'S LITERAL PSEUDOCODE — flagged here and
in the pilot report:

The Build Prompt gives this exact code to implement:

    def has_account_access(principal, account_id) -> bool:
        if principal.allowed_account_ids is None: return True
        return account_id in principal.allowed_account_ids

    def has_customer_access(principal, customer_id) -> bool:
        if principal.allowed_customer_ids is None:
            return customer_id == principal.customer_id
        return customer_id in principal.allowed_customer_ids

Neither function takes or checks `expires_at`. But:
  - Acceptance Criteria bullet 6 requires: "A User with expires_at in the
    past is treated as having no access regardless of
    allowed_account_ids/allowed_customer_ids content — expiry is checked
    independently of, and prior to, the allowlist checks."
  - Gotcha 2's own "Fix" text says the shared helper must be "tested
    exhaustively for the NULL/empty-list/populated-list/expired matrix" —
    i.e. the Gotcha itself assumes expiry is part of what this helper
    checks.

An agent that implemented the Build Prompt's literal code and stopped there
would satisfy the Build Prompt on its face and then fail Acceptance
Criteria bullet 6 and the Reference Test Harness's "expired principal" case.
This is the same class of bug the Module 03 pilot validation found (Build
Prompt text contradicting a later section) — see pilot report section 5.

Resolution taken here: added an expiry check, applied before the allowlist
check, in both functions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Principal:
    """A User or CustomerApiKey row, translated into the shape these
    functions need (see schema.to_principal)."""

    customer_id: Optional[int]
    allowed_account_ids: Optional[List[int]]
    allowed_customer_ids: Optional[List[int]]
    expires_at: Optional[datetime]


def _is_expired(principal: Principal, now: Optional[datetime] = None) -> bool:
    if principal.expires_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    return principal.expires_at < now


def has_account_access(principal: Principal, account_id: int) -> bool:
    # Expiry checked independently of, and prior to, the allowlist check —
    # Acceptance Criteria bullet 6.
    if _is_expired(principal):
        return False
    if principal.allowed_account_ids is None:
        return True
    # Empty list is NOT the same as NULL: "access to nothing," not
    # "unrestricted" — Reference Test Harness item 2.
    return account_id in principal.allowed_account_ids


def has_customer_access(principal: Principal, customer_id: int) -> bool:
    if _is_expired(principal):
        return False
    if principal.allowed_customer_ids is None:
        # NULL = "own customer only" per the Data Shapes note — NOT
        # unrestricted. This is the one asymmetry between the two
        # functions: has_account_access's NULL means "every account
        # anywhere," but has_customer_access's NULL is scoped to the
        # principal's own tenant. Easy to misread as the same rule; it
        # isn't (see pilot report section 2).
        return customer_id == principal.customer_id
    return customer_id in principal.allowed_customer_ids
