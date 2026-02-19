#!/usr/bin/env python3
"""
Resource Capacity Model
========================
Models the FTE resource pool, role-level hourly rates, and capacity constraints
for CS GrowthPulse initiatives. Used by the simulation engine to ensure
playbooks don't over-allocate resources, and by the revenue intelligence
dashboard to show utilization and efficiency.

Feature flag: 'revenue_intelligence' (per-customer toggle in Settings UI)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# ROLE DEFINITIONS
# ============================================================

class CSRole(Enum):
    """The 5 CS roles involved in Power of 1 initiatives"""
    CSM = "csm"
    CS_OPS = "cs_ops"
    PRODUCT = "product"
    PLATFORM = "platform"
    LEADERSHIP = "leadership"


@dataclass
class RoleCapacity:
    """Capacity and cost model for a single CS role"""
    role: CSRole
    display_name: str
    annual_hours: float          # Total hours allocated to GrowthPulse
    fte: float                   # FTE equivalent (annual_hours / 2080)
    hourly_rate: float           # Fully loaded cost per hour (USD)
    description: str

    @property
    def annual_cost(self) -> float:
        return self.annual_hours * self.hourly_rate

    @property
    def monthly_hours(self) -> float:
        return self.annual_hours / 12

    @property
    def weekly_hours(self) -> float:
        return self.annual_hours / 52


# ============================================================
# DEFAULT RESOURCE POOL (from Slide 18)
# ============================================================
# Total: 5,840 hours / 2.81 FTE / $247K
# These are DEFAULTS — configurable per customer in Settings UI.

DEFAULT_RESOURCE_POOL: Dict[CSRole, RoleCapacity] = {
    CSRole.CSM: RoleCapacity(
        role=CSRole.CSM,
        display_name="Customer Success Managers",
        annual_hours=1920,
        fte=0.92,
        hourly_rate=95.00,
        description="Direct customer engagement, QBRs, relationship management",
    ),
    CSRole.CS_OPS: RoleCapacity(
        role=CSRole.CS_OPS,
        display_name="CS Operations",
        annual_hours=1760,
        fte=0.85,
        hourly_rate=85.00,
        description="Process design, automation, analytics, reporting",
    ),
    CSRole.PRODUCT: RoleCapacity(
        role=CSRole.PRODUCT,
        display_name="Product Team",
        annual_hours=760,
        fte=0.37,
        hourly_rate=110.00,
        description="Feature development, in-app experiences, integrations",
    ),
    CSRole.PLATFORM: RoleCapacity(
        role=CSRole.PLATFORM,
        display_name="Platform Team (Us)",
        annual_hours=920,
        fte=0.44,
        hourly_rate=120.00,
        description="GrowthPulse platform configuration, APIs, dashboards",
    ),
    CSRole.LEADERSHIP: RoleCapacity(
        role=CSRole.LEADERSHIP,
        display_name="CS Leadership",
        annual_hours=480,
        fte=0.23,
        hourly_rate=150.00,
        description="Strategy, governance, executive alignment",
    ),
}


# ============================================================
# PER-METRIC RESOURCE ALLOCATION (from Slide 18)
# ============================================================
# Maps each Power of 1 metric to its resource requirements.

METRIC_RESOURCE_ALLOCATION = {
    "TTFV": {
        "total_hours": 1280,
        "cost": 75500,
        "quarters": ["Q1", "Q2"],
        "primary_pillar": "usage_onboarding",
        "roles": {
            CSRole.CSM: 360,       # Across all 4 work packages
            CSRole.CS_OPS: 540,
            CSRole.PRODUCT: 160,
            CSRole.PLATFORM: 220,  # Heaviest platform involvement — setup
            CSRole.LEADERSHIP: 0,  # Not counted in slide but adding for completeness
        },
    },
    "NRR": {
        "total_hours": 1000,
        "cost": 50000,
        "quarters": ["Q2", "Q3"],
        "primary_pillar": "business_outcomes",
        "roles": {
            CSRole.CSM: 400,
            CSRole.CS_OPS: 360,
            CSRole.PRODUCT: 20,
            CSRole.PLATFORM: 140,
            CSRole.LEADERSHIP: 80,
        },
    },
    "GRR": {
        "total_hours": 1280,
        "cost": 60000,
        "quarters": ["Q1", "Q2", "Q3", "Q4"],
        "primary_pillar": "business_outcomes",
        "roles": {
            CSRole.CSM: 480,
            CSRole.CS_OPS: 480,
            CSRole.PRODUCT: 20,
            CSRole.PLATFORM: 200,
            CSRole.LEADERSHIP: 100,
        },
    },
    "ticket_resolution_time": {
        "total_hours": 840,
        "cost": 26000,
        "quarters": ["Q2", "Q3"],
        "primary_pillar": "support_engagement",
        "roles": {
            CSRole.CSM: 120,
            CSRole.CS_OPS: 400,
            CSRole.PRODUCT: 160,
            CSRole.PLATFORM: 120,
            CSRole.LEADERSHIP: 40,
        },
    },
    "product_adoption": {
        "total_hours": 800,
        "cost": 21000,
        "quarters": ["Q3", "Q4"],
        "primary_pillar": "usage_onboarding",
        "roles": {
            CSRole.CSM: 240,
            CSRole.CS_OPS: 280,
            CSRole.PRODUCT: 160,
            CSRole.PLATFORM: 120,
            CSRole.LEADERSHIP: 0,
        },
    },
    "expansion_rate": {
        "total_hours": 640,
        "cost": 14500,
        "quarters": ["Q3", "Q4"],
        "primary_pillar": "business_outcomes",
        "roles": {
            CSRole.CSM: 200,
            CSRole.CS_OPS: 240,
            CSRole.PRODUCT: 40,
            CSRole.PLATFORM: 80,
            CSRole.LEADERSHIP: 80,
        },
    },
}


# ============================================================
# CAPACITY CONSTRAINTS
# ============================================================
# Used by simulation engine to prevent over-allocation.

@dataclass
class CapacityConstraint:
    """Represents a resource capacity check result"""
    is_feasible: bool
    utilization_by_role: Dict[str, float]   # 0-1 per role
    bottleneck_role: Optional[str]
    overflow_hours: float
    recommendation: str


def check_capacity(
    planned_hours_by_role: Dict[CSRole, float],
    resource_pool: Optional[Dict[CSRole, RoleCapacity]] = None,
    quarter: Optional[str] = None,
) -> CapacityConstraint:
    """
    Check if planned work fits within the resource capacity.

    Args:
        planned_hours_by_role: Hours needed per role for planned initiative
        resource_pool: Override default pool (for customer-specific configs)
        quarter: If specified, checks quarterly capacity (annual / 4)

    Returns:
        CapacityConstraint with feasibility assessment
    """
    pool = resource_pool or DEFAULT_RESOURCE_POOL
    divisor = 4 if quarter else 1  # Quarter = 1/4 of annual capacity

    utilization = {}
    bottleneck = None
    max_util = 0
    total_overflow = 0

    for role, planned in planned_hours_by_role.items():
        capacity = pool.get(role)
        if not capacity:
            continue

        available = capacity.annual_hours / divisor
        util = planned / available if available > 0 else float('inf')
        utilization[role.value] = round(util, 3)

        if util > max_util:
            max_util = util
            bottleneck = role.value

        if planned > available:
            total_overflow += (planned - available)

    is_feasible = max_util <= 1.0

    if is_feasible:
        recommendation = f"All roles within capacity. Peak utilization: {bottleneck} at {max_util:.0%}"
    else:
        recommendation = (
            f"Capacity exceeded. {bottleneck} is at {max_util:.0%} utilization. "
            f"Consider spreading work across quarters or adding {total_overflow:.0f} hours of capacity."
        )

    return CapacityConstraint(
        is_feasible=is_feasible,
        utilization_by_role=utilization,
        bottleneck_role=bottleneck,
        overflow_hours=round(total_overflow, 1),
        recommendation=recommendation,
    )


# ============================================================
# COST CALCULATION HELPERS
# ============================================================

def calculate_action_cost(
    hours_by_role: Dict[CSRole, float],
    resource_pool: Optional[Dict[CSRole, RoleCapacity]] = None,
) -> Dict:
    """
    Calculate the cost of an action (playbook, work package) given hours by role.

    Returns:
        Dict with cs_cost, platform_cost, total_cost, and breakdown by role
    """
    pool = resource_pool or DEFAULT_RESOURCE_POOL
    breakdown = {}
    cs_cost = 0
    platform_cost = 0

    for role, hours in hours_by_role.items():
        capacity = pool.get(role)
        if not capacity:
            continue

        cost = hours * capacity.hourly_rate
        breakdown[role.value] = {
            "hours": hours,
            "hourly_rate": capacity.hourly_rate,
            "cost": round(cost, 2),
        }

        if role == CSRole.PLATFORM:
            platform_cost += cost
        else:
            cs_cost += cost

    return {
        "cs_initiative_cost": round(cs_cost, 2),
        "platform_cost": round(platform_cost, 2),
        "total_cost": round(cs_cost + platform_cost, 2),
        "breakdown": breakdown,
    }


def get_resource_pool_summary(
    resource_pool: Optional[Dict[CSRole, RoleCapacity]] = None,
) -> Dict:
    """Get a summary of the resource pool for display in Settings UI."""
    pool = resource_pool or DEFAULT_RESOURCE_POOL

    roles = []
    total_hours = 0
    total_fte = 0
    total_cost = 0

    for role, capacity in pool.items():
        roles.append({
            "role": capacity.role.value,
            "display_name": capacity.display_name,
            "annual_hours": capacity.annual_hours,
            "fte": capacity.fte,
            "hourly_rate": capacity.hourly_rate,
            "annual_cost": round(capacity.annual_cost, 2),
            "monthly_hours": round(capacity.monthly_hours, 1),
            "description": capacity.description,
        })
        total_hours += capacity.annual_hours
        total_fte += capacity.fte
        total_cost += capacity.annual_cost

    return {
        "roles": roles,
        "totals": {
            "total_hours": total_hours,
            "total_fte": round(total_fte, 2),
            "total_annual_cost": round(total_cost, 2),
        },
    }
