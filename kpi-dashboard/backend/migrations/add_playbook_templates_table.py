#!/usr/bin/env python3
"""
Migration: Create playbook_templates and playbook_step_logs tables
==================================================================

Playbook Template Editor — customer-editable playbook templates with RACI
matrix and multi-backend execution (Claude Skills, n8n, manual, API).

Tables created:
  - playbook_templates : Per-customer playbook definitions with steps, RACI, triggers
  - playbook_step_logs : Step-level execution logs for RAG learning

After table creation, seeds 5 system playbooks for each existing customer.

Usage:
    python -m migrations.add_playbook_templates_table

Rollback:
    DROP TABLE IF EXISTS playbook_step_logs;
    DROP TABLE IF EXISTS playbook_templates;
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 5 system playbook seeds (cross-vertical where possible)
SYSTEM_PLAYBOOKS = [
    {
        'playbook_id': 'PB-SYS-01',
        'name': 'Emergency Retention',
        'description': 'Immediate intervention when account health drops to critical. Triage root cause, build action plan, execute, and re-score.',
        'trigger_conditions': [{'kpi_code': 'OVERALL_HEALTH', 'operator': '<', 'value': 50}],
        'trigger_kpis': ['OVERALL_HEALTH'],
        'trigger_logic': 'OR',
        'steps': [
            {'id': 'S1', 'name': 'Health triage & root cause', 'description': 'Analyze pillar scores, recent signals, and stakeholder changes', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Product'], 'informed': ['CRO'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'health-triage'}},
            {'id': 'S2', 'name': 'Action plan with RACI', 'description': 'Build prioritized action plan with owners and deadlines', 'estimated_hours': 4,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': ['CFO'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'action-plan-builder'}},
            {'id': 'S3', 'name': 'Execute interventions', 'description': 'Run top actions — calls, escalations, support pods', 'estimated_hours': 32,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Support'], 'informed': [],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S4', 'name': 'Re-score & close', 'description': 'Re-measure health score and close or escalate', 'estimated_hours': 4,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': ['CRO'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'health-rescore'}},
        ],
        'estimated_hours': 48, 'estimated_duration_days': 14, 'automation_level': 'partial', 'vertical': None,
    },
    {
        'playbook_id': 'PB-SYS-02',
        'name': 'Deployment Acceleration',
        'description': 'Accelerate time-to-first-value for new deployments by removing bottlenecks and tracking milestones.',
        'trigger_conditions': [{'kpi_code': 'P1-KPI1', 'operator': '>', 'value': 20}],
        'trigger_kpis': ['P1-KPI1'],
        'trigger_logic': 'OR',
        'steps': [
            {'id': 'S1', 'name': 'Kickoff & bottleneck analysis', 'description': 'Stakeholder alignment, identify blockers', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Solutions Architect'], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'deployment-audit'}},
            {'id': 'S2', 'name': 'Milestone tracking setup', 'description': 'Configure milestone tracking and assign owners', 'estimated_hours': 16,
             'responsible': 'CS Ops', 'accountable': 'CSM', 'consulted': [], 'informed': ['VP CS'],
             'execution_backend': 'n8n_webhook', 'backend_config': {'webhook_url': '{{N8N_BASE}}/webhook/milestone-tracker'}},
            {'id': 'S3', 'name': 'Unblock & escalate', 'description': 'Remove blockers — parts, access, approvals', 'estimated_hours': 40,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Support', 'Product'], 'informed': [],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S4', 'name': 'Go-live validation', 'description': 'First workload verification and sign-off', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': ['CRO'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'golive-checklist'}},
        ],
        'estimated_hours': 72, 'estimated_duration_days': 21, 'automation_level': 'partial', 'vertical': 'dc2_s',
    },
    {
        'playbook_id': 'PB-SYS-03',
        'name': 'Expansion Opportunity',
        'description': 'Identify and close expansion opportunities when capacity utilization and expansion probability are high.',
        'trigger_conditions': [
            {'kpi_code': 'P5-KPI1', 'operator': '>', 'value': 80},
            {'kpi_code': 'P5-KPI7', 'operator': '>', 'value': 70},
        ],
        'trigger_kpis': ['P5-KPI1', 'P5-KPI7'],
        'trigger_logic': 'AND',
        'steps': [
            {'id': 'S1', 'name': 'Opportunity scoring', 'description': 'Analyze usage trends and whitespace', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'CRO', 'consulted': ['Sales'], 'informed': ['VP CS'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'expansion-scorer'}},
            {'id': 'S2', 'name': 'Business case & ROI', 'description': 'Build ROI case from Power-of-1 data', 'estimated_hours': 16,
             'responsible': 'CSM', 'accountable': 'CRO', 'consulted': ['Finance'], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'roi-builder'}},
            {'id': 'S3', 'name': 'Executive alignment', 'description': 'Stakeholder and sponsor alignment', 'estimated_hours': 24,
             'responsible': 'CSM', 'accountable': 'CRO', 'consulted': ['VP CS'], 'informed': ['CFO'],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S4', 'name': 'Proposal & negotiation', 'description': 'Pricing, terms, contract', 'estimated_hours': 40,
             'responsible': 'Sales', 'accountable': 'CRO', 'consulted': ['CSM', 'Legal'], 'informed': ['CFO'],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S5', 'name': 'Implementation kickoff', 'description': 'Rollout timeline and success criteria', 'estimated_hours': 16,
             'responsible': 'CS Ops', 'accountable': 'CSM', 'consulted': ['Product'], 'informed': ['VP CS'],
             'execution_backend': 'n8n_webhook', 'backend_config': {'webhook_url': '{{N8N_BASE}}/webhook/expansion-onboard'}},
        ],
        'estimated_hours': 104, 'estimated_duration_days': 60, 'automation_level': 'low', 'vertical': 'dc2_s',
    },
    {
        'playbook_id': 'PB-SYS-04',
        'name': 'Champion Recovery',
        'description': 'Rapid response when a champion departs. Assess impact, find replacement, bridge executive relationship.',
        'trigger_conditions': [{'kpi_code': 'SIGNAL:champion_loss', 'operator': '==', 'value': 1}],
        'trigger_kpis': ['SIGNAL:champion_loss'],
        'trigger_logic': 'OR',
        'steps': [
            {'id': 'S1', 'name': 'Stakeholder impact assessment', 'description': 'Assess departing champion influence on decisions and outcomes', 'estimated_hours': 4,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': ['CRO'],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'stakeholder-impact'}},
            {'id': 'S2', 'name': 'Identify replacement champion', 'description': 'Map org chart, engagement history, find new sponsor', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Sales'], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'champion-finder'}},
            {'id': 'S3', 'name': 'Executive bridge meeting', 'description': 'VP CS meets customer exec to maintain relationship', 'estimated_hours': 4,
             'responsible': 'VP CS', 'accountable': 'CRO', 'consulted': ['CSM'], 'informed': ['CFO'],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S4', 'name': 'Re-establish value narrative', 'description': 'Present ROI story and health history to new champion', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'value-narrative'}},
        ],
        'estimated_hours': 24, 'estimated_duration_days': 14, 'automation_level': 'partial', 'vertical': None,
    },
    {
        'playbook_id': 'PB-SYS-05',
        'name': 'QBR & Executive Engagement',
        'description': 'Establish and maintain quarterly executive engagement cadence with data-driven QBR decks.',
        'trigger_conditions': [{'kpi_code': 'P4-KPI3', 'operator': '<', 'value': 3}],
        'trigger_kpis': ['P4-KPI3'],
        'trigger_logic': 'OR',
        'steps': [
            {'id': 'S1', 'name': 'Stakeholder mapping refresh', 'description': 'Update contacts, roles, engagement frequency', 'estimated_hours': 4,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'stakeholder-mapper'}},
            {'id': 'S2', 'name': 'QBR deck preparation', 'description': 'Auto-generate deck from health, ROI, and KPI trends', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': ['Product'], 'informed': [],
             'execution_backend': 'claude_skill', 'backend_config': {'skill_name': 'qbr-deck-builder'}},
            {'id': 'S3', 'name': 'Executive QBR delivery', 'description': 'VP CS delivers QBR to customer executive', 'estimated_hours': 4,
             'responsible': 'VP CS', 'accountable': 'CRO', 'consulted': ['CSM'], 'informed': ['CFO'],
             'execution_backend': 'manual', 'backend_config': {}},
            {'id': 'S4', 'name': 'Action items & follow-up', 'description': 'Track action items with owners and due dates', 'estimated_hours': 8,
             'responsible': 'CSM', 'accountable': 'VP CS', 'consulted': [], 'informed': ['CRO'],
             'execution_backend': 'n8n_webhook', 'backend_config': {'webhook_url': '{{N8N_BASE}}/webhook/qbr-followup'}},
        ],
        'estimated_hours': 24, 'estimated_duration_days': 30, 'automation_level': 'medium', 'vertical': None,
    },
]


def run_migration():
    """Create playbook_templates and playbook_step_logs tables, seed system playbooks."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # ── Create playbook_templates table ──
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS playbook_templates (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
                vertical VARCHAR(50),
                playbook_id VARCHAR(50) NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                trigger_conditions JSONB,
                trigger_kpis JSONB,
                trigger_logic VARCHAR(10) DEFAULT 'OR',
                steps JSONB,
                estimated_hours FLOAT,
                estimated_duration_days INTEGER,
                automation_level VARCHAR(20) DEFAULT 'partial',
                is_system BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'draft',
                version INTEGER DEFAULT 1,
                created_by INTEGER REFERENCES users(user_id),
                approved_by INTEGER REFERENCES users(user_id),
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_customer_playbook UNIQUE (customer_id, playbook_id)
            )
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_pt_customer_status ON playbook_templates(customer_id, status)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_pt_vertical ON playbook_templates(vertical)
        """))
        print("  Created playbook_templates table")

        # ── Create playbook_step_logs table ──
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS playbook_step_logs (
                id SERIAL PRIMARY KEY,
                execution_id VARCHAR(100) NOT NULL,
                customer_id INTEGER NOT NULL,
                account_id INTEGER,
                step_id VARCHAR(50) NOT NULL,
                step_name VARCHAR(200),
                status VARCHAR(20),
                executed_by VARCHAR(100),
                execution_backend VARCHAR(30),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                input_context JSONB,
                output_result JSONB,
                decision_rationale TEXT,
                outcome_notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_psl_execution ON playbook_step_logs(execution_id, step_id)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_psl_customer ON playbook_step_logs(customer_id)
        """))
        print("  Created playbook_step_logs table")

        conn.commit()

        # ── Seed system playbooks for each existing customer ──
        from models import Customer
        customers = Customer.query.all()
        seeded = 0
        for customer in customers:
            cid = customer.customer_id
            for pb in SYSTEM_PLAYBOOKS:
                try:
                    conn.execute(db.text("""
                        INSERT INTO playbook_templates
                            (customer_id, vertical, playbook_id, name, description,
                             trigger_conditions, trigger_kpis, trigger_logic,
                             steps, estimated_hours, estimated_duration_days,
                             automation_level, is_system, status, version)
                        VALUES
                            (:cid, :vertical, :pid, :name, :desc,
                             :tc, :tkpis, :tl,
                             :steps, :hours, :days,
                             :auto, TRUE, 'active', 1)
                        ON CONFLICT (customer_id, playbook_id) DO NOTHING
                    """), {
                        'cid': cid,
                        'vertical': pb['vertical'],
                        'pid': pb['playbook_id'],
                        'name': pb['name'],
                        'desc': pb['description'],
                        'tc': json.dumps(pb['trigger_conditions']),
                        'tkpis': json.dumps(pb['trigger_kpis']),
                        'tl': pb['trigger_logic'],
                        'steps': json.dumps(pb['steps']),
                        'hours': pb['estimated_hours'],
                        'days': pb['estimated_duration_days'],
                        'auto': pb['automation_level'],
                    })
                    seeded += 1
                except Exception as e:
                    print(f"  Warning: seed failed for customer {cid} / {pb['playbook_id']}: {e}")

        conn.commit()
        conn.close()
        print(f"  Seeded {seeded} system playbooks across {len(customers)} customers")


if __name__ == '__main__':
    run_migration()
    print("Migration complete: playbook_templates + playbook_step_logs")
