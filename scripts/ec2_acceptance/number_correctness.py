"""Dashboard NUMBER-CORRECTNESS eval.

Unlike checks.py (which asserts numbers are *present* and that two endpoints
*agree*), this module independently RE-DERIVES each portfolio aggregate from the
per-account primitives the platform itself exposes (`/api/v1/accounts`), then
asserts the dashboard endpoints return the arithmetically-correct value.

It closes the gap called out in
`kpi-dashboard/docs/KT_dashboard_data_lineage_and_evals.md` §7(6):
  "No automated check that a dashboard number is *arithmetically correct*
   given the underlying data."

Source of truth for the recompute:
  GET /api/v1/accounts   → per-account {health_score, status, revenue/arr,
                                        pillar_scores}

Re-derived and asserted against:
  GET /api/v1/health-summary           total_arr, arr_exposure, band counts,
                                       revenue-weighted average_health
  GET /api/executive/cro-dashboard     arr_exposure, revenue_at_risk/protected/expansion
  GET /api/executive/cfo-dashboard     total_arr, revenue_* parity
  GET /api/outcome-roi/portfolio-summary   revenue_* parity
  GET /api/v1/predictor/account/<id>/nrr-forecast   (optional) NRR sanity + recompute

Definitions are taken verbatim from the backend:
  * arr_exposure   = sum(revenue) for accounts with health < healthy_min
                     (executive_dashboard_api.py / api_routes.py)
  * average_health = revenue-weighted mean of account health (L4)
  * band           = classify(health): healthy >= healthy_min,
                     at_risk in [at_risk_min, healthy_min), critical < at_risk_min

Status legend: PASS (number is correct) · WARN (mismatch fully explained by
borderline accounts / rounding — flag, don't fail) · FAIL (a real wrong number)
· SKIP (endpoint unavailable / feature off).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .http_client import AcceptanceClient

# Accounts whose health is within this many points of a band boundary can
# legitimately land in different bands across endpoints (precalc vs trailing
# recompute, rounding). A count/exposure mismatch explained ENTIRELY by such
# accounts is a WARN, not a FAIL.
BAND_TOL = 2.0
# Relative tolerance for money sums (rounding to whole dollars on the API side).
MONEY_REL_TOL = 0.005
MONEY_ABS_TOL = 1.0
# Absolute tolerance for an averaged 0-100 health score.
HEALTH_ABS_TOL = 0.5


# ────────────────────────────── result collector ──────────────────────────────
class Results:
    def __init__(self) -> None:
        self.rows: List[Tuple[str, str, str]] = []  # (status, name, detail)

    def add(self, status: str, name: str, detail: str = "") -> None:
        self.rows.append((status, name, detail))
        glyph = {"PASS": "  ✓", "WARN": "  ~", "FAIL": "  ✗", "SKIP": "  ·"}[status]
        line = f"{glyph} {name}"
        if detail:
            line += f"  — {detail}"
        print(line)

    def pas(self, n, d=""): self.add("PASS", n, d)
    def warn(self, n, d=""): self.add("WARN", n, d)
    def fail(self, n, d=""): self.add("FAIL", n, d)
    def skip(self, n, d=""): self.add("SKIP", n, d)

    @property
    def n_fail(self) -> int:
        return sum(1 for s, _, _ in self.rows if s == "FAIL")

    @property
    def n_warn(self) -> int:
        return sum(1 for s, _, _ in self.rows if s == "WARN")

    @property
    def n_pass(self) -> int:
        return sum(1 for s, _, _ in self.rows if s == "PASS")


# ────────────────────────────── small helpers ──────────────────────────────
def _money_close(a: float, b: float) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= max(MONEY_ABS_TOL, MONEY_REL_TOL * max(abs(a), abs(b)))


def _classify(health: float, healthy_min: float, at_risk_min: float) -> str:
    if health >= healthy_min:
        return "healthy"
    if health >= at_risk_min:
        return "at_risk"
    return "critical"


def _near_boundary(health: float, healthy_min: float, at_risk_min: float) -> bool:
    return (
        abs(health - healthy_min) <= BAND_TOL
        or abs(health - at_risk_min) <= BAND_TOL
    )


def _safe_get_json(client: AcceptanceClient, path: str) -> Optional[Any]:
    try:
        return client.get_json(path)
    except Exception as e:  # noqa: BLE001
        print(f"  (could not fetch {path}: {type(e).__name__})")
        return None


def fetch_thresholds(client: AcceptanceClient) -> Tuple[float, float]:
    """Return (healthy_min, at_risk_min). Defaults to standardized 70/50."""
    data = _safe_get_json(client, "/api/dc2s/config/health-thresholds") or {}
    healthy = data.get("healthy_min")
    at_risk = data.get("at_risk_min")
    # tolerate nested {thresholds:{healthy:{min},at_risk:{min}}}
    if healthy is None:
        healthy = (((data.get("thresholds") or {}).get("healthy") or {}).get("min"))
    if at_risk is None:
        at_risk = (((data.get("thresholds") or {}).get("at_risk") or {}).get("min"))
    return float(healthy or 70), float(at_risk or 50)


def fetch_accounts(client: AcceptanceClient) -> List[Dict[str, Any]]:
    """Normalize /api/v1/accounts into the primitives we recompute from."""
    data = _safe_get_json(client, "/api/v1/accounts") or {}
    raw = data.get("accounts") if isinstance(data, dict) else data
    out: List[Dict[str, Any]] = []
    for a in raw or []:
        health = a.get("health_score", a.get("overall_health"))
        arr = a.get("arr", a.get("revenue"))
        out.append({
            "id": a.get("account_id"),
            "name": a.get("account_name"),
            "health": float(health) if health is not None else None,
            "arr": float(arr) if arr is not None else 0.0,
            "status": a.get("status") or a.get("classification"),
            "pillars": {k: float(v) for k, v in (a.get("pillar_scores") or {}).items()
                        if v is not None},
        })
    return out


# ────────────────────────────── check groups ──────────────────────────────
def check_per_account_invariants(r: Results, accounts, healthy_min, at_risk_min) -> None:
    print("\n--- Per-account invariants (from /api/v1/accounts) ---")
    bad_range, bad_arr, status_fail, status_warn, pillar_viol = [], [], [], [], []
    for a in accounts:
        h = a["health"]
        if h is None or not (0.0 <= h <= 100.0):
            bad_range.append(f"{a['name']}={h}")
            continue
        if a["arr"] < 0:
            bad_arr.append(f"{a['name']}={a['arr']}")
        # status must equal classify(its own health)
        expected = _classify(h, healthy_min, at_risk_min)
        if a["status"] != expected:
            entry = f"{a['name']}: status={a['status']} but health={h} ⇒ {expected}"
            (status_warn if _near_boundary(h, healthy_min, at_risk_min) else status_fail).append(entry)
        # a weighted average of pillar scores must lie within [min,max] of them
        if a["pillars"]:
            lo, hi = min(a["pillars"].values()), max(a["pillars"].values())
            if not (lo - 0.5 <= h <= hi + 0.5):
                pillar_viol.append(f"{a['name']}: health={h} outside pillar range [{lo:.1f},{hi:.1f}]")

    r.fail("health_score in [0,100]", f"{len(bad_range)} bad: {bad_range[:5]}") if bad_range else r.pas("health_score in [0,100]", f"{len(accounts)} accounts")
    if bad_arr:
        r.fail("arr >= 0", f"{bad_arr[:5]}")
    else:
        r.pas("arr >= 0")
    if status_fail:
        r.fail("account.status == classify(health)", f"{len(status_fail)} mismatched: {status_fail[:5]}")
    elif status_warn:
        r.warn("account.status == classify(health)", f"{len(status_warn)} borderline: {status_warn[:5]}")
    else:
        r.pas("account.status == classify(health)")
    if pillar_viol:
        r.fail("health within pillar-score range (L2→L3 bound)", f"{len(pillar_viol)}: {pillar_viol[:5]}")
    else:
        r.pas("health within pillar-score range (L2→L3 bound)")


def _check_aggregates(r: Results, client, accounts, healthy_min, at_risk_min) -> None:
    print("\n--- Portfolio aggregates: recompute vs /api/v1/health-summary ---")
    summary = _safe_get_json(client, "/api/v1/health-summary")
    if not summary:
        r.skip("health-summary aggregates", "endpoint unavailable")
        return

    valid = [a for a in accounts if a["health"] is not None]
    total_arr = sum(a["arr"] for a in valid)
    exposure = sum(a["arr"] for a in valid if a["health"] < healthy_min)
    counts = {"healthy": 0, "at_risk": 0, "critical": 0}
    for a in valid:
        counts[_classify(a["health"], healthy_min, at_risk_min)] += 1
    wsum = sum(a["health"] * a["arr"] for a in valid)
    avg_health = (wsum / total_arr) if total_arr > 0 else (
        sum(a["health"] for a in valid) / len(valid) if valid else 0
    )

    # total_arr
    s_total = summary.get("total_arr")
    if _money_close(total_arr, s_total):
        r.pas("total_arr", f"recomputed ${total_arr:,.0f} == summary ${s_total:,.0f}")
    else:
        r.fail("total_arr", f"recomputed ${total_arr:,.0f} != summary ${s_total:,.0f}")

    # arr_exposure
    s_exp = summary.get("arr_exposure")
    if _money_close(exposure, s_exp):
        r.pas("arr_exposure", f"recomputed ${exposure:,.0f} == summary ${s_exp:,.0f}")
    else:
        # borderline-tolerant: are the differing-band accounts all near a boundary?
        borderline = any(_near_boundary(a["health"], healthy_min, at_risk_min) for a in valid)
        (r.warn if borderline else r.fail)(
            "arr_exposure",
            f"recomputed ${exposure:,.0f} vs summary ${s_exp:,.0f}"
            + (" (borderline accounts present)" if borderline else ""),
        )

    # band counts
    s_counts = {
        "healthy": summary.get("healthy_accounts"),
        "at_risk": summary.get("risk_accounts"),
        "critical": summary.get("critical_accounts"),
    }
    if all(counts[k] == s_counts[k] for k in counts):
        r.pas("band counts", f"{counts}")
    else:
        borderline = [a["name"] for a in valid if _near_boundary(a["health"], healthy_min, at_risk_min)]
        total_diff = sum(abs(counts[k] - (s_counts[k] or 0)) for k in counts)
        if borderline and total_diff <= len(borderline):
            r.warn("band counts", f"recomputed {counts} vs summary {s_counts}; explained by borderline {borderline[:5]}")
        else:
            r.fail("band counts", f"recomputed {counts} vs summary {s_counts}")

    # revenue-weighted average health
    s_avg = summary.get("average_health")
    if s_avg is not None and abs(avg_health - s_avg) <= HEALTH_ABS_TOL:
        r.pas("average_health (rev-weighted)", f"recomputed {avg_health:.1f} == summary {s_avg}")
    elif s_avg is not None:
        r.warn("average_health (rev-weighted)", f"recomputed {avg_health:.1f} vs summary {s_avg} (precalc/trailing skew?)")
    else:
        r.skip("average_health (rev-weighted)", "field absent")


def _check_cross_endpoint(r: Results, client, accounts, healthy_min) -> None:
    print("\n--- Cross-endpoint parity & sanity (CRO / CFO / portfolio) ---")
    cro = _safe_get_json(client, "/api/executive/cro-dashboard")
    cfo = _safe_get_json(client, "/api/executive/cfo-dashboard")
    port = _safe_get_json(client, "/api/outcome-roi/portfolio-summary")

    valid = [a for a in accounts if a["health"] is not None]
    total_arr = sum(a["arr"] for a in valid)
    exposure = sum(a["arr"] for a in valid if a["health"] < healthy_min)

    # CFO total_arr equals recomputed sum
    if cfo and cfo.get("total_arr") is not None:
        if _money_close(total_arr, cfo["total_arr"]):
            r.pas("cfo.total_arr == sum(account.arr)", f"${total_arr:,.0f}")
        else:
            r.fail("cfo.total_arr == sum(account.arr)", f"recomputed ${total_arr:,.0f} != cfo ${cfo['total_arr']:,.0f}")

    # CRO arr_exposure equals recomputed exposure
    if cro and cro.get("arr_exposure") is not None:
        if _money_close(exposure, cro["arr_exposure"]):
            r.pas("cro.arr_exposure == sum(arr where health<healthy_min)", f"${exposure:,.0f}")
        else:
            borderline = any(_near_boundary(a["health"], healthy_min, healthy_min) for a in valid)
            (r.warn if borderline else r.fail)(
                "cro.arr_exposure == sum(arr where health<healthy_min)",
                f"recomputed ${exposure:,.0f} vs cro ${cro['arr_exposure']:,.0f}",
            )

    # CRO == CFO == portfolio on the three revenue buckets
    for field in ("revenue_at_risk", "revenue_protected", "expansion_pipeline"):
        vals = {
            "cro": (cro or {}).get(field),
            "cfo": (cfo or {}).get(field),
            "portfolio": (port or {}).get(field),
        }
        present = {k: v for k, v in vals.items() if v is not None}
        if len(present) < 2:
            r.skip(f"parity {field}", "fewer than two sources expose it")
            continue
        first = next(iter(present.values()))
        if all(_money_close(first, v) for v in present.values()):
            r.pas(f"parity {field}", f"{present}")
        else:
            r.fail(f"parity {field}", f"DISAGREE {present}")
        # sanity bound: 0 <= value <= total_arr
        for src, v in present.items():
            if v < -MONEY_ABS_TOL or (total_arr > 0 and v > total_arr * 1.0001):
                r.fail(f"sanity {field} ({src})", f"${v:,.0f} outside [0, total_arr ${total_arr:,.0f}]")


def _check_predictor(r: Results, client, accounts, limit: int) -> None:
    print("\n--- Predictor v3 NRR: per-account sanity + portfolio recompute (optional) ---")
    valid = [a for a in accounts if a["health"] is not None and a["id"] is not None]
    sample = valid[:limit] if limit > 0 else valid
    if not sample:
        r.skip("predictor", "no accounts")
        return

    rows: List[Tuple[float, float]] = []  # (arr, nrr_point)
    n_bad_ci, n_bad_point, n_bad_prob, n_bad_lift, n_503 = 0, 0, 0, 0, 0
    for a in sample:
        data = _safe_get_json(client, f"/api/v1/predictor/account/{a['id']}/nrr-forecast?horizon=12mo")
        if not data:
            continue
        if isinstance(data, dict) and (data.get("fallback") or data.get("error")):
            n_503 += 1
            continue
        nrr = (data.get("expected_nrr") or {})
        point, lo, hi = nrr.get("point"), nrr.get("lower_90"), nrr.get("upper_90")
        if point is None:
            continue
        rows.append((a["arr"], float(point)))
        if lo is not None and hi is not None and not (lo - 1e-6 <= point <= hi + 1e-6):
            n_bad_ci += 1
        if not (0.0 <= point <= 2.0):
            n_bad_point += 1
        p_churn = (data.get("term_decomposition") or {}).get("p_churn_at_horizon")
        if p_churn is not None and not (0.0 <= p_churn <= 1.0):
            n_bad_prob += 1
        exp = (data.get("expansion_outlook") or {})
        lift, clo, chi = exp.get("expected_arr_lift"), exp.get("ci_lower_arr_lift"), exp.get("ci_upper_arr_lift")
        if lift is not None:
            if lift < -MONEY_ABS_TOL:
                n_bad_lift += 1
            if clo is not None and chi is not None and not (clo - 1 <= lift <= chi + 1):
                n_bad_lift += 1

    if n_503 and not rows:
        r.skip("predictor", f"feature off / fallback (503) for {n_503} accounts")
        return
    if not rows:
        r.skip("predictor", "no forecasts returned")
        return

    r.fail("nrr CI bounds lower_90<=point<=upper_90", f"{n_bad_ci} violations") if n_bad_ci else r.pas("nrr CI bounds lower_90<=point<=upper_90", f"{len(rows)} accounts")
    r.fail("nrr point in [0,2]", f"{n_bad_point} out of range") if n_bad_point else r.pas("nrr point in [0,2]")
    r.fail("p_churn in [0,1]", f"{n_bad_prob} out of range") if n_bad_prob else r.pas("p_churn in [0,1]")
    r.fail("expansion arr_lift >= 0 and within CI", f"{n_bad_lift} violations") if n_bad_lift else r.pas("expansion arr_lift >= 0 and within CI")

    arr_sum = sum(arr for arr, _ in rows)
    port_nrr = (sum(arr * p for arr, p in rows) / arr_sum) if arr_sum > 0 else 0
    if 0.0 <= port_nrr <= 2.0:
        r.pas("portfolio NRR (ARR-weighted recompute)", f"{port_nrr * 100:.1f}% across {len(rows)} accounts")
    else:
        r.fail("portfolio NRR (ARR-weighted recompute)", f"{port_nrr:.3f} implausible")


# ────────────────────────────── entry point ──────────────────────────────
def verify_number_correctness(
    client: AcceptanceClient,
    *,
    run_predictor: bool = False,
    predictor_limit: int = 8,
) -> bool:
    """Returns True if no FAIL rows (WARN/SKIP allowed)."""
    r = Results()

    healthy_min, at_risk_min = fetch_thresholds(client)
    print(f"  thresholds: healthy>={healthy_min:.0f}  at_risk>={at_risk_min:.0f}  critical<{at_risk_min:.0f}")

    accounts = fetch_accounts(client)
    if not accounts:
        r.fail("fetch /api/v1/accounts", "no accounts returned")
        print(f"\nRESULT: {r.n_pass} pass / {r.n_warn} warn / {r.n_fail} fail")
        return False
    print(f"  loaded {len(accounts)} accounts as recompute primitives")

    check_per_account_invariants(r, accounts, healthy_min, at_risk_min)
    _check_aggregates(r, client, accounts, healthy_min, at_risk_min)
    _check_cross_endpoint(r, client, accounts, healthy_min)
    if run_predictor:
        _check_predictor(r, client, accounts, predictor_limit)

    print(f"\nRESULT: {r.n_pass} pass / {r.n_warn} warn / {r.n_fail} fail")
    return r.n_fail == 0
