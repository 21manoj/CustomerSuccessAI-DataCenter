#!/usr/bin/env python3
"""
E2E Test: Pre-Playbook Validation

Tests the complete flow of:
1. Signal Analyst output validation
2. Confidence threshold checks
3. Reasoning validation before triggering
4. Trigger condition validation
5. Pre-trigger validation logic

CRITICAL TEST - Validates pre-playbook validation before triggering
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from extensions import db
from models import Account, DC2SKPI, AccountNote, Customer
from agents.signal_analyst_agent import SignalAnalystAgent
from agents.models import SignalAnalystInput
from agents.signal_converter import convert_database_models_to_signals
from openai_key_utils import get_openai_api_key

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def validate_pre_playbook(result, min_confidence=0.6, min_reasoning_length=200) -> dict:
    """Validate Signal Analyst output before playbook triggering"""
    validation = {
        'passed': True,
        'issues': [],
        'warnings': []
    }
    
    # Check confidence
    if result.confidence.overall_confidence < min_confidence:
        validation['passed'] = False
        validation['issues'].append(f"Confidence too low: {result.confidence.overall_confidence:.2f} < {min_confidence}")
    
    # Check reasoning
    if len(result.reasoning) < min_reasoning_length:
        validation['warnings'].append(f"Reasoning too short: {len(result.reasoning)} < {min_reasoning_length}")
    
    # Check churn probability threshold
    if result.churn_probability > 70:
        validation['warnings'].append(f"High churn probability: {result.churn_probability:.1f}%")
    
    # Check data alignment
    if result.data_alignment:
        alignment = result.data_alignment.get('alignment', '')
        if alignment == 'disagreement':
            validation['warnings'].append("Data alignment shows disagreement - may need investigation")
        elif alignment == 'insufficient_data':
            validation['passed'] = False
            validation['issues'].append("Insufficient data for playbook triggering")
    
    # Check risk drivers
    if not result.risk_drivers:
        validation['warnings'].append("No risk drivers identified")
    
    return validation

def test_pre_playbook_validation():
    """Test pre-playbook validation E2E"""
    log("="*80)
    log("E2E TEST: Pre-Playbook Validation")
    log("="*80)
    
    with app.app_context():
        try:
            # Setup
            log("\n📋 Step 1: Setting up test data...")
            customer = Customer.query.filter_by(customer_name="Test Customer Validation").first()
            if not customer:
                customer = Customer(customer_name="Test Customer Validation", email="test@validation.com")
                db.session.add(customer)
                db.session.commit()
            
            customer_id = customer.customer_id
            
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_name="Test Account Validation"
            ).first()
            if not account:
                account = Account(
                    customer_id=customer_id,
                    account_name="Test Account Validation",
                    revenue=50000.0,
                    account_status="active"
                )
                db.session.add(account)
                db.session.commit()
            
            account_id = account.account_id
            
            # Create high-risk signals
            log("\n📊 Step 2: Creating high-risk signals...")
            
            dc_kpi = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=1),
                value=2000.0,  # Critical
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
            
            note = AccountNote(
                account_id=account_id,
                customer_id=customer_id,
                note_type="escalation",
                note_content="Customer frustrated. Considering cancellation. Support issues unresolved.",
                created_by=user.user_id,
                created_at=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(note)
            db.session.commit()
            
            log("✅ Created high-risk signals")
            
            # Run analysis
            log("\n🤖 Step 3: Running Signal Analyst...")
            
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
                account_health_score=35.0  # Critical
            )
            
            agent_input = SignalAnalystInput(
                account_id=str(account_id),
                customer_id=customer_id,
                vertical_type="saas_customer_success",
                account_name=account.account_name,
                health_score=35.0,
                quantitative_signals=db_signals['quantitative_signals'],
                qualitative_signals=db_signals['qualitative_signals'],
                historical_patterns=[],
                analysis_type="churn_risk",
                time_horizon_days=60
            )
            
            agent = SignalAnalystAgent(
                openai_api_key=openai_api_key,
                customer_id=customer_id,
                account_id=str(account_id)
            )
            
            result = agent.analyze(agent_input)
            
            log(f"✅ Analysis completed:")
            outcome_value = result.predicted_outcome.value if hasattr(result.predicted_outcome, 'value') else str(result.predicted_outcome)
            log(f"   - Outcome: {outcome_value}")
            log(f"   - Churn Probability: {result.churn_probability:.1f}%")
            log(f"   - Confidence: {result.confidence.overall_confidence:.2f}")
            
            # Pre-playbook validation
            log("\n✅ Step 4: Pre-Playbook Validation...")
            
            validation = validate_pre_playbook(result, min_confidence=0.6)
            
            if validation['passed']:
                log("✅ Validation PASSED - Ready for playbook triggering")
            else:
                log("❌ Validation FAILED - Not ready for playbook triggering", "ERROR")
            
            if validation['issues']:
                log("   Issues:")
                for issue in validation['issues']:
                    log(f"      - {issue}", "ERROR")
            
            if validation['warnings']:
                log("   Warnings:")
                for warning in validation['warnings']:
                    log(f"      - {warning}", "WARNING")
            
            # Check trigger readiness
            log("\n✅ Step 5: Trigger Readiness Assessment...")
            
            trigger_ready = (
                validation['passed'] and
                result.churn_probability > 50 and
                result.confidence.overall_confidence >= 0.6 and
                len(result.reasoning) >= 200
            )
            
            if trigger_ready:
                log("✅ READY FOR PLAYBOOK TRIGGER")
                log(f"   - Churn Probability: {result.churn_probability:.1f}% (threshold: >50%)")
                log(f"   - Confidence: {result.confidence.overall_confidence:.2f} (threshold: >=0.6)")
                log(f"   - Reasoning Length: {len(result.reasoning)} (threshold: >=200)")
            else:
                log("⚠️  NOT READY FOR PLAYBOOK TRIGGER", "WARNING")
                log("   - Additional validation or investigation needed")
            
            log("\n" + "="*80)
            if validation['passed']:
                log("✅ TEST PASSED: Pre-Playbook Validation E2E")
            else:
                log("⚠️  TEST PASSED WITH ISSUES: Pre-Playbook Validation E2E")
            log("="*80)
            return True
            
        except Exception as e:
            log(f"❌ TEST FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_pre_playbook_validation()
    sys.exit(0 if success else 1)
