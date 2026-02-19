"""
Tests for Phase 0, 1, and 2 implementation
- Phase 0.1: Account model has journey_phase, renewal_date, contract_start_date, contract_value
- Phase 0.2: _sync_journey_phase() wired into DC2S health recalculation
- Phase 0.3: Recommendations endpoint uses real PLAYBOOK_CONFIG trigger logic
- Phase 1:   New tables (CustomerActionBinding, IntegrationCredential, etc.) + model extensions
- Phase 2:   TriggerValidationResult model + PlaybookTriggerValidator

Uses a minimal Flask app to avoid importing the full app.py (which has heavy
import-time dependencies on Anthropic/OpenAI/Qdrant not needed for these tests).
"""

import os
import sys
import json
import pytest
import uuid
from datetime import datetime, timedelta

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Suppress the DC2_S vertical initialization print statements during test collection
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/testdb')

from flask import Flask
from extensions import db as _db


def _create_test_app():
    """Build a minimal Flask app with only the models we need."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _db.init_app(app)

    with app.app_context():
        # Import models (triggers SQLAlchemy table registration)
        import models  # noqa: F401
        import models_action_interface  # noqa: F401
        # Register the DC2S blueprint for endpoint tests
        from verticals.dc2_s.api_routes import dc2s_api
        app.register_blueprint(dc2s_api, url_prefix='/api/dc2s')

    return app


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope='module')
def app_ctx():
    app = _create_test_app()
    with app.app_context():
        _db.create_all()
        yield app, _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_session(app_ctx):
    yield
    _db.session.rollback()


def _seed_dc2s_account(db_inst, customer_id=1, account_id=100, deployment_days_ago=200):
    from models import Customer, Account

    cust = _db.session.get(Customer, customer_id)
    if not cust:
        cust = Customer(customer_id=customer_id, customer_name=f'TestCo-{customer_id}',
                        email=f'test{customer_id}@test.com')
        db_inst.session.add(cust)
        db_inst.session.flush()

    deploy_date = (datetime.utcnow() - timedelta(days=deployment_days_ago)).strftime('%Y-%m-%d')
    acct = Account(
        account_id=account_id,
        customer_id=customer_id,
        account_name=f'DC Account {account_id}',
        vertical='dc2_s',
        profile_metadata={
            'vertical': 'dc2_S',
            'deployment_type': 'on_premise',
            'deployment_date': deploy_date,
            'gpu_count': 64,
            'gpu_model': 'H100',
        },
    )
    db_inst.session.add(acct)
    db_inst.session.flush()
    return acct


def _seed_kpis(db_inst, account_id, kpi_map):
    from models import DC2SKPI
    now = datetime.utcnow()
    for code, val in kpi_map.items():
        db_inst.session.add(DC2SKPI(
            account_id=account_id,
            kpi_code=code,
            value=val,
            measured_at=now,
        ))
    db_inst.session.flush()


# ============================================================
# Phase 0.1: Account model columns
# ============================================================

class TestPhase0_1_AccountColumns:
    def test_journey_phase_column_exists(self, app_ctx):
        from models import Account
        acct = Account(account_id=900, customer_id=1, account_name='Schema Test',
                       journey_phase='deployment')
        assert acct.journey_phase == 'deployment'

    def test_journey_phase_default(self, app_ctx):
        """After INSERT, journey_phase should default to 'onboarding'."""
        _, db_inst = app_ctx
        from models import Customer, Account
        cust = _db.session.get(Customer, 1)
        if not cust:
            cust = Customer(customer_id=1, customer_name='Default Test', email='default@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()
        acct = Account(account_id=901, customer_id=1, account_name='Default Phase')
        db_inst.session.add(acct)
        db_inst.session.flush()
        # After flush the column default is applied
        assert acct.journey_phase == 'onboarding'

    def test_renewal_date_column(self, app_ctx):
        from models import Account
        dt = datetime(2026, 12, 31)
        acct = Account(account_id=902, customer_id=1, account_name='Renewal Test',
                       renewal_date=dt)
        assert acct.renewal_date == dt

    def test_contract_columns(self, app_ctx):
        from models import Account
        acct = Account(account_id=903, customer_id=1, account_name='Contract Test',
                       contract_start_date=datetime(2025, 1, 1), contract_value=5000000)
        assert acct.contract_start_date is not None
        assert float(acct.contract_value) == 5000000.0


# ============================================================
# Phase 0.2: _sync_journey_phase
# ============================================================

class TestPhase0_2_JourneyPhaseSync:
    def test_phase_deployment(self, app_ctx):
        _, db_inst = app_ctx
        _seed_dc2s_account(db_inst, customer_id=2, account_id=201, deployment_days_ago=30)
        db_inst.session.commit()

        from verticals.dc2_s.api_routes import _sync_journey_phase
        from models import Account
        acct = _db.session.get(Account, 201)
        _sync_journey_phase(acct)
        assert acct.journey_phase == 'deployment'

    def test_phase_performance(self, app_ctx):
        _, db_inst = app_ctx
        _seed_dc2s_account(db_inst, customer_id=3, account_id=202, deployment_days_ago=150)
        db_inst.session.commit()

        from verticals.dc2_s.api_routes import _sync_journey_phase
        from models import Account
        acct = _db.session.get(Account, 202)
        _sync_journey_phase(acct)
        assert acct.journey_phase == 'performance'

    def test_phase_excellence(self, app_ctx):
        _, db_inst = app_ctx
        _seed_dc2s_account(db_inst, customer_id=4, account_id=203, deployment_days_ago=400)
        db_inst.session.commit()

        from verticals.dc2_s.api_routes import _sync_journey_phase
        from models import Account
        acct = _db.session.get(Account, 203)
        _sync_journey_phase(acct)
        assert acct.journey_phase == 'excellence'

    def test_phase_no_metadata(self, app_ctx):
        _, db_inst = app_ctx
        from models import Customer, Account
        cust = _db.session.get(Customer, 5)
        if not cust:
            cust = Customer(customer_id=5, customer_name='No Meta', email='nometa@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()
        acct = Account(account_id=204, customer_id=5, account_name='No Meta Account', vertical='dc2_s')
        db_inst.session.add(acct)
        db_inst.session.commit()

        from verticals.dc2_s.api_routes import _sync_journey_phase
        _sync_journey_phase(acct)
        assert acct.journey_phase == 'deployment'


# ============================================================
# Phase 0.3: Recommendations use real trigger logic
# ============================================================

class TestPhase0_3_RealRecommendations:
    def test_recommendations_endpoint_uses_playbook_config(self, app_ctx):
        app, db_inst = app_ctx
        _seed_dc2s_account(db_inst, customer_id=6, account_id=301, deployment_days_ago=30)
        _seed_kpis(db_inst, 301, {
            'P1-KPI1': 25,    # > 20 → triggers PB-01
            'P1-KPI4': 40,    # > 35 → triggers PB-01
            'P1-KPI2': 85,
            'P1-KPI3': 90,
        })
        db_inst.session.commit()

        with app.test_client() as client:
            resp = client.get('/api/dc2s/recommendations/301',
                              headers={'X-Customer-ID': '6'})
            assert resp.status_code == 200
            data = resp.get_json()
            pb_ids = [r['playbook_id'] for r in data['recommendations']]
            assert 'PB-01' in pb_ids, f"Expected PB-01 in {pb_ids}"
            for r in data['recommendations']:
                assert r['playbook_id'].startswith('PB-'), \
                    f"Got non-standard playbook ID: {r['playbook_id']}"

    def test_recommendations_include_phase(self, app_ctx):
        app, db_inst = app_ctx
        _seed_dc2s_account(db_inst, customer_id=7, account_id=302, deployment_days_ago=150)
        _seed_kpis(db_inst, 302, {
            'P2-KPI1': 4.0,    # RMA > 2.6 → triggers PB-02
            'P2-KPI2': 3000,   # MTBF < 4380 → triggers PB-02
        })
        db_inst.session.commit()

        with app.test_client() as client:
            resp = client.get('/api/dc2s/recommendations/302',
                              headers={'X-Customer-ID': '7'})
            assert resp.status_code == 200
            data = resp.get_json()
            assert 'journey_phase' in data
            assert 'overall_health' in data
            assert data['journey_phase'] in ('deployment', 'performance', 'excellence')


# ============================================================
# Phase 1: New tables + model extensions
# ============================================================

class TestPhase1_NewTables:
    def test_customer_action_binding_crud(self, app_ctx):
        _, db_inst = app_ctx
        from models_action_interface import CustomerActionBinding
        from models import Customer

        cust = _db.session.get(Customer, 10)
        if not cust:
            cust = Customer(customer_id=10, customer_name='Binding Test', email='binding@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()

        binding = CustomerActionBinding(
            customer_id=10, action_name='create_task', provider='jira',
            config={'project_key': 'CS', 'issue_type': 'Task'}, enabled=True,
        )
        db_inst.session.add(binding)
        db_inst.session.flush()
        assert binding.id is not None
        assert binding.to_dict()['action_name'] == 'create_task'

    def test_integration_credential(self, app_ctx):
        _, db_inst = app_ctx
        from models_action_interface import IntegrationCredential

        cred = IntegrationCredential(
            customer_id=10, provider='slack', credential_type='bot_token',
            encrypted_data=b'fake-encrypted-data',
        )
        db_inst.session.add(cred)
        db_inst.session.flush()
        assert cred.id is not None

    def test_playbook_step_log(self, app_ctx):
        _, db_inst = app_ctx
        from models_action_interface import PlaybookStepLog
        from models import PlaybookExecution, Customer

        cust = _db.session.get(Customer, 11)
        if not cust:
            cust = Customer(customer_id=11, customer_name='StepLog Test', email='steplog@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()

        exec_id = str(uuid.uuid4())
        execution = PlaybookExecution(
            execution_id=exec_id, customer_id=11, playbook_id='PB-02',
            status='in-progress', execution_data={}, started_at=datetime.utcnow(),
        )
        db_inst.session.add(execution)
        db_inst.session.flush()

        step = PlaybookStepLog(
            execution_id=exec_id, step_index=0, action_name='send_alert',
            provider='slack', status='success', duration_ms=150,
        )
        db_inst.session.add(step)
        db_inst.session.flush()
        assert step.to_dict()['step_index'] == 0

    def test_crm_field_mapping(self, app_ctx):
        _, db_inst = app_ctx
        from models_action_interface import CRMFieldMapping
        mapping = CRMFieldMapping(
            customer_id=10, cs_pulse_field='health_score',
            crm_object='Account', crm_field='Health_Score__c',
            transform='scale_100_to_10',
        )
        db_inst.session.add(mapping)
        db_inst.session.flush()
        assert mapping.id is not None

    def test_customer_contact(self, app_ctx):
        _, db_inst = app_ctx
        from models_action_interface import CustomerContact
        contact = CustomerContact(
            customer_id=10, role='champion', name='Jane Doe',
            email='jane@example.com', title='VP Engineering',
        )
        db_inst.session.add(contact)
        db_inst.session.flush()
        d = contact.to_dict()
        assert d['role'] == 'champion'
        assert d['email'] == 'jane@example.com'


class TestPhase1_ModelExtensions:
    def test_playbook_trigger_new_columns(self, app_ctx):
        _, db_inst = app_ctx
        from models import PlaybookTrigger, Customer

        cust = _db.session.get(Customer, 12)
        if not cust:
            cust = Customer(customer_id=12, customer_name='Trigger Ext', email='trigext@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()

        trigger = PlaybookTrigger(
            customer_id=12, playbook_type='expansion',
            playbook_id='PB-04',
            trigger_conditions={'P5-KPI1': {'operator': '>', 'value': 80}},
            execution_mode='workflow', requires_llm_validation=True,
        )
        db_inst.session.add(trigger)
        db_inst.session.flush()
        assert trigger.playbook_id == 'PB-04'
        assert trigger.requires_llm_validation is True

    def test_playbook_execution_new_columns(self, app_ctx):
        _, db_inst = app_ctx
        from models import PlaybookExecution, Customer

        cust = _db.session.get(Customer, 13)
        if not cust:
            cust = Customer(customer_id=13, customer_name='Exec Ext', email='execext@test.com')
            db_inst.session.add(cust)
            db_inst.session.flush()

        execution = PlaybookExecution(
            execution_id=str(uuid.uuid4()), customer_id=13, playbook_id='PB-02',
            status='completed', execution_data={}, started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(), execution_mode='mcp_direct',
            trigger_context={'P2-KPI1': {'value': 3.5, 'threshold': 2.6}},
            outcome='resolved', outcome_notes='RMA rate reduced after firmware update',
            llm_validation_result={'approved': True, 'confidence': 0.92},
        )
        db_inst.session.add(execution)
        db_inst.session.flush()
        assert execution.outcome == 'resolved'
        assert execution.llm_validation_result['confidence'] == 0.92


# ============================================================
# Phase 2: TriggerValidationResult + PlaybookTriggerValidator
# ============================================================

class TestPhase2_TriggerValidationResult:
    def test_model_auto_approved(self, app_ctx):
        import importlib; _am = importlib.import_module('agents.models'); TriggerValidationResult = _am.TriggerValidationResult; TriggerValidationDecision = _am.TriggerValidationDecision
        result = TriggerValidationResult(
            approved=True, confidence=0.92,
            reasoning='Strong alignment between KPIs and qualitative signals.',
            decision=TriggerValidationDecision.AUTO_APPROVED,
        )
        assert result.approved is True
        assert result.decision == 'auto_approved'

    def test_model_auto_rejected(self, app_ctx):
        import importlib; _am = importlib.import_module('agents.models'); TriggerValidationResult = _am.TriggerValidationResult; TriggerValidationDecision = _am.TriggerValidationDecision
        result = TriggerValidationResult(
            approved=False, confidence=0.25,
            reasoning='KPI breach is transient, no qualitative confirmation.',
            decision=TriggerValidationDecision.AUTO_REJECTED,
        )
        assert result.approved is False
        assert result.confidence < 0.4

    def test_model_pending_approval(self, app_ctx):
        import importlib; _am = importlib.import_module('agents.models'); TriggerValidationResult = _am.TriggerValidationResult; TriggerValidationDecision = _am.TriggerValidationDecision
        result = TriggerValidationResult(
            approved=False, confidence=0.55,
            reasoning='Mixed signals.',
            decision=TriggerValidationDecision.PENDING_MANUAL_APPROVAL,
        )
        assert result.decision == 'pending_manual_approval'


class TestPhase2_PlaybookTriggerValidator:
    def test_threshold_auto_approve(self, app_ctx):
        from playbook_trigger_validator import PlaybookTriggerValidator
        decision, approved = PlaybookTriggerValidator._apply_thresholds(0.9)
        assert approved is True
        assert decision == 'auto_approved'

    def test_threshold_auto_reject(self, app_ctx):
        from playbook_trigger_validator import PlaybookTriggerValidator
        decision, approved = PlaybookTriggerValidator._apply_thresholds(0.2)
        assert approved is False
        assert decision == 'auto_rejected'

    def test_threshold_pending(self, app_ctx):
        from playbook_trigger_validator import PlaybookTriggerValidator
        decision, approved = PlaybookTriggerValidator._apply_thresholds(0.6)
        assert approved is False
        assert decision == 'pending_manual_approval'

    def test_fallback_rule_based_critical(self, app_ctx):
        from playbook_trigger_validator import PlaybookTriggerValidator
        validator = PlaybookTriggerValidator(openai_api_key='fake-key')
        result = validator._fallback_rule_based(
            playbook_id='PB-02',
            trigger_context={'P2-KPI1': {'value': 4.0}, 'P2-KPI2': {'value': 3000}},
            health_score=40.0,
        )
        assert result.approved is True
        assert result.confidence >= 0.8

    def test_fallback_rule_based_moderate(self, app_ctx):
        from playbook_trigger_validator import PlaybookTriggerValidator
        validator = PlaybookTriggerValidator(openai_api_key='fake-key')
        result = validator._fallback_rule_based(
            playbook_id='PB-03',
            trigger_context={'P3-KPI1': {'value': 55}},
            health_score=65.0,
        )
        assert result.decision == 'pending_manual_approval'

    def test_cache_hit(self, app_ctx):
        from playbook_trigger_validator import _set_cached, _get_cached
        import importlib; _am = importlib.import_module('agents.models'); TriggerValidationResult = _am.TriggerValidationResult; TriggerValidationDecision = _am.TriggerValidationDecision

        cached_result = TriggerValidationResult(
            approved=True, confidence=0.88,
            reasoning='Cached result.',
            decision=TriggerValidationDecision.AUTO_APPROVED,
        )
        _set_cached('999', 'PB-02', cached_result)
        hit = _get_cached('999', 'PB-02')
        assert hit is not None
        assert hit.confidence == 0.88


# ============================================================
# Integration: determine_customer_phase utility
# ============================================================

class TestDetermineCustomerPhase:
    def test_explicit_phase(self, app_ctx):
        from verticals.dc2_s.vertical_config import determine_customer_phase
        assert determine_customer_phase({'phase': 'excellence'}) == 'excellence'

    def test_inferred_deployment(self, app_ctx):
        from verticals.dc2_s.vertical_config import determine_customer_phase
        assert determine_customer_phase({'days_since_deployment': 45}) == 'deployment'

    def test_inferred_performance(self, app_ctx):
        from verticals.dc2_s.vertical_config import determine_customer_phase
        assert determine_customer_phase({'days_since_deployment': 180}) == 'performance'

    def test_inferred_excellence(self, app_ctx):
        from verticals.dc2_s.vertical_config import determine_customer_phase
        assert determine_customer_phase({'days_since_deployment': 300}) == 'excellence'
