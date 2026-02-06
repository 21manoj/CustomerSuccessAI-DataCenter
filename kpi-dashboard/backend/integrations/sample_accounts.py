#!/usr/bin/env python3
"""
DC2_S Sample Accounts Generator
Creates 10 realistic pilot accounts with KPI values for Google Sheets integration

Account Mix:
- 3 High-performing (healthy, expansion-ready)
- 4 Medium-performing (some risks, optimization needed)
- 3 At-risk (critical issues, intervention needed)

Phases:
- 3 Deployment phase
- 4 Performance phase
- 3 Excellence phase
"""

from datetime import datetime, timedelta
import random

# Sample account configurations
SAMPLE_ACCOUNTS = [
    # ========================================
    # HIGH PERFORMERS (3 accounts)
    # ========================================
    {
        "account_id": 1,
        "account_name": "CloudScale AI Labs",
        "customer_id": 101,
        "industry": "ai_infrastructure",
        "region": "US-West",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-06-01",
            "days_since_deployment": 214,
            "gpu_count": 64,
            "gpu_model": "H100",
            "cluster_size": 8,
            "total_gpu_memory_gb": 5120,
            "cpu_count": 512,
            "ram_gb": 4096,
            "storage_tb": 500,
            "use_case": "llm_training",
            "workload_types": ["training", "inference", "research"],
            "phase": "excellence",
            "phase_entered_date": "2025-11-01",
            "partner_tier": "tier_1",
            "var_partner_id": "VAR-001",
            "var_partner_name": "TechPartner Solutions",
            "deployment_value": 15000000.0,
            "arr": 3000000.0,
            "expansion_opportunity_value": 8000000.0,
            "complexity": "high",
            "risk_level": "low"
        },
        "kpi_values": {
            # P1: Deployment Velocity
            "P1-KPI1": 11.0,   # Time-to-first-workload: 11 days (EXCELLENT)
            "P1-KPI2": 98.0,   # Installation completion: 98%
            "P1-KPI3": 97.0,   # Configuration accuracy: 97%
            "P1-KPI4": 25.0,   # Deployment cycle time: 25 days
            
            # P2: Operational Stability
            "P2-KPI1": 0.8,    # RMA rate: 0.8% (EXCELLENT)
            "P2-KPI2": 12500,  # MTBF: 12,500 hours
            "P2-KPI3": 1,      # Critical incidents: 1
            "P2-KPI4": 99.8,   # System uptime: 99.8%
            
            # P3: AI Workload Performance
            "P3-KPI1": 78.0,   # GPU utilization: 78% (EXCELLENT)
            "P3-KPI2": 95.0,   # Training completion: 95%
            "P3-KPI3": 42.0,   # Inference latency: 42ms
            "P3-KPI5": 85.0,   # GPU memory efficiency: 85%
            
            # P4: Channel & Partner Health
            "P4-KPI1": 82.0,   # Partner engagement: 82
            "P4-KPI3": 5,      # QBR frequency: 5 per year
            
            # P5: Expansion Readiness
            "P5-KPI1": 82.0,   # Capacity utilization: 82%
            "P5-KPI2": 15.0,   # Capacity trajectory: +15% MoM
            "P5-KPI3": 18.0,   # Workload growth: +18% MoM
            "P5-KPI7": 85.0    # Expansion probability: 85%
        },
        "expected_health": 88.5,
        "expected_status": "healthy",
        "notes": "Flagship account - high expansion probability"
    },
    
    {
        "account_id": 2,
        "account_name": "Nexus Research Institute",
        "customer_id": 102,
        "industry": "ai_infrastructure",
        "region": "US-East",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-08-15",
            "days_since_deployment": 139,
            "gpu_count": 32,
            "gpu_model": "H100",
            "cluster_size": 4,
            "total_gpu_memory_gb": 2560,
            "use_case": "research",
            "workload_types": ["training", "research"],
            "phase": "performance",
            "phase_entered_date": "2025-11-15",
            "partner_tier": "direct",
            "deployment_value": 8000000.0,
            "arr": 1600000.0,
            "expansion_opportunity_value": 4000000.0,
            "complexity": "medium",
            "risk_level": "low"
        },
        "kpi_values": {
            "P1-KPI1": 13.0,
            "P1-KPI2": 95.0,
            "P1-KPI4": 28.0,
            "P2-KPI1": 1.2,
            "P2-KPI2": 11000,
            "P2-KPI4": 99.6,
            "P3-KPI1": 75.0,
            "P3-KPI2": 92.0,
            "P3-KPI5": 82.0,
            "P5-KPI1": 78.0,
            "P5-KPI2": 12.0,
            "P5-KPI7": 78.0
        },
        "expected_health": 85.0,
        "expected_status": "healthy"
    },
    
    {
        "account_id": 3,
        "account_name": "Quantum Computing Corp",
        "customer_id": 103,
        "industry": "ai_infrastructure",
        "region": "Europe",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "colocation",
            "deployment_date": "2025-07-01",
            "days_since_deployment": 184,
            "gpu_count": 48,
            "gpu_model": "H100",
            "cluster_size": 6,
            "total_gpu_memory_gb": 3840,
            "use_case": "multi_modal",
            "workload_types": ["training", "inference"],
            "phase": "excellence",
            "phase_entered_date": "2025-12-01",
            "partner_tier": "tier_1",
            "var_partner_id": "VAR-002",
            "var_partner_name": "Euro Tech Partners",
            "deployment_value": 12000000.0,
            "arr": 2400000.0,
            "expansion_opportunity_value": 6000000.0,
            "complexity": "high",
            "risk_level": "low"
        },
        "kpi_values": {
            "P1-KPI1": 10.0,
            "P1-KPI2": 97.0,
            "P2-KPI1": 1.0,
            "P2-KPI2": 13000,
            "P2-KPI4": 99.7,
            "P3-KPI1": 80.0,
            "P3-KPI2": 94.0,
            "P5-KPI1": 85.0,
            "P5-KPI2": 16.0,
            "P5-KPI7": 82.0
        },
        "expected_health": 87.0,
        "expected_status": "healthy"
    },
    
    # ========================================
    # MEDIUM PERFORMERS (4 accounts)
    # ========================================
    
    {
        "account_id": 4,
        "account_name": "DataVision Analytics",
        "customer_id": 104,
        "industry": "ai_infrastructure",
        "region": "US-Central",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-09-15",
            "days_since_deployment": 108,
            "gpu_count": 24,
            "gpu_model": "A100",
            "cluster_size": 3,
            "total_gpu_memory_gb": 1920,
            "use_case": "computer_vision",
            "workload_types": ["inference", "training"],
            "phase": "performance",
            "phase_entered_date": "2025-12-15",
            "partner_tier": "tier_2",
            "var_partner_id": "VAR-005",
            "var_partner_name": "Midwest Solutions",
            "deployment_value": 6000000.0,
            "arr": 1200000.0,
            "complexity": "medium",
            "risk_level": "medium"
        },
        "kpi_values": {
            "P1-KPI1": 16.0,   # Time-to-first-workload: 16 days (RISK)
            "P1-KPI2": 88.0,
            "P2-KPI1": 2.1,    # RMA rate: 2.1% (RISK)
            "P2-KPI2": 8500,
            "P2-KPI4": 99.2,
            "P3-KPI1": 62.0,   # GPU utilization: 62% (RISK)
            "P3-KPI2": 87.0,
            "P5-KPI1": 68.0,
            "P5-KPI2": 6.0,
            "P5-KPI7": 55.0
        },
        "expected_health": 68.0,
        "expected_status": "risk"
    },
    
    {
        "account_id": 5,
        "account_name": "ML Solutions Inc",
        "customer_id": 105,
        "industry": "ai_infrastructure",
        "region": "Asia-Pacific",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "hybrid",
            "deployment_date": "2025-10-01",
            "days_since_deployment": 92,
            "gpu_count": 16,
            "gpu_model": "A100",
            "cluster_size": 2,
            "total_gpu_memory_gb": 1280,
            "use_case": "recommendation_systems",
            "workload_types": ["inference"],
            "phase": "performance",
            "phase_entered_date": "2025-12-20",
            "partner_tier": "tier_2",
            "var_partner_id": "VAR-008",
            "var_partner_name": "APAC Tech Group",
            "deployment_value": 4000000.0,
            "arr": 800000.0,
            "complexity": "medium",
            "risk_level": "medium"
        },
        "kpi_values": {
            "P1-KPI1": 18.0,
            "P1-KPI2": 85.0,
            "P2-KPI1": 2.3,
            "P2-KPI4": 98.8,
            "P3-KPI1": 58.0,
            "P3-KPI2": 84.0,
            "P5-KPI1": 65.0,
            "P5-KPI2": 4.0,
            "P5-KPI7": 48.0
        },
        "expected_health": 64.0,
        "expected_status": "risk"
    },
    
    {
        "account_id": 6,
        "account_name": "IntelliTech Systems",
        "customer_id": 106,
        "industry": "ai_infrastructure",
        "region": "US-West",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-11-01",
            "days_since_deployment": 61,
            "gpu_count": 16,
            "gpu_model": "H100",
            "cluster_size": 2,
            "total_gpu_memory_gb": 1280,
            "use_case": "llm_inference",
            "workload_types": ["inference"],
            "phase": "deployment",
            "phase_entered_date": "2025-11-01",
            "partner_tier": "direct",
            "deployment_value": 4500000.0,
            "complexity": "medium",
            "risk_level": "medium"
        },
        "kpi_values": {
            "P1-KPI1": 17.0,
            "P1-KPI2": 90.0,
            "P1-KPI4": 42.0,
            "P2-KPI1": 1.8,
            "P2-KPI4": 99.3,
            "P3-KPI1": 60.0,
            "P3-KPI2": 88.0,
            "P5-KPI1": 55.0,
            "P5-KPI2": 8.0,
            "P5-KPI7": 52.0
        },
        "expected_health": 66.0,
        "expected_status": "risk"
    },
    
    {
        "account_id": 7,
        "account_name": "Neural Networks Ltd",
        "customer_id": 107,
        "industry": "ai_infrastructure",
        "region": "Europe",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "colocation",
            "deployment_date": "2025-10-15",
            "days_since_deployment": 78,
            "gpu_count": 20,
            "gpu_model": "A100",
            "cluster_size": 2,
            "total_gpu_memory_gb": 1600,
            "use_case": "llm_training",
            "workload_types": ["training"],
            "phase": "deployment",
            "phase_entered_date": "2025-10-15",
            "partner_tier": "tier_1",
            "var_partner_id": "VAR-003",
            "var_partner_name": "European AI Partners",
            "deployment_value": 5000000.0,
            "complexity": "medium",
            "risk_level": "medium"
        },
        "kpi_values": {
            "P1-KPI1": 19.0,
            "P1-KPI2": 87.0,
            "P1-KPI4": 38.0,
            "P2-KPI1": 2.0,
            "P2-KPI4": 99.0,
            "P3-KPI1": 64.0,
            "P3-KPI2": 86.0,
            "P5-KPI1": 62.0,
            "P5-KPI2": 7.0,
            "P5-KPI7": 50.0
        },
        "expected_health": 67.0,
        "expected_status": "risk"
    },
    
    # ========================================
    # AT-RISK / CRITICAL (3 accounts)
    # ========================================
    
    {
        "account_id": 8,
        "account_name": "StartupAI Ventures",
        "customer_id": 108,
        "industry": "ai_infrastructure",
        "region": "US-East",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-11-15",
            "days_since_deployment": 47,
            "gpu_count": 8,
            "gpu_model": "A100",
            "cluster_size": 1,
            "total_gpu_memory_gb": 640,
            "use_case": "research",
            "workload_types": ["training"],
            "phase": "deployment",
            "phase_entered_date": "2025-11-15",
            "partner_tier": "direct",
            "deployment_value": 2000000.0,
            "complexity": "low",
            "risk_level": "high"
        },
        "kpi_values": {
            "P1-KPI1": 28.0,   # Time-to-first-workload: 28 days (CRITICAL)
            "P1-KPI2": 78.0,
            "P1-KPI4": 52.0,
            "P2-KPI1": 3.2,    # RMA rate: 3.2% (CRITICAL)
            "P2-KPI2": 5500,
            "P2-KPI3": 4,      # Critical incidents: 4
            "P2-KPI4": 98.2,
            "P3-KPI1": 42.0,   # GPU utilization: 42% (CRITICAL)
            "P3-KPI2": 76.0,
            "P5-KPI1": 38.0,
            "P5-KPI2": -2.0,   # Negative growth
            "P5-KPI7": 22.0
        },
        "expected_health": 42.0,
        "expected_status": "critical"
    },
    
    {
        "account_id": 9,
        "account_name": "Legacy Systems Co",
        "customer_id": 109,
        "industry": "ai_infrastructure",
        "region": "US-Central",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "on_premise",
            "deployment_date": "2025-09-01",
            "days_since_deployment": 122,
            "gpu_count": 12,
            "gpu_model": "V100",
            "cluster_size": 2,
            "total_gpu_memory_gb": 384,
            "use_case": "computer_vision",
            "workload_types": ["inference"],
            "phase": "performance",
            "phase_entered_date": "2025-12-01",
            "partner_tier": "tier_2",
            "var_partner_id": "VAR-009",
            "var_partner_name": "Regional Tech VAR",
            "deployment_value": 3000000.0,
            "complexity": "low",
            "risk_level": "critical"
        },
        "kpi_values": {
            "P1-KPI1": 24.0,
            "P1-KPI2": 82.0,
            "P2-KPI1": 2.8,
            "P2-KPI2": 6200,
            "P2-KPI3": 3,
            "P2-KPI4": 98.5,
            "P3-KPI1": 48.0,
            "P3-KPI2": 79.0,
            "P5-KPI1": 42.0,
            "P5-KPI2": 1.0,
            "P5-KPI7": 28.0
        },
        "expected_health": 48.0,
        "expected_status": "critical"
    },
    
    {
        "account_id": 10,
        "account_name": "Budget AI Labs",
        "customer_id": 110,
        "industry": "ai_infrastructure",
        "region": "Asia-Pacific",
        "profile_metadata": {
            "vertical": "dc2_S",
            "deployment_type": "hybrid",
            "deployment_date": "2025-12-01",
            "days_since_deployment": 31,
            "gpu_count": 8,
            "gpu_model": "A10",
            "cluster_size": 1,
            "total_gpu_memory_gb": 192,
            "use_case": "llm_inference",
            "workload_types": ["inference"],
            "phase": "deployment",
            "phase_entered_date": "2025-12-01",
            "partner_tier": "tier_2",
            "var_partner_id": "VAR-010",
            "var_partner_name": "APAC Budget Solutions",
            "deployment_value": 1500000.0,
            "complexity": "low",
            "risk_level": "high"
        },
        "kpi_values": {
            "P1-KPI1": 32.0,
            "P1-KPI2": 75.0,
            "P1-KPI4": 58.0,
            "P2-KPI1": 3.5,
            "P2-KPI2": 4800,
            "P2-KPI3": 5,
            "P2-KPI4": 97.8,
            "P3-KPI1": 38.0,
            "P3-KPI2": 72.0,
            "P5-KPI1": 35.0,
            "P5-KPI2": -3.0,
            "P5-KPI7": 18.0
        },
        "expected_health": 38.0,
        "expected_status": "critical"
    }
]

def get_all_sample_accounts():
    """Get all 10 sample accounts"""
    return SAMPLE_ACCOUNTS

def get_accounts_by_status(status):
    """Get accounts filtered by health status"""
    return [acc for acc in SAMPLE_ACCOUNTS if acc.get('expected_status') == status]

def get_accounts_by_phase(phase):
    """Get accounts filtered by journey phase"""
    return [acc for acc in SAMPLE_ACCOUNTS 
            if acc['profile_metadata'].get('phase') == phase]

def get_account_by_id(account_id):
    """Get a specific account by ID"""
    for acc in SAMPLE_ACCOUNTS:
        if acc['account_id'] == account_id:
            return acc
    return None

def get_summary_stats():
    """Get summary statistics of sample accounts"""
    return {
        "total_accounts": len(SAMPLE_ACCOUNTS),
        "by_status": {
            "healthy": len(get_accounts_by_status("healthy")),
            "risk": len(get_accounts_by_status("risk")),
            "critical": len(get_accounts_by_status("critical"))
        },
        "by_phase": {
            "deployment": len(get_accounts_by_phase("deployment")),
            "performance": len(get_accounts_by_phase("performance")),
            "excellence": len(get_accounts_by_phase("excellence"))
        },
        "total_deployment_value": sum(
            acc['profile_metadata'].get('deployment_value', 0) 
            for acc in SAMPLE_ACCOUNTS
        ),
        "total_arr": sum(
            acc['profile_metadata'].get('arr', 0) 
            for acc in SAMPLE_ACCOUNTS
        )
    }

if __name__ == "__main__":
    # Print summary
    stats = get_summary_stats()
    print("DC2_S Sample Accounts Summary")
    print("=" * 60)
    print(f"Total Accounts: {stats['total_accounts']}")
    print()
    print("By Status:")
    print(f"  Healthy: {stats['by_status']['healthy']}")
    print(f"  Risk: {stats['by_status']['risk']}")
    print(f"  Critical: {stats['by_status']['critical']}")
    print()
    print("By Phase:")
    print(f"  Deployment: {stats['by_phase']['deployment']}")
    print(f"  Performance: {stats['by_phase']['performance']}")
    print(f"  Excellence: {stats['by_phase']['excellence']}")
    print()
    print(f"Total Deployment Value: ${stats['total_deployment_value']:,.0f}")
    print(f"Total ARR: ${stats['total_arr']:,.0f}")
