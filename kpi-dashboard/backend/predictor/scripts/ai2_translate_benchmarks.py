#!/usr/bin/env python3
"""AI-2 — Benchmark → coefficient translation step.

Closes AI-2 from `nrr_predictor_v3_design_notes.md`. Validates that the
PLACEHOLDER coefficient `μ` values in `cdi_seed.py` are arithmetically
consistent with the benchmark annual rates they were derived from.

Per design notes Q2 + PLAN A1: public benchmarks report aggregate annual
rates (NRR, gross retention, expansion frequency); the GLMM consumes
coefficient-level priors. Going from one to the other is non-trivial.
This script does the univariate sanity check — does the intercept μ
imply the right monthly rate? — and reports deltas.

Univariate check is the floor of useful. A full multivariate simulation
(generate synthetic portfolio, apply full coefficient set, roll forward
12 months, compare portfolio NRR distribution to benchmark) is a Block 2
exercise that runs against the actual fitted GLMM, not against the seed.

Usage (from kpi-dashboard/backend):
    PYTHONPATH=. python predictor/scripts/ai2_translate_benchmarks.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional

# Make the package importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from predictor.cdi_seed import SEEDS, CDIProfileSeed  # noqa: E402


def annual_to_monthly_hazard(annual_event_rate: float) -> float:
    """Convert annual event probability to monthly hazard.

    Assumes events are roughly Poisson over time, so survival is
    multiplicative: S(12mo) = (1 − h_monthly)^12.
    Therefore: h_monthly = 1 − (1 − annual_event_rate)^(1/12).
    """
    if not 0 <= annual_event_rate < 1:
        raise ValueError(f'annual_event_rate must be in [0, 1), got {annual_event_rate}')
    return 1 - (1 - annual_event_rate) ** (1.0 / 12.0)


def annual_event_to_monthly_rate(annual_event_count_per_acct: float) -> float:
    """For events that can recur (expansion), uniform monthly approximation.

    annual_expansion_event_rate=0.45 means 45% of accounts have ≥1 expansion
    per year; we approximate monthly P(any event) as (1 − (1 − 0.45)^(1/12)).
    """
    return annual_to_monthly_hazard(annual_event_count_per_acct)


def logit(p: float) -> float:
    if not 0 < p < 1:
        raise ValueError(f'logit input must be in (0, 1), got {p}')
    return math.log(p / (1 - p))


def report_profile(seed: CDIProfileSeed) -> dict:
    """Univariate translation check for one profile.

    Compares each intercept's placeholder `mu` against the value implied
    by the benchmark annual rates. Returns a dict with deltas.
    """
    # 1. Hazard intercept — should equal logit(monthly hazard from
    #    annual_gross_retention)
    annual_gross_churn = 1 - seed.annual_gross_retention
    monthly_hazard_target = annual_to_monthly_hazard(annual_gross_churn)
    hazard_mu_implied = logit(monthly_hazard_target)
    hazard_delta = hazard_mu_implied - seed.hazard_intercept.mu

    # 2. Expansion event intercept — should equal logit(monthly P(event))
    monthly_expansion_target = annual_event_to_monthly_rate(
        seed.annual_expansion_event_rate
    )
    expansion_event_mu_implied = logit(monthly_expansion_target)
    expansion_event_delta = expansion_event_mu_implied - seed.expansion_event_intercept.mu

    # 3. Expansion size intercept — log of expected fractional uplift
    expansion_size_mu_implied = math.log(seed.annual_expansion_size_pct_given_event)
    expansion_size_delta = expansion_size_mu_implied - seed.expansion_size_intercept.mu

    return {
        'profile': f'{seed.vertical}__{seed.saas_profile}',
        'benchmark_vintage': seed.benchmark_vintage,
        'annual_rates': {
            'gross_retention': seed.annual_gross_retention,
            'nrr': seed.annual_net_revenue_retention,
            'expansion_event_rate': seed.annual_expansion_event_rate,
            'expansion_size_pct_given_event': seed.annual_expansion_size_pct_given_event,
        },
        'hazard_intercept': {
            'placeholder_mu': seed.hazard_intercept.mu,
            'implied_mu': round(hazard_mu_implied, 3),
            'delta': round(hazard_delta, 3),
            'monthly_hazard_target': round(monthly_hazard_target, 5),
            'verdict': _verdict(hazard_delta),
        },
        'expansion_event_intercept': {
            'placeholder_mu': seed.expansion_event_intercept.mu,
            'implied_mu': round(expansion_event_mu_implied, 3),
            'delta': round(expansion_event_delta, 3),
            'monthly_event_rate_target': round(monthly_expansion_target, 5),
            'verdict': _verdict(expansion_event_delta),
        },
        'expansion_size_intercept': {
            'placeholder_mu': seed.expansion_size_intercept.mu,
            'implied_mu': round(expansion_size_mu_implied, 3),
            'delta': round(expansion_size_delta, 3),
            'verdict': _verdict(expansion_size_delta),
        },
    }


def _verdict(delta: float) -> str:
    """Categorize coefficient delta magnitude.

    On logit scale: delta < 0.1 ≈ rounding error; 0.1–0.3 ≈ minor calibration
    drift; > 0.3 ≈ structural mis-anchoring of the prior.
    """
    abs_d = abs(delta)
    if abs_d < 0.1:
        return 'OK (within rounding)'
    if abs_d < 0.3:
        return 'MINOR — recommend update'
    return 'MAJOR — placeholder mis-anchored, must update before G2 sign-off'


def render_markdown(reports: list[dict]) -> str:
    """Render reports as G2-reviewer markdown artifact."""
    lines = [
        '# AI-2 — Benchmark → Coefficient Translation Report',
        '',
        '*Closes AI-2 from `nrr_predictor_v3_design_notes.md`.*',
        '',
        'Univariate sanity check: do the placeholder `μ` values in `cdi_seed.py` ',
        'imply the same monthly rates as the benchmark annual rates they were ',
        'derived from? Discrepancies above 0.3 (logit scale) are structural; ',
        'must be fixed before G2 sign-off.',
        '',
        '## Methodology',
        '',
        '- **Hazard intercept μ** target: `logit(1 − (1 − annual_gross_churn)^(1/12))`',
        '- **Expansion-event intercept μ** target: `logit(1 − (1 − annual_event_rate)^(1/12))`',
        '- **Expansion-size intercept μ** target: `log(annual_expansion_size_pct_given_event)`',
        '',
        '## Results per profile',
        '',
    ]
    for r in reports:
        lines.append(f'### `{r["profile"]}`')
        lines.append('')
        lines.append(f'**Benchmark:** {r["benchmark_vintage"]}')
        lines.append('')
        lines.append('Annual rates (from cdi_seed):')
        lines.append('')
        for k, v in r['annual_rates'].items():
            lines.append(f'- `{k}` = {v}')
        lines.append('')
        lines.append('| Coefficient | Placeholder μ | Implied μ | Delta | Verdict |')
        lines.append('|---|---|---|---|---|')
        for key in ('hazard_intercept', 'expansion_event_intercept', 'expansion_size_intercept'):
            block = r[key]
            lines.append(
                f'| `{key}` | {block["placeholder_mu"]} | {block["implied_mu"]} | '
                f'{block["delta"]:+.3f} | {block["verdict"]} |'
            )
        lines.append('')

    # Summary verdict
    has_major = any(
        'MAJOR' in r[key]['verdict']
        for r in reports
        for key in ('hazard_intercept', 'expansion_event_intercept', 'expansion_size_intercept')
    )
    has_minor = any(
        'MINOR' in r[key]['verdict']
        for r in reports
        for key in ('hazard_intercept', 'expansion_event_intercept', 'expansion_size_intercept')
    )

    lines.append('## Verdict')
    lines.append('')
    if has_major:
        lines.append('**MAJOR mis-anchoring detected.** Update placeholders in `cdi_seed.py` to the implied values before G2 sign-off. Otherwise the GLMM will start from priors that misrepresent the benchmark, requiring it to "learn against" the seed instead of "from" it.')
    elif has_minor:
        lines.append('**Minor calibration drift on some intercepts.** Update before G2 sign-off — cheap, removes a quibble target.')
    else:
        lines.append('**All intercepts within rounding tolerance.** No updates needed before G2 sign-off.')
    lines.append('')

    lines.append('## Out of scope for this report (deferred to Block 2)')
    lines.append('')
    lines.append('Univariate intercept checks are the floor of useful. The full multivariate calibration — generate a synthetic SaaS portfolio matching benchmark composition, apply the full coefficient set, roll forward 12 months, compare the simulated portfolio NRR distribution to the benchmark distribution, iterate — runs against the fitted GLMM in Block 2, not against the seed alone. The non-intercept coefficients (`health_slope_3mo`, `days_to_renewal_0_30`) are anchored at AI-2-translation TBD values pending that Block 2 simulation.')
    lines.append('')
    lines.append('---')
    lines.append('*Generated by `predictor/scripts/ai2_translate_benchmarks.py`.*')

    return '\n'.join(lines)


def main(out_path: Optional[Path] = None) -> int:
    reports = [report_profile(seed) for seed in SEEDS.values()]
    md = render_markdown(reports)

    if out_path is None:
        out_path = (
            Path(__file__).resolve().parent.parent
            / 'sql'
            / 'ai2_benchmark_translation_report.md'
        )
    out_path.write_text(md)
    print(md)
    print(f'\n[Saved to {out_path}]')

    has_major = any(
        'MAJOR' in r[key]['verdict']
        for r in reports
        for key in ('hazard_intercept', 'expansion_event_intercept', 'expansion_size_intercept')
    )
    return 1 if has_major else 0


if __name__ == '__main__':
    sys.exit(main())
