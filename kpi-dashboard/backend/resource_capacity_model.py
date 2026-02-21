#!/usr/bin/env python3
"""
Resource Capacity Model
========================
Models the FTE resource pool, role-level hourly rates, and capacity constraints
for CS GrowthPulse initiatives. Used by the simulation engine to ensure
playbooks don't over-allocate resources, and by the revenue intelligence
dashboard to show utilization and efficiency.

DATA SOURCE: All rates loaded from config/resource_rates.json — editable via Settings UI.

Feature flag: 'revenue_intelligence' (per-customer toggle in Settings UI)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# CONFIG LOADER
# ============================================================

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")


def _load_resource_config() -> dict:
    """Load resource rates from config/resource_rates.json."""
    path = os.path.join(_CONFIG_DIR, "resource_rates.json")
    with open(path, "r") as f:
        return json.load(f)


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
    annual_hours: float
    fte: float
    hourly_rate: float
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
# BUILD RESOURCE POOL FROM JSON
# ============================================================

def _build_resource_pool(config: dict) -> Dict[CSRole, RoleCapacity]:
    """Parse JSON config into CSRole → RoleCapacity mapping."""
    pool = {}
    for role_key, data in config.get("roles", {}).items():
        role = CSRole(role_key)
        pool[role] = RoleCapacity(
            role=role,
            display_name=data["display_name"],
            annual_hours=data["annual_hours"],
            fte=data["fte"],
            hourly_rate=data["hourly_rate"],
            description=data["description"],
        )
    return pool


def _build_metric_allocation(config: dict) -> dict:
    """Parse JSON metric_resource_allocation into the expected format."""
    result = {}
    for metric_id, alloc in config.get("metric_resource_allocation", {}).items():
        roles = {}
        for role_key, hours in alloc.get("roles", {}).items():
            roles[CSRole(role_key)] = hours
        result[metric_id] = {
            "total_hours": alloc["total_hours"],
            "cost": sum(
                hours * DEFAULT_RESOURCE_POOL[CSRole(rk)].hourly_rate
                for rk, hours in alloc.get("roles", {}).items()
                if CSRole(rk) in DEFAULT_RESOURCE_POOL
            ) if hasattr(DEFAULT_RESOURCE_POOL, '__iter__') else 0,
            "quarters": alloc.get("quarters", []),
            "primary_pillar": alloc.get("primary_pillar", ""),
            "roles": roles,
        }
    return result


# ============================================================
# MODULE-LEVEL CONSTANTS — loaded from JSON
# ============================================================

_cfg = _load_resource_config()

DEFAULT_RESOURCE_POOL: Dict[CSRole, RoleCapacity] = _build_resource_pool(_cfg)

# Convenience alias: role → hourly rate
ROLE_RATES: Dict[str, float] = {
    role.value: cap.hourly_rate for role, cap in DEFAULT_RESOURCE_POOL.items()
}


def _build_metric_allocation_real(config: dict) -> dict:
    """Build metric allocation with real costs from the loaded pool."""
    result = {}
    for metric_id, alloc in config.get("metric_resource_allocation", {}).items():
        roles = {}
        total_cost = 0
        for role_key, hours in alloc.get("roles", {}).items():
            cs_role = CSRole(role_key)
            roles[cs_role] = hours
            if cs_role in DEFAULT_RESOURCE_POOL:
                total_cost += hours * DEFAULT_RESOURCE_POOL[cs_role].hourly_rate
        result[metric_id] = {
            "total_hours": alloc["total_hours"],
            "cost": round(total_cost, 2),
            "quarters": alloc.get("quarters", []),
            "primary_pillar": alloc.get("primary_pillar", ""),
            "roles": roles,
        }
    return result


METRIC_RESOURCE_ALLOCATION = _build_metric_allocation_real(_cfg)


def reload_config():
    """
    Reload resource rates from JSON.
    Call this after the Settings UI saves new values.
    """
    global DEFAULT_RESOURCE_POOL, ROLE_RATES, METRIC_RESOURCE_ALLOCATION

    cfg = _load_resource_config()
    DEFAULT_RESOURCE_POOL = _build_resource_pool(cfg)
    ROLE_RATES = {role.value: cap.hourly_rate for role, cap in DEFAULT_RESOURCE_POOL.items()}
    METRIC_RESOURCE_ALLOCATION = _build_metric_allocation_real(cfg)


# ============================================================
# CAPACITY CONSTRAINTS
# ============================================================

@dataclass
class CapacityConstraint:
    """Represents a resource capacity check result"""
    is_feasible: bool
    utilization_by_role: Dict[str, float]
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
    divisor = 4 if quarter else 1

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


def calculate_metric_action_cost(metric_id: str) -> Dict:
    """
    Calculate the cost of executing a 1% improvement action for a specific metric.
    Uses the metric_resource_allocation from config/resource_rates.json.

    Returns:
        Dict with total_cost, cs_initiative_cost, platform_cost, hours breakdown
    """
    alloc = METRIC_RESOURCE_ALLOCATION.get(metric_id)
    if not alloc:
        return {"error": f"No resource allocation for metric: {metric_id}", "total_cost": 0}

    return calculate_action_cost(alloc["roles"])


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
