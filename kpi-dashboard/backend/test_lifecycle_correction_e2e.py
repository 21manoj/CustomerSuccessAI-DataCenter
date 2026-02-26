#!/usr/bin/env python3
"""
E2E Test: 20-Account Lifecycle Health Correction
=================================================

Creates a customer with 20 accounts distributed as:
  - 20% Healthy  (Green)  = 4 accounts   (health score >= 85)
  - 40% At-Risk  (Orange) = 8 accounts   (health score 50-69)
  - 40% Critical (Red)    = 8 accounts   (health score < 50)

Then simulates a correction cycle where:
  - 50% of Critical  (4 accounts)  uplift → Orange (At-Risk)
  - 50% of Orange    (4 accounts)  uplift → Green  (Healthy)
  - 10% of Healthy   (1 account)   falls  → Orange (At-Risk)

Expected final distribution:
  - Healthy:  4 - 1 + 4 = 7  (35%)
  - At-Risk:  8 - 4 + 4 + 1 = 9  (45%)
  - Critical: 8 - 4 = 4          (20%)
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import random

sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from extensions import db
from models import (
    Customer, Account, CustomerConfig,
    DC2SKPI, KPIScore, PillarScore, HealthScore
)
from utils.score_calculator import ScoreCalculator, calculate_customer_scores, calculate_account_scores


# ============================================================================
# CONSTANTS
# ============================================================================

# Score thresholds (from score_calculator._determine_status)
#   excellent >= 85, good >= 70, warning >= 50, critical < 50
# For this test:
#   Healthy (Green)  = KPI values that produce score >= 85  →  actual_value >= target
#   At-Risk (Orange) = KPI values that produce score 50-69  →  actual_value ~= 42-59 (for target=85, range=[0,100])
#   Critical (Red)   = KPI values that produce score < 50   →  actual_value < 42

# KPI value presets (actual raw values; target=85, range=[0,100], operator='>')
# score = ((value - 0) / (85 - 0)) * 100 = value / 0.85
# For score=90 → value=76.5; score=50 → value=42.5; score=30 → value=25.5

KPI_CODES = [
    'AI-KPI1', 'AI-KPI2',
    'CH-KPI1', 'CH-KPI2',
    'DV-KPI1', 'DV-KPI2',
    'EX-KPI1', 'EX-KPI2',
    'OS-KPI1', 'OS-KPI2',
]

PILLAR_CODES = ['AI', 'CH', 'DV', 'EX', 'OS']

# Pillar weights for the test customer (must sum to 1.0)
PILLAR_WEIGHTS = {'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20}

# KPI weights per pillar (2 KPIs per pillar, equal weight)
KPI_WEIGHTS = {
    'AI': {'AI-KPI1': 0.5, 'AI-KPI2': 0.5},
    'CH': {'CH-KPI1': 0.5, 'CH-KPI2': 0.5},
    'DV': {'DV-KPI1': 0.5, 'DV-KPI2': 0.5},
    'EX': {'EX-KPI1': 0.5, 'EX-KPI2': 0.5},
    'OS': {'OS-KPI1': 0.5, 'OS-KPI2': 0.5},
}


def value_for_score(target_score: float, target: float = 85.0) -> float:
    """
    Reverse-engineer the raw KPI value needed to produce target_score.
    score = ((value - 0) / (target - 0)) * 100 = value * 100 / target
    value = score * target / 100
    """
    return round(target_score * target / 100.0, 2)


def jitter(base: float, pct: float = 0.03) -> float:
    """Add small random jitter to a value."""
    return round(base * (1 + random.uniform(-pct, pct)), 2)


# ============================================================================
# TEST SETUP
# ============================================================================

def create_test_customer():
    """Create a fresh test customer with 20 accounts and DC2_S config."""
    print("\n" + "=" * 70)
    print("STEP 1: Create test customer with 20 accounts")
    print("=" * 70)

    # Clean up any previous test run
    existing = Customer.query.filter_by(customer_name='Lifecycle Correction Test Corp').first()
    if existing:
        cid = existing.customer_id
        print(f"  Cleaning up previous run (customer_id={cid})...")
        HealthScore.query.filter(HealthScore.account_id.in_(
            db.session.query(Account.account_id).filter_by(customer_id=cid)
        )).delete(synchronize_session='fetch')
        PillarScore.query.filter(PillarScore.account_id.in_(
            db.session.query(Account.account_id).filter_by(customer_id=cid)
        )).delete(synchronize_session='fetch')
        KPIScore.query.filter(KPIScore.account_id.in_(
            db.session.query(Account.account_id).filter_by(customer_id=cid)
        )).delete(synchronize_session='fetch')
        DC2SKPI.query.filter(DC2SKPI.account_id.in_(
            db.session.query(Account.account_id).filter_by(customer_id=cid)
        )).delete(synchronize_session='fetch')
        Account.query.filter_by(customer_id=cid).delete()
        CustomerConfig.query.filter_by(customer_id=cid).delete()
        db.session.delete(existing)
        db.session.commit()
        print("  Cleaned up.")

    # Create customer
    customer = Customer(customer_name='Lifecycle Correction Test Corp', email='lifecycle@test.com')
    db.session.add(customer)
    db.session.flush()
    customer_id = customer.customer_id
    print(f"  Customer created: id={customer_id}")

    # Create DC2_S config with explicit weights
    config = CustomerConfig(
        customer_id=customer_id,
        vertical='dc2_s',
        dc2s_pillar_weights=PILLAR_WEIGHTS,
        dc2s_enabled_kpis=KPI_CODES,
        dc2s_kpi_weights=KPI_WEIGHTS,
        dc2s_kpi_definitions={},
        dc2s_kpi_overrides={}
    )
    db.session.add(config)

    # Create 20 accounts
    accounts = []
    envs = [
        'Production', 'Staging', 'Development', 'QA', 'UAT',
        'DR-Primary', 'DR-Secondary', 'Sandbox', 'Integration', 'Performance',
        'Lab-1', 'Lab-2', 'Edge-West', 'Edge-East', 'GPU-Cluster',
        'HPC-Node-A', 'HPC-Node-B', 'Archive', 'Analytics', 'ML-Training'
    ]
    for i in range(20):
        acct = Account(
            customer_id=customer_id,
            account_name=f'Lifecycle Test - {envs[i]}',
            account_status='active',
            vertical='dc2_s',
            industry='Data Center Infrastructure',
            region='us-west-2'
        )
        db.session.add(acct)
        db.session.flush()
        accounts.append(acct)

    db.session.commit()
    account_ids = [a.account_id for a in accounts]
    print(f"  Created 20 accounts: {account_ids[0]}..{account_ids[-1]}")
    return customer_id, account_ids


# ============================================================================
# KPI MEASUREMENT INSERTION
# ============================================================================

def insert_kpi_measurements(account_id: int, target_status: str, month: date):
    """
    Insert KPI measurements for an account to produce the target health status.

    target_status: 'healthy', 'at_risk', or 'critical'
    """
    # Map status → target KPI score (which determines health score)
    score_map = {
        'healthy':  92.0,   # produces excellent (>=85)
        'at_risk':  58.0,   # produces warning (50-69)
        'critical': 28.0,   # produces critical (<50)
    }

    target_score = score_map[target_status]

    # Delete existing measurements for this account+month
    month_start = month
    if month.month == 12:
        month_end = date(month.year + 1, 1, 1)
    else:
        month_end = date(month.year, month.month + 1, 1)

    DC2SKPI.query.filter(
        DC2SKPI.account_id == account_id,
        DC2SKPI.measured_at >= month_start,
        DC2SKPI.measured_at < month_end
    ).delete()

    # Insert 10 KPI measurements (2 per pillar)
    raw_value = value_for_score(target_score)
    measured_at = datetime(month.year, month.month, 15)  # mid-month

    for kpi_code in KPI_CODES:
        pillar = kpi_code.split('-')[0]
        kpi = DC2SKPI(
            account_id=account_id,
            kpi_code=kpi_code,
            value=Decimal(str(jitter(raw_value))),
            target=Decimal('85.0'),
            pillar=pillar,
            weight=Decimal('0.5'),
            measured_at=measured_at,
            status=target_status.replace('at_risk', 'warning')
        )
        db.session.add(kpi)

    db.session.flush()


# ============================================================================
# MAIN TEST
# ============================================================================

def run_test():
    """Execute the full lifecycle correction test."""
    with app.app_context():
        customer_id, account_ids = create_test_customer()

        # ==================================================================
        # PHASE 1: Initial distribution (Month 1 = Dec 2024)
        # ==================================================================
        month_1 = date(2024, 12, 1)

        print("\n" + "=" * 70)
        print("STEP 2: Insert initial KPI measurements (Month 1)")
        print("  Distribution: 4 Healthy, 8 At-Risk, 8 Critical")
        print("=" * 70)

        # Assign statuses: first 4 healthy, next 8 at-risk, last 8 critical
        healthy_ids  = account_ids[0:4]     # 4 healthy  (20%)
        at_risk_ids  = account_ids[4:12]    # 8 at-risk  (40%)
        critical_ids = account_ids[12:20]   # 8 critical (40%)

        for aid in healthy_ids:
            insert_kpi_measurements(aid, 'healthy', month_1)
        for aid in at_risk_ids:
            insert_kpi_measurements(aid, 'at_risk', month_1)
        for aid in critical_ids:
            insert_kpi_measurements(aid, 'critical', month_1)
        db.session.commit()
        print(f"  Inserted KPI measurements for 20 accounts")

        # Calculate scores
        print("\n" + "=" * 70)
        print("STEP 3: Calculate scores for Month 1")
        print("=" * 70)
        results_m1 = calculate_customer_scores(customer_id, month_1)
        successful_m1 = sum(1 for r in results_m1.values() if r and 'error' not in r)
        print(f"  Calculated: {successful_m1}/20 accounts")

        # Verify distribution
        print("\n" + "=" * 70)
        print("STEP 4: Verify initial distribution")
        print("=" * 70)

        dist_m1 = get_status_distribution(account_ids, month_1)
        print_distribution("Month 1 (Initial)", dist_m1)

        assert dist_m1['healthy'] == 4,  f"Expected 4 healthy, got {dist_m1['healthy']}"
        assert dist_m1['at_risk'] == 8,  f"Expected 8 at-risk, got {dist_m1['at_risk']}"
        assert dist_m1['critical'] == 8, f"Expected 8 critical, got {dist_m1['critical']}"
        print("  PASS: Initial distribution verified")

        # ==================================================================
        # PHASE 2: Correction cycle (Month 2 = Jan 2025)
        # ==================================================================
        month_2 = date(2025, 1, 1)

        print("\n" + "=" * 70)
        print("STEP 5: Apply corrections (Month 2)")
        print("  - 50% of Critical (4) uplift → At-Risk")
        print("  - 50% of At-Risk  (4) uplift → Healthy")
        print("  - 10% of Healthy  (1) falls  → At-Risk")
        print("=" * 70)

        # 50% of critical uplift to at-risk (first 4 of 8 critical)
        uplift_critical = critical_ids[:4]
        stay_critical   = critical_ids[4:]
        for aid in uplift_critical:
            insert_kpi_measurements(aid, 'at_risk', month_2)
        for aid in stay_critical:
            insert_kpi_measurements(aid, 'critical', month_2)
        print(f"  Critical: {len(uplift_critical)} uplifted → At-Risk, {len(stay_critical)} remain Critical")

        # 50% of at-risk uplift to healthy (first 4 of 8 at-risk)
        uplift_at_risk = at_risk_ids[:4]
        stay_at_risk   = at_risk_ids[4:]
        for aid in uplift_at_risk:
            insert_kpi_measurements(aid, 'healthy', month_2)
        for aid in stay_at_risk:
            insert_kpi_measurements(aid, 'at_risk', month_2)
        print(f"  At-Risk:  {len(uplift_at_risk)} uplifted → Healthy, {len(stay_at_risk)} remain At-Risk")

        # 10% of healthy fall to at-risk (1 of 4 healthy)
        fall_healthy   = healthy_ids[:1]
        stay_healthy   = healthy_ids[1:]
        for aid in fall_healthy:
            insert_kpi_measurements(aid, 'at_risk', month_2)
        for aid in stay_healthy:
            insert_kpi_measurements(aid, 'healthy', month_2)
        print(f"  Healthy:  {len(fall_healthy)} fell → At-Risk, {len(stay_healthy)} remain Healthy")

        db.session.commit()

        # Calculate scores for month 2
        print("\n" + "=" * 70)
        print("STEP 6: Calculate scores for Month 2")
        print("=" * 70)
        results_m2 = calculate_customer_scores(customer_id, month_2)
        successful_m2 = sum(1 for r in results_m2.values() if r and 'error' not in r)
        print(f"  Calculated: {successful_m2}/20 accounts")

        # ==================================================================
        # PHASE 3: Verify corrected distribution
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 7: Verify corrected distribution")
        print("=" * 70)

        dist_m2 = get_status_distribution(account_ids, month_2)
        print_distribution("Month 2 (After Correction)", dist_m2)

        # Expected: 7 healthy, 9 at-risk, 4 critical
        assert dist_m2['healthy'] == 7,  f"Expected 7 healthy, got {dist_m2['healthy']}"
        assert dist_m2['at_risk'] == 9,  f"Expected 9 at-risk, got {dist_m2['at_risk']}"
        assert dist_m2['critical'] == 4, f"Expected 4 critical, got {dist_m2['critical']}"
        print("  PASS: Corrected distribution verified")

        # ==================================================================
        # PHASE 4: Verify trends
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 8: Verify trends (Month 1 → Month 2)")
        print("=" * 70)

        trend_summary = verify_trends(account_ids, month_2,
                                      uplift_critical, uplift_at_risk, fall_healthy,
                                      stay_healthy, stay_at_risk, stay_critical)

        # ==================================================================
        # PHASE 5: Print summary report
        # ==================================================================
        print("\n" + "=" * 70)
        print("FINAL REPORT")
        print("=" * 70)

        print(f"\n  Customer ID: {customer_id}")
        print(f"  Accounts:    20")
        print()
        print(f"  {'Status':<12} {'Month 1':>10} {'Month 2':>10} {'Delta':>10}")
        print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
        for status in ['healthy', 'at_risk', 'critical']:
            label = {'healthy': 'Healthy', 'at_risk': 'At-Risk', 'critical': 'Critical'}[status]
            m1 = dist_m1[status]
            m2 = dist_m2[status]
            delta = m2 - m1
            color = '+' if delta > 0 else ''
            print(f"  {label:<12} {m1:>10} {m2:>10} {color}{delta:>9}")
        print()
        print(f"  Trends: {trend_summary['improving']} improving, "
              f"{trend_summary['declining']} declining, "
              f"{trend_summary['stable']} stable")

        print("\n" + "=" * 70)
        print("ALL ASSERTIONS PASSED")
        print("=" * 70)

        return {
            'customer_id': customer_id,
            'month_1_distribution': dist_m1,
            'month_2_distribution': dist_m2,
            'trends': trend_summary
        }


# ============================================================================
# HELPERS
# ============================================================================

def get_status_distribution(account_ids: list, month: date) -> dict:
    """Get health status distribution for accounts at a given month."""
    dist = {'healthy': 0, 'at_risk': 0, 'critical': 0, 'unknown': 0}

    for aid in account_ids:
        hs = HealthScore.query.filter_by(account_id=aid, measurement_month=month).first()
        if not hs:
            dist['unknown'] += 1
            continue

        score = float(hs.health_score)
        status = hs.health_status

        # Map status labels to our 3-tier buckets
        if status in ('excellent', 'good') or score >= 70:
            dist['healthy'] += 1
        elif status == 'warning' or (50 <= score < 70):
            dist['at_risk'] += 1
        else:
            dist['critical'] += 1

    return dist


def print_distribution(label: str, dist: dict):
    """Pretty-print a status distribution."""
    total = sum(dist.values())
    print(f"\n  {label}:")
    bar_width = 40

    for status, count in [('healthy', dist['healthy']),
                          ('at_risk', dist['at_risk']),
                          ('critical', dist['critical'])]:
        pct = count / total * 100 if total > 0 else 0
        bar_len = int(bar_width * count / total) if total > 0 else 0
        color_map = {'healthy': '\033[92m', 'at_risk': '\033[93m', 'critical': '\033[91m'}
        reset = '\033[0m'
        color = color_map.get(status, '')
        label_txt = {'healthy': 'Healthy ', 'at_risk': 'At-Risk ', 'critical': 'Critical'}[status]
        bar = color + '█' * bar_len + reset + '░' * (bar_width - bar_len)
        print(f"    {label_txt} [{bar}] {count:>2} ({pct:4.0f}%)")

    if dist.get('unknown', 0) > 0:
        print(f"    Unknown  : {dist['unknown']}")
    print()


def verify_trends(account_ids, month_2,
                  uplift_critical, uplift_at_risk, fall_healthy,
                  stay_healthy, stay_at_risk, stay_critical):
    """Verify health score trends after correction."""
    summary = {'improving': 0, 'declining': 0, 'stable': 0, 'no_trend': 0}

    # Accounts that should be improving (uplifted)
    for aid in uplift_critical + uplift_at_risk:
        hs = HealthScore.query.filter_by(account_id=aid, measurement_month=month_2).first()
        if hs and hs.trend == 'improving':
            summary['improving'] += 1
            print(f"    Account {aid}: {hs.trend:>10} ({hs.change_from_last_month:+.1f}) ✅ expected improving")
        elif hs and hs.trend:
            summary[hs.trend] += 1
            print(f"    Account {aid}: {hs.trend:>10} ({hs.change_from_last_month:+.1f}) ⚠️  expected improving")
        else:
            summary['no_trend'] += 1

    # Accounts that should be declining (fell from healthy)
    for aid in fall_healthy:
        hs = HealthScore.query.filter_by(account_id=aid, measurement_month=month_2).first()
        if hs and hs.trend == 'declining':
            summary['declining'] += 1
            print(f"    Account {aid}: {hs.trend:>10} ({hs.change_from_last_month:+.1f}) ✅ expected declining")
        elif hs and hs.trend:
            summary[hs.trend] += 1
            print(f"    Account {aid}: {hs.trend:>10} ({hs.change_from_last_month:+.1f}) ⚠️  expected declining")
        else:
            summary['no_trend'] += 1

    # Accounts that should be stable
    for aid in stay_healthy + stay_at_risk + stay_critical:
        hs = HealthScore.query.filter_by(account_id=aid, measurement_month=month_2).first()
        if hs and hs.trend:
            summary[hs.trend] += 1
            print(f"    Account {aid}: {hs.trend:>10} ({hs.change_from_last_month:+.1f})")
        else:
            summary['no_trend'] += 1

    return summary


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    try:
        result = run_test()
        print(f"\nTest result: {json.dumps(result, indent=2, default=str)}")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
