#!/usr/bin/env python3
"""
Setup Sacme & Tacme — Two enterprise customers with controlled ARR,
12-month historical data, context graph, and 6-month incremental simulation.

Sacme: 10 accounts, $50M total ARR
Tacme: 10 accounts, $500M total ARR

Usage:
    python3 setup_sacme_tacme.py [--base-url http://localhost:5059]

Login credentials created:
    - admin@sacme.com / test123
    - admin@tacme.com / test123
"""

import sys
import os
import json
import time
import random
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path

# Add load-driver to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import CSPulseClient

# Add backend to path for context graph generator
_backend_dir = str(Path(__file__).resolve().parent.parent / 'kpi-dashboard' / 'backend')
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────
BASE_URL = "http://localhost:5059"
PASSWORD = "test123"

CUSTOMERS = [
    {
        'name': 'Sacme',
        'email': 'admin@sacme.com',
        'password': PASSWORD,
        'num_accounts': 10,
        'total_arr': 50_000_000,      # $50M
        'arc_id': 'arc_expansion_champion',
    },
    {
        'name': 'Tacme',
        'email': 'admin@tacme.com',
        'password': PASSWORD,
        'num_accounts': 10,
        'total_arr': 500_000_000,     # $500M
        'arc_id': 'arc_land_and_expand',
    },
]

# Simulation settings
HISTORICAL_MONTHS = 12
INCREMENTAL_MONTHS = 6
SECONDS_PER_DAY = 2  # 2 seconds = 1 simulated day

# Story arc catalog for context graph (each customer uses one arc via config['arc_id'])
STORY_ARCS = [
    'arc_expansion_champion',
    'arc_land_and_expand',
    'arc_crisis_recovery',
    'arc_silent_churn',
    'arc_competitive_displacement',
    'arc_stalled_deployment',
    'arc_seasonal_surge',
    'arc_exec_sponsor_change',
]

# Load KPI catalog
try:
    from catalog_loader import get_kpi_list_for_load_driver, get_kpi_target
    DC2S_KPIS = get_kpi_list_for_load_driver()
    logger.info(f"Loaded {len(DC2S_KPIS)} KPIs from catalog")
except Exception as e:
    logger.warning(f"Catalog load failed: {e}, using fallback")
    DC2S_KPIS = [
        {'code': f'{p}-KPI{i}', 'name': f'{p}-KPI{i}', 'pillar': p, 'weight': 0.125, 'unit': '%'}
        for p in ['P1', 'P2', 'P3', 'P4', 'P5'] for i in range(1, 9)
    ]


def distribute_arr(total_arr: float, num_accounts: int, seed: int = 42) -> list:
    """Distribute total ARR across accounts with realistic enterprise mix.

    ~30% in top 2 accounts, ~50% in middle 5, ~20% in bottom 3.
    """
    rng = random.Random(seed)

    # Create weight distribution (Pareto-like)
    raw_weights = [rng.paretovariate(1.5) for _ in range(num_accounts)]
    total_weight = sum(raw_weights)

    # Sort descending (largest accounts first) and scale to total ARR
    raw_weights.sort(reverse=True)
    arr_values = [round(w / total_weight * total_arr, 0) for w in raw_weights]

    # Adjust rounding to match total exactly
    diff = total_arr - sum(arr_values)
    arr_values[0] += diff

    return arr_values


def generate_accounts_csv(customer_id: int, customer_name: str,
                          num_accounts: int, arr_values: list) -> str:
    """Generate accounts.csv with controlled ARR distribution."""
    import csv
    import io
    import uuid as uuid_mod

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'account_id', 'customer_id', 'account_name', 'industry', 'region',
        'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
        'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid'
    ])

    envs = ['Production', 'Staging', 'Development', 'Analytics', 'AI-Training',
            'Edge-Compute', 'DR-Backup', 'Testing', 'Research', 'Integration']
    industries = ['Technology', 'Financial Services', 'Healthcare', 'Manufacturing',
                  'Retail', 'Energy', 'Telecommunications', 'Government', 'Education', 'Media']
    regions = ['North America', 'EMEA', 'APAC', 'LATAM']
    csm_names = ['Sarah Chen', 'Mike Johnson', 'Lisa Park', 'David Kim', 'Emma Wilson']

    account_base = customer_id * 1000 + 1

    for i in range(num_accounts):
        account_id = account_base + i
        arr = arr_values[i]

        # Tier based on ARR
        if arr >= 10_000_000:
            tier = 'Enterprise'
        elif arr >= 1_000_000:
            tier = 'Mid-Market'
        else:
            tier = 'SMB'

        contract_start = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 90))
        contract_end = contract_start + timedelta(days=365)
        renewal_date = contract_end - timedelta(days=30)

        csm = random.choice(csm_names)
        status = random.choices(['active', 'active', 'active', 'at_risk'], weights=[0.7, 0.1, 0.1, 0.1])[0]

        writer.writerow([
            account_id, customer_id,
            f"{customer_name}-{envs[i]}",
            industries[i],
            random.choice(regions),
            'dc2_s', tier,
            int(arr), int(arr),
            contract_start.strftime('%Y-%m-%d'),
            contract_end.strftime('%Y-%m-%d'),
            renewal_date.strftime('%Y-%m-%d'),
            csm,
            f"{csm.lower().replace(' ', '.')}@{customer_name.lower()}.com",
            status,
            f'dc_acct_{uuid_mod.uuid4().hex[:12]}',
        ])

    return output.getvalue()


def generate_kpi_csv(customer_id: int, num_accounts: int, months: int = 12) -> str:
    """Generate kpi_measurements.csv with N months of historical data."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'account_id', 'kpi_code', 'kpi_name', 'pillar',
        'measured_at', 'value', 'target', 'weight', 'unit', 'status'
    ])

    account_base = customer_id * 1000 + 1
    # Start 12 months ago from today
    base_date = datetime(2025, 3, 1)  # Mar 2025 for 12 months through Feb 2026

    # Drift profiles per account (realistic mix)
    profiles = ['healthy', 'healthy', 'healthy', 'improving', 'improving',
                'stable', 'declining', 'recovering', 'seasonal', 'critical']

    for i in range(num_accounts):
        account_id = account_base + i
        profile = profiles[i % len(profiles)]

        for month_offset in range(months):
            measured_at = (base_date + timedelta(days=30 * month_offset)).strftime('%Y-%m-%d')

            for kpi in DC2S_KPIS:
                target = _get_target(kpi['code'])
                value = _generate_value(kpi['code'], target, month_offset, profile)
                status = _classify_status(value, target, kpi['code'])

                writer.writerow([
                    account_id, kpi['code'], kpi['name'], kpi['pillar'],
                    measured_at, round(value, 2), round(target, 2),
                    kpi['weight'], kpi['unit'], status
                ])

    return output.getvalue()


def generate_enhanced_qualitative_signals_csv(customer_id: int, num_accounts: int,
                                               months: int = 12) -> str:
    """Generate enhanced_qualitative_signals.csv with scenario-aware signals
    and optional graph metadata columns."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'signal_id', 'account_id', 'signal_date', 'signal_type',
        'content', 'sentiment', 'sentiment_score',
        'arc_id', 'story_phase', 'linked_node_id'
    ])

    signal_types = ['customer_feedback', 'meeting', 'milestone', 'health_check', 'incident']

    positive_signals = [
        'GPU utilization continues to increase month over month',
        'Successful deployment of new AI training workloads',
        'Executive sponsor very engaged in QBR',
        'Customer exploring expansion into inference workloads',
        'Renewal discussions progressing positively',
        'New data center buildout approved by customer',
        'Customer reference case study approved',
        'Technical architecture review exceeded expectations',
    ]
    neutral_signals = [
        'Routine maintenance completed on schedule',
        'Standard QBR conducted with all stakeholders',
        'No significant changes in workload patterns',
        'Renewal discussion progressing normally',
        'Staff training completed for new features',
    ]
    negative_signals = [
        'Increase in support ticket volume observed',
        'Executive sponsor missed scheduled QBR',
        'GPU utilization trending downward',
        'Competitor mentioned in stakeholder conversation',
        'Budget review flagged by customer CFO',
        'Delayed migration timeline impacting ROI',
    ]

    account_base = customer_id * 1000 + 1
    base_date = datetime(2025, 3, 1)
    counter = 0

    for i in range(num_accounts):
        account_id = account_base + i
        for month_offset in range(months):
            num_signals = random.randint(2, 4)
            for _ in range(num_signals):
                counter += 1
                signal_date = base_date + timedelta(days=30 * month_offset + random.randint(0, 29))

                sentiment = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.5, 0.3, 0.2]
                )[0]

                if sentiment == 'positive':
                    content = random.choice(positive_signals)
                    score = round(random.uniform(0.5, 0.95), 2)
                elif sentiment == 'neutral':
                    content = random.choice(neutral_signals)
                    score = round(random.uniform(0.0, 0.3), 2)
                else:
                    content = random.choice(negative_signals)
                    score = round(random.uniform(-0.9, -0.3), 2)

                writer.writerow([
                    f'sig_{account_id}_{counter}',
                    account_id,
                    signal_date.strftime('%Y-%m-%d'),
                    random.choice(signal_types),
                    content, sentiment, score,
                    '',   # arc_id — populated by context graph pipeline
                    '',   # story_phase — populated by context graph pipeline
                    '',   # linked_node_id — populated by context graph pipeline
                ])

    return output.getvalue()


def generate_products_csv(customer_id: int, num_accounts: int) -> str:
    """Generate products.csv."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'account_id', 'product_name', 'product_category',
        'quantity', 'unit_price', 'deployment_date', 'status'
    ])

    products = [
        ('GPU Compute Cluster', 'Compute'),
        ('AI Training Platform', 'AI/ML'),
        ('Inference Engine', 'AI/ML'),
        ('Data Lake Storage', 'Storage'),
        ('Edge Deployment Kit', 'Edge'),
        ('Network Fabric Controller', 'Networking'),
        ('Cooling Management System', 'Facilities'),
        ('Power Distribution Unit', 'Facilities'),
        ('Security Gateway', 'Security'),
        ('Monitoring Dashboard', 'Observability'),
    ]

    account_base = customer_id * 1000 + 1

    for i in range(num_accounts):
        account_id = account_base + i
        num_products = random.randint(2, 5)
        selected = random.sample(products, min(num_products, len(products)))

        for prod_name, prod_cat in selected:
            deploy_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
            writer.writerow([
                account_id, prod_name, prod_cat,
                random.randint(1, 100),
                round(random.uniform(5000, 100000), 2),
                deploy_date.strftime('%Y-%m-%d'),
                random.choice(['active', 'active', 'active', 'provisioning']),
            ])

    return output.getvalue()


def generate_contacts_csv(customer_id: int, num_accounts: int,
                          customer_name: str) -> str:
    """Generate contacts.csv."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'account_id', 'contact_name', 'contact_email',
        'role', 'department', 'is_primary'
    ])

    roles = ['VP Engineering', 'CTO', 'Director IT', 'Data Center Manager',
             'Cloud Architect', 'Infrastructure Lead', 'DevOps Manager',
             'Procurement Manager', 'CFO']
    departments = ['Engineering', 'IT', 'Operations', 'Infrastructure', 'Finance', 'Executive']
    contact_names = ['Pat Johnson', 'Sam Williams', 'Alex Brown', 'Jordan Davis',
                     'Taylor Wilson', 'Casey Miller', 'Morgan Garcia', 'Riley Martinez',
                     'Quinn Anderson', 'Drew Thomas']

    account_base = customer_id * 1000 + 1

    for i in range(num_accounts):
        account_id = account_base + i
        num_contacts = random.randint(2, 4)

        for j in range(num_contacts):
            name = random.choice(contact_names)
            writer.writerow([
                account_id, name,
                f"{name.lower().replace(' ', '.')}@{customer_name.lower()}.com",
                random.choice(roles),
                random.choice(departments),
                'true' if j == 0 else 'false',
            ])

    return output.getvalue()


# ── KPI value helpers ──────────────────────────────────────────────────

KPI_TARGETS = {
    'P1-KPI1': 14, 'P1-KPI2': 4, 'P1-KPI3': 90, 'P1-KPI4': 10, 'P1-KPI5': 2,
    'P1-KPI6': 95, 'P1-KPI7': 85, 'P1-KPI8': 90,
    'P2-KPI1': 99.9, 'P2-KPI2': 30, 'P2-KPI3': 3, 'P2-KPI4': 80, 'P2-KPI5': 99.5,
    'P2-KPI6': 4, 'P2-KPI7': 2, 'P2-KPI8': 500,
    'P3-KPI1': 85, 'P3-KPI2': 95, 'P3-KPI3': 50, 'P3-KPI4': 200,
    'P3-KPI5': 99, 'P3-KPI6': 80, 'P3-KPI7': 90, 'P3-KPI8': 12,
    'P4-KPI1': 80, 'P4-KPI2': 4, 'P4-KPI3': 85, 'P4-KPI4': 60,
    'P4-KPI5': 90, 'P4-KPI6': 30, 'P4-KPI7': 50, 'P4-KPI8': 4.5,
    'P5-KPI1': 75, 'P5-KPI2': 12, 'P5-KPI3': 500000, 'P5-KPI4': 85,
    'P5-KPI5': 30, 'P5-KPI6': 90, 'P5-KPI7': 25, 'P5-KPI8': 95,
}

LOWER_IS_BETTER = {
    'P1-KPI1', 'P1-KPI2', 'P1-KPI4', 'P1-KPI5',
    'P2-KPI2', 'P2-KPI3', 'P2-KPI6', 'P2-KPI7',
    'P3-KPI3', 'P3-KPI4',
    'P4-KPI4',
}


def _get_target(kpi_code: str) -> float:
    try:
        return get_kpi_target(kpi_code)
    except Exception:
        return KPI_TARGETS.get(kpi_code, 85.0)


def _generate_value(kpi_code: str, target: float, month: int, profile: str) -> float:
    """Generate KPI value with drift profile."""
    noise = random.gauss(0, 2.0)

    if profile == 'healthy':
        drift = month * 0.3 + noise
    elif profile == 'improving':
        drift = month * 1.5 + noise
    elif profile == 'stable':
        drift = noise
    elif profile == 'declining':
        drift = -month * 1.2 + noise
    elif profile == 'recovering':
        drift = -10 + month * 2.0 + noise
    elif profile == 'seasonal':
        drift = 8.0 * math.sin(2 * math.pi * month / 6) + noise
    elif profile == 'critical':
        if month <= 3:
            drift = -month * 4.0 + noise
        else:
            drift = -12.0 + noise * 0.5
    else:
        drift = noise

    if kpi_code in LOWER_IS_BETTER:
        value = target - drift  # Lower values = better performance
    else:
        value = target + drift

    # Clamp to reasonable ranges
    if kpi_code in ('P2-KPI1', 'P2-KPI5', 'P1-KPI6'):
        value = max(90, min(100, value))
    elif 'KPI' in kpi_code and kpi_code not in ('P5-KPI3', 'P3-KPI4', 'P2-KPI8'):
        value = max(0, min(100, value))
    else:
        value = max(0, value)

    return value


def _classify_status(value: float, target: float, kpi_code: str) -> str:
    if kpi_code in LOWER_IS_BETTER:
        ratio = value / target if target > 0 else 1.0
        if ratio <= 1.0:
            return 'healthy'
        elif ratio <= 1.5:
            return 'risk'
        else:
            return 'critical'
    else:
        score = min(100, (value / target) * 100) if target > 0 else 50
        if score >= 70:
            return 'healthy'
        elif score >= 50:
            return 'risk'
        else:
            return 'critical'


# ── Main setup flow ────────────────────────────────────────────────────

def setup_customer(client: CSPulseClient, config: dict) -> dict:
    """Full setup for one customer: register → upload CSVs → process → context graph → scores."""

    name = config['name']
    email = config['email']
    password = config['password']
    num_accounts = config['num_accounts']
    total_arr = config['total_arr']
    arc_id = config['arc_id']

    result = {'name': name, 'email': email, 'errors': []}

    logger.info(f"\n{'='*70}")
    logger.info(f"Setting up {name}: {num_accounts} accounts, ${total_arr:,.0f} ARR")
    logger.info(f"{'='*70}")

    # ── Step 1: Register customer via /api/onboarding/complete ──
    logger.info(f"  Step 1: Creating customer via onboarding/complete...")

    client.timeout = 300
    complete_resp = client.post('/api/onboarding/complete', {
        'customer_name': name,
        'email': email,
        'password': password,
        'num_accounts': num_accounts,
        'vertical': 'dc2_s',
        'onboarding_mode': 'demo',
        'industry': 'Technology',
    }, skip_auth_check=True)

    if not complete_resp or not complete_resp.get('success'):
        logger.error(f"    FAILED: {complete_resp}")
        result['errors'].append(f"Onboarding failed: {complete_resp}")
        return result

    customer_id = complete_resp.get('customer_id')
    customer_uuid = complete_resp.get('customer_uuid')
    accounts_created = complete_resp.get('accounts', 0)
    logger.info(f"    OK: Customer {customer_id} created ({accounts_created} accounts)")
    result['customer_id'] = customer_id
    result['customer_uuid'] = customer_uuid

    # ── Step 2: Login as the new customer ──
    logger.info(f"  Step 2: Logging in as {email}...")
    cust_client = CSPulseClient(
        base_url=client.base_url,
        email=email,
        password=password,
        customer_id=customer_id,
        timeout=300
    )
    login_ok = cust_client.login()
    if not login_ok:
        logger.warning(f"    Login failed, continuing with unauthenticated calls")
        cust_client._authenticated = True
    else:
        logger.info(f"    OK: Logged in")

    # Fetch real account IDs (created by onboarding in Step 1)
    real_account_ids = None
    try:
        accounts_list = cust_client.get_accounts()
        if accounts_list:
            real_account_ids = [acc.get('account_id') for acc in accounts_list]
            logger.info(f"    Fetched {len(real_account_ids)} real account IDs from API")
    except Exception as e:
        logger.warning(f"    Could not fetch account IDs: {e}")

    # ── Step 3: Upload custom CSVs with controlled ARR ──
    logger.info(f"  Step 3: Generating & uploading CSVs with ${total_arr:,.0f} ARR...")

    arr_values = distribute_arr(total_arr, num_accounts, seed=hash(name) % 10000)
    logger.info(f"    ARR distribution: {[f'${v:,.0f}' for v in arr_values]}")

    # Generate 5 base CSVs (profiles.csv removed — merged into account_business_profiles)
    csvs = {
        'accounts': generate_accounts_csv(customer_id, name, num_accounts, arr_values),
        'kpi_measurements': generate_kpi_csv(customer_id, num_accounts, HISTORICAL_MONTHS),
        'enhanced_qualitative_signals': generate_enhanced_qualitative_signals_csv(customer_id, num_accounts, HISTORICAL_MONTHS),
        'products': generate_products_csv(customer_id, num_accounts),
        'contacts': generate_contacts_csv(customer_id, num_accounts, name),
    }

    upload_ok = 0
    for file_type, csv_content in csvs.items():
        resp = cust_client.upload_csv(
            customer_id=customer_id,
            file_type=file_type,
            csv_content=csv_content,
            filename=f'{file_type}.csv'
        )
        if resp and resp.get('status') == 'success':
            upload_ok += 1
            logger.info(f"    {file_type}: uploaded")
        else:
            logger.warning(f"    {file_type}: FAILED ({resp})")
            result['errors'].append(f"Upload {file_type} failed")

    logger.info(f"    Uploaded {upload_ok}/{len(csvs)} base CSVs")

    # ── Step 4: Generate & upload context graph CSVs (one story arc per customer) ──
    if arc_id not in STORY_ARCS:
        logger.warning(f"  arc_id {arc_id!r} not in STORY_ARCS; using anyway")
    logger.info(f"  Step 4: Generating context graph CSVs (story arc={arc_id})...")

    try:
        from scripts.generate_context_graph_data import ContextGraphGenerator

        cg_seed = hash(name) % 10000
        if real_account_ids:
            account_arc_map = {aid: arc_id for aid in real_account_ids}
            gen = ContextGraphGenerator(
                customer_id=customer_id,
                arc_id=arc_id,
                account_arc_map=account_arc_map,
                seed=cg_seed,
            )
        else:
            gen = ContextGraphGenerator(
                customer_id=customer_id,
                arc_id=arc_id,
                num_accounts=num_accounts,
                seed=cg_seed,
            )

        # 8 context graph CSVs (decision_evidence consolidated into decisions)
        cg_csvs = {
            'stakeholders': gen.generate_stakeholders_csv(),
            'engagement_events': gen.generate_engagement_events_csv(),
            'account_business_profiles': gen.generate_account_business_profiles_csv(),
            'decisions': gen.generate_decisions_csv(),
            'outcomes': gen.generate_outcomes_csv(),
            'signal_edges': gen.generate_signal_edges_csv(),
            'industry_benchmarks': gen.generate_industry_benchmarks_csv(),
            'enhanced_signals': gen.generate_enhanced_signals_csv(),
        }

        cg_ok = 0
        for file_type, csv_content in cg_csvs.items():
            resp = cust_client.upload_csv(
                customer_id=customer_id,
                file_type=file_type,
                csv_content=csv_content,
                filename=f'{file_type}.csv'
            )
            if resp and resp.get('status') == 'success':
                cg_ok += 1
                logger.info(f"    {file_type}: uploaded")
            else:
                logger.warning(f"    {file_type}: FAILED ({resp})")

        logger.info(f"    Uploaded {cg_ok}/8 context graph CSVs")
        result['context_graph_files'] = cg_ok

    except ImportError as e:
        logger.warning(f"    Context graph generator not available: {e}")
        result['errors'].append("Context graph generator not available")
    except Exception as e:
        logger.warning(f"    Context graph generation failed: {e}")
        result['errors'].append(f"Context graph error: {e}")

    # ── Step 5: Enable context graph feature toggle ──
    logger.info(f"  Step 5: Enabling context_graph feature toggle...")
    toggle_resp = cust_client.post('/api/features/context-graph', {
        'customer_id': customer_id,
        'enabled': True
    })
    if toggle_resp:
        logger.info(f"    OK: Context graph enabled")
        # Enable all sub-toggles
        for sub in ['story_arcs', 'signal_edges', 'stakeholder_tracking',
                     'decision_lifecycle', 'outcome_economics', 'industry_benchmarks']:
            cust_client.put('/api/features/context-graph/sub-toggle', {
                'customer_id': customer_id,
                'name': sub,
                'enabled': True
            })
        logger.info(f"    OK: All sub-toggles enabled")
    else:
        logger.warning(f"    Feature toggle not available (non-critical)")

    # ── Step 6: Process data (load CSVs → DB, run pipeline) ──
    logger.info(f"  Step 6: Processing data (CSV → DB → scores)...")

    process_resp = cust_client.process_data(
        customer_id=customer_id,
        skip_wizard_b=True,
        skip_wizard_c=True,
        strict_kpi_ranges=False
    )

    if process_resp and process_resp.get('status') in ('success', 'warning'):
        steps = process_resp.get('steps_completed', [])
        cg_result = process_resp.get('context_graph', {})
        logger.info(f"    OK: Data processed — steps: {len(steps)}")
        if cg_result:
            logger.info(f"    Context graph: {cg_result.get('nodes_inserted', 0)} nodes, "
                        f"{cg_result.get('edges_inserted', 0)} edges")
        result['process_data'] = 'success'
        result['context_graph_result'] = cg_result
    else:
        logger.warning(f"    Process-data issue: {str(process_resp)[:150]}")
        result['errors'].append(f"process-data: {str(process_resp)[:100]}")

    # ── Step 7: Calculate scores for latest month ──
    logger.info(f"  Step 7: Calculating scores...")

    scores_resp = cust_client.post('/api/dc2s/scores/calculate', {
        'customer_id': customer_id,
        'measurement_month': '2026-02-01'  # Latest historical month
    })

    if scores_resp:
        logger.info(f"    OK: Scores calculated")
        result['scores'] = 'calculated'
    else:
        logger.warning(f"    Score calculation issue")
        result['errors'].append("Score calculation failed")

    # ── Step 8: Update account ARR in database ──
    logger.info(f"  Step 8: Updating account ARR values in database...")

    # Use the accounts API or direct DB update
    accounts = cust_client.get_accounts()
    if accounts:
        logger.info(f"    Found {len(accounts)} accounts in dashboard")
        result['accounts_visible'] = len(accounts)

    # ── Step 9: Verify ROI/financial endpoints ──
    logger.info(f"  Step 9: Verifying ROI endpoints...")

    roi_resp = cust_client.get('/api/roi/power-of-1/historical',
                                params={'customer_id': customer_id})
    if roi_resp:
        logger.info(f"    OK: ROI historical endpoint available")
        result['roi_available'] = True
    else:
        logger.info(f"    ROI endpoint not available yet (will populate with incremental)")

    # Project forward ROI
    proj_resp = cust_client.post('/api/roi/power-of-1/project', {
        'customer_id': customer_id,
        'improvement_pct': 4.0
    })
    if proj_resp:
        logger.info(f"    OK: ROI projection at 4%: {str(proj_resp)[:100]}")
        result['roi_projection'] = proj_resp

    result['status'] = 'success' if not result['errors'] else 'partial'
    return result


def run_incremental_simulation(client: CSPulseClient, customer_id: int,
                                customer_name: str, num_accounts: int,
                                months: int = 6, seconds_per_day: int = 2):
    """Run incremental simulation: generate daily KPI updates for N months.

    Each day takes `seconds_per_day` seconds of real time.
    Total: months * 30 days * seconds_per_day seconds.
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Incremental Simulation: {customer_name}")
    logger.info(f"  Months: {months}, Speed: {seconds_per_day}s/day")
    total_days = months * 30
    total_time = total_days * seconds_per_day
    logger.info(f"  Total: {total_days} days = {total_time}s ({total_time/60:.1f} min)")
    logger.info(f"{'='*70}")

    account_base = customer_id * 1000 + 1
    base_date = datetime(2026, 3, 1)  # Start incremental from Mar 2026

    profiles = ['healthy', 'healthy', 'healthy', 'improving', 'improving',
                'stable', 'declining', 'recovering', 'seasonal', 'critical']

    days_processed = 0
    months_uploaded = set()

    for day in range(total_days):
        current_date = base_date + timedelta(days=day)
        current_month = current_date.strftime('%Y-%m-01')

        # Only upload KPI data once per month (on 1st of month or first day we see)
        if current_month not in months_uploaded:
            month_offset = HISTORICAL_MONTHS + (day // 30)

            # Generate KPI data for this month
            kpi_rows = []
            for i in range(num_accounts):
                account_id = account_base + i
                profile = profiles[i % len(profiles)]

                for kpi in DC2S_KPIS:
                    target = _get_target(kpi['code'])
                    value = _generate_value(kpi['code'], target, month_offset, profile)
                    status = _classify_status(value, target, kpi['code'])

                    kpi_rows.append({
                        'account_id': account_id,
                        'kpi_code': kpi['code'],
                        'measured_at': current_month,
                        'value': round(value, 2),
                        'target': round(target, 2),
                        'pillar': kpi['pillar'],
                        'weight': kpi['weight'],
                        'status': status
                    })

            # Upload via bulk endpoint
            upload_resp = client.post('/api/dc2s/kpis/bulk-upload', {
                'kpi_data': kpi_rows,
                'measurement_month': current_month
            })

            if upload_resp and upload_resp.get('status') != 'error':
                logger.info(f"    Month {current_month}: uploaded {len(kpi_rows)} KPI measurements")
            else:
                logger.warning(f"    Month {current_month}: upload issue: {upload_resp}")

            # Recalculate scores
            score_resp = client.post('/api/dc2s/scores/calculate', {
                'customer_id': customer_id,
                'measurement_month': current_month
            })
            if score_resp:
                logger.info(f"    Scores recalculated for {current_month}")

            months_uploaded.add(current_month)

        days_processed += 1

        # Progress update every 30 days
        if day > 0 and day % 30 == 0:
            pct = (day / total_days) * 100
            logger.info(f"  Progress: Day {day}/{total_days} ({pct:.0f}%) — "
                        f"{len(months_uploaded)} months uploaded")

        # Wait for simulated day
        time.sleep(seconds_per_day)

    logger.info(f"  Incremental simulation complete: {days_processed} days, "
                f"{len(months_uploaded)} months")
    return {'days': days_processed, 'months': len(months_uploaded)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Setup Sacme & Tacme customers')
    parser.add_argument('--base-url', default=BASE_URL, help='Backend URL')
    parser.add_argument('--skip-incremental', action='store_true', help='Skip incremental simulation')
    parser.add_argument('--incremental-only', action='store_true', help='Only run incremental (customers must exist)')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("CS Pulse DataCenter — Sacme & Tacme Setup")
    logger.info("=" * 70)

    # Create base client (no auth needed for registration)
    base_client = CSPulseClient(
        base_url=args.base_url,
        timeout=300
    )
    base_client._authenticated = True

    if not base_client.health_check():
        logger.error("Backend is not healthy. Start the server first.")
        sys.exit(1)

    results = {}

    if not args.incremental_only:
        # ── Phase 1: Create both customers ──
        for config in CUSTOMERS:
            result = setup_customer(base_client, config)
            results[config['name']] = result

            if result.get('status') == 'success':
                logger.info(f"\n  ✅ {config['name']}: Setup complete!")
            else:
                logger.info(f"\n  ⚠️  {config['name']}: Partial ({len(result.get('errors', []))} warnings)")

    if not args.skip_incremental:
        # ── Phase 2: Run incremental simulation ──
        logger.info(f"\n{'='*70}")
        logger.info(f"Phase 2: Incremental Simulation (6 months, {SECONDS_PER_DAY}s/day)")
        logger.info(f"{'='*70}")

        for config in CUSTOMERS:
            name = config['name']

            # Login as customer
            cust_client = CSPulseClient(
                base_url=args.base_url,
                email=config['email'],
                password=config['password'],
                timeout=300
            )
            login_ok = cust_client.login()
            if not login_ok:
                logger.warning(f"  {name}: Login failed, skipping incremental")
                cust_client._authenticated = True

            customer_id = results.get(name, {}).get('customer_id')
            if not customer_id:
                # Try to find by listing accounts
                logger.warning(f"  {name}: No customer_id cached, skipping")
                continue

            inc_result = run_incremental_simulation(
                client=cust_client,
                customer_id=customer_id,
                customer_name=name,
                num_accounts=config['num_accounts'],
                months=INCREMENTAL_MONTHS,
                seconds_per_day=SECONDS_PER_DAY,
            )
            results[name]['incremental'] = inc_result

    # ── Summary ──
    logger.info(f"\n{'='*70}")
    logger.info(f"SETUP COMPLETE")
    logger.info(f"{'='*70}")

    for name, result in results.items():
        status = result.get('status', 'unknown')
        customer_id = result.get('customer_id', '?')
        icon = "✅" if status == 'success' else "⚠️"
        logger.info(f"  {icon} {name}: customer_id={customer_id}")

    logger.info(f"\n  Login Credentials:")
    logger.info(f"  ┌──────────────────────────────────────────────┐")
    for config in CUSTOMERS:
        name = config['name']
        cid = results.get(name, {}).get('customer_id', '?')
        logger.info(f"  │ {name:8s}: {config['email']:25s} / {config['password']} │")
    logger.info(f"  └──────────────────────────────────────────────┘")

    return 0


if __name__ == '__main__':
    sys.exit(main())
