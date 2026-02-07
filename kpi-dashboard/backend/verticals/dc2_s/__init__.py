#!/usr/bin/env python3
"""
DC2_S Vertical Package
Data Center Hardware Infrastructure

This package contains vertical-specific configurations for
data center hardware infrastructure customers running AI/ML workloads.

Main components:
- kpi_definitions: 38 KPIs across 5 pillars
- pillar_weights: L1/L2 weight management and learning loop support
- vertical_config: Partner tiers, phases, playbooks, alerts
- metadata_schema: Profile metadata schema for DC2_S accounts
"""

# KPI Definitions
from .kpi_definitions import (
    DC2S_PILLARS,
    DC2S_KPIS,
    DC2S_METADATA as KPI_METADATA,
    get_kpi_by_code,
    get_kpis_by_pillar,
    get_pillar_info,
    get_health_status,
    calculate_pillar_score,
    calculate_overall_health
)

# Pillar Weights
from .pillar_weights import (
    BOOTSTRAP_L2_WEIGHTS,
    CURRENT_L2_WEIGHTS,
    WEIGHT_METADATA,
    WeightConfig,
    WeightAdjuster,
    ConvergenceTracker,
    get_bootstrap_weights,
    get_current_weights,
    get_weights_for_customer,
    get_l1_weights_for_customer,
    calculate_weight_drift,
    validate_weights
)

# Vertical Configuration
from .vertical_config import (
    PartnerTier,
    CustomerPhase,
    PARTNER_TIER_CONFIG,
    PHASE_CONFIG,
    PLAYBOOK_CONFIG,
    ALERT_THRESHOLDS,
    INTEGRATION_CONFIG,
    VERTICAL_METADATA,
    get_partner_permissions,
    can_access_resource,
    get_phase_info,
    determine_customer_phase,
    get_playbook_config,
    get_playbooks_for_phase,
    should_trigger_playbook,
    get_triggered_alerts
)

# Metadata Schema
from .metadata_schema import (
    DC2S_METADATA_SCHEMA,
    DC2S_METADATA_DEFAULTS,
    EXAMPLE_METADATA,
    create_metadata,
    validate_metadata,
    update_metadata,
    get_metadata_field,
    set_metadata_field,
    calculate_days_since_deployment,
    auto_calculate_fields,
    create_dc2s_account_metadata,
    extract_dc2s_fields,
    export_metadata_json,
    import_metadata_json
)

# Package metadata
__version__ = "1.0.0"
__author__ = "CS Pulse Team"
__description__ = "DC2_S vertical for data center hardware infrastructure"

# Public API
__all__ = [
    # KPI Definitions
    'DC2S_PILLARS',
    'DC2S_KPIS',
    'KPI_METADATA',
    'get_kpi_by_code',
    'get_kpis_by_pillar',
    'get_pillar_info',
    'get_health_status',
    'calculate_pillar_score',
    'calculate_overall_health',
    
    # Pillar Weights
    'BOOTSTRAP_L2_WEIGHTS',
    'CURRENT_L2_WEIGHTS',
    'WEIGHT_METADATA',
    'WeightConfig',
    'WeightAdjuster',
    'ConvergenceTracker',
    'get_bootstrap_weights',
    'get_current_weights',
    'get_weights_for_customer',
    'calculate_weight_drift',
    'validate_weights',
    
    # Vertical Configuration
    'PartnerTier',
    'CustomerPhase',
    'PARTNER_TIER_CONFIG',
    'PHASE_CONFIG',
    'PLAYBOOK_CONFIG',
    'ALERT_THRESHOLDS',
    'INTEGRATION_CONFIG',
    'VERTICAL_METADATA',
    'get_partner_permissions',
    'can_access_resource',
    'get_phase_info',
    'determine_customer_phase',
    'get_playbook_config',
    'get_playbooks_for_phase',
    'should_trigger_playbook',
    'get_triggered_alerts',
    
    # Metadata Schema
    'DC2S_METADATA_SCHEMA',
    'DC2S_METADATA_DEFAULTS',
    'EXAMPLE_METADATA',
    'create_metadata',
    'validate_metadata',
    'update_metadata',
    'get_metadata_field',
    'set_metadata_field',
    'calculate_days_since_deployment',
    'auto_calculate_fields',
    'create_dc2s_account_metadata',
    'extract_dc2s_fields',
    'export_metadata_json',
    'import_metadata_json',
]

# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_vertical_summary() -> dict:
    """Get summary of DC2_S vertical configuration"""
    return {
        "vertical_id": "dc2_S",
        "vertical_name": "Data Center Hardware Infrastructure",
        "version": __version__,
        "total_kpis": len(DC2S_KPIS),
        "total_pillars": len(DC2S_PILLARS),
        "total_playbooks": len(PLAYBOOK_CONFIG),
        "partner_tiers": list(PARTNER_TIER_CONFIG.keys()),
        "customer_phases": list(PHASE_CONFIG.keys()),
        "l2_weights": BOOTSTRAP_L2_WEIGHTS.copy()
    }

def quick_health_check(kpi_values: dict) -> dict:
    """
    Quick health check for an account
    
    Args:
        kpi_values: Dictionary of {kpi_code: value}
        
    Returns:
        Health check summary
    """
    # Calculate pillar scores
    pillar_scores = {}
    for pillar_id in DC2S_PILLARS.keys():
        score = calculate_pillar_score(pillar_id, kpi_values)
        pillar_scores[pillar_id] = score
    
    # Calculate overall health
    overall_health = calculate_overall_health(pillar_scores)
    
    # Get triggered alerts
    triggered_alerts = get_triggered_alerts(kpi_values)
    
    # Determine health status
    if overall_health >= 75:
        status = "healthy"
    elif overall_health >= 50:
        status = "risk"
    else:
        status = "critical"
    
    return {
        "overall_health": overall_health,
        "status": status,
        "pillar_scores": pillar_scores,
        "triggered_alerts": triggered_alerts,
        "alert_count": len(triggered_alerts)
    }

def create_account_with_metadata(**kwargs) -> dict:
    """
    Helper to create Account dict with DC2_S metadata
    
    Usage:
        account_data = create_account_with_metadata(
            account_name="ACME AI Labs",
            gpu_count=64,
            gpu_model="H100",
            deployment_value=15000000.0
        )
    
    Returns:
        Dictionary ready for Account model creation
    """
    # Extract account-level fields
    account_name = kwargs.pop('account_name', 'New Account')
    industry = kwargs.pop('industry', 'ai_infrastructure')
    region = kwargs.pop('region', 'US')
    
    # Create metadata from remaining kwargs
    metadata = create_dc2s_account_metadata(**kwargs)
    
    return {
        "account_name": account_name,
        "industry": industry,
        "region": region,
        "profile_metadata": metadata
    }

def get_recommended_playbooks(
    kpi_values: dict,
    current_phase: str
) -> list:
    """
    Get recommended playbooks based on KPIs and phase
    
    Args:
        kpi_values: Current KPI values
        current_phase: Current customer phase
        
    Returns:
        List of recommended playbook IDs
    """
    recommended = []
    
    # Get playbooks for current phase
    phase_playbooks = get_playbooks_for_phase(current_phase)
    
    # Check which should trigger
    for playbook_id in phase_playbooks:
        if should_trigger_playbook(playbook_id, kpi_values):
            recommended.append(playbook_id)
    
    return recommended

# ============================================================
# PACKAGE INITIALIZATION
# ============================================================

def initialize_vertical():
    """Initialize DC2_S vertical (called on package import)"""
    # Validate configuration
    assert len(DC2S_KPIS) == 38, "Expected 38 KPIs"
    assert len(DC2S_PILLARS) == 5, "Expected 5 pillars"
    assert abs(sum(BOOTSTRAP_L2_WEIGHTS.values()) - 1.0) < 0.01, "L2 weights must sum to 1.0"
    
    # Validate L1 weights per pillar
    for pillar_id in DC2S_PILLARS.keys():
        pillar_kpis = get_kpis_by_pillar(pillar_id)
        total_l1_weight = sum(kpi.get('weight_l1', 0) for kpi in pillar_kpis.values())
        assert abs(total_l1_weight - 1.0) < 0.01, f"L1 weights for {pillar_id} must sum to 1.0"

# Run initialization
initialize_vertical()

print(f"DC2_S Vertical v{__version__} loaded successfully")
print(f"  - {len(DC2S_KPIS)} KPIs across {len(DC2S_PILLARS)} pillars")
print(f"  - {len(PLAYBOOK_CONFIG)} playbooks configured")
print(f"  - {len(PARTNER_TIER_CONFIG)} partner tiers defined")
