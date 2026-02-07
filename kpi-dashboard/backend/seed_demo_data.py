#!/usr/bin/env python3
"""
CS Pulse Demo Data Seeder
Creates 5 DC2_S accounts with 52-week KPI data, signals, and journey patterns.

Journey patterns:
  - crisis_recovery: starts critical, recovers over 20 weeks to healthy
  - near_churn_rescue: starts healthy, declines to critical around week 30, rescued
  - proactive_growth: stable healthy, steady expansion signals
  - slow_degradation: starts healthy, gradual decline (at-risk by week 52)
  - stable_steady: consistently healthy, minor fluctuations

Usage:
    DATABASE_URL=postgresql://... python3 seed_demo_data.py
"""

import os
import sys
import math
import random
from datetime import datetime, timedelta, date
from decimal import Decimal

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATABASE_URL', 'postgresql://cspulse:cspulse123@localhost:5432/cspulse')

from app_dc_demo import app, db
from models import Customer, User, Account, DC2SKPI, QualitativeSignal, CustomerConfig
from werkzeug.security import generate_password_hash

# ============================================================
# KPI RANGE SPECS (from kpi_definitions.py ranges)
# ============================================================
# Format: (healthy_mid, critical_mid, higher_is_better)
# We'll generate values that follow the journey pattern

KPI_SPECS = {
    # P1: Deployment Velocity
    'P1-KPI1': {'healthy': 7,   'risk': 17, 'critical': 40,  'hib': False, 'unit': 'days'},
    'P1-KPI2': {'healthy': 95,  'risk': 83, 'critical': 60,  'hib': True,  'unit': '%'},
    'P1-KPI3': {'healthy': 98,  'risk': 90, 'critical': 75,  'hib': True,  'unit': '%'},
    'P1-KPI4': {'healthy': 15,  'risk': 38, 'critical': 68,  'hib': False, 'unit': 'days'},
    'P1-KPI5': {'healthy': 3,   'risk': 11, 'critical': 22,  'hib': False, 'unit': 'days'},
    'P1-KPI6': {'healthy': 95,  'risk': 80, 'critical': 55,  'hib': True,  'unit': '%'},
    'P1-KPI7': {'healthy': 10,  'risk': 4,  'critical': 1,   'hib': True,  'unit': 'servers/day'},
    'P1-KPI8': {'healthy': 98,  'risk': 88, 'critical': 70,  'hib': True,  'unit': '%'},
    # P2: Operational Stability
    'P2-KPI1': {'healthy': 0.5, 'risk': 1.9, 'critical': 5,   'hib': False, 'unit': '%'},
    'P2-KPI2': {'healthy': 9000,'risk': 6500,'critical': 3000, 'hib': True,  'unit': 'hours'},
    'P2-KPI3': {'healthy': 0,   'risk': 2,   'critical': 8,   'hib': False, 'unit': 'count'},
    'P2-KPI4': {'healthy': 99.8,'risk': 99.0,'critical': 97,  'hib': True,  'unit': '%'},
    'P2-KPI5': {'healthy': 98,  'risk': 90,  'critical': 78,  'hib': True,  'unit': '%'},
    'P2-KPI6': {'healthy': 1.1, 'risk': 1.3, 'critical': 2.0, 'hib': False, 'unit': 'ratio'},
    'P2-KPI7': {'healthy': 2,   'risk': 8,   'critical': 40,  'hib': False, 'unit': 'hours'},
    'P2-KPI8': {'healthy': 98,  'risk': 88,  'critical': 70,  'hib': True,  'unit': '%'},
    # P3: AI Workload Performance
    'P3-KPI1': {'healthy': 80,  'risk': 55,  'critical': 30,  'hib': True,  'unit': '%'},
    'P3-KPI2': {'healthy': 95,  'risk': 83,  'critical': 60,  'hib': True,  'unit': '%'},
    'P3-KPI3': {'healthy': 25,  'risk': 75,  'critical': 300, 'hib': False, 'unit': 'ms'},
    'P3-KPI4': {'healthy': 12,  'risk': 36,  'critical': 100, 'hib': False, 'unit': 'hours'},
    'P3-KPI5': {'healthy': 90,  'risk': 70,  'critical': 45,  'hib': True,  'unit': '%'},
    'P3-KPI6': {'healthy': 92,  'risk': 78,  'critical': 55,  'hib': True,  'unit': '%'},
    'P3-KPI7': {'healthy': 6,   'risk': 2,   'critical': 1,   'hib': True,  'unit': 'count'},
    'P3-KPI8': {'healthy': 50000,'risk':7500, 'critical': 2000,'hib': True,  'unit': 'samples/hr'},
    # P4: Channel & Partner Health
    'P4-KPI1': {'healthy': 85,  'risk': 63,  'critical': 30,  'hib': True,  'unit': 'score'},
    'P4-KPI2': {'healthy': 90,  'risk': 70,  'critical': 40,  'hib': True,  'unit': 'score'},
    'P4-KPI3': {'healthy': 7,   'risk': 3,   'critical': 1,   'hib': True,  'unit': 'count'},
    'P4-KPI4': {'healthy': 10,  'risk': 35,  'critical': 75,  'hib': False, 'unit': 'score'},
    'P4-KPI5': {'healthy': 8,   'risk': 2,   'critical': 0,   'hib': True,  'unit': 'count'},
    'P4-KPI6': {'healthy': 75,  'risk': 25,  'critical': -50, 'hib': True,  'unit': 'score'},
    # P5: Expansion Readiness
    'P5-KPI1': {'healthy': 80,  'risk': 60,  'critical': 35,  'hib': True,  'unit': '%'},
    'P5-KPI2': {'healthy': 20,  'risk': 0,   'critical': -25, 'hib': True,  'unit': '%'},
    'P5-KPI3': {'healthy': 30,  'risk': 5,   'critical': -20, 'hib': True,  'unit': '%'},
    'P5-KPI4': {'healthy': 40,  'risk': 8,   'critical': -30, 'hib': True,  'unit': '%'},
    'P5-KPI5': {'healthy': 85,  'risk': 55,  'critical': 25,  'hib': True,  'unit': 'score'},
    'P5-KPI6': {'healthy': 5,   'risk': 1,   'critical': 0,   'hib': True,  'unit': 'count'},
    'P5-KPI7': {'healthy': 70,  'risk': 38,  'critical': 15,  'hib': True,  'unit': '%'},
    'P5-KPI8': {'healthy': 88,  'risk': 63,  'critical': 30,  'hib': True,  'unit': 'score'},
}

# ============================================================
# JOURNEY PATTERN FUNCTIONS
# Return a "health factor" 0.0 (critical) to 1.0 (healthy) for each week
# ============================================================

def pattern_crisis_recovery(week):
    """Starts critical (~0.1), recovers to healthy (~0.85) over 20 weeks, then stable."""
    if week <= 20:
        return 0.1 + 0.75 * (week / 20)
    return 0.85 + 0.05 * math.sin(week / 5)

def pattern_near_churn_rescue(week):
    """Healthy initially, declines to critical around week 28-32, then rescued."""
    if week <= 12:
        return 0.85 + 0.05 * math.sin(week / 3)
    elif week <= 30:
        # Decline
        t = (week - 12) / 18.0
        return 0.85 - 0.7 * t
    elif week <= 40:
        # Rescue phase
        t = (week - 30) / 10.0
        return 0.15 + 0.55 * t
    return 0.70 + 0.05 * math.sin(week / 4)

def pattern_proactive_growth(week):
    """Consistently healthy with slight upward trend."""
    return 0.80 + 0.15 * (week / 52) + 0.03 * math.sin(week / 6)

def pattern_slow_degradation(week):
    """Starts healthy, gradually declines to at-risk by week 52."""
    return 0.90 - 0.45 * (week / 52) + 0.03 * math.sin(week / 4)

def pattern_stable_steady(week):
    """Consistently healthy, minor noise."""
    return 0.78 + 0.07 * math.sin(week / 8) + 0.03 * math.cos(week / 3)


JOURNEY_PATTERNS = {
    'crisis_recovery': pattern_crisis_recovery,
    'near_churn_rescue': pattern_near_churn_rescue,
    'proactive_growth': pattern_proactive_growth,
    'slow_degradation': pattern_slow_degradation,
    'stable_steady': pattern_stable_steady,
}

# ============================================================
# DEMO ACCOUNTS
# ============================================================

DEMO_ACCOUNTS = [
    {
        'name': 'CloudScale AI Labs',
        'industry': 'AI Infrastructure',
        'region': 'US-West',
        'revenue': 15000000,
        'pattern': 'proactive_growth',
        'metadata': {
            'gpu_count': 256, 'gpu_model': 'H100',
            'deployment_type': 'on-premise', 'contract_term_months': 36,
            'primary_workload': 'LLM Training', 'data_center_location': 'San Jose, CA'
        }
    },
    {
        'name': 'Quantum Computing Corp',
        'industry': 'Research',
        'region': 'US-East',
        'revenue': 8500000,
        'pattern': 'near_churn_rescue',
        'metadata': {
            'gpu_count': 128, 'gpu_model': 'A100',
            'deployment_type': 'colocation', 'contract_term_months': 24,
            'primary_workload': 'Quantum Simulation', 'data_center_location': 'Ashburn, VA'
        }
    },
    {
        'name': 'MedTech Genomics',
        'industry': 'Healthcare',
        'region': 'EU-West',
        'revenue': 6200000,
        'pattern': 'crisis_recovery',
        'metadata': {
            'gpu_count': 64, 'gpu_model': 'H100',
            'deployment_type': 'hybrid', 'contract_term_months': 36,
            'primary_workload': 'Genomic Sequencing', 'data_center_location': 'Frankfurt, DE'
        }
    },
    {
        'name': 'FinServ Analytics Group',
        'industry': 'Financial Services',
        'region': 'US-East',
        'revenue': 12000000,
        'pattern': 'slow_degradation',
        'metadata': {
            'gpu_count': 192, 'gpu_model': 'H100',
            'deployment_type': 'on-premise', 'contract_term_months': 24,
            'primary_workload': 'Risk Modeling', 'data_center_location': 'Chicago, IL'
        }
    },
    {
        'name': 'AutoDrive Systems',
        'industry': 'Automotive',
        'region': 'US-West',
        'revenue': 9800000,
        'pattern': 'stable_steady',
        'metadata': {
            'gpu_count': 384, 'gpu_model': 'H100',
            'deployment_type': 'on-premise', 'contract_term_months': 48,
            'primary_workload': 'Autonomous Driving ML', 'data_center_location': 'Phoenix, AZ'
        }
    },
]


def generate_kpi_value(kpi_code, health_factor, noise=0.05):
    """Generate a KPI value based on health factor (0=critical, 1=healthy)."""
    spec = KPI_SPECS[kpi_code]
    h_val = spec['healthy']
    c_val = spec['critical']

    # Clamp health_factor
    hf = max(0.0, min(1.0, health_factor + random.gauss(0, noise)))

    # Interpolate between critical and healthy
    if spec['hib']:
        value = c_val + (h_val - c_val) * hf
    else:
        # Lower is better: healthy has smaller values
        value = h_val + (c_val - h_val) * (1 - hf)

    # Add a bit of noise
    value += random.gauss(0, abs(h_val - c_val) * 0.03)

    # Round appropriately
    if spec['unit'] in ('count', 'servers/day'):
        return max(0, round(value))
    elif spec['unit'] in ('hours',) and abs(value) > 100:
        return round(value)
    elif spec['unit'] == '%' and abs(value) > 10:
        return round(value, 1)
    return round(value, 2)


SIGNAL_TEMPLATES = {
    'positive': [
        ("email", "Customer expressed satisfaction with GPU performance and uptime"),
        ("meeting", "QBR completed successfully; discussed Phase 2 expansion plans"),
        ("email", "Team praised rapid deployment turnaround and support responsiveness"),
        ("meeting", "Technical review: workload optimization yielding 15% throughput improvement"),
        ("email", "Renewed contract interest discussed; expansion budget approved internally"),
    ],
    'negative': [
        ("escalation", "Performance degradation reported on training cluster; impacting SLAs"),
        ("email", "Customer expressed frustration with repeated GPU failures"),
        ("escalation", "Executive escalation: deployment timeline slipping behind schedule"),
        ("meeting", "Emergency call: production workloads failing, churn risk elevated"),
        ("email", "Budget freeze communicated; expansion plans on hold"),
    ],
    'neutral': [
        ("meeting", "Routine check-in; no major issues reported"),
        ("email", "Requested documentation for new workload type deployment"),
        ("meeting", "Technical training session completed for customer operations team"),
        ("email", "Infrastructure capacity planning review scheduled for next quarter"),
        ("meeting", "Monthly operations review; metrics stable, no action items"),
    ],
}


def generate_signals(account_id, pattern_fn, start_date, weeks=52):
    """Generate qualitative signals that match the journey pattern."""
    signals = []
    signal_counter = 0

    for week in range(1, weeks + 1):
        hf = pattern_fn(week)
        week_date = start_date + timedelta(weeks=week)

        # 1-3 signals per week
        n_signals = random.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]

        for _ in range(n_signals):
            signal_counter += 1
            signal_date = week_date + timedelta(days=random.randint(0, 6))

            # Choose sentiment based on health factor
            if hf >= 0.7:
                sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.5, 0.4, 0.1])[0]
            elif hf >= 0.4:
                sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.2, 0.4, 0.4])[0]
            else:
                sentiment = random.choices(['positive', 'neutral', 'negative'], weights=[0.05, 0.25, 0.7])[0]

            sig_type, content = random.choice(SIGNAL_TEMPLATES[sentiment])

            # Sentiment score: positive=0.6-1.0, neutral=0.3-0.6, negative=-0.5-0.2
            if sentiment == 'positive':
                score = round(random.uniform(0.6, 1.0), 2)
            elif sentiment == 'neutral':
                score = round(random.uniform(0.3, 0.6), 2)
            else:
                score = round(random.uniform(-0.5, 0.2), 2)

            signals.append(QualitativeSignal(
                signal_id=f'sig-{account_id}-{signal_counter}',
                account_id=account_id,
                signal_date=signal_date.date(),
                signal_type=sig_type,
                content=f"[Week {week}] {content}",
                sentiment=sentiment,
                sentiment_score=Decimal(str(score)),
                stakeholder_level=random.choice(['executive', 'director', 'manager', 'engineer']),
                stakeholder_title=random.choice(['VP Engineering', 'CTO', 'Director of AI', 'Infrastructure Lead', 'ML Platform Manager']),
                is_narrative_signal=True,
            ))

    return signals


def seed_data():
    """Main seeder function."""
    with app.app_context():
        print("Creating tables...")
        db.create_all()

        # Check if demo data already exists
        existing = Customer.query.filter_by(customer_name='CS Pulse DC Demo').first()
        if existing:
            print(f"Demo customer already exists (ID={existing.customer_id}). Cleaning up...")
            # Clean existing demo data
            accounts = Account.query.filter_by(customer_id=existing.customer_id).all()
            for acc in accounts:
                DC2SKPI.query.filter_by(account_id=acc.account_id).delete()
                QualitativeSignal.query.filter_by(account_id=acc.account_id).delete()
            Account.query.filter_by(customer_id=existing.customer_id).delete()
            User.query.filter_by(customer_id=existing.customer_id).delete()
            CustomerConfig.query.filter_by(customer_id=existing.customer_id).delete()
            Customer.query.filter_by(customer_id=existing.customer_id).delete()
            db.session.commit()
            print("Cleaned up existing demo data.")

        # 1. Create Customer
        customer = Customer(
            customer_name='CS Pulse DC Demo',
            email='demo@cspulse.ai',
            phone='+1-555-0100',
            domain='cspulse.ai',
            vertical='dc2_s',
        )
        db.session.add(customer)
        db.session.flush()
        cust_id = customer.customer_id
        print(f"Created customer: {customer.customer_name} (ID={cust_id})")

        # 2. Create User (login: demo@cspulse.ai / demo123)
        user = User(
            customer_id=cust_id,
            user_name='Demo CSM',
            email='demo@cspulse.ai',
            password_hash=generate_password_hash('demo123'),
            active=True,
            vertical='dc2_s',
            role='admin',
        )
        db.session.add(user)
        db.session.flush()
        print(f"Created user: {user.email} (password: demo123)")

        # 3. Create CustomerConfig with Gold-template defaults
        config = CustomerConfig(
            customer_id=cust_id,
            vertical='dc2_s',
            dc2s_pillar_weights={"P1": 0.15, "P2": 0.20, "P3": 0.25, "P4": 0.15, "P5": 0.25},
            kpi_upload_mode='corporate',
            config_version='1.0',
        )
        db.session.add(config)

        # 4. Create 5 Demo Accounts
        start_date = datetime(2025, 2, 1)  # 52 weeks back from ~Feb 2026
        all_kpis = []
        all_signals = []

        for i, acct_def in enumerate(DEMO_ACCOUNTS):
            account = Account(
                customer_id=cust_id,
                account_name=acct_def['name'],
                revenue=Decimal(str(acct_def['revenue'])),
                account_status='active',
                industry=acct_def['industry'],
                vertical='dc2_s',
                region=acct_def['region'],
                profile_metadata=acct_def['metadata'],
            )
            db.session.add(account)
            db.session.flush()
            acct_id = account.account_id
            print(f"  Account {i+1}: {acct_def['name']} (ID={acct_id}, pattern={acct_def['pattern']})")

            pattern_fn = JOURNEY_PATTERNS[acct_def['pattern']]

            # Generate 52 weeks of KPI data
            for week in range(1, 53):
                hf = pattern_fn(week)
                measured_at = start_date + timedelta(weeks=week)

                for kpi_code in KPI_SPECS.keys():
                    pillar = kpi_code.split('-')[0]
                    value = generate_kpi_value(kpi_code, hf)

                    kpi = DC2SKPI(
                        account_id=acct_id,
                        kpi_code=kpi_code,
                        value=Decimal(str(value)),
                        pillar=pillar,
                        measured_at=measured_at,
                    )
                    all_kpis.append(kpi)

            # Generate signals
            signals = generate_signals(acct_id, pattern_fn, start_date, weeks=52)
            all_signals.extend(signals)

        # Bulk insert KPIs
        print(f"\nInserting {len(all_kpis)} KPI measurements...")
        db.session.bulk_save_objects(all_kpis)

        print(f"Inserting {len(all_signals)} qualitative signals...")
        db.session.bulk_save_objects(all_signals)

        db.session.commit()

        # Summary
        total_accounts = Account.query.filter_by(customer_id=cust_id).count()
        total_kpis = DC2SKPI.query.join(Account).filter(Account.customer_id == cust_id).count()
        total_signals = QualitativeSignal.query.join(
            Account, QualitativeSignal.account_id == Account.account_id
        ).filter(Account.customer_id == cust_id).count()

        print(f"\n{'='*50}")
        print(f"Demo data seeded successfully!")
        print(f"  Customer: CS Pulse DC Demo (ID={cust_id})")
        print(f"  Login: demo@cspulse.ai / demo123")
        print(f"  Accounts: {total_accounts}")
        print(f"  KPI measurements: {total_kpis}")
        print(f"  Qualitative signals: {total_signals}")
        print(f"  Journey patterns: {', '.join(a['pattern'] for a in DEMO_ACCOUNTS)}")
        print(f"{'='*50}")


if __name__ == '__main__':
    random.seed(42)  # Reproducible demo data
    seed_data()
