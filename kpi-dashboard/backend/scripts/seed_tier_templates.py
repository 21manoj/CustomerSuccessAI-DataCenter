#!/usr/bin/env python3
"""
Seed Tier Templates
===================
Creates 6 template sets (3 tiers x 2 verticals) in vertical_templates.

Each tier gets config_types: kpi_config, health_thresholds, pillar_weights,
and (for Professional/Enterprise) playbook_config.

Tier KPI subsets:
  - Starter      : Top 2 KPIs per pillar by weight_l1  (10 each)
  - Professional : Top 4 KPIs per pillar by weight_l1  (20 each)
  - Enterprise   : All KPIs enabled                    (38 DC2_S / 35 SaaS)

Usage:
  python scripts/seed_tier_templates.py
  python scripts/seed_tier_templates.py --dry-run

Safe: idempotent -- skips if (vertical, tier, config_type, version) already exists.
"""

import argparse
import json
import sys

sys.path.insert(0, '.')
from app_v3_minimal import app
from models import db, VerticalTemplate

# ===================================================================
# DC2_S KPI Definitions — sorted by weight_l1 descending per pillar
# ===================================================================
DC2S_KPIS = {
    'P1': [
        ('P1-KPI1', 'Time-to-First-Workload', 0.20),
        ('P1-KPI2', 'Installation Completion Rate', 0.15),
        ('P1-KPI4', 'Deployment Cycle Time', 0.15),
        ('P1-KPI5', 'Hardware Commissioning Time', 0.13),
        ('P1-KPI3', 'Configuration Accuracy', 0.12),
        ('P1-KPI6', 'Network Readiness Score', 0.10),
        ('P1-KPI7', 'Deployment Team Velocity', 0.08),
        ('P1-KPI8', 'Documentation Completeness', 0.07),
    ],
    'P2': [
        ('P2-KPI1', 'RMA Frequency Rate', 0.20),
        ('P2-KPI2', 'MTBF', 0.18),
        ('P2-KPI3', 'Critical Incidents (30d)', 0.17),
        ('P2-KPI4', 'System Uptime Percentage', 0.15),
        ('P2-KPI5', 'Thermal Management Score', 0.12),
        ('P2-KPI6', 'Power Efficiency (PUE)', 0.08),
        ('P2-KPI7', 'Mean Time To Repair (MTTR)', 0.06),
        ('P2-KPI8', 'Preventive Maintenance Compliance', 0.04),
    ],
    'P3': [
        ('P3-KPI1', 'GPU Utilization Rate', 0.22),
        ('P3-KPI2', 'Training Job Completion Rate', 0.20),
        ('P3-KPI3', 'Inference Latency (P95)', 0.15),
        ('P3-KPI4', 'Model Training Time', 0.14),
        ('P3-KPI5', 'GPU Memory Efficiency', 0.12),
        ('P3-KPI6', 'Distributed Training Efficiency', 0.09),
        ('P3-KPI7', 'Workload Diversity Score', 0.05),
        ('P3-KPI8', 'Batch Processing Throughput', 0.03),
    ],
    'P4': [
        ('P4-KPI1', 'Partner Engagement Score', 0.22),
        ('P4-KPI2', 'VAR Performance Rating', 0.20),
        ('P4-KPI3', 'Joint QBR Frequency', 0.18),
        ('P4-KPI4', 'Channel Conflict Score', 0.15),
        ('P4-KPI5', 'Co-selling Opportunities', 0.13),
        ('P4-KPI6', 'Partner NPS', 0.12),
    ],
    'P5': [
        ('P5-KPI1', 'Capacity Utilization Rate', 0.18),
        ('P5-KPI2', 'Capacity Utilization Trajectory', 0.18),
        ('P5-KPI3', 'Workload Growth Velocity', 0.18),
        ('P5-KPI4', 'Compute Hour Consumption Trend', 0.15),
        ('P5-KPI7', 'Expansion Probability (90d)', 0.13),
        ('P5-KPI5', 'Budget Availability Signals', 0.10),
        ('P5-KPI6', 'New Use Case Adoption', 0.05),
        ('P5-KPI8', 'Technical Champion Engagement', 0.03),
    ],
}

DC2S_PILLAR_WEIGHTS = {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}

# ===================================================================
# SaaS Premium KPI Definitions — sorted by weight_l1 descending
# ===================================================================
SAAS_KPIS = {
    'P1': [
        ('P1-KPI1', 'Daily Active Users (DAU) Rate', 0.20),
        ('P1-KPI2', 'Feature Adoption Breadth', 0.18),
        ('P1-KPI3', 'Time-to-Value (TTV)', 0.16),
        ('P1-KPI4', 'Login Frequency', 0.14),
        ('P1-KPI5', 'API Integration Usage', 0.12),
        ('P1-KPI6', 'Workflow Completion Rate', 0.10),
        ('P1-KPI7', 'Module Activation Rate', 0.10),
    ],
    'P2': [
        ('P2-KPI1', 'Executive Sponsor Engagement', 0.22),
        ('P2-KPI2', 'QBR Attendance Rate', 0.18),
        ('P2-KPI3', 'Training Completion Rate', 0.15),
        ('P2-KPI5', 'CSM Interaction Frequency', 0.13),
        ('P2-KPI4', 'Community Participation Score', 0.12),
        ('P2-KPI6', 'Webinar/Event Attendance', 0.10),
        ('P2-KPI7', 'Customer Advocacy Score', 0.10),
    ],
    'P3': [
        ('P3-KPI1', 'Ticket Resolution Time', 0.20),
        ('P3-KPI2', 'CSAT Score', 0.18),
        ('P3-KPI3', 'NPS Score', 0.15),
        ('P3-KPI4', 'Escalation Rate', 0.14),
        ('P3-KPI5', 'First Contact Resolution Rate', 0.13),
        ('P3-KPI6', 'Support Ticket Volume Trend', 0.10),
        ('P3-KPI7', 'SLA Compliance Rate', 0.10),
    ],
    'P4': [
        ('P4-KPI1', 'Partner-Sourced Revenue Rate', 0.20),
        ('P4-KPI2', 'Partner Certification Level', 0.16),
        ('P4-KPI3', 'Partner Deal Registration Rate', 0.15),
        ('P4-KPI5', 'Partner Satisfaction Score', 0.14),
        ('P4-KPI4', 'Channel Conflict Resolution Time', 0.13),
        ('P4-KPI6', 'Co-Marketing Campaign ROI', 0.12),
        ('P4-KPI7', 'Partner Technical Enablement Score', 0.10),
    ],
    'P5': [
        ('P5-KPI1', 'Net Revenue Retention (NRR)', 0.22),
        ('P5-KPI2', 'Gross Revenue Retention (GRR)', 0.18),
        ('P5-KPI3', 'Expansion Revenue Rate', 0.15),
        ('P5-KPI5', 'Renewal Probability (90d)', 0.15),
        ('P5-KPI4', 'Annual Contract Value (ACV) Growth', 0.12),
        ('P5-KPI6', 'Churn Risk Score', 0.10),
        ('P5-KPI7', 'Customer Lifetime Value Trend', 0.08),
    ],
}

SAAS_PILLAR_WEIGHTS = {'P1': 0.20, 'P2': 0.15, 'P3': 0.15, 'P4': 0.20, 'P5': 0.30}


# ===================================================================
# Tier Selection Logic
# ===================================================================

def select_kpis(kpi_dict, n_per_pillar):
    """Select top N KPIs per pillar by weight_l1.

    Args:
        kpi_dict: { pillar: [(code, name, weight), ...] } — already sorted desc
        n_per_pillar: int or None (None = all)

    Returns:
        list of KPI codes, dict of {code: weight}
    """
    codes = []
    weights = {}
    for pillar, kpis in sorted(kpi_dict.items()):
        selected = kpis if n_per_pillar is None else kpis[:n_per_pillar]
        for code, name, weight in selected:
            codes.append(code)
            weights[code] = weight
    return codes, weights


def build_kpi_config(kpi_dict, n_per_pillar, tier_label):
    """Build the kpi_config template for a given tier."""
    codes, weights = select_kpis(kpi_dict, n_per_pillar)
    total = sum(len(v) for v in kpi_dict.values())
    return {
        'tier': tier_label,
        'enabled_kpis': codes if n_per_pillar is not None else 'ALL',
        'kpi_count': len(codes) if n_per_pillar is not None else total,
        'total_available': total,
        'selection_rule': f'Top {n_per_pillar} by L1 weight per pillar' if n_per_pillar else 'All KPIs enabled',
        'kpi_weights': weights if n_per_pillar is not None else {},
        'power_of_1_compliant': tier_label != 'starter',
    }


def build_health_thresholds(tier_label):
    """Health thresholds are the same for all tiers (50/70)."""
    return {
        'tier': tier_label,
        'thresholds': {
            'critical_max': 50,
            'at_risk_max': 70,
            'healthy_min': 70,
        },
        'description': 'Standard health classification: <50 critical, 50-69 at-risk, 70+ healthy',
    }


def build_pillar_weights(pillar_weights, tier_label):
    """Pillar weights config."""
    return {
        'tier': tier_label,
        'pillar_weights_L2': pillar_weights,
        'source': 'calibrated from bootstrap' if tier_label != 'starter' else 'equal distribution',
    }


def build_playbook_config(tier_label):
    """Playbook configuration per tier."""
    if tier_label == 'starter':
        return None  # No playbooks for Starter
    elif tier_label == 'professional':
        return {
            'tier': tier_label,
            'manual_playbooks': True,
            'auto_trigger': False,
            'max_concurrent_playbooks': 3,
            'approval_required': True,
        }
    else:  # enterprise
        return {
            'tier': tier_label,
            'manual_playbooks': True,
            'auto_trigger': True,
            'max_concurrent_playbooks': 10,
            'approval_required': False,
            'partner_playbooks_enabled': True,
        }


def build_tier_limits(tier_label):
    """Tier-specific limits (seats, accounts, etc.)."""
    limits = {
        'starter': {
            'max_accounts': 5,
            'max_seats': 3,
            'max_api_keys': 2,
            'data_retention_days': 90,
        },
        'professional': {
            'max_accounts': 25,
            'max_seats': 10,
            'max_api_keys': 10,
            'data_retention_days': 365,
        },
        'enterprise': {
            'max_accounts': None,  # unlimited
            'max_seats': 50,
            'max_api_keys': 50,
            'data_retention_days': 730,
        },
    }
    return {
        'tier': tier_label,
        'limits': limits[tier_label],
    }


# ===================================================================
# Template Generation
# ===================================================================

VERTICALS = {
    'dc2_s': {'kpis': DC2S_KPIS, 'pillar_weights': DC2S_PILLAR_WEIGHTS, 'label': 'Data Center'},
    'saas_premium': {'kpis': SAAS_KPIS, 'pillar_weights': SAAS_PILLAR_WEIGHTS, 'label': 'SaaS Premium'},
}

TIERS = {
    'starter': {'n_per_pillar': 2, 'label': 'Quick Start'},
    'professional': {'n_per_pillar': 4, 'label': 'Standard'},
    'enterprise': {'n_per_pillar': None, 'label': 'Full'},  # None = all
}


def generate_templates():
    """Generate all 6 template sets (3 tiers x 2 verticals).

    Returns list of dicts ready for VerticalTemplate creation.
    """
    templates = []

    for vertical, vinfo in VERTICALS.items():
        for tier, tinfo in TIERS.items():
            # 1. kpi_config
            kpi_config = build_kpi_config(vinfo['kpis'], tinfo['n_per_pillar'], tier)
            templates.append({
                'vertical': vertical,
                'tier': tier,
                'config_type': 'kpi_config',
                'version': '1.0',
                'config': kpi_config,
                'description': f"{vinfo['label']} {tinfo['label']} — {kpi_config['kpi_count']} KPIs",
                'is_active': True,
            })

            # 2. health_thresholds
            templates.append({
                'vertical': vertical,
                'tier': tier,
                'config_type': 'health_thresholds',
                'version': '1.0',
                'config': build_health_thresholds(tier),
                'description': f"{vinfo['label']} {tinfo['label']} — health thresholds",
                'is_active': True,
            })

            # 3. pillar_weights
            templates.append({
                'vertical': vertical,
                'tier': tier,
                'config_type': 'pillar_weights',
                'version': '1.0',
                'config': build_pillar_weights(vinfo['pillar_weights'], tier),
                'description': f"{vinfo['label']} {tinfo['label']} — L2 pillar weights",
                'is_active': True,
            })

            # 4. playbook_config (not for Starter)
            pb = build_playbook_config(tier)
            if pb:
                templates.append({
                    'vertical': vertical,
                    'tier': tier,
                    'config_type': 'playbook_config',
                    'version': '1.0',
                    'config': pb,
                    'description': f"{vinfo['label']} {tinfo['label']} — playbook config",
                    'is_active': True,
                })

            # 5. tier_limits
            templates.append({
                'vertical': vertical,
                'tier': tier,
                'config_type': 'tier_limits',
                'version': '1.0',
                'config': build_tier_limits(tier),
                'description': f"{vinfo['label']} {tinfo['label']} — tier limits",
                'is_active': True,
            })

    return templates


# ===================================================================
# Runner
# ===================================================================

def run_seed(dry_run=False):
    with app.app_context():
        templates = generate_templates()
        created = 0
        skipped = 0

        for t in templates:
            # Check if this template already exists
            existing = VerticalTemplate.query.filter_by(
                vertical=t['vertical'],
                tier=t['tier'],
                config_type=t['config_type'],
                version=t['version'],
            ).first()

            if existing:
                print(f"  [SKIP] {t['vertical']}/{t['tier']}/{t['config_type']} v{t['version']} — already exists (id={existing.template_id})")
                skipped += 1
                continue

            if not dry_run:
                tmpl = VerticalTemplate(
                    vertical=t['vertical'],
                    tier=t['tier'],
                    config_type=t['config_type'],
                    version=t['version'],
                    config=t['config'],
                    description=t['description'],
                    is_active=t['is_active'],
                )
                db.session.add(tmpl)
                print(f"  [ADD]  {t['vertical']}/{t['tier']}/{t['config_type']} v{t['version']} — {t['description']}")
            else:
                print(f"  [PLAN] {t['vertical']}/{t['tier']}/{t['config_type']} v{t['version']} — {t['description']}")
            created += 1

        if not dry_run:
            db.session.commit()
            print(f"\n  Created {created} templates, skipped {skipped} existing.")
        else:
            print(f"\n  DRY RUN: Would create {created}, skip {skipped}.")

        # Summary
        print("\n--- Template Summary ---")
        for vertical in ['dc2_s', 'saas_premium']:
            for tier in ['starter', 'professional', 'enterprise']:
                kpi_t = [t for t in templates
                         if t['vertical'] == vertical
                         and t['tier'] == tier
                         and t['config_type'] == 'kpi_config']
                if kpi_t:
                    cfg = kpi_t[0]['config']
                    kpi_count = cfg['kpi_count']
                    kpi_list = cfg['enabled_kpis']
                    if isinstance(kpi_list, list):
                        kpi_str = ', '.join(kpi_list)
                    else:
                        kpi_str = kpi_list
                    print(f"  {vertical}/{tier}: {kpi_count} KPIs — {kpi_str}")

        # Verify total row count
        if not dry_run:
            total = VerticalTemplate.query.count()
            print(f"\n  Total vertical_templates rows: {total}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed Tier Templates')
    parser.add_argument('--dry-run', action='store_true', help='Preview without creating')
    args = parser.parse_args()
    run_seed(dry_run=args.dry_run)
