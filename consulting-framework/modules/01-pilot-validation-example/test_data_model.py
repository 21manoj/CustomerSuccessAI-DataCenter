"""
Test suite exercising every Acceptance Criteria bullet in
consulting-framework/modules/01-foundation-data-model.md literally, plus the
three Reference Test Harness items, plus a couple of tests covering places
the spec was ambiguous and a choice had to be made (labeled BONUS).

Run: python -m pytest test_data_model.py -v
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import schema
from access_control import Principal, has_account_access, has_customer_access
from schema import to_principal


@pytest.fixture
def conn():
    c = schema.connect(":memory:")
    schema.init_db(c)
    yield c
    c.close()


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ===========================================================================
# Acceptance Criteria bullet 1:
# "Creating an Account row with a customer_id that doesn't exist in
# customers raises a database-level integrity error — it is not possible to
# insert an orphaned account through the schema itself (regardless of what
# application code attempts)."
# ===========================================================================

def test_ac1_orphaned_account_insert_raises_integrity_error(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO accounts (customer_id, account_name, uuid) "
            "VALUES (?, ?, ?)",
            (999_999, "Ghost Studio", "fitguild_v1_acct_orphan"),
        )
    conn.rollback()
    # Prove it: no row exists.
    row = conn.execute(
        "SELECT * FROM accounts WHERE account_name = ?", ("Ghost Studio",)
    ).fetchone()
    assert row is None


def test_ac1_holds_regardless_of_application_code_path(conn):
    """Same assertion via the schema.py insert_account() helper, not raw
    SQL, to show the constraint holds no matter which application code path
    is used to attempt the insert — the schema itself is what's enforcing
    this, not any particular helper function's validation."""
    with pytest.raises(sqlite3.IntegrityError):
        schema.insert_account(conn, customer_id=424_242, account_name="Ghost Studio 2")


# ===========================================================================
# Acceptance Criteria bullet 2 / Reference Test Harness item 1
# (constraint-catalog assertion — "the single highest-value test in this
# module"):
# "A directly-queried constraint catalog listing shows a foreign-key
# constraint from accounts.customer_id to customers.customer_id — don't
# accept 'the ORM model declares it' as sufficient evidence; query the
# actual database."
# ===========================================================================

def test_ac2_constraint_catalog_shows_accounts_customer_id_fk(conn):
    # PRAGMA foreign_key_list is SQLite's structured constraint-catalog
    # query — it reads the compiled schema the SQLite engine itself parsed
    # out of the CREATE TABLE statement, not any Python source in this repo.
    fks = schema.fk_constraints(conn, "accounts")
    matches = [fk for fk in fks if fk["from"] == "customer_id" and fk["table"] == "customers" and fk["to"] == "customer_id"]
    assert len(matches) == 1, (
        f"expected exactly one accounts.customer_id -> customers.customer_id "
        f"FK in the constraint catalog, found: {fks}"
    )


def test_ac2_constraint_catalog_covers_every_customer_id_fk(conn):
    """The Build Prompt's rule is broader than the single Acceptance
    Criteria example: 'Every foreign key to customers.customer_id or
    accounts.account_id must be a real, DB-enforced foreign key
    constraint.' Checking all four FK columns this schema has, not just the
    one the Acceptance Criteria spells out."""
    expectations = {
        "accounts": ("customer_id", "customers", "customer_id"),
        "users": ("customer_id", "customers", "customer_id"),
        "customer_configs": ("customer_id", "customers", "customer_id"),
        "customer_api_keys": ("customer_id", "customers", "customer_id"),
    }
    for table, (from_col, to_table, to_col) in expectations.items():
        fks = schema.fk_constraints(conn, table)
        matches = [
            fk for fk in fks
            if fk["from"] == from_col and fk["table"] == to_table and fk["to"] == to_col
        ]
        assert len(matches) == 1, f"{table}.{from_col} -> {to_table}.{to_col} missing from catalog: {fks}"


def test_ac2_catalog_query_does_not_depend_on_python_layer(conn):
    """Sanity check on the 'don't trust the model file' spirit of the
    criterion: the same PRAGMA query run on a *raw* sqlite3 connection that
    never imported schema.py's helpers still finds the constraint, proving
    it's physically in the database file/schema, not conjured by this
    repo's Python code."""
    raw = sqlite3.connect(":memory:")
    raw.executescript(schema.SCHEMA_PATH.read_text())
    fks = raw.execute("PRAGMA foreign_key_list(accounts)").fetchall()
    assert any(fk[3] == "customer_id" and fk[2] == "customers" for fk in fks)
    raw.close()


# ===========================================================================
# Acceptance Criteria bullet 3:
# "has_account_access(user_with_null_allowed_account_ids, ANY_ACCOUNT_ID)
# returns True for every account, including ones created after the user
# was. has_account_access(user_with_allowed_account_ids=[1,2],
# account_id=3) returns False."
# ===========================================================================

def test_ac3_null_allowlist_grants_access_to_any_account_including_future_ones(conn):
    customer = schema.insert_customer(conn, "FitGuild HQ", "hq@fitguild.example")
    user = schema.insert_user(
        conn, "Alex Admin", "alex@fitguild.example", "hash",
        customer_id=customer["customer_id"], allowed_account_ids=None,
    )
    principal = to_principal(user)

    existing = schema.insert_account(conn, customer["customer_id"], "Downtown Studio")
    assert has_account_access(principal, existing["account_id"]) is True

    # "including ones created after the user was" — literally create a new
    # account after the user row exists and confirm access still holds.
    future_account = schema.insert_account(conn, customer["customer_id"], "New Studio Opened Later")
    assert has_account_access(principal, future_account["account_id"]) is True
    assert has_account_access(principal, 9_999_999) is True  # any ID at all


def test_ac3_populated_allowlist_denies_non_member(conn):
    principal = Principal(
        customer_id=1, allowed_account_ids=[1, 2], allowed_customer_ids=None, expires_at=None,
    )
    assert has_account_access(principal, 3) is False
    assert has_account_access(principal, 1) is True
    assert has_account_access(principal, 2) is True


# ===========================================================================
# Acceptance Criteria bullet 4:
# "Two different Customer rows never receive colliding uuid values (unique
# constraint enforced at the DB level, not just checked in application
# code)."
# ===========================================================================

def test_ac4_duplicate_customer_uuid_rejected_at_db_level(conn):
    schema.insert_customer(conn, "Customer One", "one@fitguild.example")
    # Force a collision directly via SQL, bypassing schema.py's uuid4()
    # generation entirely, so the test proves the DB constraint itself
    # rejects it — not that the Python helper happens to avoid collisions.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO customers (customer_name, email, vertical, uuid) "
            "VALUES (?, ?, ?, ?)",
            ("Customer Two", "two@fitguild.example", "fitguild_v1",
             conn.execute("SELECT uuid FROM customers WHERE customer_name = ?", ("Customer One",)).fetchone()["uuid"]),
        )
    conn.rollback()


def test_ac4_uuid_uniqueness_is_a_real_index_not_app_logic(conn):
    fks = conn.execute("PRAGMA index_list(customers)").fetchall()
    unique_indexes = [ix for ix in fks if ix["unique"] == 1]
    # customers.email and customers.domain and customers.uuid should all be
    # backed by real unique indexes (auto-created by the UNIQUE column
    # constraints in schema.sql).
    assert len(unique_indexes) >= 3, unique_indexes


# ===========================================================================
# Acceptance Criteria bullet 5:
# "Adding a new nullable column to Account does not require changing any
# existing INSERT statement elsewhere in the codebase (proves the
# additive-only pattern is actually additive, not merely intended to be)."
# ===========================================================================

def test_ac5_additive_column_does_not_break_existing_inserts(conn):
    # Insert BEFORE the schema change, using the same helper the rest of
    # the suite uses (i.e. an "existing INSERT statement elsewhere in the
    # codebase").
    customer = schema.insert_customer(conn, "Additive Co", "additive@fitguild.example")
    before = schema.insert_account(conn, customer["customer_id"], "Studio Before")
    assert before["account_id"] is not None

    # Additive-only schema evolution: new nullable column, no repurposing.
    conn.execute("ALTER TABLE accounts ADD COLUMN loyalty_tier TEXT")
    conn.commit()

    # The EXACT SAME insert_account() call — unmodified — still works.
    after = schema.insert_account(conn, customer["customer_id"], "Studio After")
    assert after["account_id"] is not None

    # New column defaults to NULL for both the pre-existing row and any row
    # inserted through the unmodified statement.
    row = conn.execute(
        "SELECT loyalty_tier FROM accounts WHERE account_id = ?", (after["account_id"],)
    ).fetchone()
    assert row["loyalty_tier"] is None


# ===========================================================================
# Acceptance Criteria bullet 6:
# "A User with expires_at in the past is treated as having no access
# regardless of allowed_account_ids/allowed_customer_ids content — expiry
# is checked independently of, and prior to, the allowlist checks."
# ===========================================================================

def test_ac6_expired_user_denied_even_with_null_allowlist(conn):
    past = iso(datetime.now(timezone.utc) - timedelta(days=1))
    customer = schema.insert_customer(conn, "Expiry Co", "expiry@fitguild.example")
    user = schema.insert_user(
        conn, "Expired Contractor", "expired@fitguild.example", "hash",
        customer_id=customer["customer_id"],
        allowed_account_ids=None,  # otherwise "unrestricted"
        allowed_customer_ids=None,
        expires_at=past,
        is_contractor=True,
    )
    principal = to_principal(user)
    assert has_account_access(principal, 1) is False
    assert has_customer_access(principal, customer["customer_id"]) is False


def test_ac6_expired_user_denied_even_when_target_is_in_allowlist(conn):
    """The critical case: expiry must win even when the allowlist alone
    would grant access — proves expiry is checked prior to, not merged
    with, the allowlist check."""
    past = iso(datetime.now(timezone.utc) - timedelta(days=1))
    principal = Principal(
        customer_id=1, allowed_account_ids=[42], allowed_customer_ids=[1],
        expires_at=datetime.strptime(past, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc),
    )
    assert has_account_access(principal, 42) is False  # would be True if not expired
    assert has_customer_access(principal, 1) is False  # would be True if not expired


def test_ac6_future_expiry_does_not_deny_access(conn):
    future = datetime.now(timezone.utc) + timedelta(days=30)
    principal = Principal(
        customer_id=1, allowed_account_ids=None, allowed_customer_ids=None, expires_at=future,
    )
    assert has_account_access(principal, 1) is True


# ===========================================================================
# Reference Test Harness item 2: table-driven access-control matrix,
# including the empty-list case the Acceptance Criteria bullets don't
# spell out but the Harness text does: "empty-list allowlist ... should
# behave as 'access to nothing,' not 'unrestricted'".
# ===========================================================================

@pytest.mark.parametrize(
    "allowed_account_ids,target_id,expected",
    [
        (None, 1, True),          # NULL -> unrestricted
        (None, 999, True),        # NULL -> unrestricted, any ID
        ([1, 2], 1, True),        # populated, member
        ([1, 2], 3, False),       # populated, non-member
        ([], 1, False),           # empty list -> access to NOTHING, not everything
    ],
)
def test_rth2_has_account_access_matrix(allowed_account_ids, target_id, expected):
    principal = Principal(
        customer_id=1, allowed_account_ids=allowed_account_ids,
        allowed_customer_ids=None, expires_at=None,
    )
    assert has_account_access(principal, target_id) is expected


@pytest.mark.parametrize(
    "allowed_customer_ids,own_customer_id,target_id,expected",
    [
        (None, 1, 1, True),       # NULL -> own customer only, matches
        (None, 1, 2, False),      # NULL -> own customer only, mismatch
        ([1, 2], 5, 2, True),     # populated, member (even though not own customer)
        ([1, 2], 5, 3, False),    # populated, non-member
        ([], 1, 1, False),        # empty list -> access to nothing, even own customer
    ],
)
def test_rth2_has_customer_access_matrix(allowed_customer_ids, own_customer_id, target_id, expected):
    principal = Principal(
        customer_id=own_customer_id, allowed_account_ids=None,
        allowed_customer_ids=allowed_customer_ids, expires_at=None,
    )
    assert has_customer_access(principal, target_id) is expected


def test_rth2_expired_matrix_overrides_every_allowlist_shape():
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    for allowed in (None, [], [1, 2]):
        principal = Principal(
            customer_id=1, allowed_account_ids=allowed, allowed_customer_ids=allowed,
            expires_at=past,
        )
        assert has_account_access(principal, 1) is False
        assert has_customer_access(principal, 1) is False


# ===========================================================================
# Reference Test Harness item 3 (cross-tenant fixture test):
# "create two customers with accounts under each, and assert that every
# read path in modules built on top of this one ... returns
# missing/not_found rather than data when given a real account_id alongside
# the wrong customer_id."
# ===========================================================================

def test_rth3_cross_tenant_read_returns_not_found_not_data(conn):
    customer_a = schema.insert_customer(conn, "Tenant A", "a@fitguild.example")
    customer_b = schema.insert_customer(conn, "Tenant B", "b@fitguild.example")
    account_a = schema.insert_account(conn, customer_a["customer_id"], "Tenant A Studio")
    account_b = schema.insert_account(conn, customer_b["customer_id"], "Tenant B Studio")

    # Right account, right tenant -> data.
    assert schema.get_account_scoped(conn, account_a["account_id"], customer_a["customer_id"]) is not None

    # Right (real, existing) account_id, WRONG tenant -> not found, never
    # tenant B's account data leaking into a tenant-A-scoped read.
    leaked = schema.get_account_scoped(conn, account_b["account_id"], customer_a["customer_id"])
    assert leaked is None

    leaked_other_direction = schema.get_account_scoped(conn, account_a["account_id"], customer_b["customer_id"])
    assert leaked_other_direction is None


# ===========================================================================
# BONUS — coverage for spots the spec was ambiguous (see report). Not
# derived from a specific Acceptance Criteria bullet.
# ===========================================================================

def test_bonus_domain_nullable_unique_allows_multiple_nulls(conn):
    """The spec says 'domain (unique, nullable)' without stating whether
    multiple customers can have a NULL domain simultaneously. Standard SQL
    unique-constraint semantics treat NULLs as non-equal to each other (SQLite
    and Postgres both), so multiple NULLs are allowed. Verifying that's what
    this schema actually does, since 'unique, nullable' alone doesn't say so."""
    schema.insert_customer(conn, "No Domain One", "nd1@fitguild.example", domain=None)
    schema.insert_customer(conn, "No Domain Two", "nd2@fitguild.example", domain=None)
    count = conn.execute("SELECT COUNT(*) AS c FROM customers WHERE domain IS NULL").fetchone()["c"]
    assert count == 2


def test_bonus_customer_config_is_one_per_customer(conn):
    """Data Shapes says 'customer_id (FK, UNIQUE — one config row per
    customer, not a list)'. Confirming that UNIQUE constraint is real."""
    customer = schema.insert_customer(conn, "Config Co", "config@fitguild.example")
    schema.insert_customer_config(conn, customer["customer_id"])
    with pytest.raises(sqlite3.IntegrityError):
        schema.insert_customer_config(conn, customer["customer_id"])


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
