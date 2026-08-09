# Real-Anchored Demo Data — Getting off *pure* synthetic

**Problem this solves:** the #1 demo criticism is *"your data is made up."* This
toolchain moves the load-driver from **pure synthetic** to a **real-anchored
hybrid**, so the two things a prospect actually probes both close:

1. *"Are these real companies or made-up logos?"* → **real** (firmographics overlay)
2. *"Are these numbers plausible for my segment?"* → **benchmark-defensible** (calibration)

## The honest-claim boundary (read this first)

There are three data layers. Only two can be made real; the third cannot — by
anyone, from any marketplace — because linked CS-outcome + intervention +
counterfactual data does not exist to borrow.

| Layer | What it is | This toolchain | Claim you may make |
|---|---|---|---|
| **A. Account spine** | names, industries, regions, sizes | **REAL** (overlay #2) | "real company book" ✅ |
| **B. Behaviour / calibration** | NRR, churn, expansion, health mix | **REAL distributions** (calibration #1) | "behaviour calibrated to 2026 SaaS benchmarks" ✅ |
| **C. Outcomes + counterfactual** | *which* account churned, what "CS Pulse would have saved" | **model-generated** (Wizard B/D) | "real customer outcome data" ❌ **never** |

> **Demo framing that turns this into a strength:**
> *"Real company book, behaviour calibrated to 2026 SaaS benchmarks. The outcome
> attribution is our model — here's the causal graph and the benchmark anchor so
> you can audit exactly how we got there."*
> This invites the audit instead of dodging it — the same transparency move as the
> dual-horizon NRR relabel. The only path to a genuinely real Layer C is one
> anonymised **design-partner** book under NDA (a GTM ask, not a download).

## Files

| File | Role |
|---|---|
| `benchmarks.json` | Cited 2026 B2B SaaS benchmarks (NRR/churn/expansion/health) by segment. Editable single source of calibration truth. |
| `generators/benchmark_manifest_generator.py` | **#1** — emit a manifest whose aggregate behaviour reproduces the benchmarks. |
| `generators/firmographics_overlay.py` | **#2** — drape real company identities over a calibrated manifest. |
| `generators/sample_firmographics.csv` | Illustrative real-company export (replace with a licensed Cybersyn/PDL/Crunchbase export). |

## Workflow

```bash
# 1. Generate a benchmark-calibrated book (deterministic per --seed)
python3 generators/benchmark_manifest_generator.py \
    --accounts 40 --name "Acme Portfolio" --domain acme.io \
    --seed 42 --out manifests/acme_calibrated.json

# 2. Drape real companies over it
python3 generators/firmographics_overlay.py \
    --manifest manifests/acme_calibrated.json \
    --firmographics generators/sample_firmographics.csv \
    --out manifests/acme_calibrated.real.json

# 3. Load it like any other manifest (extra _calibration/_firmographics keys are ignored)
#    e.g. via the normal onboarding/manifest path used for the other SaaS manifests.
```

The generator prints the achieved ARR-weighted NRR per segment vs the benchmark
target — every book is self-validating:

```
enterprise   NRR 117.7%  (target 118%)  n=8
mid_market   NRR 107.2%  (target 108%)  n=18
smb          NRR  96.7%  (target 97%)   n=14
```

`_calibration.achieved` (in the manifest) records those numbers as provenance you
can point a skeptical CRO at.

## Sourcing a real firmographics export (Layer A)

The overlay accepts any CSV with a company-name column (aliases auto-detected:
`company_name`/`name`, `industry`/`sector`, `region`/`country`,
`employee_count`/`employees`, `revenue`/`annual_revenue`). Good sources:

- **Snowflake Marketplace — Cybersyn** (Snowflake-owned): free tiers incl. Census,
  GitHub, financials; company firmographics.
- **People Data Labs / Crunchbase** listings (Snowflake or Databricks Marketplace).
- **Public-domain**: US Census / gov business registries (lowest licence risk).

> ⚠ **Licence:** "anonymised" ≠ "licensed for demos." Many marketplace *sample*
> shares are eval/non-commercial; using them in a sales deck is a redistribution
> use. Verify each listing's licence; prefer public-domain or explicitly
> demo-licensed data. Re-identification risk on firmographics is low but non-zero.

## Plausibility guard

`firmographics_overlay.py` rank-matches biggest account → biggest-revenue company,
and flags any account whose ARR exceeds `--max-arr-share` (default 40%) of the
matched company's revenue — an implausible book (a $10M ARR account on a $5M-revenue
company). It never silently rewrites ARR (that would break calibration); it flags
and tells you to use a larger company for that account.

## What this does NOT change

- No engine/architecture change. Manifests are standard v2.0; the loader ignores
  the provenance keys.
- Layer C (outcomes, Wizard B counterfactual, Wizard D forecast) is untouched and
  remains model-generated. Calibrating inputs does not, and cannot, make the
  counterfactual real — that's answered by transparency, not borrowed data.
