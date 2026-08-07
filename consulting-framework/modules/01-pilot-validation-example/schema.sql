-- Foundation Data Model — DDL, built from
-- consulting-framework/modules/01-foundation-data-model.md alone.
--
-- Vertical for this pilot: "fitguild_v1" — FitGuild, a boutique
-- fitness-studio SaaS. Customer = franchise operator (the client's client).
-- Account = one physical studio location that gets a health score.
--
-- SQLite specifics called out inline where they matter for the FK-enforcement
-- requirement (Gotcha 1 / Acceptance Criteria bullets 1-2). Foreign keys are
-- OFF by default per SQLite *connection* — schema.py's connect() turns them
-- on for every connection so this is never a per-call-site decision.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- customers — tenant root. Everything else hangs off customer_id.
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    domain        TEXT UNIQUE,              -- nullable; SQLite/Postgres both
                                             -- allow multiple NULLs under a
                                             -- UNIQUE constraint, which is the
                                             -- behavior "unique, nullable"
                                             -- implies but the spec doesn't
                                             -- state outright (see report).
    vertical      TEXT NOT NULL,
    uuid          TEXT NOT NULL UNIQUE,      -- external ID, e.g.
                                             -- "fitguild_v1_cust_<uuid4>"
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ---------------------------------------------------------------------------
-- accounts — sub-tenant unit within a customer (a FitGuild studio location).
-- ---------------------------------------------------------------------------
CREATE TABLE accounts (
    account_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    INTEGER NOT NULL,
    account_name   TEXT NOT NULL,
    revenue        NUMERIC NOT NULL DEFAULT 0,
    account_status TEXT NOT NULL DEFAULT 'active',
    uuid           TEXT NOT NULL UNIQUE,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE INDEX idx_accounts_customer_id ON accounts (customer_id);

-- ---------------------------------------------------------------------------
-- users — login identity, allowlist-based access restriction.
--
-- NOTE (deviation from the spec's literal Data Shapes block, flagged in the
-- report): the Build Prompt requires a UUID column on "every Customer/
-- Account/User row", but the Data Shapes block for User does not list a
-- `uuid` column at all. Implemented the Build Prompt's explicit,
-- non-negotiable rule over the Data Shapes omission -- added `uuid` here.
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id          INTEGER,            -- NULLABLE by design (platform
                                             -- admin accounts not scoped to
                                             -- one tenant) -- explicit spec note.
    user_name            TEXT NOT NULL,
    email                TEXT NOT NULL UNIQUE,
    password_hash        TEXT NOT NULL,
    active               INTEGER NOT NULL DEFAULT 1,   -- boolean
    allowed_account_ids  TEXT,               -- JSON list; NULL = unrestricted
    allowed_customer_ids TEXT,               -- JSON list; NULL = own customer only
    expires_at           TEXT,               -- NULL = never
    is_contractor        INTEGER NOT NULL DEFAULT 0,
    uuid                 TEXT NOT NULL UNIQUE,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE INDEX idx_users_customer_id ON users (customer_id);

-- ---------------------------------------------------------------------------
-- customer_configs — one-per-customer settings container. Other modules
-- (e.g. Module 03) attach their own JSON config under columns this module
-- merely owns the table/contract for, not the contents.
--
-- AMBIGUOUS in the spec (flagged in report): "a set of JSON columns other
-- modules own the *contents* of" does not say how many columns, or their
-- names. Modeled as a single generic `config_json` blob keyed by owning
-- module, e.g. {"module_03_weights": {...}}, as the most defensible
-- additive-only reading -- new modules add a new top-level key, never a new
-- column, which is at least consistent with the "additive-only" engine rule
-- even though the spec doesn't say this at the CustomerConfig table level.
-- ---------------------------------------------------------------------------
CREATE TABLE customer_configs (
    config_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    vertical    TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

-- ---------------------------------------------------------------------------
-- customer_api_keys — programmatic/agent access, scoped and revocable
-- independent of a human user.
-- ---------------------------------------------------------------------------
CREATE TABLE customer_api_keys (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id         INTEGER NOT NULL,
    key_prefix          TEXT NOT NULL,
    key_hash            TEXT NOT NULL,
    scopes              TEXT,               -- JSON list
    allowed_account_ids TEXT,               -- JSON list; NULL = all
    expires_at          TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE INDEX idx_api_keys_key_prefix ON customer_api_keys (key_prefix);
CREATE INDEX idx_api_keys_customer_id ON customer_api_keys (customer_id);
