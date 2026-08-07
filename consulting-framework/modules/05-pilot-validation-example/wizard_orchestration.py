"""Wizard orchestration framework — pilot validation build for Module 05.

Built from `consulting-framework/modules/05-intelligence-wizards.md` ONLY.  No
reference-implementation file was read.

Scope, per the module's Boundary section:
  * run tracking (WizardRun bookkeeping)
  * the single-active-version pattern (versioned artifacts)
  * trigger governance (explicit_only vs lazy_ok, enforced not documented)
  * the wizard entry-point contract / result-shape normalisation

NOT in scope: any actual analysis algorithm.  See `stub_wizards.py`.

Storage is real SQLite with manual transaction control (`isolation_level=None`
plus explicit `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`), so the atomicity claim
in Engine bullet 2 ("as ONE atomic operation") is actually enforced by a
database rather than simulated with dicts.

DEVIATIONS FROM THE SPEC AS LITERALLY WRITTEN — each is defended in the report:

  D1. `scope` is a first-class column on VersionedArtifact.  Data Shapes does
      NOT list it, but the Build Prompt's writer requires it and Acceptance
      Criterion 6 depends on it.
  D2. The uniqueness constraint is on (customer_id, scope, version), NOT the
      Data Shapes' `UNIQUE (customer_id, version)`.  The literal constraint
      makes AC6 (two scopes, same customer) impossible to satisfy, because
      version numbering is per-(customer, scope) and both scopes start at 1.
  D3. Deactivate-then-insert, not the Build Prompt's insert-then-deactivate.
      Same atomicity, but compatible with the partial unique index on
      is_active that Data Shapes floats.  The literal ordering is transcribed in
      `write_versioned_artifact_spec_literal` so the test suite can prove it.
  D4. NULL-safe customer matching (`customer_id IS ?`), not `customer_id = ?`.
      Both WizardRun.customer_id and VersionedArtifact.customer_id are declared
      nullable; SQL equality never matches NULL, so the literal predicate leaves
      platform-scope artifacts with two active rows.
  D5. `TRIGGER_POLICY.get(wizard_id, "explicit_only")`, not
      `TRIGGER_POLICY[wizard_id]`.  Gotcha 4's Fix says explicit_only must be
      the code-level default; the Build Prompt's subscript raises KeyError.
  D6. `trigger_source` is validated (non-empty, prefixed, non-generic).  The
      Build Prompt's pseudocode contains only a COMMENT about this; AC7 and
      Gotcha 3 both require actual enforcement.
  D7. Entry points are called as `entry_point(customer_id, **kwargs)` with
      `run_id` and `orchestrator` injected, so a wizard can supply the
      `source_run_id` that `write_versioned_artifact` requires.
  D8. `error_message` is populated as its own column (Data Shapes declares it;
      the Build Prompt only stuffs `{'error': str(e)}` into `results`).
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import stub_wizards

# ---------------------------------------------------------------------------
# Wizard registry
# ---------------------------------------------------------------------------
# Per Gotcha 1: THIS dict — not an if/elif chain and not a separately maintained
# allowlist — is the single source of truth for "which wizard ids are
# reachable."  The validity check in `trigger_wizard` is membership in this
# dict and nothing else.
WIZARD_ENTRY_POINTS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "a": stub_wizards.run_wizard_a,
    "b": stub_wizards.run_wizard_b,
    "c": stub_wizards.run_wizard_c,
    "d": stub_wizards.run_wizard_d,
    "boom": stub_wizards.run_wizard_boom,
    "lazy": stub_wizards.run_wizard_lazy,
    "silent": stub_wizards.run_wizard_silent,
    "artifact": stub_wizards.run_wizard_artifact,
    # `orphan` is intentionally absent from TRIGGER_POLICY below, to prove the
    # Gotcha-4 default actually holds in code.
    "orphan": stub_wizards.run_wizard_a,
}

DEFAULT_TRIGGER_POLICY = "explicit_only"

TRIGGER_POLICY: Dict[str, str] = {
    "a": "explicit_only",
    "b": "explicit_only",
    "c": "explicit_only",
    "d": "explicit_only",
    "boom": "explicit_only",
    "silent": "explicit_only",
    "artifact": "explicit_only",
    "lazy": "lazy_ok",  # the one deliberate, reviewable opt-in
    # "orphan" deliberately omitted -> must resolve to explicit_only, not crash
}

EXPLICIT_PREFIX = "explicit_trigger:"
LAZY_PREFIX = "lazy_trigger:"

# Gotcha 3: reject values that are technically non-empty but say nothing about
# WHO asked.  The two named in the gotcha are "mcp_onboarding" and "system".
GENERIC_TRIGGER_ACTORS = {
    "system",
    "mcp_onboarding",
    "default",
    "unknown",
    "automated",
    "auto",
    "cron",
    "admin",
    "none",
    "n/a",
}

TERMINAL_STATUSES = ("completed", "failed")


class TriggerPolicyError(PermissionError):
    """Raised when a lazy trigger targets an explicit_only wizard.

    Subclasses PermissionError because AC2 names PermissionError literally.
    """


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS wizard_run (
    run_id        TEXT PRIMARY KEY,
    customer_id   INTEGER,                       -- nullable: platform-level runs
    wizard_id     TEXT    NOT NULL,
    status        TEXT    NOT NULL
                  CHECK (status IN ('queued','running','completed','failed')),
    config        TEXT,                          -- JSON: what was requested
    results       TEXT,                          -- JSON: what came back
    error_message TEXT,
    created_at    TEXT    NOT NULL,
    started_at    TEXT,
    completed_at  TEXT,
    created_by    TEXT    NOT NULL
                  CHECK (length(trim(created_by)) > 0)   -- Gotcha 3, at the DB
);

CREATE TABLE IF NOT EXISTS versioned_artifact (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER,                       -- nullable
    scope         TEXT    NOT NULL,              -- D1
    version       INTEGER NOT NULL,
    source_run_id TEXT    REFERENCES wizard_run(run_id),
    payload       TEXT    NOT NULL,
    is_active     INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL
);

-- D2: per (customer, scope) version uniqueness.  COALESCE so the platform-level
-- (customer_id IS NULL) rows are actually covered -- NULLs are distinct in a
-- plain UNIQUE index, which would silently disable the constraint there.
CREATE UNIQUE INDEX IF NOT EXISTS ux_artifact_version
    ON versioned_artifact (COALESCE(customer_id, -1), scope, version);

"""

# The "at most one active per (customer, scope)" invariant, enforced by the
# database as a backstop.  Data Shapes says a partial unique index on is_active
# "is possible in some databases" but that the write path must still be one
# transaction regardless -- this index can only CATCH a violation, it cannot
# make two commits atomic.  Kept separable so a test can build an orchestrator
# without it and observe what the write path alone does or doesn't guarantee.
SINGLE_ACTIVE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_artifact_single_active
    ON versioned_artifact (COALESCE(customer_id, -1), scope)
    WHERE is_active = 1;
"""


class WizardOrchestrator:
    """Owns the DB connection, the dispatcher, and the versioned-artifact writer."""

    def __init__(
        self, db_path: str = ":memory:", single_active_index: bool = True
    ) -> None:
        # isolation_level=None => no implicit transaction management by the
        # driver; every transaction below is opened and closed explicitly.
        self.conn = sqlite3.connect(db_path, isolation_level=None, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        if single_active_index:
            self.conn.executescript(SINGLE_ACTIVE_INDEX)
        self._lock = threading.Lock()

    def close(self) -> None:
        self.conn.close()

    # -- transaction helper -------------------------------------------------
    class _Tx:
        def __init__(self, conn: sqlite3.Connection) -> None:
            self.conn = conn

        def __enter__(self) -> sqlite3.Connection:
            self.conn.execute("BEGIN IMMEDIATE")
            return self.conn

        def __exit__(self, exc_type, exc, tb) -> bool:
            if exc_type is None:
                self.conn.execute("COMMIT")
            else:
                self.conn.execute("ROLLBACK")
            return False  # never swallow

    def transaction(self) -> "WizardOrchestrator._Tx":
        return WizardOrchestrator._Tx(self.conn)

    # ======================================================================
    # 1. Trigger dispatcher
    # ======================================================================
    @staticmethod
    def policy_for(wizard_id: str) -> str:
        """D5 / Gotcha 4: silence in the config is SAFE, never a crash and never
        auto-triggerable."""
        return TRIGGER_POLICY.get(wizard_id, DEFAULT_TRIGGER_POLICY)

    @staticmethod
    def validate_trigger_source(trigger_source: Any) -> str:
        """D6 / Gotcha 3 / AC7.

        The Build Prompt only comments that this must happen.  Requirements
        actually stated across the doc:
          - non-empty (AC7)
          - not blank/whitespace (AC7 "blank")
          - not "overly-generic" (Gotcha 3's Fix)
          - and, because the policy check keys off `startswith("lazy_trigger:")`,
            the prefix must be one of the two known ones -- otherwise a lazy
            caller that forgets the prefix is silently treated as explicit and
            the whole governance mechanism is bypassed.  The spec never states
            this last rule; see report.
        """
        if not isinstance(trigger_source, str):
            raise ValueError(
                "trigger_source is required and must be a string, got "
                f"{type(trigger_source).__name__}"
            )
        cleaned = trigger_source.strip()
        if not cleaned:
            raise ValueError("trigger_source is required and must be non-empty")
        if not (
            cleaned.startswith(EXPLICIT_PREFIX) or cleaned.startswith(LAZY_PREFIX)
        ):
            raise ValueError(
                "trigger_source must start with "
                f"'{EXPLICIT_PREFIX}' or '{LAZY_PREFIX}'; got {cleaned!r}. "
                "An unprefixed source cannot be classified by the trigger "
                "policy check and would silently be treated as explicit."
            )
        prefix, _, actor = cleaned.partition(":")
        actor = actor.strip()
        if not actor:
            raise ValueError(
                f"trigger_source {cleaned!r} names no actor -- the audit trail "
                "must be reconstructable into 'which human or which specific "
                "automated code path requested this'"
            )
        if actor.lower() in GENERIC_TRIGGER_ACTORS:
            raise ValueError(
                f"trigger_source actor {actor!r} is too generic (Gotcha 3): "
                "use a specific user or a specific dashboard view"
            )
        return cleaned

    def trigger_wizard(
        self,
        customer_id: Optional[int],
        wizard_id: str,
        trigger_source: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Guard-clause ordering matters and is the point of Gotcha 1.

        Order:
          1. reachability = membership in WIZARD_ENTRY_POINTS (nothing else)
          2. trigger_source validation
          3. trigger-policy check
          4. ONLY THEN create the WizardRun row
        AC2 requires 3 to happen strictly before 4: a rejected trigger leaves
        zero audit trail, because rejection is not the same event as failure.
        """
        # (1) Reachability -- dict membership IS the validity check.  There is
        #     deliberately no second allowlist anywhere in this file.
        if wizard_id not in WIZARD_ENTRY_POINTS:
            raise ValueError(f"Unknown wizard: {wizard_id}")

        # (2) Audit-trail quality.
        trigger_source = self.validate_trigger_source(trigger_source)

        # (3) Governance, BEFORE any row exists.
        if (
            self.policy_for(wizard_id) == "explicit_only"
            and trigger_source.startswith(LAZY_PREFIX)
        ):
            raise TriggerPolicyError(
                f"Wizard {wizard_id} is explicit-only, cannot be lazy-triggered"
            )

        # (4) Bookkeeping.
        run_id = self.create_wizard_run(
            customer_id, wizard_id, trigger_source, config
        )
        self._mark_running(run_id)

        try:
            entry_point = WIZARD_ENTRY_POINTS[wizard_id]
            kwargs = dict(config or {})
            # D7: give the wizard what it needs to route artifact writes back
            # through the one atomic writer.
            kwargs.setdefault("run_id", run_id)
            kwargs.setdefault("orchestrator", self)
            result = entry_point(customer_id, **kwargs)
            succeeded = self.interpret_result(result)
            self.complete_wizard_run(run_id, succeeded, result)
        except Exception as exc:  # noqa: BLE001 -- deliberate: AC4
            self.complete_wizard_run(
                run_id, False, {"error": str(exc)}, error_message=str(exc)
            )
            raise
        return self.get_run(run_id)

    # -- result-shape normalisation (Gotcha 2 / AC3) ------------------------
    @staticmethod
    def interpret_result(result: Any) -> bool:
        """Handle BOTH conventions in ONE place, with zero wizard-specific
        branching.  Transcribed from the Build Prompt, with a non-dict guard
        added (the Build Prompt's `'return_code' in result` raises TypeError on
        a wizard that returns None)."""
        if not isinstance(result, dict):
            return False
        if "return_code" in result:
            return result.get("return_code") == 0
        return result.get("status") == "completed"

    # -- WizardRun bookkeeping ---------------------------------------------
    # NOTE: the Build Prompt calls create_wizard_run / complete_wizard_run /
    # run.to_dict() but never defines any of them.  Everything below is
    # reconstructed from Data Shapes + the Engine bullet.
    def create_wizard_run(
        self,
        customer_id: Optional[int],
        wizard_id: str,
        trigger_source: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        run_id = uuid.uuid4().hex
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO wizard_run
                   (run_id, customer_id, wizard_id, status, config, created_at,
                    created_by)
                   VALUES (?, ?, ?, 'queued', ?, ?, ?)""",
                (
                    run_id,
                    customer_id,
                    wizard_id,
                    json.dumps(config or {}),
                    _utcnow(),
                    trigger_source,
                ),
            )
        return run_id

    def _mark_running(self, run_id: str) -> None:
        """The status enum includes 'running' but the spec never says who sets
        it.  Set here, so the enum value is reachable and so a hung wizard is
        distinguishable from a never-started one."""
        with self.transaction() as conn:
            conn.execute(
                "UPDATE wizard_run SET status='running', started_at=? "
                "WHERE run_id=?",
                (_utcnow(), run_id),
            )

    def complete_wizard_run(
        self,
        run_id: str,
        succeeded: bool,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if error_message is None and isinstance(result, dict):
            if not succeeded:
                error_message = str(
                    result.get("error") or result.get("reason") or "wizard reported failure"
                )
        with self.transaction() as conn:
            conn.execute(
                """UPDATE wizard_run
                      SET status = ?, results = ?, error_message = ?,
                          completed_at = ?
                    WHERE run_id = ?""",
                (
                    "completed" if succeeded else "failed",
                    json.dumps(result if isinstance(result, dict) else {"raw": repr(result)}),
                    error_message,
                    _utcnow(),
                    run_id,
                ),
            )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM wizard_run WHERE run_id = ?", (run_id,)
        ).fetchone()
        return self._run_to_dict(row)

    def list_runs(self, wizard_id: Optional[str] = None):
        if wizard_id is None:
            rows = self.conn.execute(
                "SELECT * FROM wizard_run ORDER BY created_at, rowid"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM wizard_run WHERE wizard_id = ? ORDER BY created_at, rowid",
                (wizard_id,),
            ).fetchall()
        return [self._run_to_dict(r) for r in rows]

    @staticmethod
    def _run_to_dict(row) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        d = dict(row)
        for key in ("config", "results"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (TypeError, ValueError):
                    pass
        return d

    # ======================================================================
    # 2. Versioned-artifact writer
    # ======================================================================
    def next_version_number(
        self, conn: sqlite3.Connection, customer_id: Optional[int], scope: str
    ) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM versioned_artifact "
            "WHERE customer_id IS ? AND scope = ?",  # D4: NULL-safe
            (customer_id, scope),
        ).fetchone()
        return int(row["v"]) + 1

    def write_versioned_artifact(
        self,
        customer_id: Optional[int],
        scope: str,
        payload: Dict[str, Any],
        source_run_id: Optional[str],
        _fault_hook: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """Append a new version and deactivate the previous one, atomically.

        `scope` disambiguates artifact TYPES for the same customer, so activating
        a Wizard D calibration never deactivates an unrelated Wizard B
        pattern-learning row.

        `_fault_hook` exists purely for Reference Test Harness item 3: it fires
        BETWEEN the two halves of the transaction so a test can crash the write
        mid-flight and assert the previous row is still active afterwards.
        """
        if not scope or not str(scope).strip():
            raise ValueError("scope is required -- without it, artifact types collide")

        with self._lock, self.transaction() as conn:
            version = self.next_version_number(conn, customer_id, scope)

            # D3: deactivate FIRST, then insert the new active row.  Same single
            # transaction, same guarantee, but it never transiently violates the
            # one-active-row unique index the way insert-then-deactivate does.
            conn.execute(
                "UPDATE versioned_artifact SET is_active = 0 "
                "WHERE customer_id IS ? AND scope = ? AND is_active = 1",
                (customer_id, scope),
            )

            if _fault_hook is not None:
                _fault_hook()

            cur = conn.execute(
                """INSERT INTO versioned_artifact
                   (customer_id, scope, version, source_run_id, payload,
                    is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (
                    customer_id,
                    scope,
                    version,
                    source_run_id,
                    json.dumps(payload),
                    _utcnow(),
                ),
            )
            new_id = cur.lastrowid

        return self.get_artifact(new_id)

    # -- literal-spec transcription, retained only to prove defects ---------
    def write_versioned_artifact_spec_literal(
        self,
        customer_id: Optional[int],
        scope: str,
        payload: Dict[str, Any],
        source_run_id: Optional[str],
    ) -> Dict[str, Any]:
        """The Build Prompt's writer transcribed as literally as SQLite allows.

        Two literal-fidelity details are preserved on purpose:
          * INSERT (is_active=1) happens BEFORE the deactivation UPDATE
          * the deactivation predicate uses `customer_id = ?`, i.e. SQL equality,
            matching `VersionedArtifact.customer_id == customer_id`
        Used ONLY by the defect-proof tests.
        """
        with self._lock, self.transaction() as conn:
            version = self.next_version_number(conn, customer_id, scope)
            cur = conn.execute(
                """INSERT INTO versioned_artifact
                   (customer_id, scope, version, source_run_id, payload,
                    is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (
                    customer_id,
                    scope,
                    version,
                    source_run_id,
                    json.dumps(payload),
                    _utcnow(),
                ),
            )
            new_id = cur.lastrowid
            conn.execute(
                "UPDATE versioned_artifact SET is_active = 0 "
                "WHERE customer_id = ? AND scope = ? AND id != ?",
                (customer_id, scope, new_id),
            )
        return self.get_artifact(new_id)

    # -- reads --------------------------------------------------------------
    def get_artifact(self, artifact_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM versioned_artifact WHERE id = ?", (artifact_id,)
        ).fetchone()
        return self._artifact_to_dict(row)

    def get_active_artifact(
        self, customer_id: Optional[int], scope: str
    ) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM versioned_artifact "
            "WHERE customer_id IS ? AND scope = ? AND is_active = 1",
            (customer_id, scope),
        ).fetchone()
        return self._artifact_to_dict(row)

    def active_artifacts(self, customer_id: Optional[int], scope: str):
        rows = self.conn.execute(
            "SELECT * FROM versioned_artifact "
            "WHERE customer_id IS ? AND scope = ? AND is_active = 1 ORDER BY version",
            (customer_id, scope),
        ).fetchall()
        return [self._artifact_to_dict(r) for r in rows]

    def all_artifacts(self, customer_id: Optional[int], scope: str):
        rows = self.conn.execute(
            "SELECT * FROM versioned_artifact "
            "WHERE customer_id IS ? AND scope = ? ORDER BY version",
            (customer_id, scope),
        ).fetchall()
        return [self._artifact_to_dict(r) for r in rows]

    @staticmethod
    def _artifact_to_dict(row) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        d = dict(row)
        d["is_active"] = bool(d["is_active"])
        if d.get("payload"):
            try:
                d["payload"] = json.loads(d["payload"])
            except (TypeError, ValueError):
                pass
        return d
