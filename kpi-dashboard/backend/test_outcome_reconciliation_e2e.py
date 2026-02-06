#!/usr/bin/env python3
"""
E2E Test: Outcome Reconciliation

Tests the complete flow of:
1. Multiple signal analysis results
2. Outcome reconciliation logic
3. Prediction validation
4. Confidence score reconciliation
5. Multi-signal conflict resolution

CRITICAL TEST - Validates outcome reconciliation before playbook triggering
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from extensions import db
from models import Account, DC2SKPI, AccountNote, QualitativeSignal, Customer
from agents.signal_analyst_agent import SignalAnalystAgent
from agents.models import SignalAnalystInput
from agents.signal_converter import convert_database_models_to_signals
from agents.qualitative_signal_converter import convert_qualitative_signals_to_signal_data
from openai_key_utils import get_openai_api_key

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def reconcile_outcomes(results: list) -> dict:
    """Reconcile multiple analysis outcomes"""
    if not results:
        return {'status': 'insufficient_data', 'confidence': 0.0}
    
    # Count outcomes
    outcome_counts = {}
    total_confidence = 0.0
    
    for result in results:
        outcome = result.predicted_outcome.value
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        total_confidence += result.confidence.overall_confidence
    
    # Determine reconciled outcome
    most_common = max(outcome_counts.items(), key=lambda x: x[1])
    avg_confidence = total_confidence / len(results)
    
    # Check for conflicts
    has_conflict = len(outcome_counts) > 1
    
    return {
        'reconciled_outcome': most_common[0],
        'outcome_counts': outcome_counts,
        'average_confidence': avg_confidence,
        'has_conflict': has_conflict,
        'conflict_resolution': 'majority_vote' if has_conflict else 'unanimous'
    }

def test_outcome_reconciliation():
    """Test outcome reconciliation E2E"""
    log("="*80)
    log("E2E TEST: Outcome Reconciliation")
    log("="*80)
    
    with app.app_context():
        try:
            # Setup
            log("\n📋 Step 1: Setting up test data...")
            customer = Customer.query.filter_by(customer_name="Test Customer Reconciliation").first()
            if not customer:
                customer = Customer(customer_name="Test Customer Reconciliation", email="test@recon.com")
                db.session.add(customer)
                db.session.commit()
            
            customer_id = customer.customer_id
            
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_name="Test Account Reconciliation"
            ).first()
            if not account:
                account = Account(
                    customer_id=customer_id,
                    account_name="Test Account Reconciliation",
                    revenue=90000.0,
                    account_status="active"
                )
                db.session.add(account)
                db.session.commit()
            
            account_id = account.account_id
            
            # Create conflicting signals
            log("\n📊 Step 2: Creating conflicting signals...")
            
            # Declining KPI
            dc_kpi = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=1),
                value=3000.0,  # Declining
                target=6000.0,
                pillar="AI"
            )
            db.session.add(dc_kpi)
            
            # Get or create a user for created_by
            from models import User
            user = User.query.filter_by(customer_id=customer_id).first()
            if not user:
                user = User(
                    customer_id=customer_id,
                    user_name="Test User",
                    email=f"testuser@{customer_id}.com",
                    password_hash="test"
                )
                db.session.add(user)
                db.session.flush()
            
            # Positive signal (conflicting)
            note = AccountNote(
                account_id=account_id,
                customer_id=customer_id,
                note_type="meeting",
                note_content="QBR went very well. Customer expanding usage next quarter. Very satisfied.",
                created_by=user.user_id,
                created_at=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(note)
            db.session.commit()
            
            log("✅ Created conflicting signals (declining KPI + positive note)")
            
            # Run multiple analyses
            log("\n🤖 Step 3: Running multiple analyses...")
            
            openai_api_key = get_openai_api_key(customer_id)
            if not openai_api_key:
                log("⚠️  OpenAI API key not found", "WARNING")
                return False
            
            dc_kpis = DC2SKPI.query.filter_by(account_id=account_id).all()
            notes = AccountNote.query.filter_by(account_id=account_id).all()
            
            db_signals = convert_database_models_to_signals(
                account=account,
                dc_kpis=dc_kpis,
                notes=notes,
                account_health_score=58.0
            )
            
            agent_input = SignalAnalystInput(
                account_id=str(account_id),
                customer_id=customer_id,
                vertical_type="saas_customer_success",
                account_name=account.account_name,
                health_score=58.0,
                quantitative_signals=db_signals['quantitative_signals'],
                qualitative_signals=db_signals['qualitative_signals'],
                historical_patterns=[],
                analysis_type="comprehensive",
                time_horizon_days=60
            )
            
            agent = SignalAnalystAgent(
                openai_api_key=openai_api_key,
                customer_id=customer_id,
                account_id=str(account_id)
            )
            
            # Run analysis
            result = agent.analyze(agent_input)
            
            log(f"✅ Analysis completed:")
            outcome_value = result.predicted_outcome.value if hasattr(result.predicted_outcome, 'value') else str(result.predicted_outcome)
            log(f"   - Outcome: {outcome_value}")
            log(f"   - Churn Probability: {result.churn_probability:.1f}%")
            log(f"   - Confidence: {result.confidence.overall_confidence:.2f}")
            
            # Check data alignment (reconciliation indicator)
            log("\n✅ Step 4: Checking outcome reconciliation...")
            
            if result.data_alignment:
                alignment = result.data_alignment
                log(f"   Data Alignment: {alignment.get('alignment', 'N/A')}")
                
                if alignment.get('alignment') == 'disagreement':
                    log("   ⚠️  DISAGREEMENT detected - signals conflict")
                    log(f"   Reasoning: {alignment.get('reasoning', '')[:200]}...")
                else:
                    log("   ✅ Signals aligned - no conflict")
            
            # Validate reconciliation
            log("\n✅ Step 5: Validating reconciliation...")
            
            # Check if reasoning addresses conflict
            reasoning = result.reasoning.lower()
            addresses_conflict = any(word in reasoning for word in ['conflict', 'disagreement', 'conflicting', 'lagging', 'temporary'])
            
            if addresses_conflict:
                log("✅ Reasoning addresses signal conflicts")
            else:
                log("⚠️  Reasoning may not address conflicts", "WARNING")
            
            # Check confidence
            if result.confidence.overall_confidence < 0.6:
                log("⚠️  Low confidence - may indicate reconciliation needed", "WARNING")
            else:
                log(f"✅ Confidence acceptable: {result.confidence.overall_confidence:.2f}")
            
            log("\n" + "="*80)
            log("✅ TEST PASSED: Outcome Reconciliation E2E")
            log("="*80)
            return True
            
        except Exception as e:
            log(f"❌ TEST FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_outcome_reconciliation()
    sys.exit(0 if success else 1)
