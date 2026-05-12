#!/usr/bin/env python3
"""Sanity check harness for cust 333 — captures key dashboard + API + Ask AI
numbers to a JSON snapshot for before/after deploy comparison.

Usage:
    python3 scripts/sanity_check_cust333.py <output.json>

Captures:
  - Authentication round-trip
  - CFO dashboard (12 anchor numbers + 3 lens blocks + investment allocation)
  - CRO dashboard (revenue cards + metrics)
  - CEO dashboard (portfolio summary)
  - VP CS / CSM API surfaces (csm-scorecard, daily-actions, team-capacity)
  - Predictor v3 endpoints (account NRR, top expansion, top at-risk)
  - Ask AI: 2 canonical NRR questions (verifies tool dispatch works)
  - Admin endpoints: post-load-attribution (idempotent)
  - Frontend bundle hash (verifies build deploy succeeded)
"""
import argparse
import json
import subprocess
import sys
import time
from typing import Any, Dict, Optional

import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://3.94.106.197"
CUST_ID = 333
EMAIL = "admin@predictor-v3-demo.io"
PASSWORD = "DemoCust395!"


def _make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def _login(opener) -> bool:
    req = urllib.request.Request(
        f"{BASE_URL}/api/login",
        data=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = opener.open(req, timeout=15)
        return resp.status == 200
    except Exception as e:
        print(f"  login failed: {e}", file=sys.stderr)
        return False


def _api_get(opener, path: str, timeout: int = 90) -> Optional[Dict[str, Any]]:
    try:
        resp = opener.open(f"{BASE_URL}{path}", timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)[:200]}


def _api_post(opener, path: str, body: dict, timeout: int = 90) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = opener.open(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)[:200]}


def _frontend_bundle() -> str:
    """Extract main.<hash>.js from the served index.html."""
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}/", timeout=10)
        html = resp.read().decode()
        import re
        m = re.search(r"main\.[a-f0-9]+\.js", html)
        return m.group(0) if m else "(not found)"
    except Exception as e:
        return f"(error: {e})"


def run_checks() -> dict:
    opener, cj = _make_opener()

    snapshot: Dict[str, Any] = {
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "base_url": BASE_URL,
        "customer_id": CUST_ID,
        "frontend_bundle": _frontend_bundle(),
    }

    # ─── Auth ───
    if not _login(opener):
        snapshot["auth"] = "FAILED"
        return snapshot
    snapshot["auth"] = "ok"

    # ─── CFO dashboard ───
    cfo = _api_get(opener, f"/api/executive/cfo-dashboard?customer_id={CUST_ID}")
    if cfo and "_error" not in cfo:
        proof = cfo.get("proof_data") or {}
        wb = cfo.get("wizard_b_nrr") or {}
        v3 = cfo.get("predictor_v3_portfolio_nrr") or {}
        ha = cfo.get("historical_actuals") or {}
        ls = cfo.get("layered_story") or {}
        snapshot["cfo"] = {
            "total_arr": cfo.get("total_arr"),
            "account_count": cfo.get("account_count"),
            # proof_data (Row C — Realized)
            "proof_revenue_protected": proof.get("revenue_protected"),
            "proof_revenue_expanded": proof.get("revenue_expanded"),
            "proof_total_cost": proof.get("total_cost"),
            "proof_realized_roi": proof.get("realized_roi"),
            "proof_executions_total": proof.get("executions_total"),
            "proof_executions_resolved": proof.get("executions_resolved"),
            # wizard_b_nrr (Row B — Counterfactual)
            "wb_with_cs_pulse_nrr_pct": wb.get("with_cs_pulse_nrr_pct"),
            "wb_without_cs_pulse_nrr_pct": wb.get("without_cs_pulse_nrr_pct"),
            "wb_delta_pct": wb.get("delta_pct"),
            "wb_arr_protected": wb.get("arr_protected"),
            "wb_accounts_saved": wb.get("accounts_saved"),
            "wb_lens": wb.get("lens"),
            "wb_engine": wb.get("engine"),
            # predictor_v3_portfolio_nrr (Forecast NRR — Next 12mo)
            "v3_arr_weighted_nrr_pct": v3.get("arr_weighted_nrr_pct"),
            "v3_simple_avg_nrr_pct": v3.get("simple_avg_nrr_pct"),
            "v3_account_count": v3.get("account_count"),
            "v3_active_account_count": v3.get("active_account_count"),
            "v3_lens": v3.get("lens"),
            "v3_engine": v3.get("engine"),
            "v3_method_counts": v3.get("prediction_method_counts"),
            # historical_actuals (Row A — Historical Performance)
            "ha_historical_nrr_pct_ttm": ha.get("historical_nrr_pct_ttm"),
            "ha_arr_churned": ha.get("arr_churned"),
            "ha_arr_expanded": ha.get("arr_expanded"),
            "ha_arr_contracted": ha.get("arr_contracted"),
            "ha_starting_arr_ttm": ha.get("starting_arr_ttm"),
            # Layered story
            "ls_blended_roi": ls.get("blended_roi"),
            "ls_total_value": ls.get("total_value"),
            "ls_layer_names": [L.get("name") for L in (ls.get("layers") or [])],
            "ls_layer_values": [L.get("value") for L in (ls.get("layers") or [])],
            "ls_layer_rois":   [L.get("roi") for L in (ls.get("layers") or [])],
        }
    else:
        snapshot["cfo"] = {"_error": (cfo or {}).get("_error", "no response")}

    # ─── CRO dashboard ───
    cro = _api_get(opener, f"/api/executive/cro-dashboard?customer_id={CUST_ID}")
    if cro and "_error" not in cro:
        snapshot["cro"] = {
            "total_arr": cro.get("total_arr"),
            "revenue_at_risk": cro.get("revenue_at_risk"),
            "revenue_protected": cro.get("revenue_protected"),
            "expansion_pipeline": cro.get("expansion_pipeline"),
            "accounts_at_risk_count": cro.get("accounts_at_risk_count"),
            "nrr_pct": cro.get("nrr_pct"),
            "grr_pct": cro.get("grr_pct"),
            "playbook_roi_pct": cro.get("playbook_roi_pct"),
        }
    else:
        snapshot["cro"] = {"_error": (cro or {}).get("_error", "no response")}

    # ─── CEO dashboard ───
    ceo = _api_get(opener, f"/api/executive/ceo-dashboard?customer_id={CUST_ID}")
    if ceo and "_error" not in ceo:
        snapshot["ceo"] = {
            "total_arr": ceo.get("total_arr"),
            "avg_health_score": ceo.get("avg_health_score"),
            "portfolio_nrr": ceo.get("portfolio_nrr"),
            "total_accounts": ceo.get("total_accounts"),
            "total_at_risk": ceo.get("total_at_risk"),
        }
    else:
        snapshot["ceo"] = {"_error": (ceo or {}).get("_error", "no response")}

    # ─── VP CS / CSM endpoints ───
    for path, key in [
        (f"/api/v1/csm-scorecard?customer_id={CUST_ID}", "csm_scorecard"),
        (f"/api/v1/daily-actions?customer_id={CUST_ID}",  "daily_actions"),
        (f"/api/v1/health-summary?customer_id={CUST_ID}", "health_summary"),
        (f"/api/v1/team-capacity?customer_id={CUST_ID}",  "team_capacity"),
        (f"/api/v1/playbook-success-metrics?customer_id={CUST_ID}", "playbook_success_metrics"),
    ]:
        resp = _api_get(opener, path)
        if resp and "_error" not in resp:
            # capture top-level numeric/list-length fingerprint
            keys = list(resp.keys()) if isinstance(resp, dict) else []
            snapshot[key] = {
                "ok": True,
                "top_keys": sorted(keys)[:15],
                # Capture a few specific numeric fields if present:
                "totals": {k: resp.get(k) for k in ['total_accounts', 'total_arr', 'avg_health', 'count', 'total', 'team_total'] if k in (resp if isinstance(resp, dict) else {})},
            }
        else:
            snapshot[key] = {"_error": (resp or {}).get("_error", "no response")}

    # ─── Predictor v3 endpoints ───
    v3_top_exp = _api_get(opener, f"/api/v1/predictor/customer/{CUST_ID}/top-expansion-opportunities?horizon=12mo&limit=5")
    v3_top_risk = _api_get(opener, f"/api/v1/predictor/customer/{CUST_ID}/top-at-risk-accounts?horizon=12mo&limit=5")

    def _summ_v3(r):
        if not r or "_error" in (r or {}):
            return {"_error": (r or {}).get("_error", "no response")}
        results = r.get("results") or []
        return {
            "count": len(results),
            "top_5_account_names": [x.get("account_name") for x in results[:5]],
            "top_5_arrs": [x.get("arr") for x in results[:5]],
            "top_5_expansion_lifts": [(x.get("expansion_outlook") or {}).get("expected_arr_lift") for x in results[:5]],
            "top_5_nrr_points": [(x.get("expected_nrr") or {}).get("point") for x in results[:5]],
        }
    snapshot["v3_top_expansion"] = _summ_v3(v3_top_exp)
    snapshot["v3_top_at_risk"] = _summ_v3(v3_top_risk)

    # Per-account: Antares Holdings (acct 3207)
    v3_antares = _api_get(opener, f"/api/v1/predictor/account/3207/nrr-forecast?horizon=12mo")
    if v3_antares and "_error" not in v3_antares:
        en = v3_antares.get("expected_nrr") or {}
        td = v3_antares.get("term_decomposition") or {}
        eo = v3_antares.get("expansion_outlook") or {}
        snapshot["v3_antares"] = {
            "prediction_method": v3_antares.get("prediction_method"),
            "calibration_id": v3_antares.get("calibration_id"),
            "expected_nrr_point": en.get("point"),
            "p_churn_at_horizon": td.get("p_churn_at_horizon"),
            "p_survive_at_horizon": td.get("p_survive_at_horizon"),
            "e_expand_pct_given_survive": td.get("e_expand_pct_given_survive"),
            "expansion_expected_arr_lift": eo.get("expected_arr_lift"),
            "top_drivers_count": len(td.get("top_drivers") or []),
        }
    else:
        snapshot["v3_antares"] = {"_error": (v3_antares or {}).get("_error", "no response")}

    # ─── Ask AI: 2 canonical NRR questions ───
    askai_q1 = _api_post(opener, "/api/executive/ask-v2", {
        "query": "What is our portfolio NRR forecast for the next 12 months?",
        "persona": "cfo",
    }, timeout=90)
    snapshot["askai_portfolio_nrr"] = {
        "tools_called": (askai_q1 or {}).get("tools_called", []),
        "response_first_300": ((askai_q1 or {}).get("response") or "")[:300],
        "has_100_5": "100.5" in ((askai_q1 or {}).get("response") or ""),
        "has_88_5": "88.5" in ((askai_q1 or {}).get("response") or ""),
    }

    askai_q2 = _api_post(opener, "/api/executive/ask-v2", {
        "query": "Why is Antares Holdings forecast at 102% NRR over the next 12 months? Use the Predictor v3 explanation with drivers.",
        "persona": "cfo",
    }, timeout=90)
    snapshot["askai_antares"] = {
        "tools_called": (askai_q2 or {}).get("tools_called", []),
        "response_first_300": ((askai_q2 or {}).get("response") or "")[:300],
        "has_102_1": "102.1" in ((askai_q2 or {}).get("response") or ""),
    }

    # ─── Admin endpoints (idempotent) ───
    pla = _api_post(opener, "/api/admin/post-load-attribution", {"customer_id": CUST_ID})
    snapshot["admin_post_load_attribution"] = {
        "status": (pla or {}).get("status"),
        "executions_updated": (pla or {}).get("executions_updated"),
        "total_revenue_protected": (pla or {}).get("total_revenue_protected"),
        "total_cs_investment": (pla or {}).get("total_cs_investment"),
        "realized_roi_multiplier": (pla or {}).get("realized_roi_multiplier"),
    }

    return snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="Path to save snapshot JSON")
    args = parser.parse_args()

    print(f"Running sanity check against {BASE_URL} (cust {CUST_ID})...")
    snap = run_checks()

    with open(args.output, "w") as f:
        json.dump(snap, f, indent=2, default=str)

    print(f"\nSnapshot written to: {args.output}")
    print(f"Frontend bundle: {snap.get('frontend_bundle')}")
    print(f"Auth: {snap.get('auth')}")
    print(f"CFO total_arr: {(snap.get('cfo') or {}).get('total_arr')}")
    print(f"v3 portfolio NRR: {(snap.get('cfo') or {}).get('v3_arr_weighted_nrr_pct')}%")
    print(f"Wizard B NRR: {(snap.get('cfo') or {}).get('wb_with_cs_pulse_nrr_pct')}%")
    print(f"Realized ROI: {(snap.get('cfo') or {}).get('proof_realized_roi')}x")
    print(f"Antares NRR forecast: {(snap.get('v3_antares') or {}).get('expected_nrr_point')}")
    print(f"Ask AI Q1 tools: {(snap.get('askai_portfolio_nrr') or {}).get('tools_called')}")
    print(f"Ask AI Q2 tools: {(snap.get('askai_antares') or {}).get('tools_called')}")


if __name__ == "__main__":
    main()
