#!/usr/bin/env python3
"""
benchmark_manifest_generator.py  —  Recommendation #1 (benchmark-anchored data).

Emit a v2.0 load-driver manifest whose SYNTHETIC BEHAVIOR is calibrated to
published 2026 B2B SaaS benchmarks (load-driver/benchmarks.json), so every
aggregate number a demo shows is defensible ("our SMB cohort runs 97% NRR,
matching ChartMogul") even though the rows are generated.

What this DOES:  the portfolio's ARR-weighted NRR, gross churn, expansion and
contraction reproduce the benchmark distributions by segment (enterprise /
mid-market / SMB), realised through discrete per-account lifecycle events using
the real manifest vocabulary (expand / contract / churn / renew).

What this does NOT do:  it does not make any single account's OUTCOME or the
"what CS Pulse would have saved" COUNTERFACTUAL real. That layer is inherently
model-generated (Wizard B / Wizard D) and is out of scope here. See
README_real_data.md for the honest-claim boundary.

Pair with firmographics_overlay.py (#2) to drape REAL company identities
(names, industries, sizes) over the calibrated behaviour layer.

Usage:
    python3 generators/benchmark_manifest_generator.py \
        --accounts 40 --name "Acme Portfolio" --domain acme.io \
        --seed 42 --out manifests/generated_calibrated_saas.json

Deterministic for a given --seed.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BENCHMARKS = os.path.normpath(os.path.join(HERE, "..", "benchmarks.json"))

# Starter-9 KPI codes (canonical default per onboarding contract).
STARTER_9 = ["P1-KPI1", "P1-KPI2", "P1-KPI4", "P2-KPI1", "P2-KPI3",
             "P3-KPI1", "P3-KPI3", "P5-KPI1", "P5-KPI5"]

# Neutral placeholder identity pools. firmographics_overlay.py replaces these
# with real companies; kept readable so a manifest is legible pre-overlay.
_NAME_A = ["Polaris", "Vega", "Altair", "Orion", "Lyra", "Draco", "Cygnus",
           "Aquila", "Corvus", "Pyxis", "Carina", "Dorado", "Tucana", "Volans",
           "Mensa", "Norma", "Antlia", "Fornax", "Caelum", "Reticulum",
           "Hydrus", "Grus", "Pavo", "Indus", "Lupus", "Ara", "Crux", "Vela"]
_NAME_B = ["Cloud", "Systems", "Software", "Labs", "Networks", "Analytics",
           "Platform", "Digital", "Technologies", "Data", "Works", "Logic"]
_INDUSTRIES = ["SaaS", "FinTech", "HealthTech", "MarTech", "DevTools",
               "Cybersecurity", "E-commerce", "Logistics", "InsurTech", "EdTech"]
_REGIONS = ["US", "EU", "APAC", "UK", "LATAM"]


def _load_benchmarks(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _segment_counts(total: int, mix: Dict[str, float]) -> Dict[str, int]:
    """Largest-remainder apportionment so counts sum exactly to `total`."""
    raw = {k: total * v for k, v in mix.items()}
    counts = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(counts.values())
    frac = sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)
    for i in range(remainder):
        counts[frac[i % len(frac)]] += 1
    return counts


def _sample_arr(rng: random.Random, band: Dict[str, float]) -> int:
    """Log-uniform ARR within the segment band (realistic long tail)."""
    import math
    lo, hi = band["min"], band["max"]
    v = math.exp(rng.uniform(math.log(lo), math.log(hi)))
    # Round to a clean-ish figure.
    step = 10000 if v < 1_000_000 else 100000
    return int(round(v / step) * step)


def _scaled_deltas(rng: random.Random, arrs: List[int], target_dollars: float,
                   mag: Dict[str, float]) -> List[float]:
    """Sample raw per-account delta_pct, then scale so sum(arr*delta) == target_dollars."""
    if not arrs or target_dollars <= 0:
        return [0.0] * len(arrs)
    raw = [rng.uniform(mag["min"], mag["max"]) for _ in arrs]
    achieved = sum(a * r / 100.0 for a, r in zip(arrs, raw))
    factor = (target_dollars / achieved) if achieved > 0 else 1.0
    out = []
    for r in raw:
        scaled = r * factor
        out.append(max(3.0, min(60.0, scaled)))  # clamp to plausible band
    return out


def _health(rng: random.Random, classification: str) -> int:
    return {
        "healthy": rng.randint(72, 90),
        "at_risk": rng.randint(52, 68),
        "critical": rng.randint(28, 49),
    }[classification]


def _build_segment_accounts(rng: random.Random, seg_key: str, seg: Dict[str, Any],
                            n: int, bench: Dict[str, Any], months: int) -> List[Dict[str, Any]]:
    if n <= 0:
        return []
    arcs = bench["story_arc_by_role"]
    mags = bench["lifecycle_magnitudes"]

    arrs = sorted((_sample_arr(rng, seg["arr_band"]) for _ in range(n)), reverse=True)
    seg_arr = sum(arrs)

    # --- role assignment driven by benchmark $ targets ---
    target_churn = seg["gross_revenue_churn_annual"] * seg_arr
    target_contract = seg["contraction_rate"] * seg_arr
    target_expand = seg["expansion_rate"] * seg_arr

    roles = ["stable"] * n
    idx_by_arr_asc = sorted(range(n), key=lambda i: arrs[i])  # churn hits small first
    idx_by_arr_desc = list(reversed(idx_by_arr_asc))          # expansion favours large

    # Churn: hit the revenue-churn DOLLAR target (drives NRR) while keeping the
    # churn COUNT near the logo-churn target (drives the health-band mix). Select
    # accounts nearest the IDEAL average churned size = churn$ / logo_count, not
    # smallest-first — smallest-first maximised the logo count and inflated the
    # critical band. Nearest-to-average satisfies both $ and count at once.
    logo_count = max(1, round(seg["logo_churn_annual"] * n)) if target_churn > 0 else 0
    churned = []
    if logo_count > 0:
        avg_churn_size = target_churn / logo_count
        by_closeness = sorted(range(n), key=lambda i: abs(arrs[i] - avg_churn_size))
        cum = 0.0
        for i in by_closeness:
            if cum >= target_churn and churned:
                break
            if len(churned) >= n - 1:
                break
            churned.append(i)
            cum += arrs[i]
    for i in churned:
        roles[i] = "churn"

    # Contract: a handful of mid-sized accounts; _scaled_deltas then sizes each
    # partial delta so the aggregate hits the contraction $ target. Keep the COUNT
    # small (bounded to the at-risk band budget) so contractions don't flood the
    # at-risk classification — the health bands are set from the distribution below.
    hd = seg["health_distribution"]
    contract_budget = max(1, round(hd["at_risk"] * n))
    contract = []
    cum = 0.0
    for i in idx_by_arr_asc:
        if roles[i] != "stable":
            continue
        if len(contract) >= contract_budget or (cum >= target_contract and contract):
            break
        contract.append(i)
        cum += arrs[i]
    for i in contract:
        roles[i] = "contract"

    # Expand: largest available accounts carry expansion.
    expand = []
    cum = 0.0
    for i in idx_by_arr_desc:
        if roles[i] != "stable":
            continue
        expand.append(i)
        cum += arrs[i]
        if cum >= target_expand and len(expand) >= max(1, n // 4):
            break
    for i in expand:
        roles[i] = "expand"

    # Compute scaled deltas for expand/contract so aggregate $ hits targets.
    exp_deltas = _scaled_deltas(rng, [arrs[i] for i in expand], target_expand,
                                mags["expand_delta_pct"])
    con_deltas = _scaled_deltas(rng, [arrs[i] for i in contract], target_contract,
                                mags["contract_delta_pct"])
    delta_for = {}
    for i, d in zip(expand, exp_deltas):
        delta_for[i] = round(d, 1)
    for i, d in zip(contract, con_deltas):
        delta_for[i] = -round(d, 1)

    # --- classification by health_distribution (DECOUPLED from lifecycle events) ---
    # Health class is a point-in-time snapshot; a lifecycle event is a full-year
    # outcome. They correlate but are not identical: churn is a SUBSET of critical
    # (a critical account may not have churned yet — the leading-signal story),
    # contraction a subset of at-risk, expansion a subset of healthy. Take the band
    # COUNTS from the benchmark distribution, seat the event accounts in their band,
    # then fill the remainder so each band hits its target.
    hd = seg["health_distribution"]
    n_healthy = max(len(expand), round(hd["healthy"] * n))
    n_critical = max(len(churned), round(hd["critical"] * n))
    n_at_risk = max(len(contract), n - n_healthy - n_critical)
    # Renormalise if rounding / event-seat minimums pushed the sum off n.
    while n_healthy + n_at_risk + n_critical > n:
        if n_at_risk > len(contract):
            n_at_risk -= 1
        elif n_healthy > len(expand):
            n_healthy -= 1
        elif n_critical > len(churned):
            n_critical -= 1
        else:
            break
    n_healthy += max(0, n - (n_healthy + n_at_risk + n_critical))  # give slack to healthy

    classification = [None] * n
    for i in churned:
        classification[i] = "critical"
    for i in contract:
        classification[i] = "at_risk"
    for i in expand:
        classification[i] = "healthy"

    def _count(cls):
        return sum(1 for c in classification if c == cls)

    # Fill remaining critical slots with the smallest stable accounts (unresolved
    # crises with no event yet); healthy with the largest; the rest are at-risk.
    for i in idx_by_arr_asc:
        if _count("critical") >= n_critical:
            break
        if classification[i] is None:
            classification[i] = "critical"
    for i in idx_by_arr_desc:
        if _count("healthy") >= n_healthy:
            break
        if classification[i] is None:
            classification[i] = "healthy"
    for i in range(n):
        if classification[i] is None:
            classification[i] = "at_risk"

    accounts = []
    for i in range(n):
        role = roles[i]
        cls = classification[i]
        arr = arrs[i]
        if role == "churn":
            event, delta, arc = "churn", -100, rng.choice(arcs["churn"])
            traj, decline = "declining", rng.randint(max(6, months // 2), months - 1)
        elif role == "contract":
            event, delta, arc = "contract", delta_for[i], rng.choice(arcs["contract"])
            traj, decline = "declining", rng.randint(max(4, months // 2), months - 1)
        elif role == "expand":
            event, delta, arc = "expand", delta_for[i], rng.choice(arcs["expand"])
            traj, decline = ("improving" if rng.random() < 0.5 else "stable"), None
        elif cls == "healthy":  # stable + healthy — a flat renewal
            event, delta, arc = "renew", 0, rng.choice(arcs["renew_stable"])
            traj, decline = "stable", None
        else:  # stable but critical / at-risk — leading-signal account, no event yet
            event, delta = "renew", 0
            arc = rng.choice(arcs["churn"] if cls == "critical" else arcs["contract"])
            traj = "declining"
            decline = rng.randint(max(4, months // 2), months - 1)

        name = f"{_NAME_A[i % len(_NAME_A)]} {rng.choice(_NAME_B)}"
        accounts.append({
            "name": name,
            "arr": arr,
            "target_health": _health(rng, cls),
            "classification": cls,
            "story_arc": arc,
            "partner_tier": "direct",
            "renewal_date": rng.choice(["2026-09-30", "2026-12-31", "2027-03-31", "2027-06-30"]),
            "narrative": _narrative(role, arc, cls),
            "kpi_trajectory": traj,
            "decline_start_month": decline,
            "industry": rng.choice(_INDUSTRIES),
            "region": rng.choice(_REGIONS),
            "_segment": seg_key,           # provenance; harmless extra key
            "lifecycle": {
                "event": event,
                "event_month": rng.randint(max(3, months // 3), months - 1),
                "delta_pct": delta,
            },
        })
    return accounts


def _narrative(role: str, arc: str, cls: str = "healthy") -> str:
    a = arc.replace("_", " ")
    if role == "stable" and cls == "critical":
        return f"Critical health, not yet churned ({a}); leading-signal risk, no event this period"
    if role == "stable" and cls == "at_risk":
        return f"At-risk drift ({a}); softening signals, no lifecycle event yet"
    return {
        "expand": f"Expansion motion ({a}); healthy adoption, upsell landed",
        "contract": f"Downsell pressure ({a}); partial contraction at renewal",
        "churn": f"At-risk to lost ({a}); renewal not secured",
        "stable": f"Steady-state renewal ({a})",
    }[role]


def _nrr_report(accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute achieved ARR-weighted NRR/churn/expansion overall + by segment."""
    def bucket(accs):
        start = sum(a["arr"] for a in accs)
        exp = con = chu = 0.0
        for a in accs:
            lc = a["lifecycle"]
            d, arr = lc["delta_pct"], a["arr"]
            if lc["event"] == "expand":
                exp += arr * d / 100.0
            elif lc["event"] == "contract":
                con += arr * (-d) / 100.0
            elif lc["event"] == "churn":
                chu += arr
        nrr = (start + exp - con - chu) / start if start else 0
        return {
            "accounts": len(accs), "start_arr": round(start),
            "expansion_pct": round(exp / start, 4) if start else 0,
            "contraction_pct": round(con / start, 4) if start else 0,
            "gross_churn_pct": round(chu / start, 4) if start else 0,
            "nrr": round(nrr, 4),
        }
    segs = sorted({a["_segment"] for a in accounts})
    return {
        "portfolio": bucket(accounts),
        "by_segment": {s: bucket([a for a in accounts if a["_segment"] == s]) for s in segs},
    }


def build_manifest(*, accounts: int, name: str, domain: str, seed: int = 42,
                   benchmarks_path: str = DEFAULT_BENCHMARKS,
                   kpis: List[str] | None = None,
                   start: str = "2024-10-01", end: str = "2026-03-31",
                   months: int = 18) -> Dict[str, Any]:
    rng = random.Random(seed)
    bench = _load_benchmarks(benchmarks_path)
    mix = bench["portfolio_defaults"]["segment_account_mix"]
    counts = _segment_counts(accounts, mix)

    accs: List[Dict[str, Any]] = []
    for seg_key in ["enterprise", "mid_market", "smb"]:
        seg = bench["segments"][seg_key]
        accs.extend(_build_segment_accounts(rng, seg_key, seg, counts[seg_key],
                                            bench, months))
    rng.shuffle(accs)
    total_arr = sum(a["arr"] for a in accs)
    report = _nrr_report(accs)

    manifest = {
        "manifest_version": "2.0",
        "_calibration": {
            "generator": "benchmark_manifest_generator.py",
            "benchmarks_source": os.path.basename(benchmarks_path),
            "seed": seed,
            "honest_claim": "Behaviour calibrated to 2026 SaaS benchmarks (real-anchored). "
                            "Account OUTCOMES/counterfactuals remain model-generated — NOT real.",
            "achieved": report,
            "benchmark_targets": {
                s: {"nrr": bench["segments"][s]["nrr_median"],
                    "gross_churn": bench["segments"][s]["gross_revenue_churn_annual"],
                    "expansion": bench["segments"][s]["expansion_rate"]}
                for s in ["enterprise", "mid_market", "smb"]
            },
        },
        "customer": {
            "name": name,
            "domain": domain,
            "vertical": "saas_premium",
            "admin_email": f"admin@{domain}",
            "admin_name": f"{name} Admin",
            "total_arr": total_arr,
            "description": f"Benchmark-calibrated synthetic SaaS book ({accounts} accounts, seed {seed}). "
                           "Behaviour anchored to 2026 NRR/churn benchmarks; identities are placeholders "
                           "(run firmographics_overlay.py to drape real companies).",
        },
        "time_range": {
            "start": start, "end": end, "frequency": "monthly",
            "data_points_per_kpi": months,
        },
        "kpis": {
            "selection": "starter_9",
            "count": len(kpis or STARTER_9),
            "codes": kpis or STARTER_9,
        },
        "accounts": accs,
    }
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a benchmark-calibrated SaaS manifest.")
    p.add_argument("--accounts", type=int, default=40)
    p.add_argument("--name", default="Benchmark Calibrated SaaS Co")
    p.add_argument("--domain", default="benchmark-saas.io")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--benchmarks", default=DEFAULT_BENCHMARKS)
    p.add_argument("--out", default=None, help="Output manifest path (default: stdout)")
    args = p.parse_args()

    m = build_manifest(accounts=args.accounts, name=args.name, domain=args.domain,
                       seed=args.seed, benchmarks_path=args.benchmarks)
    payload = json.dumps(m, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(payload + "\n")
        rep = m["_calibration"]["achieved"]["portfolio"]
        print(f"Wrote {args.out}")
        print(f"  {args.accounts} accounts · total ARR ${m['customer']['total_arr']:,}")
        print(f"  Portfolio ARR-weighted NRR: {rep['nrr']*100:.1f}% "
              f"(expansion {rep['expansion_pct']*100:.1f}% · "
              f"contraction {rep['contraction_pct']*100:.1f}% · "
              f"gross churn {rep['gross_churn_pct']*100:.1f}%)")
        for s, b in m["_calibration"]["achieved"]["by_segment"].items():
            tgt = m["_calibration"]["benchmark_targets"][s]["nrr"]
            print(f"  {s:12s} NRR {b['nrr']*100:5.1f}%  (target {tgt*100:.0f}%)  "
                  f"n={b['accounts']}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
