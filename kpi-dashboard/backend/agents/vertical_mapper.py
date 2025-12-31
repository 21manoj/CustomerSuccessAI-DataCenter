"""
Vertical Mapping Utility

Maps system vertical values ('saas', 'datacenter') to agent vertical types
('saas_customer_success', 'data_center_infrastructure')
"""

from typing import Optional

# Mapping from system vertical to agent vertical type
VERTICAL_MAPPING = {
    'saas': 'saas_customer_success',
    'datacenter': 'data_center_infrastructure',
    'data_center': 'data_center_infrastructure',  # Alternative spelling
}

# Reverse mapping (for backward compatibility if needed)
AGENT_TO_SYSTEM_VERTICAL = {
    'saas_customer_success': 'saas',
    'data_center_infrastructure': 'datacenter',
}


def map_vertical_to_agent_type(system_vertical: str) -> str:
    """
    Map system vertical to agent vertical type
    
    Args:
        system_vertical: System vertical value ('saas', 'datacenter')
        
    Returns:
        Agent vertical type ('saas_customer_success', 'data_center_infrastructure')
        
    Raises:
        ValueError: If vertical is not recognized
    """
    vertical_lower = system_vertical.lower().strip()
    
    if vertical_lower in VERTICAL_MAPPING:
        return VERTICAL_MAPPING[vertical_lower]
    
    # If already in agent format, return as-is
    if vertical_lower in AGENT_TO_SYSTEM_VERTICAL:
        return vertical_lower
    
    # Default fallback - assume it's already in correct format
    # but log a warning
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Unknown vertical '{system_vertical}', using as-is")
    return vertical_lower


def map_agent_type_to_system(agent_vertical_type: str) -> str:
    """
    Map agent vertical type back to system vertical (reverse mapping)
    
    Args:
        agent_vertical_type: Agent vertical type ('saas_customer_success', etc.)
        
    Returns:
        System vertical value ('saas', 'datacenter')
    """
    agent_lower = agent_vertical_type.lower().strip()
    
    if agent_lower in AGENT_TO_SYSTEM_VERTICAL:
        return AGENT_TO_SYSTEM_VERTICAL[agent_lower]
    
    # Default fallback
    return agent_lower

