#!/usr/bin/env python3
"""G3 — Sanity Report (Block 2 day 5).

Per PLAN_nrr_predictor_v3.md G3 (expanded to 30+ minutes), the
reviewer (Manoj) gut-checks 5 named accounts. Pass = 5/5 directionally
right. Fail = any one feels wrong → diagnose feature/segment/arc misspec.

This script:
  1. Triggers Wizard D for the target customers (writes calibrations)
  2. Runs predict_for_account_id for the 5 named accounts in both
     'renewal' and '12mo' horizons
  3. Renders a markdown artifact with predicted NRR + CI + decomposition
     + top drivers + A6 expansion_outlook for each account
  4. Side-by-side comparison: today's Wizard B legacy NRR vs predictor v3

Named accounts for customer 393 (per PLAN G3): Zermatt, Bernina,
Pilatus, Matterhorn, Denali.

Usage (from kpi-dashboard/backend, inside container):
    PYTHONPATH=. python predictor/scripts/g3_sanity_report.py 393
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


SANITY_ACCOUNTS_BY_CUSTOMER = {
    393: ['Zermatt Analytics', 'Bernina Health Systems', 'Pilatus Enterprise',
          'Matterhorn Digital', 'Denali Cloud Platform'],
    # Predictor V3 Demo SaaS Co — 5-account spectrum spanning expansion,
    # competitive_displacement, silent_churn, recovery, land_and_expand.
    395: ['Antares Holdings',         # expansion_champion, big lift expected
          'Cassiopeia Insurance',     # competitive_displacement → churned (definitive event present)
          'Lyra Media',               # silent_churn → churned (definitive event present)
          'Deneb Pharma',             # crisis_recovery, mid-recovery
          'Polaris Cloud'],           # land_and_expand, healthy whale
}


def render_account_block(prediction: dict, account_name: str) -> str:
    lines = [
        f'### {account_name} (account_id={prediction["account_id"]})',
        '',
        f'- **Horizon:** {prediction["horizon"]} ({prediction["horizon_months"]} months)',
        f'- **Prediction method:** `{prediction["prediction_method"]}`',
        f'- **Calibration:** `{prediction["calibration_id"]}`',
        f'- **Calibrated at:** {prediction.get("calibrated_at") or "(CDI seed only — no tenant fit yet)"}',
        '',
        f'**Expected NRR:** {prediction["expected_nrr"]["point"]:.3f} '
        f'(90% CI: {prediction["expected_nrr"]["lower_90"]:.3f} – '
        f'{prediction["expected_nrr"]["upper_90"]:.3f})',
        '',
        '**Term decomposition:**',
        '',
        '| Term | Value |',
        '|---|---|',
        f'| `p_churn_at_horizon` | {prediction["term_decomposition"]["p_churn_at_horizon"]:.3f} |',
        f'| `p_survive_at_horizon` | {prediction["term_decomposition"]["p_survive_at_horizon"]:.3f} |',
        f'| `e_contract_pct_given_survive` | {prediction["term_decomposition"]["e_contract_pct_given_survive"]:.3f} |',
        f'| `e_expand_pct_given_survive` | {prediction["term_decomposition"]["e_expand_pct_given_survive"]:.3f} |',
        '',
        '**Top NRR drivers:**',
        '',
    ]
    for d in prediction['term_decomposition']['top_drivers']:
        lines.append(f'- `{d["covariate"]}` → {d["contribution"]:+.4f}')
    lines.extend([
        '',
        '**A6 expansion outlook:**',
        '',
        f'- `p_expansion_event_horizon` = {prediction["expansion_outlook"]["p_expansion_event_horizon"]:.3f}',
        f'- `expected_size_pct_given_event` = {prediction["expansion_outlook"]["expected_size_pct_given_event"]:.3f}',
        f'- `expected_arr_lift` = ${prediction["expansion_outlook"]["expected_arr_lift"]:,.0f} '
        f'(CI: ${prediction["expansion_outlook"]["ci_lower_arr_lift"]:,.0f} – '
        f'${prediction["expansion_outlook"]["ci_upper_arr_lift"]:,.0f})',
        f'- `horizon_to_likely_event_months` = {prediction["expansion_outlook"]["horizon_to_likely_event_months"]}',
        '',
        '**Top expansion drivers:**',
        '',
    ])
    if prediction['expansion_outlook']['expansion_drivers']:
        for d in prediction['expansion_outlook']['expansion_drivers']:
            lines.append(f'- `{d["covariate"]}` → {d["contribution"]:+.4f}')
    else:
        lines.append('- (none — all expansion-positive coefficients are zero or absent)')
    lines.append('')
    return '\n'.join(lines)


def build_sanity_report(customer_id: int) -> str:
    from extensions import db
    from models import Account
    from predictor.inference import predict_for_account_id
    from wizards.wizard_d_predictor_calibrator import run_wizard_d

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f'# G3 — Sanity Report — Customer {customer_id}',
        '',
        f'*Generated {ts}.*',
        '',
        'Per PLAN_nrr_predictor_v3.md G3, reviewer gut-checks the 5 named ',
        'accounts below for directional correctness. Pass = 5/5 directionally ',
        'right. Fail on any account → diagnose feature / segment / arc misspec, ',
        'fix, re-run; **never "ship anyway."**',
        '',
        '## Step 1 — Trigger Wizard D (calibration pass)',
        '',
    ]

    wizard_d_response = run_wizard_d(
        customer_ids=[customer_id],
        fitted_by='g3_sanity_report',
        notes=f'Generated by g3_sanity_report.py for customer {customer_id}',
    )
    lines.extend([
        f'- run_id: `{wizard_d_response["run_id"]}`',
        f'- status: **{wizard_d_response["status"]}**',
        f'- sub_models_calibrated: {wizard_d_response.get("sub_models_calibrated", 0)}',
        f'- fits_by_status: `{wizard_d_response.get("fits_by_status", {})}`',
        f'- panel_summary: `{wizard_d_response.get("panel_summary", {})}`',
        f'- duration_seconds: {wizard_d_response.get("duration_seconds")}',
        '',
    ])

    if wizard_d_response['status'] != 'completed':
        lines.extend([
            '## Aborted',
            '',
            f'> Wizard D did not complete: status=`{wizard_d_response["status"]}`. '
            f'Cannot proceed to G3 sanity checks. Diagnose data shape first.',
            '',
        ])
        return '\n'.join(lines)

    # Look up account_ids for the named accounts
    sanity_names = SANITY_ACCOUNTS_BY_CUSTOMER.get(customer_id, [])
    if not sanity_names:
        lines.append(f'> No sanity-account list configured for customer_id={customer_id}.')
        return '\n'.join(lines)

    accts = (
        db.session.query(Account)
        .filter(Account.customer_id == customer_id, Account.account_name.in_(sanity_names))
        .all()
    )
    found_by_name = {a.account_name: a for a in accts}
    missing = [n for n in sanity_names if n not in found_by_name]

    lines.extend([
        '## Step 2 — Predictions for named accounts',
        '',
    ])
    if missing:
        lines.append(f'> WARNING: missing accounts in DB: {missing}')
        lines.append('')

    for name in sanity_names:
        if name not in found_by_name:
            continue
        acct = found_by_name[name]
        lines.append(f'## {name}')
        lines.append('')
        lines.append(f'- ARR: ${float(acct.revenue or 0):,.0f}')
        lines.append(f'- arc_type: `{acct.arc_type}`')
        lines.append('')
        for horizon in ('renewal', '12mo'):
            try:
                prediction = predict_for_account_id(
                    account_id=acct.account_id,
                    horizon=horizon,
                    db_session=db.session,
                )
                lines.append(render_account_block(prediction, name))
            except Exception as e:
                lines.append(f'### {name} — horizon={horizon} — **ERROR**')
                lines.append('')
                lines.append(f'> {type(e).__name__}: {e}')
                lines.append('')

    lines.extend([
        '---',
        '',
        '## Reviewer Checklist (5/5 required to pass G3)',
        '',
    ])
    for name in sanity_names:
        lines.append(f'- [ ] {name} — predicted NRR + decomposition direction matches gut?')
    lines.extend([
        '',
        '*Generated by `predictor/scripts/g3_sanity_report.py`.*',
    ])

    return '\n'.join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: g3_sanity_report.py <customer_id>')
        return 2
    customer_id = int(sys.argv[1])

    from app_v3_minimal import app

    with app.app_context():
        md = build_sanity_report(customer_id)
        out_dir = Path(__file__).resolve().parent.parent / 'sql'
        out_path = out_dir / f'g3_sanity_report__cust_{customer_id}.md'
        out_path.write_text(md)
        print(md)
        print(f'\n[Saved to {out_path}]')
    return 0


if __name__ == '__main__':
    sys.exit(main())
