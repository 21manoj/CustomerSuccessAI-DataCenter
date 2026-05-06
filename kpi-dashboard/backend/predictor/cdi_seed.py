"""CDI seed — public-benchmark hyperparameters per (vertical, saas_profile).

Per Architecture Decision A1 in PLAN_nrr_predictor_v3.md, the Phase 1 v1
GLMM uses informative starting values + ridge/elastic-net penalty terms
(NOT proper Bayesian {μ, σ} priors). The seed values below are the
informative starting values; the σ widths translate to penalty strengths
(narrow σ → strong shrinkage toward μ; wide σ → weak penalty).

Per A2 in design notes Q2, these public-benchmark values are
"priors-with-provenance, not truth." Reviewer (Manoj) approves at G2
before Block 2 fits anything. AI-2 from the design-notes follow-up table
is the ~2-day translation step that turns a benchmark NRR distribution
into coefficient-level priors — that work happens in Block 1 day 3.

PLACEHOLDER VALUES — replace at G2 with reviewer-approved benchmarks
and the synthetic-panel calibration outputs from AI-2.

Sources cited (vintages locked here so we don't drift across re-fits):
  - Gainsight Pulse Benchmarks 2024 — SaaS NRR distributions by ARR tier
  - OpenView 2024 SaaS Benchmarks — gross retention, expansion rates
  - Vertical-specific equivalents for healthcare/data-center (deferred —
    see AI-1; healthcare not in Phase 1 scope per `nrr_predictor_v3_design_notes.md`)

Per A6: separate priors for `p_expansion_event` because expansion is a
first-class output. SaaS-Enterprise vs SaaS-SMB have meaningfully
different expansion frequencies — large enterprise contracts expand less
often but for more dollars; SMB accounts expand more frequently for less.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict


@dataclass
class CoefficientPrior:
    """One coefficient's informative starting value + shrinkage penalty.

    `mu` is the starting value passed to the GLMM as a fixed-effect prior
    mean. `sigma` controls the ridge penalty: narrower → stronger
    shrinkage toward `mu`. `provenance` is the source citation, surfaced
    in the model card.
    """
    mu: float
    sigma: float
    provenance: str


@dataclass
class CDIProfileSeed:
    """One (vertical, saas_profile) seed bundle.

    Fields map to specific covariates in `predictor/features.py`'s
    `feature_columns()`. Names match for the GLMM fit code to plumb
    through unambiguously.
    """
    vertical: str
    saas_profile: str
    benchmark_vintage: str

    # Annual base rates from public benchmarks — used to derive monthly
    # hazard intercept and expansion rate. Kept separate from coefficients
    # so we can sanity-check against published numbers.
    annual_gross_retention: float
    annual_net_revenue_retention: float
    annual_expansion_event_rate: float
    annual_expansion_size_pct_given_event: float

    # Hazard model (sub-model 1) coefficient priors
    hazard_intercept: CoefficientPrior = field(default_factory=lambda: CoefficientPrior(0.0, 1.0, 'placeholder'))
    health_slope_3mo: CoefficientPrior = field(default_factory=lambda: CoefficientPrior(0.0, 1.0, 'placeholder'))
    days_to_renewal_0_30: CoefficientPrior = field(default_factory=lambda: CoefficientPrior(0.0, 1.0, 'placeholder'))

    # Expansion two-part model (sub-model 3) priors — A6 elevates these
    # to first-class. P(event) on logit scale; size given event on log scale.
    expansion_event_intercept: CoefficientPrior = field(default_factory=lambda: CoefficientPrior(0.0, 1.0, 'placeholder'))
    expansion_size_intercept: CoefficientPrior = field(default_factory=lambda: CoefficientPrior(0.0, 1.0, 'placeholder'))


# ----------------------------------------------------------------------------
# Seed bundles — PLACEHOLDER VALUES, replace at G2.
# ----------------------------------------------------------------------------

SEEDS: Dict[str, CDIProfileSeed] = {
    'saas_premium__saas_enterprise': CDIProfileSeed(
        vertical='saas_premium',
        saas_profile='saas_enterprise',
        benchmark_vintage='Gainsight Pulse 2024 + OpenView 2024',
        # Whales: high retention, modest churn, high $ per expansion event
        annual_gross_retention=0.93,                  # ~7% gross churn
        annual_net_revenue_retention=1.12,            # NRR 112% typical for Enterprise SaaS
        annual_expansion_event_rate=0.45,             # 45% of accounts expand annually
        annual_expansion_size_pct_given_event=0.18,   # +18% ARR per expansion
        hazard_intercept=CoefficientPrior(
            mu=-4.5,    # logit of (~0.7%/month from 7% annual)
            sigma=0.5,  # moderate shrinkage
            provenance='derived from Gainsight Pulse 2024 mid-Enterprise SaaS gross retention',
        ),
        health_slope_3mo=CoefficientPrior(
            mu=-0.04,
            sigma=0.05,
            provenance='AI-2 translation from synthetic-panel calibration (TBD G2)',
        ),
        days_to_renewal_0_30=CoefficientPrior(
            mu=+0.6,    # renewal proximity raises hazard absent intervention
            sigma=0.3,
            provenance='AI-2 translation (TBD G2)',
        ),
        expansion_event_intercept=CoefficientPrior(
            mu=-2.5,    # logit of (~3.5%/month from 45% annual)
            sigma=0.5,
            provenance='derived from OpenView 2024 Enterprise SaaS expansion frequency',
        ),
        expansion_size_intercept=CoefficientPrior(
            mu=-1.7,    # log of 0.18 = -1.71
            sigma=0.4,
            provenance='derived from OpenView 2024 Enterprise SaaS upsell size distribution',
        ),
    ),
    'saas_premium__saas_smb': CDIProfileSeed(
        vertical='saas_premium',
        saas_profile='saas_smb',
        benchmark_vintage='Gainsight Pulse 2024 + OpenView 2024',
        # Volume SaaS: lower retention, higher expansion frequency, smaller
        # $ per expansion. NRR 100% is the SaaS-SMB modal target.
        annual_gross_retention=0.85,                  # ~15% gross churn — typical for SMB
        annual_net_revenue_retention=1.02,            # NRR 102% — SMB modal
        annual_expansion_event_rate=0.62,             # 62% of accounts expand annually
        annual_expansion_size_pct_given_event=0.10,   # +10% ARR per expansion (smaller per-event)
        hazard_intercept=CoefficientPrior(
            mu=-3.6,    # logit of (~1.4%/month from 15% annual)
            sigma=0.5,
            provenance='derived from Gainsight Pulse 2024 SMB SaaS gross retention',
        ),
        health_slope_3mo=CoefficientPrior(
            mu=-0.06,   # SMB hazards more sensitive to health movement
            sigma=0.05,
            provenance='AI-2 translation (TBD G2)',
        ),
        days_to_renewal_0_30=CoefficientPrior(
            mu=+0.8,
            sigma=0.3,
            provenance='AI-2 translation (TBD G2)',
        ),
        expansion_event_intercept=CoefficientPrior(
            mu=-2.0,    # logit of (~5%/month from 62% annual)
            sigma=0.4,
            provenance='derived from OpenView 2024 SMB SaaS expansion frequency',
        ),
        expansion_size_intercept=CoefficientPrior(
            mu=-2.3,    # log of 0.10 = -2.30
            sigma=0.4,
            provenance='derived from OpenView 2024 SMB SaaS upsell size distribution',
        ),
    ),
}


def get_seed(vertical: str, saas_profile: str) -> CDIProfileSeed:
    """Look up the CDI seed for a (vertical, profile) tuple.

    Raises KeyError if no seed exists — Phase 1 explicitly supports only
    `saas_premium` × {`saas_enterprise`, `saas_smb`}. Other tuples get
    raised so cold-start logic (per A1) doesn't silently fall back to a
    default that doesn't match the tenant.
    """
    key = f'{vertical}__{saas_profile}'
    if key not in SEEDS:
        raise KeyError(
            f'No CDI seed for vertical={vertical}, saas_profile={saas_profile}. '
            f'Phase 1 supports: {list(SEEDS.keys())}'
        )
    return SEEDS[key]


def export_seeds_for_review() -> dict:
    """Serialize all seeds for the G2 review artifact.

    Output is human-readable JSON the reviewer skims to check vintages +
    starting values + provenance. Not used by the model fit code directly.
    """
    return {
        key: {
            **asdict(seed),
            # Flatten CoefficientPriors for readability
            'hazard_intercept': asdict(seed.hazard_intercept),
            'health_slope_3mo': asdict(seed.health_slope_3mo),
            'days_to_renewal_0_30': asdict(seed.days_to_renewal_0_30),
            'expansion_event_intercept': asdict(seed.expansion_event_intercept),
            'expansion_size_intercept': asdict(seed.expansion_size_intercept),
        }
        for key, seed in SEEDS.items()
    }


if __name__ == '__main__':
    import json
    print(json.dumps(export_seeds_for_review(), indent=2))
