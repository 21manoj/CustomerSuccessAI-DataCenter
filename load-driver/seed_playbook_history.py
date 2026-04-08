#!/usr/bin/env python3
"""
Seed realistic playbook execution history for a customer via MCP tools.

Run AFTER manifest data is loaded (accounts, health scores, context graph exist).
Calls execute_playbook() → close_playbook() MCP functions which:
  1. Create PlaybookExecutionV2 records with health/ARR context
  2. Auto-compute revenue protected via churn probability model
  3. Create OUTCOME nodes in context graph with RESULTED_IN edges
  4. Complete the Signal → Decision → Outcome causal chain

Usage:
    # Inside Docker container (recommended)
    docker exec cspulse-platform python3 /app/load-driver/seed_playbook_history.py --customer-id 251

    # Dry run
    docker exec cspulse-platform python3 /app/load-driver/seed_playbook_history.py --customer-id 251 --dry-run

Flow: manifest → upload → process_data → system alive → seed_playbook_history
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

# Add backend to path for MCP function imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kpi-dashboard', 'backend'))


# ── Playbook scenarios keyed by health condition ──
PLAYBOOK_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-05',
        'triggered_by': 'health_drop',
        'outcome': 'resolved',
        'health_improvement': (8, 15),
        'hours_multiplier': (0.75, 1.15),
        'outcome_notes': 'Intensive health monitoring identified root causes. Stabilization plan executed. KPI trajectory improving.',
    },
    {
        'condition': lambda h, arc: h < 50 and arc in ('champion_loss', 'stakeholder_exodus'),
        'playbook_id': 'PB-06',
        'triggered_by': 'signal_analyst',
        'outcome': 'resolved',
        'health_improvement': (5, 12),
        'hours_multiplier': (0.80, 1.10),
        'outcome_notes': 'Stakeholder re-engagement completed. New executive sponsor identified. Relationship health improving.',
    },
    {
        'condition': lambda h, arc: 35 <= h < 50,
        'playbook_id': 'PB-02',
        'triggered_by': 'csm_manual',
        'outcome': 'resolved',
        'health_improvement': (6, 10),
        'hours_multiplier': (0.80, 1.20),
        'outcome_notes': 'Hardware reliability issues addressed. RMA rate reduced. Proactive monitoring in place.',
    },
    {
        'condition': lambda h, arc: 50 <= h < 70,
        'playbook_id': 'PB-03',
        'triggered_by': 'csm_manual',
        'outcome': 'resolved',
        'health_improvement': (4, 8),
        'hours_multiplier': (0.85, 1.10),
        'outcome_notes': 'GPU utilization improved through workload rebalancing. Customer seeing better ROI on compute spend.',
    },
]

# Some escalations (not everything succeeds)
ESCALATION_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-01',
        'triggered_by': 'health_drop',
        'outcome': 'escalated',
        'health_improvement': (0, 3),
        'hours_multiplier': (0.70, 0.90),
        'outcome_notes': 'Initial intervention insufficient. Escalated to VP CS for executive-level engagement.',
    },
]


def seed_playbook_history(customer_id: int, seed: int = 42, dry_run: bool = False):
    """Seed playbook executions via MCP execute_playbook → close_playbook."""

    random.seed(seed)

    from app_v3_minimal import app
    with app.app_context():
        from models import db, Account, HealthScore, PlaybookExecutionV2, ContextNode

        # Import MCP functions (they run inside Flask context)
        from mcp_server.cs_pulse_revenue import execute_playbook, close_playbook

        # Check for existing executions
        existing = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).count()
        if existing > 0:
            print(f"WARNING: {existing} executions already exist for customer {customer_id}. Skipping.")
            print(f"To re-seed: DELETE FROM playbook_executions_v2 WHERE customer_id = {customer_id};")
            return

        # Get accounts with latest health scores
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            print(f"No accounts found for customer {customer_id}")
            return

        print(f"Customer {customer_id}: {len(accounts)} accounts")

        account_health = {}
        for acct in accounts:
            latest = (
                HealthScore.query
                .filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.desc())
                .first()
            )
            if latest:
                # Get arc_type from context graph
                arc_type = 'unknown'
                try:
                    arc_node = (
                        ContextNode.query
                        .filter_by(account_id=acct.account_id, node_type='SIGNAL', source='system')
                        .filter(ContextNode.title.ilike('%Arc Detected%'))
                        .first()
                    )
                    if arc_node and arc_node.properties:
                        props = arc_node.properties if isinstance(arc_node.properties, dict) else json.loads(arc_node.properties)
                        arc_type = props.get('arc_type', 'unknown')
                except Exception:
                    pass

                account_health[acct.account_id] = {
                    'account': acct,
                    'health': float(latest.health_score),
                    'arc_type': arc_type,
                }

        executions_created = 0
        now = datetime.utcnow()

        for acct_id, info in account_health.items():
            acct = info['account']
            health = info['health']
            arc_type = info['arc_type']

            print(f"\n  {acct.account_name}: health={health:.1f}, ARR=${float(acct.revenue or 0)/1e6:.1f}M, arc={arc_type}")

            # Match scenarios
            matched = []
            for scenario in PLAYBOOK_SCENARIOS:
                if scenario['condition'](health, arc_type):
                    matched.append(scenario)
            if health < 35:
                for esc in ESCALATION_SCENARIOS:
                    if esc['condition'](health, arc_type):
                        matched.append(esc)
                        break

            if not matched:
                print(f"    No playbook match (health {health:.0f} — no applicable scenario)")
                continue

            for i, scenario in enumerate(matched):
                pb_id = scenario['playbook_id']

                if dry_run:
                    h_min, h_max = scenario['health_improvement']
                    improvement = random.uniform(h_min, h_max)
                    print(f"    [DRY RUN] {pb_id}: {scenario['outcome']}, health {health:.0f}→{health + improvement:.0f}")
                    executions_created += 1
                    continue

                # ── Step 1: Execute playbook via MCP function ──
                try:
                    exec_result = execute_playbook(
                        customer_id=customer_id,
                        account_id=acct_id,
                        playbook_id=pb_id,
                        triggered_by=scenario['triggered_by'],
                    )
                except Exception as e:
                    print(f"    ERROR executing {pb_id}: {e}")
                    continue

                execution_id = exec_result.get('execution_id')
                if not execution_id:
                    print(f"    ERROR: No execution_id returned for {pb_id}")
                    continue

                # ── Step 2: Backdate the trigger timestamp ──
                days_ago = random.randint(45, 60) if i == 0 else random.randint(15, 30)
                triggered_at = now - timedelta(days=days_ago)
                duration_days = random.randint(14, 30)

                pe = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
                if pe:
                    pe.triggered_at = triggered_at
                    pe.phase_2_at = triggered_at + timedelta(days=max(7, duration_days // 3))
                    pe.phase_3_at = triggered_at + timedelta(days=max(14, duration_days * 2 // 3))
                    db.session.commit()

                # ── Step 3: Compute health at close ──
                h_min, h_max = scenario['health_improvement']
                improvement = random.uniform(h_min, h_max)
                health_at_close = min(100, health + improvement)

                # CSM hours actual
                m_min, m_max = scenario['hours_multiplier']
                csm_hours_actual = round((pe.csm_hours_planned or 64) * random.uniform(m_min, m_max), 1)

                # ── Step 4: Close playbook via MCP function ──
                try:
                    close_result = close_playbook(
                        customer_id=customer_id,
                        execution_id=execution_id,
                        outcome=scenario['outcome'],
                        outcome_notes=scenario['outcome_notes'],
                        health_at_close=round(health_at_close, 2),
                        csm_hours_actual=csm_hours_actual,
                        # revenue_protected=None → auto-computed from churn model
                    )
                except Exception as e:
                    print(f"    ERROR closing {pb_id}: {e}")
                    continue

                # ── Step 5: Backdate the close timestamp ──
                closed_at = triggered_at + timedelta(days=duration_days)
                if closed_at > now:
                    closed_at = now - timedelta(days=random.randint(1, 5))

                pe = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
                if pe:
                    pe.closed_at = closed_at
                    db.session.commit()

                rev_protected = close_result.get('revenue_protected', 0)
                roi = close_result.get('realized_roi_pct', 0)
                cost = close_result.get('total_cost', 0)

                print(f"    {pb_id}: {scenario['outcome']}, "
                      f"health {health:.0f}→{health_at_close:.0f} (+{improvement:.0f}), "
                      f"${rev_protected/1e3:.0f}K protected, ROI {roi:.0f}%, "
                      f"cost ${cost/1e3:.1f}K, {days_ago}d ago"
                      f"{' [+CG OUTCOME]' if close_result.get('context_graph_node_created') else ''}")

                executions_created += 1

        if not dry_run and executions_created > 0:
            resolved = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='resolved').count()
            escalated = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='escalated').count()
            total_protected = db.session.query(db.func.sum(PlaybookExecutionV2.revenue_protected)).filter_by(customer_id=customer_id).scalar() or 0
            total_cost = db.session.query(db.func.sum(PlaybookExecutionV2.total_cost)).filter_by(customer_id=customer_id).scalar() or 0

            # Count CG outcome nodes created
            cg_outcomes = ContextNode.query.filter_by(
                customer_id=customer_id, node_type='OUTCOME', node_subtype='playbook_outcome'
            ).count()

            print(f"\nCreated {executions_created} playbook executions for customer {customer_id}")
            print(f"  Resolved: {resolved}, Escalated: {escalated}")
            print(f"  Revenue Protected: ${total_protected/1e6:.2f}M")
            print(f"  Total Cost: ${total_cost/1e3:.1f}K")
            print(f"  Portfolio ROI: {(total_protected / total_cost * 100):.0f}%" if total_cost > 0 else "  Portfolio ROI: N/A")
            print(f"  Context Graph OUTCOME nodes created: {cg_outcomes}")
        elif dry_run:
            print(f"\n[DRY RUN] Would create {executions_created} playbook executions")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed playbook execution history via MCP tools')
    parser.add_argument('--customer-id', type=int, required=True, help='Customer ID to seed')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without writing')
    args = parser.parse_args()

    seed_playbook_history(args.customer_id, seed=args.seed, dry_run=args.dry_run)
