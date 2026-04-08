#!/usr/bin/env python3
"""
Seed realistic playbook execution history via Flask API endpoints.

Run AFTER manifest data is loaded (accounts, health scores, context graph exist).
Uses Flask test client to call MCP execute_playbook → close_playbook internally,
which creates PlaybookExecutionV2 records + context graph OUTCOME nodes.

Usage:
    # Inside Docker container
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kpi-dashboard', 'backend'))


# ── Playbook scenarios ──
PLAYBOOK_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-05',
        'triggered_by': 'health_drop',
        'outcome': 'resolved',
        'health_improvement': (8, 15),
        'hours_mult': (0.75, 1.15),
        'notes': 'Intensive health monitoring identified root causes. Stabilization plan executed. KPI trajectory improving.',
    },
    {
        'condition': lambda h, arc: h < 50 and arc in ('champion_loss', 'stakeholder_exodus'),
        'playbook_id': 'PB-06',
        'triggered_by': 'signal_analyst',
        'outcome': 'resolved',
        'health_improvement': (5, 12),
        'hours_mult': (0.80, 1.10),
        'notes': 'Stakeholder re-engagement completed. New executive sponsor identified. Relationship health improving.',
    },
    {
        'condition': lambda h, arc: 35 <= h < 50,
        'playbook_id': 'PB-02',
        'triggered_by': 'csm_manual',
        'outcome': 'resolved',
        'health_improvement': (6, 10),
        'hours_mult': (0.80, 1.20),
        'notes': 'Hardware reliability issues addressed. RMA rate reduced. Proactive monitoring in place.',
    },
    {
        'condition': lambda h, arc: 50 <= h < 70,
        'playbook_id': 'PB-03',
        'triggered_by': 'csm_manual',
        'outcome': 'resolved',
        'health_improvement': (4, 8),
        'hours_mult': (0.85, 1.10),
        'notes': 'GPU utilization improved through workload rebalancing. Customer seeing better compute ROI.',
    },
]

ESCALATION_SCENARIOS = [
    {
        'condition': lambda h, arc: h < 35,
        'playbook_id': 'PB-01',
        'triggered_by': 'health_drop',
        'outcome': 'escalated',
        'health_improvement': (0, 3),
        'hours_mult': (0.70, 0.90),
        'notes': 'Initial intervention insufficient. Escalated to VP CS for executive-level engagement.',
    },
]


def _call_mcp_execute(app, customer_id, account_id, playbook_id, triggered_by):
    """Call execute_playbook MCP function inside Flask context."""
    from mcp_server.cs_pulse_revenue import execute_playbook
    return execute_playbook(
        customer_id=customer_id,
        account_id=account_id,
        playbook_id=playbook_id,
        triggered_by=triggered_by,
    )


def _call_mcp_close(app, customer_id, execution_id, outcome, notes, health_at_close, csm_hours):
    """Call close_playbook MCP function inside Flask context."""
    from mcp_server.cs_pulse_revenue import close_playbook
    return close_playbook(
        customer_id=customer_id,
        execution_id=execution_id,
        outcome=outcome,
        outcome_notes=notes,
        health_at_close=health_at_close,
        csm_hours_actual=csm_hours,
    )


def seed_playbook_history(customer_id: int, seed: int = 42, dry_run: bool = False):
    """Seed playbook executions via MCP functions called inside Flask app context."""
    random.seed(seed)

    from app_v3_minimal import app

    with app.app_context():
        from models import db, Account, HealthScore, PlaybookExecutionV2, ContextNode

        # Idempotent: skip if already seeded
        existing = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).count()
        if existing > 0:
            print(f"WARNING: {existing} executions already exist for customer {customer_id}. Skipping.")
            print(f"To re-seed: DELETE FROM playbook_executions_v2 WHERE customer_id = {customer_id};")
            return

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            print(f"No accounts found for customer {customer_id}")
            return

        print(f"Customer {customer_id}: {len(accounts)} accounts")

        # Build account info with health + arc type
        account_info = {}
        for acct in accounts:
            latest_hs = (
                HealthScore.query.filter_by(account_id=acct.account_id)
                .order_by(HealthScore.measurement_month.desc()).first()
            )
            if not latest_hs:
                continue

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

            account_info[acct.account_id] = {
                'account': acct,
                'health': float(latest_hs.health_score),
                'arc': arc_type,
            }

        now = datetime.utcnow()
        created = 0
        cg_nodes = 0

        for acct_id, info in account_info.items():
            acct = info['account']
            health = info['health']
            arc = info['arc']

            print(f"\n  {acct.account_name}: health={health:.1f}, ARR=${float(acct.revenue or 0)/1e6:.1f}M, arc={arc}")

            # Match scenarios
            matched = []
            for s in PLAYBOOK_SCENARIOS:
                if s['condition'](health, arc):
                    matched.append(s)
            if health < 35:
                for s in ESCALATION_SCENARIOS:
                    if s['condition'](health, arc):
                        matched.append(s)
                        break

            if not matched:
                print(f"    No playbook match")
                continue

            for i, scenario in enumerate(matched):
                h_min, h_max = scenario['health_improvement']
                improvement = random.uniform(h_min, h_max)
                health_at_close = min(100, health + improvement)
                m_min, m_max = scenario['hours_mult']

                if dry_run:
                    print(f"    [DRY RUN] {scenario['playbook_id']}: {scenario['outcome']}, "
                          f"health {health:.0f}→{health_at_close:.0f}")
                    created += 1
                    continue

                # Step 1: Execute
                try:
                    exec_result = _call_mcp_execute(
                        app, customer_id, acct_id,
                        scenario['playbook_id'], scenario['triggered_by']
                    )
                    execution_id = exec_result.get('execution_id')
                    if not execution_id:
                        print(f"    ERROR: No execution_id for {scenario['playbook_id']}")
                        continue
                except Exception as e:
                    print(f"    ERROR execute: {e}")
                    continue

                # Step 2: Backdate trigger
                days_ago = random.randint(45, 60) if i == 0 else random.randint(15, 30)
                duration = random.randint(14, 30)
                triggered_at = now - timedelta(days=days_ago)

                pe = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
                if pe:
                    pe.triggered_at = triggered_at
                    pe.phase_2_at = triggered_at + timedelta(days=max(7, duration // 3))
                    pe.phase_3_at = triggered_at + timedelta(days=max(14, duration * 2 // 3))
                    db.session.commit()

                # Step 3: Close with outcome
                csm_hours = round((pe.csm_hours_planned or 64) * random.uniform(m_min, m_max), 1)
                try:
                    close_result = _call_mcp_close(
                        app, customer_id, execution_id,
                        scenario['outcome'], scenario['notes'],
                        round(health_at_close, 2), csm_hours
                    )
                except Exception as e:
                    print(f"    ERROR close: {e}")
                    continue

                # Step 4: Backdate close
                closed_at = triggered_at + timedelta(days=duration)
                if closed_at > now:
                    closed_at = now - timedelta(days=random.randint(1, 5))
                pe = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
                if pe:
                    pe.closed_at = closed_at
                    db.session.commit()

                rev = close_result.get('revenue_protected', 0)
                roi = close_result.get('realized_roi_pct', 0)
                cost = close_result.get('total_cost', 0)
                cg = close_result.get('context_graph_node_id')

                print(f"    {scenario['playbook_id']}: {scenario['outcome']}, "
                      f"health {health:.0f}→{health_at_close:.0f} (+{improvement:.0f}), "
                      f"${rev/1e3:.0f}K protected, ROI {roi:.0f}%, cost ${cost/1e3:.1f}K, "
                      f"{days_ago}d ago{' [+CG]' if cg else ''}")

                created += 1
                if cg:
                    cg_nodes += 1

        # Summary
        if not dry_run and created > 0:
            resolved = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='resolved').count()
            escalated = PlaybookExecutionV2.query.filter_by(customer_id=customer_id, outcome='escalated').count()
            total_protected = db.session.query(
                db.func.sum(PlaybookExecutionV2.revenue_protected)
            ).filter_by(customer_id=customer_id).scalar() or 0
            total_cost = db.session.query(
                db.func.sum(PlaybookExecutionV2.total_cost)
            ).filter_by(customer_id=customer_id).scalar() or 0

            print(f"\nCreated {created} playbook executions for customer {customer_id}")
            print(f"  Resolved: {resolved}, Escalated: {escalated}")
            print(f"  Revenue Protected: ${total_protected/1e6:.2f}M")
            print(f"  Total Cost: ${total_cost/1e3:.1f}K")
            if total_cost > 0:
                print(f"  Portfolio ROI: {(total_protected / total_cost * 100):.0f}%")
            print(f"  Context Graph nodes: {cg_nodes}")
        elif dry_run:
            print(f"\n[DRY RUN] Would create {created} playbook executions")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed playbook history via MCP functions')
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    seed_playbook_history(args.customer_id, seed=args.seed, dry_run=args.dry_run)
