#!/usr/bin/env python3
"""
Create 3 "Gold" template customers with enterprise entitlements, all toggles on,
10 accounts each, full context graph, health trends, and ROI data.

Gold customers:
  1. Gold_DC_Alpha   - dc2_s vertical, 10 accounts
  2. Gold_DC_Beta    - dc2_s vertical, 10 accounts
  3. Gold_SaaS_Gamma - saas_premium vertical, 10 accounts

Usage:
    python scripts/create_gold_customers.py
    (Requires backend server running on port 5059)
"""
import requests
import io
import csv
import json
import time
import sys
import random
import math
from pathlib import Path
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:5059/api"

# ─────────────────────────────────────────────────────────
# KPI definitions for data generation
# ─────────────────────────────────────────────────────────

# DC2_S: 38 KPIs across 5 pillars (P1: 8, P2: 8, P3: 7, P4: 8, P5: 7)
DC2S_KPI_TARGETS = {
    'P1-KPI1': ('days', 14, 'lower'), 'P1-KPI2': ('%', 90, 'higher'), 'P1-KPI3': ('%', 95, 'higher'),
    'P1-KPI4': ('%', 85, 'higher'), 'P1-KPI5': ('%', 80, 'higher'), 'P1-KPI6': ('ratio', 0.9, 'higher'),
    'P1-KPI7': ('days', 7, 'lower'), 'P1-KPI8': ('%', 90, 'higher'),
    'P2-KPI1': ('%', 99.9, 'higher'), 'P2-KPI2': ('hours', 4, 'lower'), 'P2-KPI3': ('ratio', 0.05, 'lower'),
    'P2-KPI4': ('%', 95, 'higher'), 'P2-KPI5': ('%', 85, 'higher'), 'P2-KPI6': ('%', 99, 'higher'),
    'P2-KPI7': ('hours', 2, 'lower'), 'P2-KPI8': ('%', 90, 'higher'),
    'P3-KPI1': ('%', 80, 'higher'), 'P3-KPI2': ('%', 85, 'higher'), 'P3-KPI3': ('score', 75, 'higher'),
    'P3-KPI4': ('%', 90, 'higher'), 'P3-KPI5': ('score', 70, 'higher'), 'P3-KPI6': ('%', 85, 'higher'),
    'P3-KPI7': ('%', 80, 'higher'),
    'P4-KPI1': ('%', 70, 'higher'), 'P4-KPI2': ('score', 80, 'higher'), 'P4-KPI3': ('%', 75, 'higher'),
    'P4-KPI4': ('%', 85, 'higher'), 'P4-KPI5': ('score', 75, 'higher'), 'P4-KPI6': ('%', 80, 'higher'),
    'P4-KPI7': ('%', 70, 'higher'), 'P4-KPI8': ('%', 85, 'higher'),
    'P5-KPI1': ('%', 95, 'higher'), 'P5-KPI2': ('%', 90, 'higher'), 'P5-KPI3': ('%', 25, 'higher'),
    'P5-KPI4': ('%', 85, 'higher'), 'P5-KPI5': ('ratio', 3.0, 'higher'), 'P5-KPI6': ('%', 20, 'higher'),
    'P5-KPI7': ('%', 80, 'higher'),
}

# SaaS Premium: 35 KPIs across 5 pillars (7 each)
SAAS_KPI_TARGETS = {
    'P1-KPI1': ('%', 60, 'higher'), 'P1-KPI2': ('%', 45, 'higher'), 'P1-KPI3': ('days', 21, 'lower'),
    'P1-KPI4': ('freq', 3.5, 'higher'), 'P1-KPI5': ('%', 30, 'higher'), 'P1-KPI6': ('%', 75, 'higher'),
    'P1-KPI7': ('%', 70, 'higher'),
    'P2-KPI1': ('score', 70, 'higher'), 'P2-KPI2': ('%', 85, 'higher'), 'P2-KPI3': ('%', 60, 'higher'),
    'P2-KPI4': ('score', 40, 'higher'), 'P2-KPI5': ('freq', 4, 'higher'), 'P2-KPI6': ('%', 25, 'higher'),
    'P2-KPI7': ('score', 50, 'higher'),
    'P3-KPI1': ('hours', 24, 'lower'), 'P3-KPI2': ('score', 85, 'higher'), 'P3-KPI3': ('score', 40, 'higher'),
    'P3-KPI4': ('%', 8, 'lower'), 'P3-KPI5': ('%', 70, 'higher'), 'P3-KPI6': ('%', 5, 'lower'),
    'P3-KPI7': ('%', 95, 'higher'),
    'P4-KPI1': ('%', 25, 'higher'), 'P4-KPI2': ('score', 60, 'higher'), 'P4-KPI3': ('%', 40, 'higher'),
    'P4-KPI4': ('days', 14, 'lower'), 'P4-KPI5': ('score', 75, 'higher'), 'P4-KPI6': ('%', 200, 'higher'),
    'P4-KPI7': ('score', 65, 'higher'),
    'P5-KPI1': ('%', 110, 'higher'), 'P5-KPI2': ('%', 92, 'higher'), 'P5-KPI3': ('%', 15, 'higher'),
    'P5-KPI4': ('%', 12, 'higher'), 'P5-KPI5': ('%', 85, 'higher'), 'P5-KPI6': ('%', 20, 'lower'),
    'P5-KPI7': ('ratio', 2, 'higher'),
}

# Health archetypes for 10 accounts (mix of healthy, at-risk, critical)
ACCOUNT_ARCHETYPES = [
    ('Production', 'healthy', 1.0),      # Starts healthy, stays healthy
    ('Development', 'healthy', 0.95),
    ('Staging', 'at_risk', 0.85),         # Starts at-risk, improves
    ('Analytics', 'at_risk', 0.80),
    ('Research', 'healthy', 0.90),
    ('Training', 'critical', 0.65),       # Starts critical, recovers
    ('Edge', 'at_risk', 0.75),
    ('Backup', 'healthy', 0.92),
    ('Performance', 'critical', 0.60),    # Critical throughout
    ('Integration', 'at_risk', 0.78),
]

SAAS_ACCOUNT_NAMES = [
    'Enterprise Core', 'Growth Team', 'Product Analytics', 'Marketing Ops',
    'Sales Enablement', 'Customer Success', 'Engineering', 'Data Platform',
    'Security Ops', 'DevOps Central',
]

INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Manufacturing', 'Retail',
              'Energy', 'Media', 'Education', 'Logistics', 'Telecom']

SIGNAL_TYPES = ['nps', 'csat', 'support_ticket', 'feature_request', 'escalation',
                'executive_feedback', 'renewal_signal', 'usage_alert']

SENTIMENTS = ['positive', 'positive', 'neutral', 'negative', 'positive']  # weighted positive

STAKEHOLDER_ROLES = ['champion', 'economic_buyer', 'executive_sponsor', 'technical_lead',
                     'end_user', 'decision_maker']

OUTCOME_TYPES = ['retention', 'expansion', 'churn_averted', 'roi_positive']


def make_csv(headers, rows):
    """Create in-memory CSV content."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode()


def generate_kpi_value(target, direction, archetype_factor, month_idx, total_months=6):
    """Generate a realistic KPI value with improvement trend over time.

    All archetypes start below target and improve, creating positive ROI signal.
    Healthy accounts start closer to target and improve more.
    Critical accounts start further from target but still improve.
    """
    # Starting position: archetype_factor determines how far below target we start
    # Month progression: all accounts improve over time (CS investment pays off)
    start_pct = archetype_factor * 0.6  # healthy=0.60, at_risk=0.48-0.51, critical=0.36-0.39
    end_pct = archetype_factor * 1.05   # healthy=1.05 (exceeds target), at_risk=0.84, critical=0.68

    # Linear interpolation with slight acceleration
    t = month_idx / max(total_months - 1, 1)
    t_curved = t * t * 0.3 + t * 0.7  # slight acceleration toward end
    progression = start_pct + (end_pct - start_pct) * t_curved

    noise = random.uniform(-0.03, 0.03) * target

    if direction == 'lower':
        # For lower-is-better: start high (bad), improve to lower (good)
        inv_start = 2.0 - start_pct   # e.g. 1.40 for healthy
        inv_end = 2.0 - end_pct       # e.g. 0.95 for healthy
        inv_prog = inv_start + (inv_end - inv_start) * t_curved
        value = target * inv_prog + noise
    else:
        value = target * progression + noise

    return round(max(0, value), 2)


def generate_accounts_csv(customer_id, account_names, vertical):
    """Generate accounts.csv."""
    rows = []
    for i, name in enumerate(account_names):
        aid = customer_id * 1000 + i + 1
        rows.append({
            'account_id': aid,
            'customer_id': customer_id,
            'account_name': f'{name}',
            'industry': INDUSTRIES[i % len(INDUSTRIES)],
            'region': ['US-West', 'US-East', 'EU-West', 'APAC', 'US-Central'][i % 5],
            'revenue': round(random.uniform(500000, 5000000), 2),
            'vertical': vertical,
            'account_status': 'active',
        })
    return make_csv(list(rows[0].keys()), rows)


def generate_kpi_csv(customer_id, num_accounts, kpi_targets, months=6):
    """Generate kpi_measurements.csv with 6 months of data."""
    rows = []
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        _, archetype, factor = ACCOUNT_ARCHETYPES[i] if i < len(ACCOUNT_ARCHETYPES) else ('default', 'at_risk', 0.8)
        for m in range(months):
            date = f'2024-{m+1:02d}-01'
            for kpi_code, (unit, target, direction) in kpi_targets.items():
                pillar = kpi_code.split('-')[0]
                value = generate_kpi_value(target, direction, factor, m, months)
                rows.append({
                    'account_id': aid,
                    'kpi_code': kpi_code,
                    'measured_at': date,
                    'value': value,
                    'target': target,
                    'pillar': pillar,
                    'weight': round(1.0 / 8, 4),
                    'status': 'active',
                })
    return make_csv(list(rows[0].keys()), rows)


def generate_signals_csv(customer_id, num_accounts, months=6):
    """Generate enhanced_qualitative_signals.csv."""
    rows = []
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        for m in range(months):
            num_signals = random.randint(2, 5)
            for s in range(num_signals):
                day = random.randint(1, 28)
                rows.append({
                    'account_id': aid,
                    'signal_date': f'2024-{m+1:02d}-{day:02d}',
                    'signal_type': random.choice(SIGNAL_TYPES),
                    'content': f'Signal for account {aid} month {m+1}: {random.choice(["Great progress", "Needs attention", "Positive feedback", "Feature gap identified", "Strong adoption", "Risk of churn", "Executive escalation", "Renewal discussion"])}',
                    'sentiment': random.choice(SENTIMENTS),
                    'signal_ref': f'sig_{aid}_{m}_{s}',
                    'revenue_impact': round(random.uniform(-50000, 100000), 2),
                })
    return make_csv(list(rows[0].keys()), rows)


def generate_products_csv(customer_id, num_accounts, vertical):
    """Generate products.csv."""
    dc_products = ['DC Pro', 'DC Lite', 'DC Enterprise', 'GPU Cluster', 'Edge Node']
    saas_products = ['SaaS Core', 'SaaS Analytics', 'SaaS Enterprise', 'API Gateway', 'Data Pipeline']
    products = saas_products if vertical == 'saas_premium' else dc_products
    rows = []
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        for j in range(random.randint(1, 3)):
            rows.append({
                'account_id': aid,
                'product_name': products[(i + j) % len(products)],
                'product_category': 'Infrastructure' if vertical == 'dc2_s' else 'SaaS',
                'status': 'active',
            })
    return make_csv(list(rows[0].keys()), rows)


def generate_stakeholders_csv(customer_id, num_accounts):
    """Generate stakeholders.csv for context graph."""
    rows = []
    names = ['Alice Chen', 'Bob Smith', 'Carol White', 'David Kim', 'Eva Martinez',
             'Frank Johnson', 'Grace Lee', 'Henry Wilson', 'Iris Zhang', 'Jack Brown']
    titles = ['VP Engineering', 'CFO', 'CTO', 'Director of IT', 'Head of Product',
              'SVP Operations', 'Chief Data Officer', 'Director of CS', 'VP Sales', 'COO']
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        for j in range(random.randint(2, 4)):
            idx = (i * 3 + j) % len(names)
            rows.append({
                'account_id': aid,
                'stakeholder_name': f'{names[idx]}',
                'title': titles[idx],
                'role': STAKEHOLDER_ROLES[j % len(STAKEHOLDER_ROLES)],
                'influence_score': round(random.uniform(0.5, 1.0), 2),
                'sentiment': random.choice(['positive', 'neutral', 'negative']),
            })
    return make_csv(list(rows[0].keys()), rows)


def generate_engagement_events_csv(customer_id, num_accounts, months=6):
    """Generate engagement_events.csv for context graph."""
    rows = []
    event_types = ['qbr', 'escalation', 'training', 'onboarding', 'renewal_discussion',
                   'executive_briefing', 'technical_review', 'success_planning']
    channels = ['zoom', 'phone', 'email', 'in_person', 'slack']
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        for m in range(months):
            num_events = random.randint(2, 6)
            for e in range(num_events):
                day = random.randint(1, 28)
                rows.append({
                    'account_id': aid,
                    'event_date': f'2024-{m+1:02d}-{day:02d}',
                    'event_type': random.choice(event_types),
                    'description': f'Engagement event for account {aid}',
                    'stakeholder_name': random.choice(['Alice Chen', 'Bob Smith', 'Carol White', 'David Kim']),
                    'channel': random.choice(channels),
                })
    return make_csv(list(rows[0].keys()), rows)


def generate_business_profiles_csv(customer_id, num_accounts, vertical):
    """Generate account_business_profiles.csv for context graph."""
    rows = []
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        rows.append({
            'account_id': aid,
            'arr': round(random.uniform(500000, 5000000), 2),
            'industry': INDUSTRIES[i % len(INDUSTRIES)],
            'employee_count': random.randint(100, 5000),
            'tech_stack': random.choice(['AWS,Kubernetes', 'Azure,Docker', 'GCP,Terraform', 'On-Prem,VMware']),
            'assigned_csm': random.choice(['Jane Doe', 'Mike CSM', 'Sarah CSM', 'Tom CSM']),
            'csm_manager': 'John Manager',
            'primary_champion_name': random.choice(['Alice Chen', 'Bob Smith', 'Carol White']),
            'primary_champion_title': random.choice(['VP Engineering', 'CTO', 'Director of IT']),
        })
    return make_csv(list(rows[0].keys()), rows)


def generate_outcomes_csv(customer_id, num_accounts):
    """Generate outcomes.csv for context graph."""
    rows = []
    for i in range(num_accounts):
        aid = customer_id * 1000 + i + 1
        _, archetype, factor = ACCOUNT_ARCHETYPES[i] if i < len(ACCOUNT_ARCHETYPES) else ('default', 'at_risk', 0.8)
        # Generate outcome types based on health archetype
        if factor >= 0.9:
            outcomes = [('retention', 'Full ARR Retained', 1.0), ('expansion', 'Expansion Closed', 0.3),
                        ('churn_averted', 'Churn Risk Averted', 0.15), ('roi_positive', 'Net ROI Positive', 0.8)]
        elif factor >= 0.75:
            outcomes = [('retention', 'Partial Retention', 0.7), ('churn_averted', 'Churn Risk Mitigated', 0.2),
                        ('roi_positive', 'Modest ROI', 0.4)]
        else:
            outcomes = [('churn_averted', 'Emergency Churn Save', 0.1), ('retention', 'At-Risk Retention', 0.5)]

        base_arr = random.uniform(500000, 3000000)
        for otype, title, multiplier in outcomes:
            rows.append({
                'account_id': aid,
                'outcome_date': f'2024-{random.randint(1,6):02d}-{random.randint(1,28):02d}',
                'title': title,
                'outcome_type': otype,
                'revenue_value': round(base_arr * multiplier, 2),
                'outcome_id': f'out_{otype}_{aid}',
            })
    return make_csv(list(rows[0].keys()), rows)


def create_customer(name, vertical, admin_email):
    """Create a customer via onboarding/complete API."""
    print(f"\n{'='*60}")
    print(f"Creating customer: {name} ({vertical})")
    print(f"{'='*60}")
    resp = requests.post(f"{BASE}/onboarding/complete", json={
        "customer_name": name,
        "vertical": vertical,
        "tier": "enterprise",
        "admin_email": admin_email,
        "admin_password": "gold123!",
        "admin_name": f"Admin {name}",
        "onboarding_mode": "custom",
        "domain": admin_email.split('@')[1],
        "context_graph_enabled": True,
        "num_accounts": 0,  # We'll create accounts via CSV
    })
    data = resp.json()
    cid = data.get('customer_id')
    print(f"  Customer ID: {cid}, Status: {resp.status_code}")
    if resp.status_code not in (200, 201):
        print(f"  ERROR: {data}")
        return None
    return cid


def enable_enterprise_toggles(customer_id, admin_email):
    """Enable all enterprise toggles and create admin user via direct DB."""
    import psycopg2
    from werkzeug.security import generate_password_hash
    conn = psycopg2.connect(dbname='cs_pulse_datacenter', user='dcuser')
    cur = conn.cursor()

    # Feature toggles
    toggles = [
        ('subscription_tier', True, json.dumps({"tier": "enterprise"})),
        ('context_graph', True, json.dumps({
            "story_arcs": True, "signal_edges": True, "stakeholder_tracking": True,
            "decision_lifecycle": True, "outcome_economics": True, "industry_benchmarks": True
        })),
        ('revenue_intelligence', True, json.dumps({})),
        ('mcp_integration', True, json.dumps({
            "salesforce": True, "servicenow": True, "surveys": True
        })),
    ]

    for fname, enabled, config in toggles:
        cur.execute("""
            INSERT INTO feature_toggles (customer_id, feature_name, enabled, config)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (customer_id, feature_name) DO UPDATE SET
                enabled = EXCLUDED.enabled, config = EXCLUDED.config, updated_at = NOW()
        """, (customer_id, fname, enabled, config))

    # Create admin user (onboarding API doesn't always create one)
    pw_hash = generate_password_hash('gold123!')
    cur.execute("SELECT user_id FROM users WHERE email = %s", (admin_email,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (email, password_hash, customer_id, user_name, active)
            VALUES (%s, %s, %s, %s, %s)
        """, (admin_email, pw_hash, customer_id, f'Admin {customer_id}', True))

    conn.commit()
    conn.close()
    print(f"  ✅ Enterprise toggles + admin user created")


def upload_csv(customer_id, file_type, filename, content):
    """Upload a single CSV file."""
    resp = requests.post(
        f"{BASE}/onboarding/upload",
        data={'customer_id': customer_id, 'file_type': file_type},
        files={'file': (filename, content, 'text/csv')},
    )
    status = "✅" if resp.status_code == 200 else "❌"
    print(f"    {status} {filename}: {resp.status_code}")
    if resp.status_code != 200:
        print(f"       {resp.json()}")
    return resp.status_code == 200


def process_data(customer_id):
    """Run process-data to load CSVs, compute health, generate context graph."""
    print(f"  Running process-data...")
    resp = requests.post(f"{BASE}/onboarding/process-data", json={
        "customer_id": customer_id,
        "strict_kpi_ranges": False,
    })
    data = resp.json()
    steps = data.get('steps_completed', [])
    print(f"  Steps: {steps}")
    if data.get('errors'):
        # Filter out expected non-critical errors
        real_errors = [e for e in data['errors'] if 'Embedding' not in e and 'Journey generator' not in e and 'Wizard A' not in e]
        if real_errors:
            print(f"  ⚠️  Errors: {real_errors}")
    return data


def verify_customer(customer_id, vertical):
    """Verify context graph, health trends, and ROI for a customer."""
    import psycopg2
    conn = psycopg2.connect(dbname='cs_pulse_datacenter', user='dcuser')
    cur = conn.cursor()

    print(f"\n  --- Verification for Customer {customer_id} ({vertical}) ---")

    # Accounts
    cur.execute('SELECT count(*) FROM accounts WHERE customer_id=%s', (customer_id,))
    print(f"  Accounts: {cur.fetchone()[0]}")

    # KPIs
    acct_low = customer_id * 1000 + 1
    acct_high = customer_id * 1000 + 999
    cur.execute('SELECT count(*), count(DISTINCT measured_at) FROM dc2s_kpis WHERE account_id BETWEEN %s AND %s',
                (acct_low, acct_high))
    row = cur.fetchone()
    print(f"  KPI measurements: {row[0]} rows, {row[1]} months")

    # Pillar scores
    cur.execute('SELECT count(*) FROM pillar_scores WHERE account_id BETWEEN %s AND %s',
                (acct_low, acct_high))
    print(f"  Pillar scores: {cur.fetchone()[0]} rows")

    # Health trends
    cur.execute('SELECT count(*), MIN(overall_health_score), MAX(overall_health_score) FROM health_trends WHERE account_id BETWEEN %s AND %s',
                (acct_low, acct_high))
    row = cur.fetchone()
    if row[1] is not None:
        print(f"  Health trends: {row[0]} rows, score range: {row[1]:.1f} - {row[2]:.1f}")
    else:
        print(f"  Health trends: {row[0]} rows (no data)")

    # Context graph
    cur.execute('SELECT node_type, count(*) FROM context_nodes WHERE customer_id=%s GROUP BY node_type ORDER BY count(*) DESC',
                (customer_id,))
    nodes = cur.fetchall()
    total_nodes = sum(r[1] for r in nodes)
    print(f"  Context graph nodes: {total_nodes}")
    for ntype, cnt in nodes:
        print(f"    {ntype}: {cnt}")

    cur.execute('SELECT edge_type, count(*) FROM context_edges WHERE customer_id=%s GROUP BY edge_type',
                (customer_id,))
    edges = cur.fetchall()
    total_edges = sum(r[1] for r in edges)
    print(f"  Context graph edges: {total_edges}")

    # Auto-generated files
    backend_dir = Path(__file__).parent.parent
    cg_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}' / 'data' / 'context_graph'
    auto_files = ['decisions.csv', 'signal_edges.csv', 'industry_benchmarks.csv']
    for f in auto_files:
        fpath = cg_dir / f
        status = "✅" if fpath.exists() else "❌"
        print(f"  {status} Auto-gen: {f}")

    conn.close()
    return total_nodes, total_edges


def verify_roi(customer_id, admin_email):
    """Login and check ROI endpoint."""
    # Login
    session = requests.Session()
    resp = session.post(f"{BASE}/login", json={"email": admin_email, "password": "gold123!"})
    if resp.status_code != 200:
        print(f"  ⚠️  Login failed for {admin_email}: {resp.status_code}")
        return None

    # Historical ROI
    resp = session.get(f"{BASE}/outcome-roi/historical")
    if resp.status_code != 200:
        print(f"  ⚠️  ROI endpoint returned {resp.status_code}: {resp.text[:200]}")
        return None

    data = resp.json()
    result = data.get('result', {})
    source = data.get('data_source', '?')
    investment = result.get('investment_breakdown', {}).get('total', 0)
    metrics = result.get('metric_outcomes', [])
    total_impact = sum(m.get('dollar_impact', 0) for m in metrics)
    roi_pct = ((total_impact - investment) / investment * 100) if investment else 0

    print(f"  ROI: {roi_pct:.0f}% (source={source}, investment=${investment:,.0f}, impact=${total_impact:,.0f})")
    for m in metrics[:3]:
        print(f"    {m['display_name']}: {m['improvement_pct']:.1f}% → ${m['dollar_impact']:,.0f}")

    return source


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

def main():
    random.seed(42)  # Reproducible data

    customers = [
        ("Gold_DC_Alpha", "dc2_s", "admin@gold-dc-alpha.com", DC2S_KPI_TARGETS),
        ("Gold_DC_Beta", "dc2_s", "admin@gold-dc-beta.com", DC2S_KPI_TARGETS),
        ("Gold_SaaS_Gamma", "saas_premium", "admin@gold-saas-gamma.com", SAAS_KPI_TARGETS),
    ]

    results = []

    for name, vertical, email, kpi_targets in customers:
        # 1. Create customer
        cid = create_customer(name, vertical, email)
        if not cid:
            print(f"  ❌ Failed to create {name}, skipping")
            continue

        # 2. Enable enterprise toggles + admin user
        enable_enterprise_toggles(cid, email)

        # 3. Generate and upload CSVs
        print(f"  Uploading CSVs...")
        account_names = SAAS_ACCOUNT_NAMES if vertical == 'saas_premium' else [a[0] for a in ACCOUNT_ARCHETYPES]

        # Core 4
        upload_csv(cid, 'accounts', 'accounts.csv', generate_accounts_csv(cid, account_names, vertical))
        upload_csv(cid, 'kpis', 'kpi_measurements.csv', generate_kpi_csv(cid, 10, kpi_targets))
        upload_csv(cid, 'enhanced_signals', 'enhanced_qualitative_signals.csv', generate_signals_csv(cid, 10))
        upload_csv(cid, 'products', 'products.csv', generate_products_csv(cid, 10, vertical))

        # Context Graph 4
        upload_csv(cid, 'stakeholders', 'stakeholders.csv', generate_stakeholders_csv(cid, 10))
        upload_csv(cid, 'engagement_events', 'engagement_events.csv', generate_engagement_events_csv(cid, 10))
        upload_csv(cid, 'account_business_profiles', 'account_business_profiles.csv', generate_business_profiles_csv(cid, 10, vertical))
        upload_csv(cid, 'outcomes', 'outcomes.csv', generate_outcomes_csv(cid, 10))

        # 4. Process data (loads KPIs, computes health, generates context graph)
        pd_result = process_data(cid)

        # 5. Verify
        total_nodes, total_edges = verify_customer(cid, vertical)

        # 6. Verify ROI
        roi_source = verify_roi(cid, email)

        results.append({
            'name': name, 'customer_id': cid, 'vertical': vertical,
            'nodes': total_nodes, 'edges': total_edges, 'roi_source': roi_source,
        })

    # ─────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"GOLD CUSTOMER SUMMARY")
    print(f"{'='*60}")
    all_pass = True
    for r in results:
        cg_ok = r['nodes'] > 0 and r['edges'] > 0
        roi_ok = r['roi_source'] == 'health_trends'
        status = "✅" if (cg_ok and roi_ok) else "⚠️"
        if not (cg_ok and roi_ok):
            all_pass = False
        print(f"  {status} {r['name']} (ID={r['customer_id']}, {r['vertical']})")
        print(f"     Context Graph: {r['nodes']} nodes, {r['edges']} edges {'✅' if cg_ok else '❌'}")
        print(f"     ROI source: {r['roi_source']} {'✅' if roi_ok else '❌'}")

    print(f"\n  Overall: {'✅ ALL PASS' if all_pass else '⚠️  ISSUES FOUND'}")
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
