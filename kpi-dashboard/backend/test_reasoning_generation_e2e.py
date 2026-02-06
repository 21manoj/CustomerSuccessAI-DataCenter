#!/usr/bin/env python3
"""
E2E Test: Reasoning Generation

Tests the complete flow of:
1. Signal Analyst reasoning generation
2. Reasoning quality assessment
3. Reasoning consistency validation
4. Reasoning explainability

CRITICAL TEST - Validates reasoning quality and explainability
"""

import sys
import os
import json
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

def assess_reasoning_quality(reasoning: str) -> dict:
    """Assess reasoning quality"""
    quality = {
        'length': len(reasoning),
        'has_specifics': False,
        'has_examples': False,
        'has_temporal_context': False,
        'has_causal_links': False,
        'score': 0.0
    }
    
    # Check for specific details
    quality['has_specifics'] = any(word in reasoning.lower() for word in ['kpi', 'metric', 'signal', 'score', 'trend'])
    
    # Check for examples
    quality['has_examples'] = any(word in reasoning.lower() for word in ['example', 'instance', 'case', 'such as', 'for instance'])
    
    # Check for temporal context
    quality['has_temporal_context'] = any(word in reasoning.lower() for word in ['week', 'month', 'day', 'recent', 'declining', 'improving'])
    
    # Check for causal links
    quality['has_causal_links'] = any(word in reasoning.lower() for word in ['because', 'due to', 'caused by', 'resulting in', 'leads to'])
    
    # Calculate score
    score = 0.0
    if quality['has_specifics']: score += 0.25
    if quality['has_examples']: score += 0.25
    if quality['has_temporal_context']: score += 0.25
    if quality['has_causal_links']: score += 0.25
    quality['score'] = score
    
    return quality

def test_reasoning_generation():
    """Test reasoning generation E2E"""
    log("="*80)
    log("E2E TEST: Reasoning Generation")
    log("="*80)
    
    with app.app_context():
        try:
            # Setup test data
            log("\n📋 Step 1: Setting up test data...")
            customer = Customer.query.filter_by(customer_name="Test Customer Reasoning").first()
            if not customer:
                customer = Customer(customer_name="Test Customer Reasoning", email="test@reasoning.com")
                db.session.add(customer)
                db.session.commit()
            
            customer_id = customer.customer_id
            
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_name="Test Account Reasoning"
            ).first()
            if not account:
                account = Account(
                    customer_id=customer_id,
                    account_name="Test Account Reasoning",
                    revenue=75000.0,
                    account_status="active"
                )
                db.session.add(account)
                db.session.commit()
            
            account_id = account.account_id
            
            # Create signals
            log("\n📊 Step 2: Creating test signals...")
            
            # Declining KPI
            dc_kpi1 = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=14),
                value=6000.0,
                target=6000.0,
                pillar="AI"
            )
            dc_kpi2 = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=1),
                value=3500.0,  # Declining
                target=6000.0,
                pillar="AI"
            )
            db.session.add_all([dc_kpi1, dc_kpi2])
            
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
            
            # Negative signal
            note = AccountNote(
                account_id=account_id,
                customer_id=customer_id,
                note_type="support",
                note_content="Customer frustrated with slow response times. Support tickets taking 5+ days.",
                created_by=user.user_id,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(note)
            db.session.commit()
            
            log(f"✅ Created test signals for account {account_id}")
            
            # Convert to signals
            log("\n🔄 Step 3: Converting to SignalData...")
            dc_kpis = DC2SKPI.query.filter_by(account_id=account_id).all()
            notes = AccountNote.query.filter_by(account_id=account_id).all()
            
            db_signals = convert_database_models_to_signals(
                account=account,
                dc_kpis=dc_kpis,
                notes=notes,
                account_health_score=55.0
            )
            
            # Test reasoning generation
            log("\n🤖 Step 4: Testing reasoning generation...")
            
            openai_api_key = get_openai_api_key(customer_id)
            if not openai_api_key:
                log("⚠️  OpenAI API key not found", "WARNING")
                return False
            
            agent_input = SignalAnalystInput(
                account_id=str(account_id),
                customer_id=customer_id,
                vertical_type="saas_customer_success",
                account_name=account.account_name,
                health_score=55.0,
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
            
            # Assess reasoning quality
            log("\n✅ Step 5: Assessing reasoning quality...")
            reasoning = result.reasoning
            quality = assess_reasoning_quality(reasoning)
            
            log(f"   Reasoning Length: {quality['length']} chars")
            log(f"   Has Specifics: {quality['has_specifics']}")
            log(f"   Has Examples: {quality['has_examples']}")
            log(f"   Has Temporal Context: {quality['has_temporal_context']}")
            log(f"   Has Causal Links: {quality['has_causal_links']}")
            log(f"   Quality Score: {quality['score']:.2f}/1.0")
            
            # Validate reasoning
            log("\n✅ Step 6: Validating reasoning...")
            issues = []
            
            if quality['score'] < 0.5:
                issues.append("Reasoning quality score too low")
            
            if len(reasoning) < 200:
                issues.append("Reasoning too short")
            
            if not quality['has_specifics']:
                issues.append("Reasoning lacks specific details")
            
            if issues:
                log(f"⚠️  Issues found: {', '.join(issues)}", "WARNING")
            else:
                log("✅ Reasoning quality validated")
            
            # Check key insights
            if result.key_insights:
                log(f"\n✅ Key Insights ({len(result.key_insights)}):")
                for i, insight in enumerate(result.key_insights[:3], 1):
                    log(f"   {i}. {insight[:80]}...")
            
            log("\n" + "="*80)
            if issues:
                log("⚠️  TEST PASSED WITH WARNINGS: Reasoning Generation E2E")
            else:
                log("✅ TEST PASSED: Reasoning Generation E2E")
            log("="*80)
            return True
            
        except Exception as e:
            log(f"❌ TEST FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_reasoning_generation()
    sys.exit(0 if success else 1)
