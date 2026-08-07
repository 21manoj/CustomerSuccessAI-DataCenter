"""
Test suite for the pilot-validation Health Scoring Engine build.

Each test is labeled with which "Acceptance Criteria" bullet (from
consulting-framework/modules/03-intelligence-health-scoring-engine.md) it
exercises, quoted verbatim in the docstring, so it's traceable back to the
spec. A couple of extra tests at the bottom cover the "Reference Test
Harness" item 1 (hand-computed rollup math) and touch on Gotcha 5's UTC
helper, which are not literally AC bullets but are explicitly called for
elsewhere in the spec.

Run with: python -m pytest test_health_scoring_engine.py -v
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pytest

from health_scoring_engine import (
    Account,
    Customer,
    CustomerConfigRow,
    HealthScoreRow,
    InMemoryDB,
    KPIRow,
    PillarScoreRow,
    calculate_overall_health,
    calculate_pillar_score,
    classify_health_status,
    get_account_health,
    is_file_newer_than_db,
    load_vertical_config,
    resolve_l2_weights,
    run_scoring_pipeline,
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sample_vertical_config.json")


@pytest.fixture
def config():
    return load_vertical_config(CONFIG_PATH)


@pytest.fixture
def db():
    return InMemoryDB()


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# AC 1: "Given a KPI catalog with pillars whose weight_l2 values sum to 1.0,
# and an account with values for every KPI, calculate_overall_health returns
# a value strictly between the account's lowest and highest pillar score."
# ---------------------------------------------------------------------------

def test_ac1_overall_health_strictly_between_pillar_extremes(config):
    weight_l2_sum = sum(p["weight_l2"] for p in config["pillars"].values())
    assert weight_l2_sum == pytest.approx(1.0)

    # Values for every KPI in the catalog, deliberately varied so pillar
    # scores differ from each other (see validation report on why "strictly
    # between" cannot hold in general if all pillar scores are equal).
    kpi_values = {
        "VH-UPTIME": 98,
        "VH-MAINT": 1,
        "DS-INCIDENT": 0.5,
        "DS-COMPLIANCE": 99,
        "DP-ONTIME": 97,
        "DP-DAMAGE": 0.5,
        "FE-MPG": 8,
        "FE-COSTMILE": 1.5,
    }

    pillar_scores = {
        pillar: calculate_pillar_score(pillar, kpi_values, config)
        for pillar in config["pillars"]
    }

    overall = calculate_overall_health(pillar_scores, config)

    lo, hi = min(pillar_scores.values()), max(pillar_scores.values())
    assert lo < overall < hi, (pillar_scores, overall)


# ---------------------------------------------------------------------------
# AC 2: "Given kpi_values missing an entire pillar's KPIs,
# calculate_pillar_score for that pillar returns 0, not an exception, not
# None."
# ---------------------------------------------------------------------------

def test_ac2_missing_entire_pillar_returns_zero(config):
    kpi_values = {
        # Only P1's KPIs present; P2, P3, P4 entirely absent.
        "VH-UPTIME": 97,
        "VH-MAINT": 0.5,
    }
    for pillar in ("P2", "P3", "P4"):
        result = calculate_pillar_score(pillar, kpi_values, config)
        assert result == 0
        assert result is not None

    # And fully empty kpi_values for a pillar that does have KPIs at all.
    assert calculate_pillar_score("P1", {}, config) == 0


# ---------------------------------------------------------------------------
# AC 3: "get_account_health(account_id, customer_id=X) for an account that
# exists but belongs to customer Y != X returns missing=True,
# missing_reason='not_found_or_wrong_tenant' -- never that account's real
# score."
# ---------------------------------------------------------------------------

def test_ac3_cross_tenant_read_returns_wrong_tenant(db, config):
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-1"] = Account("acct-1", "cust-Y", "Acme Depot 12")
    db.health_scores.append(
        HealthScoreRow("acct-1", "2026-06", 88.0, "healthy", _now())
    )
    db.pillar_scores.append(
        PillarScoreRow("acct-1", "2026-06", "P1", 90.0, _now())
    )

    result = get_account_health("acct-1", db, customer_id="cust-X")

    assert result.missing is True
    assert result.missing_reason == "not_found_or_wrong_tenant"
    # The real score must never leak through, in any field.
    assert result.health_score is None
    assert result.pillars == {}


# ---------------------------------------------------------------------------
# AC 4: "get_account_health for an account with zero HealthScore rows
# returns missing=True, missing_reason='no_health_scores' -- the caller must
# be able to distinguish 'no data' from 'score is literally zero.'"
# ---------------------------------------------------------------------------

def test_ac4_zero_health_score_rows_returns_no_health_scores(db, config):
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-2"] = Account("acct-2", "cust-Y", "Acme Depot 44")
    # Deliberately no db.health_scores rows for acct-2.

    result = get_account_health("acct-2", db)  # no tenant check requested

    assert result.missing is True
    assert result.missing_reason == "no_health_scores"
    assert result.health_score is None  # never a sentinel like 0 or 50


def test_ac4_distinguishable_from_a_real_zero_score(db, config):
    """A literal score of 0 must be distinguishable from 'no data' -- confirm
    a real (if pathological) zero score does NOT get coerced into the
    missing-data path."""
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-3"] = Account("acct-3", "cust-Y", "Acme Depot 77")
    db.health_scores.append(
        HealthScoreRow("acct-3", "2026-06", 0.0, "critical", _now())
    )

    result = get_account_health("acct-3", db)

    assert result.missing is False
    assert result.health_score == 0.0
    assert result.missing_reason is None


# ---------------------------------------------------------------------------
# AC 5: "AccountHealth.pillars for a given call always share
# measurement_month with AccountHealth.health_score -- assert this holds even
# when different pillars' underlying KPI data was uploaded at different
# wall-clock times."
# ---------------------------------------------------------------------------

def test_ac5_pillars_pinned_to_overall_scores_month_not_latest_per_pillar(db, config):
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-4"] = Account("acct-4", "cust-Y", "Acme Depot 5")

    t0 = datetime(2026, 6, 5, tzinfo=timezone.utc)
    t1 = datetime(2026, 7, 20, tzinfo=timezone.utc)  # uploaded much later, wall-clock

    # The overall HealthScore row is (and stays) pinned to 2026-06 -- e.g.
    # the pipeline hasn't scored July yet because not every pillar has July
    # data.
    db.health_scores.append(
        HealthScoreRow("acct-4", "2026-06", 72.0, "at_risk", t0)
    )
    for pillar, val in {"P1": 66.8, "P2": 69.5, "P3": 73.9, "P4": 84.4}.items():
        db.pillar_scores.append(
            PillarScoreRow("acct-4", "2026-06", pillar, val, t0)
        )

    # A newer, partial upload: only P1's July pillar score exists, written
    # much later in wall-clock time than the June rows above. A naive
    # "latest row per pillar" query would pick THIS up for P1 and mix it
    # with June data for P2-P4.
    db.pillar_scores.append(
        PillarScoreRow("acct-4", "2026-07", "P1", 40.0, t1)
    )

    result = get_account_health("acct-4", db)

    assert result.measurement_month == "2026-06"
    assert result.pillars["P1"] == 66.8, "must use June's P1, not the newer July row"
    assert set(result.pillars.keys()) == {"P1", "P2", "P3", "P4"}
    assert all(
        # every pillar row actually used came from the June cohort
        val in (66.8, 69.5, 73.9, 84.4) for val in result.pillars.values()
    )


# ---------------------------------------------------------------------------
# AC 6: "Calling the scoring pipeline twice in a row on identical input data
# (no new KPI rows) writes zero new HealthScore rows the second time -- but
# calling it after genuinely new KPI rows exist (later month, or a same-day
# incremental reload) writes new rows within the same run, without needing a
# manual trigger."
# ---------------------------------------------------------------------------

def test_ac6_idempotent_then_picks_up_new_data_same_run(db, config):
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-5"] = Account("acct-5", "cust-Y", "Acme Depot 9")

    db.kpi_rows.append(KPIRow("acct-5", "2026-06", "VH-UPTIME", 96, _now()))
    db.kpi_rows.append(KPIRow("acct-5", "2026-06", "DS-COMPLIANCE", 99, _now()))

    first_run = run_scoring_pipeline(db, config)
    assert len(first_run) == 1
    assert len(db.health_scores) == 1

    # Re-run with NO new KPI rows: must write zero new rows.
    second_run = run_scoring_pipeline(db, config)
    assert second_run == []
    assert len(db.health_scores) == 1

    # Genuinely new data arrives: a later month for the same account.
    db.kpi_rows.append(KPIRow("acct-5", "2026-07", "VH-UPTIME", 80, _now()))

    third_run = run_scoring_pipeline(db, config)
    assert len(third_run) == 1
    assert third_run[0].measurement_month == "2026-07"
    assert len(db.health_scores) == 2  # both June and July now present

    # Same-day incremental reload: more KPI rows added for a month that has
    # NOT yet been scored (simulating a second batch landing the same day
    # for a brand-new month) still gets picked up without a manual/full
    # recalc trigger.
    db.kpi_rows.append(KPIRow("acct-5", "2026-08", "VH-UPTIME", 91, _now()))
    fourth_run = run_scoring_pipeline(db, config)
    assert len(fourth_run) == 1
    assert fourth_run[0].measurement_month == "2026-08"


def test_ac6_full_recalc_is_the_only_path_that_overwrites(db, config):
    db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
    db.accounts["acct-6"] = Account("acct-6", "cust-Y", "Acme Depot 3")
    db.kpi_rows.append(KPIRow("acct-6", "2026-06", "VH-UPTIME", 96, _now()))

    run_scoring_pipeline(db, config)
    original_score = db.health_scores[0].health_score

    # Mutate the underlying KPI value (simulating a correction) without
    # adding a new (account, month) pair -- normal run must NOT rescore it.
    db.kpi_rows[0].value = 10
    normal_rerun = run_scoring_pipeline(db, config)
    assert normal_rerun == []
    assert db.health_scores[0].health_score == original_score

    # Only full_recalc=True is allowed to rewrite the existing row.
    recalc_run = run_scoring_pipeline(db, config, full_recalc=True)
    assert len(recalc_run) == 1
    assert len(db.health_scores) == 1  # old row replaced, not duplicated
    assert db.health_scores[0].health_score != original_score


# ---------------------------------------------------------------------------
# AC 7: "Weight resolution logs its source (customer-override vs.
# bootstrap-default) every time it's called with a customer_id, at a level
# visible in normal operational logs."
# ---------------------------------------------------------------------------

class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_ac7_weight_resolution_logs_bootstrap_default_source(db, config):
    handler = _CapturingHandler()
    eng_logger = logging.getLogger("health_scoring_engine")
    eng_logger.addHandler(handler)
    try:
        db.customers["cust-Y"] = Customer("cust-Y", "Acme Logistics", "freightops_v1")
        # No CustomerConfigRow at all for cust-Y.
        weights = resolve_l2_weights("cust-Y", db, config)

        assert weights == {p: pc["weight_l2"] for p, pc in config["pillars"].items()}
        assert len(handler.records) == 1
        msg = handler.records[0].getMessage()
        assert handler.records[0].levelno == logging.INFO
        assert "BOOTSTRAP_DEFAULT" in msg
        assert "cust-Y" in msg
    finally:
        eng_logger.removeHandler(handler)


def test_ac7_weight_resolution_logs_customer_override_source(db, config):
    handler = _CapturingHandler()
    eng_logger = logging.getLogger("health_scoring_engine")
    eng_logger.addHandler(handler)
    try:
        db.customers["cust-Z"] = Customer("cust-Z", "Bolt Freight", "freightops_v1")
        db.customer_configs["cust-Z"] = CustomerConfigRow(
            customer_id="cust-Z",
            vertical="freightops_v1",
            weight_overrides={"P1": 0.55, "P2": 0.15, "P3": 0.15, "P4": 0.15},
        )

        weights = resolve_l2_weights("cust-Z", db, config)

        assert weights == {"P1": 0.55, "P2": 0.15, "P3": 0.15, "P4": 0.15}
        assert len(handler.records) == 1
        msg = handler.records[0].getMessage()
        assert handler.records[0].levelno == logging.INFO
        assert "CUSTOMER_OVERRIDE" in msg
        assert "cust-Z" in msg
    finally:
        eng_logger.removeHandler(handler)


def test_ac7_weight_resolution_ignores_vertical_gate_gotcha4(db, config):
    """Directly exercises Gotcha 4's fix: a customer's override must NOT be
    silently dropped because of a vertical-name mismatch check -- gate only
    on 'does a non-empty override exist'."""
    handler = _CapturingHandler()
    eng_logger = logging.getLogger("health_scoring_engine")
    eng_logger.addHandler(handler)
    try:
        db.customers["cust-W"] = Customer("cust-W", "New Vertical Co", "some_brand_new_vertical")
        db.customer_configs["cust-W"] = CustomerConfigRow(
            customer_id="cust-W",
            vertical="some_brand_new_vertical",  # deliberately NOT "freightops_v1"
            weight_overrides={"P1": 0.4, "P2": 0.2, "P3": 0.2, "P4": 0.2},
        )

        weights = resolve_l2_weights("cust-W", db, config)

        assert weights == {"P1": 0.4, "P2": 0.2, "P3": 0.2, "P4": 0.2}
        assert "CUSTOMER_OVERRIDE" in handler.records[0].getMessage()
    finally:
        eng_logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Bonus (not a literal AC bullet, but called for by "Reference Test Harness"
# item 1): hand-computed rollup math, including all-missing / all-healthy
# edge cases.
# ---------------------------------------------------------------------------

def test_rollup_hand_computed_all_healthy(config):
    # Every KPI exactly at its healthy-range boundary that yields 100.
    kpi_values = {
        "VH-UPTIME": 100,     # 100 * 100/100 = 100
        "VH-MAINT": 0.2,      # lower-is-better, value == healthy.min -> 100
        "DS-INCIDENT": 0.2,   # value == healthy.min -> 100
        "DS-COMPLIANCE": 100,
        "DP-ONTIME": 100,
        "DP-DAMAGE": 0.1,
        "FE-MPG": 9,
        "FE-COSTMILE": 1.2,
    }
    for pillar in config["pillars"]:
        assert calculate_pillar_score(pillar, kpi_values, config) == pytest.approx(100.0)

    pillar_scores = {p: 100.0 for p in config["pillars"]}
    assert calculate_overall_health(pillar_scores, config) == pytest.approx(100.0)


def test_rollup_hand_computed_all_missing(config):
    for pillar in config["pillars"]:
        assert calculate_pillar_score(pillar, {}, config) == 0
    assert calculate_overall_health({}, config) == 0


def test_rollup_hand_computed_p1_specific_value(config):
    # P1: VH-UPTIME weight .6 (higher_is_better, healthy.max=100),
    #     VH-MAINT weight .4 (lower_is_better, healthy.min=0.2)
    kpi_values = {"VH-UPTIME": 90, "VH-MAINT": 1.0}
    # sub(VH-UPTIME) = 100 * 90/100 = 90
    # sub(VH-MAINT)  = 100 * 0.2/1.0 = 20
    # pillar = 90*.6 + 20*.4 = 54 + 8 = 62
    assert calculate_pillar_score("P1", kpi_values, config) == pytest.approx(62.0)


def test_classify_health_status_thresholds():
    assert classify_health_status(85) == "healthy"
    assert classify_health_status(70) == "healthy"
    assert classify_health_status(69.9) == "at_risk"
    assert classify_health_status(50) == "at_risk"
    assert classify_health_status(49.9) == "critical"
    assert classify_health_status(0) == "critical"


def test_gotcha5_utc_safe_timestamp_comparison():
    """Not an AC bullet, but Gotcha 5 explicitly calls this out as something
    to get right. Simulate a file uploaded at 11:00 PM Pacific (which is
    07:00 UTC the NEXT day) against a DB timestamp of "same day, 11:59 PM
    UTC" -- a naive local-time comparison would wrongly call the file
    older."""
    db_last_written = datetime(2026, 8, 6, 23, 59, tzinfo=timezone.utc)
    # File mtime as a UTC epoch timestamp for 2026-08-07 07:00 UTC (which is
    # 2026-08-06 23:00 Pacific -- i.e. earlier that same Pacific evening).
    file_mtime_utc = datetime(2026, 8, 7, 7, 0, tzinfo=timezone.utc).timestamp()

    assert is_file_newer_than_db(file_mtime_utc, db_last_written) is True
