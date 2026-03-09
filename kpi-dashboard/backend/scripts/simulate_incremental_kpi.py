#!/usr/bin/env python3
"""
Incremental KPI Simulation Script (Weight-Aware)
==================================================
Simulates N months of KPI/pillar score improvement for a given customer.
Uses pillar weights and Power-of-1 economic impact to weight improvements
so higher-impact pillars improve proportionally more, directly affecting ROI.

Usage:
  python scripts/simulate_incremental_kpi.py --customer_id 291 --months 6 --improvement 2.5
  python scripts/simulate_incremental_kpi.py --customer_id 292 --months 3 --improvement 4.0 --seed 99
  python scripts/simulate_incremental_kpi.py --customer_id 291 --months 6 --improvement 2.5 --dry-run

Arguments:
  --customer_id   Customer ID to simulate (required)
  --months        Number of months to simulate (default: 6)
  --improvement   Total improvement % over the period (default: 2.5)
  --noise         Noise std dev in pillar-score points/month (default: 0.3)
  --seed          Random seed for reproducibility (default: 42)
  --dry-run       Show what would be inserted without committing
"""
import argparse
import json
import math
import os
import random
import sys
from datetime import date
from dateutil.relativedelta import relativedelta

sys.path.insert(0, '.')
from app_v3_minimal import app
from models import db
from sqlalchemy import text


# ============================================================
# Pillar → Metric mapping and economic impact
# ============================================================
# Annual impact per 1% improvement at $10M ARR base (from power_of_1_economics.json)
PILLAR_IMPACT = {
    'P1': 61250,   # P1→TTFV: $61,250/pct
    'P2': 38000,   # P2→ticket_resolution_time: $38,000/pct
    'P3': 25000,   # P3→product_adoption: $25,000/pct
    'P4': 100000,  # P4→GRR: $100,000/pct
    'P5': 20000,   # P5→expansion_rate: $20,000/pct
    # NRR ($105K/pct) is synthesized from P4 (0.4) + P5 (0.6), so it amplifies both
}

# Bootstrap fallback weights (from kpi_definitions.DC2S_PILLARS)
# Only used if customer has no Wizard C calibrated weights in CustomerConfig
FALLBACK_PILLAR_WEIGHTS = {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}


def load_weights(customer_id):
    """
    Load pillar weights (L2) and KPI weights (L1) from the weight hierarchy:
      1. CustomerConfig DB (Wizard C calibrated) — single source of truth
      2. bootstrap_weights_config.json (per-customer file)
      3. kpi_definitions.DC2S_KPIS (canonical defaults)

    Returns:
        (pillar_weights, kpi_l1_weights)
        pillar_weights: {'P1': 0.15, 'P2': 0.20, ...}
        kpi_l1_weights: {'P1-KPI1': 0.20, 'P1-KPI2': 0.15, ...} per-KPI L1 weights
    """
    from models import CustomerConfig
    from pathlib import Path

    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()

    # --- L2 pillar weights ---
    pillar_weights = FALLBACK_PILLAR_WEIGHTS.copy()
    if config and config.dc2s_pillar_weights:
        pillar_weights = config.dc2s_pillar_weights

    # --- L1 KPI weights ---
    # Priority 1: CustomerConfig DB (Wizard C calibrated)
    kpi_l1_weights = {}
    if config and config.dc2s_kpi_weights:
        # DB stores as {'P1': {'P1-KPI1': 0.20, ...}} or flat {'P1-KPI1': 0.20, ...}
        db_kw = config.dc2s_kpi_weights
        if db_kw:
            for key, val in db_kw.items():
                if isinstance(val, dict):
                    # Nested by pillar: {'P1': {'P1-KPI1': 0.20}}
                    kpi_l1_weights.update(val)
                else:
                    # Flat: {'P1-KPI1': 0.20}
                    kpi_l1_weights[key] = val

    # Priority 2: bootstrap_weights_config.json
    if not kpi_l1_weights:
        cfg_path = Path(__file__).parent.parent / 'verticals' / f'customer{customer_id}-dc2_s' / 'journey' / 'config' / 'bootstrap_weights_config.json'
        if cfg_path.exists():
            with open(cfg_path) as f:
                bw = json.load(f)
            # Pick up L2 pillar weights if DB was empty
            raw_l2 = bw.get('pillar_weights_L2', {})
            if raw_l2 and pillar_weights == FALLBACK_PILLAR_WEIGHTS:
                for key, w in raw_l2.items():
                    pillar = key.split('_')[0]
                    pillar_weights[pillar] = w

    # Priority 3 (always): fill in from kpi_definitions as fallback for any missing KPIs
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
        for kpi_code, kpi_def in DC2S_KPIS.items():
            if kpi_code not in kpi_l1_weights:
                kpi_l1_weights[kpi_code] = kpi_def.get('weight_l1', 1.0 / 8)  # default equal
    except ImportError:
        pass

    return pillar_weights, kpi_l1_weights


def compute_pillar_improvement_weights(pillar_weights):
    """
    Combine L2 pillar weights (from Wizard C) with economic impact
    to get improvement allocation per pillar.
    Higher-weight + higher-impact pillars get proportionally more improvement.
    """
    raw = {}
    for p in pillar_weights:
        raw[p] = pillar_weights[p] * PILLAR_IMPACT.get(p, 25000)
    total = sum(raw.values())
    return {p: v / total for p, v in raw.items()}


def classify(score):
    """Health status from score using centralized thresholds."""
    if score < 50:
        return 'critical'
    if score < 70:
        return 'at_risk'
    return 'healthy'


def run_simulation(customer_id, months, improvement_pct, noise_std, seed, dry_run=False):
    random.seed(seed)

    with app.app_context():
        # Load weights from Wizard C source of truth (CustomerConfig → bootstrap_weights_config.json → fallback)
        pillar_weights, kpi_l1_weights = load_weights(customer_id)
        print(f"Pillar weights (L2, from Wizard C): {json.dumps(pillar_weights)}")
        if kpi_l1_weights:
            print(f"KPI weights (L1): loaded for {len(kpi_l1_weights)} pillars")
        else:
            print(f"KPI weights (L1): none found — uniform weighting within pillars")

        # Compute weighted improvement allocation per pillar
        pillar_alloc = compute_pillar_improvement_weights(pillar_weights)

        # Get accounts
        accts = [r[0] for r in db.session.execute(text(
            'SELECT account_id FROM accounts WHERE customer_id = :cid ORDER BY account_id'
        ), {'cid': customer_id}).fetchall()]

        if not accts:
            print(f"ERROR: No accounts found for customer_id={customer_id}")
            return

        # Get latest month
        latest_month = db.session.execute(text('''
            SELECT MAX(measurement_month) FROM pillar_scores ps
            JOIN accounts a ON ps.account_id = a.account_id
            WHERE a.customer_id = :cid
        '''), {'cid': customer_id}).scalar()

        if not latest_month:
            print(f"ERROR: No pillar_scores data for customer_id={customer_id}")
            return

        print(f"Customer {customer_id}: {len(accts)} accounts, latest month = {latest_month}")
        print(f"Simulating {months} months at {improvement_pct}% total improvement (noise={noise_std})")
        print(f"Pillar improvement allocation (weight-aware, from Wizard C):")
        for p in sorted(pillar_alloc):
            alloc = pillar_alloc[p]
            pts = improvement_pct * alloc * 5  # scale factor: each pillar gets alloc share, * 5 to normalize across 5 pillars
            print(f"  {p} (L2={pillar_weights.get(p, 0.20):.0%}, impact=${PILLAR_IMPACT.get(p, 0):,}/pct): alloc={alloc:.1%}, ~{pts:.2f} pts over {months}mo")
        if dry_run:
            print("*** DRY RUN — no data will be committed ***")

        # Load baseline pillar scores
        bp = {}
        for r in db.session.execute(text('''
            SELECT account_id, pillar_code, pillar_score, contributing_kpis, kpi_weights
            FROM pillar_scores WHERE measurement_month = :m AND account_id IN :accts
        '''), {'m': latest_month, 'accts': tuple(accts)}).fetchall():
            ckpis = r[3]
            kw = r[4]
            if isinstance(ckpis, dict):
                ckpis = json.dumps(ckpis)
            if isinstance(kw, dict):
                kw = json.dumps(kw)
            bp[(r[0], r[1])] = {'score': float(r[2]), 'ckpis': ckpis, 'kw': kw}

        # Load baseline KPI scores
        bk = {}
        for r in db.session.execute(text('''
            SELECT account_id, kpi_code, kpi_value, kpi_target, kpi_score, kpi_status
            FROM kpi_scores WHERE measurement_month = :m AND account_id IN :accts
        '''), {'m': latest_month, 'accts': tuple(accts)}).fetchall():
            bk[(r[0], r[1])] = {
                'value': float(r[2]) if r[2] else None,
                'target': float(r[3]) if r[3] else None,
                'score': float(r[4]) if r[4] else 50.0,
                'status': r[5]
            }

        # Figure out which KPIs belong to which pillar (from existing data pattern)
        kpi_to_pillar = {}
        for (aid, kc), kd in bk.items():
            # KPI code format: P1-KPI1, P2-KPI3, etc.
            if '-' in kc:
                pillar = kc.split('-')[0]
                kpi_to_pillar[kc] = pillar

        print(f"Baseline: {len(bp)} pillar rows, {len(bk)} KPI rows")

        pi, ki = 0, 0

        for mi in range(1, months + 1):
            sim_month = latest_month + relativedelta(months=mi)

            for aid in accts:
                # --- Pillar scores (weight-aware improvement) ---
                for pillar in ['P1', 'P2', 'P3', 'P4', 'P5']:
                    key = (aid, pillar)
                    if key not in bp:
                        continue
                    base = bp[key]['score']

                    # Weight-aware: each pillar gets its allocated share of total improvement
                    # multiply by 5 (number of pillars) so the WEIGHTED AVERAGE improvement = improvement_pct
                    pillar_total_improvement = improvement_pct * pillar_alloc[pillar] * 5
                    monthly_improvement = pillar_total_improvement / months
                    improvement = monthly_improvement * mi
                    noise = random.gauss(0, noise_std * math.sqrt(mi))
                    ns = max(0, min(100, base + improvement + noise))

                    if not dry_run:
                        db.session.execute(text('''
                            INSERT INTO pillar_scores
                              (account_id, measurement_month, pillar_code, pillar_score,
                               pillar_status, contributing_kpis, kpi_weights, calculated_at)
                            VALUES (:aid, :m, :pc, :ps, :st, :ck, :kw, NOW())
                        '''), {
                            'aid': aid, 'm': sim_month, 'pc': pillar,
                            'ps': round(ns, 1), 'st': classify(ns),
                            'ck': bp[key]['ckpis'], 'kw': bp[key]['kw']
                        })
                    pi += 1

                # --- KPI scores (L1 weight-aware within pillar) ---
                for (a, kc), kd in bk.items():
                    if a != aid:
                        continue
                    base_score = kd['score']

                    # Get this KPI's pillar and L1 weight
                    pillar = kpi_to_pillar.get(kc, 'P3')
                    pillar_total_improvement = improvement_pct * pillar_alloc.get(pillar, 0.2) * 5

                    # Apply L1 weight: higher-weighted KPIs within a pillar improve more
                    # Normalize by average L1 weight so the pillar-level improvement is preserved
                    l1_weight = kpi_l1_weights.get(kc, 1.0 / 8)
                    # Get all KPIs for this pillar to compute average weight
                    pillar_kpis = [k for k in kpi_to_pillar if kpi_to_pillar[k] == pillar]
                    avg_l1 = sum(kpi_l1_weights.get(k, 1.0/8) for k in pillar_kpis) / max(len(pillar_kpis), 1)
                    l1_scale = l1_weight / avg_l1 if avg_l1 > 0 else 1.0

                    monthly_improvement = (pillar_total_improvement * l1_scale) / months
                    improvement = monthly_improvement * mi
                    noise = random.gauss(0, noise_std * math.sqrt(mi))
                    ns = max(0, min(100, base_score + improvement + noise))

                    nv = kd['value']
                    if nv is not None and base_score > 0:
                        nv = round(nv * (ns / base_score), 2)

                    if not dry_run:
                        db.session.execute(text('''
                            INSERT INTO kpi_scores
                              (account_id, measurement_month, kpi_code, kpi_value,
                               kpi_target, kpi_score, kpi_status, calculated_at)
                            VALUES (:aid, :m, :kc, :kv, :kt, :ks, :st, NOW())
                        '''), {
                            'aid': aid, 'm': sim_month, 'kc': kc,
                            'kv': nv, 'kt': kd['target'],
                            'ks': round(ns, 1), 'st': classify(ns)
                        })
                    ki += 1

        if not dry_run:
            db.session.commit()

        sim_start = latest_month + relativedelta(months=1)
        sim_end = latest_month + relativedelta(months=months)
        print(f"\n{'Would insert' if dry_run else 'Inserted'}: {pi} pillar, {ki} KPI rows")
        print(f"Sim range: {sim_start} -> {sim_end}")

        # Show progression
        if not dry_run:
            print(f"\nPillar progression (avg across {len(accts)} accounts):")
            check_months = [latest_month, sim_start,
                            latest_month + relativedelta(months=months // 2),
                            sim_end]
            for cm in check_months:
                row = db.session.execute(text('''
                    SELECT ps.pillar_code, AVG(ps.pillar_score)
                    FROM pillar_scores ps JOIN accounts a ON ps.account_id = a.account_id
                    WHERE a.customer_id = :cid AND ps.measurement_month = :m
                    GROUP BY ps.pillar_code ORDER BY ps.pillar_code
                '''), {'cid': customer_id, 'm': cm}).fetchall()
                if row:
                    scores = ', '.join(f"{r[0]}={float(r[1]):.1f}" for r in row)
                    print(f"  {cm}: {scores}")

        return {
            'customer_id': customer_id,
            'months': months,
            'improvement_pct': improvement_pct,
            'pillar_rows': pi,
            'kpi_rows': ki,
            'sim_start': str(sim_start),
            'sim_end': str(sim_end),
            'pillar_allocation': {p: round(v, 4) for p, v in pillar_alloc.items()},
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulate incremental KPI improvement (weight-aware)')
    parser.add_argument('--customer_id', type=int, required=True, help='Customer ID')
    parser.add_argument('--months', type=int, default=6, help='Months to simulate (default: 6)')
    parser.add_argument('--improvement', type=float, default=2.5, help='Total improvement %% (default: 2.5)')
    parser.add_argument('--noise', type=float, default=0.3, help='Noise std dev (default: 0.3)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without inserting')
    args = parser.parse_args()

    result = run_simulation(
        customer_id=args.customer_id,
        months=args.months,
        improvement_pct=args.improvement,
        noise_std=args.noise,
        seed=args.seed,
        dry_run=args.dry_run,
    )
    if result:
        print(f"\nDone: {json.dumps(result, indent=2)}")
