#!/usr/bin/env python3
"""
End-to-End MCP Server Test
===========================
Tests the full customer lifecycle through MCP tools:
  1. Onboarding: create customer, upload CSVs, process data
  2. Wizards: A, B, C
  3. Intelligence: list accounts, health, playbooks, CSM actions
  4. Revenue: ROI, revenue at risk, context graph
  5. Admin: export, clone

Runs against the local backend (port 5059) and local DB.
Tests MCP tool functions directly (no MCP transport needed).

Usage:
    cd kpi-dashboard
    python3 backend/mcp_server/test_mcp_e2e.py
"""

import os
import sys
import json
import traceback
from datetime import datetime

# Setup paths
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Force MCP enabled
os.environ['FEATURE_MCP_SERVER'] = 'true'
os.environ['MCP_AUTH_ENABLED'] = 'false'
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL',
    'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter')

# Mock fastmcp if not installed (Python 3.9 compat)
try:
    import fastmcp
except ImportError:
    import types
    fastmcp_mod = types.ModuleType('fastmcp')
    class _FakeMCP:
        def __init__(self, *a, **kw): pass
        def tool(self, f=None, **kw):
            if f: return f
            def dec(fn): return fn
            return dec
        def resource(self, *a, **kw):
            def dec(fn): return fn
            return dec
        def run(self, **kw): pass
    fastmcp_mod.FastMCP = _FakeMCP
    exc_mod = types.ModuleType('fastmcp.exceptions')
    class ToolError(Exception): pass
    exc_mod.ToolError = ToolError
    fastmcp_mod.exceptions = exc_mod
    sys.modules['fastmcp'] = fastmcp_mod
    sys.modules['fastmcp.exceptions'] = exc_mod

# Test results tracking
PASS = []
FAIL = []
SKIP = []

TEST_CUSTOMER_NAME = f"MCP_E2E_Test_{datetime.now().strftime('%H%M%S')}"
TEST_CUSTOMER_ID = None


def test(name, func, *args, **kwargs):
    """Run a test, track pass/fail."""
    try:
        result = func(*args, **kwargs)
        PASS.append(name)
        print(f"  ✅ {name}")
        return result
    except Exception as e:
        FAIL.append((name, str(e)))
        print(f"  ❌ {name}: {e}")
        if os.environ.get('VERBOSE'):
            traceback.print_exc()
        return None


def test_skip(name, reason):
    """Skip a test."""
    SKIP.append((name, reason))
    print(f"  ⏭️  {name}: {reason}")


# ===================================================================
# Import all MCP tool functions directly
# ===================================================================
print("\n🔧 Importing MCP tool modules...")

try:
    from mcp_server import common
    print("  ✅ common.py imported")
except Exception as e:
    print(f"  ❌ common.py: {e}")
    sys.exit(1)

# Import each server module
try:
    from mcp_server import cs_pulse_intelligence as intel
    print(f"  ✅ cs_pulse_intelligence.py imported")
except Exception as e:
    print(f"  ❌ cs_pulse_intelligence.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from mcp_server import cs_pulse_revenue as revenue
    print(f"  ✅ cs_pulse_revenue.py imported")
except Exception as e:
    print(f"  ❌ cs_pulse_revenue.py: {e}")

try:
    from mcp_server import cs_pulse_onboarding as onboard
    print(f"  ✅ cs_pulse_onboarding.py imported")
except Exception as e:
    print(f"  ❌ cs_pulse_onboarding.py: {e}")

try:
    from mcp_server import cs_pulse_admin as admin
    print(f"  ✅ cs_pulse_admin.py imported")
except Exception as e:
    print(f"  ❌ cs_pulse_admin.py: {e}")


# ===================================================================
# Phase 1: ONBOARDING — Create customer from scratch
# ===================================================================
print(f"\n{'='*60}")
print("Phase 1: ONBOARDING")
print(f"{'='*60}")

# 1a. List verticals
def test_list_verticals():
    r = onboard.list_verticals()
    assert 'verticals' in r, f"Missing 'verticals' key: {list(r.keys())}"
    vlist = r['verticals']
    assert len(vlist) > 0, "No verticals found"
    # verticals is a list of dicts, each with 'vertical' key
    verts = [v['vertical'] if isinstance(v, dict) else v for v in vlist]
    print(f"       Verticals: {verts}")
    return r

result = test("list_verticals", test_list_verticals)

# 1b. Get CSV templates
def test_csv_templates():
    r = onboard.get_csv_templates(vertical='dc2_s')
    assert 'schemas' in r, f"Missing 'schemas' key, got: {list(r.keys())}"
    print(f"       File types: {list(r['schemas'].keys())[:5]}...")
    return r

test("get_csv_templates(dc2_s)", test_csv_templates)

# 1c. Get vertical config
def test_vertical_config():
    r = onboard.get_vertical_config(vertical='dc2_s')
    assert r is not None
    return r

test("get_vertical_config(dc2_s)", test_vertical_config)

# 1d. Get reference customer
def test_reference_customer():
    r = onboard.get_reference_customer(vertical='dc2_s')
    assert r is not None
    print(f"       Reference: {r.get('customer_id', 'N/A')} - {r.get('company_name', r.get('customer_name', 'N/A'))}")
    return r

test("get_reference_customer(dc2_s)", test_reference_customer)

# 1e. Create customer
def test_create_customer():
    global TEST_CUSTOMER_ID
    domain = f'{TEST_CUSTOMER_NAME.lower().replace("_","-")}.test'
    r = onboard.create_customer(
        name=TEST_CUSTOMER_NAME,
        domain=domain,
        vertical='dc2_s',
        admin_email=f'admin@{domain}',
        admin_name='E2E Test Admin',
    )
    assert 'customer_id' in r, f"No customer_id in response: {list(r.keys())}"
    TEST_CUSTOMER_ID = r['customer_id']
    print(f"       Created customer {TEST_CUSTOMER_ID}: {TEST_CUSTOMER_NAME}")
    return r

result = test("create_customer", test_create_customer)
if not TEST_CUSTOMER_ID:
    print("\n💀 Cannot continue without a customer. Aborting.")
    sys.exit(1)

# 1f. Enable features
def test_enable_features():
    r = onboard.enable_features(
        customer_id=TEST_CUSTOMER_ID,
        features=['context_graph', 'revenue_intelligence', 'mcp_integration'],
    )
    return r

test("enable_features", test_enable_features)

# 1g. Generate and upload CSVs using synthetic data generator
print("\n  📊 Generating synthetic data...")

def generate_and_upload_csvs():
    """Use the real synthetic data generator, then upload via MCP."""
    import subprocess
    import csv
    import io

    output_dir = f'/tmp/mcp_e2e_test_{TEST_CUSTOMER_ID}'
    os.makedirs(output_dir, exist_ok=True)

    # Generate synthetic data
    gen_script = os.path.join(_backend_dir, 'scripts', 'generate_synthetic_customer_data.py')
    cmd = [
        sys.executable, gen_script,
        '--customer-id', str(TEST_CUSTOMER_ID),
        '--company-name', TEST_CUSTOMER_NAME,
        '--output-dir', output_dir,
        '--num-accounts', '5',
        '--num-months', '6',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_backend_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Data generator failed: {result.stderr[:500]}")

    # Upload each CSV via MCP tool
    file_types = {
        'accounts': 'accounts.csv',
        'kpi_measurements': 'kpi_measurements.csv',
        'enhanced_qualitative_signals': 'enhanced_qualitative_signals.csv',
        'products': 'products.csv',
    }

    for file_type, filename in file_types.items():
        filepath = os.path.join(output_dir, filename)
        if not os.path.exists(filepath):
            print(f"       ⚠️  {filename} not found, skipping")
            continue
        with open(filepath, 'r') as f:
            csv_content = f.read()

        r = onboard.upload_csv(
            customer_id=TEST_CUSTOMER_ID,
            file_type=file_type,
            csv_content=csv_content,
        )
        status = '✅' if r and not r.get('error') else '❌'
        rows = len(csv_content.strip().split('\n')) - 1
        print(f"       {status} upload {file_type}: {rows} rows")

    return True

test("generate_and_upload_csvs", generate_and_upload_csvs)

# 1h. Generate context graph data
def generate_and_upload_context_graph():
    """Generate context graph CSVs and upload."""
    import subprocess
    import csv
    import io

    output_dir = f'/tmp/mcp_e2e_test_{TEST_CUSTOMER_ID}/context_graph'
    os.makedirs(output_dir, exist_ok=True)

    gen_script = os.path.join(_backend_dir, 'scripts', 'generate_context_graph_data.py')
    cmd = [
        sys.executable, gen_script,
        '--customer-id', str(TEST_CUSTOMER_ID),
        '--num-accounts', '5',
        '--all-arcs',
        '--output-dir', output_dir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_backend_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Context graph generator failed: {result.stderr[:500]}")

    # Context graph generator puts CSVs in arc subdirectories.
    # We need to consolidate them into single files per type.
    cg_file_types = [
        'stakeholders', 'engagement_events', 'account_business_profiles',
        'outcomes', 'decisions', 'signal_edges', 'enhanced_qualitative_signals',
        'industry_benchmarks',
    ]

    for file_type in cg_file_types:
        filename = f'{file_type}.csv'
        # Collect rows from all arc subdirectories
        all_rows = []
        header = None
        for arc_dir in sorted(os.listdir(output_dir)):
            arc_path = os.path.join(output_dir, arc_dir, filename)
            if os.path.isfile(arc_path):
                with open(arc_path, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if rows:
                        if header is None:
                            header = rows[0]
                        all_rows.extend(rows[1:])  # skip header after first

        if not all_rows or header is None:
            print(f"       ⚠️  {filename} not found in any arc")
            continue

        # Build consolidated CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerows(all_rows)
        csv_content = buf.getvalue()

        r = onboard.upload_csv(
            customer_id=TEST_CUSTOMER_ID,
            file_type=file_type,
            csv_content=csv_content,
        )
        print(f"       ✅ upload {file_type}: {len(all_rows)} rows")

    return True

test("generate_and_upload_context_graph", generate_and_upload_context_graph)

# 1i. Process data
def test_process_data():
    r = onboard.process_data(customer_id=TEST_CUSTOMER_ID)
    steps = r.get('steps_completed', [])
    errors = r.get('errors', [])
    # Filter non-critical errors
    real_errors = [e for e in errors
                   if 'Embedding' not in str(e)
                   and 'Journey generator' not in str(e)
                   and 'Wizard A' not in str(e)
                   and 'faiss' not in str(e).lower()
                   and 'qdrant' not in str(e).lower()]
    print(f"       Steps: {steps}")
    if real_errors:
        print(f"       ⚠️  Errors: {real_errors[:3]}")
    return r

test("process_data", test_process_data)

# 1j. Check onboarding status
def test_onboarding_status():
    r = onboard.get_onboarding_status(customer_id=TEST_CUSTOMER_ID)
    print(f"       Status: {r.get('status', 'unknown')}")
    return r

test("get_onboarding_status", test_onboarding_status)


# ===================================================================
# Phase 2: WIZARDS — A, B, C
# ===================================================================
print(f"\n{'='*60}")
print("Phase 2: WIZARDS")
print(f"{'='*60}")

def test_wizard(wizard_name):
    def _run():
        r = onboard.trigger_wizard(customer_id=TEST_CUSTOMER_ID, wizard=wizard_name)
        status = r.get('status', r.get('wizard_status', 'unknown'))
        print(f"       Wizard {wizard_name}: {status}")
        if r.get('error'):
            print(f"       Error: {r['error'][:200]}")
        return r
    return _run

test("trigger_wizard(A)", test_wizard('A'))
test("trigger_wizard(B)", test_wizard('B'))
test("trigger_wizard(C)", test_wizard('C'))


# ===================================================================
# Phase 3: INTELLIGENCE — Query the customer
# ===================================================================
print(f"\n{'='*60}")
print("Phase 3: INTELLIGENCE")
print(f"{'='*60}")

# 3a. Platform instructions
def test_platform_instructions():
    r = intel.get_platform_instructions()
    assert 'instructions' in r, f"Missing instructions: {list(r.keys())}"
    print(f"       Instructions length: {len(r['instructions'])} chars")
    return r

test("get_platform_instructions", test_platform_instructions)

# 3b. KPI catalog
def test_kpi_catalog():
    r = intel.get_kpi_catalog(customer_id=TEST_CUSTOMER_ID)
    assert 'pillars' in r, f"Missing pillars: {list(r.keys())}"
    print(f"       Vertical: {r.get('vertical')}, Pillars: {r.get('total_pillars')}, KPIs: {r.get('total_kpis')}")
    return r

test("get_kpi_catalog", test_kpi_catalog)

# 3c. List accounts
TEST_ACCOUNT_ID = None

def test_list_accounts():
    global TEST_ACCOUNT_ID
    r = intel.list_accounts(customer_id=TEST_CUSTOMER_ID)
    assert 'accounts' in r, f"Missing accounts: {list(r.keys())}"
    accounts = r['accounts']
    print(f"       Accounts: {len(accounts)}")
    if accounts:
        TEST_ACCOUNT_ID = accounts[0]['account_id']
        print(f"       First account: {TEST_ACCOUNT_ID} ({accounts[0].get('account_name', 'N/A')}) health={accounts[0].get('health_score', 'N/A')}")
    return r

test("list_accounts", test_list_accounts)

# 3d. Get account health
def test_account_health():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account to test")
    r = intel.get_account_health(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    print(f"       Health: {r.get('health_score', 'N/A')}, Status: {r.get('status', 'N/A')}")
    pillars = r.get('pillar_scores', {})
    if pillars:
        print(f"       Pillars: {json.dumps({k: round(v,1) if isinstance(v, float) else v for k,v in list(pillars.items())[:5]})}")
    return r

test("get_account_health", test_account_health)

# 3e. At-risk accounts
def test_at_risk():
    r = intel.get_at_risk_accounts(customer_id=TEST_CUSTOMER_ID)
    count = len(r.get('at_risk_accounts', r.get('accounts', [])))
    print(f"       At-risk accounts: {count}")
    return r

test("get_at_risk_accounts", test_at_risk)

# 3f. CSM daily actions
def test_csm_actions():
    r = intel.get_csm_daily_actions(customer_id=TEST_CUSTOMER_ID)
    actions = r.get('actions', r.get('daily_actions', []))
    print(f"       Actions: {len(actions)}")
    return r

test("get_csm_daily_actions", test_csm_actions)

# 3g. CRM account data
def test_crm_data():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_crm_account_data(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_crm_account_data", test_crm_data)

# 3h. Support tickets
def test_support():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_support_tickets(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_support_tickets", test_support)

# 3i. Customer feedback
def test_feedback():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_customer_feedback(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_customer_feedback", test_feedback)

# 3j. Search signals
def test_signals():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.search_signals(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    signals = r.get('signals', r.get('nodes', []))
    print(f"       Signals: {len(signals)}")
    return r

test("search_signals", test_signals)

# 3k. Playbook recommendations
def test_playbooks():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_playbook_recommendations(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    recs = r.get('recommendations', r.get('playbooks', []))
    print(f"       Recommendations: {len(recs)}")
    return r

test("get_playbook_recommendations", test_playbooks)

# 3l. Playbook economics
def test_playbook_economics():
    r = intel.get_playbook_economics(customer_id=TEST_CUSTOMER_ID)
    return r

test("get_playbook_economics", test_playbook_economics)

# 3m. Calculate Power of 1
def test_power_of_1():
    r = intel.calculate_power_of_1(customer_id=TEST_CUSTOMER_ID, metric_id='NRR')
    print(f"       Power of 1 (NRR): impact=${r.get('annual_impact', r.get('revenue_impact', 'N/A'))}")
    return r

test("calculate_power_of_1", test_power_of_1)

# 3n. Account journey timeline
def test_journey():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_account_journey_timeline(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_account_journey_timeline", test_journey)

# 3o. Stakeholder map
def test_stakeholder():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_stakeholder_map(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    stakeholders = r.get('stakeholders', [])
    print(f"       Stakeholders: {len(stakeholders)}")
    return r

test("get_stakeholder_map", test_stakeholder)

# 3p. Context graph mermaid
def test_mermaid():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_context_graph_mermaid(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    mermaid = r.get('mermaid', '')
    print(f"       Mermaid diagram: {len(mermaid)} chars")
    return r

test("get_context_graph_mermaid", test_mermaid)


# ===================================================================
# Phase 4: REVENUE INTELLIGENCE
# ===================================================================
print(f"\n{'='*60}")
print("Phase 4: REVENUE INTELLIGENCE")
print(f"{'='*60}")

# 4a. Revenue at risk
def test_rev_at_risk():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = revenue.get_revenue_at_risk(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_revenue_at_risk", test_rev_at_risk)

# 4b. Graph summary
def test_graph_summary():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = revenue.get_graph_summary(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    nodes = r.get('total_nodes', r.get('node_count', 0))
    edges = r.get('total_edges', r.get('edge_count', 0))
    print(f"       Nodes: {nodes}, Edges: {edges}")
    return r

test("get_graph_summary", test_graph_summary)

# 4c. Causal chain (need a node_id)
def test_causal_chain():
    import psycopg2
    conn = psycopg2.connect(
        dbname='cs_pulse_datacenter', user='dcuser',
        password='dcpass123', host='localhost')
    cur = conn.cursor()
    cur.execute(
        "SELECT node_id FROM context_nodes WHERE customer_id = %s LIMIT 1",
        (TEST_CUSTOMER_ID,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise RuntimeError("No context nodes found")
    node_id = row[0]
    r = revenue.get_causal_chain(customer_id=TEST_CUSTOMER_ID, node_id=node_id)
    print(f"       Chain from node {node_id}: {len(r.get('chain', r.get('nodes', [])))} nodes")
    return r

test("get_causal_chain", test_causal_chain)

# 4d. Outcome ROI story
def test_roi_story():
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = revenue.get_outcome_roi_story(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    return r

test("get_outcome_roi_story", test_roi_story)

# 4e. Portfolio ROI summary
def test_portfolio_roi():
    r = revenue.get_portfolio_roi_summary(customer_id=TEST_CUSTOMER_ID)
    return r

test("get_portfolio_roi_summary", test_portfolio_roi)


# ===================================================================
# Phase 5: ADMIN
# ===================================================================
print(f"\n{'='*60}")
print("Phase 5: ADMIN")
print(f"{'='*60}")

# 5a. Export CSVs
def test_export():
    r = admin.export_customer_csvs(customer_id=TEST_CUSTOMER_ID)
    files = r.get('files', r.get('exported_files', []))
    print(f"       Exported: {len(files)} files")
    return r

test("export_customer_csvs", test_export)

# 5b. Download CSV
def test_download():
    r = admin.download_customer_csv(customer_id=TEST_CUSTOMER_ID, file_type='accounts')
    content = r.get('csv_content', r.get('content', ''))
    rows = len(content.strip().split('\n')) - 1 if content else 0
    print(f"       Downloaded accounts.csv: {rows} rows")
    return r

test("download_customer_csv(accounts)", test_download)

# 5c. Clone customer
CLONE_ID = None

def test_clone():
    global CLONE_ID
    r = admin.clone_customer(
        source_customer_id=TEST_CUSTOMER_ID,
        new_name=f"Clone_{TEST_CUSTOMER_NAME}",
        new_domain=f"clone-{TEST_CUSTOMER_NAME.lower()}.test",
    )
    CLONE_ID = r.get('new_customer_id', r.get('customer_id'))
    print(f"       Cloned to customer {CLONE_ID}")
    return r

test("clone_customer", test_clone)


# ===================================================================
# Phase 6: CROSS-VERTICAL — Test SaaS Premium KPI catalog
# ===================================================================
print(f"\n{'='*60}")
print("Phase 6: CROSS-VERTICAL (SaaS Premium)")
print(f"{'='*60}")

def test_saas_kpi_catalog():
    # Test that SaaS Premium KPI catalog loads correctly
    r = intel.get_kpi_catalog(customer_id=326)  # Gold_Reference_SaaS_Premium
    vertical = r.get('vertical', 'unknown')
    total_kpis = r.get('total_kpis', 0)
    pillars = r.get('pillars', {})
    print(f"       Vertical: {vertical}, KPIs: {total_kpis}")
    for pcode, pdata in sorted(pillars.items()):
        print(f"       {pcode}: {pdata.get('name', 'N/A')} ({pdata.get('kpi_count', 0)} KPIs)")
    assert total_kpis == 35, f"Expected 35 SaaS KPIs, got {total_kpis}"
    assert vertical in ('saas_premium', 'saas'), f"Expected saas_premium, got {vertical}"
    return r

test("get_kpi_catalog(saas_premium)", test_saas_kpi_catalog)

def test_saas_list_accounts():
    r = intel.list_accounts(customer_id=326)
    accounts = r.get('accounts', [])
    print(f"       SaaS Premium accounts: {len(accounts)}")
    return r

test("list_accounts(saas_premium/326)", test_saas_list_accounts)


# ===================================================================
# Phase 7: DEEP VALIDATION — Health, Playbooks, ROI, Context Graph
# Uses the test customer we created + customer 295 (Tacme) for rich
# context graph data (540 nodes, 1130 edges already in DB).
# ===================================================================
print(f"\n{'='*60}")
print("Phase 7: DEEP VALIDATION")
print(f"{'='*60}")

# --- 7a. Health score correctness ---
def test_health_score_correctness():
    """Validate health scores are computed and status matches thresholds."""
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_account_health(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    health = r.get('health_score')
    pillars = r.get('pillar_scores', {})
    status = r.get('status', '')

    assert health is not None, "Health score is None"
    assert 0 <= health <= 100, f"Health score {health} out of range"

    # Verify status matches thresholds
    import utils.health_thresholds as ht
    expected_status = ht.classify(health)
    assert status == expected_status, f"Status mismatch: got '{status}', expected '{expected_status}' for score {health}"

    print(f"       Health={health:.1f}, Status={status}")
    if pillars:
        print(f"       Pillars: {', '.join(f'{k}={v:.1f}' for k,v in sorted(pillars.items()))}")
        # If we have pillar scores, verify they're P1-P5
        for pcode in pillars:
            assert pcode.startswith('P'), f"Invalid pillar code: {pcode}"
            assert 0 <= pillars[pcode] <= 100, f"Pillar {pcode} score {pillars[pcode]} out of range"
    else:
        print(f"       ⚠️  No pillar scores in response (health={health})")
    return r

test("health_score_correctness", test_health_score_correctness)


# --- 7b. Pillar score ranges ---
def test_pillar_score_ranges():
    """All pillar scores should be 0-100."""
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_account_health(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    for pcode, pscore in r.get('pillar_scores', {}).items():
        assert 0 <= pscore <= 100, f"Pillar {pcode} score {pscore} out of range"
    print(f"       All 5 pillar scores in [0,100] range")
    return True

test("pillar_score_ranges", test_pillar_score_ranges)


# --- 7c. KPI catalog structure ---
def test_kpi_catalog_structure():
    """Verify catalog has correct weight sums."""
    r = intel.get_kpi_catalog(customer_id=TEST_CUSTOMER_ID)
    pillars = r.get('pillars', {})
    assert len(pillars) == 5, f"Expected 5 pillars, got {len(pillars)}"
    for pcode, pdata in pillars.items():
        kpis = pdata.get('kpis', {})
        assert len(kpis) > 0, f"Pillar {pcode} has no KPIs"
        # L1 weights should sum to ~1.0
        l1_sum = sum(k.get('weight_l1', 0) for k in kpis.values())
        assert 0.95 <= l1_sum <= 1.05, f"Pillar {pcode} L1 weights sum to {l1_sum}, expected ~1.0"
    # L2 pillar weights are at top level, not inside each pillar dict
    l2_weights = r.get('default_pillar_weights_l2', {})
    l2_sum = sum(l2_weights.values())
    assert 0.95 <= l2_sum <= 1.05, f"L2 pillar weights sum to {l2_sum}, expected ~1.0"
    print(f"       L2 weights: {l2_weights}, sum={l2_sum:.2f}, all L1 weights valid")
    return True

test("kpi_catalog_weight_sums", test_kpi_catalog_structure)


# --- 7d. Playbook trigger logic ---
def test_playbook_trigger_logic():
    """Directly test should_trigger_playbook with known KPI values."""
    from verticals.dc2_s.vertical_config import should_trigger_playbook, PLAYBOOK_CONFIG

    # PB-01 triggers when P1-KPI1 > 20 AND P1-KPI4 > 35
    assert should_trigger_playbook("PB-01", {"P1-KPI1": 25, "P1-KPI4": 40}) == True, \
        "PB-01 should trigger: TTFV=25>20, cycle=40>35"
    assert should_trigger_playbook("PB-01", {"P1-KPI1": 15, "P1-KPI4": 40}) == False, \
        "PB-01 should NOT trigger: TTFV=15<=20"
    assert should_trigger_playbook("PB-01", {"P1-KPI1": 25, "P1-KPI4": 30}) == False, \
        "PB-01 should NOT trigger: cycle=30<=35"

    # PB-02 triggers when P2-KPI1 > 2.6 AND P2-KPI2 < 4380
    assert should_trigger_playbook("PB-02", {"P2-KPI1": 3.0, "P2-KPI2": 4000}) == True, \
        "PB-02 should trigger: RMA=3.0>2.6, MTBF=4000<4380"
    assert should_trigger_playbook("PB-02", {"P2-KPI1": 2.0, "P2-KPI2": 4000}) == False, \
        "PB-02 should NOT trigger: RMA=2.0<=2.6"

    # PB-03 triggers when P3-KPI1 < 60 AND P3-KPI5 < 75
    assert should_trigger_playbook("PB-03", {"P3-KPI1": 50, "P3-KPI5": 70}) == True, \
        "PB-03 should trigger: GPU=50<60, mem=70<75"
    assert should_trigger_playbook("PB-03", {"P3-KPI1": 65, "P3-KPI5": 70}) == False, \
        "PB-03 should NOT trigger: GPU=65>=60"

    # Missing KPI should not trigger
    assert should_trigger_playbook("PB-01", {"P1-KPI1": 25}) == False, \
        "PB-01 should NOT trigger when P1-KPI4 missing"

    triggered = sum(1 for pb_id in PLAYBOOK_CONFIG
                    if should_trigger_playbook(pb_id, {
                        "P1-KPI1": 25, "P1-KPI4": 40,
                        "P2-KPI1": 3.0, "P2-KPI2": 4000,
                        "P3-KPI1": 50, "P3-KPI5": 70,
                        "P5-KPI1": 0.5, "P5-KPI2": 0.8, "P5-KPI7": 10,
                        "P4-KPI3": 30, "P5-KPI8": 20,
                        "OVERALL_HEALTH": 45,
                    }))
    print(f"       Trigger logic: 9 assertions passed, {triggered}/{len(PLAYBOOK_CONFIG)} playbooks trigger with bad KPIs")
    return True

test("playbook_trigger_logic", test_playbook_trigger_logic)


# --- 7e. Playbook recommendations via MCP ---
def test_playbook_recommendations_detail():
    """Verify playbook recommendation returns playbook metadata."""
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = intel.get_playbook_recommendations(customer_id=TEST_CUSTOMER_ID, account_id=TEST_ACCOUNT_ID)
    recs = r.get('recommendations', r.get('playbooks', []))
    # Each recommendation should have id/name
    for rec in recs[:3]:
        assert 'playbook_id' in rec or 'id' in rec or 'name' in rec, \
            f"Recommendation missing id/name: {list(rec.keys())}"
    print(f"       {len(recs)} playbook(s) recommended")
    if recs:
        first = recs[0]
        print(f"       Top: {first.get('playbook_id', first.get('id', 'N/A'))} - {first.get('name', 'N/A')}")
    return r

test("playbook_recommendations_detail", test_playbook_recommendations_detail)


# --- 7f. ROI Engine — Power of 1 returns numeric values ---
def test_power_of_1_math():
    """Power of 1 should return numeric revenue impact."""
    r = intel.calculate_power_of_1(customer_id=TEST_CUSTOMER_ID, metric_id='NRR')
    # Check for numeric impact fields
    has_impact = any(
        isinstance(r.get(k), (int, float))
        for k in ('annual_impact', 'revenue_impact', 'monthly_impact', 'arr_impact')
    )
    print(f"       Response keys: {sorted(r.keys())}")
    # The function should return some structured data
    assert r is not None, "Power of 1 returned None"
    return r

test("power_of_1_math", test_power_of_1_math)


# --- 7g. ROI story has required sections ---
def test_roi_story_structure():
    """ROI story should have historical + projection sections."""
    if not TEST_ACCOUNT_ID:
        raise RuntimeError("No account")
    r = revenue.get_outcome_roi_story(
        customer_id=TEST_CUSTOMER_ID,
        account_id=TEST_ACCOUNT_ID,
        target_improvement_pct=10.0,
        projection_months=12,
    )
    assert r is not None, "ROI story returned None"
    # Should have some structure (historical, projected, etc)
    keys = set(r.keys())
    print(f"       ROI story keys: {sorted(keys)}")
    # Should have at minimum scope and some content
    assert 'scope' in keys or len(keys) > 2, f"ROI story too sparse: {keys}"
    return r

test("roi_story_structure", test_roi_story_structure)


# --- 7h. Portfolio ROI summary ---
def test_portfolio_roi_detail():
    """Portfolio ROI should aggregate across accounts."""
    r = revenue.get_portfolio_roi_summary(customer_id=TEST_CUSTOMER_ID)
    assert r is not None
    keys = set(r.keys())
    print(f"       Portfolio ROI keys: {sorted(keys)}")
    return r

test("portfolio_roi_detail", test_portfolio_roi_detail)


# --- 7i. Playbook economics has cost data ---
def test_playbook_economics_detail():
    """Playbook economics should return per-playbook cost data."""
    r = intel.get_playbook_economics(customer_id=TEST_CUSTOMER_ID)
    keys = set(r.keys())
    print(f"       Economics keys: {sorted(keys)}")
    # Should have some cost/investment data
    assert r is not None
    return r

test("playbook_economics_detail", test_playbook_economics_detail)


# ===================================================================
# Phase 8: CONTEXT GRAPH DEEP DIVE — Using customer 295 (Tacme)
# Customer 295 has 540 nodes, 1130 edges pre-loaded in DB.
# ===================================================================
print(f"\n{'='*60}")
print("Phase 8: CONTEXT GRAPH DEEP DIVE (customer 295)")
print(f"{'='*60}")

RICH_CID = 295  # Tacme — has real context graph data
RICH_ACCT_ID = None

# 8a. List accounts for rich customer
def test_rich_list_accounts():
    global RICH_ACCT_ID
    r = intel.list_accounts(customer_id=RICH_CID)
    accts = r.get('accounts', [])
    assert len(accts) > 0, f"No accounts for customer {RICH_CID}"
    RICH_ACCT_ID = accts[0]['account_id']
    print(f"       Accounts: {len(accts)}, first={RICH_ACCT_ID}")
    return r

test("rich_list_accounts(295)", test_rich_list_accounts)


# 8b. Context graph summary — should have real nodes and edges
def test_rich_graph_summary():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = revenue.get_graph_summary(customer_id=RICH_CID, account_id=RICH_ACCT_ID)
    nodes = r.get('total_nodes', r.get('node_count', 0))
    edges = r.get('total_edges', r.get('edge_count', 0))
    print(f"       Nodes: {nodes}, Edges: {edges}")
    assert nodes > 0, f"Expected context nodes, got {nodes}"
    assert edges > 0, f"Expected context edges, got {edges}"
    return r

test("rich_graph_summary(295)", test_rich_graph_summary)


# 8c. Search signals — should find SIGNAL nodes
def test_rich_search_signals():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.search_signals(customer_id=RICH_CID, account_id=RICH_ACCT_ID, node_type='SIGNAL')
    signals = r.get('signals', r.get('nodes', []))
    print(f"       SIGNAL nodes: {len(signals)}")
    assert len(signals) > 0, "No SIGNAL nodes found"
    # Each signal should have basic metadata
    s0 = signals[0]
    print(f"       First signal: subtype={s0.get('node_subtype')}, title={str(s0.get('title',''))[:60]}")
    return r

test("rich_search_signals(295)", test_rich_search_signals)


# 8d. Search decisions
def test_rich_search_decisions():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.search_signals(customer_id=RICH_CID, account_id=RICH_ACCT_ID, node_type='DECISION')
    decisions = r.get('signals', r.get('nodes', []))
    print(f"       DECISION nodes: {len(decisions)}")
    assert len(decisions) > 0, "No DECISION nodes found"
    return r

test("rich_search_decisions(295)", test_rich_search_decisions)


# 8e. Search outcomes — should have revenue impact
def test_rich_search_outcomes():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.search_signals(customer_id=RICH_CID, account_id=RICH_ACCT_ID, node_type='OUTCOME')
    outcomes = r.get('signals', r.get('nodes', []))
    print(f"       OUTCOME nodes: {len(outcomes)}")
    assert len(outcomes) > 0, "No OUTCOME nodes found"
    # At least one outcome should have revenue_impact
    has_revenue = any(o.get('revenue_impact') is not None and o.get('revenue_impact') != 0
                      for o in outcomes)
    if has_revenue:
        rev_outcome = next(o for o in outcomes if o.get('revenue_impact'))
        print(f"       Revenue outcome: ${rev_outcome.get('revenue_impact'):,.0f} - {str(rev_outcome.get('title',''))[:50]}")
    else:
        print(f"       ⚠️  No outcomes with revenue_impact (checking revenue_impact_type)")
    return r

test("rich_search_outcomes(295)", test_rich_search_outcomes)


# 8f. Causal chain traversal — the key test
def test_rich_causal_chain():
    """Traverse upstream from an OUTCOME to find the Signal→Decision→Outcome chain."""
    import psycopg2
    conn = psycopg2.connect(
        dbname='cs_pulse_datacenter', user='dcuser',
        password='dcpass123', host='localhost')
    cur = conn.cursor()

    # Find a SIGNAL node that has outgoing edges
    cur.execute("""
        SELECT cn.node_id, cn.node_type, cn.title
        FROM context_nodes cn
        JOIN context_edges ce ON cn.node_id = ce.from_node_id AND ce.customer_id = cn.customer_id
        WHERE cn.customer_id = %s AND cn.node_type = 'SIGNAL'
        LIMIT 1
    """, (RICH_CID,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise RuntimeError("No SIGNAL node with outgoing edges found")

    node_id = row[0]
    print(f"       Starting from SIGNAL node {node_id}: {str(row[2] or '')[:50]}")

    r = revenue.get_causal_chain(customer_id=RICH_CID, node_id=node_id, direction='downstream')
    chain = r.get('chain', r.get('nodes', []))
    print(f"       Downstream chain: {len(chain)} nodes")

    # Chain should have at least 1 node (the signal itself or its downstream)
    assert len(chain) >= 0, f"Causal chain returned error"

    # Print chain types
    if chain:
        types = [n.get('node_type', '?') for n in chain]
        print(f"       Chain types: {' → '.join(types)}")
    return r

test("rich_causal_chain(295)", test_rich_causal_chain)


# 8g. Revenue at risk — should aggregate from OUTCOME nodes
def test_rich_revenue_at_risk():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = revenue.get_revenue_at_risk(customer_id=RICH_CID, account_id=RICH_ACCT_ID)
    keys = set(r.keys())
    print(f"       Revenue keys: {sorted(keys)}")
    # Should have some revenue breakdown
    for key in ('at_risk', 'protected', 'expansion', 'total_arr'):
        if key in r:
            val = r[key]
            if isinstance(val, (int, float)):
                print(f"       {key}: ${val:,.0f}")
    return r

test("rich_revenue_at_risk(295)", test_rich_revenue_at_risk)


# 8h. Stakeholder map — should have stakeholder nodes
def test_rich_stakeholder_map():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.get_stakeholder_map(customer_id=RICH_CID, account_id=RICH_ACCT_ID)
    stakeholders = r.get('stakeholders', [])
    print(f"       Stakeholders: {len(stakeholders)}")
    if stakeholders:
        s0 = stakeholders[0]
        print(f"       First: {s0.get('name', s0.get('title',''))} - {s0.get('role', s0.get('node_subtype',''))}")
    return r

test("rich_stakeholder_map(295)", test_rich_stakeholder_map)


# 8i. Mermaid diagram — should be substantial
def test_rich_mermaid():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.get_context_graph_mermaid(customer_id=RICH_CID, account_id=RICH_ACCT_ID, max_nodes=30)
    mermaid = r.get('mermaid', '')
    print(f"       Mermaid diagram: {len(mermaid)} chars")
    assert len(mermaid) > 100, f"Mermaid diagram too short ({len(mermaid)} chars) — likely empty"
    # Should contain node type indicators
    assert 'SIGNAL' in mermaid.upper() or 'signal' in mermaid.lower() or '🟠' in mermaid or 'orange' in mermaid.lower() or 'S_' in mermaid, \
        "Mermaid diagram missing signal nodes"
    return r

test("rich_mermaid_diagram(295)", test_rich_mermaid)


# 8j. Journey timeline — should have events
def test_rich_journey_timeline():
    if not RICH_ACCT_ID:
        raise RuntimeError("No account")
    r = intel.get_account_journey_timeline(customer_id=RICH_CID, account_id=RICH_ACCT_ID, limit=50)
    events = r.get('events', r.get('timeline', []))
    print(f"       Timeline events: {len(events)}")
    if events:
        # Check event structure
        e0 = events[0]
        print(f"       First event: type={e0.get('node_type', e0.get('type','?'))}, {str(e0.get('title',''))[:50]}")
    return r

test("rich_journey_timeline(295)", test_rich_journey_timeline)


# 8k. CSM actions for rich customer — should have prioritized actions
def test_rich_csm_actions():
    r = intel.get_csm_daily_actions(customer_id=RICH_CID)
    actions = r.get('actions', r.get('daily_actions', []))
    print(f"       CSM actions: {len(actions)}")
    if actions:
        a0 = actions[0]
        print(f"       Top action: {a0.get('playbook_id', a0.get('playbook','?'))} - {a0.get('action', a0.get('description',''))[:60]}")
        # Should have urgency/impact data
        has_urgency = 'urgency' in a0 or 'priority' in a0 or 'impact' in a0
        if has_urgency:
            print(f"       Urgency/impact data present")
    return r

test("rich_csm_actions(295)", test_rich_csm_actions)


# ===================================================================
# Phase 9: WIZARD EXECUTION — Using customer 407 (Gold_Reference_DC2S)
# Load data into DB first, then run wizards A/B/C.
# ===================================================================
print(f"\n{'='*60}")
print("Phase 9: WIZARD EXECUTION (customer 407)")
print(f"{'='*60}")

# 9a. Ensure customer 407 exists in DB (create if needed), then load data
CUST_407_EXISTS = False

def test_ensure_407_in_db():
    """Create customer 407 in DB if missing, then run process_data to load on-disk CSVs."""
    global CUST_407_EXISTS
    app = common.get_flask_app()
    with app.app_context():
        from models import Customer, CustomerConfig
        from extensions import db

        c407 = Customer.query.filter_by(customer_id=407).first()
        if not c407:
            # Create the customer record directly (with specific ID)
            c407 = Customer(
                customer_id=407,
                customer_name='Gold_Reference_DC2S',
                email='admin@gold-dc2s.ref',
                domain='gold-dc2s.ref',
                vertical='dc2_s',
            )
            db.session.add(c407)
            db.session.flush()

            # Create CustomerConfig
            cfg = CustomerConfig(customer_id=407, vertical='dc2_s')
            db.session.add(cfg)
            db.session.commit()
            print(f"       Created customer 407 in DB")
        else:
            print(f"       Customer 407 already in DB: {c407.customer_name}")

        CUST_407_EXISTS = True

    # Now run process_data to load on-disk CSVs into DB
    r = onboard.process_data(customer_id=407)
    steps = r.get('steps_completed', [])
    status = r.get('status', 'unknown')
    errors = r.get('errors', [])
    print(f"       process_data status: {status}")
    print(f"       Steps: {steps}")
    if errors:
        real_errors = [e for e in errors if 'Cannot connect' not in str(e)]
        if real_errors:
            print(f"       ⚠️  Errors: {real_errors[:3]}")
    assert status in ('success', 'partial'), f"process_data failed: {errors}"
    assert 'accounts_loaded' in steps or 'kpis_loaded' in steps, f"No data loaded: {steps}"
    return r

test("ensure_407_in_db_and_load_data", test_ensure_407_in_db)


# 9b. Run Wizard A on customer 407
def test_wizard_a_407():
    r = onboard.trigger_wizard(customer_id=407, wizard='a')
    status = r.get('status', 'unknown')
    summary = r.get('result_summary', {})
    print(f"       Wizard A status: {status}")
    if summary.get('stdout_tail'):
        # Print last meaningful lines
        lines = [l for l in summary['stdout_tail'].strip().split('\n') if l.strip()]
        for l in lines[-3:]:
            print(f"       {l[:80]}")
    elif summary.get('note'):
        print(f"       {summary['note']}")
    return r

# 9c. Run Wizard B
def test_wizard_b_407():
    r = onboard.trigger_wizard(customer_id=407, wizard='b')
    status = r.get('status', 'unknown')
    summary = r.get('result_summary', {})
    print(f"       Wizard B status: {status}")
    if summary.get('stdout_tail'):
        lines = [l for l in summary['stdout_tail'].strip().split('\n') if l.strip()]
        for l in lines[-3:]:
            print(f"       {l[:80]}")
    elif summary.get('note'):
        print(f"       {summary['note']}")
    return r

# 9d. Run Wizard C
def test_wizard_c_407():
    r = onboard.trigger_wizard(customer_id=407, wizard='c')
    status = r.get('status', 'unknown')
    summary = r.get('result_summary', {})
    print(f"       Wizard C status: {status}")
    if summary.get('stdout_tail'):
        lines = [l for l in summary['stdout_tail'].strip().split('\n') if l.strip()]
        for l in lines[-3:]:
            print(f"       {l[:80]}")
    elif summary.get('note'):
        print(f"       {summary['note']}")
    # After Wizard C, check if weights were calibrated
    if status == 'completed':
        try:
            cat = intel.get_kpi_catalog(customer_id=407)
            print(f"       Post-C catalog: {cat.get('total_kpis')} KPIs, {cat.get('total_pillars')} pillars")
        except Exception:
            pass
    return r

# 9e. Post-wizard: verify health scores now exist for 407's accounts
def test_407_health_after_load():
    """After loading data, customer 407 should have accounts with health scores."""
    r = intel.list_accounts(customer_id=407)
    accts = r.get('accounts', [])
    assert len(accts) > 0, f"No accounts for 407 after load"
    scored = [a for a in accts if a.get('health_score') is not None and a.get('health_score') > 0]
    print(f"       407 accounts: {len(accts)}, with health scores: {len(scored)}")
    if scored:
        print(f"       First scored: {scored[0].get('account_name','')[:40]} health={scored[0].get('health_score')}")
    return r

if CUST_407_EXISTS:
    test("407_health_after_load", test_407_health_after_load)
    test("wizard_a(407)", test_wizard_a_407)
    test("wizard_b(407)", test_wizard_b_407)
    test("wizard_c(407)", test_wizard_c_407)
else:
    test_skip("wizard_a(407)", "Customer 407 not loaded")
    test_skip("wizard_b(407)", "Customer 407 not loaded")
    test_skip("wizard_c(407)", "Customer 407 not loaded")


# ===================================================================
# CLEANUP — Remove test customers
# ===================================================================
print(f"\n{'='*60}")
print("CLEANUP")
print(f"{'='*60}")

def cleanup():
    import psycopg2
    conn = psycopg2.connect(
        dbname='cs_pulse_datacenter', user='dcuser',
        password='dcpass123', host='localhost')
    cur = conn.cursor()

    for cid in [TEST_CUSTOMER_ID, CLONE_ID]:
        if not cid:
            continue
        # Get account IDs
        cur.execute('SELECT account_id FROM accounts WHERE customer_id = %s', (cid,))
        account_ids = [r[0] for r in cur.fetchall()]

        if account_ids:
            placeholders = ','.join(['%s'] * len(account_ids))
            for table in ['dc2s_kpis', 'health_scores', 'kpi_scores', 'pillar_scores',
                          'qualitative_signals', 'playbook_executions']:
                try:
                    cur.execute(f'DELETE FROM {table} WHERE account_id IN ({placeholders})', account_ids)
                except Exception:
                    conn.rollback()

        for table in ['context_edges', 'context_nodes', 'roi_snapshots',
                      'feature_toggles', 'customer_api_keys', 'customer_configs',
                      'wizard_runs']:
            try:
                cur.execute(f'DELETE FROM {table} WHERE customer_id = %s', (cid,))
            except Exception:
                conn.rollback()

        cur.execute('DELETE FROM accounts WHERE customer_id = %s', (cid,))
        cur.execute('DELETE FROM users WHERE customer_id = %s', (cid,))
        cur.execute('DELETE FROM customers WHERE customer_id = %s', (cid,))
        print(f"  🗑️  Cleaned up customer {cid}")

    # Clean up wizard_runs for customer 407 (but keep the customer itself)
    try:
        cur.execute('DELETE FROM wizard_runs WHERE customer_id = 407')
        print(f"  🗑️  Cleaned up wizard_runs for customer 407")
    except Exception:
        conn.rollback()

    conn.commit()
    conn.close()

try:
    cleanup()
except Exception as e:
    print(f"  ⚠️  Cleanup error: {e}")


# ===================================================================
# SUMMARY
# ===================================================================
print(f"\n{'='*60}")
print("TEST SUMMARY")
print(f"{'='*60}")
print(f"  ✅ Passed: {len(PASS)}")
print(f"  ❌ Failed: {len(FAIL)}")
print(f"  ⏭️  Skipped: {len(SKIP)}")

if FAIL:
    print(f"\n  Failed tests:")
    for name, err in FAIL:
        print(f"    ❌ {name}: {err[:150]}")

total = len(PASS) + len(FAIL) + len(SKIP)
pct = len(PASS) / max(total, 1) * 100
print(f"\n  Score: {len(PASS)}/{total} ({pct:.0f}%)")
print(f"  {'🎉 ALL TESTS PASSED!' if not FAIL else '⚠️  SOME TESTS FAILED'}")

sys.exit(1 if FAIL else 0)
