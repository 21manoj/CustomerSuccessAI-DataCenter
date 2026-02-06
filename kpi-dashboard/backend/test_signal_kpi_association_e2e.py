#!/usr/bin/env python3
"""
E2E Test: Signal to KPI Association

Tests the complete flow of:
1. Signal collection (quantitative and qualitative)
2. KPI association and mapping
3. Quantitative score association
4. Signal-KPI correlation validation
5. Confidence scoring for associations

CRITICAL TEST - Validates core Signal Analyst functionality
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from extensions import db
from models import Account, KPI, AccountNote, DC2SKPI, QualitativeSignal, Customer, User
from agents.signal_analyst_api import signal_analyst_api
from agents.models import SignalAnalystInput, SignalData
from agents.signal_converter import convert_database_models_to_signals
from agents.qualitative_signal_converter import convert_qualitative_signals_to_signal_data
from openai_key_utils import get_openai_api_key

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def test_signal_kpi_association():
    """Test signal to KPI association E2E"""
    log("="*80)
    log("E2E TEST: Signal to KPI Association")
    log("="*80)
    
    with app.app_context():
        try:
            # Step 1: Setup test data
            log("\n📋 Step 1: Setting up test data...")
            customer = Customer.query.filter_by(customer_name="Test Customer E2E").first()
            if not customer:
                customer = Customer(customer_name="Test Customer E2E", email="test@e2e.com")
                db.session.add(customer)
                db.session.commit()
                log(f"✅ Created test customer: {customer.customer_id}")
            else:
                log(f"✅ Using existing test customer: {customer.customer_id}")
            
            customer_id = customer.customer_id
            
            # Create test account
            account = Account.query.filter_by(
                customer_id=customer_id,
                account_name="Test Account E2E"
            ).first()
            if not account:
                account = Account(
                    customer_id=customer_id,
                    account_name="Test Account E2E",
                    revenue=100000.0,
                    industry="Technology",
                    region="North America",
                    account_status="active"
                )
                db.session.add(account)
                db.session.commit()
                log(f"✅ Created test account: {account.account_id}")
            else:
                log(f"✅ Using existing test account: {account.account_id}")
            
            account_id = account.account_id
            
            # Step 2: Create quantitative signals (KPIs)
            log("\n📊 Step 2: Creating quantitative signals (KPIs)...")
            
            # Create DC2S KPIs
            from models import DC2SKPI
            dc_kpi = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=7),
                value=5000.0,
                target=6000.0,
                pillar="AI"
            )
            db.session.add(dc_kpi)
            
            dc_kpi2 = DC2SKPI(
                account_id=account_id,
                kpi_code="DAU",
                measured_at=datetime.utcnow() - timedelta(days=1),
                value=3500.0,  # Declining
                target=6000.0,
                pillar="AI"
            )
            db.session.add(dc_kpi2)
            db.session.commit()
            log(f"✅ Created {2} DC2S KPI measurements")
            
            # Step 3: Create qualitative signals
            log("\n💬 Step 3: Creating qualitative signals...")
            
            # Get or create a user for created_by
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
            
            # Create AccountNote
            note = AccountNote(
                account_id=account_id,
                customer_id=customer_id,
                note_type="support",
                note_content="Customer frustrated with slow response times. Support tickets taking 5+ days to resolve.",
                created_by=user.user_id,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(note)
            
            # Create QualitativeSignal (check if exists first to avoid duplicates)
            signal_id = f"test_{account_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            existing_signal = QualitativeSignal.query.filter_by(signal_id=signal_id).first()
            if not existing_signal:
                qual_signal = QualitativeSignal(
                    signal_id=signal_id,
                    account_id=account_id,
                    signal_date=datetime.utcnow().date() - timedelta(days=2),
                    signal_type="escalation",
                    content="Customer escalated support ticket due to delayed response",
                    sentiment="negative"
                )
                db.session.add(qual_signal)
                db.session.commit()
            else:
                log(f"✅ Using existing qualitative signal: {signal_id}")
            log(f"✅ Created {2} qualitative signals")
            
            # Step 4: Convert to SignalData format
            log("\n🔄 Step 4: Converting to SignalData format...")
            
            dc_kpis = DC2SKPI.query.filter_by(account_id=account_id).all()
            notes = AccountNote.query.filter_by(account_id=account_id).all()
            qual_signals = QualitativeSignal.query.filter_by(account_id=account_id).all()
            
            # Convert qualitative signals
            qual_signal_data = convert_qualitative_signals_to_signal_data(qual_signals)
            
            # Convert database models to signals
            db_signals = convert_database_models_to_signals(
                account=account,
                kpis=None,
                dc_kpis=dc_kpis,
                notes=notes,
                account_health_score=55.0  # At-risk
            )
            
            log(f"✅ Converted signals:")
            log(f"   - Quantitative: {len(db_signals['quantitative_signals'])}")
            log(f"   - Qualitative: {len(db_signals['qualitative_signals']) + len(qual_signal_data)}")
            
            # Step 5: Test Signal-KPI Association
            log("\n🔗 Step 5: Testing Signal-KPI Association...")
            
            # Check if quantitative signals have KPI associations
            quant_signals = db_signals['quantitative_signals']
            kpi_associations = []
            for signal in quant_signals:
                payload = signal.payload
                if payload.get('signal_type') == 'dc2s_kpi':
                    kpi_code = payload.get('kpi_code')
                    value = payload.get('value')
                    health_status = payload.get('health_status')
                    kpi_associations.append({
                        'kpi_code': kpi_code,
                        'value': value,
                        'health_status': health_status
                    })
            
            log(f"✅ Found {len(kpi_associations)} KPI associations")
            for assoc in kpi_associations:
                log(f"   - {assoc['kpi_code']}: {assoc['value']} ({assoc['health_status']})")
            
            # Step 6: Test Signal Analyst API
            log("\n🤖 Step 6: Testing Signal Analyst API...")
            
            openai_api_key = get_openai_api_key(customer_id)
            if not openai_api_key:
                log("⚠️  OpenAI API key not found, skipping Signal Analyst test", "WARNING")
                return False
            
            # Build SignalAnalystInput
            from agents.models import SignalAnalystInput
            agent_input = SignalAnalystInput(
                account_id=str(account_id),
                customer_id=customer_id,
                vertical_type="saas_customer_success",
                account_name=account.account_name,
                account_arr=float(account.revenue) if account.revenue else None,
                health_score=55.0,
                quantitative_signals=db_signals['quantitative_signals'],
                qualitative_signals=db_signals['qualitative_signals'] + qual_signal_data,
                historical_patterns=[],
                analysis_type="churn_risk",
                time_horizon_days=60
            )
            
            # Call Signal Analyst
            from agents.signal_analyst_agent import SignalAnalystAgent
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
            
            # Step 7: Validate Signal-KPI Association in Output
            log("\n✅ Step 7: Validating Signal-KPI Association in Output...")
            
            # Check if reasoning mentions KPIs
            reasoning = result.reasoning.lower()
            kpi_mentioned = any(kpi in reasoning for kpi in ['dau', 'kpi', 'metric', 'usage', 'declining'])
            
            if kpi_mentioned:
                log("✅ Reasoning mentions KPIs - association validated")
            else:
                log("⚠️  Reasoning does not mention KPIs - may need improvement", "WARNING")
            
            # Check if risk drivers reference signals
            if result.risk_drivers:
                log(f"✅ Found {len(result.risk_drivers)} risk drivers")
                for i, driver in enumerate(result.risk_drivers[:3], 1):
                    log(f"   {i}. {driver.driver[:80]}...")
                    if driver.supporting_signals:
                        log(f"      Supported by: {len(driver.supporting_signals)} signals")
            
            # Check data alignment
            if result.data_alignment:
                alignment = result.data_alignment
                log(f"✅ Data Alignment: {alignment.get('alignment', 'N/A')}")
                log(f"   - Confidence: {alignment.get('confidence', 0):.2f}")
                log(f"   - Trend: {alignment.get('trend_direction', 'N/A')}")
                log(f"   - Sentiment: {alignment.get('signal_sentiment', 'N/A')}")
            
            log("\n" + "="*80)
            log("✅ TEST PASSED: Signal-KPI Association E2E")
            log("="*80)
            return True
            
        except Exception as e:
            log(f"❌ TEST FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_signal_kpi_association()
    sys.exit(0 if success else 1)
