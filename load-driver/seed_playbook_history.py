#!/usr/bin/env python3
"""
Seed realistic playbook execution history for a customer.

Run AFTER manifest data is loaded (accounts, health scores, context graph exist).
Creates PlaybookExecutionV2 records with realistic timelines, CSM hours,
health improvements, and revenue attribution.

Usage:
    # Against local server
    python3 seed_playbook_history.py --customer-id 251 --base-url http://localhost:5059

    # Against EC2
    python3 seed_playbook_history.py --customer-id 251 --base-url https://d2oqfugrb2ltg9.cloudfront.net

    # Dry run (show what would be created)
    python3 seed_playbook_history.py --customer-id 251 --dry-run

This script calls the platform API directly (not MCP) to insert PlaybookExecutionV2
records with backdated timestamps, simulating 2-3 months of operational history.
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

# Add backend to path for direct DB access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kpi-dashboard', 'backend'))


# ── Playbook templates keyed by health condition ──
PLAYBOOK_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-05',
        'playbook_name': 'Health Monitoring',
        'triggered_by': 'health_drop',
        'csm_hours_planned': 64,
        'outcome': 'resolved',
        'health_improvement': (8, 15),  # health improves by 8-15 points
        'outcome_notes': 'Intensive health monitoring identified root causes. Stabilization plan executed. KPI trajectory improving.',
        'action_log': [
            {'action': 'Account health review with CSM', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'Root cause analysis on declining pillars', 'owner': 'CS Ops', 'status': 'completed'},
            {'action': 'Executive sponsor briefing', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'Remediation plan presented to customer', 'owner': 'CSM + TAM', 'status': 'completed'},
        ],
    },
    {
        'condition': lambda h, arc: h < 50 and arc in ('champion_loss', 'stakeholder_exodus'),
        'playbook_id': 'PB-06',
        'playbook_name': 'Customer Engagement',
        'triggered_by': 'signal_analyst',
        'csm_hours_planned': 72,
        'outcome': 'resolved',
        'health_improvement': (5, 12),
        'outcome_notes': 'Stakeholder re-engagement completed. New executive sponsor identified and onboarded. Relationship health improving.',
        'action_log': [
            {'action': 'Stakeholder mapping refresh', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'New champion identification', 'owner': 'CSM + AE', 'status': 'completed'},
            {'action': 'Executive alignment meeting', 'owner': 'VP CS', 'status': 'completed'},
            {'action': 'QBR rescheduled with new stakeholders', 'owner': 'CSM', 'status': 'completed'},
        ],
    },
    {
        'condition': lambda h, arc: 35 <= h < 50,
        'playbook_id': 'PB-02',
        'playbook_name': 'RMA Prevention',
        'triggered_by': 'csm_manual',
        'csm_hours_planned': 88,
        'outcome': 'resolved',
        'health_improvement': (6, 10),
        'outcome_notes': 'Hardware reliability issues addressed. RMA rate reduced. Proactive monitoring in place.',
        'action_log': [
            {'action': 'RMA batch analysis and triage', 'owner': 'TAM', 'status': 'completed'},
            {'action': 'Firmware update and cooling optimization', 'owner': 'Platform Eng', 'status': 'completed'},
            {'action': 'Component replacement for affected nodes', 'owner': 'Field Ops', 'status': 'completed'},
            {'action': 'Monitoring dashboard and alerting setup', 'owner': 'CS Ops', 'status': 'completed'},
        ],
    },
    {
        'condition': lambda h, arc: 50 <= h < 70,
        'playbook_id': 'PB-03',
        'playbook_name': 'GPU Optimization',
        'triggered_by': 'csm_manual',
        'csm_hours_planned': 80,
        'outcome': 'resolved',
        'health_improvement': (4, 8),
        'outcome_notes': 'GPU utilization improved through workload rebalancing and scheduling optimization. Customer seeing better ROI on compute spend.',
        'action_log': [
            {'action': 'Workload profiling and bottleneck analysis', 'owner': 'TAM', 'status': 'completed'},
            {'action': 'Scheduling policy optimization', 'owner': 'Platform Eng', 'status': 'completed'},
            {'action': 'Customer training on best practices', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'Performance validation and benchmarking', 'owner': 'TAM', 'status': 'completed'},
        ],
    },
]

# Second wave — some escalated (realistic: not everything succeeds)
ESCALATION_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-01',
        'playbook_name': 'Deployment Acceleration',
        'triggered_by': 'health_drop',
        'csm_hours_planned': 72,
        'outcome': 'escalated',
        'health_improvement': (0, 3),  # minimal improvement
        'outcome_notes': 'Initial intervention insufficient. Escalated to VP CS for executive-level engagement. Customer requesting dedicated TAM.',
        'action_log': [
            {'action': 'Deployment assessment', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'Bottleneck removal attempt', 'owner': 'TAM', 'status': 'completed'},
            {'action': 'Customer escalation received', 'owner': 'CSM', 'status': 'completed'},
            {'action': 'VP CS executive review', 'owner': 'VP CS', 'status': 'in_progress'},
        ],
    },
]


def seed_playbook_history(customer_id: int, seed: int = 42, dry_run: bool = False):
    """Seed PlaybookExecutionV2 records for a customer's accounts."""

    random.seed(seed)

    from app_v3_minimal import app
    with app.app_context():
        from models import db, Account, HealthScore, PlaybookExecutionV2

        # Get accounts with latest health scores
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            print(f"No accounts found for customer {customer_id}")
            return

        print(f"Customer {customer_id}: {len(accounts)} accounts")

        # Get latest health per account
        account_health = {}
        for acct in accounts:
            latest = (
                HealthScore.query
                .filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.desc())
                .first()
            )
            if latest:
                account_health[acct.account_id] = {
                    'account': acct,
                    'health': float(latest.health_score),
                    'month': latest.measurement_month,
                }

        # Check for existing executions
        existing = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).count()
        if existing > 0:
            print(f"  WARNING: {existing} executions already exist. Skipping to avoid duplicates.")
            print(f"  To re-seed, delete existing: DELETE FROM playbook_executions_v2 WHERE customer_id = {customer_id};")
            return

        executions_created = 0
        now = datetime.utcnow()

        for acct_id, info in account_health.items():
            acct = info['account']
            health = info['health']
            arr = float(acct.revenue or 0)
            arc_type = 'unknown'

            # Try to get arc_type from context graph
            try:
                from models import ContextNode
                arc_node = (
                    ContextNode.query
                    .filter_by(account_id=acct_id, node_type='SIGNAL', source='system')
                    .filter(ContextNode.title.ilike('%Arc Detected%'))
                    .first()
                )
                if arc_node and arc_node.properties:
                    props = arc_node.properties if isinstance(arc_node.properties, dict) else json.loads(arc_node.properties)
                    arc_type = props.get('arc_type', 'unknown')
            except Exception:
                pass

            print(f"\n  {acct.account_name}: health={health:.1f}, ARR=${arr/1e6:.1f}M, arc={arc_type}")

            # Match playbook scenarios
            matched = []
            for scenario in PLAYBOOK_SCENARIOS:
                if scenario['condition'](health, arc_type):
                    matched.append(scenario)
            # Add one escalation for the worst account
            if health < 35:
                for esc in ESCALATION_SCENARIOS:
                    if esc['condition'](health, arc_type):
                        matched.append(esc)
                        break

            if not matched:
                print(f"    No playbook match (health too high or no applicable scenario)")
                continue

            for i, scenario in enumerate(matched):
                # Stagger execution dates: first playbook 45-60 days ago, second 20-30 days ago
                days_ago = random.randint(45, 60) if i == 0 else random.randint(15, 30)
                triggered_at = now - timedelta(days=days_ago)
                duration_days = random.randint(14, 30)
                closed_at = triggered_at + timedelta(days=duration_days)

                # Don't close future executions
                if closed_at > now:
                    closed_at = now - timedelta(days=random.randint(1, 5))

                # Health improvement
                h_min, h_max = scenario['health_improvement']
                health_improvement = random.uniform(h_min, h_max)
                health_at_close = min(100, health + health_improvement)

                # CSM hours (actual = planned * 0.8-1.2)
                hours_planned = scenario['csm_hours_planned']
                hours_actual = round(hours_planned * random.uniform(0.75, 1.15), 1)
                exec_hours = round(random.uniform(2, 8), 1)
                hourly_rate = 85.0
                total_cost = round((hours_actual + exec_hours) * hourly_rate * 1.20, 2)  # 20% overhead

                # Revenue attribution (churn probability model)
                def health_to_churn(h):
                    if h < 50: return 0.35 + (50 - h) * 0.002
                    elif h < 70: return 0.15 + (70 - h) * 0.005
                    else: return 0.03 + (100 - h) * 0.0017

                churn_before = health_to_churn(health)
                churn_after = health_to_churn(health_at_close)
                churn_reduction = max(0, churn_before - churn_after)
                revenue_protected = round(churn_reduction * arr * 0.50, 2)  # 50% attribution

                # ROI
                realized_roi = round((revenue_protected / total_cost) * 100, 1) if total_cost > 0 else 0
                nrr_impact = round((revenue_protected / arr) * 100, 2) if arr > 0 else 0

                # Health status
                def classify(h):
                    if h >= 70: return 'healthy'
                    elif h >= 50: return 'at_risk'
                    return 'critical'

                # Action log with dates
                action_log = []
                for j, action in enumerate(scenario['action_log']):
                    action_date = triggered_at + timedelta(days=int(duration_days * (j + 1) / (len(scenario['action_log']) + 1)))
                    action_log.append({
                        'date': action_date.strftime('%Y-%m-%d'),
                        'action': action['action'],
                        'owner': action['owner'],
                        'status': action['status'],
                        'outcome': 'Completed successfully' if action['status'] == 'completed' else 'In progress',
                    })

                exec_id = f"exec-{scenario['playbook_id']}-{acct_id}-{random.randint(10000, 99999)}"

                print(f"    {scenario['playbook_id']} ({scenario['playbook_name']}): "
                      f"{scenario['outcome']}, health {health:.0f}→{health_at_close:.0f} (+{health_improvement:.0f}), "
                      f"${revenue_protected/1e3:.0f}K protected, ROI {realized_roi:.0f}%, "
                      f"cost ${total_cost/1e3:.1f}K, {days_ago}d ago")

                if dry_run:
                    executions_created += 1
                    continue

                execution = PlaybookExecutionV2(
                    execution_id=exec_id,
                    customer_id=customer_id,
                    account_id=acct_id,
                    playbook_id=scenario['playbook_id'],
                    playbook_name=scenario['playbook_name'],
                    triggered_by=scenario['triggered_by'],
                    arc_type=arc_type,
                    status='completed',
                    phase='secure',
                    csm_hours_planned=hours_planned,
                    csm_hours_actual=hours_actual,
                    exec_hours=exec_hours,
                    csm_hourly_rate=hourly_rate,
                    total_cost=total_cost,
                    health_at_trigger=round(health, 2),
                    health_status_at_trigger=classify(health),
                    arr_at_trigger=arr,
                    health_at_close=round(health_at_close, 2),
                    health_status_at_close=classify(health_at_close),
                    health_delta=round(health_improvement, 2),
                    revenue_protected=revenue_protected,
                    revenue_expanded=0,
                    revenue_lost=0,
                    nrr_impact_pct=nrr_impact,
                    outcome=scenario['outcome'],
                    outcome_notes=scenario['outcome_notes'],
                    realized_roi_pct=realized_roi,
                    projected_roi_pct=round(realized_roi * random.uniform(0.7, 1.1), 1),
                    roi_variance_pct=round(random.uniform(-15, 25), 1),
                    actions_planned=len(scenario['action_log']),
                    actions_completed=sum(1 for a in scenario['action_log'] if a['status'] == 'completed'),
                    action_log=action_log,
                    triggered_at=triggered_at,
                    phase_2_at=triggered_at + timedelta(days=max(7, duration_days // 3)),
                    phase_3_at=triggered_at + timedelta(days=max(14, duration_days * 2 // 3)),
                    closed_at=closed_at,
                )
                db.session.add(execution)
                executions_created += 1

        if not dry_run:
            db.session.commit()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Created {executions_created} playbook executions for customer {customer_id}")
        if not dry_run:
            # Summary stats
            resolved = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='resolved').count()
            escalated = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='escalated').count()
            total_protected = db.session.query(db.func.sum(PlaybookExecutionV2.revenue_protected)).filter_by(customer_id=customer_id).scalar() or 0
            total_cost = db.session.query(db.func.sum(PlaybookExecutionV2.total_cost)).filter_by(customer_id=customer_id).scalar() or 0
            print(f"  Resolved: {resolved}, Escalated: {escalated}")
            print(f"  Total Revenue Protected: ${total_protected/1e6:.2f}M")
            print(f"  Total Cost: ${total_cost/1e3:.1f}K")
            print(f"  Portfolio ROI: {(total_protected / total_cost * 100):.0f}%" if total_cost > 0 else "  Portfolio ROI: N/A")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed playbook execution history')
    parser.add_argument('--customer-id', type=int, required=True, help='Customer ID to seed')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without writing')
    args = parser.parse_args()

    seed_playbook_history(args.customer_id, seed=args.seed, dry_run=args.dry_run)
