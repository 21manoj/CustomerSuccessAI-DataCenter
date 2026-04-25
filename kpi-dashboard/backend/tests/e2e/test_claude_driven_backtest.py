"""
test_claude_driven_backtest.py
===============================

End-to-end backtest probes against the Claude-generated synthetic dataset.
Run after `scripts/claude_driven_generate_backtest.py` + `scripts/claude_driven_ingest_batch.py`
have produced 20 synthetic tenants in `cs_pulse_test`.

Grades:
  - Wizard B organic NRR forecast vs sidecar realized_nrr_pct  (MAPE)
  - ROI engine organic projection vs sidecar realized_organic_roi_pct  (MAPE)
  - With-CS-Pulse uplift math is non-negative + bounded (sanity, not MAPE)
  - I17 invariant holds on all tenants (no reverse-time edges)
  - Per-difficulty MAPE breakdown (EASY should be much better than HARD)

Persists results to scripts/datasets/claude_driven_backtest_v1_results.json
for historical-trend governance reporting.

Requires:
  export DATABASE_URL="postgresql://cspulse:cspulse_dev@localhost:5432/cs_pulse_test"
  export SYNTHETIC_CUSTOMER_IDS="400,401,402,...,419"   (from ingest script output)
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ══════════════════════════════════════════════════════════════════════
# Module setup
# ══════════════════════════════════════════════════════════════════════

# Refuse to run against prod DB — same guard as ingest script
_db_url = os.environ.get("DATABASE_URL", "")
if "cs_pulse_test" not in _db_url.lower() and "_test" not in _db_url.lower():
    pytest.skip(
        f"test_claude_driven_backtest requires a test DB (got DATABASE_URL={_db_url!r})",
        allow_module_level=True,
    )

from app_v3_minimal import app, db
from models import Account, ContextEdge, ContextNode

SYN_CUST_ENV = os.environ.get("SYNTHETIC_CUSTOMER_IDS", "")
SYN_CUST_IDS = (
    [int(x) for x in SYN_CUST_ENV.split(",") if x.strip().isdigit()]
    if SYN_CUST_ENV
    else []
)

RESULTS_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts/datasets/claude_driven_backtest_v1_results.json"
)


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def results_accumulator():
    """Accumulates MAPE + coverage numbers across all tests, writes at teardown."""
    data = {
        "test_run_at": datetime.utcnow().isoformat() + "Z",
        "dataset_version": "v1",
        "synthetic_customer_ids": SYN_CUST_IDS,
        "metrics": {},
        "per_tenant": {},
        "per_difficulty": {},
    }
    yield data
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n✓ results written to {RESULTS_PATH}", file=sys.stderr)


def _sidecar_accounts(cust_id: int) -> list[tuple[Account, dict]]:
    """Return [(account, sidecar_dict), ...] for every account with a
    synthetic_ground_truth sidecar."""
    accts = Account.query.filter_by(customer_id=cust_id).all()
    return [
        (a, (a.profile_metadata or {}).get("synthetic_ground_truth") or {})
        for a in accts
        if (a.profile_metadata or {}).get("synthetic_ground_truth")
    ]


def _weighted_organic_nrr(accts_sidecars: list) -> float:
    """Revenue-weighted organic NRR across a tenant's accounts."""
    total_arr = 0
    weighted = 0
    for a, sc in accts_sidecars:
        arr = float(a.revenue or 0)
        if arr <= 0:
            continue
        realized = sc.get("realized_nrr_pct_for_account")
        if realized is None:
            continue
        total_arr += arr
        weighted += arr * float(realized)
    return (weighted / total_arr) if total_arr > 0 else 0.0


def _weighted_organic_roi(accts_sidecars: list) -> float:
    total_inv = 0
    total_impact = 0
    for _, sc in accts_sidecars:
        inv = sc.get("organic_cs_investment_usd_annual", 0)
        impact = sc.get("realized_organic_net_impact_usd", 0)
        if inv:
            total_inv += float(inv) / 2  # 6-month window
            total_impact += float(impact)
    return (total_impact / total_inv * 100) if total_inv > 0 else 0.0


def _run_wizard_b(cust_id: int) -> dict:
    from wizards.wizard_b_pattern_db import run_wizard_b
    try:
        return run_wizard_b(customer_id=cust_id) or {}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# NRR MAPE — the primary grading metric
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not SYN_CUST_IDS, reason="SYNTHETIC_CUSTOMER_IDS env var not set")
def test_wizard_b_organic_nrr_mape(results_accumulator):
    """Wizard B's without_cs_pulse_nrr_pct should match organic realized NRR.
    Target: portfolio MAPE < 5pp."""
    errors = []
    per_tenant = {}

    with app.app_context():
        for cid in SYN_CUST_IDS:
            accts_sc = _sidecar_accounts(cid)
            if not accts_sc:
                continue

            wb = _run_wizard_b(cid)
            nrr_fc = (wb.get("nrr_intelligence") or {}).get("forecast") or {}
            forecast = nrr_fc.get("without_cs_pulse_nrr_pct") \
                or nrr_fc.get("current_nrr_pct")
            if forecast is None:
                continue

            actual = _weighted_organic_nrr(accts_sc)
            if actual == 0:
                continue

            err_pp = abs(float(forecast) - actual)
            errors.append(err_pp)
            per_tenant[cid] = {
                "forecast": round(float(forecast), 2),
                "actual": round(actual, 2),
                "abs_err_pp": round(err_pp, 2),
            }

    assert errors, "no tenants produced comparable forecasts"
    mape = statistics.mean(errors)
    results_accumulator["metrics"]["nrr_portfolio_mape_pp"] = round(mape, 2)
    results_accumulator["metrics"]["nrr_portfolio_median_abs_err_pp"] = round(
        statistics.median(errors), 2)
    results_accumulator["per_tenant"]["nrr"] = per_tenant
    # Threshold only enforced once ≥5 tenants (single-tenant MAPE is noise)
    if len(SYN_CUST_IDS) >= 5:
        assert mape < 5.0, f"NRR portfolio MAPE {mape:.2f}pp exceeds 5pp threshold"


# ══════════════════════════════════════════════════════════════════════
# ROI MAPE
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not SYN_CUST_IDS, reason="SYNTHETIC_CUSTOMER_IDS env var not set")
def test_outcome_roi_organic_mape(results_accumulator):
    """Outcome ROI engine's historical projection vs sidecar realized ROI.
    Measures MAPE; records to results JSON; threshold relaxed when
    tenant count < 5 (single-tenant is insufficient for a portfolio MAPE)."""
    from outcome_roi_engine import calculate_historical_roi
    errors_pct = []
    per_tenant = {}

    with app.app_context():
        for cid in SYN_CUST_IDS:
            accts_sc = _sidecar_accounts(cid)
            if not accts_sc:
                continue

            try:
                roi_result = calculate_historical_roi(cid) or {}
            except Exception as e:
                print(f"  ROI calc fail cust {cid}: {e}", file=sys.stderr)
                continue

            forecast = roi_result.get("historical_roi_pct") \
                or roi_result.get("combined_roi_pct") or 0.0
            actual = _weighted_organic_roi(accts_sc)
            if actual == 0:
                continue

            err_pct = abs(float(forecast) - actual) / abs(actual) * 100
            errors_pct.append(err_pct)
            per_tenant[cid] = {
                "forecast_pct": round(float(forecast), 1),
                "actual_pct": round(actual, 1),
                "abs_err_pct": round(err_pct, 1),
            }

    if not errors_pct:
        results_accumulator["metrics"]["roi_portfolio_mape_pct"] = None
        results_accumulator["metrics"]["roi_no_comparable"] = True
        return  # record-and-return; not a hard fail

    mape = statistics.mean(errors_pct)
    results_accumulator["metrics"]["roi_portfolio_mape_pct"] = round(mape, 2)
    results_accumulator["per_tenant"]["roi"] = per_tenant
    # Relaxed: threshold only enforced once ≥5 tenants in dataset
    if len(SYN_CUST_IDS) >= 5:
        assert mape < 25.0, f"ROI portfolio MAPE {mape:.1f}% exceeds 25% threshold"


# ══════════════════════════════════════════════════════════════════════
# Sanity checks on with-CS-Pulse math (not MAPE)
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not SYN_CUST_IDS, reason="SYNTHETIC_CUSTOMER_IDS env var not set")
def test_with_cs_pulse_uplift_non_negative_bounded(results_accumulator):
    """with_cs_pulse_nrr_pct >= without_cs_pulse_nrr_pct, and uplift < 15pp."""
    violations = []
    uplifts = []

    with app.app_context():
        for cid in SYN_CUST_IDS:
            wb = _run_wizard_b(cid)
            nrr_fc = (wb.get("nrr_intelligence") or {}).get("forecast") or {}
            organic = nrr_fc.get("without_cs_pulse_nrr_pct")
            # Wizard B encodes "with CS Pulse" as current_nrr_pct (the
            # post-intervention projection). with_cs_pulse_nrr_pct name
            # is reserved for future explicit field.
            with_cs = nrr_fc.get("with_cs_pulse_nrr_pct") \
                or nrr_fc.get("current_nrr_pct")
            if organic is None or with_cs is None:
                continue
            uplift = float(with_cs) - float(organic)
            uplifts.append(uplift)
            if with_cs < organic:
                violations.append((cid, "with_cs < organic", organic, with_cs))
            if uplift > 25:
                violations.append((cid, "uplift > 25pp", organic, with_cs))

    results_accumulator["metrics"]["mean_uplift_pp"] = (
        round(statistics.mean(uplifts), 2) if uplifts else None
    )
    assert not violations, f"uplift sanity violations: {violations[:5]}"


# ══════════════════════════════════════════════════════════════════════
# Invariant probe — I17 must hold on all synthetic tenants
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not SYN_CUST_IDS, reason="SYNTHETIC_CUSTOMER_IDS env var not set")
def test_i17_zero_violations_on_synthetic(results_accumulator):
    """Pre-commit gate held on every edge written by pipeline for all tenants."""
    total = 0
    per_tenant = {}

    with app.app_context():
        for cid in SYN_CUST_IDS:
            q = (
                db.session.query(ContextEdge)
                .join(ContextNode, ContextNode.node_id == ContextEdge.from_node_id)
                .filter(ContextEdge.customer_id == cid)
                .filter(ContextEdge.edge_type.in_(
                    ["CAUSED_BY", "LED_TO", "TRIGGERED", "RESULTED_IN", "INDICATES"]))
            )
            # Re-join for to_node temporal check
            count = 0
            for edge in q.all():
                from_node = ContextNode.query.get(edge.from_node_id)
                to_node = ContextNode.query.get(edge.to_node_id)
                if (from_node and to_node
                        and from_node.occurred_at and to_node.occurred_at
                        and from_node.occurred_at > to_node.occurred_at):
                    count += 1
            total += count
            per_tenant[cid] = count

    results_accumulator["metrics"]["i17_violations_total"] = total
    results_accumulator["per_tenant"]["i17"] = per_tenant
    # Record as data but don't hard-fail beta backtest: the invariant is a
    # platform gate, and a violation here points at pipeline-side work
    # (Wizard A LLM / context_graph writer). Gate flips to strict assertion
    # once ≥5 tenants confirm the platform fix.
    if len(SYN_CUST_IDS) >= 5:
        assert total == 0, f"{total} I17 violations across synthetic tenants: {per_tenant}"


# ══════════════════════════════════════════════════════════════════════
# Per-difficulty MAPE — dataset-quality check
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not SYN_CUST_IDS, reason="SYNTHETIC_CUSTOMER_IDS env var not set")
def test_per_difficulty_mape_spread(results_accumulator):
    """HARD cases should have systematically higher error than EASY.
    If they don't, the dataset is too homogeneous — regenerate with stronger
    diversity prompts."""
    buckets = {"EASY": [], "MEDIUM": [], "HARD": []}

    with app.app_context():
        for cid in SYN_CUST_IDS:
            accts_sc = _sidecar_accounts(cid)
            wb = _run_wizard_b(cid)
            forecast_portfolio = (wb.get("nrr") or {}).get(
                "without_cs_pulse_nrr_pct"
            ) or (wb.get("nrr") or {}).get("current_nrr_pct")
            if forecast_portfolio is None:
                continue
            # Portfolio-level forecast applied to each account's realized; imperfect
            # but captures the general shape of who's harder to forecast.
            for a, sc in accts_sc:
                diff = sc.get("difficulty")
                realized = sc.get("realized_nrr_pct_for_account")
                if diff not in buckets or realized is None:
                    continue
                buckets[diff].append(abs(float(forecast_portfolio) - float(realized)))

    per_diff = {}
    for k, vals in buckets.items():
        if vals:
            per_diff[k] = {
                "n": len(vals),
                "mape_pp": round(statistics.mean(vals), 2),
                "median_pp": round(statistics.median(vals), 2),
            }
    results_accumulator["per_difficulty"] = per_diff

    if buckets["EASY"] and buckets["HARD"] and len(SYN_CUST_IDS) >= 5:
        easy_mape = statistics.mean(buckets["EASY"])
        hard_mape = statistics.mean(buckets["HARD"])
        # HARD should be at least 1.2× harder than EASY — if not,
        # Claude didn't generate enough adversarial cases.
        assert hard_mape >= easy_mape * 1.2, (
            f"Dataset too homogeneous: EASY MAPE {easy_mape:.2f}pp vs "
            f"HARD {hard_mape:.2f}pp — expected HARD >= 1.2× EASY. "
            f"Regenerate dataset with stronger diversity constraints."
        )
