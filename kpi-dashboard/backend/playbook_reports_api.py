"""
Playbook Reports API

Generates comprehensive reports for playbook executions with RACI, outcomes, and exit criteria
"""

from flask import Blueprint, request, jsonify
from models import db, Account, KPI, PlaybookReport
from datetime import datetime
from dateutil import parser as date_parser
import json
import random

playbook_reports_api = Blueprint('playbook_reports_api', __name__)

def get_customer_id():
    """Get customer ID from request headers"""
    return request.headers.get('X-Customer-ID', type=int, default=1)


# In-memory cache for faster access (automatically loaded from DB on startup)
_execution_reports = {}
_db_loaded = False

def load_reports_from_db():
    """Load all reports from database into memory cache on startup"""
    global _db_loaded
    if _db_loaded:
        return
    
    try:
        all_reports = PlaybookReport.query.all()
        for report in all_reports:
            _execution_reports[report.execution_id] = report.report_data
        _db_loaded = True
        print(f"✓ Loaded {len(all_reports)} playbook reports from database")
    except Exception as e:
        print(f"Warning: Could not load reports from database: {e}")
        _db_loaded = True  # Set to True to prevent repeated attempts


def save_report_to_db(execution_id, report, execution_data):
    """Save or update a playbook report in the database"""
    try:
        customer_id = get_customer_id()
        
        # Parse timestamps
        started_at = execution_data.get('startedAt')
        if isinstance(started_at, str):
            started_at = date_parser.parse(started_at)
        
        completed_at = execution_data.get('completedAt')
        if completed_at and isinstance(completed_at, str):
            completed_at = date_parser.parse(completed_at)
        
        # Get account info
        account_id = execution_data.get('accountId') or execution_data.get('context', {}).get('accountId')
        account_name = report.get('account_name', 'All Accounts')
        
        # Count steps
        results = execution_data.get('results', [])
        steps_completed = len([r for r in results if r.get('status') == 'completed'])
        
        # Check if report already exists
        existing_report = PlaybookReport.query.filter_by(execution_id=execution_id).first()
        
        if existing_report:
            # Update existing report
            existing_report.report_data = report
            existing_report.status = execution_data.get('status', 'in-progress')
            existing_report.steps_completed = steps_completed
            existing_report.completed_at = completed_at
            existing_report.updated_at = datetime.utcnow()
        else:
            # Create new report
            new_report = PlaybookReport(
                execution_id=execution_id,
                customer_id=customer_id,
                account_id=account_id,
                playbook_id=report.get('playbook_id'),
                playbook_name=report.get('playbook_name'),
                account_name=account_name,
                status=execution_data.get('status', 'in-progress'),
                report_data=report,
                duration=report.get('duration'),
                steps_completed=steps_completed,
                started_at=started_at or datetime.utcnow(),
                completed_at=completed_at,
                report_generated_at=datetime.utcnow()
            )
            db.session.add(new_report)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error saving report to database: {e}")
        db.session.rollback()
        return False


def generate_voc_sprint_report(execution_id, playbook_data, account_data=None):
    """Generate comprehensive VoC Sprint report"""
    
    # Simulate data based on account or general metrics
    if account_data:
        account_name = account_data.get('account_name', 'Selected Account')
        account_id = account_data.get('account_id')
    else:
        account_name = 'All Accounts'
        account_id = None
    
    # Simulate themes discovered
    themes = [
        {
            'theme': 'Product Value Gaps',
            'evidence': '15 customers mentioned difficulty realizing ROI',
            'customer_quotes': [
                '"We purchased for Feature X but can\'t figure out how to use it effectively"',
                '"The value proposition was clear in sales, but implementation is unclear"'
            ],
            'impact': 'High',
            'frequency': 15
        },
        {
            'theme': 'Adoption Challenges',
            'evidence': '8 customers struggling with user onboarding',
            'customer_quotes': [
                '"Our team finds the interface confusing"',
                '"Need better training materials"'
            ],
            'impact': 'Medium',
            'frequency': 8
        },
        {
            'theme': 'Support Response Time',
            'evidence': '12 mentions of slow support response',
            'customer_quotes': [
                '"Waiting 2+ days for ticket responses"',
                '"Critical issues not prioritized"'
            ],
            'impact': 'High',
            'frequency': 12
        },
        {
            'theme': 'Feature Roadmap Alignment',
            'evidence': '6 customers requesting specific features',
            'customer_quotes': [
                '"Need mobile app support"',
                '"API documentation needs improvement"'
            ],
            'impact': 'Medium',
            'frequency': 6
        },
        {
            'theme': 'Integration Complexity',
            'evidence': '10 customers facing integration issues',
            'customer_quotes': [
                '"Integration with our CRM took 3 months"',
                '"Need better API examples"'
            ],
            'impact': 'High',
            'frequency': 10
        }
    ]
    
    # 3 Committed Fixes (Now, Next Release, Process)
    committed_fixes = [
        {
            'fix': 'Implement in-app value calculator',
            'type': 'Now',
            'owner': 'Product Team - Sarah Chen',
            'timeline': '2 weeks',
            'status': 'In Progress'
        },
        {
            'fix': 'Enhanced onboarding tutorial with video walkthroughs',
            'type': 'Next Release',
            'owner': 'Enablement Team - Mike Johnson',
            'timeline': '6 weeks (Q1 Release)',
            'status': 'Planned'
        },
        {
            'fix': 'Improve support ticket prioritization process',
            'type': 'Process',
            'owner': 'Support Lead - Jennifer Martinez',
            'timeline': 'Ongoing',
            'status': 'Implemented'
        }
    ]
    
    # RACI Matrix
    raci = {
        'Discovery & Interviews': {
            'CSM': 'Responsible',
            'Product Manager': 'Consulted',
            'Support Lead': 'Consulted',
            'Executive Sponsor': 'Informed'
        },
        'Theme Analysis': {
            'CSM': 'Accountable',
            'Product Manager': 'Responsible',
            'Support Lead': 'Consulted',
            'Executive Sponsor': 'Informed'
        },
        'Executive Readout': {
            'CSM': 'Responsible',
            'Product Manager': 'Responsible',
            'Support Lead': 'Informed',
            'Executive Sponsor': 'Accountable'
        },
        'Fix Implementation': {
            'CSM': 'Accountable',
            'Product Manager': 'Responsible',
            'Support Lead': 'Responsible',
            'Executive Sponsor': 'Consulted'
        },
        'Customer Communications': {
            'CSM': 'Responsible',
            'Product Manager': 'Consulted',
            'Support Lead': 'Consulted',
            'Executive Sponsor': 'Informed'
        }
    }
    
    # Outcomes Achieved
    outcomes = {
        'nps_improvement': {
            'baseline': 6.5,
            'current': 14.2,
            'improvement': '+7.7 points',
            'target': '+6-10 points',
            'status': 'Achieved'
        },
        'csat_improvement': {
            'baseline': 3.2,
            'current': 3.6,
            'improvement': '+0.4 points',
            'target': '+0.2-0.3 points',
            'status': 'Exceeded'
        },
        'ticket_sentiment': {
            'baseline': 'Negative trend',
            'current': 'Positive trend',
            'improvement': 'Sentiment shift',
            'target': 'Positive trend',
            'status': 'Achieved'
        },
        'renewal_intent': {
            'baseline': '62%',
            'current': '78%',
            'improvement': '+16%',
            'target': 'Measurable increase',
            'status': 'Exceeded'
        }
    }
    
    # Exit Criteria
    exit_criteria = [
        {'criteria': 'Themes logged and categorized', 'status': 'Met', 'evidence': '5 themes identified with supporting quotes'},
        {'criteria': '3 fixes committed with owners assigned', 'status': 'Met', 'evidence': '1 Now, 1 Next Release, 1 Process fix committed'},
        {'criteria': '"We heard you" communications sent', 'status': 'Met', 'evidence': 'Email sent to all interview participants + broader customer base'},
        {'criteria': 'NPS follow-up scheduled', 'status': 'Met', 'evidence': 'Follow-up survey scheduled for 45 days post-implementation'}
    ]
    
    return {
        'execution_id': execution_id,
        'playbook_name': 'VoC Sprint',
        'playbook_id': 'voc-sprint',
        'account_name': account_name,
        'account_id': account_id,
        'report_generated_at': datetime.utcnow().isoformat(),
        'duration': '30 days',
        'status': 'Completed',
        'themes_discovered': themes,
        'committed_fixes': committed_fixes,
        'raci_matrix': raci,
        'outcomes_achieved': outcomes,
        'exit_criteria': exit_criteria,
        'executive_summary': f"Successfully completed VoC Sprint for {account_name}. Conducted 8 customer interviews, analyzed 60 days of support tickets and QBR notes. Identified 5 key themes affecting customer satisfaction. Secured executive commitment for 3 prioritized fixes. NPS improved by 7.7 points (exceeding +6-10 target), CSAT improved by 0.4 points (exceeding +0.2-0.3 target). All exit criteria met.",
        'next_steps': [
            'Monitor NPS scores weekly for continued improvement',
            'Track implementation progress of 3 committed fixes',
            'Conduct follow-up NPS survey in 45 days',
            'Share learnings with product and support teams',
            'Update customer success playbook based on insights'
        ]
    }


def generate_activation_blitz_report(execution_id, playbook_data, account_data=None):
    """Generate comprehensive Activation Blitz report"""
    
    if account_data:
        account_name = account_data.get('account_name', 'Selected Account')
        account_id = account_data.get('account_id')
    else:
        account_name = 'All Accounts'
        account_id = None
    
    # Simulated activation results
    activation_results = {
        'features_activated': [
            {'feature': 'Advanced Analytics Dashboard', 'adoption_rate': '78%', 'users': 42},
            {'feature': 'Automated Reporting', 'adoption_rate': '65%', 'users': 35}
        ],
        'training_completed': {
            'power_users': '85% (17/20)',
            'viewers': '92% (23/25)',
            'total_sessions': 8
        },
        'use_cases_published': [
            {'title': 'Revenue Forecasting with Advanced Analytics', 'downloads': 38, 'satisfaction': 4.5},
            {'title': 'Automated Monthly Reports Setup', 'downloads': 32, 'satisfaction': 4.7},
            {'title': 'Real-time Dashboard Configuration', 'downloads': 28, 'satisfaction': 4.3}
        ]
    }
    
    # RACI Matrix
    raci = {
        'In-App Walkthroughs': {
            'CSM': 'Accountable',
            'Enablement': 'Responsible',
            'Admin Champion': 'Consulted',
            'Product Team': 'Informed'
        },
        'Role-Based Training': {
            'CSM': 'Accountable',
            'Enablement': 'Responsible',
            'Admin Champion': 'Responsible',
            'Product Team': 'Consulted'
        },
        'Use Case Development': {
            'CSM': 'Responsible',
            'Enablement': 'Responsible',
            'Admin Champion': 'Consulted',
            'Product Team': 'Consulted'
        },
        'Executive Checkpoint': {
            'CSM': 'Responsible',
            'Enablement': 'Consulted',
            'Admin Champion': 'Informed',
            'Executive Sponsor': 'Accountable'
        },
        'Success Stories': {
            'CSM': 'Responsible',
            'Enablement': 'Consulted',
            'Admin Champion': 'Responsible',
            'Marketing': 'Informed'
        }
    }
    
    # Outcomes
    outcomes = {
        'adoption_improvement': {
            'baseline': 42,
            'current': 58,
            'improvement': '+16 points',
            'target': '+10-15 points',
            'status': 'Exceeded'
        },
        'active_users_increase': {
            'baseline': 35,
            'current': 54,
            'improvement': '+54%',
            'target': '+20-30%',
            'status': 'Exceeded'
        },
        'dau_mau_ratio': {
            'baseline': 0.18,
            'current': 0.32,
            'improvement': '+78%',
            'target': '≥ 0.25',
            'status': 'Exceeded'
        },
        'time_to_value': {
            'baseline': '45 days',
            'current': '22 days',
            'improvement': '-51%',
            'target': 'Reduction',
            'status': 'Exceeded'
        }
    }
    
    # Exit Criteria
    exit_criteria = [
        {'criteria': 'Two features activated successfully', 'status': 'Met', 'evidence': 'Advanced Analytics (78%) and Automated Reporting (65%) activated'},
        {'criteria': 'DAU/MAU ≥ 25%', 'status': 'Met', 'evidence': 'Achieved 32% DAU/MAU ratio'},
        {'criteria': 'Adoption index ≥ 60 (or +10 vs. baseline)', 'status': 'Met', 'evidence': 'Adoption index increased from 42 to 58 (+16 points)'},
        {'criteria': 'Two success stories secured for QBR', 'status': 'Met', 'evidence': '2 customer success stories documented with metrics'}
    ]
    
    return {
        'execution_id': execution_id,
        'playbook_name': 'Activation Blitz',
        'playbook_id': 'activation-blitz',
        'account_name': account_name,
        'account_id': account_id,
        'report_generated_at': datetime.utcnow().isoformat(),
        'duration': '30 days',
        'status': 'Completed',
        'activation_results': activation_results,
        'raci_matrix': raci,
        'outcomes_achieved': outcomes,
        'exit_criteria': exit_criteria,
        'executive_summary': f"Successfully completed Activation Blitz for {account_name}. Activated 2 key features with adoption rates of 78% and 65%. Conducted 8 training sessions with 85%+ completion rates. Published 3 KPI-aligned use cases averaging 4.5/5 satisfaction. Adoption index improved by 16 points (exceeding +10-15 target), active users increased by 54% (exceeding +20-30% target), DAU/MAU ratio reached 32% (exceeding 25% target). All exit criteria exceeded.",
        'next_steps': [
            'Monitor ongoing feature adoption weekly',
            'Schedule advanced training for power users',
            'Expand use case library based on customer feedback',
            'Track time-to-value metrics for new users',
            'Share success stories in upcoming QBR'
        ]
    }


def generate_sla_stabilizer_report(execution_id, playbook_data, account_data=None):
    """Generate comprehensive SLA Stabilizer report"""
    
    if account_data:
        account_name = account_data.get('account_name', 'Selected Account')
        account_id = account_data.get('account_id')
    else:
        account_name = 'All Accounts'
        account_id = None
    
    # Root cause analysis
    root_causes = [
        {
            'cause': 'High ticket volume (spike in P1/P2 tickets)',
            'frequency': '45% of breaches',
            'impact': 'Critical',
            'evidence': '23 P1 tickets in 30 days vs. 8 average'
        },
        {
            'cause': 'Complex technical issues requiring escalation',
            'frequency': '30% of breaches',
            'impact': 'High',
            'evidence': '18 escalations with avg resolution time 72hrs'
        },
        {
            'cause': 'Inadequate ticket routing and prioritization',
            'frequency': '25% of breaches',
            'impact': 'Medium',
            'evidence': 'Manual routing causing 4-6 hour delays'
        }
    ]
    
    # Preventive measures implemented
    preventive_measures = [
        {
            'measure': 'AI-powered ticket routing and prioritization',
            'implementation': 'Deploy ML model to auto-route and prioritize tickets based on content, urgency, and customer tier',
            'timeline': 'Week 1 - Implemented',
            'expected_impact': '40% reduction in routing delays',
            'status': 'Deployed'
        },
        {
            'measure': 'Escalation fast-track protocol',
            'implementation': 'Define clear escalation paths with 1-hour response SLA for P1 tickets',
            'timeline': 'Week 1 - Implemented',
            'expected_impact': '50% reduction in escalation resolution time',
            'status': 'Deployed'
        },
        {
            'measure': 'Proactive capacity planning dashboard',
            'implementation': 'Real-time monitoring of ticket queue depth, team capacity, and predictive breach alerts',
            'timeline': 'Week 2 - Implemented',
            'expected_impact': 'Prevent 60% of capacity-related breaches',
            'status': 'Active'
        }
    ]
    
    # RACI Matrix
    raci = {
        'Root Cause Analysis': {
            'Support Manager': 'Responsible',
            'CSM': 'Accountable',
            'Support Engineers': 'Consulted',
            'Customer': 'Informed'
        },
        'Capacity Planning': {
            'Support Manager': 'Accountable',
            'CSM': 'Consulted',
            'VP Customer Success': 'Responsible',
            'Finance': 'Consulted'
        },
        'Process Improvements': {
            'Support Manager': 'Responsible',
            'CSM': 'Accountable',
            'Support Engineers': 'Consulted',
            'Product Team': 'Informed'
        },
        'Monitoring Dashboard': {
            'Support Manager': 'Accountable',
            'Engineering': 'Responsible',
            'CSM': 'Consulted',
            'Customer': 'Informed'
        },
        'Customer Communications': {
            'CSM': 'Responsible',
            'Support Manager': 'Consulted',
            'Customer': 'Accountable',
            'Executive Sponsor': 'Informed'
        }
    }
    
    # Outcomes achieved
    outcomes = {
        'sla_compliance': {
            'baseline': '78%',
            'current': '96%',
            'improvement': '+18%',
            'target': '> 95%',
            'status': 'Exceeded'
        },
        'response_time': {
            'baseline': '4.2 hours',
            'current': '1.8 hours',
            'improvement': '-2.4 hours (-57%)',
            'target': '< 2 hours',
            'status': 'Achieved'
        },
        'resolution_time': {
            'baseline': '18.5 hours',
            'current': '12.3 hours',
            'improvement': '-6.2 hours (-34%)',
            'target': '30% improvement',
            'status': 'Exceeded'
        },
        'reopen_rate': {
            'baseline': '22%',
            'current': '8%',
            'improvement': '-14%',
            'target': '< 10%',
            'status': 'Achieved'
        },
        'customer_satisfaction': {
            'baseline': '3.4/5',
            'current': '4.3/5',
            'improvement': '+0.9 points',
            'target': '> 4.0/5',
            'status': 'Exceeded'
        },
        'escalation_reduction': {
            'baseline': '36 escalations/month',
            'current': '15 escalations/month',
            'improvement': '-58%',
            'target': '50% reduction',
            'status': 'Exceeded'
        }
    }
    
    # Exit criteria
    exit_criteria = [
        {'criteria': 'SLA compliance restored to > 95%', 'status': 'Met', 'evidence': '96% compliance over last 14 days'},
        {'criteria': 'Response time < 2 hours', 'status': 'Met', 'evidence': 'Average response time 1.8 hours'},
        {'criteria': 'Resolution time improved by 30%', 'status': 'Met', 'evidence': '34% improvement (18.5hrs → 12.3hrs)'},
        {'criteria': 'Ticket reopen rate < 10%', 'status': 'Met', 'evidence': '8% reopen rate'},
        {'criteria': 'Customer satisfaction > 4.0/5', 'status': 'Met', 'evidence': '4.3/5 support satisfaction'},
        {'criteria': 'Escalation reduction by 50%', 'status': 'Met', 'evidence': '58% reduction (36 → 15 monthly)'}
    ]
    
    return {
        'execution_id': execution_id,
        'playbook_name': 'SLA Stabilizer',
        'playbook_id': 'sla-stabilizer',
        'account_name': account_name,
        'account_id': account_id,
        'report_generated_at': datetime.utcnow().isoformat(),
        'duration': '14 days',
        'status': 'Completed',
        'root_causes': root_causes,
        'preventive_measures': preventive_measures,
        'raci_matrix': raci,
        'outcomes_achieved': outcomes,
        'exit_criteria': exit_criteria,
        'executive_summary': f"Successfully completed SLA Stabilizer for {account_name}. Analyzed 60 days of SLA breaches, identified 3 root causes. Implemented AI-powered ticket routing, escalation fast-track, and real-time monitoring. SLA compliance improved from 78% to 96% (exceeding 95% target). Response time reduced by 57%, resolution time by 34%. All 6 exit criteria met or exceeded.",
        'next_steps': [
            'Continue monitoring SLA metrics weekly',
            'Refine AI routing model based on feedback',
            'Conduct monthly capacity planning reviews',
            'Share best practices with other accounts',
            'Schedule quarterly SLA review with customer'
        ]
    }


def generate_renewal_safeguard_report(execution_id, playbook_data, account_data=None):
    """Generate comprehensive Renewal Safeguard report"""
    
    if account_data:
        account_name = account_data.get('account_name', 'Selected Account')
        account_id = account_data.get('account_id')
    else:
        account_name = 'All Accounts'
        account_id = None
    
    # Risk assessment results
    risk_assessment = {
        'initial_risk_score': 72,  # High risk
        'current_risk_score': 28,  # Low risk
        'improvement': '-44 points',
        'key_risks_identified': [
            {'risk': 'Low executive engagement', 'severity': 'Critical', 'status': 'Mitigated'},
            {'risk': 'Declining product usage', 'severity': 'High', 'status': 'Resolved'},
            {'risk': 'Lack of documented ROI', 'severity': 'High', 'status': 'Resolved'},
            {'risk': 'Champion departure concern', 'severity': 'Medium', 'status': 'Mitigated'}
        ]
    }
    
    # Value demonstration activities
    value_activities = [
        {
            'activity': 'Executive Business Review (EBR)',
            'description': 'Comprehensive EBR with C-level stakeholders showcasing ROI and strategic value',
            'outcome': 'CEO and CFO confirmed value alignment with strategic initiatives',
            'date': 'Week 4'
        },
        {
            'activity': 'ROI Analysis & Business Case',
            'description': 'Documented $2.3M annual value: $1.5M cost savings + $800K revenue impact',
            'outcome': 'CFO validated ROI calculations, requested expansion discussion',
            'date': 'Week 6'
        },
        {
            'activity': 'Success Story Development',
            'description': 'Co-created customer success story highlighting key wins and outcomes',
            'outcome': 'Featured in customer internal newsletter and company all-hands',
            'date': 'Week 8'
        },
        {
            'activity': 'Strategic Roadmap Alignment',
            'description': 'Mapped product roadmap to customer 2025 strategic priorities',
            'outcome': '4 high-priority features aligned to customer initiatives',
            'date': 'Week 10'
        }
    ]
    
    # RACI Matrix
    raci = {
        'Risk Assessment': {
            'CSM': 'Responsible',
            'Sales': 'Consulted',
            'Customer Success Manager': 'Accountable',
            'Customer Champion': 'Consulted'
        },
        'Executive Engagement': {
            'Account Executive': 'Responsible',
            'CSM': 'Responsible',
            'VP Customer Success': 'Accountable',
            'Customer Executives': 'Consulted'
        },
        'ROI Documentation': {
            'CSM': 'Responsible',
            'Customer Success Ops': 'Responsible',
            'Finance': 'Consulted',
            'Customer Finance': 'Accountable'
        },
        'Usage Optimization': {
            'CSM': 'Accountable',
            'Solutions Engineer': 'Responsible',
            'Customer Admin': 'Responsible',
            'Customer Users': 'Consulted'
        },
        'Renewal Negotiation': {
            'Account Executive': 'Accountable',
            'CSM': 'Responsible',
            'Sales Leadership': 'Consulted',
            'Customer Procurement': 'Consulted'
        }
    }
    
    # Outcomes achieved
    outcomes = {
        'health_score': {
            'baseline': 62,
            'current': 82,
            'improvement': '+20 points',
            'target': '+15 points',
            'status': 'Exceeded'
        },
        'executive_engagement': {
            'baseline': 'Low (score: 3/10)',
            'current': 'High (score: 9/10)',
            'improvement': '+6 points',
            'target': 'Measurable improvement',
            'status': 'Exceeded'
        },
        'roi_documentation': {
            'baseline': 'None',
            'current': '$2.3M annual value',
            'improvement': 'Fully documented',
            'target': 'Documented and validated',
            'status': 'Achieved'
        },
        'renewal_outcome': {
            'baseline': 'At-risk (72% risk score)',
            'current': 'Secured + 15% expansion',
            'improvement': 'Renewal saved + growth',
            'target': 'Renewal secured',
            'status': 'Exceeded'
        },
        'contract_value': {
            'baseline': '$450K ARR',
            'current': '$517.5K ARR',
            'improvement': '+$67.5K (+15%)',
            'target': 'Renewal at current value',
            'status': 'Exceeded'
        }
    }
    
    # Exit criteria
    exit_criteria = [
        {'criteria': 'Renewal secured or timeline extended', 'status': 'Met', 'evidence': 'Renewed with 15% expansion, 2-year commitment'},
        {'criteria': 'Health score improved by 15+ points', 'status': 'Met', 'evidence': 'Improved from 62 to 82 (+20 points)'},
        {'criteria': 'Executive engagement restored', 'status': 'Met', 'evidence': 'C-level engagement score 9/10, EBR completed'},
        {'criteria': 'ROI documented and validated', 'status': 'Met', 'evidence': '$2.3M annual value documented and CFO-validated'},
        {'criteria': 'Business case presented', 'status': 'Met', 'evidence': 'Presented to executive team, received board approval'}
    ]
    
    return {
        'execution_id': execution_id,
        'playbook_name': 'Renewal Safeguard',
        'playbook_id': 'renewal-safeguard',
        'account_name': account_name,
        'account_id': account_id,
        'report_generated_at': datetime.utcnow().isoformat(),
        'duration': '90 days',
        'status': 'Completed',
        'risk_assessment': risk_assessment,
        'value_activities': value_activities,
        'raci_matrix': raci,
        'outcomes_achieved': outcomes,
        'exit_criteria': exit_criteria,
        'executive_summary': f"Successfully completed Renewal Safeguard for {account_name}. Reduced renewal risk from 72 (High) to 28 (Low). Conducted executive business review, documented $2.3M annual ROI, and aligned strategic roadmap. Health score improved from 62 to 82 (+20 points). Secured renewal with 15% expansion ($67.5K additional ARR) and 2-year commitment. All 5 exit criteria met or exceeded.",
        'next_steps': [
            'Execute expansion implementation plan',
            'Schedule quarterly EBRs for ongoing alignment',
            'Monitor health score and usage trends',
            'Identify additional expansion opportunities',
            'Develop customer advocacy opportunity (case study, reference)'
        ]
    }


def generate_expansion_timing_report(execution_id, playbook_data, account_data=None):
    """Generate comprehensive Expansion Timing report"""
    
    if account_data:
        account_name = account_data.get('account_name', 'Selected Account')
        account_id = account_data.get('account_id')
    else:
        account_name = 'All Accounts'
        account_id = None
    
    # Expansion opportunities identified
    expansion_opportunities = [
        {
            'opportunity': 'Department expansion (Marketing → Sales)',
            'size': '$85K ARR',
            'probability': '85%',
            'timeline': 'Q1 2025',
            'champion': 'VP Sales',
            'status': 'Proposal submitted'
        },
        {
            'opportunity': 'Premium tier upgrade',
            'size': '$45K ARR',
            'probability': '90%',
            'timeline': 'Q4 2024',
            'champion': 'VP Operations',
            'status': 'Contract in review'
        },
        {
            'opportunity': 'Add-on module: Advanced Analytics',
            'size': '$32K ARR',
            'probability': '75%',
            'timeline': 'Q2 2025',
            'champion': 'CFO',
            'status': 'Discovery phase'
        }
    ]
    
    # Strategic triggers met
    triggers_met = [
        {'trigger': 'Health score > 80', 'current_value': 87, 'status': 'Met'},
        {'trigger': 'Adoption rate > 85%', 'current_value': '92%', 'status': 'Met'},
        {'trigger': 'Usage > 80% of plan limits', 'current_value': '88%', 'status': 'Met'},
        {'trigger': 'Budget window open', 'current_value': 'Q4 planning', 'status': 'Met'},
        {'trigger': 'Executive satisfaction high', 'current_value': '9.2/10', 'status': 'Met'}
    ]
    
    # Value propositions developed
    value_propositions = [
        {
            'title': 'Sales Department ROI Analysis',
            'summary': 'Projected $420K revenue impact for Sales team based on Marketing success',
            'key_metrics': ['65% increase in pipeline velocity', '28% higher win rates', '$12.5M additional closed revenue'],
            'investment': '$85K ARR',
            'roi': '495% first year'
        },
        {
            'title': 'Premium Tier Business Case',
            'summary': 'Advanced features enable 40% time savings and $180K annual cost reduction',
            'key_metrics': ['15 hours/week time savings', '3 FTE cost avoidance', 'Automation of 25 manual processes'],
            'investment': '$45K ARR',
            'roi': '400% first year'
        }
    ]
    
    # RACI Matrix
    raci = {
        'Opportunity Identification': {
            'CSM': 'Responsible',
            'Account Executive': 'Consulted',
            'Customer Success Ops': 'Consulted',
            'Customer Champion': 'Informed'
        },
        'Value Proposition Development': {
            'Solutions Engineer': 'Responsible',
            'CSM': 'Accountable',
            'Product Marketing': 'Consulted',
            'Customer Stakeholders': 'Consulted'
        },
        'Executive Presentation': {
            'Account Executive': 'Responsible',
            'CSM': 'Responsible',
            'VP Sales': 'Accountable',
            'Customer Executives': 'Accountable'
        },
        'Proposal & Negotiation': {
            'Account Executive': 'Accountable',
            'CSM': 'Responsible',
            'Sales Engineering': 'Consulted',
            'Customer Procurement': 'Consulted'
        },
        'Implementation Planning': {
            'CSM': 'Accountable',
            'Solutions Engineer': 'Responsible',
            'Customer IT': 'Responsible',
            'Customer Business Units': 'Consulted'
        }
    }
    
    # Outcomes achieved
    outcomes = {
        'expansion_pipeline': {
            'baseline': '$0',
            'current': '$162K ARR',
            'improvement': '+$162K pipeline',
            'target': 'Identify opportunities',
            'status': 'Exceeded'
        },
        'deals_closed': {
            'baseline': '0',
            'current': '1 closed ($45K)',
            'improvement': '+$45K ARR',
            'target': 'Present opportunities',
            'status': 'Exceeded'
        },
        'customer_satisfaction': {
            'baseline': '8.5/10',
            'current': '9.2/10',
            'improvement': '+0.7 points',
            'target': 'Maintain high satisfaction',
            'status': 'Achieved'
        },
        'expansion_rate': {
            'baseline': '0%',
            'current': '36% (planned)',
            'improvement': '+36%',
            'target': '> 20%',
            'status': 'Exceeded'
        },
        'strategic_alignment': {
            'baseline': 'Moderate',
            'current': 'High - Executive sponsorship',
            'improvement': 'C-level champions identified',
            'target': 'Executive alignment',
            'status': 'Achieved'
        }
    }
    
    # Exit criteria
    exit_criteria = [
        {'criteria': 'Expansion opportunities identified and qualified', 'status': 'Met', 'evidence': '3 opportunities totaling $162K ARR pipeline'},
        {'criteria': 'Value propositions developed and validated', 'status': 'Met', 'evidence': '2 comprehensive business cases with CFO validation'},
        {'criteria': 'Executive presentations completed', 'status': 'Met', 'evidence': 'Presented to VP Sales, VP Ops, and CFO with positive feedback'},
        {'criteria': 'At least 1 expansion deal in contracting', 'status': 'Met', 'evidence': 'Premium tier upgrade ($45K) closed, Sales expansion ($85K) in contracting'},
        {'criteria': 'Multi-year commitment secured', 'status': 'Met', 'evidence': '3-year commitment with built-in expansion milestones'}
    ]
    
    return {
        'execution_id': execution_id,
        'playbook_name': 'Expansion Timing',
        'playbook_id': 'expansion-timing',
        'account_name': account_name,
        'account_id': account_id,
        'report_generated_at': datetime.utcnow().isoformat(),
        'duration': '60 days',
        'status': 'Completed',
        'expansion_opportunities': expansion_opportunities,
        'triggers_met': triggers_met,
        'value_propositions': value_propositions,
        'raci_matrix': raci,
        'outcomes_achieved': outcomes,
        'exit_criteria': exit_criteria,
        'executive_summary': f"Successfully completed Expansion Timing playbook for {account_name}. Identified $162K ARR expansion pipeline across 3 opportunities. Closed $45K premium tier upgrade, $85K Sales department expansion in contracting. Health score 87, adoption 92%, usage 88% - all optimal expansion triggers met. Developed comprehensive ROI business cases validated by CFO. Secured 3-year commitment with expansion milestones. All 5 exit criteria met or exceeded.",
        'next_steps': [
            'Close Sales department expansion ($85K)',
            'Initiate implementation for closed deals',
            'Advance Analytics module discovery',
            'Monitor expansion milestones quarterly',
            'Develop next expansion opportunities (international, enterprise features)'
        ]
    }


@playbook_reports_api.route('/api/playbooks/executions/<execution_id>/report', methods=['GET'])
def get_execution_report(execution_id):
    """Generate or retrieve playbook execution report"""
    try:
        # Load reports from DB on first access
        load_reports_from_db()
        
        customer_id = get_customer_id()
        
        # Check if report already exists in cache
        if execution_id in _execution_reports:
            return jsonify({
                'status': 'success',
                'report': _execution_reports[execution_id],
                'cached': True
            })
        
        # Get execution data from playbook_execution_api
        from playbook_execution_api import _executions
        
        customer_executions = _executions.get(customer_id, {})
        execution = customer_executions.get(execution_id)
        
        if not execution:
            return jsonify({
                'status': 'error',
                'message': 'Execution not found'
            }), 404
        
        # Get account data if account_id provided
        account_data = None
        if execution.get('accountId'):
            account = Account.query.filter_by(
                account_id=execution['accountId'],
                customer_id=customer_id
            ).first()
            if account:
                account_data = {
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'revenue': float(account.revenue) if account.revenue else 0,
                    'industry': account.industry,
                    'region': account.region
                }
        elif execution.get('context', {}).get('accountName'):
            account_data = {
                'account_name': execution['context']['accountName'],
                'account_id': execution.get('context', {}).get('accountId')
            }
        
        # Generate report based on playbook type
        playbook_id = execution['playbookId']
        
        if playbook_id == 'voc-sprint':
            report = generate_voc_sprint_report(execution_id, execution, account_data)
        elif playbook_id == 'activation-blitz':
            report = generate_activation_blitz_report(execution_id, execution, account_data)
        elif playbook_id == 'sla-stabilizer':
            report = generate_sla_stabilizer_report(execution_id, execution, account_data)
        elif playbook_id == 'renewal-safeguard':
            report = generate_renewal_safeguard_report(execution_id, execution, account_data)
        elif playbook_id == 'expansion-timing':
            report = generate_expansion_timing_report(execution_id, execution, account_data)
        else:
            # Generic report for other playbooks
            report = {
                'execution_id': execution_id,
                'playbook_name': playbook_id,
                'playbook_id': playbook_id,
                'account_name': account_data.get('account_name') if account_data else 'All Accounts',
                'report_generated_at': datetime.utcnow().isoformat(),
                'status': execution['status'],
                'executive_summary': f"Playbook execution {execution_id} for {playbook_id}",
                'next_steps': []
            }
        
        # Cache the report in memory
        _execution_reports[execution_id] = report
        
        # Save to database
        save_report_to_db(execution_id, report, execution)
        
        return jsonify({
            'status': 'success',
            'report': report,
            'cached': False,
            'persisted': True
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_reports_api.route('/api/playbooks/reports', methods=['GET'])
def get_all_reports():
    """Get all playbook execution reports for a customer from database"""
    try:
        # Load reports from DB on first access
        load_reports_from_db()
        
        customer_id = get_customer_id()
        playbook_type = request.args.get('playbook_type')
        status = request.args.get('status')
        
        # Query reports from database
        query = PlaybookReport.query.filter_by(customer_id=customer_id)
        
        if playbook_type:
            query = query.filter_by(playbook_id=playbook_type)
        
        if status:
            query = query.filter_by(status=status)
        
        # Order by most recent first
        query = query.order_by(PlaybookReport.report_generated_at.desc())
        
        db_reports = query.all()
        
        # Group by account+playbook and keep only the latest
        execution_groups = {}
        for db_report in db_reports:
            combination_key = f"{db_report.account_id}_{db_report.account_name}_{db_report.playbook_id}"
            
            if combination_key not in execution_groups:
                execution_groups[combination_key] = db_report
            else:
                # Keep newer report (already sorted by desc, so first one is newest)
                pass
        
        # Build response
        reports = []
        for db_report in execution_groups.values():
            reports.append({
                'execution_id': db_report.execution_id,
                'playbook_name': db_report.playbook_id,
                'account_name': db_report.account_name,
                'account_id': db_report.account_id,
                'status': db_report.status,
                'started_at': db_report.started_at.isoformat() if db_report.started_at else None,
                'completed_at': db_report.completed_at.isoformat() if db_report.completed_at else None,
                'steps_completed': db_report.steps_completed or 0,
                'has_full_report': True,  # All DB reports have full reports
                'report_generated_at': db_report.report_generated_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'reports': reports,
            'total': len(reports),
            'total_in_database': len(db_reports),
            'deduplicated': len(db_reports) - len(reports),
            'source': 'database'
        })
    
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_reports_api.route('/api/playbooks/reports/export/<execution_id>', methods=['GET'])
def export_report(execution_id):
    """Export playbook report as downloadable format"""
    try:
        # Get the report
        if execution_id not in _execution_reports:
            return jsonify({
                'status': 'error',
                'message': 'Report not found. Generate report first.'
            }), 404
        
        report = _execution_reports[execution_id]
        
        # Format as markdown for download
        markdown = f"""# {report['playbook_name']} - Execution Report

**Account**: {report['account_name']}  
**Execution ID**: {execution_id}  
**Generated**: {report['report_generated_at']}  
**Status**: {report['status']}

## Executive Summary

{report['executive_summary']}

## RACI Matrix

| Activity | CSM | Product Manager | Support Lead | Executive Sponsor |
|----------|-----|-----------------|--------------|-------------------|
"""
        
        if 'raci_matrix' in report:
            for activity, roles in report['raci_matrix'].items():
                row = f"| {activity} |"
                for role in ['CSM', 'Product Manager', 'Support Lead', 'Executive Sponsor']:
                    row += f" {roles.get(role, '-')} |"
                markdown += row + "\n"
        
        markdown += "\n## Outcomes Achieved\n\n"
        if 'outcomes_achieved' in report:
            for outcome_name, outcome_data in report['outcomes_achieved'].items():
                markdown += f"### {outcome_name.replace('_', ' ').title()}\n"
                markdown += f"- Baseline: {outcome_data['baseline']}\n"
                markdown += f"- Current: {outcome_data['current']}\n"
                markdown += f"- Improvement: {outcome_data['improvement']}\n"
                markdown += f"- Status: **{outcome_data['status']}**\n\n"
        
        markdown += "\n## Exit Criteria\n\n"
        if 'exit_criteria' in report:
            for criterion in report['exit_criteria']:
                markdown += f"- [{'x' if criterion['status'] == 'Met' else ' '}] {criterion['criteria']}\n"
                markdown += f"  - Evidence: {criterion['evidence']}\n"
        
        return jsonify({
            'status': 'success',
            'markdown': markdown,
            'report': report
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

