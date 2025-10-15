"""
Seed Data for Playbook Testing

Creates realistic scenarios for each playbook type
"""

from models import Customer, Account, KPI, User
from datetime import datetime, timedelta
import random

def create_base_customer(db):
    """Create base customer for all scenarios"""
    # Check if customer already exists
    existing_customer = Customer.query.filter_by(customer_id=1).first()
    if existing_customer:
        return existing_customer
    
    customer = Customer(
        customer_id=1,
        customer_name='Playbook Test Company',
        email='playbook@test.com'
    )
    db.session.add(customer)
    
    # Check if user already exists
    existing_user = User.query.filter_by(user_id=1).first()
    if not existing_user:
        user = User(
            user_id=1,
            customer_id=1,
            user_name='Test User',
            email='test@test.com',
            password_hash='test_hash'
        )
        db.session.add(user)
    
    db.session.commit()
    return customer


# ============================================================================
# VoC Sprint Scenarios
# ============================================================================

def create_voc_scenario_1(db):
    """
    VoC Sprint Scenario 1: Declining NPS and Multiple Churn Signals
    
    Triggers:
    - NPS < 10 (simulated via health score)
    - CSAT < 3.6 (simulated via health score)
    - Account marked as 'At Risk'
    - Multiple support tickets indicating dissatisfaction
    """
    account = Account(
        account_id=101,
        customer_id=1,
        account_name='TechCorp Industries',
        revenue=250000,
        account_status='At Risk',
        industry='Technology',
        region='North America'
    )
    db.session.add(account)
    
    # High volume of support tickets (dissatisfaction signal)
    kpis = [
        KPI(kpi_id=1001, account_id=101, category='Customer Success', kpi_parameter='Support Tickets', data='45', weight='High', impact_level='Critical'),
        KPI(kpi_id=1002, account_id=101, category='Customer Success', kpi_parameter='Escalations', data='8', weight='High', impact_level='Critical'),
        KPI(kpi_id=1003, account_id=101, category='Relationship Strength', kpi_parameter='Executive Engagement', data='Low', weight='High', impact_level='Critical'),
        KPI(kpi_id=1004, account_id=101, category='Product Usage', kpi_parameter='Login Frequency', data='Declining', weight='Medium', impact_level='High'),
        KPI(kpi_id=1005, account_id=101, category='Business Outcomes', kpi_parameter='ROI Perception', data='Negative', weight='High', impact_level='Critical'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_voc_scenario_2(db):
    """
    VoC Sprint Scenario 2: Sudden Health Score Drop
    
    Triggers:
    - Health score drop ≥ 10 points in 30-60 days
    - Recent churn mentions in notes
    - CSAT below threshold
    """
    account = Account(
        account_id=102,
        customer_id=1,
        account_name='MediHealth Solutions',
        revenue=180000,
          # Dropped from 65+ (simulated)
        account_status='Active',  # Still active but declining
        industry='Healthcare',
        region='Europe'
    )
    db.session.add(account)
    
    # Mixed signals - some good, some concerning
    kpis = [
        KPI(kpi_id=1011, account_id=102, category='Customer Success', kpi_parameter='Response Time', data='Slow', weight='High', impact_level='High'),
        KPI(kpi_id=1012, account_id=102, category='Product Usage', kpi_parameter='Feature Adoption', data='35%', weight='Medium', impact_level='Medium'),
        KPI(kpi_id=1013, account_id=102, category='Relationship Strength', kpi_parameter='QBR Attendance', data='Missed Last 2', weight='High', impact_level='High'),
        KPI(kpi_id=1014, account_id=102, category='Business Outcomes', kpi_parameter='Value Realization', data='Below Target', weight='High', impact_level='High'),
        KPI(kpi_id=1015, account_id=102, category='Customer Success', kpi_parameter='Satisfaction Score', data='2.8', weight='High', impact_level='Critical'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# Activation Blitz Scenarios
# ============================================================================

def create_activation_scenario_1(db):
    """
    Activation Blitz Scenario 1: New Customer with Low Adoption
    
    Triggers:
    - Adoption index < 60
    - Active users < 50
    - DAU/MAU < 25%
    - Multiple unused features in plan
    """
    account = Account(
        account_id=201,
        customer_id=1,
        account_name='StartupFast Inc',
        revenue=45000,
          # Low adoption proxy
        account_status='Active',
        industry='Technology',
        region='North America'
    )
    db.session.add(account)
    
    # Very limited feature usage
    kpis = [
        KPI(kpi_id=2001, account_id=201, category='Product Usage', kpi_parameter='Active Users', data='12', weight='High', impact_level='High'),
        KPI(kpi_id=2002, account_id=201, category='Product Usage', kpi_parameter='Feature A Usage', data='Not Used', weight='Medium', impact_level='Medium'),
        KPI(kpi_id=2003, account_id=201, category='Product Usage', kpi_parameter='Feature B Usage', data='Not Used', weight='Medium', impact_level='Medium'),
        KPI(kpi_id=2004, account_id=201, category='Product Usage', kpi_parameter='DAU/MAU Ratio', data='0.15', weight='High', impact_level='High'),
        KPI(kpi_id=2005, account_id=201, category='Customer Success', kpi_parameter='Onboarding Status', data='Incomplete', weight='High', impact_level='Critical'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_activation_scenario_2(db):
    """
    Activation Blitz Scenario 2: Stalled Expansion Account
    
    Triggers:
    - Adoption index < 60
    - Purchased premium features but not using them
    - Low user engagement despite large team
    """
    account = Account(
        account_id=202,
        customer_id=1,
        account_name='Enterprise Global Corp',
        revenue=500000,  # High revenue but low usage
          # Below adoption threshold
        account_status='Active',
        industry='Finance',
        region='Asia-Pacific'
    )
    db.session.add(account)
    
    # Large account with poor adoption
    kpis = [
        KPI(kpi_id=2011, account_id=202, category='Product Usage', kpi_parameter='Active Users', data='35', weight='High', impact_level='High'),
        KPI(kpi_id=2012, account_id=202, category='Product Usage', kpi_parameter='Licensed Users', data='200', weight='Medium', impact_level='Medium'),
        KPI(kpi_id=2013, account_id=202, category='Product Usage', kpi_parameter='Premium Feature X', data='0%', weight='High', impact_level='Critical'),
        KPI(kpi_id=2014, account_id=202, category='Product Usage', kpi_parameter='Premium Feature Y', data='5%', weight='High', impact_level='High'),
        KPI(kpi_id=2015, account_id=202, category='Product Usage', kpi_parameter='Advanced Analytics', data='Not Configured', weight='Medium', impact_level='High'),
        KPI(kpi_id=2016, account_id=202, category='Business Outcomes', kpi_parameter='Time to Value', data='Delayed', weight='High', impact_level='High'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# SLA Stabilizer Scenarios
# ============================================================================

def create_sla_scenario_1(db):
    """
    SLA Stabilizer Scenario 1: Consistent SLA Breaches
    
    Triggers:
    - Multiple SLA breaches in last 30 days
    - Response time degradation
    - Escalating ticket volume
    """
    account = Account(
        account_id=301,
        customer_id=1,
        account_name='CriticalOps Systems',
        revenue=320000,
        
        account_status='Active',
        industry='Technology',
        region='North America'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=3001, account_id=301, category='Customer Success', kpi_parameter='SLA Breaches', data='8', weight='Critical', impact_level='Critical'),
        KPI(kpi_id=3002, account_id=301, category='Customer Success', kpi_parameter='Avg Response Time', data='4.5 hours', weight='High', impact_level='High'),
        KPI(kpi_id=3003, account_id=301, category='Customer Success', kpi_parameter='SLA Target', data='2 hours', weight='High', impact_level='High'),
        KPI(kpi_id=3004, account_id=301, category='Customer Success', kpi_parameter='Ticket Volume', data='Increasing', weight='Medium', impact_level='High'),
        KPI(kpi_id=3005, account_id=301, category='Customer Success', kpi_parameter='Resolution Time', data='Above Target', weight='High', impact_level='High'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_sla_scenario_2(db):
    """
    SLA Stabilizer Scenario 2: Quality Issues Despite Meeting SLA
    
    Triggers:
    - SLA met but customer satisfaction declining
    - High reopen rate
    - Quality concerns in feedback
    """
    account = Account(
        account_id=302,
        customer_id=1,
        account_name='QualityFirst Manufacturing',
        revenue=275000,
        
        account_status='Active',
        industry='Manufacturing',
        region='Europe'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=3011, account_id=302, category='Customer Success', kpi_parameter='SLA Compliance', data='98%', weight='High', impact_level='Low'),
        KPI(kpi_id=3012, account_id=302, category='Customer Success', kpi_parameter='Ticket Reopen Rate', data='35%', weight='High', impact_level='Critical'),
        KPI(kpi_id=3013, account_id=302, category='Customer Success', kpi_parameter='First Contact Resolution', data='45%', weight='High', impact_level='High'),
        KPI(kpi_id=3014, account_id=302, category='Customer Success', kpi_parameter='Support Satisfaction', data='2.9', weight='High', impact_level='High'),
        KPI(kpi_id=3015, account_id=302, category='Relationship Strength', kpi_parameter='Support Feedback', data='Negative Trend', weight='Medium', impact_level='High'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# Renewal Safeguard Scenarios
# ============================================================================

def create_renewal_scenario_1(db):
    """
    Renewal Safeguard Scenario 1: 90-Day Renewal Risk
    
    Triggers:
    - Renewal date within 90 days
    - Health score < 70
    - Declining engagement
    - Budget concerns mentioned
    """
    account = Account(
        account_id=401,
        customer_id=1,
        account_name='RenewalRisk Enterprises',
        revenue=420000,
        
        account_status='Active',  # But renewal at risk
        industry='Finance',
        region='North America'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=4001, account_id=401, category='Business Outcomes', kpi_parameter='Renewal Date', data='75 days', weight='Critical', impact_level='Critical'),
        KPI(kpi_id=4002, account_id=401, category='Relationship Strength', kpi_parameter='Executive Engagement', data='Declining', weight='High', impact_level='High'),
        KPI(kpi_id=4003, account_id=401, category='Business Outcomes', kpi_parameter='ROI Achievement', data='Below Expectations', weight='High', impact_level='Critical'),
        KPI(kpi_id=4004, account_id=401, category='Product Usage', kpi_parameter='Usage Trend', data='Declining 15%', weight='High', impact_level='High'),
        KPI(kpi_id=4005, account_id=401, category='Relationship Strength', kpi_parameter='Budget Concerns', data='Mentioned', weight='Critical', impact_level='Critical'),
        KPI(kpi_id=4006, account_id=401, category='Customer Success', kpi_parameter='Business Review Status', data='Overdue', weight='High', impact_level='High'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_renewal_scenario_2(db):
    """
    Renewal Safeguard Scenario 2: Silent Churn Risk
    
    Triggers:
    - Renewal within 120 days
    - Sudden decrease in communication
    - Champion left company
    - Competitive evaluation signals
    """
    account = Account(
        account_id=402,
        customer_id=1,
        account_name='SilentChurn Industries',
        revenue=195000,
          # Appears okay but signals are concerning
        account_status='Active',
        industry='Healthcare',
        region='Europe'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=4011, account_id=402, category='Business Outcomes', kpi_parameter='Renewal Date', data='110 days', weight='Critical', impact_level='High'),
        KPI(kpi_id=4012, account_id=402, category='Relationship Strength', kpi_parameter='Champion Status', data='Left Company', weight='Critical', impact_level='Critical'),
        KPI(kpi_id=4013, account_id=402, category='Relationship Strength', kpi_parameter='Communication Frequency', data='Dropped 60%', weight='High', impact_level='High'),
        KPI(kpi_id=4014, account_id=402, category='Product Usage', kpi_parameter='Login Activity', data='Reduced', weight='Medium', impact_level='Medium'),
        KPI(kpi_id=4015, account_id=402, category='Relationship Strength', kpi_parameter='Competitive Signals', data='Detected', weight='Critical', impact_level='Critical'),
        KPI(kpi_id=4016, account_id=402, category='Customer Success', kpi_parameter='Success Plan Status', data='Not Updated', weight='Medium', impact_level='High'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# Expansion Timing Scenarios
# ============================================================================

def create_expansion_scenario_1(db):
    """
    Expansion Timing Scenario 1: High Adoption Ready for Upsell
    
    Triggers:
    - Health score > 80
    - High feature adoption
    - Growing team size
    - Approaching usage limits
    """
    account = Account(
        account_id=501,
        customer_id=1,
        account_name='GrowthMode Technologies',
        revenue=150000,
          # High health, ready for expansion
        account_status='Active',
        industry='Technology',
        region='North America'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=5001, account_id=501, category='Product Usage', kpi_parameter='Feature Adoption', data='92%', weight='High', impact_level='Low'),
        KPI(kpi_id=5002, account_id=501, category='Product Usage', kpi_parameter='Active Users', data='85', weight='High', impact_level='Low'),
        KPI(kpi_id=5003, account_id=501, category='Product Usage', kpi_parameter='User Growth', data='+45% QoQ', weight='High', impact_level='Low'),
        KPI(kpi_id=5004, account_id=501, category='Product Usage', kpi_parameter='Usage vs Limit', data='85% of plan', weight='High', impact_level='Medium'),
        KPI(kpi_id=5005, account_id=501, category='Business Outcomes', kpi_parameter='ROI Achievement', data='Exceeded Target', weight='High', impact_level='Low'),
        KPI(kpi_id=5006, account_id=501, category='Relationship Strength', kpi_parameter='Executive Satisfaction', data='Very High', weight='High', impact_level='Low'),
        KPI(kpi_id=5007, account_id=501, category='Product Usage', kpi_parameter='Premium Feature Interest', data='Inquiries Made', weight='Medium', impact_level='Low'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_expansion_scenario_2(db):
    """
    Expansion Timing Scenario 2: Cross-Sell Opportunity
    
    Triggers:
    - High satisfaction with current product
    - Adjacent use case identified
    - Budget available
    - Strategic initiative alignment
    """
    account = Account(
        account_id=502,
        customer_id=1,
        account_name='Strategic Expansion Corp',
        revenue=380000,
        
        account_status='Active',
        industry='Finance',
        region='Asia-Pacific'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=5011, account_id=502, category='Business Outcomes', kpi_parameter='Current Product Satisfaction', data='9.2/10', weight='High', impact_level='Low'),
        KPI(kpi_id=5012, account_id=502, category='Relationship Strength', kpi_parameter='Executive Sponsorship', data='Strong', weight='High', impact_level='Low'),
        KPI(kpi_id=5013, account_id=502, category='Business Outcomes', kpi_parameter='Adjacent Use Case', data='Identified', weight='High', impact_level='Low'),
        KPI(kpi_id=5014, account_id=502, category='Business Outcomes', kpi_parameter='Budget Availability', data='Confirmed', weight='Critical', impact_level='Low'),
        KPI(kpi_id=5015, account_id=502, category='Relationship Strength', kpi_parameter='Strategic Alignment', data='High', weight='High', impact_level='Low'),
        KPI(kpi_id=5016, account_id=502, category='Product Usage', kpi_parameter='Cross-Sell Interest', data='Expressed', weight='High', impact_level='Low'),
        KPI(kpi_id=5017, account_id=502, category='Business Outcomes', kpi_parameter='Expansion Timeline', data='Q1 Planning', weight='Medium', impact_level='Low'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# Control Scenarios (Healthy Accounts - Should NOT Trigger)
# ============================================================================

def create_healthy_account_1(db):
    """Healthy account that should not trigger any playbooks"""
    account = Account(
        account_id=901,
        customer_id=1,
        account_name='Perfect Health Co',
        revenue=200000,
        
        account_status='Active',
        industry='Technology',
        region='North America'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=9001, account_id=901, category='Product Usage', kpi_parameter='Feature Adoption', data='95%', weight='High', impact_level='Low'),
        KPI(kpi_id=9002, account_id=901, category='Customer Success', kpi_parameter='Support Tickets', data='2', weight='Low', impact_level='Low'),
        KPI(kpi_id=9003, account_id=901, category='Business Outcomes', kpi_parameter='ROI', data='Excellent', weight='High', impact_level='Low'),
        KPI(kpi_id=9004, account_id=901, category='Relationship Strength', kpi_parameter='Engagement', data='High', weight='High', impact_level='Low'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


def create_healthy_account_2(db):
    """Another healthy account for control"""
    account = Account(
        account_id=902,
        customer_id=1,
        account_name='Thriving Business Inc',
        revenue=350000,
        
        account_status='Active',
        industry='Healthcare',
        region='Europe'
    )
    db.session.add(account)
    
    kpis = [
        KPI(kpi_id=9011, account_id=902, category='Product Usage', kpi_parameter='Active Users', data='150', weight='High', impact_level='Low'),
        KPI(kpi_id=9012, account_id=902, category='Customer Success', kpi_parameter='Satisfaction', data='4.8/5', weight='High', impact_level='Low'),
        KPI(kpi_id=9013, account_id=902, category='Business Outcomes', kpi_parameter='Value Realization', data='Exceeds Target', weight='High', impact_level='Low'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()
    return account


# ============================================================================
# Main Seed Function
# ============================================================================

def seed_all_scenarios(db):
    """Seed all playbook scenarios"""
    print("🌱 Seeding playbook test scenarios...")
    
    # Create base customer
    create_base_customer(db)
    print("✅ Created base customer and user")
    
    # VoC Sprint scenarios
    create_voc_scenario_1(db)
    print("✅ Created VoC Sprint Scenario 1: Declining NPS")
    
    create_voc_scenario_2(db)
    print("✅ Created VoC Sprint Scenario 2: Health Score Drop")
    
    # Activation Blitz scenarios
    create_activation_scenario_1(db)
    print("✅ Created Activation Blitz Scenario 1: Low Adoption")
    
    create_activation_scenario_2(db)
    print("✅ Created Activation Blitz Scenario 2: Stalled Expansion")
    
    # SLA Stabilizer scenarios
    create_sla_scenario_1(db)
    print("✅ Created SLA Stabilizer Scenario 1: SLA Breaches")
    
    create_sla_scenario_2(db)
    print("✅ Created SLA Stabilizer Scenario 2: Quality Issues")
    
    # Renewal Safeguard scenarios
    create_renewal_scenario_1(db)
    print("✅ Created Renewal Safeguard Scenario 1: 90-Day Risk")
    
    create_renewal_scenario_2(db)
    print("✅ Created Renewal Safeguard Scenario 2: Silent Churn")
    
    # Expansion Timing scenarios
    create_expansion_scenario_1(db)
    print("✅ Created Expansion Timing Scenario 1: High Adoption")
    
    create_expansion_scenario_2(db)
    print("✅ Created Expansion Timing Scenario 2: Cross-Sell")
    
    # Control scenarios
    create_healthy_account_1(db)
    create_healthy_account_2(db)
    print("✅ Created 2 healthy control accounts")
    
    print(f"\n📊 Total accounts created: 12")
    print(f"   - VoC Sprint scenarios: 2")
    print(f"   - Activation Blitz scenarios: 2")
    print(f"   - SLA Stabilizer scenarios: 2")
    print(f"   - Renewal Safeguard scenarios: 2")
    print(f"   - Expansion Timing scenarios: 2")
    print(f"   - Healthy controls: 2")
    print("\n✅ Seed data creation complete!")

