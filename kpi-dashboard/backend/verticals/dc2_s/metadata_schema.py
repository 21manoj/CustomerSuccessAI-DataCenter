#!/usr/bin/env python3
"""
DC2_S Vertical - Metadata Schema
JSON schema for Account.profile_metadata field

Defines the structure of DC2_S-specific data stored in the
existing Account model's profile_metadata JSON field.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# ============================================================
# METADATA SCHEMA DEFINITION
# ============================================================

DC2S_METADATA_SCHEMA = {
    "type": "object",
    "required": ["vertical", "deployment_type", "phase"],
    "properties": {
        # Core identifiers
        "vertical": {
            "type": "string",
            "const": "dc2_S",
            "description": "Vertical identifier - always 'dc2_S'"
        },
        
        # Deployment configuration
        "deployment_type": {
            "type": "string",
            "enum": ["on_premise", "colocation", "hybrid"],
            "description": "Hardware deployment model"
        },
        "deployment_date": {
            "type": "string",
            "format": "date",
            "description": "Date hardware was deployed (YYYY-MM-DD)"
        },
        "days_since_deployment": {
            "type": "integer",
            "minimum": 0,
            "description": "Calculated days since deployment"
        },
        
        # Hardware specifications
        "gpu_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Total number of GPUs deployed"
        },
        "gpu_model": {
            "type": "string",
            "enum": ["H100", "A100", "V100", "A10", "L40", "Other"],
            "description": "Primary GPU model"
        },
        "cluster_size": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of servers in cluster"
        },
        "total_gpu_memory_gb": {
            "type": "number",
            "minimum": 0,
            "description": "Total GPU memory across cluster (GB)"
        },
        "cpu_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Total CPU cores"
        },
        "ram_gb": {
            "type": "number",
            "minimum": 0,
            "description": "Total system RAM (GB)"
        },
        "storage_tb": {
            "type": "number",
            "minimum": 0,
            "description": "Total storage capacity (TB)"
        },
        
        # Use case & workload
        "use_case": {
            "type": "string",
            "enum": [
                "llm_training",
                "llm_inference",
                "computer_vision",
                "recommendation_systems",
                "research",
                "multi_modal",
                "other"
            ],
            "description": "Primary AI/ML use case"
        },
        "workload_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of workload types running"
        },
        
        # Journey phase
        "phase": {
            "type": "string",
            "enum": ["deployment", "performance", "excellence"],
            "description": "Current customer journey phase"
        },
        "phase_entered_date": {
            "type": "string",
            "format": "date",
            "description": "Date entered current phase"
        },
        
        # Partner information
        "partner_tier": {
            "type": "string",
            "enum": ["tier_1", "tier_2", "direct"],
            "description": "Partner tier classification"
        },
        "var_partner_id": {
            "type": "string",
            "description": "VAR partner identifier (if applicable)"
        },
        "var_partner_name": {
            "type": "string",
            "description": "VAR partner company name"
        },
        
        # Financial
        "deployment_value": {
            "type": "number",
            "minimum": 0,
            "description": "Initial deployment contract value (USD)"
        },
        "arr": {
            "type": "number",
            "minimum": 0,
            "description": "Annual recurring revenue (USD)"
        },
        "expansion_opportunity_value": {
            "type": "number",
            "minimum": 0,
            "description": "Estimated Phase 2 expansion value (USD)"
        },
        
        # Complexity & risk
        "complexity": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Deployment complexity level"
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Current risk assessment"
        },
        
        # Custom fields
        "custom_fields": {
            "type": "object",
            "description": "Customer-specific custom data"
        },
        
        # Tracking
        "last_updated": {
            "type": "string",
            "format": "date-time",
            "description": "Last metadata update timestamp"
        }
    }
}

# ============================================================
# DEFAULT VALUES
# ============================================================

DC2S_METADATA_DEFAULTS = {
    "vertical": "dc2_S",
    "deployment_type": "on_premise",
    "phase": "deployment",
    "gpu_count": 0,
    "gpu_model": "H100",
    "cluster_size": 1,
    "use_case": "llm_training",
    "workload_types": [],
    "partner_tier": "direct",
    "complexity": "medium",
    "risk_level": "low",
    "custom_fields": {},
    "last_updated": None  # Will be set on creation
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_metadata(
    deployment_type: str = "on_premise",
    gpu_count: int = 0,
    gpu_model: str = "H100",
    use_case: str = "llm_training",
    deployment_value: float = 0.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a valid DC2_S metadata object
    
    Args:
        deployment_type: Hardware deployment model
        gpu_count: Number of GPUs
        gpu_model: GPU model type
        use_case: Primary AI/ML use case
        deployment_value: Contract value
        **kwargs: Additional metadata fields
        
    Returns:
        Valid metadata dictionary
    """
    metadata = DC2S_METADATA_DEFAULTS.copy()
    
    # Update with provided values
    metadata.update({
        "deployment_type": deployment_type,
        "gpu_count": gpu_count,
        "gpu_model": gpu_model,
        "use_case": use_case,
        "deployment_value": deployment_value,
        "last_updated": datetime.utcnow().isoformat()
    })
    
    # Add any additional fields
    metadata.update(kwargs)
    
    return metadata

def validate_metadata(metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate metadata against schema
    
    Args:
        metadata: Metadata dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required fields
    required = ["vertical", "deployment_type", "phase"]
    for field in required:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")
    
    # Check vertical identifier
    if metadata.get("vertical") != "dc2_S":
        errors.append("vertical must be 'dc2_S'")
    
    # Check enum values
    if "deployment_type" in metadata:
        if metadata["deployment_type"] not in ["on_premise", "colocation", "hybrid"]:
            errors.append("Invalid deployment_type")
    
    if "phase" in metadata:
        if metadata["phase"] not in ["deployment", "performance", "excellence"]:
            errors.append("Invalid phase")
    
    if "use_case" in metadata:
        valid_use_cases = ["llm_training", "llm_inference", "computer_vision", 
                          "recommendation_systems", "research", "multi_modal", "other"]
        if metadata["use_case"] not in valid_use_cases:
            errors.append("Invalid use_case")
    
    # Check numeric ranges
    if "gpu_count" in metadata:
        if not isinstance(metadata["gpu_count"], int) or metadata["gpu_count"] < 0:
            errors.append("gpu_count must be non-negative integer")
    
    if "deployment_value" in metadata:
        if not isinstance(metadata["deployment_value"], (int, float)) or metadata["deployment_value"] < 0:
            errors.append("deployment_value must be non-negative number")
    
    return (len(errors) == 0, errors)

def update_metadata(
    existing_metadata: Dict[str, Any],
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update existing metadata with new values
    
    Args:
        existing_metadata: Current metadata
        updates: Fields to update
        
    Returns:
        Updated metadata dictionary
    """
    updated = existing_metadata.copy()
    updated.update(updates)
    updated["last_updated"] = datetime.utcnow().isoformat()
    
    # Validate updated metadata
    is_valid, errors = validate_metadata(updated)
    if not is_valid:
        raise ValueError(f"Invalid metadata after update: {', '.join(errors)}")
    
    return updated

def get_metadata_field(metadata: Dict[str, Any], field: str, default: Any = None) -> Any:
    """Safely get a metadata field with default"""
    return metadata.get(field, default)

def set_metadata_field(
    metadata: Dict[str, Any],
    field: str,
    value: Any
) -> Dict[str, Any]:
    """
    Set a metadata field and return updated metadata
    
    Args:
        metadata: Current metadata
        field: Field name to set
        value: New value
        
    Returns:
        Updated metadata
    """
    return update_metadata(metadata, {field: value})

def calculate_days_since_deployment(deployment_date: str) -> int:
    """
    Calculate days since deployment
    
    Args:
        deployment_date: Deployment date (YYYY-MM-DD)
        
    Returns:
        Number of days since deployment
    """
    try:
        deploy_dt = datetime.fromisoformat(deployment_date)
        delta = datetime.utcnow() - deploy_dt
        return delta.days
    except (ValueError, TypeError):
        return 0

def auto_calculate_fields(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-calculate derived fields in metadata
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        Metadata with calculated fields
    """
    updated = metadata.copy()
    
    # Calculate days since deployment
    if "deployment_date" in metadata:
        updated["days_since_deployment"] = calculate_days_since_deployment(
            metadata["deployment_date"]
        )
    
    # Calculate total GPU memory
    if "gpu_count" in metadata and "gpu_model" in metadata:
        # GPU memory per model (GB)
        gpu_memory_map = {
            "H100": 80,
            "A100": 80,
            "V100": 32,
            "A10": 24,
            "L40": 48
        }
        memory_per_gpu = gpu_memory_map.get(metadata["gpu_model"], 40)
        updated["total_gpu_memory_gb"] = metadata["gpu_count"] * memory_per_gpu
    
    return updated

# ============================================================
# EXAMPLE METADATA OBJECTS
# ============================================================

EXAMPLE_METADATA = {
    "small_deployment": {
        "vertical": "dc2_S",
        "deployment_type": "on_premise",
        "deployment_date": "2025-10-15",
        "days_since_deployment": 78,
        "gpu_count": 8,
        "gpu_model": "H100",
        "cluster_size": 1,
        "total_gpu_memory_gb": 640,
        "use_case": "llm_training",
        "workload_types": ["training", "fine_tuning"],
        "phase": "performance",
        "phase_entered_date": "2025-12-01",
        "partner_tier": "direct",
        "deployment_value": 2000000.0,
        "arr": 0,
        "complexity": "medium",
        "risk_level": "low",
        "custom_fields": {},
        "last_updated": "2026-01-01T00:00:00Z"
    },
    
    "large_deployment": {
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
        "risk_level": "low",
        "custom_fields": {
            "internal_project_code": "ML-INFRA-2025",
            "technical_champion": "Jane Doe",
            "executive_sponsor": "John Smith"
        },
        "last_updated": "2026-01-01T00:00:00Z"
    },
    
    "var_deployment": {
        "vertical": "dc2_S",
        "deployment_type": "colocation",
        "deployment_date": "2025-11-15",
        "days_since_deployment": 47,
        "gpu_count": 16,
        "gpu_model": "A100",
        "cluster_size": 2,
        "total_gpu_memory_gb": 1280,
        "use_case": "computer_vision",
        "workload_types": ["inference"],
        "phase": "deployment",
        "phase_entered_date": "2025-11-15",
        "partner_tier": "tier_2",
        "var_partner_id": "VAR-042",
        "var_partner_name": "Regional AI Solutions",
        "deployment_value": 4500000.0,
        "arr": 0,
        "complexity": "medium",
        "risk_level": "medium",
        "custom_fields": {},
        "last_updated": "2026-01-01T00:00:00Z"
    }
}

# ============================================================
# INTEGRATION WITH ACCOUNT MODEL
# ============================================================

def create_dc2s_account_metadata(**kwargs) -> Dict[str, Any]:
    """
    Create metadata for new DC2_S account
    
    Usage:
        metadata = create_dc2s_account_metadata(
            gpu_count=64,
            gpu_model="H100",
            deployment_value=15000000.0
        )
        
        account = Account(
            customer_id=1,
            account_name="ACME AI Labs",
            industry="ai_infrastructure",
            profile_metadata=metadata
        )
    
    Returns:
        Valid metadata dictionary ready for Account.profile_metadata
    """
    metadata = create_metadata(**kwargs)
    metadata = auto_calculate_fields(metadata)
    
    # Validate before returning
    is_valid, errors = validate_metadata(metadata)
    if not is_valid:
        raise ValueError(f"Invalid metadata: {', '.join(errors)}")
    
    return metadata

def extract_dc2s_fields(profile_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract DC2_S-specific fields from profile_metadata
    
    Args:
        profile_metadata: Account.profile_metadata dict
        
    Returns:
        Dictionary of DC2_S fields
    """
    if profile_metadata.get("vertical") != "dc2_S":
        return {}
    
    return {k: v for k, v in profile_metadata.items() 
            if k in DC2S_METADATA_SCHEMA["properties"]}

# ============================================================
# METADATA EXPORT/IMPORT
# ============================================================

def export_metadata_json(metadata: Dict[str, Any]) -> str:
    """Export metadata as JSON string"""
    return json.dumps(metadata, indent=2)

def import_metadata_json(json_str: str) -> Dict[str, Any]:
    """Import metadata from JSON string"""
    metadata = json.loads(json_str)
    is_valid, errors = validate_metadata(metadata)
    if not is_valid:
        raise ValueError(f"Invalid metadata in JSON: {', '.join(errors)}")
    return metadata
