"""
Mock ServiceNow MCP Server
Generates realistic support ticket data based on account KPIs
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import json
import random

try:
    from mcp.server import Server
    from mcp.types import Resource, Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️  MCP not installed. Run: pip install mcp")


class MockServiceNowMCPServer:
    """
    Mock ServiceNow ITSM Server
    Generates support tickets based on account health and KPI data
    """
    
    def __init__(self, customer_id=1):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed")
            
        self.server = Server("mock-servicenow")
        self.customer_id = customer_id
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        
        print(f"Mock ServiceNow MCP Server initialized for customer {customer_id}")
    
    async def list_resources(self):
        """List available ServiceNow resources"""
        return [
            Resource(
                uri="servicenow://tickets",
                name="Support Tickets",
                description="All support tickets and incidents",
                mimeType="application/json"
            ),
            Resource(
                uri="servicenow://sla_breaches",
                name="SLA Breaches",
                description="Tickets with SLA violations",
                mimeType="application/json"
            ),
            Resource(
                uri="servicenow://escalations",
                name="Escalated Tickets",
                description="Tickets escalated to management",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str):
        """Generate mock ServiceNow data from your database"""
        from app import app, db
        from models import Account, KPI
        
        with app.app_context():
            if uri == "servicenow://tickets":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                tickets = []
                for acc in accounts:
                    # Generate 3-10 tickets per account
                    num_tickets = random.randint(3, 10)
                    
                    # Get KPIs to determine ticket severity
                    kpis = KPI.query.filter_by(account_id=acc.account_id).all()
                    critical_kpis = [k for k in kpis if k.impact_level == 'Critical']
                    
                    for i in range(num_tickets):
                        created = datetime.now() - timedelta(days=random.randint(1, 90))
                        resolved = None
                        state = random.choice(["New", "In Progress", "Resolved", "Closed"])
                        
                        if state in ["Resolved", "Closed"]:
                            resolved = created + timedelta(hours=random.randint(1, 72))
                        
                        # Higher ticket severity for accounts with critical KPIs
                        if len(critical_kpis) > 3:
                            priority = random.choice(["1-Critical", "2-High", "2-High", "3-Medium"])
                        else:
                            priority = random.choice(["2-High", "3-Medium", "3-Medium", "4-Low"])
                        
                        tickets.append({
                            "Number": f"INC{acc.account_id:04d}{i:04d}",
                            "AccountId": f"SF_{acc.account_id}",
                            "AccountName": acc.account_name,
                            "ShortDescription": random.choice([
                                "Performance degradation in production",
                                "API timeout errors",
                                "Login authentication failure",
                                "Data sync issues",
                                "Feature not working as expected",
                                "Integration error with third-party system",
                                "Report generation timeout",
                                "Dashboard loading slowly"
                            ]),
                            "Priority": priority,
                            "State": state,
                            "CreatedDate": created.isoformat(),
                            "ResolvedDate": resolved.isoformat() if resolved else None,
                            "SLA_Breach": random.random() < 0.15,  # 15% breach rate
                            "Escalated": priority == "1-Critical" and random.random() < 0.3,
                            "Category": random.choice(["Technical", "Configuration", "Enhancement", "Question"]),
                            "AssignedTo": random.choice(["Support Team", "Engineering", "Customer Success"])
                        })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(tickets, indent=2)
                    }]
                }
            
            elif uri == "servicenow://sla_breaches":
                # Filter to SLA breaches only
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                breaches = []
                for acc in accounts:
                    num_breaches = random.randint(0, 5)
                    
                    for i in range(num_breaches):
                        created = datetime.now() - timedelta(days=random.randint(1, 30))
                        
                        breaches.append({
                            "Number": f"INC{acc.account_id:04d}{i:04d}",
                            "AccountId": f"SF_{acc.account_id}",
                            "AccountName": acc.account_name,
                            "Priority": random.choice(["1-Critical", "2-High"]),
                            "SLA_Type": random.choice(["Response", "Resolution"]),
                            "SLA_Target": "2 hours",
                            "Actual_Time": f"{random.randint(3, 48)} hours",
                            "Breach_Amount": f"{random.randint(1, 24)} hours",
                            "CreatedDate": created.isoformat()
                        })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(breaches, indent=2)
                    }]
                }
            
            elif uri == "servicenow://escalations":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                escalations = []
                for acc in accounts:
                    if random.random() < 0.4:  # 40% of accounts have escalations
                        escalations.append({
                            "Number": f"INC{acc.account_id:04d}0001",
                            "AccountId": f"SF_{acc.account_id}",
                            "AccountName": acc.account_name,
                            "Escalated_To": random.choice(["VP Engineering", "CTO", "CEO"]),
                            "Reason": random.choice([
                                "Customer threatening churn",
                                "Critical production issue",
                                "Repeated SLA breaches",
                                "Executive escalation"
                            ]),
                            "EscalatedDate": (datetime.now() - timedelta(days=random.randint(1, 14))).isoformat()
                        })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(escalations, indent=2)
                    }]
                }
    
    async def list_tools(self):
        """Available ServiceNow actions"""
        return [
            Tool(
                name="create_ticket",
                description="Create a new support ticket in ServiceNow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["1-Critical", "2-High", "3-Medium", "4-Low"]}
                    },
                    "required": ["account_id", "subject", "priority"]
                }
            ),
            Tool(
                name="update_ticket_status",
                description="Update ticket status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_number": {"type": "string"},
                        "status": {"type": "string", "enum": ["New", "In Progress", "Resolved", "Closed"]}
                    },
                    "required": ["ticket_number", "status"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict):
        """Execute ServiceNow actions (mock - logs only)"""
        timestamp = datetime.now().isoformat()
        
        if name == "create_ticket":
            ticket_num = f"INC{random.randint(10000, 99999)}"
            log_msg = f"[{timestamp}] MOCK SN: Created ticket {ticket_num}: {arguments['subject']}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Created ticket {ticket_num}: {arguments['subject']}"
                }]
            }
        
        elif name == "update_ticket_status":
            ticket = arguments['ticket_number']
            status = arguments['status']
            
            log_msg = f"[{timestamp}] MOCK SN: Updated {ticket} to {status}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Updated ticket {ticket} to {status}"
                }]
            }


async def main():
    """Run the mock ServiceNow MCP server"""
    import asyncio
    
    if not MCP_AVAILABLE:
        print("❌ MCP SDK not installed. Install with: pip install mcp")
        return
    
    print("=" * 60)
    print("Mock ServiceNow MCP Server")
    print("=" * 60)
    print("Generating support ticket data from SQLite database")
    print("Port: stdio (MCP protocol)")
    print("")
    
    server = MockServiceNowMCPServer(customer_id=1)
    await server.server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

