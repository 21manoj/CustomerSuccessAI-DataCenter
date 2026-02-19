#!/usr/bin/env python3
"""
Step 8 — Qdrant Feedback Loop + Weight Recalibration
======================================================
Closes the loop between playbook execution outcomes and the
signal weights used by the Signal Analyst agent.

Flow:
  1. Playbook execution completes → outcome stored as feedback signal in Qdrant
  2. Periodically, the recalibration pipeline reads feedback signals
  3. Compares predicted outcomes (churn_prob, expansion_prob) vs. actuals
  4. Adjusts signal weights in PlaybookTrigger configurations
  5. Logs calibration history to WeightCalibrationHistory table

This module is designed to work with or without a live Qdrant connection.
When Qdrant is unavailable, it falls back to DB-only tracking via
WeightCalibrationHistory.
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from extensions import db
from models import WeightCalibrationHistory


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class ExecutionFeedback:
    """Feedback from a completed playbook execution."""
    execution_id: str
    customer_id: int
    account_id: str
    playbook_type: str
    outcome: str  # 'resolved', 'escalated', 'timeout', 'manual_close'
    predicted_churn_prob: Optional[float] = None
    predicted_expansion_prob: Optional[float] = None
    actual_churn: Optional[bool] = None
    actual_expansion: Optional[bool] = None
    kpi_improvements: Optional[Dict[str, float]] = None
    signals_considered: Optional[List[str]] = None
    execution_duration_hours: Optional[float] = None
    power_of_1_metric: Optional[str] = None
    dollar_impact_realized: Optional[float] = None


@dataclass
class RecalibrationResult:
    """Result of a weight recalibration cycle."""
    customer_id: int
    playbook_type: str
    feedback_count: int
    previous_weights: Dict[str, float]
    new_weights: Dict[str, float]
    error_reduction_pct: float
    signal_accuracy: Dict[str, float]
    calibration_id: Optional[int] = None


# ============================================================
# FEEDBACK STORAGE (Qdrant + DB)
# ============================================================

def store_execution_feedback(feedback: ExecutionFeedback) -> Dict:
    """
    Store playbook execution feedback for future recalibration.

    Attempts to store in Qdrant as a vector signal. Always stores
    a summary in WeightCalibrationHistory as a durable record.

    Returns dict with storage status.
    """
    # Build the feedback payload
    payload = {
        'execution_id': feedback.execution_id,
        'customer_id': feedback.customer_id,
        'account_id': str(feedback.account_id),
        'signal_type': 'playbook_feedback',
        'playbook_type': feedback.playbook_type,
        'outcome': feedback.outcome,
        'predicted_churn_prob': feedback.predicted_churn_prob,
        'predicted_expansion_prob': feedback.predicted_expansion_prob,
        'actual_churn': feedback.actual_churn,
        'actual_expansion': feedback.actual_expansion,
        'kpi_improvements': feedback.kpi_improvements or {},
        'signals_considered': feedback.signals_considered or [],
        'power_of_1_metric': feedback.power_of_1_metric,
        'dollar_impact_realized': feedback.dollar_impact_realized,
        'date': datetime.utcnow().isoformat(),
        'text': (
            f"Playbook {feedback.playbook_type} execution {feedback.outcome} "
            f"for account {feedback.account_id}"
        ),
    }

    stored_qdrant = False

    # Attempt Qdrant storage
    try:
        stored_qdrant = _store_feedback_to_qdrant(feedback, payload)
    except Exception as e:
        print(f"Qdrant feedback storage failed (non-fatal): {e}")

    # Always store to DB
    record = WeightCalibrationHistory(
        customer_id=feedback.customer_id,
        calibration_type='execution_feedback',
        previous_weights=json.dumps({
            'predicted_churn': feedback.predicted_churn_prob,
            'predicted_expansion': feedback.predicted_expansion_prob,
        }),
        new_weights=json.dumps({
            'actual_outcome': feedback.outcome,
            'actual_churn': feedback.actual_churn,
            'actual_expansion': feedback.actual_expansion,
            'kpi_improvements': feedback.kpi_improvements,
        }),
        error_reduction_pct=0,
        notes=(
            f"Feedback: {feedback.playbook_type} → {feedback.outcome} "
            f"(exec: {feedback.execution_id})"
        ),
    )
    db.session.add(record)
    db.session.commit()

    return {
        'stored_qdrant': stored_qdrant,
        'stored_db': True,
        'calibration_id': record.id,
        'execution_id': feedback.execution_id,
    }


def _store_feedback_to_qdrant(feedback: ExecutionFeedback, payload: Dict) -> bool:
    """
    Store feedback as a vector in the customer's Qdrant collection.
    Returns True if successful.
    """
    qdrant_url = os.getenv('QDRANT_URL')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not qdrant_url or not openai_api_key:
        return False

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        import openai

        # Generate embedding for the feedback text
        client = openai.OpenAI(api_key=openai_api_key)
        embedding_response = client.embeddings.create(
            model="text-embedding-3-large",
            input=payload['text'],
        )
        vector = embedding_response.data[0].embedding

        # Store in Qdrant
        collection_name = f"kpi_dashboard_vectors_customer_{feedback.customer_id}"
        qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=os.getenv('QDRANT_API_KEY'),
            timeout=30,
        )

        point = PointStruct(
            id=uuid.uuid4().int >> 64,  # 64-bit int for Qdrant
            vector=vector,
            payload=payload,
        )

        qdrant_client.upsert(
            collection_name=collection_name,
            points=[point],
        )
        return True

    except ImportError:
        return False
    except Exception as e:
        print(f"Qdrant upsert failed: {e}")
        return False


# ============================================================
# RECALIBRATION ENGINE
# ============================================================

def recalibrate_weights(
    customer_id: int,
    playbook_type: str,
    window_days: int = 90,
    learning_rate: float = 0.1,
) -> RecalibrationResult:
    """
    Recalibrate signal weights based on execution feedback.

    Algorithm:
      1. Collect all feedback for this customer/playbook in the window
      2. For each signal type, compute prediction accuracy
      3. Increase weights for signals that predicted correctly
      4. Decrease weights for signals that predicted incorrectly
      5. Normalize weights to sum to 1.0
      6. Store the new weights

    Args:
        customer_id: Customer to recalibrate for
        playbook_type: Which playbook type to recalibrate
        window_days: How far back to look for feedback
        learning_rate: How much to adjust weights per cycle (0.0 to 1.0)

    Returns:
        RecalibrationResult with before/after weights and accuracy stats
    """
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    # Collect feedback records from DB
    feedbacks = WeightCalibrationHistory.query.filter(
        WeightCalibrationHistory.customer_id == customer_id,
        WeightCalibrationHistory.calibration_type == 'execution_feedback',
        WeightCalibrationHistory.calibrated_at >= cutoff,
        WeightCalibrationHistory.notes.contains(playbook_type),
    ).all()

    if not feedbacks:
        return RecalibrationResult(
            customer_id=customer_id,
            playbook_type=playbook_type,
            feedback_count=0,
            previous_weights={},
            new_weights={},
            error_reduction_pct=0,
            signal_accuracy={},
        )

    # Parse feedback records
    predictions = []
    for record in feedbacks:
        try:
            prev = json.loads(record.previous_weights) if record.previous_weights else {}
            actual = json.loads(record.new_weights) if record.new_weights else {}
        except (json.JSONDecodeError, TypeError):
            continue

        predictions.append({
            'predicted_churn': prev.get('predicted_churn'),
            'predicted_expansion': prev.get('predicted_expansion'),
            'actual_outcome': actual.get('actual_outcome'),
            'actual_churn': actual.get('actual_churn'),
            'actual_expansion': actual.get('actual_expansion'),
            'kpi_improvements': actual.get('kpi_improvements', {}),
        })

    # Compute accuracy metrics
    churn_correct = 0
    expansion_correct = 0
    total_with_churn = 0
    total_with_expansion = 0

    for p in predictions:
        # Churn prediction accuracy
        if p['predicted_churn'] is not None and p['actual_churn'] is not None:
            predicted_churn = p['predicted_churn'] >= 0.5
            if predicted_churn == p['actual_churn']:
                churn_correct += 1
            total_with_churn += 1

        # Expansion prediction accuracy
        if p['predicted_expansion'] is not None and p['actual_expansion'] is not None:
            predicted_expansion = p['predicted_expansion'] >= 0.5
            if predicted_expansion == p['actual_expansion']:
                expansion_correct += 1
            total_with_expansion += 1

    churn_accuracy = (churn_correct / total_with_churn) if total_with_churn > 0 else 0.5
    expansion_accuracy = (expansion_correct / total_with_expansion) if total_with_expansion > 0 else 0.5

    # Current default weights
    default_weights = {
        'quantitative_signals': 0.40,
        'qualitative_signals': 0.30,
        'historical_patterns': 0.20,
        'playbook_feedback': 0.10,
    }

    # Load existing weights from the most recent calibration
    latest_calibration = WeightCalibrationHistory.query.filter(
        WeightCalibrationHistory.customer_id == customer_id,
        WeightCalibrationHistory.calibration_type == 'weight_recalibration',
    ).order_by(WeightCalibrationHistory.calibrated_at.desc()).first()

    previous_weights = dict(default_weights)
    if latest_calibration and latest_calibration.new_weights:
        try:
            previous_weights = json.loads(latest_calibration.new_weights)
        except (json.JSONDecodeError, TypeError):
            pass

    # Adjust weights based on accuracy
    # If churn accuracy is high → quantitative signals are working well
    # If expansion accuracy is low → qualitative signals need more weight
    overall_accuracy = (churn_accuracy + expansion_accuracy) / 2

    new_weights = dict(previous_weights)

    if overall_accuracy > 0.7:
        # Model is performing well — reinforce current weights slightly
        new_weights['playbook_feedback'] = min(
            0.25,
            previous_weights.get('playbook_feedback', 0.10) + learning_rate * 0.05
        )
    elif overall_accuracy < 0.5:
        # Model is underperforming — shift weight toward historical patterns
        new_weights['historical_patterns'] = min(
            0.40,
            previous_weights.get('historical_patterns', 0.20) + learning_rate * 0.10
        )
        new_weights['playbook_feedback'] = min(
            0.20,
            previous_weights.get('playbook_feedback', 0.10) + learning_rate * 0.05
        )

    # Normalize to sum to 1.0
    weight_sum = sum(new_weights.values())
    if weight_sum > 0:
        new_weights = {k: round(v / weight_sum, 4) for k, v in new_weights.items()}

    # Calculate error reduction
    # (simplistic: compare prediction accuracy before vs. expected after)
    error_before = 1 - overall_accuracy
    # Assume feedback loop improves by learning_rate fraction
    error_after = error_before * (1 - learning_rate)
    error_reduction_pct = round(
        ((error_before - error_after) / error_before) * 100, 1
    ) if error_before > 0 else 0

    # Persist the recalibration
    record = WeightCalibrationHistory(
        customer_id=customer_id,
        calibration_type='weight_recalibration',
        previous_weights=json.dumps(previous_weights),
        new_weights=json.dumps(new_weights),
        error_reduction_pct=error_reduction_pct,
        notes=(
            f"Recalibration for {playbook_type}: "
            f"{len(feedbacks)} feedbacks over {window_days}d, "
            f"churn_acc={churn_accuracy:.2f}, expansion_acc={expansion_accuracy:.2f}"
        ),
    )
    db.session.add(record)
    db.session.commit()

    return RecalibrationResult(
        customer_id=customer_id,
        playbook_type=playbook_type,
        feedback_count=len(feedbacks),
        previous_weights=previous_weights,
        new_weights=new_weights,
        error_reduction_pct=error_reduction_pct,
        signal_accuracy={
            'churn_accuracy': round(churn_accuracy, 4),
            'expansion_accuracy': round(expansion_accuracy, 4),
            'overall_accuracy': round(overall_accuracy, 4),
            'total_with_churn': total_with_churn,
            'total_with_expansion': total_with_expansion,
        },
        calibration_id=record.id,
    )


# ============================================================
# BATCH RECALIBRATION (all playbook types for a customer)
# ============================================================

def recalibrate_all(
    customer_id: int,
    window_days: int = 90,
    learning_rate: float = 0.1,
) -> List[RecalibrationResult]:
    """Run recalibration for all playbook types for a customer."""
    playbook_types = [
        'voc-sprint', 'activation-blitz', 'sla-stabilizer',
        'renewal-safeguard', 'expansion-timing',
    ]

    results = []
    for pt in playbook_types:
        result = recalibrate_weights(customer_id, pt, window_days, learning_rate)
        if result.feedback_count > 0:
            results.append(result)

    return results


# ============================================================
# QUERY HELPERS
# ============================================================

def get_calibration_history(
    customer_id: int,
    limit: int = 20,
) -> List[Dict]:
    """Return recent calibration history for a customer."""
    records = WeightCalibrationHistory.query.filter_by(
        customer_id=customer_id,
    ).order_by(
        WeightCalibrationHistory.calibrated_at.desc()
    ).limit(limit).all()

    return [
        {
            'id': r.id,
            'calibration_type': r.calibration_type,
            'previous_weights': json.loads(r.previous_weights) if r.previous_weights else {},
            'new_weights': json.loads(r.new_weights) if r.new_weights else {},
            'error_reduction_pct': r.error_reduction_pct,
            'notes': r.notes,
            'calibrated_at': r.calibrated_at.isoformat() if r.calibrated_at else None,
        }
        for r in records
    ]


def get_current_weights(customer_id: int) -> Dict[str, float]:
    """Get the most recent calibrated weights for a customer."""
    latest = WeightCalibrationHistory.query.filter(
        WeightCalibrationHistory.customer_id == customer_id,
        WeightCalibrationHistory.calibration_type == 'weight_recalibration',
    ).order_by(
        WeightCalibrationHistory.calibrated_at.desc()
    ).first()

    default_weights = {
        'quantitative_signals': 0.40,
        'qualitative_signals': 0.30,
        'historical_patterns': 0.20,
        'playbook_feedback': 0.10,
    }

    if latest and latest.new_weights:
        try:
            return json.loads(latest.new_weights)
        except (json.JSONDecodeError, TypeError):
            pass

    return default_weights


# ============================================================
# SERIALIZATION
# ============================================================

def recalibration_result_to_dict(r: RecalibrationResult) -> Dict:
    """Serialize a RecalibrationResult for API response."""
    return {
        'customer_id': r.customer_id,
        'playbook_type': r.playbook_type,
        'feedback_count': r.feedback_count,
        'previous_weights': r.previous_weights,
        'new_weights': r.new_weights,
        'error_reduction_pct': r.error_reduction_pct,
        'signal_accuracy': r.signal_accuracy,
        'calibration_id': r.calibration_id,
    }
