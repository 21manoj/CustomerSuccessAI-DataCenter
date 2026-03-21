"""
MCP Integration Layer
Manages connections to all MCP servers and provides unified interface
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if MCP is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. MCP features disabled. Install with: pip install mcp")


class MCPIntegration:
    """
    Manages all MCP server connections
    Provides unified interface for AI to access external systems
    """
    
    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        self.sessions = {}
        self.connected = False
        
        if not MCP_AVAILABLE:
            logger.warning("MCP SDK not available")
    
    async def connect_all(self, systems: Optional[List[str]] = None):
        """
        Connect to specified MCP servers
        
        Args:
            systems: List of systems to connect ('salesforce', 'servicenow', 'surveys')
                    If None, connects to all enabled systems
        """
        if not MCP_AVAILABLE:
            return False
        
        if systems is None:
            systems = ['salesforce', 'servicenow', 'surveys']
        
        try:
            for system in systems:
                await self._connect_to_system(system)
            
            self.connected = True
            logger.info(f"Connected to {len(self.sessions)} MCP servers")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MCP servers: {e}")
            return False
    
    async def _connect_to_system(self, system: str):
        """Connect to a specific external system (Salesforce, ServiceNow, etc.)"""
        SUPPORTED_SYSTEMS = {'salesforce', 'servicenow', 'surveys'}

        if system not in SUPPORTED_SYSTEMS:
            logger.warning(f"Unknown MCP system: {system}")
            return

        # TODO: Implement real OAuth/API connections for each system
        # Real integrations coming — SFDC, HubSpot, Zendesk
        logger.info(f"Integration with {system} not yet configured — stub only")
        self.sessions[system] = {
            'connected': False,
            'connected_at': datetime.now().isoformat(),
            'status': 'not_configured'
        }
    
    async def fetch_account_data(self, account_id: int, systems: List[str]) -> Dict[str, Any]:
        """
        Fetch account data from all specified systems
        
        Returns enriched context for AI
        """
        context = {}
        
        for system in systems:
            if system not in self.sessions:
                continue
            
            try:
                data = await self._fetch_from_system(system, account_id)
                context[system] = data
            except Exception as e:
                logger.error(f"Error fetching from {system}: {e}")
                context[system] = {'error': str(e)}
        
        return context
    
    async def _fetch_from_system(self, system: str, account_id: int) -> Dict[str, Any]:
        """Fetch data from a specific external system.

        TODO: Implement real connectors for Salesforce, HubSpot, Zendesk, ServiceNow.
        Each connector should use OAuth tokens stored in CustomerWorkflowConfig.
        """
        session = self.sessions.get(system)
        if not session or session.get('status') == 'not_configured':
            return {'error': f'{system} integration not configured'}

        return {'error': f'{system} connector not yet implemented'}
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        self.sessions.clear()
        self.connected = False
        logger.info("Disconnected from all MCP servers")
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status for all systems"""
        return {
            'connected': self.connected,
            'systems': {
                system: {
                    'connected': True,
                    'connected_at': data.get('connected_at')
                }
                for system, data in self.sessions.items()
            },
            'customer_id': self.customer_id
        }


def is_mcp_enabled(customer_id: int) -> bool:
    """Check if MCP integration is enabled for customer"""
    from models import FeatureToggle
    
    try:
        toggle = FeatureToggle.query.filter_by(
            customer_id=customer_id,
            feature_name='mcp_integration'
        ).first()
        
        return toggle.enabled if toggle else False
    except Exception as e:
        logger.error(f"Error checking MCP feature toggle: {e}")
        return False


def get_mcp_config(customer_id: int) -> Dict[str, bool]:
    """Get MCP system configuration for customer"""
    from models import FeatureToggle
    
    try:
        toggle = FeatureToggle.query.filter_by(
            customer_id=customer_id,
            feature_name='mcp_integration'
        ).first()
        
        if not toggle or not toggle.config:
            return {
                'salesforce': False,
                'servicenow': False,
                'surveys': False
            }
        
        return {
            'salesforce': toggle.config.get('salesforce', False),
            'servicenow': toggle.config.get('servicenow', False),
            'surveys': toggle.config.get('surveys', False)
        }
    except Exception as e:
        logger.error(f"Error getting MCP config: {e}")
        return {
            'salesforce': False,
            'servicenow': False,
            'surveys': False
        }

