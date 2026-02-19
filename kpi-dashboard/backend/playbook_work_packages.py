#!/usr/bin/env python3
"""
Step 7 — Playbook → Work Package Decomposition
=================================================
Maps every playbook to its Power of 1 work packages with WP-level
cost/role tracking. Bridges the playbook execution system with the
resource capacity model.

When a playbook fires, this module decomposes it into costed work
packages so the system can:
  1. Track resource consumption at the WP level
  2. Attribute $ impact per work package
  3. Feed actual hours back into the capacity model
  4. Create ActionEconomics records for each WP

Playbook IDs (from IMPLEMENTATION_PLAN_ACTION_INTERFACE):
  Data Center: PB-DC-01 through PB-DC-06
  SaaS:        SaaS-PB-01 through SaaS-PB-08
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from power_of_1_model import (
    POWER_OF_1_METRICS, WorkPackage as PO1WorkPackage, RoleHours,
)
from resource_capacity_model import CSRole, calculate_action_cost


# ============================================================
# PLAYBOOK → METRIC MAPPING
# ============================================================

# Which Power of 1 metric does each playbook primarily improve?
PLAYBOOK_METRIC_MAP: Dict[str, List[str]] = {
    # Data Center playbooks
    'PB-DC-01': ['TTFV'],                            # Deployment Acceleration
    'PB-DC-02': ['ticket_resolution_time'],           # RMA Prevention
    'PB-DC-03': ['product_adoption'],                 # GPU Optimization
    'PB-DC-04': ['expansion_rate'],                   # Capacity Planning
    'PB-DC-05': ['GRR'],                              # Health Monitoring
    'PB-DC-06': ['NRR', 'expansion_rate'],            # Customer Engagement
    # SaaS playbooks
    'SaaS-PB-01': ['GRR', 'NRR'],                    # Churn Prevention
    'SaaS-PB-02': ['NRR', 'GRR'],                    # Renewal Tracking
    'SaaS-PB-03': ['expansion_rate', 'NRR'],          # Expansion
    'SaaS-PB-04': ['product_adoption', 'TTFV'],       # Low Engagement
    'SaaS-PB-05': ['TTFV'],                           # Onboarding
    'SaaS-PB-06': ['NRR'],                            # QBR
    'SaaS-PB-07': ['GRR'],                            # Executive Escalation
    'SaaS-PB-08': ['NRR', 'expansion_rate'],           # Advocacy
    # Legacy playbook types
    'voc-sprint': ['GRR', 'NRR'],
    'activation-blitz': ['product_adoption', 'TTFV'],
    'sla-stabilizer': ['ticket_resolution_time'],
    'renewal-safeguard': ['GRR', 'NRR'],
    'expansion-timing': ['expansion_rate', 'NRR'],
}


class WPStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class DecomposedWorkPackage:
    """A work package derived from a Power of 1 metric, assigned to a playbook execution."""
    wp_index: int
    wp_name: str
    wp_description: str
    metric_id: str
    metric_display_name: str
    deliverables: List[str]
    estimated_hours: float
    role_hours: Dict[str, float]  # role_name → hours
    estimated_cost: float
    status: WPStatus = WPStatus.PENDING
    actual_hours: Optional[float] = None
    actual_cost: Optional[float] = None


@dataclass
class PlaybookDecomposition:
    """Full work package decomposition for a playbook execution."""
    playbook_id: str
    execution_id: Optional[str]
    metric_ids: List[str]
    work_packages: List[DecomposedWorkPackage]
    total_estimated_hours: float
    total_estimated_cost: float
    role_summary: Dict[str, float]  # role → total hours


# ============================================================
# DECOMPOSITION ENGINE
# ============================================================

def decompose_playbook(
    playbook_id: str,
    execution_id: Optional[str] = None,
) -> PlaybookDecomposition:
    """
    Decompose a playbook into its constituent work packages with
    cost/role tracking from the Power of 1 model.

    Args:
        playbook_id: The playbook identifier (e.g., 'PB-DC-01')
        execution_id: Optional execution_id to associate with

    Returns:
        PlaybookDecomposition with all work packages, costs, and roles
    """
    metric_ids = PLAYBOOK_METRIC_MAP.get(playbook_id, [])

    if not metric_ids:
        return PlaybookDecomposition(
            playbook_id=playbook_id,
            execution_id=execution_id,
            metric_ids=[],
            work_packages=[],
            total_estimated_hours=0,
            total_estimated_cost=0,
            role_summary={},
        )

    work_packages = []
    role_summary: Dict[str, float] = {}
    total_hours = 0
    total_cost = 0
    wp_index = 0

    for metric_id in metric_ids:
        metric = POWER_OF_1_METRICS.get(metric_id)
        if not metric:
            continue

        for wp in metric.work_packages:
            # Build role hours dict from RoleAllocation attributes
            role_attrs = ['csm', 'cs_ops', 'product', 'platform', 'leadership']
            role_hours = {}
            cost_input = {}
            for attr in role_attrs:
                hours = getattr(wp.roles, attr, 0) or 0
                if hours > 0:
                    role_hours[attr] = hours
                    try:
                        cost_input[CSRole(attr)] = hours
                    except ValueError:
                        pass
                    role_summary[attr] = role_summary.get(attr, 0) + hours

            # Calculate cost
            cost = calculate_action_cost(cost_input) if cost_input else {'total_cost': 0}

            dwp = DecomposedWorkPackage(
                wp_index=wp_index,
                wp_name=wp.name,
                wp_description=wp.description,
                metric_id=metric_id,
                metric_display_name=metric.display_name,
                deliverables=wp.deliverables,
                estimated_hours=wp.hours,
                role_hours=role_hours,
                estimated_cost=cost['total_cost'],
            )
            work_packages.append(dwp)
            total_hours += wp.hours
            total_cost += cost['total_cost']
            wp_index += 1

    return PlaybookDecomposition(
        playbook_id=playbook_id,
        execution_id=execution_id,
        metric_ids=metric_ids,
        work_packages=work_packages,
        total_estimated_hours=round(total_hours, 1),
        total_estimated_cost=round(total_cost, 2),
        role_summary={k: round(v, 1) for k, v in role_summary.items()},
    )


# ============================================================
# COST TRACKING HELPERS
# ============================================================

def record_wp_completion(
    decomposition: PlaybookDecomposition,
    wp_index: int,
    actual_hours: float,
) -> DecomposedWorkPackage:
    """
    Mark a work package as completed and record actual hours.
    Returns the updated work package.
    """
    if wp_index >= len(decomposition.work_packages):
        raise ValueError(f"WP index {wp_index} out of range")

    wp = decomposition.work_packages[wp_index]
    wp.status = WPStatus.COMPLETED
    wp.actual_hours = actual_hours

    # Recompute actual cost using the same role ratio as estimate
    if wp.estimated_hours > 0 and actual_hours > 0:
        ratio = actual_hours / wp.estimated_hours
        actual_roles = {}
        for role, hours in wp.role_hours.items():
            try:
                actual_roles[CSRole(role)] = hours * ratio
            except ValueError:
                pass
        cost = calculate_action_cost(actual_roles)
        wp.actual_cost = cost['total_cost']
    else:
        wp.actual_cost = 0

    return wp


def get_execution_cost_summary(
    decomposition: PlaybookDecomposition,
) -> Dict:
    """
    Get a summary of estimated vs. actual costs for the full execution.
    """
    completed = [wp for wp in decomposition.work_packages if wp.status == WPStatus.COMPLETED]
    pending = [wp for wp in decomposition.work_packages if wp.status == WPStatus.PENDING]

    actual_hours = sum(wp.actual_hours or 0 for wp in completed)
    actual_cost = sum(wp.actual_cost or 0 for wp in completed)

    return {
        'playbook_id': decomposition.playbook_id,
        'total_work_packages': len(decomposition.work_packages),
        'completed': len(completed),
        'pending': len(pending),
        'estimated_hours': decomposition.total_estimated_hours,
        'actual_hours': round(actual_hours, 1),
        'hours_variance': round(actual_hours - decomposition.total_estimated_hours, 1),
        'estimated_cost': decomposition.total_estimated_cost,
        'actual_cost': round(actual_cost, 2),
        'cost_variance': round(actual_cost - decomposition.total_estimated_cost, 2),
        'role_summary': decomposition.role_summary,
    }


# ============================================================
# SERIALIZATION
# ============================================================

def decomposition_to_dict(d: PlaybookDecomposition) -> Dict:
    """Serialize a PlaybookDecomposition for API response."""
    return {
        'playbook_id': d.playbook_id,
        'execution_id': d.execution_id,
        'metric_ids': d.metric_ids,
        'total_estimated_hours': d.total_estimated_hours,
        'total_estimated_cost': d.total_estimated_cost,
        'role_summary': d.role_summary,
        'work_packages': [
            {
                'wp_index': wp.wp_index,
                'wp_name': wp.wp_name,
                'wp_description': wp.wp_description,
                'metric_id': wp.metric_id,
                'metric_display_name': wp.metric_display_name,
                'deliverables': wp.deliverables,
                'estimated_hours': wp.estimated_hours,
                'role_hours': wp.role_hours,
                'estimated_cost': wp.estimated_cost,
                'status': wp.status.value,
                'actual_hours': wp.actual_hours,
                'actual_cost': wp.actual_cost,
            }
            for wp in d.work_packages
        ],
    }


def get_all_playbook_decompositions() -> Dict[str, Dict]:
    """Return decompositions for all known playbooks."""
    results = {}
    for playbook_id in PLAYBOOK_METRIC_MAP:
        d = decompose_playbook(playbook_id)
        results[playbook_id] = {
            'metric_ids': d.metric_ids,
            'total_hours': d.total_estimated_hours,
            'total_cost': d.total_estimated_cost,
            'work_package_count': len(d.work_packages),
            'role_summary': d.role_summary,
        }
    return results
