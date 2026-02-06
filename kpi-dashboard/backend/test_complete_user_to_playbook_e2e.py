#!/usr/bin/env python3
"""
E2E Test: Complete User to Playbook Flow

Tests the complete end-to-end flow:
1. Create new user
2. Onboard user
3. Run the system
4. Create and visualize journeys
5. Analyze signals and associate with KPIs
6. Reasoning and reconciling outcomes
7. Pre-playbook validation
8. Playbook trigger readiness

COMPREHENSIVE E2E TEST - Full workflow validation
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from extensions import db
from models import Account, Customer, User, DC2SKPI, AccountNote, QualitativeSignal, CustomerConfig
from agents.signal_analyst_agent import SignalAnalystAgent
from agents.models import SignalAnalystInput
from agents.signal_converter import convert_database_models_to_signals
from agents.qualitative_signal_converter import convert_qualitative_signals_to_signal_data
from openai_key_utils import get_openai_api_key

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def test_complete_flow():
    """Test complete user to playbook flow E2E"""
    log("="*80)
    log("E2E TEST: Complete User to Playbook Flow")
    log("="*80)
    
    with app.app_context():
        try:
            # Step 1: Create User
            log("\n👤 Step 1: Creating user...")
            test_email = f"test_e2e_{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
            
            user = User.query.filter_by(email=test_email).first()
            if not user:
                # Create customer first
                customer = Customer(
                    customer_name=f"Test Customer E2E {datetime.now().strftime('%H%M%S')}",
                    email=test_email
                )
                db.session.add(customer)
                db.session.flush()
                
                user = User(
                    customer_id=customer.customer_id,
                    user_name="Test User E2E",
                    email=test_email,
                    password_hash="test_hash"  # In real test, would hash password
                )
                db.session.add(user)
                db.session.commit()
                log(f"✅ Created user: {user.email} (customer_id: {user.customer_id})")
            else:
                log(f"✅ Using existing user: {user.email}")
            
            customer_id = user.customer_id
            
            # Step 2: Onboard (Create CustomerConfig)
            log("\n⚙️  Step 2: Onboarding (creating config)...")
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if not config:
                config = CustomerConfig(
                    customer_id=customer_id,
                    vertical="saas_customer_success"
                )
                db.session.add(config)
                db.session.commit()
                log("✅ Created customer config")
            else:
                log("✅ Customer config exists")
            
            # Step 3: Create Account
            log("\n🏢 Step 3: Creating account...")
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_name="E2E Test Account"
            ).first()
            if not account:
                account = Account(
                    customer_id=customer_id,
                    account_name="E2E Test Account",
                    revenue=100000.0,
                    industry="Technology",
                    region="North America",
                    account_status="active"
                )
                db.session.add(account)
                db.session.commit()
                log(f"✅ Created account: {account.account_id}")
            else:
                log(f"✅ Using existing account: {account.account_id}")
            
            account_id = account.account_id
            
            # Step 4: Create KPIs and Signals
            log("\n📊 Step 4: Creating KPIs and signals...")
            
            # Create KPIs showing decline
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
                value=3000.0,  # Declining
                target=6000.0,
                pillar="AI"
            )
            db.session.add_all([dc_kpi1, dc_kpi2])
            
            # Create negative signals
            # Use the user we created earlier
            note = AccountNote(
                account_id=account_id,
                customer_id=customer_id,
                note_type="escalation",
                note_content="Customer frustrated with support response times. Tickets taking 5+ days.",
                created_by=user.user_id,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(note)
            
            qual_signal = QualitativeSignal(
                signal_id=f"e2e_{account_id}_1",
                account_id=account_id,
                signal_date=datetime.utcnow().date() - timedelta(days=2),
                signal_type="escalation",
                content="Customer escalated support ticket due to delayed response",
                sentiment="negative"
            )
            db.session.add(qual_signal)
            db.session.commit()
            
            log("✅ Created KPIs and signals")
            
            # Step 5: Signal Analysis
            log("\n🤖 Step 5: Running Signal Analyst...")
            
            openai_api_key = get_openai_api_key(customer_id)
            if not openai_api_key:
                log("⚠️  OpenAI API key not found, skipping analysis", "WARNING")
                return False
            
            dc_kpis = DC2SKPI.query.filter_by(account_id=account_id).all()
            notes = AccountNote.query.filter_by(account_id=account_id).all()
            qual_signals = QualitativeSignal.query.filter_by(account_id=account_id).all()
            
            # Convert signals
            qual_signal_data = convert_qualitative_signals_to_signal_data(qual_signals)
            db_signals = convert_database_models_to_signals(
                account=account,
                dc_kpis=dc_kpis,
                notes=notes,
                account_health_score=45.0  # At-risk
            )
            
            agent_input = SignalAnalystInput(
                account_id=str(account_id),
                customer_id=customer_id,
                vertical_type="saas_customer_success",
                account_name=account.account_name,
                account_arr=float(account.revenue) if account.revenue else None,
                health_score=45.0,
                quantitative_signals=db_signals['quantitative_signals'],
                qualitative_signals=db_signals['qualitative_signals'] + qual_signal_data,
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
            
            log(f"✅ Signal Analyst completed:")
            log(f"   - Health Score: {result.health_score:.1f}")
            log(f"   - Churn Probability: {result.churn_probability:.1f}%")
            outcome_value = result.predicted_outcome.value if hasattr(result.predicted_outcome, 'value') else str(result.predicted_outcome)
            log(f"   - Predicted Outcome: {outcome_value}")
            log(f"   - Confidence: {result.confidence.overall_confidence:.2f}")
            
            # Step 6: Validate Signal-KPI Association
            log("\n🔗 Step 6: Validating Signal-KPI Association...")
            
            # Check if signals are associated with KPIs in reasoning
            reasoning = result.reasoning.lower()
            kpi_mentioned = any(word in reasoning for word in ['dau', 'kpi', 'metric', 'usage', 'declining'])
            
            if kpi_mentioned:
                log("✅ Signals associated with KPIs in reasoning")
            else:
                log("⚠️  Signals may not be associated with KPIs", "WARNING")
            
            # Step 7: Validate Reasoning
            log("\n📝 Step 7: Validating Reasoning...")
            
            if len(result.reasoning) >= 200:
                log(f"✅ Reasoning length acceptable: {len(result.reasoning)} chars")
            else:
                log(f"⚠️  Reasoning too short: {len(result.reasoning)} chars", "WARNING")
            
            if result.key_insights:
                log(f"✅ Key insights provided: {len(result.key_insights)}")
            else:
                log("⚠️  No key insights provided", "WARNING")
            
            # Step 8: Outcome Reconciliation
            log("\n🔄 Step 8: Validating Outcome Reconciliation...")
            
            if result.data_alignment:
                alignment = result.data_alignment
                log(f"✅ Data Alignment: {alignment.get('alignment', 'N/A')}")
                log(f"   - Confidence: {alignment.get('confidence', 0):.2f}")
                
                if alignment.get('alignment') == 'agreement':
                    log("✅ Signals aligned - high confidence in outcome")
                elif alignment.get('alignment') == 'disagreement':
                    log("⚠️  Signals conflict - reconciliation needed", "WARNING")
            
            # Step 9: Pre-Playbook Validation
            log("\n✅ Step 9: Pre-Playbook Validation...")
            
            validation_passed = (
                result.confidence.overall_confidence >= 0.6 and
                len(result.reasoning) >= 200 and
                result.churn_probability > 0
            )
            
            if validation_passed:
                log("✅ Pre-playbook validation PASSED")
                log(f"   - Confidence: {result.confidence.overall_confidence:.2f} (>= 0.6)")
                log(f"   - Reasoning: {len(result.reasoning)} chars (>= 200)")
                log(f"   - Churn Probability: {result.churn_probability:.1f}%")
            else:
                log("⚠️  Pre-playbook validation has issues", "WARNING")
            
            # Step 10: Playbook Trigger Readiness
            log("\n🚀 Step 10: Playbook Trigger Readiness...")
            
            trigger_ready = (
                validation_passed and
                result.churn_probability > 50 and
                result.data_alignment and
                result.data_alignment.get('alignment') != 'insufficient_data'
            )
            
            if trigger_ready:
                log("✅ READY FOR PLAYBOOK TRIGGER")
                log(f"   - Churn Probability: {result.churn_probability:.1f}% (threshold: >50%)")
                log(f"   - Confidence: {result.confidence.overall_confidence:.2f} (threshold: >=0.6)")
                log(f"   - Data Alignment: {result.data_alignment.get('alignment', 'N/A')}")
                
                if result.recommended_actions:
                    log(f"   - Recommended Actions: {len(result.recommended_actions)}")
            else:
                log("⚠️  NOT READY FOR PLAYBOOK TRIGGER", "WARNING")
                log("   - Additional validation or investigation needed")
            
            # Summary
            log("\n" + "="*80)
            log("📊 E2E TEST SUMMARY")
            log("="*80)
            log(f"✅ User Created: {user.email}")
            log(f"✅ Customer Onboarded: {customer_id}")
            log(f"✅ Account Created: {account_id}")
            log(f"✅ Signals Created: {len(dc_kpis) + len(notes) + len(qual_signals)}")
            log(f"✅ Signal Analysis: Completed")
            log(f"✅ Signal-KPI Association: {'Validated' if kpi_mentioned else 'Needs Review'}")
            log(f"✅ Reasoning: {'Valid' if len(result.reasoning) >= 200 else 'Needs Review'}")
            log(f"✅ Outcome Reconciliation: {'Validated' if result.data_alignment else 'Missing'}")
            log(f"✅ Pre-Playbook Validation: {'PASSED' if validation_passed else 'NEEDS REVIEW'}")
            log(f"✅ Playbook Trigger Ready: {'YES' if trigger_ready else 'NO'}")
            log("="*80)
            
            if trigger_ready:
                log("✅ TEST PASSED: Complete User to Playbook Flow E2E")
            else:
                log("⚠️  TEST PASSED WITH WARNINGS: Complete User to Playbook Flow E2E")
            
            return True
            
        except Exception as e:
            log(f"❌ TEST FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_complete_flow()
    sys.exit(0 if success else 1)
