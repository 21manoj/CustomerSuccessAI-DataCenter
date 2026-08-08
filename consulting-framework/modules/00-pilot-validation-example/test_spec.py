"""
Adversarial validation tests for Module 00 (Integration & Bootstrap).

Acceptance-criteria tests exercise the spec's literal logic where it is sound.
`test_defect_*` tests PROVE a defect by executing the spec's literal pseudocode
and demonstrating the failure, then show the corrected version passing alongside.
"""
import os
import pytest
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, ForeignKey, UniqueConstraint,
    create_engine, text,
)

import impl
from impl import (
    ensure_schema, check_constraint_drift, check_constraint_drift_FIXED,
    SchemaDriftError, _DbShim,
    resolve_weights, resolve_vertical, data_path, classify, normalize_vertical,
    is_enabled, Toggle, TOGGLES, ToggleCfg,
    process_data, ProcessResult, run_stage, STAGE_ORDER, OPTIONAL_STAGES,
    create_customer,
)


# ---------------------------------------------------------------------------
# Helpers for the real sqlite drift check
# ---------------------------------------------------------------------------
def make_orm_metadata():
    """ORM declares: child.parent_id -> parent.id (FK) and UNIQUE(child.email)."""
    md = MetaData()
    Table("parent", md, Column("id", Integer, primary_key=True))
    Table("child", md,
          Column("id", Integer, primary_key=True),
          Column("parent_id", Integer, ForeignKey("parent.id")),
          Column("email", String),
          UniqueConstraint("email", name="uq_child_email"))
    return md


def live_db(create_fk: bool, create_unique: bool):
    """Physically create the live DB, optionally omitting the FK and/or UNIQUE
    to simulate the create_all-only drift trap from Gotcha 1."""
    eng = create_engine("sqlite:///:memory:")
    fk = "REFERENCES parent(id)" if create_fk else ""
    uq = "UNIQUE" if create_unique else ""
    with eng.begin() as c:
        c.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        c.execute(text(
            f"CREATE TABLE child (id INTEGER PRIMARY KEY, "
            f"parent_id INTEGER {fk}, email VARCHAR {uq})"))
    return _DbShim(eng, make_orm_metadata())


@pytest.fixture(autouse=True)
def _clean_env():
    saved = {k: v for k, v in os.environ.items() if k.startswith("FEATURE_")}
    for k in list(saved):
        del os.environ[k]
    impl._PER_CUSTOMER_ROWS.clear()
    yield
    for k in list(os.environ):
        if k.startswith("FEATURE_"):
            del os.environ[k]
    os.environ.update(saved)


# ===========================================================================
# ACCEPTANCE CRITERIA
# ===========================================================================
def test_ac_golden_e2e_success(monkeypatch):
    r = process_data(1, "auto")
    assert r.status == "success"
    assert r.scores_written > 0
    assert set(["score", "signal_scan", "wizard_a"]).issubset(set(r.steps_completed))
    assert not r.errors


def test_ac_idempotent_rerun(monkeypatch):
    """Second auto run reports zero NEW writes (Module 03 owns ON CONFLICT)."""
    calls = {"n": 0}
    def score(cid, mode):
        calls["n"] += 1
        return 11 if calls["n"] == 1 else 0
    monkeypatch.setattr(impl, "module03_score", score)
    first = process_data(1, "auto")
    second = process_data(1, "auto")
    assert first.scores_written == 11
    assert second.scores_written == 0


def test_ac_drift_fails_loudly_missing_fk():
    """Gotcha 1 headline: ORM declares an FK the live DB lacks -> raise."""
    db = live_db(create_fk=False, create_unique=True)
    with pytest.raises(SchemaDriftError) as ei:
        ensure_schema(app=None, db=db, run_migrations=lambda d: None)
    assert "parent.id" in str(ei.value)


def test_ac_drift_matched_schema_boots():
    """Matched schema (create_all made the FK) -> no drift, boots cleanly."""
    eng = create_engine("sqlite:///:memory:")
    md = make_orm_metadata()
    md.create_all(eng)                       # create_all DOES make the FK on fresh sqlite
    db = _DbShim(eng, md)
    ensure_schema(app=None, db=db, run_migrations=lambda d: None)  # must not raise


def test_ac_create_all_does_not_add_missing_fk_on_existing_table():
    """Prove the trap the check guards: create_all on a pre-existing table never
    adds the missing FK."""
    db = live_db(create_fk=False, create_unique=True)
    db.create_all()                          # table already exists -> skipped
    rep = check_constraint_drift(db)
    assert "parent.id" in rep.missing        # still missing after create_all


def test_ac_stage_isolation_and_order(monkeypatch):
    def boom(cid): raise RuntimeError("kaboom")
    monkeypatch.setattr(impl, "module06_signal_scan", boom)
    r = process_data(1, "auto")
    assert r.stages["signal_scan"]["ok"] is False
    assert any(e.startswith("signal_scan:") for e in r.errors)
    assert "non-fatal" in r.stages["signal_scan"]["detail"]
    # remaining stages still ran
    assert "wizard_a" in r.steps_completed and "record_run" in r.steps_completed
    assert r.status == "partial"
    # ordering invariant
    assert STAGE_ORDER.index("score") < STAGE_ORDER.index("signal_scan")


def test_ac_wizards_ab_inline_cd_absent(monkeypatch):
    # wizard_b gated below the minimum
    monkeypatch.setattr(impl, "journey_count", lambda cid: 2)
    r = process_data(1, "auto")
    assert "wizard_a" in r.steps_completed
    assert "wizard_b" not in r.steps_completed
    # No wizard C or D anywhere in the stage list
    assert not any("wizard_c" in s or "wizard_d" in s for s in STAGE_ORDER)


def test_ac_scores_written_is_int_not_string_parsed(monkeypatch):
    """Gotcha 8: mangling a step-description string must not change the count."""
    monkeypatch.setattr(impl, "module03_score", lambda cid, mode: 7)
    # publish_health returns weird text; scores_written must be unaffected
    monkeypatch.setattr(impl, "publish_health_events",
                        lambda cid: "health_written_999_scores")
    r = process_data(1, "auto")
    assert isinstance(r.scores_written, int)
    assert r.scores_written == 7


def test_ac_weight_resolver_singular_fallthrough(monkeypatch):
    # all tiers empty -> kpi_definitions default, exactly once
    monkeypatch.setattr(impl, "module01_customer_config_weights", lambda cid: None)
    monkeypatch.setattr(impl, "load_bootstrap_weights", lambda cid: None)
    w = resolve_weights(1, "dc2_s")
    assert w["_source"] == "kpi_definitions:dc2_s"
    # tier1 present -> wins
    monkeypatch.setattr(impl, "module01_customer_config_weights",
                        lambda cid: {"P1-KPI1": 9.9, "_source": "db"})
    assert resolve_weights(1, "dc2_s")["_source"] == "db"


def test_ac_vertical_single_source_determinism(monkeypatch):
    # two columns disagree; canonical (config) wins deterministically
    monkeypatch.setattr(impl, "module01_customer_config_vertical",
                        lambda cid: "saas_premium")
    monkeypatch.setattr(impl, "module01_customer_vertical", lambda cid: "dc2_s")
    v = resolve_vertical(1)
    assert v == "saas_premium"
    assert data_path(1) == "verticals/customer1-saas_premium/data"
    # data path vertical == scoring vertical (same resolver)
    assert data_path(1).split("-")[-1].split("/")[0] == resolve_vertical(1)


def test_ac_thresholds_centralized_json_move(monkeypatch):
    assert classify(49) == "critical"
    assert classify(50) == "at_risk"
    assert classify(70) == "healthy"
    assert classify(None) == "no_data"
    # move the JSON -> boundaries move
    monkeypatch.setitem(impl.THRESHOLDS, "healthy", {"min": 80})
    assert classify(70) == "at_risk"
    assert classify(80) == "healthy"


# ===========================================================================
# DEFECT 1 — Feature-toggle system is dead code: the sequencer never consults it
# ===========================================================================
def test_defect_1_toggle_gating_not_wired_into_sequencer(monkeypatch):
    """SHAPE (c)+(d). Spec: Boundary 'Owns: feature-toggle system'; Dependencies
    'add each module behind a feature toggle. A disabled module must leave the app
    booting and the rest of the pipeline working'; AC 'A disabled module still
    boots the pipeline ... with that stage absent from steps_completed'.

    Piece-5 `process_data` (SPEC lines 259-277) NEVER calls `is_enabled`. Disabling
    an optional stage's toggle therefore does NOT remove the stage from the run:
    the AC is unsatisfiable against the literal pseudocode, and the whole toggle
    manager (piece 4) is orphaned — built but never consumed.
    """
    # Disable the ROI stage's toggle via the documented env override.
    os.environ["FEATURE_ROI"] = "false"
    assert is_enabled(Toggle.ROI) is False          # toggle really is OFF

    r = process_data(1, "auto")

    # DEFECT: the disabled stage still ran and is present in steps_completed,
    # because the sequencer ignores the toggle entirely.
    assert "roi" in r.steps_completed, (
        "Expected the toggle to gate the stage, but process_data ran 'roi' "
        "regardless of FEATURE_ROI=false — toggles are never consulted.")

    # --- Corrected sequencer wires is_enabled into the loop; stage now absent ---
    _STAGE_TO_TOGGLE = {
        "signal_analyst": Toggle.SIGNAL_ANALYST, "roi": Toggle.ROI,
        "index": Toggle.INDEX, "record_run": Toggle.RECORD_RUN,
    }

    def process_data_FIXED(customer_id, mode="auto"):
        result = ProcessResult(status="", steps_completed=[], errors=[],
                               scores_written=0, stages={})
        n = run_stage("score", lambda: impl.module03_score(customer_id, mode), result)
        result.scores_written = int(n or 0)
        for extra in ("signal_analyst", "roi", "index", "record_run"):
            if not is_enabled(_STAGE_TO_TOGGLE[extra], customer_id):
                continue                      # disabled module leaves pipeline working
            run_stage(extra, lambda e=extra: OPTIONAL_STAGES[e](customer_id), result)
        result.status = ("success" if result.steps_completed and not result.errors
                         else "failed" if not result.steps_completed else "partial")
        return result

    fixed = process_data_FIXED(1, "auto")
    assert "roi" not in fixed.steps_completed        # AC now satisfied
    assert "index" in fixed.steps_completed          # others intact
    assert fixed.status == "success"


# ===========================================================================
# DEFECT 2 — Drift check ignores UNIQUE constraints (only FKs compared)
# ===========================================================================
def test_defect_2_drift_check_ignores_unique_constraints():
    """SHAPE (a)+(d). Piece-2 comment (SPEC line 172) says the check compares
    'ORM-declared FKs/uniques', and Gotcha 1's Symptom (SPEC lines 375-376) names
    'two tenants collide on an ID whose "unique" constraint was never created' as
    the second failure this guard must catch. But the pseudocode body only iterates
    `insp.get_foreign_keys(...)` — the unique-constraint check lives ONLY in the
    comment. A live DB missing a declared UNIQUE boots silently, defeating half of
    the module's headline schema-drift guarantee.
    """
    # Live DB HAS the FK but is MISSING the declared UNIQUE(email).
    db = live_db(create_fk=True, create_unique=False)

    report = check_constraint_drift(db)
    # DEFECT: unique drift is invisible -> no missing entries, ensure_schema boots.
    assert report.missing == [], (
        "Expected literal check to overlook the missing UNIQUE, and it does.")
    ensure_schema(app=None, db=db, run_migrations=lambda d: None)  # boots silently — BUG

    # --- Corrected check also compares uniques and flags the drift ---
    fixed = check_constraint_drift_FIXED(db)
    assert any("UNIQUE" in m for m in fixed.missing), (
        "Fixed check must flag the missing UNIQUE(email) constraint.")
    # and the fixed check still passes a fully-matched schema
    good = live_db(create_fk=True, create_unique=True)
    assert check_constraint_drift_FIXED(good).missing == []


# ===========================================================================
# Rule-out: the suspected `.split(".")[-2]` no-op actually DOES flag FK drift
# (documents that the FK half of the guard is sound; the gap is uniques only).
# ===========================================================================
def test_ruleout_fk_munge_is_not_a_noop():
    db = live_db(create_fk=False, create_unique=True)
    assert check_constraint_drift(db).missing == ["parent.id"]
