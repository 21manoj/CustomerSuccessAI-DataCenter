# 01 — Data Model & Schema

**Layer:** Foundation

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Establish the tenant/identity bedrock every other module builds on: who the
client's customers are, what accounts they hold, who can log in and see what.
Every other module's Dependencies section assumes this one exists and behaves
a specific way — get the multi-tenancy contract wrong here and it's wrong
everywhere, silently, for every module built on top.

## Boundary

**Owns:**
- Tenant identity: `Customer` (the root of multi-tenancy — everything else
  hangs off `customer_id`).
- `Account` — the sub-tenant unit within a customer (in this system's domain,
  a customer's individual accounts/depots/branches — whatever the client's
  vocabulary calls the thing that gets a health score).
- `User` — login identity, scoped to a customer, with an allowlist-based
  access-restriction pattern (see Engine section) rather than a role-only
  model.
- `CustomerConfig` — the one-per-customer settings container other modules
  attach their config to (e.g. Module 03's per-customer weight overrides live
  here as a JSON column, not a new top-level table).
- `CustomerApiKey` — programmatic/agent access credentials, scoped and
  revocable independent of a human user.
- The multi-tenancy contract itself: every table that holds client data
  carries a `customer_id`, and every query that crosses a trust boundary
  filters by it explicitly (see Gotcha 2).

**Explicitly does not own:**
- KPI/scoring tables (`HealthScore`, `PillarScore`, KPI value storage) —
  Module 03 (Health Scoring Engine) defines its own tables that merely
  reference `Account`/`Customer` from here.
- Causal graph tables (`ContextNode`/`ContextEdge`) — Module 04.
- Prediction/wizard state (calibration history, wizard run logs) — Module 05.
- Authentication mechanics (password hashing, session/token issuance, magic
  links) — this module defines the `User` row's *shape*, not the login flow
  built on top of it. Treat auth flow as a thin layer this module supports,
  not something to build here.

## Dependencies

None — this is the first module in dependency order. Every other module in
this library depends on this one.

### Data Shapes

```
Customer:        customer_id (PK), customer_name, email (globally unique),
                  domain (unique, nullable — used for multi-tenant email-domain
                  matching if the client wants that), vertical, uuid
                  (globally-unique external ID, separate from the integer PK
                  — see Gotcha 3), created_at, updated_at

CustomerConfig:   config_id (PK), customer_id (FK, UNIQUE — one config row per
                  customer, not a list), vertical, config_json (ONE JSON blob
                  column, namespaced by owning module, e.g. {"module_03_
                  weights": {...}, "module_05_calibration": {...}} — not one
                  physical column per module. This module owns the table, the
                  1:1-per-customer contract, and the top-level namespacing
                  convention; it does NOT own what any individual namespace's
                  contents mean — that's the owning module's config surface,
                  documented in that module's spec)

Account:          account_id (PK), customer_id (FK, NOT NULL — see Gotcha 1
                  on why this MUST be a real, enforced DB constraint, not
                  just declared in the ORM), account_name (NOT NULL),
                  revenue (NOT NULL, default 0), account_status (NOT NULL,
                  default 'active'), uuid, created_at, updated_at

User:             user_id (PK), customer_id (FK, NULLABLE — see note below),
                  user_name, email (globally unique), password_hash, active,
                  uuid, allowed_account_ids (JSON list, NULL = unrestricted),
                  allowed_customer_ids (JSON list, NULL = own customer only —
                  ONLY meaningful for cross-tenant support/test accounts, see
                  platform-admin note below), expires_at (NULL = never — set
                  for contractor/temp access), is_contractor

CustomerApiKey:   id (PK), customer_id (FK), key_prefix (indexed, for fast
                  lookup), key_hash (never store the raw key), scopes (JSON
                  list), allowed_account_ids (JSON list, NULL = all),
                  expires_at, is_active
```

Every entity table (`Customer`, `Account`, `User`) gets a `uuid` column — see
the Build Prompt's UUID rule below, which applies uniformly to all three, not
just `Account`.

`User.customer_id` is nullable by design — it allows a small number of
platform-wide/admin accounts not scoped to any single tenant. Every other
`customer_id` FK in this module is NOT NULL; don't copy the nullable pattern
without a specific reason. **Platform-admin access is fail-closed by
default**: a `User` with `customer_id = NULL` and `allowed_customer_ids =
NULL` has access to NO tenant under `has_customer_access` (the "NULL means
unrestricted" rule applies to a user's OWN tenant scope, not to a user who
has no tenant at all) — a platform admin MUST have `allowed_customer_ids`
explicitly populated (or an explicit wildcard sentinel your implementation
defines, e.g. `["*"]`) to access any tenant's data. This is intentional,
not an oversight: a principal with no home tenant getting silent
unrestricted access by default would be the far more dangerous failure
direction.

## Engine vs. Config

**Engine (build once):**
- The multi-tenancy filter contract: any function reading client data by ID
  alone (not already inside a request scoped to a known tenant) must accept
  and enforce `customer_id`, returning "not found" rather than another
  tenant's row on mismatch — never structure a read as "look up by ID, trust
  the caller."
- The allowlist-not-denylist access pattern on `User`/`CustomerApiKey`:
  `NULL` = unrestricted, a populated JSON list = restricted to exactly those
  IDs. This is a `has_account_access(account_id)` / `has_customer_access(...)`
  method, not ad-hoc `if` checks scattered per endpoint.
- UUID-alongside-integer-PK: every core entity gets both a fast internal
  integer PK for joins/FKs, and a separately-unique, prefixed external UUID
  (e.g. `saas_acct_<uuid4>`) for anything that leaves the system (API
  responses, cross-system references, exports) — never expose the raw integer
  PK as a stable external identifier (see Gotcha 4).
- Additive-only schema evolution: new client-specific or vertical-specific
  fields get added as new nullable columns (or a new JSON blob column) on the
  existing table, never by repurposing or redefining an existing column's
  meaning. `CustomerConfig`'s own comments in the origin system literally say
  "EXISTING FIELDS — DO NOT MODIFY" above a block of newer additions; that's
  the pattern, made explicit.

**Config (an FDE fills in per client):**
- What `vertical` values are valid for this client's deployment.
- Whether `domain`-based tenant matching is used at all (some clients want
  email-domain auto-association at signup; others don't).
- The specific JSON schema inside `CustomerConfig`'s vertical-specific columns
  — owned contents-wise by whichever module (03, 05, etc.) actually reads
  them, but the empty column exists here.

## Build Prompt

> Build the foundation data model for `{CLIENT_NAME}`'s deployment. Implement
> five tables — `customers`, `accounts`, `users`, `customer_configs`,
> `customer_api_keys` — matching the Data Shapes above exactly, including
> types and nullability. Two non-negotiable rules:
>
> 1. **Every foreign key to `customers.customer_id` or `accounts.account_id`
>    must be a real, DB-enforced foreign key constraint** — not just an ORM
>    relationship annotation. After creating the schema, verify with a direct
>    query against the database's constraint catalog (e.g.
>    `pg_constraint`/`information_schema.table_constraints` on Postgres) that
>    the constraint actually exists — do not trust the ORM model file as proof
>    it's enforced. See Gotcha 1: this exact gap shipped to production
>    undetected for a long time in the origin system.
>
> 2. **Write one shared access-control helper module**, not per-endpoint
>    checks. The expiry check MUST be the first thing both functions do,
>    unconditionally — an expired principal has zero access regardless of
>    what its allowlists say, never treat expiry as an independent add-on
>    check a caller might forget to also make:
>    ```
>    def _is_expired(principal) -> bool:
>        return principal.expires_at is not None and now() > principal.expires_at
>
>    def has_account_access(principal, account_id) -> bool:
>        if _is_expired(principal): return False
>        if principal.allowed_account_ids is None: return True
>        return account_id in principal.allowed_account_ids
>
>    def has_customer_access(principal, customer_id) -> bool:
>        if _is_expired(principal): return False
>        if principal.customer_id is None:  # platform-admin principal
>            allowed = principal.allowed_customer_ids or []
>            return customer_id in allowed or "*" in allowed
>        if principal.allowed_customer_ids is None:
>            return customer_id == principal.customer_id
>        return customer_id in principal.allowed_customer_ids
>    ```
>    where `principal` is a `User` or `CustomerApiKey` row (note:
>    `CustomerApiKey` has no `allowed_customer_ids` or platform-admin concept
>    — it's always scoped to exactly its own `customer_id`; only
>    `has_account_access` applies to it). Every API endpoint, agent tool, or
>    export path that takes an `account_id` or `customer_id` from outside a
>    fully-trusted internal call MUST route through these functions — never
>    re-implement this logic inline at the call site (it will eventually be
>    gotten backwards at one of the sites — see Gotcha 2). Also implement and
>    test the empty-list case explicitly: `allowed_account_ids = []` (a
>    present-but-empty list) must deny access to every account — it is NOT
>    the same as `None`, which means unrestricted. Confusing these two is a
>    silent full access-control bypass in the dangerous direction.
>
> Generate a UUID with a type-prefixed format (e.g. `f"{vertical}_acct_
> {uuid4()}"`) for every `Customer`/`Account`/`User` row at creation time, and
> store it in a dedicated unique `uuid` column alongside the integer primary
> key. Never expose the raw integer PK in any response or reference meant to
> leave the system or be shared with the client.
>
> Make every new column you add beyond this minimal schema **nullable with a
> safe default**, and never repurpose or redefine an existing column once
> another module depends on it — schema evolution here is additive-only.

## Acceptance Criteria

- Creating an `Account` row with a `customer_id` that doesn't exist in
  `customers` raises a database-level integrity error — it is not possible to
  insert an orphaned account through the schema itself (regardless of what
  application code attempts).
- A directly-queried constraint catalog listing shows a foreign-key
  constraint from `accounts.customer_id` to `customers.customer_id` — don't
  accept "the ORM model declares it" as sufficient evidence; query the actual
  database's own constraint metadata (`pg_constraint`/`information_schema` on
  Postgres, `PRAGMA foreign_key_list` on SQLite, or your engine's equivalent
  — the requirement is "ask the database," not a specific vendor command),
  on a connection that never even imports the application's ORM/model layer.
- `has_account_access(user_with_null_allowed_account_ids, ANY_ACCOUNT_ID)`
  returns `True` for every account, including ones created after the user
  was. `has_account_access(user_with_allowed_account_ids=[1,2],
  account_id=3)` returns `False`. `has_account_access(user_with_
  allowed_account_ids=[], account_id=ANY)` returns `False` for every
  account — an empty list is NOT the same as `None`; a matrix test covering
  None / empty / populated / expired is required, not just the None and
  populated cases.
- Two different `Customer` rows never receive colliding `uuid` values (unique
  constraint enforced at the DB level, not just checked in application code).
- Adding a new nullable column to `Account` does not require changing any
  existing INSERT statement elsewhere in the codebase (proves the
  additive-only pattern is actually additive, not merely intended to be).
- A `User`/`CustomerApiKey` with `expires_at` in the past is treated as having
  no access regardless of `allowed_account_ids`/`allowed_customer_ids`
  content — running the Build Prompt's own `has_account_access` code against
  an expired principal with `allowed_account_ids=None` must return `False`,
  not `True`. (This is deliberately the same case Gotcha 2 describes as a
  silent bypass — test it against your actual implementation, not just
  against the pseudocode as written, since it's easy to build the helper
  correctly but leave a stale/cached check somewhere else in the call path.)
- A platform-admin principal (`customer_id=NULL`, `allowed_customer_ids=NULL`)
  has access to NO customer via `has_customer_access` — fail-closed, not
  fail-open, for the no-home-tenant case.

## Reference Test Harness

1. **Constraint-catalog assertion** — after schema creation, a test that
   queries the database's own constraint metadata (not the ORM) and asserts
   the expected foreign keys exist. This is the single highest-value test in
   this module, because it's the one class of bug that produces zero
   application-level symptoms until, months later, a report or migration
   trips over orphaned rows no one knew existed.
2. **Access-control unit tests** — table-driven tests over the
   `has_account_access`/`has_customer_access` helpers covering: NULL
   allowlist, populated allowlist (member and non-member IDs), expired
   principal, and empty-list allowlist (which should behave as "access to
   nothing," not "unrestricted" — an empty list and `NULL` are NOT the same
   thing; get this backwards and it silently becomes a total access-control
   bypass).
3. **Cross-tenant fixture test** — create two customers with accounts under
   each, and assert that every read path in modules built on top of this one
   (start with Module 03) returns `missing`/`not_found` rather than data when
   given a real `account_id` alongside the wrong `customer_id`.

## Known Gotchas

**1. ORM-declared foreign keys are not automatically DB-enforced**
*Symptom:* Orphaned rows exist — child rows referencing a parent ID that no
longer (or never did) exist — discovered much later, usually during a data
migration, backup/restore, or an unrelated audit, with no idea how long
they've been there or how they got there.
*Root cause:* The application's ORM model file declares
`db.ForeignKey('customers.customer_id')`, which looks like a real constraint
in code review, but if the actual database table was created (or migrated)
without that constraint physically present — a common gap when tables are
created via a raw migration script rather than the ORM's own
create-from-model path — the database will silently accept inserts that
violate the "constraint," because there is no constraint, only an annotation.
*Fix:* Never trust the model file as proof. After any schema
creation/migration, directly query the database's own constraint catalog to
confirm the FK physically exists. Verified in the origin system: 414
`accounts` rows currently reference `customer_id` values with no
corresponding `customers` row, and `accounts.customer_id` has **zero**
FK constraints in the live database despite being declared in the ORM model.

**2. NULL-means-unrestricted is easy to get backwards at a call site**
*Symptom:* A user who should be restricted to a handful of accounts can see
everything; or, less dangerously but still wrong, a user who should have
unrestricted access is locked out of accounts created after their allowlist
was set.
*Root cause:* The access pattern here is inverted from what most engineers
expect on first read — `NULL` (absent) means *unrestricted*, not *no access*.
Re-implementing this check inline at each new endpoint, instead of calling one
shared helper, means every new call site is a fresh chance to get the
NULL-handling backwards, and the failure mode (a bypass) is the dangerous
direction.
*Fix:* One shared helper function, used everywhere, tested exhaustively for
the NULL/empty-list/populated-list/expired matrix. Never let a second
implementation of this logic exist anywhere in the codebase.

**3. UUID and integer PK are not interchangeable, and mixing them up is a
silent security/reliability bug**
*Symptom:* An integer account ID guessed or incremented by an external caller
returns another customer's data; or, an external reference to "the same"
account breaks after a database migration/reseed changes integer PK
assignment.
*Root cause:* Integer primary keys are sequential and predictable, and are
not stable across a reseed/restore (a `TRUNCATE ... RESTART IDENTITY`, for
example, reassigns them from 1). Exposing them externally invites both
enumeration and stale-reference bugs.
*Fix:* Every entity gets a separate, prefixed UUID column, generated once at
creation, used for anything that crosses a system boundary. The integer PK
stays purely internal — joins, FKs, nothing else.

**4. Additive-only schema discipline has to be enforced by convention, not
tooling — and it decays under pressure**
*Symptom:* A column's meaning quietly shifts between two different uses over
the life of a project (e.g. a status field that meant one thing when a
feature shipped starts encoding a second, unrelated concept later), and old
rows and new rows are no longer comparable without knowing which era they're
from.
*Root cause:* Under deadline pressure, reusing an existing nullable/loosely-
typed column feels faster than adding a new one and migrating readers.
*Fix:* Treat "add a new column, never repurpose an old one" as a hard rule for
FDEs unfamiliar with the codebase's history, specifically because they're the
least equipped to know what silently depends on a column's current meaning.
The origin system's own `CustomerConfig` model has an explicit
`DO NOT MODIFY — KEEP AS IS` comment block above its original fields for
exactly this reason — copy that pattern (a visible comment marking the
original contract) into any schema an FDE hands off to a client's own team.

## Provenance

Origin: `kpi-dashboard/backend/models.py` (`Customer`, `CustomerApiKey`,
`CustomerConfig`, `Account`, `User` classes, lines 11–227 at time of writing).
Orphaned-row and missing-FK findings verified directly against the live
`cs_pulse_datacenter` local replica database on 2026-08-07 (414 orphaned
`accounts` rows; zero FK constraints on `accounts.customer_id` confirmed via
direct `pg_constraint` query) — this is a real, currently-present condition in
the reference system, not a historical/fixed issue.

## Validation Note

Validated 2026-08-07: a fresh agent, given only this spec (forbidden from
reading `models.py` or any other reference-implementation file), built a
working schema + access-control layer from scratch for an invented vertical
("fitguild_v1," a boutique-fitness-studio SaaS), choosing raw SQL DDL over an
ORM specifically because Gotcha 1 made that the more defensible choice — a
direct, correct application of the Gotcha, unprompted. 27 tests, all passing.

**What the run found broken, and what changed:**

1. **The Build Prompt's literal `has_account_access`/`has_customer_access`
   pseudocode omitted the expiry check** that Acceptance Criteria and Gotcha 2
   both require — the same failure class as the Module 03 pilot (a
   self-contained Build Prompt that, followed literally, reproduces the exact
   bug a Gotcha exists to warn against). The agent proved this wasn't
   theoretical: running the original pseudocode verbatim against an expired
   principal with `allowed_account_ids=None` returned `True` — a real access
   bypass. **Fixed**: rewrote the Build Prompt's code block to check expiry
   first, unconditionally, in both functions, and added the empty-list case
   (`[]` ≠ `None`) directly into the code and into Acceptance Criteria (it had
   only lived in Reference Test Harness prose, which a reader who only skims
   the AC checklist could miss).
2. **`User` was missing a `uuid` column in Data Shapes** despite the Build
   Prompt requiring UUIDs on `Customer`/`Account`/`User` uniformly, and the
   Build Prompt separately said to "match Data Shapes exactly" — a second,
   independent internal contradiction, this time Data-Shapes-vs-Build-Prompt
   rather than Gotcha-vs-Build-Prompt. **Fixed**: added `uuid` to `User` in
   Data Shapes, and added a rule to `MODULE_TEMPLATE.md` that this
   cross-check applies to every section pair, not just Build-Prompt-vs-
   Gotchas.
3. **`CustomerConfig`'s JSON structure was underspecified** ("a set of JSON
   columns... doesn't own what any individual column means") to the point
   that two implementers would produce incompatible tables. **Fixed**:
   adopted the agent's own resolution as the spec's actual answer — one
   `config_json` blob, namespaced by owning module — since a shared
   foundation module having two valid-but-incompatible physical schemas
   defeats the point of it being shared.
4. **The platform-admin (`customer_id=NULL`) case was introduced in a note
   but never reconciled with the access-control pseudocode**, which the agent
   found would fail-closed by literal accident, not by design, for that case.
   **Fixed**: made the fail-closed behavior explicit and intentional in both
   the Data Shapes note and the Build Prompt's code (an admin needs an
   explicit allowlist, including an explicit wildcard sentinel option).
5. **The constraint-catalog command in Acceptance Criteria was Postgres-
   specific** (`pg_constraint`), which doesn't transfer to an FDE choosing a
   different database for a client. **Fixed**: reworded to state the
   requirement ("ask the database's own catalog, not the ORM, from a
   connection that never imports the model layer") with Postgres and SQLite
   as examples rather than a single mandated command.

**Confirms the Module 03 finding generalizes**: this is now two-for-two
modules where an isolated fresh-agent rebuild caught a real Build-Prompt-level
defect that inspection alone missed. The adversarial validation step is
carrying real weight, not just checking a box — continue it for every
remaining module rather than treating the first two catches as bad luck now
fixed.
