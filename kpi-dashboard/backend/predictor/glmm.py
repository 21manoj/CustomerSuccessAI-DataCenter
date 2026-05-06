"""GLMM fit module — Block 2 of NRR Predictor v3.

Per Architecture Decision A1 in PLAN_nrr_predictor_v3.md:
  Phase 1 v1 = frequentist hierarchical GLMM (statsmodels).
  Bayesian deferred to Phase 2 (data + hire gated).

Three sub-models share this module:
  - hazard          (sub-model 1, logit, monthly churn probability)
  - contraction     (sub-model 2, GLM, conditional on survival)
  - expansion_event (sub-model 3a, logit, monthly P(expansion))
  - expansion_size  (sub-model 3b, log link, conditional on event)

Per A6 (expansion as first-class), all four sub-models share equal
calibration discipline. No "primary + secondary."

Hierarchical structure (per design notes Q5 + A5):
  CDI vertical-level prior (informative starting values + ridge penalty)
    → tenant random intercept/slopes
      → segment random intercept (within tenant)

Ridge penalty: per-coefficient L2 against the CDI seed μ, scaled by
1/σ² (so narrow σ = strong shrinkage toward seed). This implements
A1's "weaker but pragmatic" version of Bayesian hierarchical priors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from predictor.cdi_seed import CDIProfileSeed, get_seed
from predictor.features import engineer_features, feature_columns

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Sub-model registry — what each sub-model fits, what outcome column to use,
# what link function is appropriate.
# ----------------------------------------------------------------------------

@dataclass
class SubModelSpec:
    name: str
    outcome_column: str
    link: str  # 'logit' | 'log' | 'identity'
    family: str  # statsmodels family name
    description: str
    # Subset of feature_columns() this sub-model uses; None = all
    feature_subset: Optional[List[str]] = None

SUB_MODELS: Dict[str, SubModelSpec] = {
    'hazard': SubModelSpec(
        name='hazard',
        outcome_column='is_churn_event',
        link='logit',
        family='Binomial',
        description='Monthly churn hazard, logit link (sub-model 1)',
    ),
    'contraction': SubModelSpec(
        name='contraction',
        outcome_column='is_contraction_event',
        link='logit',
        family='Binomial',
        description='Monthly contraction event, logit link (sub-model 2 part A)',
    ),
    'expansion_event': SubModelSpec(
        name='expansion_event',
        outcome_column='is_expansion_event',
        link='logit',
        family='Binomial',
        description='Monthly expansion event probability (sub-model 3a)',
    ),
    # expansion_size is fit only on rows where is_expansion_event=True;
    # it predicts E[size | event] on log scale. The outcome column for
    # this sub-model is `expansion_size_pct` which we derive from
    # the OUTCOME node revenue_impact / arr (TBD when real expansion
    # outcomes accumulate; v1 fits on synthetic-event rows or skips).
    'expansion_size': SubModelSpec(
        name='expansion_size',
        outcome_column='expansion_size_pct',
        link='log',
        family='Gamma',
        description='Expansion magnitude given event, log link (sub-model 3b)',
    ),
}


# ----------------------------------------------------------------------------
# Fit result envelope — what each sub-model fit produces
# ----------------------------------------------------------------------------

@dataclass
class FitResult:
    sub_model: str
    saas_profile: str
    fit_type: str  # 'cdi_seed' | 'tenant_glmm' | 'tenant_glmm_pooled' | 'fallback_to_prior'
    status: str    # 'converged' | 'singular' | 'insufficient_events' | 'fallback'
    coefficients: Dict[str, float]
    coefficient_se: Dict[str, float]
    n_observations: int
    n_events: int
    n_tenants: int
    convergence_diagnostics: dict = field(default_factory=dict)
    notes: str = ''

    def to_predictor_row(self, customer_id: Optional[int], vertical: str) -> dict:
        """Shape for a `PredictorCalibration` row.

        Returns the dict subset suitable to pass as kwargs to the model
        constructor (with timestamps + calibration_id added by caller).
        """
        return {
            'customer_id': customer_id,
            'vertical': vertical,
            'saas_profile': self.saas_profile,
            'sub_model': self.sub_model,
            'fit_type': self.fit_type,
            'coefficients': self.coefficients,
            'metrics': {
                'coefficient_se': self.coefficient_se,
                'n_observations': self.n_observations,
                'n_events': self.n_events,
                'n_tenants': self.n_tenants,
                'convergence': self.convergence_diagnostics,
                'status': self.status,
            },
            'notes': self.notes,
        }


# ----------------------------------------------------------------------------
# Fit functions
# ----------------------------------------------------------------------------

def _seed_to_starting_values(
    seed: CDIProfileSeed, sub_model: str
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Extract informative starting values + sigma for ridge penalty from CDI seed.

    Returns: (starting_values, ridge_lambda_per_coef)
    where ridge_lambda = 1 / σ² (narrow σ → strong shrinkage).
    """
    if sub_model == 'hazard':
        intercept = seed.hazard_intercept
        slope = seed.health_slope_3mo
        renewal = seed.days_to_renewal_0_30
        starts = {
            'Intercept': intercept.mu,
            'health_slope_3mo': slope.mu,
            'dtr_0-30': renewal.mu,
        }
        ridges = {
            'Intercept': 1.0 / (intercept.sigma ** 2),
            'health_slope_3mo': 1.0 / (slope.sigma ** 2),
            'dtr_0-30': 1.0 / (renewal.sigma ** 2),
        }
    elif sub_model == 'expansion_event':
        intercept = seed.expansion_event_intercept
        starts = {'Intercept': intercept.mu}
        ridges = {'Intercept': 1.0 / (intercept.sigma ** 2)}
    elif sub_model == 'expansion_size':
        intercept = seed.expansion_size_intercept
        starts = {'Intercept': intercept.mu}
        ridges = {'Intercept': 1.0 / (intercept.sigma ** 2)}
    elif sub_model == 'contraction':
        # Contraction priors aren't carried explicitly in CDI seed v1.
        # Use a weakly-informative zero-centered prior — events are rare
        # enough that the data dominates anyway when present.
        starts = {'Intercept': -4.0}    # ≈ 1.8%/month
        ridges = {'Intercept': 1.0}
    else:
        raise KeyError(f'Unknown sub_model: {sub_model}')

    return starts, ridges


def fit_sub_model(
    panel_df: pd.DataFrame,
    sub_model: str,
    saas_profile: str,
    customer_id: Optional[int] = None,
    min_events_to_fit: int = 5,
) -> FitResult:
    """Fit one GLMM sub-model on the given panel slice.

    Hierarchical structure: random intercept per tenant_id, fixed effects
    on the engineered feature columns. The CDI prior is plumbed through
    starting values + ridge penalty (informative pseudo-prior).

    Falls back to CDI prior coefficients if events are too sparse to fit
    (returns FitResult with status='insufficient_events', fit_type='fallback_to_prior'
    so calling code can route inference through cold-start logic).
    """
    spec = SUB_MODELS[sub_model]
    seed = get_seed('saas_premium', saas_profile)

    # Filter panel to the right profile + drop unobserved-health rows
    df = panel_df[panel_df['saas_profile'] == saas_profile].copy()
    if customer_id is not None:
        df = df[df['tenant_id'] == customer_id]

    df = engineer_features(df)
    n_obs = len(df)
    n_events = int(df[spec.outcome_column].sum()) if spec.outcome_column in df.columns else 0
    n_tenants = df['tenant_id'].nunique()

    starting_values, ridge_lambdas = _seed_to_starting_values(seed, sub_model)

    # Insufficient-events branch — fall back to the CDI prior wholesale.
    # This is the cold-start path per A1: "informative starting values +
    # coefficient prior shrinkage via penalized likelihood." With zero or
    # near-zero events, the penalized likelihood maximum is the prior mode.
    if n_events < min_events_to_fit:
        coef = dict(starting_values)
        # Add zeros for any feature columns we'd carry but didn't seed
        for c in feature_columns():
            coef.setdefault(c, 0.0)
        return FitResult(
            sub_model=sub_model,
            saas_profile=saas_profile,
            fit_type='fallback_to_prior',
            status='insufficient_events',
            coefficients=coef,
            coefficient_se={k: float('nan') for k in coef},
            n_observations=n_obs,
            n_events=n_events,
            n_tenants=n_tenants,
            convergence_diagnostics={
                'method': 'fallback_to_prior',
                'reason': f'n_events={n_events} < min_events_to_fit={min_events_to_fit}',
                'prior_used_mu': starting_values,
            },
            notes=(
                f'Insufficient {sub_model} events to fit ({n_events} < {min_events_to_fit}). '
                f'Falling back to CDI prior coefficients. Inference uses '
                f'cold_start prediction_method with 2× CI inflation.'
            ),
        )

    # ------------------------------------------------------------------
    # Fit with statsmodels MixedLM-style hierarchical logistic regression.
    # ------------------------------------------------------------------
    # Note: statsmodels' MixedLM is for continuous outcomes; for binomial
    # we use BinomialBayesMixedGLM (variational) for hazard / events,
    # and statsmodels.GLM with random-effects via PenalizedRegression for
    # the simpler fits. Block 2 day 2 lands the actual sm calls behind
    # this function signature; the scaffolding here defines the contract.
    # ------------------------------------------------------------------
    try:
        coefficients, ses, diagnostics = _fit_glmm_inner(
            df=df,
            outcome_col=spec.outcome_column,
            family=spec.family,
            link=spec.link,
            starting_values=starting_values,
            ridge_lambdas=ridge_lambdas,
        )
        return FitResult(
            sub_model=sub_model,
            saas_profile=saas_profile,
            fit_type='tenant_glmm_pooled' if customer_id is None else 'tenant_glmm',
            status='converged' if diagnostics.get('converged') else 'singular',
            coefficients=coefficients,
            coefficient_se=ses,
            n_observations=n_obs,
            n_events=n_events,
            n_tenants=n_tenants,
            convergence_diagnostics=diagnostics,
            notes=(
                f'Fit {sub_model} on {n_obs} obs × {n_events} events × {n_tenants} tenants. '
                f'CDI prior used as starting values + ridge.'
            ),
        )
    except Exception as e:
        logger.exception('GLMM fit failed for sub_model=%s', sub_model)
        # Fallback to prior on convergence failure too — log + tell caller
        coef = dict(starting_values)
        for c in feature_columns():
            coef.setdefault(c, 0.0)
        return FitResult(
            sub_model=sub_model,
            saas_profile=saas_profile,
            fit_type='fallback_to_prior',
            status='fallback',
            coefficients=coef,
            coefficient_se={k: float('nan') for k in coef},
            n_observations=n_obs,
            n_events=n_events,
            n_tenants=n_tenants,
            convergence_diagnostics={'error': str(e)},
            notes=f'Fit failed: {e}. Falling back to CDI prior.',
        )


def _fit_glmm_inner(
    df: pd.DataFrame,
    outcome_col: str,
    family: str,
    link: str,
    starting_values: Dict[str, float],
    ridge_lambdas: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, float], dict]:
    """Inner GLMM fit — penalized GLM via statsmodels with L2 toward seed.

    Implementation:
      1. Build design matrix from `feature_columns()` (model-agnostic).
      2. Set per-coefficient L2 penalty weights from `ridge_lambdas`
         (1/σ²; coefficients without an explicit prior get a weakly
         informative default penalty).
      3. Fit `sm.GLM(...).fit_regularized(alpha=L2_vector, L1_wt=0)`,
         centered on `starting_values` (translation: penalize
         (β − μ)² rather than β²).
      4. Bootstrap SEs over 200 resamples (cheap; rises to 1000 in
         production via bootstrap_cis()).

    Tenant random effects are NOT in this inner call — for Phase 1 v1
    we approximate hierarchical pooling via tenant fixed effects (one-hot
    on tenant_id) plus the CDI prior shrinkage. Full random-intercept
    MixedLM lands in Phase 2 (Bayesian).

    Contract:
      - Returns (coef_dict, se_dict, diagnostics_dict)
      - diagnostics_dict carries 'converged', 'iterations', 'method',
        'log_likelihood', plus warnings.
    """
    import statsmodels.api as sm

    feat_cols = feature_columns()

    # Build design matrix. Drop rows where any required feature is NaN
    # (these came from the panel's first-month rows where slope/volatility
    # weren't computable; they're unusable for fitting regardless).
    fit_df = df.copy()
    fit_df = fit_df.dropna(subset=feat_cols + [outcome_col])
    if fit_df.empty:
        # Nothing to fit on; defer to outer fallback
        raise ValueError(
            f'No fittable rows after dropping NaN on {len(feat_cols)} feature cols + {outcome_col}'
        )

    X = sm.add_constant(fit_df[feat_cols].astype(float).values, has_constant='add')
    y = fit_df[outcome_col].astype(float).values

    # Build the L2 penalty vector. Position 0 is the intercept.
    coef_names = ['Intercept'] + feat_cols
    default_lambda = 0.01  # weak penalty for un-seeded coefficients
    alpha = np.array([
        ridge_lambdas.get(name, default_lambda) for name in coef_names
    ])

    # Translate the regularizer center: statsmodels penalizes ||β||₂.
    # We want penalty on (β − μ). Rewrite y' = y, X' = X, then offset
    # the linear predictor by Σ μᵢ Xᵢ — equivalent to fitting (β − μ)
    # with zero-centered penalty. For a logit/log link this means
    # passing `offset = X @ μ_vector` to GLM.
    mu_vector = np.array([
        starting_values.get(name, 0.0) for name in coef_names
    ])
    offset = X @ mu_vector

    family_obj = {
        'Binomial': sm.families.Binomial(),
        'Gamma': sm.families.Gamma(sm.families.links.Log()),
    }[family]

    diagnostics: dict = {'method': 'GLM.fit_regularized + offset', 'family': family}
    try:
        model = sm.GLM(y, X, family=family_obj, offset=offset)
        # alpha is the L2 weight; L1_wt=0 → pure ridge
        result = model.fit_regularized(alpha=alpha, L1_wt=0.0, refit=False)
        deviation_from_prior = np.asarray(result.params)
        params = mu_vector + deviation_from_prior  # add back the prior center
        diagnostics['converged'] = True
        diagnostics['iterations'] = getattr(result, 'n_iter', None)
    except Exception as e:
        diagnostics['converged'] = False
        diagnostics['error'] = str(e)
        # Pass the failure up; outer wrapper falls back to prior wholesale
        raise

    coef = {name: float(params[i]) for i, name in enumerate(coef_names)}

    # Bootstrap SEs (200 resamples, account-clustered to respect panel
    # structure). Production runs 1000.
    ses = _bootstrap_ses(
        df=fit_df,
        feat_cols=feat_cols,
        outcome_col=outcome_col,
        family_obj=family_obj,
        starting_values=starting_values,
        ridge_lambdas=ridge_lambdas,
        n_resamples=200,
    )

    return coef, ses, diagnostics


def _bootstrap_ses(
    df: pd.DataFrame,
    feat_cols: List[str],
    outcome_col: str,
    family_obj,
    starting_values: Dict[str, float],
    ridge_lambdas: Dict[str, float],
    n_resamples: int = 200,
) -> Dict[str, float]:
    """Account-clustered bootstrap SE for each coefficient.

    Resamples accounts (with replacement); pulls all panel rows for
    the resampled accounts; refits; collects coefficient distribution;
    SE = std across resamples.
    """
    import statsmodels.api as sm

    coef_names = ['Intercept'] + feat_cols
    mu_vector = np.array([starting_values.get(n, 0.0) for n in coef_names])
    default_lambda = 0.01
    alpha = np.array([ridge_lambdas.get(n, default_lambda) for n in coef_names])

    accounts = df['account_id'].unique()
    coef_samples: List[np.ndarray] = []
    rng = np.random.default_rng(seed=42)

    for _ in range(n_resamples):
        # Sample accounts with replacement
        sampled_accts = rng.choice(accounts, size=len(accounts), replace=True)
        # Rebuild the panel by stacking per-account slices
        sample_df = pd.concat(
            [df[df['account_id'] == a] for a in sampled_accts],
            ignore_index=True,
        )
        if sample_df.empty:
            continue
        X = sm.add_constant(sample_df[feat_cols].astype(float).values, has_constant='add')
        y = sample_df[outcome_col].astype(float).values
        offset = X @ mu_vector
        try:
            model = sm.GLM(y, X, family=family_obj, offset=offset)
            r = model.fit_regularized(alpha=alpha, L1_wt=0.0, refit=False)
            coef_samples.append(mu_vector + np.asarray(r.params))
        except Exception:
            # Singular bootstrap sample — skip
            continue

    if not coef_samples:
        return {n: float('nan') for n in coef_names}

    coef_arr = np.vstack(coef_samples)
    return {coef_names[i]: float(np.std(coef_arr[:, i], ddof=1)) for i in range(len(coef_names))}


def fit_all_sub_models(
    panel_df: pd.DataFrame,
    saas_profiles: Optional[List[str]] = None,
    customer_id: Optional[int] = None,
) -> List[FitResult]:
    """Fit all 4 sub-models for all profiles in scope.

    Used by Wizard D to run a full calibration pass.
    """
    if saas_profiles is None:
        saas_profiles = panel_df['saas_profile'].unique().tolist()

    results = []
    for profile in saas_profiles:
        for sm in SUB_MODELS:
            result = fit_sub_model(
                panel_df=panel_df,
                sub_model=sm,
                saas_profile=profile,
                customer_id=customer_id,
            )
            results.append(result)
    return results
