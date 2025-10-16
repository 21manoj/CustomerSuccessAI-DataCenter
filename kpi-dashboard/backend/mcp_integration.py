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
        """Connect to a specific MCP server"""
        import os
        
        server_map = {
            'salesforce': 'mock_salesforce_server.py',
            'servicenow': 'mock_servicenow_server.py',
            'surveys': 'mock_survey_server.py'
        }
        
        if system not in server_map:
            logger.warning(f"Unknown MCP system: {system}")
            return
        
        script_path = os.path.join(
            os.path.dirname(__file__),
            'mcp_servers',
            server_map[system]
        )
        
        if not os.path.exists(script_path):
            logger.error(f"MCP server script not found: {script_path}")
            return
        
        # Note: Actual connection would use stdio_client
        # For now, we'll simulate the connection
        self.sessions[system] = {
            'connected': True,
            'script': script_path,
            'connected_at': datetime.now().isoformat()
        }
        
        logger.info(f"Connected to {system} MCP server")
    
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
        """Fetch data from a specific MCP server"""
        # For mock implementation, we'll call the server directly
        from app import app, db
        from models import Account, KPI, HealthTrend
        
        with app.app_context():
            account = Account.query.get(account_id)
            if not account:
                return {'error': 'Account not found'}
            
            if system == 'salesforce':
                # Simulate Salesforce data
                return {
                    'account': {
                        'Id': f'SF_{account_id}',
                        'Name': account.account_name,
                        'ARR__c': float(account.revenue) if account.revenue else 0,
                        'Industry': account.industry,
                        'Region__c': account.region
                    },
                    'opportunity': {
                        'StageName': 'Renewal',
                        'CloseDate': '2026-03-15',
                        'Probability': 85
                    }
                }
            
            elif system == 'servicenow':
                # Generate mock tickets
                import random
                num_tickets = random.randint(2, 8)
                tickets = []
                
                for i in range(num_tickets):
                    tickets.append({
                        'Number': f'INC{account_id:04d}{i:04d}',
                        'Priority': random.choice(['1-Critical', '2-High', '3-Medium', '4-Low']),
                        'State': random.choice(['New', 'In Progress', 'Resolved']),
                        'ShortDescription': random.choice([
                            'Performance issue',
                            'Feature request',
                            'Configuration help'
                        ])
                    })
                
                return {'tickets': tickets, 'count': len(tickets)}
            
            elif system == 'surveys':
                # Get NPS/CSAT from KPIs if available
                nps_kpi = KPI.query.filter_by(account_id=account_id).filter(
                    KPI.kpi_parameter.like('%NPS%')
                ).first()
                
                nps_score = float(nps_kpi.data) if nps_kpi and nps_kpi.data else random.randint(-50, 80)
                
                return {
                    'nps': {
                        'score': nps_score,
                        'survey_date': datetime.now().strftime('%Y-%m-%d'),
                        'response_rate': round(random.uniform(40, 80), 1)
                    },
                    'csat': {
                        'score': round(random.uniform(2.5, 4.8), 1),
                        'trend': 'stable'
                    }
                }
        
        return {}
    
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

