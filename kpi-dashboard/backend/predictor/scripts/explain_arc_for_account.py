"""Explain how an account's arc was classified and how that arc shapes
the NRR predictor's output.

Audit-tier tool: print, in plain English, the chain
  signals observed → arc rule fired → arc_type → predictor coefficient
                  → contribution to linear predictor → prediction delta

Usage (inside cspulse-platform container):
    python predictor/scripts/explain_arc_for_account.py 3906
    python predictor/scripts/explain_arc_for_account.py 3915 --counterfactual=remove_signals

Designed to answer the audit question:
    "How are you modeling executive escalations and champion loss into NRR?"

Reads only — does NOT mutate predictor_calibrations or accounts.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import Counter
from pathlib import Path

# Allow running as a script from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _print_section(title: str) -> None:
    print()
    print('=' * 72)
    print(title)
    print('=' * 72)


def _format_signal_event(node_subtype, occurred_at, properties) -> str:
    title = (properties or {}).get('title', '') if isinstance(properties, dict) else ''
    return f'  {str(occurred_at)[:10]}  subtype={node_subtype:<28s}  {title[:50]}'


def explain(account_id: int, remove_signals: bool = False) -> None:
    from app_v3_minimal import app
    from extensions import db
    from sqlalchemy import text

    from utils.arc_classifier import (
        ARC_RULES,
        extract_features,
        _CHAMPION_CHANGE_SIGNALS,
        _CHAMPION_LOSS_SIGNALS,
        _STAKEHOLDER_CRISIS_SIGNALS,
        _BUDGET_SIGNALS,
        _COMPETITOR_SIGNALS,
        _INFRA_SIGNALS,
        _EXPANSION_SIGNALS,
    )
    from predictor.features import feature_columns

    with app.app_context():
        # ── Account meta ──
        row = db.session.execute(text(
            """
            SELECT account_id, customer_id, account_name, revenue, arc_type,
                   arc_phase, arc_confidence
            FROM accounts WHERE account_id = :aid
            """
        ), {'aid': account_id}).fetchone()
        if not row:
            print(f'No account_id={account_id}')
            return

        _print_section(f'Account {row[0]} — {row[2] or "(no name)"}  (Customer {row[1]})')
        print(f'ARR              ${row[3]:,.0f}' if row[3] else 'ARR              n/a')
        print(f'Stored arc_type  {row[4]} (confidence {row[6]}, phase {row[5] or "n/a"})')

        # ── Signals (raw evidence the classifier sees) ──
        sigs = db.session.execute(text(
            """
            SELECT node_subtype, occurred_at, properties
            FROM context_nodes
            WHERE account_id = :aid AND node_type = 'SIGNAL'
              AND occurred_at >= NOW() - INTERVAL '12 months'
            ORDER BY occurred_at
            """
        ), {'aid': account_id}).fetchall()

        _print_section(f'Signal evidence (last 12mo) — {len(sigs)} SIGNAL nodes')
        if sigs and not remove_signals:
            for s in sigs:
                print(_format_signal_event(*s))
        elif remove_signals:
            print('  [counterfactual: pretending NO signals were observed]')
        else:
            print('  (none)')

        # ── Classifier inputs ──
        try:
            features = extract_features(account_id, db.session)
        except Exception as e:
            print(f'extract_features failed: {e}')
            return

        if remove_signals:
            features['signal_types'] = Counter()
            features['has_stakeholder_departure'] = False

        _print_section('Classifier inputs (extract_features)')
        for k in [
            'health_now', 'slope_30d', 'slope_60d', 'days_to_renewal',
            'p1_delta_30d', 'has_stakeholder_departure',
        ]:
            v = features.get(k)
            if isinstance(v, float):
                print(f'  {k:<30s}: {v:+.2f}')
            else:
                print(f'  {k:<30s}: {v}')
        print(f'  {"signal_types":<30s}: {dict(features.get("signal_types", Counter()))}')

        # ── Rule cascade — show every rule and which fires first ──
        _print_section('Rule cascade (priority order — first match wins)')

        # Friendly labels for each rule (matches the ARC_RULES order in arc_classifier.py)
        rule_labels = [
            'exec_sponsor_change (explicit champion-change signal + at-risk)',
            'exec_sponsor_change (stakeholder-departure + slope decline)',
            'crisis_recovery    (low health + critical_incident + stakeholder)',
            'crisis_recovery    (very low health + critical_incident)',
            'stalled_deployment (infra signals + slope < -8)',
            'stalled_deployment (P1 pillar declining + flat overall)',
            'competitive_displacement (budget signals + slope decline)',
            'competitive_displacement (competitor signals + dtr<90)',
            'silent_churn       (rapid decline, no crisis, no champion loss)',
            'silent_churn       (mild decline in at-risk band)',
            'expansion_champion (healthy + positive slope + expansion signals)',
            'land_and_expand    (healthy + expansion signals)',
            'seasonal_surge     (healthy + stable)',
            'fallback           (always — competitive_displacement default)',
        ]

        matched_idx = None
        for i, ((arc_type, confidence, condition), label) in enumerate(zip(ARC_RULES, rule_labels)):
            try:
                fired = bool(condition(features))
            except Exception as e:
                fired = False
                label = label + f' [ERROR: {e}]'
            marker = '✓ MATCH' if fired and matched_idx is None else '  '
            if fired and matched_idx is None:
                matched_idx = i
            print(f'  Rule {i+1:>2d} | conf={confidence:.2f} | {marker} | {arc_type:<26s} | {label}')

        if matched_idx is None:
            print('  (no rules matched — should never happen given fallback rule)')
            return

        matched_arc, matched_conf, _ = ARC_RULES[matched_idx]

        _print_section('Predictor contribution (expansion_size sub-model)')
        # Pull active expansion_size coefficients
        from sqlalchemy import text as _text
        coef_row = db.session.execute(_text(
            """
            SELECT coefficients FROM predictor_calibrations
            WHERE sub_model='expansion_size' AND is_active=true
              AND saas_profile='saas_enterprise'
            ORDER BY created_at DESC LIMIT 1
            """
        )).fetchone()
        if not coef_row:
            print('  (no active expansion_size calibration found)')
            return
        coefs = coef_row[0]
        arc_dummy = f'arc_{matched_arc}'
        coef_val = coefs.get(arc_dummy, 0.0)
        print(f'  Selected arc:        {matched_arc}  →  feature `{arc_dummy}` = 1')
        print(f'  GLM coefficient:     {coef_val:+.4f}  (vs. land_and_expand reference)')
        print(f'  Contribution to LP:  {coef_val:+.4f}')
        if coef_val == 0:
            print(f'  Multiplier on E[size|event]: 1.000×  (this arc is reference or unfit)')
        else:
            mult = math.exp(coef_val)
            direction = 'larger' if mult > 1 else 'smaller'
            print(f'  Multiplier on E[size|event]: {mult:.3f}×  '
                  f'(this arc predicts {abs(mult-1)*100:.0f}% {direction} expansion'
                  f' than reference, all else equal)')

        # ── Counterfactual hint ──
        _print_section('Counterfactual')
        if remove_signals:
            print('  This run shows what arc would be picked if no signals existed.')
            print('  Compare to the live (with-signals) run by re-running without --counterfactual.')
        else:
            print('  To see what arc would be picked WITHOUT these signals, rerun with')
            print(f'    python predictor/scripts/explain_arc_for_account.py {account_id} --counterfactual=remove_signals')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('account_id', type=int, help='account_id to explain')
    parser.add_argument(
        '--counterfactual', choices=['remove_signals'], default=None,
        help='Recompute classifier as if no signals were present',
    )
    args = parser.parse_args()
    explain(args.account_id, remove_signals=(args.counterfactual == 'remove_signals'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
