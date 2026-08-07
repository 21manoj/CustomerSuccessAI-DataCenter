"""
Health Scoring Engine -- standalone pilot-validation build.

This is an independent, from-scratch implementation of the module described in
`consulting-framework/modules/03-intelligence-health-scoring-engine.md`, built
for a HYPOTHETICAL vertical ("freightops_v1" -- a fleet-management SaaS, see
sample_vertical_config.json) that does not exist anywhere else in this repo.

It was written by reading ONLY the module spec -- no reference implementation
files under kpi-dashboard/backend/ were opened. Any design choice not pinned
down by the spec is called out with a "SPEC AMBIGUITY" comment at the decision
point, and is also summarized in the validation report.

Since there is no real database available (and the task says not to invent one
by reading models.py), all persistence is a tiny in-memory `InMemoryDB` class
using dataclasses/dicts/lists as a stand-in for Postgres tables. The point is
to prove out the rollup math, the canonical read contract, weight resolution,
and the idempotent-write contract -- not to wire up real storage.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("health_scoring_engine")
# Set this logger's own level explicitly (rather than relying on root via
# logging.basicConfig) so weight-resolution INFO logs stay visible even when
# an embedding test runner (e.g. pytest's log-capture plugin) raises the
# root logger's effective level -- the spec requires this be "visible in
# normal operational logs," which should not depend on ambient root config.
logger.setLevel(logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_vertical_config(path: str) -> dict:
    """Load the KPI catalog config (Module 02's output, per the spec's Build
    Prompt JSON shape: {"pillars": {...}, "kpis": {...}})."""
    with open(path, "r") as f:
        return json.load(f)


# health_thresholds.json equivalent. Spec: "this system uses 70/50, but
# that's a client decision, not an engine constant" -- kept as a separate,
# swappable dict rather than hardcoded numbers inside classify_health_status.
DEFAULT_THRESHOLDS = {
    "healthy_min": 70,
    "at_risk_min": 50,
}


def classify_health_status(score: float, thresholds: dict = DEFAULT_THRESHOLDS) -> str:
    """Single classification function every caller must go through -- Gotcha 6:
    no inline 70/50 literals anywhere else in this module."""
    if score >= thresholds["healthy_min"]:
        return "healthy"
    if score >= thresholds["at_risk_min"]:
        return "at_risk"
    return "critical"


# ---------------------------------------------------------------------------
# In-memory "database" stand-ins (NOT the real models.py -- invented minimal
# shapes sufficient to exercise the contract described in the spec)
# ---------------------------------------------------------------------------

@dataclass
class Account:
    account_id: str
    customer_id: str
    name: str


@dataclass
class Customer:
    customer_id: str
    name: str
    vertical: str


@dataclass
class KPIRow:
    account_id: str
    measurement_month: str  # "YYYY-MM" -- treated as an opaque, sortable key
    kpi_code: str
    value: float
    uploaded_at: datetime  # wall-clock time the row was written, for Gotcha 3 tests


@dataclass
class PillarScoreRow:
    account_id: str
    measurement_month: str
    pillar: str
    pillar_score: float
    created_at: datetime


@dataclass
class HealthScoreRow:
    account_id: str
    measurement_month: str
    health_score: float
    health_status: str
    created_at: datetime


@dataclass
class CustomerConfigRow:
    customer_id: str
    vertical: str
    weight_overrides: Optional[Dict[str, float]]  # pillar_code -> weight_l2, or None/empty


class InMemoryDB:
    """Stand-in for the Postgres tables Module 01 would define. Lists instead
    of a real table so we can freely inspect/mutate in tests."""

    def __init__(self) -> None:
        self.accounts: Dict[str, Account] = {}
        self.customers: Dict[str, Customer] = {}
        self.kpi_rows: List[KPIRow] = []
        self.pillar_scores: List[PillarScoreRow] = []
        self.health_scores: List[HealthScoreRow] = []
        self.customer_configs: Dict[str, CustomerConfigRow] = {}

    # -- convenience lookups -------------------------------------------------

    def kpi_rows_for(self, account_id: str, month: str) -> Dict[str, float]:
        return {
            r.kpi_code: r.value
            for r in self.kpi_rows
            if r.account_id == account_id and r.measurement_month == month
        }

    def scored_months_for(self, account_id: str) -> set:
        return {
            r.measurement_month
            for r in self.health_scores
            if r.account_id == account_id
        }

    def kpi_months_for(self, account_id: str) -> set:
        return {r.measurement_month for r in self.kpi_rows if r.account_id == account_id}

    def latest_health_score(self, account_id: str) -> Optional[HealthScoreRow]:
        rows = [r for r in self.health_scores if r.account_id == account_id]
        if not rows:
            return None
        # "latest" = most recent measurement_month (string-sortable YYYY-MM),
        # tie-broken by created_at.
        return sorted(rows, key=lambda r: (r.measurement_month, r.created_at))[-1]

    def pillar_scores_for_month(self, account_id: str, month: str) -> Dict[str, float]:
        return {
            r.pillar: r.pillar_score
            for r in self.pillar_scores
            if r.account_id == account_id and r.measurement_month == month
        }


# ---------------------------------------------------------------------------
# AccountHealth -- canonical read-service return type. Gotcha 2: dataclass,
# never a tuple.
# ---------------------------------------------------------------------------

@dataclass
class AccountHealth:
    account_id: str
    health_score: Optional[float]
    health_status: Optional[str]
    measurement_month: Optional[str]
    pillars: dict = field(default_factory=dict)
    missing: bool = False
    missing_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Layer 1: Rollup math
# ---------------------------------------------------------------------------

def _normalize_kpi_value(value: float, kpi_config: dict) -> float:
    """Normalize a single KPI value to a 0-100 sub-score against its healthy
    range, per the Build Prompt: 'normalizes each KPI value against its
    healthy-range max (or min, if higher_is_better is false)'.

    SPEC AMBIGUITY (see validation report item 2): the spec states WHICH bound
    to normalize against but not the actual formula, nor how to handle a value
    of zero/negative for a lower-is-better KPI (division by the bound would
    divide-by-zero or blow past 100 in ways the spec doesn't define). This
    implementation's choice, made explicitly because the spec didn't pin it
    down:
      - higher_is_better: sub_score = 100 * value / healthy.max, clamped to
        [0, 100]. Reaching (or exceeding) the healthy max is a perfect 100;
        below it scales down linearly toward 0.
      - lower_is_better: sub_score = 100 * healthy.min / value, clamped to
        [0, 100], with the edge case value <= 0 treated as a perfect 100
        (can't do better than zero incidents/cost/etc). This uses
        healthy.min as the "target/best" reference point per the spec's
        parenthetical, not healthy.max.
    """
    higher_is_better = kpi_config["higher_is_better"]
    healthy = kpi_config["ranges"]["healthy"]

    if higher_is_better:
        bound = healthy["max"]
        if bound <= 0:
            return 0.0
        score = 100.0 * (value / bound)
    else:
        bound = healthy["min"]
        if value <= 0:
            return 100.0
        score = 100.0 * (bound / value)

    return max(0.0, min(100.0, score))


def calculate_pillar_score(pillar: str, kpi_values: Dict[str, float], config: dict) -> float:
    """Weighted-average rollup of KPI values (already normalized to 0-100)
    into a single pillar score. Returns 0 (never raises, never None) if
    kpi_values has nothing for this pillar's KPIs -- Acceptance Criterion 2."""
    pillar_kpi_codes = [
        code for code, kc in config["kpis"].items() if kc["pillar"] == pillar
    ]

    weighted_sum = 0.0
    weight_total = 0.0
    for code in pillar_kpi_codes:
        if code not in kpi_values:
            continue
        kc = config["kpis"][code]
        sub_score = _normalize_kpi_value(kpi_values[code], kc)
        weighted_sum += sub_score * kc["weight_l1"]
        weight_total += kc["weight_l1"]

    if weight_total <= 0:
        return 0.0

    # SPEC AMBIGUITY: if only SOME of a pillar's KPIs are present (not all,
    # not none), the spec's acceptance criteria only cover the "entire
    # pillar missing" case explicitly. This implementation re-normalizes
    # over the weights that ARE present (weighted_sum / weight_total) rather
    # than dividing by the full pillar weight_l1 sum, so a partially-reported
    # pillar isn't artificially deflated. See validation report item 2.
    return weighted_sum / weight_total


def calculate_overall_health(pillar_scores: Dict[str, float], config: dict) -> float:
    """Weighted-average of pillar scores using L2 weights. Returns 0 if given
    no data (empty pillar_scores) -- never raises, never None."""
    weighted_sum = 0.0
    weight_total = 0.0
    for pillar, score in pillar_scores.items():
        if pillar not in config["pillars"]:
            continue
        w = config["pillars"][pillar]["weight_l2"]
        weighted_sum += score * w
        weight_total += w

    if weight_total <= 0:
        return 0.0

    return weighted_sum / weight_total


# ---------------------------------------------------------------------------
# Layer 3: Weight resolution
# ---------------------------------------------------------------------------

def resolve_l2_weights(customer_id: str, db: InMemoryDB, config: dict) -> Dict[str, float]:
    """Per-customer override (DB) -> code bootstrap default, source always
    logged at INFO. Implements the Gotcha 4 FIX directly: gate only on
    "does a non-empty override config exist for this customer", not on a
    vertical-name string match (that's exactly the bug the spec describes)."""
    bootstrap_weights = {p: pc["weight_l2"] for p, pc in config["pillars"].items()}

    cfg_row = db.customer_configs.get(customer_id)
    if cfg_row is not None and cfg_row.weight_overrides:
        logger.info(
            "Weight resolution for customer_id=%s: source=CUSTOMER_OVERRIDE "
            "(non-empty override config found)",
            customer_id,
        )
        return dict(cfg_row.weight_overrides)

    reason = "no_override_row" if cfg_row is None else "override_row_empty"
    logger.info(
        "Weight resolution for customer_id=%s: source=BOOTSTRAP_DEFAULT reason=%s",
        customer_id,
        reason,
    )
    return bootstrap_weights


# ---------------------------------------------------------------------------
# Layer 2: Canonical read service
# ---------------------------------------------------------------------------

def get_account_health(
    account_id: str,
    db: InMemoryDB,
    customer_id: Optional[str] = None,
    thresholds: dict = DEFAULT_THRESHOLDS,
) -> AccountHealth:
    """Canonical single-account read. Tenant-checked when customer_id is
    given. Always returns a dataclass. Pillars are pinned to the SAME
    measurement_month as the overall score (Gotcha 3) -- never independently
    "latest row per pillar."
    """
    account = db.accounts.get(account_id)

    if customer_id is not None:
        if account is None or account.customer_id != customer_id:
            return AccountHealth(
                account_id=account_id,
                health_score=None,
                health_status=None,
                measurement_month=None,
                pillars={},
                missing=True,
                missing_reason="not_found_or_wrong_tenant",
            )

    latest = db.latest_health_score(account_id)
    if latest is None:
        return AccountHealth(
            account_id=account_id,
            health_score=None,
            health_status=None,
            measurement_month=None,
            pillars={},
            missing=True,
            missing_reason="no_health_scores",
        )

    # Gotcha 3: scope pillar rows to the overall score row's own
    # measurement_month, never an independent "latest per pillar" query.
    pillars = db.pillar_scores_for_month(account_id, latest.measurement_month)

    return AccountHealth(
        account_id=account_id,
        health_score=latest.health_score,
        health_status=latest.health_status,
        measurement_month=latest.measurement_month,
        pillars=pillars,
        missing=False,
        missing_reason=None,
    )


# ---------------------------------------------------------------------------
# Idempotent scoring pipeline
# ---------------------------------------------------------------------------

def is_file_newer_than_db(file_mtime_epoch: float, db_last_written_utc: datetime) -> bool:
    """UTC-safe timestamp comparison helper for pipelines that decide "is
    there new data" by comparing a file's on-disk mtime against a DB
    'last written' timestamp (Gotcha 5). Both sides are converted to
    timezone-aware UTC before comparing -- never mixing a naive local
    fromtimestamp() against a UTC-stored value.
    """
    file_time_utc = datetime.fromtimestamp(file_mtime_epoch, tz=timezone.utc)
    if db_last_written_utc.tzinfo is None:
        # Defensive: treat naive DB timestamps as already UTC (as the spec's
        # origin system stores them), rather than silently comparing a naive
        # value against an aware one (which raises in Python anyway).
        db_last_written_utc = db_last_written_utc.replace(tzinfo=timezone.utc)
    return file_time_utc > db_last_written_utc


def run_scoring_pipeline(
    db: InMemoryDB,
    config: dict,
    thresholds: dict = DEFAULT_THRESHOLDS,
    full_recalc: bool = False,
) -> List[HealthScoreRow]:
    """Detects new data to score by finding KPI rows whose (account_id,
    month) isn't already in the scored set (or, if full_recalc, rescoring
    everything). Writes are idempotent: an (account_id, measurement_month)
    that already has a HealthScore row is skipped on a normal run.

    Returns the list of newly-written HealthScoreRow objects (empty list if
    nothing new was written), so callers/tests can assert "wrote zero new
    rows" without re-reading the whole DB.
    """
    newly_written: List[HealthScoreRow] = []
    now = datetime.now(timezone.utc)

    # Every (account_id, month) combination that has KPI data at all.
    all_account_months = sorted(
        {(r.account_id, r.measurement_month) for r in db.kpi_rows}
    )

    for account_id, month in all_account_months:
        already_scored = month in db.scored_months_for(account_id)
        if already_scored and not full_recalc:
            continue

        kpi_values = db.kpi_rows_for(account_id, month)

        pillar_scores: Dict[str, float] = {}
        for pillar in config["pillars"]:
            pillar_scores[pillar] = calculate_pillar_score(pillar, kpi_values, config)

        overall = calculate_overall_health(pillar_scores, config)
        status = classify_health_status(overall, thresholds)

        if full_recalc:
            # Explicit full_recalc mode is the only path allowed to overwrite
            # existing rows for this (account_id, month).
            db.pillar_scores = [
                r for r in db.pillar_scores
                if not (r.account_id == account_id and r.measurement_month == month)
            ]
            db.health_scores = [
                r for r in db.health_scores
                if not (r.account_id == account_id and r.measurement_month == month)
            ]

        for pillar, score in pillar_scores.items():
            db.pillar_scores.append(
                PillarScoreRow(
                    account_id=account_id,
                    measurement_month=month,
                    pillar=pillar,
                    pillar_score=score,
                    created_at=now,
                )
            )

        health_row = HealthScoreRow(
            account_id=account_id,
            measurement_month=month,
            health_score=overall,
            health_status=status,
            created_at=now,
        )
        db.health_scores.append(health_row)
        newly_written.append(health_row)

    return newly_written
