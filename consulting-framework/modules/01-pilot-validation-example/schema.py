"""
Foundation Data Model — thin Python layer over schema.sql.

Built from consulting-framework/modules/01-foundation-data-model.md ALONE,
for an invented vertical: "fitguild_v1" (FitGuild — boutique fitness-studio
SaaS). Customer = franchise operator. Account = one physical studio location.

Why schema.sql + a thin layer instead of an ORM:

  1. Gotcha 1 in the spec is specifically about ORM-declared foreign keys not
     being physically present in the database (an annotation, not a
     constraint). Writing the DDL directly sidesteps that entire failure
     mode by construction — there is no ORM model file that could drift from
     the real schema. The Acceptance Criteria / Reference Test Harness still
     require *proving* the FK exists via the database's own constraint
     catalog, which this pilot does in test_data_model.py regardless of how
     the schema was authored — the point isn't "trust that raw SQL is
     correct," it's "don't trust any layer's self-report."

  2. SQLite is the in-repo, no-Postgres-needed substitute the task calls
     for. It supports real FK enforcement, but ONLY if `PRAGMA foreign_keys
     = ON` is set on every single connection (it is OFF by default and does
     NOT persist across connections/processes). That is exactly the kind of
     "easy to get backwards silently" footgun the spec warns about elsewhere
     (Gotcha 2) applied to connection setup instead of access control, so it
     gets the same treatment: one shared `connect()` function, never a
     per-call-site PRAGMA.

Constraint catalog note: this pilot uses SQLite, not Postgres, so the exact
commands the spec names (`pg_constraint` / `information_schema.
table_constraints`) don't apply verbatim. `PRAGMA foreign_key_list(<table>)`
is SQLite's structured constraint-catalog equivalent — it reads the engine's
own parsed schema metadata, not the Python model/helper code in this file —
which satisfies the same requirement the Gotcha is protecting against
("don't trust the ORM model file as proof").
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

VERTICAL = "fitguild_v1"


def connect(db_path: str = ":memory:") -> sqlite3.Connection:
    """Single choke point for connection creation so FK enforcement and row
    access are never a per-call-site decision (see module docstring)."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def new_uuid(kind: str, vertical: str = VERTICAL) -> str:
    """Type-prefixed external UUID per the Build Prompt, e.g.
    'fitguild_v1_acct_3f9e...'. `kind` is entity-specific (cust/acct/user) —
    the spec's own example only shows the account case; see report for the
    ambiguity this required guessing on."""
    return f"{vertical}_{kind}_{uuid4()}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ---------------------------------------------------------------------------
# Inserts. Deliberately thin — no query builder, no ORM — so it's obvious
# every value that hits the DB came from this file, not framework magic.
# ---------------------------------------------------------------------------

def insert_customer(
    conn: sqlite3.Connection,
    customer_name: str,
    email: str,
    domain: Optional[str] = None,
    vertical: str = VERTICAL,
) -> sqlite3.Row:
    uuid = new_uuid("cust", vertical)
    cur = conn.execute(
        "INSERT INTO customers (customer_name, email, domain, vertical, uuid) "
        "VALUES (?, ?, ?, ?, ?)",
        (customer_name, email, domain, vertical, uuid),
    )
    conn.commit()
    return get_customer(conn, cur.lastrowid)


def get_customer(conn: sqlite3.Connection, customer_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()


def insert_account(
    conn: sqlite3.Connection,
    customer_id: int,
    account_name: str,
    revenue: float = 0,
    account_status: str = "active",
    vertical: str = VERTICAL,
) -> sqlite3.Row:
    uuid = new_uuid("acct", vertical)
    cur = conn.execute(
        "INSERT INTO accounts (customer_id, account_name, revenue, account_status, uuid) "
        "VALUES (?, ?, ?, ?, ?)",
        (customer_id, account_name, revenue, account_status, uuid),
    )
    conn.commit()
    return get_account(conn, cur.lastrowid)


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()


def get_account_scoped(
    conn: sqlite3.Connection, account_id: int, customer_id: int
) -> Optional[sqlite3.Row]:
    """The multi-tenancy filter contract from the Engine section, made
    concrete: 'any function reading client data by ID alone ... must accept
    and enforce customer_id, returning "not found" rather than another
    tenant's row on mismatch.' This is the read path Reference Test Harness
    item 3 (cross-tenant fixture test) exercises."""
    return conn.execute(
        "SELECT * FROM accounts WHERE account_id = ? AND customer_id = ?",
        (account_id, customer_id),
    ).fetchone()


def insert_user(
    conn: sqlite3.Connection,
    user_name: str,
    email: str,
    password_hash: str,
    customer_id: Optional[int] = None,
    allowed_account_ids: Optional[List[int]] = None,
    allowed_customer_ids: Optional[List[int]] = None,
    expires_at: Optional[str] = None,
    is_contractor: bool = False,
    active: bool = True,
    vertical: str = VERTICAL,
) -> sqlite3.Row:
    uuid = new_uuid("user", vertical)
    cur = conn.execute(
        "INSERT INTO users (customer_id, user_name, email, password_hash, active, "
        "allowed_account_ids, allowed_customer_ids, expires_at, is_contractor, uuid) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            customer_id,
            user_name,
            email,
            password_hash,
            1 if active else 0,
            json.dumps(allowed_account_ids) if allowed_account_ids is not None else None,
            json.dumps(allowed_customer_ids) if allowed_customer_ids is not None else None,
            expires_at,
            1 if is_contractor else 0,
            uuid,
        ),
    )
    conn.commit()
    return get_user(conn, cur.lastrowid)


def get_user(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def insert_customer_config(
    conn: sqlite3.Connection,
    customer_id: int,
    vertical: str = VERTICAL,
    config: Optional[dict] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO customer_configs (customer_id, vertical, config_json) VALUES (?, ?, ?)",
        (customer_id, vertical, json.dumps(config or {})),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM customer_configs WHERE config_id = ?", (cur.lastrowid,)
    ).fetchone()


def insert_customer_api_key(
    conn: sqlite3.Connection,
    customer_id: int,
    key_prefix: str,
    key_hash: str,
    scopes: Optional[List[str]] = None,
    allowed_account_ids: Optional[List[int]] = None,
    expires_at: Optional[str] = None,
    is_active: bool = True,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO customer_api_keys (customer_id, key_prefix, key_hash, scopes, "
        "allowed_account_ids, expires_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            customer_id,
            key_prefix,
            key_hash,
            json.dumps(scopes) if scopes is not None else None,
            json.dumps(allowed_account_ids) if allowed_account_ids is not None else None,
            expires_at,
            1 if is_active else 0,
        ),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM customer_api_keys WHERE id = ?", (cur.lastrowid,)
    ).fetchone()


def fk_constraints(conn: sqlite3.Connection, table: str) -> list:
    """Query the database's OWN constraint metadata — not this module's SQL
    strings, not any model class — per Acceptance Criteria bullet 2 / Gotcha
    1. `PRAGMA foreign_key_list` returns one row per FK physically present
    in the compiled schema; columns: id, seq, table, from, to, on_update,
    on_delete, match."""
    return conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()


# ---------------------------------------------------------------------------
# Row -> Principal conversion for access_control.py. sqlite3.Row does not
# support the dot-notation the spec's pseudocode uses (`principal.
# allowed_account_ids`), and JSON columns come back as TEXT, so this is the
# one required translation layer between "a User or CustomerApiKey row" (the
# spec's words) and the access_control functions.
# ---------------------------------------------------------------------------

def _parse_json_list(raw: Optional[str]) -> Optional[List[Any]]:
    if raw is None:
        return None
    return json.loads(raw)


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if raw is None:
        return None
    dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.replace(tzinfo=timezone.utc)


def to_principal(row: sqlite3.Row) -> "access_control.Principal":  # noqa: F821
    from access_control import Principal  # local import avoids a hard cycle

    keys = row.keys()
    return Principal(
        customer_id=row["customer_id"] if "customer_id" in keys else None,
        allowed_account_ids=_parse_json_list(row["allowed_account_ids"]),
        allowed_customer_ids=(
            _parse_json_list(row["allowed_customer_ids"])
            if "allowed_customer_ids" in keys
            else None
        ),
        expires_at=_parse_iso(row["expires_at"]) if "expires_at" in keys else None,
    )
