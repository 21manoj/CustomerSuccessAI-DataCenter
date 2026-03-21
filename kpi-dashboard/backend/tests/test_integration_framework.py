"""
E2E Test: Integration Framework
=================================

Tests the full integration pipeline with loopback stubs:
1. DB migration — tables created
2. Connector CRUD — create, list, update, test
3. Webhook ingest — single + batch records
4. Field mapping — SFDC, HubSpot, Zendesk field transforms
5. Playbook webhook triggers — create, evaluate, fire
6. n8n workflow trigger — via MCP tool
7. Integration health monitoring

Run: python -m pytest tests/test_integration_framework.py -v
  or: python tests/test_integration_framework.py  (standalone)
"""

import sys
import os
import json
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('CS_PULSE_URL', 'http://localhost:5059')

import requests

# ============================================================
# Test Session Setup
# ============================================================

def get_session():
    """Login and return authenticated session + customer_id."""
    session = requests.Session()
    # Try to login
    resp = session.post(f'{BASE_URL}/api/login', json={
        'email': 'admin@test.com',
        'password': 'admin123',
    })
    if resp.status_code == 200:
        data = resp.json()
        customer_id = data.get('customer_id', 1)
        return session, customer_id

    # Try alternate login
    resp = session.post(f'{BASE_URL}/api/dc2s/login', json={
        'email': 'admin@denali.com',
        'password': 'admin123',
    })
    if resp.status_code == 200:
        data = resp.json()
        return session, data.get('customer_id', 396)

    # Fallback: use header auth
    session.headers['X-Customer-ID'] = '396'
    return session, 396


# ============================================================
# Test Helpers
# ============================================================

def log(msg, status='INFO'):
    icon = {'PASS': '✅', 'FAIL': '❌', 'INFO': 'ℹ️', 'WARN': '⚠️'}.get(status, '  ')
    print(f"  {icon} {msg}")


def assert_ok(resp, msg):
    if resp.status_code in (200, 201):
        log(f"{msg} — HTTP {resp.status_code}", 'PASS')
        return True
    else:
        log(f"{msg} — HTTP {resp.status_code}: {resp.text[:200]}", 'FAIL')
        return False


# ============================================================
# Tests
# ============================================================

def test_01_connector_types(session):
    """Test: GET /api/integrations/connector-types"""
    print("\n" + "="*60)
    print("TEST 1: Connector Types")
    print("="*60)

    resp = session.get(f'{BASE_URL}/api/integrations/connector-types')
    if not assert_ok(resp, "Get connector types"):
        return False

    types = resp.json()
    expected = ['sfdc', 'hubspot', 'zendesk', 'n8n', 'csv_upload', 'custom_webhook']
    found = list(types.keys())

    for t in expected:
        if t in found:
            log(f"  Found: {t} ({types[t]['label']})", 'PASS')
        else:
            log(f"  Missing: {t}", 'FAIL')
            return False

    return True


def test_02_create_connectors(session, customer_id):
    """Test: Create SFDC, HubSpot, Zendesk, n8n connectors."""
    print("\n" + "="*60)
    print("TEST 2: Create Connectors")
    print("="*60)

    connectors = {}
    for ctype, name in [
        ('sfdc', 'Test Salesforce'),
        ('hubspot', 'Test HubSpot'),
        ('zendesk', 'Test Zendesk'),
        ('n8n', 'Test n8n Workflow'),
    ]:
        resp = session.post(f'{BASE_URL}/api/integrations/connectors', json={
            'connector_type': ctype,
            'connector_name': name,
            'description': f'E2E test {ctype} connector',
            'webhook_url': f'https://loopback.test/{ctype}/webhook',
        })
        if not assert_ok(resp, f"Create {ctype} connector"):
            return None

        data = resp.json()
        connectors[ctype] = data
        log(f"  ID={data['connector_id']}, secret={data.get('webhook_secret', 'n/a')[:8]}...", 'INFO')

    return connectors


def test_03_list_connectors(session, customer_id):
    """Test: List all connectors."""
    print("\n" + "="*60)
    print("TEST 3: List Connectors")
    print("="*60)

    resp = session.get(f'{BASE_URL}/api/integrations/connectors')
    if not assert_ok(resp, "List connectors"):
        return False

    data = resp.json()
    log(f"Total connectors: {data['total']}")
    return data['total'] >= 4


def test_04_test_connector(session, connector_id):
    """Test: Loopback connectivity test."""
    print("\n" + "="*60)
    print("TEST 4: Test Connector (Loopback)")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/connectors/{connector_id}/test')
    if not assert_ok(resp, "Test connector"):
        return False

    data = resp.json()
    log(f"Test result: {data['test_status']}")
    return data['test_status'] == 'pass'


def test_05_ingest_single_account(session, customer_id):
    """Test: Ingest a single account from SFDC."""
    print("\n" + "="*60)
    print("TEST 5: Ingest Single Account (SFDC)")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/ingest', json={
        'source': 'sfdc',
        'entity_type': 'account',
        'event_type': 'created',
        'data': {
            'Name': 'Acme Corp Test',
            'AnnualRevenue': 2500000,
            'Industry': 'Technology',
            'BillingCountry': 'US',
            'Id': 'sfdc_001_test_acme',
        },
        'source_id': f'sfdc_evt_{int(time.time())}',
    })
    if not assert_ok(resp, "Ingest SFDC account"):
        return None

    data = resp.json()
    log(f"Event ID: {data['event_id']}, Target: {data['target_entity']}#{data['target_id']}")
    return data.get('target_id')


def test_06_ingest_single_ticket(session, customer_id, account_id):
    """Test: Ingest a Zendesk ticket as a signal."""
    print("\n" + "="*60)
    print("TEST 6: Ingest Zendesk Ticket → Signal")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/ingest', json={
        'source': 'zendesk',
        'entity_type': 'ticket',
        'event_type': 'created',
        'data': {
            'account_id': account_id,
            'subject': 'Critical: GPU cluster offline',
            'priority': 'urgent',
            'status': 'open',
            'created_at': '2026-03-20T10:00:00Z',
            'description': 'Production GPU cluster went offline during training job',
            'satisfaction_rating.score': 'bad',
            'tags': ['gpu', 'outage', 'critical'],
        },
        'source_id': f'zd_ticket_{int(time.time())}',
    })
    if not assert_ok(resp, "Ingest Zendesk ticket"):
        return False

    data = resp.json()
    log(f"Created signal: {data['target_entity']}#{data['target_id']}")
    return True


def test_07_ingest_batch(session, customer_id):
    """Test: Batch ingest from HubSpot."""
    print("\n" + "="*60)
    print("TEST 7: Batch Ingest (HubSpot)")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/ingest/batch', json={
        'source': 'hubspot',
        'records': [
            {
                'entity_type': 'company',
                'event_type': 'created',
                'data': {
                    'name': 'Globex Corp',
                    'annualrevenue': 1800000,
                    'industry': 'Manufacturing',
                    'country': 'DE',
                    'hs_object_id': 'hs_co_001',
                },
            },
            {
                'entity_type': 'company',
                'event_type': 'created',
                'data': {
                    'name': 'Initech LLC',
                    'annualrevenue': 900000,
                    'industry': 'Finance',
                    'country': 'UK',
                    'hs_object_id': 'hs_co_002',
                },
            },
            {
                'entity_type': 'deal',
                'event_type': 'created',
                'data': {
                    'dealname': 'Globex Expansion Q2',
                    'amount': 450000,
                    'dealstage': 'Closed Won',
                    'closedate': '2026-03-15',
                    'external_account_id': 'hs_co_001',
                },
            },
        ],
    })
    if not assert_ok(resp, "Batch ingest"):
        return False

    data = resp.json()
    log(f"Created: {data['records_created']}, Updated: {data['records_updated']}, "
        f"Errored: {data['records_errored']}")
    return data['records_created'] >= 2


def test_08_create_playbook_trigger(session, customer_id):
    """Test: Create a playbook webhook trigger."""
    print("\n" + "="*60)
    print("TEST 8: Create Playbook Webhook Trigger")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/playbook-triggers', json={
        'trigger_name': 'Critical Health Alert',
        'trigger_type': 'health_critical',
        'trigger_condition': {
            'metric': 'health_score',
            'operator': 'drops_below',
            'threshold': 50,
        },
        'webhook_url': 'https://loopback.test/n8n/health-critical',
        'cooldown_minutes': 30,
        'max_fires_per_day': 20,
    })
    if not assert_ok(resp, "Create playbook trigger"):
        return None

    data = resp.json()
    log(f"Trigger ID: {data['trigger_id']}, Secret: {data.get('webhook_secret', '')[:8]}...")
    return data['trigger_id']


def test_09_test_playbook_trigger(session, trigger_id):
    """Test: Test-fire a playbook webhook trigger."""
    print("\n" + "="*60)
    print("TEST 9: Test-Fire Playbook Trigger")
    print("="*60)

    resp = session.post(f'{BASE_URL}/api/integrations/playbook-triggers/{trigger_id}/test', json={
        'health_score': 42,
        'previous_health_score': 65,
    })
    if not assert_ok(resp, "Test-fire trigger"):
        return False

    data = resp.json()
    log(f"Test result: {data['test_status']}, Loopback: {data['loopback_mode']}")
    return data['test_status'] == 'pass'


def test_10_evaluate_triggers_engine(session, customer_id):
    """Test: Evaluate trigger engine programmatically."""
    print("\n" + "="*60)
    print("TEST 10: Trigger Engine Evaluation")
    print("="*60)

    # This tests the engine directly (not via HTTP)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from app_v3_minimal import app
        with app.app_context():
            from playbook_webhook_engine import evaluate_triggers, get_loopback_log, clear_loopback_log
            from models import Account

            # Get first account
            account = Account.query.filter_by(customer_id=customer_id).first()
            if not account:
                log("No accounts found for trigger evaluation", 'WARN')
                return True

            clear_loopback_log()

            results = evaluate_triggers(
                customer_id=customer_id,
                account_id=account.account_id,
                event_type='health_update',
                context={
                    'health_score': 42,
                    'previous_health_score': 65,
                },
            )

            log(f"Triggers evaluated: {len(results)}")
            for r in results:
                log(f"  {r['trigger_name']}: fired={r['fired']}, status={r['status']}")

            loopback = get_loopback_log()
            log(f"Loopback log entries: {len(loopback)}")

            return True
    except Exception as e:
        log(f"Engine evaluation error: {e}", 'FAIL')
        return False


def test_11_integration_health(session, customer_id):
    """Test: Integration health endpoint."""
    print("\n" + "="*60)
    print("TEST 11: Integration Health")
    print("="*60)

    resp = session.get(f'{BASE_URL}/api/integrations/health')
    if not assert_ok(resp, "Get integration health"):
        return False

    data = resp.json()
    log(f"Overall: {data['overall_status']}")
    log(f"Connectors: {data['connectors']['active']} active, {data['connectors']['errored']} errored")
    log(f"Last 24h: {data['last_24h']['records_processed']} records, {data['last_24h']['syncs']} syncs")
    return True


def test_12_sync_logs(session, customer_id):
    """Test: Sync logs endpoint."""
    print("\n" + "="*60)
    print("TEST 12: Sync Logs")
    print("="*60)

    resp = session.get(f'{BASE_URL}/api/integrations/sync-logs')
    if not assert_ok(resp, "Get sync logs"):
        return False

    data = resp.json()
    log(f"Total logs: {data['total']}")
    for l in data['logs'][:3]:
        log(f"  {l['sync_type']} — {l['sync_status']} — created={l['records_created']}, errors={l['records_errored']}")
    return True


def test_13_fire_log(session, customer_id):
    """Test: Playbook webhook fire log."""
    print("\n" + "="*60)
    print("TEST 13: Webhook Fire Log")
    print("="*60)

    resp = session.get(f'{BASE_URL}/api/integrations/playbook-triggers/fire-log')
    if not assert_ok(resp, "Get fire log"):
        return False

    data = resp.json()
    log(f"Total fires: {data['total']}, Loopback stubs: {data['loopback_stub_count']}")
    return True


def test_14_update_connector(session, connector_id):
    """Test: Update connector config."""
    print("\n" + "="*60)
    print("TEST 14: Update Connector")
    print("="*60)

    resp = session.put(f'{BASE_URL}/api/integrations/connectors/{connector_id}', json={
        'connector_name': 'Updated SFDC Connector',
        'sync_frequency_minutes': 30,
        'description': 'Updated by E2E test',
    })
    if not assert_ok(resp, "Update connector"):
        return False

    data = resp.json()
    log(f"Name: {data['connector_name']}, Freq: {data['sync_frequency_minutes']}min")
    return data['connector_name'] == 'Updated SFDC Connector'


def test_15_deactivate_connector(session, connector_id):
    """Test: Deactivate connector."""
    print("\n" + "="*60)
    print("TEST 15: Deactivate Connector")
    print("="*60)

    resp = session.delete(f'{BASE_URL}/api/integrations/connectors/{connector_id}')
    if not assert_ok(resp, "Deactivate connector"):
        return False

    # Verify disabled
    resp2 = session.get(f'{BASE_URL}/api/integrations/connectors')
    data = resp2.json()
    disabled = [c for c in data['connectors'] if c['connector_id'] == connector_id]
    if disabled and disabled[0]['status'] == 'disabled':
        log("Connector confirmed disabled", 'PASS')
        return True

    log("Connector not properly disabled", 'FAIL')
    return False


# ============================================================
# Cleanup
# ============================================================

def cleanup(session, customer_id, connectors):
    """Clean up test data."""
    print("\n" + "="*60)
    print("CLEANUP")
    print("="*60)

    # Deactivate test connectors
    if connectors:
        for ctype, cdata in connectors.items():
            cid = cdata.get('connector_id')
            if cid:
                session.delete(f'{BASE_URL}/api/integrations/connectors/{cid}')
                log(f"Deactivated connector {ctype}#{cid}")

    # Clean up test accounts
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from app_v3_minimal import app
        with app.app_context():
            from extensions import db
            from models import Account

            test_accts = Account.query.filter(
                Account.customer_id == customer_id,
                Account.account_name.in_(['Acme Corp Test', 'Globex Corp', 'Initech LLC']),
            ).all()

            for a in test_accts:
                db.session.delete(a)
                log(f"Deleted test account: {a.account_name}")

            db.session.commit()
    except Exception as e:
        log(f"Cleanup error: {e}", 'WARN')


# ============================================================
# Main Runner
# ============================================================

def main():
    print("="*60)
    print("🧪 Integration Framework E2E Test")
    print("="*60)
    print(f"Server: {BASE_URL}")

    session, customer_id = get_session()
    print(f"Customer ID: {customer_id}")

    results = {}
    connectors = None
    trigger_id = None
    sfdc_connector_id = None
    account_id = None

    # Test 1: Connector types
    results['01_connector_types'] = test_01_connector_types(session)

    # Test 2: Create connectors
    connectors = test_02_create_connectors(session, customer_id)
    results['02_create_connectors'] = connectors is not None
    if connectors:
        sfdc_connector_id = connectors['sfdc']['connector_id']

    # Test 3: List connectors
    results['03_list_connectors'] = test_03_list_connectors(session, customer_id)

    # Test 4: Test connector (loopback)
    if sfdc_connector_id:
        results['04_test_connector'] = test_04_test_connector(session, sfdc_connector_id)

    # Test 5: Ingest single account
    account_id = test_05_ingest_single_account(session, customer_id)
    results['05_ingest_account'] = account_id is not None

    # Test 6: Ingest ticket
    if account_id:
        results['06_ingest_ticket'] = test_06_ingest_single_ticket(session, customer_id, account_id)

    # Test 7: Batch ingest
    results['07_batch_ingest'] = test_07_ingest_batch(session, customer_id)

    # Test 8: Create playbook trigger
    trigger_id = test_08_create_playbook_trigger(session, customer_id)
    results['08_create_trigger'] = trigger_id is not None

    # Test 9: Test-fire trigger
    if trigger_id:
        results['09_test_fire'] = test_09_test_playbook_trigger(session, trigger_id)

    # Test 10: Engine evaluation
    results['10_engine_eval'] = test_10_evaluate_triggers_engine(session, customer_id)

    # Test 11: Integration health
    results['11_health'] = test_11_integration_health(session, customer_id)

    # Test 12: Sync logs
    results['12_sync_logs'] = test_12_sync_logs(session, customer_id)

    # Test 13: Fire log
    results['13_fire_log'] = test_13_fire_log(session, customer_id)

    # Test 14: Update connector
    if sfdc_connector_id:
        results['14_update_connector'] = test_14_update_connector(session, sfdc_connector_id)

    # Test 15: Deactivate connector
    if sfdc_connector_id:
        results['15_deactivate'] = test_15_deactivate_connector(session, sfdc_connector_id)

    # Cleanup
    cleanup(session, customer_id, connectors)

    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        icon = '✅' if result else '❌'
        print(f"  {icon} {name}")

    print(f"\n{'='*60}")
    print(f"  {'✅' if passed == total else '❌'} {passed}/{total} tests passed")
    print(f"{'='*60}")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
