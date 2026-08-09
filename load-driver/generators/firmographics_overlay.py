#!/usr/bin/env python3
"""
firmographics_overlay.py  —  Recommendation #2 (real account spine).

Drape REAL company identities (names, industries, regions, employee counts)
over a benchmark-calibrated manifest's SYNTHETIC BEHAVIOUR layer. The demo
stops showing "Polaris Cloud / Altair Systems" and shows real companies with
real firmographics — while the health, lifecycle events and NRR stay exactly
as calibrated by benchmark_manifest_generator.py (#1).

Input real-company CSV (a Cybersyn / People Data Labs / Crunchbase export, or
the illustrative sample_firmographics.csv). Recognised columns (aliases ok):
    company_name | name | account_name        (required)
    industry     | sector                     (optional)
    region       | country | hq_country       (optional)
    employee_count | employees | headcount    (optional)
    revenue      | annual_revenue | revenue_usd (optional, enables the guard)

Matching:  accounts are ranked by ARR (desc) and companies by revenue (desc),
then matched rank-for-rank, so the biggest accounts get the biggest real
companies and each account's ARR stays a plausible fraction of that company's
revenue. A guard flags any account whose ARR exceeds `--max-arr-share` of the
matched company's revenue (default 0.40) — that would be an implausible book.

IMPORTANT — honest-claim boundary:
    This makes the ACCOUNT SPINE real. It does NOT make the OUTCOME or the
    "what CS Pulse would have saved" COUNTERFACTUAL real — those stay
    model-generated. Defensible claim: "real company book, behaviour calibrated
    to benchmarks." NOT defensible: "real customer outcome data."
    Also: verify the source CSV's licence permits demo/redistribution use
    (many marketplace sample shares are eval-only). Prefer public-domain
    (gov/Census) or explicitly demo-licensed firmographics.

Usage:
    python3 generators/firmographics_overlay.py \
        --manifest manifests/generated_calibrated_saas.json \
        --firmographics generators/sample_firmographics.csv \
        --out manifests/generated_calibrated_saas.real.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

_ALIASES = {
    "company_name": ["company_name", "name", "account_name", "company", "legal_name"],
    "industry": ["industry", "sector", "naics_industry", "primary_industry"],
    "region": ["region", "country", "hq_country", "headquarters_country", "location"],
    "employee_count": ["employee_count", "employees", "headcount", "num_employees", "size"],
    "revenue": ["revenue", "annual_revenue", "revenue_usd", "estimated_revenue", "total_revenue"],
}


def _num(val: Optional[str]) -> Optional[float]:
    """Parse '$1,234M' / '2.3B' / '450' → float USD, or None."""
    if val is None:
        return None
    s = str(val).strip().lower().replace(",", "").replace("$", "")
    if not s or s in ("na", "n/a", "null", "none", "-"):
        return None
    mult = 1.0
    if s.endswith("b"):
        mult, s = 1e9, s[:-1]
    elif s.endswith("m"):
        mult, s = 1e6, s[:-1]
    elif s.endswith("k"):
        mult, s = 1e3, s[:-1]
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    return float(s) * mult if m else None


def _resolve_columns(header: List[str]) -> Dict[str, Optional[str]]:
    lower = {h.lower().strip(): h for h in header}
    resolved: Dict[str, Optional[str]] = {}
    for canon, aliases in _ALIASES.items():
        resolved[canon] = next((lower[a] for a in aliases if a in lower), None)
    if resolved["company_name"] is None:
        raise ValueError(
            f"Firmographics CSV must have a company-name column "
            f"(one of {_ALIASES['company_name']}); got header {header}")
    return resolved


def load_firmographics(path: str) -> List[Dict[str, Any]]:
    with open(path, newline="") as f:
        # skip leading comment lines starting with '#'
        rows = [ln for ln in f if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(rows)
    cols = _resolve_columns(reader.fieldnames or [])
    out = []
    for r in reader:
        name = (r.get(cols["company_name"]) or "").strip()
        if not name:
            continue
        out.append({
            "company_name": name,
            "industry": (r.get(cols["industry"]) or "").strip() if cols["industry"] else "",
            "region": (r.get(cols["region"]) or "").strip() if cols["region"] else "",
            "employee_count": _num(r.get(cols["employee_count"])) if cols["employee_count"] else None,
            "revenue": _num(r.get(cols["revenue"])) if cols["revenue"] else None,
        })
    return out


def overlay(manifest: Dict[str, Any], companies: List[Dict[str, Any]], *,
            max_arr_share: float = 0.40, allow_reuse: bool = False) -> Dict[str, Any]:
    accounts = manifest["accounts"]
    n = len(accounts)

    if len(companies) < n and not allow_reuse:
        raise ValueError(
            f"Only {len(companies)} real companies for {n} accounts. "
            f"Provide a larger firmographics export or pass --allow-reuse.")

    # Rank accounts by ARR desc, companies by revenue desc (None revenue last).
    acct_order = sorted(range(n), key=lambda i: accounts[i]["arr"], reverse=True)
    comp_sorted = sorted(companies, key=lambda c: (c["revenue"] is not None, c["revenue"] or 0),
                         reverse=True)

    flagged = []
    used = 0
    for rank, acct_idx in enumerate(acct_order):
        comp = comp_sorted[rank % len(comp_sorted)]
        suffix = ""
        if rank >= len(comp_sorted):  # reuse path
            suffix = f" ({1 + rank // len(comp_sorted)})"
        acct = accounts[acct_idx]
        acct["name"] = comp["company_name"] + suffix
        if comp["industry"]:
            acct["industry"] = comp["industry"]
        if comp["region"]:
            acct["region"] = comp["region"]
        if comp["employee_count"] is not None:
            acct["employee_count"] = int(comp["employee_count"])

        # Plausibility guard: ARR should be a modest fraction of company revenue.
        rev = comp["revenue"]
        if rev and rev > 0:
            share = acct["arr"] / rev
            acct["_arr_revenue_share"] = round(share, 3)
            if share > max_arr_share:
                acct["_firmographic_warning"] = (
                    f"ARR ${acct['arr']:,} is {share*100:.0f}% of {comp['company_name']} "
                    f"revenue (${int(rev):,}) — exceeds {max_arr_share*100:.0f}% cap; "
                    f"implausibly large. Use a larger company here.")
                flagged.append(acct["name"])
        used += 1

    manifest["_firmographics"] = {
        "overlaid": True,
        "adapter": "firmographics_overlay.py",
        "companies_available": len(companies),
        "accounts_overlaid": used,
        "reused_identities": max(0, n - len(companies)) if allow_reuse else 0,
        "max_arr_share": max_arr_share,
        "plausibility_flags": flagged,
        "honest_claim": "Account SPINE is real (names/industries/regions/sizes). "
                        "OUTCOMES + counterfactuals remain model-generated — NOT real. "
                        "Defensible: 'real company book, benchmark-calibrated behaviour'.",
        "licence_reminder": "Confirm the source firmographics CSV is licensed for demo/"
                            "redistribution use; prefer public-domain or demo-licensed data.",
    }
    cust = manifest.setdefault("customer", {})
    cust["description"] = (cust.get("description", "").split(" Identities")[0]
                           + " Identities overlaid with real firmographics "
                           f"({used} real companies). Behaviour remains benchmark-calibrated "
                           "synthetic; outcomes are model-generated, not real.")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Overlay real company firmographics onto a calibrated manifest.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--firmographics", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-arr-share", type=float, default=0.40)
    p.add_argument("--allow-reuse", action="store_true",
                   help="Reuse company identities (with a numeric suffix) when there are "
                        "fewer companies than accounts.")
    args = p.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    companies = load_firmographics(args.firmographics)
    overlay(manifest, companies, max_arr_share=args.max_arr_share, allow_reuse=args.allow_reuse)

    with open(args.out, "w") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")

    fm = manifest["_firmographics"]
    print(f"Wrote {args.out}")
    print(f"  Overlaid {fm['accounts_overlaid']} accounts with "
          f"{fm['companies_available']} real companies "
          f"(reused {fm['reused_identities']}).")
    if fm["plausibility_flags"]:
        print(f"  ⚠ {len(fm['plausibility_flags'])} ARR-vs-revenue plausibility flags: "
              f"{', '.join(fm['plausibility_flags'][:5])}"
              f"{' …' if len(fm['plausibility_flags']) > 5 else ''}")
        print(f"    (ARR exceeds {args.max_arr_share*100:.0f}% of matched company revenue — "
              f"use larger companies for the biggest accounts.)")
    else:
        print("  ✓ No ARR-vs-revenue plausibility flags.")


if __name__ == "__main__":
    main()
