"""
Module 08 - Persona Dashboards: spec-faithful reconstruction from SPEC.md alone.

Self-contained. Fake Account objects + fake dependency hooks for Modules
01/03/04/05 and Module 07's envelope(). No DB, no network.

Dependency hooks are module-level names that tests assign (monkeypatch). This
mirrors "every helper is a named dependency hook whose contract Dependencies
states" (Build Prompt).
"""
from __future__ import annotations

from typing import Optional, List, Tuple, Dict, Any


# ---------------------------------------------------------------------------
# Fake Account (Module 01-owned shape; fields this module reads)
# ---------------------------------------------------------------------------
class Account:
    def __init__(self, account_id, customer_id=1, account_status=None,
                 revenue=None, profile_metadata=None):
        self.account_id = account_id
        self.customer_id = customer_id
        self.account_status = account_status
        self.revenue = revenue
        self.profile_metadata = profile_metadata
        # NOTE: intentionally NO `assigned_csm` and NO `arr` attribute/column.
        # Those live inside profile_metadata JSON (Gotcha 6).


# ---------------------------------------------------------------------------
# Dependency hooks (Modules 01/03/04/05/07). Tests assign these.
# Default to NotImplementedError so an un-stubbed path is loud, not silent.
# ---------------------------------------------------------------------------
def module01_accounts_for_customer(customer_id):
    raise NotImplementedError


def module03_read_scores(account_id):
    """-> (health_L3_or_None, pillar_scores, status)"""
    raise NotImplementedError


def module04_aggregate_revenue_with_provenance(customer_id):
    """-> {at_risk, protected, expansion, arr_basis, arr_basis_value}"""
    raise NotImplementedError


def module04_open_signals(customer_id):
    raise NotImplementedError


def module05_wizard_b_nrr(customer_id):
    raise NotImplementedError


def module05_predictor_v3_nrr(customer_id):
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Module 07 envelope() -- reconstructed FAITHFULLY to the signature the spec
# documents for it: envelope(scope, payload, arr_basis=, arr_basis_value=).
# See Dependencies (line ~80), Data Shapes (line ~105) and piece-5 note
# (line ~313) which quotes exactly `envelope(scope, payload, arr_basis=,
# arr_basis_value=)` -- i.e. NO `persona` parameter.
#
# This is the CONTRACT as the spec states it. Piece 5 nonetheless CALLS
# envelope(..., persona=persona, ...). `envelope` below is the module global
# build_dashboard uses; tests swap it to demonstrate the defect and the fix.
# ---------------------------------------------------------------------------
def envelope_documented(scope, payload, arr_basis=None, arr_basis_value=None):
    """The Module-07 contract as literally documented by this spec: no persona."""
    out = dict(payload)
    out["scope"] = scope
    out["arr_basis"] = arr_basis
    out["arr_basis_value"] = arr_basis_value
    return out


def envelope_with_persona(scope, payload, persona=None, arr_basis=None,
                          arr_basis_value=None):
    """The extended envelope piece 5 actually requires (the proposed fix)."""
    out = dict(payload)
    out["scope"] = scope
    out["persona"] = persona
    out["arr_basis"] = arr_basis
    out["arr_basis_value"] = arr_basis_value
    return out


# `envelope` is the name build_dashboard binds to at call time (module global).
# Default to the extended one so the non-envelope ACs can run; the defect test
# swaps in `envelope_documented` to prove the piece-5 call breaks under the
# documented contract.
envelope = envelope_with_persona


# ---------------------------------------------------------------------------
# PIECE 1 - account partition + per-account summary
# ---------------------------------------------------------------------------
def account_arr(acct) -> float:
    meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
    arr = meta.get("arr")
    if arr:                          # profile_metadata.arr wins when present
        return float(arr)
    return float(acct.revenue or 0)  # else the revenue column, else 0.0


def assigned_csm(acct):
    # assigned_csm is a KEY in the profile_metadata JSON, not a column (Gotcha 6).
    meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
    return meta.get("assigned_csm")


def partition_accounts(customer_id):
    active, churned = [], []
    for acct in module01_accounts_for_customer(customer_id):   # ALL statuses
        health_L3, pillars, status = module03_read_scores(acct.account_id)
        row = {"account_id": acct.account_id, "health_L3": health_L3,
               "arr": account_arr(acct), "status": acct.account_status,
               "pillars": pillars}
        if (acct.account_status or "").lower() == "churned":
            churned.append(row)
        else:
            active.append(row)
    return active, churned


# ---------------------------------------------------------------------------
# PIECE 2 - L4 revenue-weighted rollup
# ---------------------------------------------------------------------------
def rollup_L4(active_summaries) -> dict:
    scored = [a for a in active_summaries if a["health_L3"] is not None]
    n_no_data = len(active_summaries) - len(scored)
    if not scored:
        return {"health": None, "method": "no_scored_accounts",
                "n": len(active_summaries), "n_scored": 0,
                "n_zero_arr": 0, "n_no_data": n_no_data}
    total_arr = sum(a["arr"] for a in scored)
    n_zero_arr = sum(1 for a in scored if not a["arr"])
    if total_arr > 0:
        health = sum(a["health_L3"] * a["arr"] for a in scored) / total_arr
        method = "revenue_weighted"
    else:
        health = sum(a["health_L3"] for a in scored) / len(scored)
        method = "simple_unweighted"
    return {"health": round(health, 1), "method": method,
            "n": len(active_summaries), "n_scored": len(scored),
            "n_zero_arr": n_zero_arr, "n_no_data": n_no_data}


# ---------------------------------------------------------------------------
# PIECE 3 - single-source metric compile functions
# ---------------------------------------------------------------------------
def revenue_bundle(customer_id) -> dict:
    prov = module04_aggregate_revenue_with_provenance(customer_id)
    return {"revenue_at_risk": prov["at_risk"],
            "revenue_protected": prov["protected"],
            "expansion_pipeline": prov["expansion"],
            "arr_basis": prov["arr_basis"],
            "arr_basis_value": prov["arr_basis_value"]}


HEALTH_BANDS = [("critical", 0, 50), ("at_risk", 50, 70)]  # Config: Module 03 thresholds


def exposure_risk(active_summaries) -> dict:
    out = {band: 0.0 for band, _, _ in HEALTH_BANDS}
    for a in active_summaries:
        if a["health_L3"] is None:
            continue
        for band, lo, hi in HEALTH_BANDS:
            if lo <= a["health_L3"] < hi:
                out[band] += a["arr"]
    return out


# ---------------------------------------------------------------------------
# PIECE 4 - two-layer assembly
# ---------------------------------------------------------------------------
def build_layers(customer_id, active_summaries):
    trailing = {
        "portfolio_health": rollup_L4(active_summaries),
        "exposure_risk":    exposure_risk(active_summaries),
        "wizard_b_nrr":     module05_wizard_b_nrr(customer_id),
    }
    leading = {
        "signals":        module04_open_signals(customer_id),   # unfiltered by health
        "confirmed_risk": revenue_bundle(customer_id)["revenue_at_risk"],
        "predictor_nrr":  module05_predictor_v3_nrr(customer_id),
    }
    return trailing, leading


# ---------------------------------------------------------------------------
# PIECE 5 - persona lens + assembly
# ---------------------------------------------------------------------------
def scope_for(mode) -> str:
    return "platform" if mode == "portfolio_of_customers" else "portfolio"


def build_dashboard(customer_id, persona, mode="single_customer") -> dict:
    active, churned = partition_accounts(customer_id)
    trailing, leading = build_layers(customer_id, active)
    bundle = revenue_bundle(customer_id)          # single source
    churn = {"churned_count": len(churned),
             "churned_arr": sum(a["arr"] for a in churned)}
    tiles = persona_lens(persona, trailing, leading, bundle, churn, active, churned)
    payload = {"trailing": trailing, "leading": leading, "churn": churn,
               "mode": mode, **tiles}
    return envelope(scope_for(mode), payload, persona=persona,
                    arr_basis=bundle["arr_basis"],
                    arr_basis_value=bundle["arr_basis_value"])


def persona_lens(persona, trailing, leading, bundle, churn, active, churned):
    shared = {"revenue_at_risk": bundle["revenue_at_risk"],
              "revenue_protected": bundle["revenue_protected"],
              "expansion_pipeline": bundle["expansion_pipeline"]}
    if persona in ("cro", "cfo", "ceo"):
        return shared
    if persona == "vpcs":
        return {"portfolio_health": trailing["portfolio_health"], **shared}
    if persona == "csm":
        return {"accounts": active, **shared}
    raise ValueError(f"unknown persona: {persona}")


# ---------------------------------------------------------------------------
# PIECE 6 - parity checks
# ---------------------------------------------------------------------------
SHARED_METRICS = ("revenue_at_risk", "revenue_protected", "expansion_pipeline")


def assert_persona_parity(customer_id):
    payloads = {p: build_dashboard(customer_id, p) for p in ("cro", "cfo", "ceo")}
    for m in SHARED_METRICS:
        vals = {p: payloads[p][m] for p in payloads}
        if len(set(vals.values())) > 1:
            raise AssertionError(f"persona parity drift on {m}: {vals}")


def assert_surface_parity(customer_id, persona, mcp_call, flask_call):
    a, b = mcp_call(customer_id, persona), flask_call(customer_id, persona)
    for m in SHARED_METRICS:
        if a[m] != b[m]:
            raise AssertionError(f"surface parity drift on {m}: mcp={a[m]} flask={b[m]}")
