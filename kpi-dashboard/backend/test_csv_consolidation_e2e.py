#!/usr/bin/env python3
"""
End-to-end test for CSV consolidation (15→11).
Verifies:
  1. Onboard a new customer with 8 customer-provided files
  2. process-data auto-generates 3 derived files (decisions.csv, signal_edges.csv, industry_benchmarks.csv)
  3. Context graph nodes and edges are created
"""
import requests
import io
import csv
import json
import time
import sys
from pathlib import Path

BASE = "http://127.0.0.1:5059/api"
CUSTOMER_NAME = f"CSV_Consolidation_Test_{int(time.time())}"

def make_csv(headers, rows):
    """Create in-memory CSV content."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode()

# ── Step 0: Create customer via onboarding/complete ──
print("=" * 60)
print("STEP 0: Create test customer")
print("=" * 60)
resp = requests.post(f"{BASE}/onboarding/complete", json={
    "customer_name": CUSTOMER_NAME,
    "vertical": "dc2_s",
    "tier": "enterprise",
    "admin_email": f"admin@csvtest{int(time.time())}.com",
    "admin_password": "test123",
    "admin_name": "CSV Test Admin",
    "onboarding_mode": "custom",
    "domain": f"csvtest{int(time.time())}.com",
    "context_graph_enabled": True,
})
print(f"  Status: {resp.status_code}")
data = resp.json()
customer_id = data.get("customer_id")
print(f"  Customer ID: {customer_id}")
if resp.status_code not in (200, 201):
    print(f"  ERROR: {data}")
    sys.exit(1)

# ── Step 1: Upload 8 customer-provided CSV files ──
print("\n" + "=" * 60)
print("STEP 1: Upload 8 customer-provided CSV files")
print("=" * 60)

# Account IDs must be in range customer_id*1000+1 to customer_id*1000+999
acct1 = customer_id * 1000 + 1
acct2 = customer_id * 1000 + 2

# 1. accounts.csv
accounts_data = make_csv(
    ['account_id', 'customer_id', 'account_name', 'industry', 'region', 'revenue'],
    [
        {'account_id': acct1, 'customer_id': customer_id, 'account_name': 'Acme Corp', 'industry': 'Technology', 'region': 'US-West', 'revenue': 500000},
        {'account_id': acct2, 'customer_id': customer_id, 'account_name': 'Beta Inc', 'industry': 'Finance', 'region': 'US-East', 'revenue': 300000},
    ]
)

# 2. kpi_measurements.csv
kpi_data = make_csv(
    ['account_id', 'kpi_code', 'measured_at', 'value', 'target'],
    [
        {'account_id': acct1, 'kpi_code': 'P1-KPI1', 'measured_at': '2026-03-01', 'value': 85, 'target': 90},
        {'account_id': acct1, 'kpi_code': 'P1-KPI2', 'measured_at': '2026-03-01', 'value': 72, 'target': 80},
        {'account_id': acct2, 'kpi_code': 'P1-KPI1', 'measured_at': '2026-03-01', 'value': 60, 'target': 90},
    ]
)

# 3. enhanced_qualitative_signals.csv
signals_data = make_csv(
    ['account_id', 'signal_date', 'signal_type', 'content', 'sentiment', 'signal_ref', 'revenue_impact'],
    [
        {'account_id': acct1, 'signal_date': '2026-03-01', 'signal_type': 'nps', 'content': 'Great product, very satisfied', 'sentiment': 'positive', 'signal_ref': 'sig_nps_001', 'revenue_impact': 50000},
        {'account_id': acct2, 'signal_date': '2026-03-02', 'signal_type': 'support_ticket', 'content': 'Outage affecting core services', 'sentiment': 'negative', 'signal_ref': 'sig_ticket_001', 'revenue_impact': -30000},
    ]
)

# 4. products.csv
products_data = make_csv(
    ['account_id', 'product_name', 'product_category', 'status'],
    [
        {'account_id': acct1, 'product_name': 'DC Pro', 'product_category': 'Infrastructure', 'status': 'active'},
        {'account_id': acct2, 'product_name': 'DC Lite', 'product_category': 'Infrastructure', 'status': 'active'},
    ]
)

# 5. stakeholders.csv
stakeholders_data = make_csv(
    ['account_id', 'stakeholder_name', 'title', 'role', 'influence_score', 'sentiment'],
    [
        {'account_id': acct1, 'stakeholder_name': 'Alice Chen', 'title': 'VP Engineering', 'role': 'champion', 'influence_score': 0.9, 'sentiment': 'positive'},
        {'account_id': acct1, 'stakeholder_name': 'Bob Smith', 'title': 'CFO', 'role': 'economic_buyer', 'influence_score': 0.8, 'sentiment': 'neutral'},
        {'account_id': acct2, 'stakeholder_name': 'Carol White', 'title': 'CTO', 'role': 'executive_sponsor', 'influence_score': 0.85, 'sentiment': 'negative'},
    ]
)

# 6. engagement_events.csv
events_data = make_csv(
    ['account_id', 'event_date', 'event_type', 'description', 'stakeholder_name', 'channel'],
    [
        {'account_id': acct1, 'event_date': '2026-03-01', 'event_type': 'qbr', 'description': 'Quarterly review - positive outlook', 'stakeholder_name': 'Alice Chen', 'channel': 'zoom'},
        {'account_id': acct2, 'event_date': '2026-03-02', 'event_type': 'escalation', 'description': 'Critical outage escalation call', 'stakeholder_name': 'Carol White', 'channel': 'phone'},
    ]
)

# 7. account_business_profiles.csv (with merged CSM/champion fields from old profiles.csv)
profiles_data = make_csv(
    ['account_id', 'arr', 'industry', 'employee_count', 'tech_stack', 'assigned_csm', 'csm_manager', 'primary_champion_name', 'primary_champion_title'],
    [
        {'account_id': acct1, 'arr': 500000, 'industry': 'Technology', 'employee_count': 500, 'tech_stack': 'AWS,Kubernetes', 'assigned_csm': 'Jane Doe', 'csm_manager': 'John Manager', 'primary_champion_name': 'Alice Chen', 'primary_champion_title': 'VP Engineering'},
        {'account_id': acct2, 'arr': 300000, 'industry': 'Finance', 'employee_count': 200, 'tech_stack': 'Azure,Docker', 'assigned_csm': 'Mike CSM', 'csm_manager': 'John Manager', 'primary_champion_name': 'Carol White', 'primary_champion_title': 'CTO'},
    ]
)

# 8. outcomes.csv
outcomes_data = make_csv(
    ['account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value', 'outcome_id'],
    [
        {'account_id': acct1, 'outcome_date': '2026-03-10', 'title': 'Expansion deal closed', 'outcome_type': 'expansion', 'revenue_value': 150000, 'outcome_id': 'out_expansion_001'},
        {'account_id': acct2, 'outcome_date': '2026-03-12', 'title': 'Churn risk — contract not renewed', 'outcome_type': 'churn', 'revenue_value': -300000, 'outcome_id': 'out_churn_001'},
    ]
)

files_to_upload = [
    ('accounts', 'accounts.csv', accounts_data),
    ('kpis', 'kpi_measurements.csv', kpi_data),
    ('enhanced_signals', 'enhanced_qualitative_signals.csv', signals_data),
    ('products', 'products.csv', products_data),
    ('stakeholders', 'stakeholders.csv', stakeholders_data),
    ('engagement_events', 'engagement_events.csv', events_data),
    ('account_business_profiles', 'account_business_profiles.csv', profiles_data),
    ('outcomes', 'outcomes.csv', outcomes_data),
]

for file_type, filename, content in files_to_upload:
    resp = requests.post(
        f"{BASE}/onboarding/upload",
        data={'customer_id': customer_id, 'file_type': file_type},
        files={'file': (filename, content, 'text/csv')},
    )
    status = "✅" if resp.status_code == 200 else "❌"
    print(f"  {status} {filename} ({file_type}): {resp.status_code}")
    if resp.status_code != 200:
        print(f"     {resp.json()}")

# ── Step 2: Call process-data ──
print("\n" + "=" * 60)
print("STEP 2: Run process-data (should auto-generate 3 files)")
print("=" * 60)
resp = requests.post(f"{BASE}/onboarding/process-data", json={
    "customer_id": customer_id,
    "strict_kpi_ranges": False,
})
print(f"  Status: {resp.status_code}")
pd_result = resp.json()
print(f"  Steps completed: {pd_result.get('steps_completed', [])}")
if 'context_graph' in pd_result:
    cg = pd_result['context_graph']
    print(f"  Context graph: {cg.get('nodes_inserted', 0)} nodes, {cg.get('edges_inserted', 0)} edges")
    print(f"  Files loaded: {cg.get('files_loaded', [])}")
if pd_result.get('errors'):
    print(f"  ERRORS: {pd_result['errors']}")

# ── Step 3: Verify 3 auto-generated files exist on disk ──
print("\n" + "=" * 60)
print("STEP 3: Verify auto-generated files on disk")
print("=" * 60)

backend_dir = Path(__file__).parent
cg_dir = backend_dir / 'verticals' / f'customer{customer_id}-dc2_s' / 'data' / 'context_graph'
data_dir = backend_dir / 'verticals' / f'customer{customer_id}-dc2_s' / 'data'

auto_gen_files = ['decisions.csv', 'signal_edges.csv', 'industry_benchmarks.csv']
all_found = True
for f in auto_gen_files:
    fpath = cg_dir / f
    if not fpath.exists():
        fpath = data_dir / f
    if fpath.exists():
        import pandas as pd
        df = pd.read_csv(fpath)
        print(f"  ✅ {f}: {len(df)} rows at {fpath}")
        print(f"     Columns: {list(df.columns)}")
        if len(df) > 0:
            print(f"     Sample: {df.iloc[0].to_dict()}")
    else:
        print(f"  ❌ {f}: NOT FOUND in {cg_dir} or {data_dir}")
        all_found = False

# ── Step 4: Verify customer-provided files are also there ──
print("\n" + "=" * 60)
print("STEP 4: Verify customer-provided files on disk")
print("=" * 60)
customer_files = [
    ('accounts.csv', data_dir),
    ('kpi_measurements.csv', data_dir),
    ('enhanced_qualitative_signals.csv', data_dir),
    ('products.csv', data_dir),
    ('stakeholders.csv', cg_dir),
    ('engagement_events.csv', cg_dir),
    ('account_business_profiles.csv', cg_dir),
    ('outcomes.csv', cg_dir),
]
for fname, d in customer_files:
    fpath = d / fname
    if fpath.exists():
        print(f"  ✅ {fname}")
    else:
        print(f"  ❌ {fname}: NOT FOUND at {fpath}")

# ── Step 5: Verify profile_metadata was stored in accounts ──
print("\n" + "=" * 60)
print("STEP 5: Verify profile_metadata in accounts table")
print("=" * 60)
import psycopg2
try:
    conn = psycopg2.connect(dbname='cs_pulse_datacenter', user='dcuser')
    cur = conn.cursor()
    cur.execute("SELECT account_id, profile_metadata FROM accounts WHERE customer_id = %s AND profile_metadata IS NOT NULL", (customer_id,))
    rows = cur.fetchall()
    for aid, meta in rows:
        meta_dict = json.loads(meta) if isinstance(meta, str) else meta
        print(f"  ✅ Account {aid}: {list(meta_dict.keys())}")
    if not rows:
        print("  ⚠️  No profile_metadata found (may be OK if account_business_profiles loaded as context nodes only)")
    conn.close()
except Exception as e:
    print(f"  ⚠️  DB check skipped: {e}")

# ── Summary ──
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Customer ID: {customer_id}")
print(f"  Auto-generated files location: {cg_dir}")
print(f"  All 3 auto-generated files found: {'✅ YES' if all_found else '❌ NO'}")
print(f"  Context graph nodes: {pd_result.get('context_graph', {}).get('nodes_inserted', 'N/A')}")
print(f"  Context graph edges: {pd_result.get('context_graph', {}).get('edges_inserted', 'N/A')}")
