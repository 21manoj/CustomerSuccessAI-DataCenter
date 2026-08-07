"""
Pilot validation rebuild of Module 09 — Ingestion & Onboarding Pipeline.

Standalone, stdlib-only (sqlite3), no dependency on kpi-dashboard/backend.

This file has TWO clearly-separated halves:

  PART A — SPEC-LITERAL (DEFECTIVE).  The Build Prompt's pseudocode transcribed
           as literally as it can be made runnable, plus the one "natural"
           implementation of each helper the Build Prompt calls but never
           defines.  These exist ONLY so test_ingestion.py can execute the
           spec's own code and demonstrate the failures.  Do not ship.

  PART B — CORRECTED.  The implementation an FDE should actually ship, with
           every defect found in PART A repaired.  Each repair carries a
           `FIX:` comment naming the defect.

Python 3.9 compatible (the spec's `str | None` / `tuple[bool, str]` annotations
require `from __future__ import annotations` to even import here — noted in the
report as a portability nit).
"""

from __future__ import annotations

import os
import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from time import monotonic
from typing import Callable, Optional


# =============================================================================
# Shared config surface (Module 09 "Config" — an FDE fills these in per client)
# =============================================================================

@dataclass
class Rule:
    """The Build Prompt reads rule.required / rule.enum / rule.cast but never
    defines the rule object.  This is the minimal natural implementation."""
    required: bool = False
    enum: Optional[set] = None
    cast: Optional[Callable] = None


def parse_iso_date(v):
    """Cast used for date columns.  Raises ValueError on bad input."""
    return datetime.strptime(str(v), "%Y-%m-%d").date()


FILE_SCHEMAS = {
    "kpi_measurements": {
        "account_ref": Rule(required=True),
        "kpi_code": Rule(required=True, enum={"P1-KPI1", "P1-KPI2", "P2-KPI1"}),
        "measured_at": Rule(required=True, cast=parse_iso_date),
        "value": Rule(required=True, cast=float),
        "note": Rule(),  # optional / nullable
    },
    "signals": {
        "customer_id": Rule(required=True, cast=int),
        "signal_id": Rule(required=True),
        "channel": Rule(required=True, enum={"email", "slack", "ticket"}),
        "content": Rule(),  # optional / nullable
    },
    # A file type whose natural key includes an OPTIONAL column.  Realistic:
    # some clients ship touchpoints without a timestamp.  Used to prove the
    # NULL-in-natural-key defect.
    "touchpoints": {
        "account_ref": Rule(required=True),
        "touchpoint_id": Rule(required=True),
        "occurred_at": Rule(cast=parse_iso_date),  # OPTIONAL -> may be absent
        "summary": Rule(),
    },
}

NATURAL_KEYS = {  # Config, per file type — verbatim from Build Prompt piece 3
    "kpi_measurements": ("account_ref", "kpi_code", "measured_at"),
    "signals": ("customer_id", "signal_id"),
    "touchpoints": ("account_ref", "touchpoint_id", "occurred_at"),
}

# Columns actually stored per file type (the spec supplies no DDL at all).
FILE_COLUMNS = {
    "kpi_measurements": ("account_ref", "kpi_code", "measured_at", "value", "note"),
    "signals": ("customer_id", "signal_id", "channel", "content"),
    "touchpoints": ("account_ref", "touchpoint_id", "occurred_at", "summary"),
}

# Referential sanity (Boundary "Owns" bullet 1) — which column, if any, must
# resolve to an existing Account for this customer.
REFERENTIAL_KEYS = {
    "kpi_measurements": "account_ref",
    "touchpoints": "account_ref",
    "signals": None,
}


# =============================================================================
# Schema.  The spec contains NO DDL anywhere; this is invented to make
# `upsert ... ON CONFLICT (natural key)` even expressible.
# =============================================================================

DDL = """
CREATE TABLE IF NOT EXISTS ingestion_state (
    customer_id       INTEGER PRIMARY KEY,
    last_ingested_at  TEXT,     -- nullable
    last_processed_at TEXT      -- nullable (PART B only)
);
CREATE TABLE IF NOT EXISTS accounts (
    customer_id INTEGER NOT NULL,
    account_ref TEXT NOT NULL,
    PRIMARY KEY (customer_id, account_ref)
);
CREATE TABLE IF NOT EXISTS kpi_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    account_ref TEXT, kpi_code TEXT, measured_at TEXT,
    value TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    signal_id TEXT, channel TEXT, content TEXT
);
CREATE TABLE IF NOT EXISTS touchpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    account_ref TEXT, touchpoint_id TEXT, occurred_at TEXT, summary TEXT
);
"""

# Unique indexes over the natural keys.  PART A (spec-literal) never creates
# these, because the spec never mentions them; PART B does.
NATURAL_KEY_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_kpi ON kpi_measurements
    (customer_id, account_ref, kpi_code, measured_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_sig ON signals
    (customer_id, signal_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tp ON touchpoints
    (customer_id, account_ref, touchpoint_id, occurred_at);
"""


def open_db(path=":memory:", with_natural_key_indexes=True):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    if with_natural_key_indexes:
        con.executescript(NATURAL_KEY_INDEXES)
    con.commit()
    return con


def count_rows(con, table, customer_id=None):
    if customer_id is None:
        return con.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
    return con.execute(
        "SELECT COUNT(*) FROM %s WHERE customer_id=?" % table, (customer_id,)
    ).fetchone()[0]


# =============================================================================
# Data shapes (identical for both halves — these come from Data Shapes)
# =============================================================================

@dataclass
class UploadResult:
    file_type: str
    rows_accepted: int
    rows_rejected: int
    errors: list
    stored_path: Optional[str]
    validated_only: bool


@dataclass
class StageResult:
    name: str
    status: str          # 'completed' | 'skipped' | 'failed'
    detail: str
    error: Optional[str]


@dataclass
class PipelineResult:
    customer_id: int
    mode: str            # 'auto' | 'full_recalc'
    status: str          # 'success' | 'partial' | 'failed'
    stages: list
    timings: dict
    total: float


@dataclass
class Stage:
    name: str
    fn: Callable[[int], object]
    critical: bool = False


# =============================================================================
# PART A — SPEC-LITERAL (DEFECTIVE).  For proof tests only.
# =============================================================================

def as_utc(dt):
    """Verbatim from Build Prompt piece 2 (this one is correct)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def validate_row(row, schema, row_number) -> list:
    """Verbatim from Build Prompt piece 1."""
    errs = []
    for col, rule in schema.items():
        if rule.required and row.get(col) in (None, ""):
            errs.append({"row_number": row_number, "column": col,
                         "message": "required"})
            continue
        v = row.get(col)
        if v in (None, ""):
            continue                       # optional + absent is fine
        if rule.enum and v not in rule.enum:
            errs.append({"row_number": row_number, "column": col,
                         "message": "not in %s" % sorted(rule.enum)})
        if rule.cast:
            try:
                rule.cast(v)
            except (ValueError, TypeError):
                errs.append({"row_number": row_number, "column": col,
                             "message": "cannot cast to %s" % rule.cast.__name__})
    return errs


def _parse_ts(s):
    """SQLite gives back a string; the spec's `as_utc` docstring says naive
    values from the DB are UTC by convention.  Values stored WITHOUT an offset
    come back NAIVE, so `as_utc` is load-bearing and testable."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(s)


class SpecLiteral:
    """The Build Prompt's four pieces, transcribed.  `db.session` is replaced
    by a sqlite connection; every helper the prompt calls but does not define
    is filled in the single most natural way, and the choice is flagged."""

    def __init__(self, con, stages=None, upsert_impl="bare_insert"):
        self.con = con
        self.STAGES = stages if stages is not None else []
        # The Build Prompt calls `upsert(...)` and defines it only in a COMMENT
        # ("INSERT ... ON CONFLICT (natural key) DO UPDATE").  With no DDL and
        # no unique index anywhere in the spec, ON CONFLICT is not expressible,
        # so the two natural fallbacks are:
        #   "bare_insert"        -> the comment's first named anti-pattern
        #   "select_then_insert" -> the comment's second named anti-pattern
        self.upsert_impl = upsert_impl

    # ---- helpers the Build Prompt calls but never defines --------------
    def get_ingestion_state(self, customer_id):
        return self.con.execute(
            "SELECT * FROM ingestion_state WHERE customer_id=?", (customer_id,)
        ).fetchone()

    def get_or_create_ingestion_state(self, customer_id):
        self.con.execute(
            "INSERT OR IGNORE INTO ingestion_state (customer_id) VALUES (?)",
            (customer_id,))
        return self.get_ingestion_state(customer_id)

    def upsert(self, file_type, customer_id, key, row):
        cols = FILE_COLUMNS[file_type]
        vals = [customer_id] + [row.get(c) for c in cols]
        if self.upsert_impl == "select_then_insert":
            key_cols = NATURAL_KEYS[file_type]
            where = " AND ".join("%s IS ?" % c for c in key_cols)
            hit = self.con.execute(
                "SELECT id FROM %s WHERE customer_id=? AND %s" % (file_type, where),
                [customer_id] + list(key)).fetchone()
            if hit:
                return
        self.con.execute(
            "INSERT INTO %s (customer_id,%s) VALUES (%s)"
            % (file_type, ",".join(cols), ",".join(["?"] * (len(cols) + 1))),
            vals)

    # ---- piece 2 -------------------------------------------------------
    def touch_last_ingested_at(self, customer_id):
        self.get_or_create_ingestion_state(customer_id)
        self.con.execute(
            "UPDATE ingestion_state SET last_ingested_at=? WHERE customer_id=?",
            (datetime.now(timezone.utc).isoformat(), customer_id))
        self.con.commit()

    def has_new_data(self, customer_id, source_files, mode):
        if mode == "full_recalc":
            return True, "full_recalc_requested"
        state = self.get_ingestion_state(customer_id)
        if state is None or state["last_ingested_at"] is None:
            return True, "never_ingested"
        last = as_utc(_parse_ts(state["last_ingested_at"]))
        for f in source_files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime > last:
                return True, "new_data:%s" % f.name
        return False, "no_new_data"

    # ---- piece 3 -------------------------------------------------------
    def persist(self, customer_id, file_type, rows):
        key_cols = NATURAL_KEYS[file_type]
        for row in rows:
            key = tuple(row[c] for c in key_cols)   # <- row[c], not row.get(c)
            self.upsert(file_type, customer_id, key, row)
        self.con.commit()
        # NOTE: no `return` statement anywhere in the Build Prompt's persist().

    # ---- piece 1 -------------------------------------------------------
    def upload(self, customer_id, file_type, rows, validate_only=False):
        schema = FILE_SCHEMAS[file_type]
        accepted, errors = [], []
        for i, row in enumerate(rows, start=1):
            row_errors = validate_row(row, schema, row_number=i)
            (errors.extend(row_errors) if row_errors else accepted.append(row))
        if validate_only:
            return UploadResult(file_type, len(accepted), len(errors),
                                errors, None, True)
        path = self.persist(customer_id, file_type, accepted)
        self.touch_last_ingested_at(customer_id)
        return UploadResult(file_type, len(accepted), len(errors), errors,
                            path, False)

    # ---- piece 4 -------------------------------------------------------
    def process_data(self, customer_id, source_files, mode="auto"):
        fresh, reason = self.has_new_data(customer_id, source_files, mode)
        if not fresh:
            return PipelineResult(
                customer_id, mode, "success",
                stages=[StageResult("freshness_check", "skipped", reason, None)],
                timings={}, total=0.0)
        results, timings = [], {}
        for stage in self.STAGES:
            t0 = monotonic()
            try:
                detail = stage.fn(customer_id)
                results.append(StageResult(stage.name, "completed", str(detail), None))
            except Exception as e:
                results.append(StageResult(stage.name, "failed", "", str(e)))
                if stage.critical:
                    timings[stage.name] = monotonic() - t0
                    return PipelineResult(customer_id, mode, "failed", results,
                                          timings, sum(timings.values()))
            timings[stage.name] = monotonic() - t0
        status = "partial" if any(r.status == "failed" for r in results) else "success"
        return PipelineResult(customer_id, mode, status, results, timings,
                              sum(timings.values()))


# --- naive-local freshness check: the exact live bug of Gotcha 1 -------------

def naive_local_has_new_data(last_ingested_at_naive_utc, mtime_epoch, host_offset):
    """Simulates the PRE-FIX reference implementation on a host whose local
    zone is `host_offset`:

        datetime.fromtimestamp(os.path.getmtime(f))   # LOCAL wall clock, naive
        > last_ts                                      # naive, stored as UTC

    `host_offset` is a timedelta; we reproduce what `fromtimestamp` (no tz)
    would return on such a host WITHOUT touching the test machine's own zone.
    """
    local_naive = (datetime.fromtimestamp(mtime_epoch, tz=timezone.utc)
                   + host_offset).replace(tzinfo=None)
    return local_naive > last_ingested_at_naive_utc


def utc_has_new_data(last_ingested_at, mtime_epoch):
    """The FIXED comparison from Build Prompt piece 2 / Gotcha 1's Fix."""
    mtime = datetime.fromtimestamp(mtime_epoch, tz=timezone.utc)
    return mtime > as_utc(last_ingested_at)


# =============================================================================
# PART B — CORRECTED IMPLEMENTATION (this is the shippable one)
# =============================================================================

@dataclass
class Skip:
    """FIX (Engine bullet 4 / Gotcha 4 / Data Shapes 'feature_disabled'):
    the Build Prompt gives a stage NO way to skip — its loop can only emit
    'completed' or 'failed'.  A stage fn (or its gate) returns Skip(reason)."""
    reason: str


@dataclass
class StageSpec:
    name: str
    fn: Callable[[int], object]
    critical: bool = False
    enabled: Optional[Callable[[int], object]] = None   # -> True | Skip(reason)


@dataclass
class IngestionConfig:
    file_schemas: dict = field(default_factory=lambda: FILE_SCHEMAS)
    natural_keys: dict = field(default_factory=lambda: NATURAL_KEYS)
    file_columns: dict = field(default_factory=lambda: FILE_COLUMNS)
    referential_keys: dict = field(default_factory=lambda: REFERENTIAL_KEYS)
    create_missing_accounts: bool = True
    stages: list = field(default_factory=list)


NULL_SENTINEL = "\x00NULL"


class Ingestion:
    """Corrected Module 09 implementation."""

    def __init__(self, con, config: "IngestionConfig" = None, storage_dir=None):
        self.con = con
        self.config = config or IngestionConfig()
        self.storage_dir = storage_dir

    # ---------------- state -------------------------------------------
    def get_ingestion_state(self, customer_id):
        return self.con.execute(
            "SELECT * FROM ingestion_state WHERE customer_id=?",
            (customer_id,)).fetchone()

    def get_or_create_ingestion_state(self, customer_id):
        self.con.execute(
            "INSERT OR IGNORE INTO ingestion_state (customer_id) VALUES (?)",
            (customer_id,))
        self.con.commit()
        return self.get_ingestion_state(customer_id)

    def touch_last_ingested_at(self, customer_id, when=None):
        self.get_or_create_ingestion_state(customer_id)
        ts = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.con.execute(
            "UPDATE ingestion_state SET last_ingested_at=? WHERE customer_id=?",
            (ts.isoformat(), customer_id))
        self.con.commit()

    def touch_last_processed_at(self, customer_id, when=None):
        """FIX (defect D2): the Build Prompt has ONE timestamp doing two jobs.
        `last_ingested_at` is moved by upload(); `has_new_data` then compares
        source-file mtimes against it — but upload always runs AFTER the files
        were written, so the mark is always ahead of every mtime and the first
        real pipeline run after an upload reports success having processed
        nothing (the module's own stated worst outcome).  Freshness must be
        measured against when we last PROCESSED, a separate mark."""
        self.get_or_create_ingestion_state(customer_id)
        ts = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.con.execute(
            "UPDATE ingestion_state SET last_processed_at=? WHERE customer_id=?",
            (ts.isoformat(), customer_id))
        self.con.commit()

    # ---------------- accounts / referential sanity --------------------
    def account_exists(self, customer_id, account_ref):
        return self.con.execute(
            "SELECT 1 FROM accounts WHERE customer_id=? AND account_ref=?",
            (customer_id, account_ref)).fetchone() is not None

    def resolve_or_create_account(self, customer_id, account_ref):
        """FIX (defect D7): Boundary 'Owns' names referential sanity and
        Dependencies says accounts are 'resolved or created during ingestion'.
        Neither appears anywhere in the Build Prompt."""
        self.con.execute(
            "INSERT OR IGNORE INTO accounts (customer_id, account_ref) VALUES (?,?)",
            (customer_id, account_ref))
        self.con.commit()

    def validate_referential(self, customer_id, file_type, row, row_number):
        col = self.config.referential_keys.get(file_type)
        if not col:
            return []
        ref = row.get(col)
        if ref in (None, ""):
            return []      # NULL case: required-ness is the schema's job
        if self.account_exists(customer_id, ref):
            return []
        if self.config.create_missing_accounts:
            return []      # created at persist time, never during a dry-run
        return [{"row_number": row_number, "column": col,
                 "message": "unknown_account"}]

    # ---------------- validation + upload ------------------------------
    def upload(self, customer_id, file_type, rows, validate_only=False) -> "UploadResult":
        schema = self.config.file_schemas[file_type]
        accepted, errors, rejected_rows = [], [], 0
        for i, row in enumerate(rows, start=1):
            row_errors = validate_row(row, schema, row_number=i)
            row_errors = row_errors + self.validate_referential(
                customer_id, file_type, row, i)
            # FIX (defect D1): rows_rejected must count ROWS, not error
            # entries.  The Build Prompt returns len(errors), so one row with
            # three bad columns reports rows_rejected=3 for a 1-row file and
            # rows_accepted + rows_rejected != len(rows).
            if row_errors:
                errors.extend(row_errors)
                rejected_rows += 1
            else:
                accepted.append(row)
        if validate_only:
            # dry-run persists nothing, creates no accounts, moves no clock
            return UploadResult(file_type, len(accepted), rejected_rows,
                                errors, None, True)
        path = self.persist(customer_id, file_type, accepted)
        self.touch_last_ingested_at(customer_id)
        return UploadResult(file_type, len(accepted), rejected_rows, errors,
                            path, False)

    # ---------------- persist / idempotency ----------------------------
    def natural_key(self, file_type, row):
        """FIX (defect D5): the Build Prompt uses `row[c]`, which raises
        KeyError when a natural-key column is OPTIONAL and absent — mid-loop,
        after earlier rows were already written and before
        touch_last_ingested_at ran.  Use .get() and normalize NULL to a
        sentinel so SQL's 'every NULL is distinct' rule cannot defeat the
        unique index."""
        key = []
        for c in self.config.natural_keys[file_type]:
            v = row.get(c)
            key.append(NULL_SENTINEL if v in (None, "") else v)
        return tuple(key)

    def persist(self, customer_id, file_type, rows) -> Optional[str]:
        key_cols = self.config.natural_keys[file_type]
        cols = self.config.file_columns[file_type]
        ref_col = self.config.referential_keys.get(file_type)
        seen = set()
        deduped = []
        for row in rows:
            key = self.natural_key(file_type, row)
            if key in seen:
                continue          # intra-file dedup (last-write-wins upsert
                                  # would also work; skipping keeps it simple)
            seen.add(key)
            deduped.append(row)
            if ref_col and row.get(ref_col) not in (None, "") \
                    and self.config.create_missing_accounts:
                self.resolve_or_create_account(customer_id, row[ref_col])
            self.upsert(file_type, customer_id, key_cols, cols, row, key)
        self.con.commit()
        # FIX (defect D3): the Build Prompt's persist() has no return, so
        # `path = persist(...)` binds None and UploadResult.stored_path — a
        # field Data Shapes declares — is permanently NULL on real uploads.
        return self.store_raw(customer_id, file_type, deduped)

    def store_raw(self, customer_id, file_type, rows) -> Optional[str]:
        if not self.storage_dir:
            return None           # NULL case: storage not configured
        d = os.path.join(self.storage_dir, str(customer_id))
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "%s.json" % file_type)
        with open(p, "w") as fh:
            json.dump(rows, fh, default=str)
        return p

    def upsert(self, file_type, customer_id, key_cols, cols, row, key):
        """FIX (defect D4): the Build Prompt calls an undefined `upsert` and
        specifies it only in a comment ('ON CONFLICT (natural key) DO UPDATE'),
        while supplying no DDL and no unique index — so ON CONFLICT is not
        expressible and the natural fallbacks are the comment's own two named
        anti-patterns.  Here the index exists (NATURAL_KEY_INDEXES) and this
        is a real single-statement upsert.

        `key` is the already-normalized natural key from natural_key(); the
        NULL->sentinel mapping lives in exactly one place so the in-memory
        dedup and the on-disk unique index can never disagree."""
        keyed = dict(zip(key_cols, key))
        norm = {}
        for c in cols:
            norm[c] = keyed[c] if c in keyed else row.get(c)
        # AMBIGUITY (defect D11): NATURAL_KEYS uses two different conventions —
        # ("account_ref","kpi_code","measured_at") is implicitly tenant-scoped,
        # while ("customer_id","signal_id") names customer_id explicitly, even
        # though persist()/upsert() already receive customer_id as a separate
        # parameter.  The spec never says whether the tenant column is added to
        # the key or expected to be in it.  We scope every key by tenant and
        # de-duplicate, so both conventions land on the same behaviour.
        norm["customer_id"] = customer_id
        all_cols, seen_c = [], set()
        for c in ["customer_id"] + list(cols):
            if c not in seen_c:
                seen_c.add(c)
                all_cols.append(c)
        vals = [norm[c] for c in all_cols]
        updates = [c for c in all_cols
                   if c not in key_cols and c != "customer_id"]
        conflict_cols, seen_k = [], set()
        for c in ["customer_id"] + list(key_cols):
            if c not in seen_k:
                seen_k.add(c)
                conflict_cols.append(c)
        conflict = ", ".join(conflict_cols)
        set_clause = ", ".join("%s=excluded.%s" % (c, c) for c in updates) \
            or "customer_id=excluded.customer_id"
        sql = "INSERT INTO %s (%s) VALUES (%s) ON CONFLICT(%s) DO UPDATE SET %s" % (
            file_type, ",".join(all_cols), ",".join(["?"] * len(all_cols)),
            conflict, set_clause)
        self.con.execute(sql, vals)

    # ---------------- freshness ----------------------------------------
    def has_new_data(self, customer_id, source_files=(), mode="auto"):
        if mode == "full_recalc":
            return True, "full_recalc_requested"
        state = self.get_ingestion_state(customer_id)
        if state is None or state["last_ingested_at"] is None:
            return True, "never_ingested"
        if state["last_processed_at"] is None:
            return True, "never_processed"
        last = as_utc(_parse_ts(state["last_processed_at"]))
        for f in source_files:
            mtime = datetime.fromtimestamp(os.stat(str(f)).st_mtime,
                                           tz=timezone.utc)
            if mtime > last:
                return True, "new_data:%s" % os.path.basename(str(f))
        # FIX (defect D9): Boundary says the entry point is source-agnostic
        # ('CSV or API payload'), but the Build Prompt's has_new_data only ever
        # looks at source_files — an API-payload tenant has zero files and is
        # therefore permanently 'no_new_data'.
        ingested = as_utc(_parse_ts(state["last_ingested_at"]))
        if ingested > last:
            return True, "new_upload"
        return False, "no_new_data"

    # ---------------- orchestration ------------------------------------
    def process_data(self, customer_id, source_files=(), mode="auto",
                     stages=None) -> "PipelineResult":
        # FIX (defect D8): the Build Prompt iterates a module-level global
        # STAGES, so the AC 'a stage list containing only some of the optional
        # stages runs cleanly' can only be tested by monkeypatching a global.
        # The stage list is Config; it must be injectable.
        stages = stages if stages is not None else self.config.stages
        fresh, reason = self.has_new_data(customer_id, source_files, mode)
        if not fresh:
            return PipelineResult(
                customer_id, mode, "success",
                stages=[self._skip("freshness_check", reason)],
                timings={}, total=0.0)
        # FIX (defect D10): the AC requires mode='full_recalc' to re-run "with
        # reason 'full_recalc_requested'", but the Build Prompt discards
        # `reason` on the fresh path and PipelineResult has no field for it —
        # the reason is observable ONLY when the run is skipped.  Record it as
        # a completed freshness_check stage so every run carries its reason.
        results = [StageResult("freshness_check", "completed", reason, None)]
        timings = {"freshness_check": 0.0}
        aborted = False
        for stage in stages:
            t0 = monotonic()
            outcome = None
            try:
                gate = stage.enabled(customer_id) if stage.enabled else True
                outcome = gate if isinstance(gate, Skip) else stage.fn(customer_id)
            except Exception as e:
                results.append(StageResult(stage.name, "failed", "",
                                           "%s: %s" % (type(e).__name__, e)))
                if stage.critical:
                    timings[stage.name] = monotonic() - t0
                    aborted = True
                    break
                timings[stage.name] = monotonic() - t0
                continue
            # NOTE: building the StageResult happens OUTSIDE the try.  The
            # Build Prompt wraps result construction in the same
            # `except Exception` that isolates the stage, so the orchestrator's
            # own bugs are indistinguishable from a stage failure — and the
            # empty-skip-reason guard below would be silently swallowed.
            if isinstance(outcome, Skip):
                results.append(self._skip(stage.name, outcome.reason))
            else:
                results.append(StageResult(stage.name, "completed",
                                           str(outcome), None))
            timings[stage.name] = monotonic() - t0
        if aborted:
            return PipelineResult(customer_id, mode, "failed", results,
                                  timings, sum(timings.values()))
        status = "partial" if any(r.status == "failed" for r in results) \
            else "success"
        # Only a run that got through every stage may move the processed mark;
        # a 'partial' run still processed the fresh data it could.
        self.touch_last_processed_at(customer_id)
        return PipelineResult(customer_id, mode, status, results, timings,
                              sum(timings.values()))

    @staticmethod
    def _skip(name, reason):
        # FIX (Gotcha 4): a skip with no reason is indistinguishable from a
        # bug.  Make it structurally impossible rather than a convention.
        if not reason or not str(reason).strip():
            raise ValueError("stage %r skipped with no reason" % name)
        return StageResult(name, "skipped", str(reason), None)
