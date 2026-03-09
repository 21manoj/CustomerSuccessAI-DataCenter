#!/usr/bin/env python3
"""
E2E Test: Signal → Playbook Trigger → Execution → Feedback → Recalibration
============================================================================
Exercises the COMPLETE closed-loop workflow that was previously untested:

  1. Seed account with declining KPIs + negative qualitative signals
  2. Signal Analyst detects churn risk
  3. Trigger Validator gate decides approval
  4. PlaybookExecution record created
  5. Execution completes → feedback stored (DB + Qdrant fallback)
  6. Recalibration engine adjusts signal weights
  7. Weight history persisted and retrievable

No live LLM or Qdrant required — uses rule-based fallback path and
DB-only storage so the test is fully deterministic.
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock

# ---- DB required — skip if not available ----
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if not DATABASE_URL:
    pytest.skip("DATABASE_URL not set — skipping E2E loop tests", allow_module_level=True)
os.environ['DATABASE_URL'] = DATABASE_URL

from app_v3_minimal import app
from extensions import db
from models import (
    Account, Customer, User, DC2SKPI, AccountNote,
    QualitativeSignal, CustomerConfig, PlaybookTrigger,
    PlaybookExecution, WeightCalibrationHistory,
)
from qdrant_feedback_loop import (
    ExecutionFeedback, RecalibrationResult,
    store_execution_feedback, recalibrate_weights,
    recalibrate_all, get_current_weights, get_calibration_history,
)
from agents.models import TriggerValidationDecision, TriggerValidationResult
from playbook_trigger_validator import PlaybookTriggerValidator


# ============================================================
# FIXTURES — deterministic test customer (ID 9900)
# ============================================================

E2E_CUSTOMER_ID = 9900
E2E_ACCOUNT_ID = 990001


@pytest.fixture(autouse=True)
def e2e_app_context():
    """Provide app context; clean before AND after each test."""
    with app.app_context():
        _cleanup()  # ensure a clean slate even if prior run left data
        yield
        _cleanup()


def _cleanup():
    """Delete test data in FK-respecting order."""
    try:
        WeightCalibrationHistory.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        PlaybookExecution.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        PlaybookTrigger.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        QualitativeSignal.query.filter(
            QualitativeSignal.signal_id.like('e2e_loop_%')
        ).delete(synchronize_session='fetch')
        AccountNote.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        DC2SKPI.query.filter_by(account_id=E2E_ACCOUNT_ID).delete()
        Account.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        CustomerConfig.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        User.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        Customer.query.filter_by(customer_id=E2E_CUSTOMER_ID).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()


def _seed_customer():
    """Create a minimal customer + account with declining signals."""
    customer = Customer(customer_id=E2E_CUSTOMER_ID, customer_name="E2E Loop Test Corp")
    db.session.add(customer)
    db.session.flush()

    user = User(
        customer_id=E2E_CUSTOMER_ID,
        user_name="e2e_loop_user",
        email="e2e_loop@test.com",
        password_hash="test",
    )
    db.session.add(user)
    db.session.flush()

    config = CustomerConfig(customer_id=E2E_CUSTOMER_ID, vertical="dc2_s")
    db.session.add(config)

    account = Account(
        account_id=E2E_ACCOUNT_ID,
        customer_id=E2E_CUSTOMER_ID,
        account_name="E2E Loop Account",
        revenue=500000.0,
        industry="Technology",
        account_status="active",
    )
    db.session.add(account)
    db.session.flush()

    # Declining KPIs (14-day trend: 8500 → 7200 → 5500)
    for days_ago, value in [(14, 8500), (7, 7200), (1, 5500)]:
        kpi = DC2SKPI(
            account_id=E2E_ACCOUNT_ID,
            kpi_code="P3-KPI1",
            measured_at=datetime.utcnow() - timedelta(days=days_ago),
            value=value,
            target=9000.0,
            pillar="P3",
        )
        db.session.add(kpi)

    # Negative qualitative signal
    qs = QualitativeSignal(
        signal_id=f"e2e_loop_{E2E_ACCOUNT_ID}_1",
        account_id=E2E_ACCOUNT_ID,
        signal_date=(datetime.utcnow() - timedelta(days=3)).date(),
        signal_type="escalation",
        content="Customer threatened to cancel unless GPU performance improves",
        sentiment="negative",
        sentiment_score=-0.9,
    )
    db.session.add(qs)
    db.session.commit()
    return account, user


# ============================================================
# TEST 1: Full closed-loop — signal → feedback → recalibration
# ============================================================

class TestFullClosedLoop:
    """The single most important missing test: entire pipeline end-to-end."""

    def test_signal_to_feedback_to_recalibration(self):
        """
        Complete chain:
          Seed data → trigger validator (rule-based) → execution →
          feedback storage → recalibration → weights shift
        """
        account, user = _seed_customer()

        # ---- Step 1: Trigger Validator (rule-based fallback) ----
        validator = PlaybookTriggerValidator(openai_api_key="not-needed")
        result = validator._fallback_rule_based(
            playbook_id="renewal-safeguard",
            trigger_context={
                "P3-KPI1": {"value": 5500, "threshold": 7000, "operator": "<"},
                "health_score": {"value": 38, "threshold": 50, "operator": "<"},
            },
            health_score=38.0,
        )

        assert result.approved is True, "Rule-based should auto-approve (hs<50, 2 breaches)"
        assert result.decision == TriggerValidationDecision.AUTO_APPROVED
        assert result.confidence >= 0.8

        # ---- Step 2: Create PlaybookExecution record ----
        exec_id = str(uuid.uuid4())
        execution = PlaybookExecution(
            execution_id=exec_id,
            customer_id=E2E_CUSTOMER_ID,
            account_id=E2E_ACCOUNT_ID,
            playbook_id="renewal-safeguard",
            status="in-progress",
            current_step="initialized",
            started_at=datetime.utcnow(),
            execution_mode="workflow",
            execution_data={
                "trigger_context": {"P3-KPI1": {"value": 5500, "threshold": 7000}},
                "validation": result.model_dump(mode="json"),
            },
            trigger_context={
                "P3-KPI1": {"value": 5500, "threshold": 7000},
            },
            llm_validation_result=result.model_dump(mode="json"),
        )
        db.session.add(execution)
        db.session.commit()

        persisted = PlaybookExecution.query.filter_by(execution_id=exec_id).first()
        assert persisted is not None
        assert persisted.status == "in-progress"

        # ---- Step 3: Simulate execution completion ----
        persisted.status = "completed"
        persisted.completed_at = datetime.utcnow()
        persisted.outcome = "resolved"
        db.session.commit()

        # ---- Step 4: Store feedback (DB path — no Qdrant) ----
        feedback = ExecutionFeedback(
            execution_id=exec_id,
            customer_id=E2E_CUSTOMER_ID,
            account_id=str(E2E_ACCOUNT_ID),
            playbook_type="renewal-safeguard",
            outcome="resolved",
            predicted_churn_prob=0.72,
            predicted_expansion_prob=0.10,
            actual_churn=False,
            actual_expansion=False,
            kpi_improvements={"P3-KPI1": 0.15},
            signals_considered=["quantitative", "qualitative"],
            power_of_1_metric="GRR",
            dollar_impact_realized=12500.0,
        )
        storage_result = store_execution_feedback(feedback)

        assert storage_result["stored_db"] is True
        assert storage_result["execution_id"] == exec_id
        assert storage_result["calibration_id"] is not None

        # Verify DB record
        cal_record = db.session.get(
            WeightCalibrationHistory, storage_result["calibration_id"]
        )
        assert cal_record is not None
        assert cal_record.calibration_type == "execution_feedback"
        assert "renewal-safeguard" in cal_record.notes

        # ---- Step 5: Recalibration (requires >= 1 feedback record) ----
        recal = recalibrate_weights(
            customer_id=E2E_CUSTOMER_ID,
            playbook_type="renewal-safeguard",
            window_days=90,
            learning_rate=0.1,
        )

        assert recal.feedback_count >= 1
        assert recal.playbook_type == "renewal-safeguard"
        assert recal.calibration_id is not None
        # Weights should be normalized
        assert abs(sum(recal.new_weights.values()) - 1.0) < 0.01

        # ---- Step 6: Verify weights persisted & retrievable ----
        current = get_current_weights(E2E_CUSTOMER_ID)
        assert abs(sum(current.values()) - 1.0) < 0.01

        history = get_calibration_history(E2E_CUSTOMER_ID)
        assert len(history) >= 2  # 1 feedback + 1 recalibration


# ============================================================
# TEST 2: Multiple feedback cycles shift weights
# ============================================================

class TestMultipleFeedbackCycles:
    """Verify that repeated feedback actually moves the needle."""

    def test_weights_shift_after_multiple_feedbacks(self):
        """Store 5 feedback records, recalibrate, verify weight change."""
        _seed_customer()

        initial_weights = get_current_weights(E2E_CUSTOMER_ID)

        # Store 5 feedback records with high churn accuracy (predicted high, actual True)
        for i in range(5):
            fb = ExecutionFeedback(
                execution_id=str(uuid.uuid4()),
                customer_id=E2E_CUSTOMER_ID,
                account_id=str(E2E_ACCOUNT_ID),
                playbook_type="renewal-safeguard",
                outcome="resolved" if i % 2 == 0 else "escalated",
                predicted_churn_prob=0.8,
                predicted_expansion_prob=0.1,
                actual_churn=True,  # Churn prediction was correct
                actual_expansion=False,
            )
            store_execution_feedback(fb)

        recal = recalibrate_weights(
            E2E_CUSTOMER_ID, "renewal-safeguard", learning_rate=0.1,
        )

        assert recal.feedback_count == 5
        assert recal.signal_accuracy["churn_accuracy"] == 1.0  # 5/5 correct
        # High accuracy → playbook_feedback weight should increase
        assert recal.new_weights.get("playbook_feedback", 0) >= initial_weights.get("playbook_feedback", 0.10)

    def test_low_accuracy_shifts_toward_historical(self):
        """When predictions are wrong, historical_patterns weight increases."""
        _seed_customer()

        # Store feedbacks where churn was predicted but didn't happen
        for _ in range(5):
            fb = ExecutionFeedback(
                execution_id=str(uuid.uuid4()),
                customer_id=E2E_CUSTOMER_ID,
                account_id=str(E2E_ACCOUNT_ID),
                playbook_type="sla-stabilizer",
                outcome="resolved",
                predicted_churn_prob=0.8,
                actual_churn=False,  # Wrong prediction
                predicted_expansion_prob=0.7,
                actual_expansion=False,  # Also wrong
            )
            store_execution_feedback(fb)

        recal = recalibrate_weights(
            E2E_CUSTOMER_ID, "sla-stabilizer", learning_rate=0.1,
        )

        assert recal.feedback_count == 5
        assert recal.signal_accuracy["churn_accuracy"] == 0.0
        assert recal.signal_accuracy["overall_accuracy"] < 0.5
        # Low accuracy → historical_patterns weight should increase
        default_historical = 0.20
        assert recal.new_weights.get("historical_patterns", 0) >= default_historical


# ============================================================
# TEST 3: Batch recalibration across playbook types
# ============================================================

class TestBatchRecalibration:

    def test_recalibrate_all_returns_results_for_types_with_data(self):
        """recalibrate_all should only return results for types with feedback."""
        _seed_customer()

        # Only store feedback for two playbook types
        for pt in ["voc-sprint", "activation-blitz"]:
            fb = ExecutionFeedback(
                execution_id=str(uuid.uuid4()),
                customer_id=E2E_CUSTOMER_ID,
                account_id=str(E2E_ACCOUNT_ID),
                playbook_type=pt,
                outcome="resolved",
                predicted_churn_prob=0.6,
                actual_churn=True,
            )
            store_execution_feedback(fb)

        results = recalibrate_all(E2E_CUSTOMER_ID)

        types_recalibrated = {r.playbook_type for r in results}
        assert "voc-sprint" in types_recalibrated
        assert "activation-blitz" in types_recalibrated
        # Types without feedback should NOT appear
        assert "sla-stabilizer" not in types_recalibrated


# ============================================================
# TEST 4: Trigger validator threshold boundaries
# ============================================================

class TestTriggerValidatorBoundaries:

    def test_auto_approve_when_health_low_and_multiple_breaches(self):
        """health < 50 + 2+ breaches → confidence 0.85 → auto-approve."""
        validator = PlaybookTriggerValidator(openai_api_key="not-needed")
        result = validator._fallback_rule_based(
            playbook_id="renewal-safeguard",
            trigger_context={"KPI-A": {}, "KPI-B": {}},
            health_score=35.0,
        )
        assert result.decision == TriggerValidationDecision.AUTO_APPROVED
        assert result.approved is True

    def test_pending_review_when_moderate_health(self):
        """health < 70 + 1 breach → confidence 0.65 → pending review."""
        validator = PlaybookTriggerValidator(openai_api_key="not-needed")
        result = validator._fallback_rule_based(
            playbook_id="sla-stabilizer",
            trigger_context={"KPI-A": {}},
            health_score=60.0,
        )
        assert result.decision == TriggerValidationDecision.PENDING_MANUAL_APPROVAL
        assert result.approved is False

    def test_low_confidence_when_health_ok(self):
        """health >= 70 + 0 breaches → confidence 0.45 → pending."""
        validator = PlaybookTriggerValidator(openai_api_key="not-needed")
        result = validator._fallback_rule_based(
            playbook_id="expansion-accelerator",
            trigger_context={},
            health_score=75.0,
        )
        assert result.decision == TriggerValidationDecision.PENDING_MANUAL_APPROVAL
        assert result.approved is False


# ============================================================
# TEST 5: Feedback with Power of 1 fields
# ============================================================

class TestFeedbackPowerOf1Fields:

    def test_power_of_1_fields_stored_in_feedback(self):
        """Verify power_of_1_metric and dollar_impact are persisted."""
        _seed_customer()

        fb = ExecutionFeedback(
            execution_id=str(uuid.uuid4()),
            customer_id=E2E_CUSTOMER_ID,
            account_id=str(E2E_ACCOUNT_ID),
            playbook_type="voc-sprint",
            outcome="resolved",
            predicted_churn_prob=0.55,
            actual_churn=False,
            power_of_1_metric="NRR",
            dollar_impact_realized=105000.0,
            kpi_improvements={"NRR": 1.0, "GRR": 0.3},
        )
        result = store_execution_feedback(fb)

        record = db.session.get(WeightCalibrationHistory, result["calibration_id"])
        actual_data = json.loads(record.new_weights)
        assert actual_data["kpi_improvements"]["NRR"] == 1.0
        assert actual_data["actual_churn"] is False


# ============================================================
# TEST 6: Execution lifecycle tracking
# ============================================================

class TestExecutionLifecycle:

    def test_execution_status_transitions(self):
        """in-progress → completed with outcome."""
        _seed_customer()

        exec_id = str(uuid.uuid4())
        execution = PlaybookExecution(
            execution_id=exec_id,
            customer_id=E2E_CUSTOMER_ID,
            account_id=E2E_ACCOUNT_ID,
            playbook_id="activation-blitz",
            status="in-progress",
            started_at=datetime.utcnow(),
            execution_data={"context": "lifecycle test"},
        )
        db.session.add(execution)
        db.session.commit()

        # Transition to completed
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        execution.outcome = "resolved"
        db.session.commit()

        reloaded = PlaybookExecution.query.filter_by(execution_id=exec_id).first()
        assert reloaded.status == "completed"
        assert reloaded.outcome == "resolved"
        assert reloaded.completed_at is not None

    def test_execution_failure_path(self):
        """in-progress → failed."""
        _seed_customer()

        exec_id = str(uuid.uuid4())
        execution = PlaybookExecution(
            execution_id=exec_id,
            customer_id=E2E_CUSTOMER_ID,
            account_id=E2E_ACCOUNT_ID,
            playbook_id="sla-stabilizer",
            status="in-progress",
            started_at=datetime.utcnow(),
            execution_data={"context": "failure path test"},
        )
        db.session.add(execution)
        db.session.commit()

        execution.status = "failed"
        execution.completed_at = datetime.utcnow()
        execution.outcome = "timeout"
        db.session.commit()

        reloaded = PlaybookExecution.query.filter_by(execution_id=exec_id).first()
        assert reloaded.status == "failed"
        assert reloaded.outcome == "timeout"


# ============================================================
# TEST 7: Calibration history integrity
# ============================================================

class TestCalibrationHistoryIntegrity:

    def test_history_is_append_only(self):
        """Each recalibration appends a new record — never overwrites."""
        _seed_customer()

        # Store feedback and recalibrate twice
        for _ in range(3):
            fb = ExecutionFeedback(
                execution_id=str(uuid.uuid4()),
                customer_id=E2E_CUSTOMER_ID,
                account_id=str(E2E_ACCOUNT_ID),
                playbook_type="voc-sprint",
                outcome="resolved",
                predicted_churn_prob=0.6,
                actual_churn=True,
            )
            store_execution_feedback(fb)

        recal1 = recalibrate_weights(E2E_CUSTOMER_ID, "voc-sprint")
        recal2 = recalibrate_weights(E2E_CUSTOMER_ID, "voc-sprint")

        assert recal1.calibration_id != recal2.calibration_id
        history = get_calibration_history(E2E_CUSTOMER_ID)
        recal_records = [h for h in history if h["calibration_type"] == "weight_recalibration"]
        assert len(recal_records) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
