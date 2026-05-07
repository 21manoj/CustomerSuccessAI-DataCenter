"""Wizard D — Predictor Calibrator (NRR Predictor v3, Phase 1).

Per Architecture Decision A2 in PLAN_nrr_predictor_v3.md, the predictor
splits offline calibration (Wizard D) from online inference
(`backend/predictor/`). This module is the offline-fit half.

Triggered:
  - Quarterly batch (cron, TBD)
  - Admin-trigger via `trigger_wizard` MCP tool with wizard='d'
  - Per-tenant after first real-customer outcome cohort lands

Effects:
  1. Build panel for target customer(s) via predictor.panel.build_panel
  2. Run predictor.glmm.fit_all_sub_models for all 4 sub-models × all
     saas_profiles in scope
  3. INSERT new PredictorCalibration rows (immutable history per A4 spirit)
  4. Flip previous active row(s) for that (customer, profile, sub_model)
     triple to is_active=False
  5. Return summary suitable for trigger_wizard MCP response

Per A6, all 4 sub-models (hazard, contraction, expansion_event,
expansion_size) get equal calibration discipline. Expansion is not a
follow-on.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Iterable, List, Optional

from extensions import db
from models import PredictorCalibration

logger = logging.getLogger(__name__)


def run_wizard_d(
    customer_ids: Optional[Iterable[int]] = None,
    fitted_by: str = 'wizard_d_auto',
    notes: str = '',
) -> dict:
    """Run Wizard D for the given customer ids.

    Parameters
    ----------
    customer_ids : iterable of int, optional
        Tenants to recalibrate. If None, runs against all SaaS tenants.
    fitted_by : str
        Identifier of the trigger source — 'wizard_d_auto' (cron),
        'admin_trigger', 'phase_1_5_acceptance', etc. Stored on each row.
    notes : str
        Free-text notes attached to every row written by this run.

    Returns
    -------
    dict summary suitable for MCP trigger_wizard response:
        {
          'wizard': 'd',
          'run_id': '<uuid>',
          'customer_ids': [...],
          'sub_models_calibrated': N,
          'fits_by_status': {'converged': X, 'fallback_to_prior': Y, ...},
          'started_at': iso, 'completed_at': iso,
          'calibrations': [
            {'calibration_id', 'customer_id', 'saas_profile', 'sub_model',
             'fit_type', 'status', 'n_obs', 'n_events'},
            ...
          ]
        }
    """
    from predictor.glmm import fit_all_sub_models
    from predictor.build_panel import build_panel

    run_id = f'wizard_d_{uuid.uuid4().hex[:12]}'
    started_at = datetime.utcnow()
    logger.info('Wizard D run %s starting for customer_ids=%s', run_id, customer_ids)

    # 1. Resolve customer scope
    if customer_ids is None:
        from models import Customer
        customer_ids = [
            c.customer_id for c in
            Customer.query.filter_by(vertical='saas_premium').all()
        ]
    customer_ids = list(customer_ids)
    if not customer_ids:
        return {
            'wizard': 'd',
            'run_id': run_id,
            'status': 'no_customers_in_scope',
            'started_at': started_at.isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
        }

    # 2. Build panel across all target customers (one shared panel — the
    #    GLMM uses tenant fixed effects to handle inter-tenant variance)
    panel_df = build_panel(customer_ids=customer_ids)
    if panel_df.empty:
        logger.warning('Wizard D %s: empty panel; aborting', run_id)
        return {
            'wizard': 'd',
            'run_id': run_id,
            'status': 'empty_panel',
            'customer_ids': customer_ids,
            'started_at': started_at.isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
        }

    # 3. Fit all 4 sub-models per saas_profile in scope.
    #    Note: passing customer_id=None fits a pooled model across all
    #    tenants of that profile (preferred for SaaS-SMB where many
    #    small tenants share segment characteristics). Per-tenant fits
    #    can be added in a follow-up when tenant data density justifies.
    saas_profiles = panel_df['saas_profile'].unique().tolist()
    all_results = []
    for profile in saas_profiles:
        # Pool across the customer set; the fit gets tenant fixed effects
        # implicitly through the panel
        results = fit_all_sub_models(
            panel_df=panel_df,
            saas_profiles=[profile],
            customer_id=None,
        )
        all_results.extend(results)

    # 4. Persist to PredictorCalibration (immutable + flip-active pattern)
    calibrations_written = []
    panel_summary = {
        'n_rows': int(len(panel_df)),
        'n_accounts': int(panel_df['account_id'].nunique()),
        'n_tenants': int(panel_df['tenant_id'].nunique()),
        'tenant_ids': sorted([int(t) for t in panel_df['tenant_id'].unique()]),
    }

    import math
    def _sanitize_floats(obj):
        """Recursively convert NaN/Inf to None for JSON column compatibility."""
        if isinstance(obj, dict):
            return {k: _sanitize_floats(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize_floats(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    for r in all_results:
        # Deactivate previous active row(s)
        prev_active = (
            PredictorCalibration.query
            .filter_by(
                customer_id=None,            # pooled fits use customer_id=NULL
                vertical='saas_premium',
                saas_profile=r.saas_profile,
                sub_model=r.sub_model,
                is_active=True,
            )
            .all()
        )
        for p in prev_active:
            p.is_active = False

        # Build coefficient + metrics blob, ensuring serializable
        coef_serializable = _sanitize_floats(
            {k: float(v) for k, v in r.coefficients.items()}
        )

        cal = PredictorCalibration(
            calibration_id=f'{run_id}__{r.saas_profile}__{r.sub_model}',
            customer_id=None,                # pooled fit
            vertical='saas_premium',
            saas_profile=r.saas_profile,
            sub_model=r.sub_model,
            fit_type=r.fit_type,
            coefficients=coef_serializable,
            prior_used=None,                 # captured separately in metrics
            metrics=_sanitize_floats({
                **({'coefficient_se': {k: float(v) for k, v in r.coefficient_se.items()}}
                   if r.coefficient_se else {}),
                'n_observations': r.n_observations,
                'n_events': r.n_events,
                'n_tenants': r.n_tenants,
                'convergence': r.convergence_diagnostics,
                'status': r.status,
            }),
            panel_summary=panel_summary,
            fit_started_at=started_at,
            fit_completed_at=datetime.utcnow(),
            fitted_by=fitted_by,
            notes=f'{notes}\n\n{r.notes}'.strip(),
            is_active=True,
        )
        db.session.add(cal)
        calibrations_written.append(cal)

    db.session.commit()
    logger.info(
        'Wizard D run %s wrote %d calibrations across %d profiles',
        run_id, len(calibrations_written), len(saas_profiles),
    )

    completed_at = datetime.utcnow()

    # 5. Build response
    fits_by_status: dict = {}
    for r in all_results:
        fits_by_status[r.status] = fits_by_status.get(r.status, 0) + 1

    return {
        'wizard': 'd',
        'run_id': run_id,
        'status': 'completed',
        'customer_ids': customer_ids,
        'started_at': started_at.isoformat(),
        'completed_at': completed_at.isoformat(),
        'duration_seconds': (completed_at - started_at).total_seconds(),
        'panel_summary': panel_summary,
        'sub_models_calibrated': len(calibrations_written),
        'fits_by_status': fits_by_status,
        'calibrations': [
            {
                'calibration_id': c.calibration_id,
                'customer_id': c.customer_id,
                'saas_profile': c.saas_profile,
                'sub_model': c.sub_model,
                'fit_type': c.fit_type,
                'status': c.metrics.get('status') if c.metrics else None,
                'n_obs': c.metrics.get('n_observations') if c.metrics else None,
                'n_events': c.metrics.get('n_events') if c.metrics else None,
            }
            for c in calibrations_written
        ],
    }


# ----------------------------------------------------------------------------
# trigger_wizard MCP integration
# ----------------------------------------------------------------------------

def register_with_trigger_wizard():
    """Register Wizard D with the trigger_wizard MCP dispatch.

    Called from cs_pulse_admin.py's trigger_wizard implementation when
    wizard='d'. Returns a dict of {wizard_letter: callable}.
    """
    return {'d': run_wizard_d}
