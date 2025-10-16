"""
Mock Salesforce MCP Server
Provides CRM and usage data from your SQLite database
No external Salesforce account needed for testing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import json
import random

# MCP Server (will be installed separately)
try:
    from mcp.server import Server
    from mcp.types import Resource, Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️  MCP not installed. Run: pip install mcp")

class MockSalesforceMCPServer:
    """
    Mock Salesforce MCP Server
    Uses your existing SQLite database to simulate Salesforce CRM data
    """
    
    def __init__(self, customer_id=1):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed")
            
        self.server = Server("mock-salesforce")
        self.customer_id = customer_id
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        
        print(f"Mock Salesforce MCP Server initialized for customer {customer_id}")
    
    async def list_resources(self):
        """List available Salesforce-like resources"""
        return [
            Resource(
                uri="salesforce://accounts",
                name="Customer Accounts",
                description=f"All customer accounts from CRM",
                mimeType="application/json"
            ),
            Resource(
                uri="salesforce://opportunities",
                name="Sales Opportunities",
                description="Renewal and expansion opportunities",
                mimeType="application/json"
            ),
            Resource(
                uri="salesforce://usage_metrics",
                name="Product Usage Metrics",
                description="Daily/monthly active users, feature adoption",
                mimeType="application/json"
            ),
            Resource(
                uri="salesforce://contracts",
                name="Contract Information",
                description="Contract dates, terms, and values",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str):
        """Fetch data from SQLite database (simulating Salesforce)"""
        from app import app, db
        from models import Account, KPI
        
        with app.app_context():
            if uri == "salesforce://accounts":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                data = []
                for acc in accounts:
                    data.append({
                        "Id": f"SF_{acc.account_id}",
                        "Name": acc.account_name,
                        "ARR__c": float(acc.revenue) if acc.revenue else 0,
                        "Industry": acc.industry,
                        "Region__c": acc.region,
                        "Account_Status__c": acc.account_status,
                        "Type": "Customer",
                        "CreatedDate": acc.created_at.isoformat() if acc.created_at else None
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2)
                    }]
                }
            
            elif uri == "salesforce://opportunities":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                opportunities = []
                for acc in accounts:
                    # Generate mock renewal opportunity
                    renewal_date = datetime.now() + timedelta(days=random.randint(30, 365))
                    
                    opportunities.append({
                        "Id": f"OPP_{acc.account_id}",
                        "Name": f"{acc.account_name} - FY26 Renewal",
                        "AccountId": f"SF_{acc.account_id}",
                        "Amount": float(acc.revenue) if acc.revenue else 0,
                        "CloseDate": renewal_date.strftime("%Y-%m-%d"),
                        "StageName": random.choice(["Renewal", "Negotiation", "Commit", "Closed Won"]),
                        "Probability": random.randint(60, 95),
                        "Type": "Renewal",
                        "ForecastCategory": "Commit" if random.random() > 0.3 else "Best Case"
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(opportunities, indent=2)
                    }]
                }
            
            elif uri == "salesforce://usage_metrics":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                usage_data = []
                for acc in accounts:
                    # Generate realistic usage metrics
                    mau = random.randint(50, 500)
                    dau = int(mau * random.uniform(0.15, 0.35))  # DAU/MAU ratio
                    
                    usage_data.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "Monthly_Active_Users__c": mau,
                        "Daily_Active_Users__c": dau,
                        "DAU_MAU_Ratio__c": round((dau / mau * 100), 1),
                        "Feature_Adoption_Rate__c": round(random.uniform(40, 95), 1),
                        "API_Calls_Last_Month__c": random.randint(1000, 50000),
                        "Login_Frequency__c": round(random.uniform(1, 10), 1),
                        "Last_Login__c": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat()
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(usage_data, indent=2)
                    }]
                }
            
            elif uri == "salesforce://contracts":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                contracts = []
                for acc in accounts:
                    start_date = datetime.now() - timedelta(days=random.randint(200, 600))
                    end_date = start_date + timedelta(days=365)
                    
                    contracts.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "Contract_Start__c": start_date.strftime("%Y-%m-%d"),
                        "Contract_End__c": end_date.strftime("%Y-%m-%d"),
                        "Contract_Value__c": float(acc.revenue) if acc.revenue else 0,
                        "Payment_Terms__c": random.choice(["Annual", "Quarterly", "Monthly"]),
                        "Auto_Renewal__c": random.choice([True, False]),
                        "Contract_Type__c": "Enterprise License"
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(contracts, indent=2)
                    }]
                }
    
    async def list_tools(self):
        """Available Salesforce actions"""
        return [
            Tool(
                name="update_health_score",
                description="Update account health score in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "Salesforce Account ID (SF_XXX)"},
                        "health_score": {"type": "number", "minimum": 0, "maximum": 100}
                    },
                    "required": ["account_id", "health_score"]
                }
            ),
            Tool(
                name="create_task",
                description="Create a task/action item in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["High", "Medium", "Low"]}
                    },
                    "required": ["account_id", "subject"]
                }
            ),
            Tool(
                name="update_opportunity_stage",
                description="Update opportunity stage in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "opportunity_id": {"type": "string"},
                        "stage": {"type": "string", "enum": ["Renewal", "Negotiation", "Commit", "Closed Won", "Closed Lost"]}
                    },
                    "required": ["opportunity_id", "stage"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict):
        """Execute Salesforce actions (mock - just logs)"""
        timestamp = datetime.now().isoformat()
        
        if name == "update_health_score":
            account_id = arguments['account_id']
            health_score = arguments['health_score']
            
            log_msg = f"[{timestamp}] MOCK SF: Updated {account_id} health score to {health_score}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Updated health score to {health_score} for account {account_id}"
                }]
            }
        
        elif name == "create_task":
            account_id = arguments['account_id']
            subject = arguments['subject']
            priority = arguments.get('priority', 'Medium')
            
            task_id = f"TASK_{random.randint(10000, 99999)}"
            log_msg = f"[{timestamp}] MOCK SF: Created task {task_id}: {subject} (Priority: {priority})"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Created task {task_id}: {subject}"
                }]
            }
        
        elif name == "update_opportunity_stage":
            opp_id = arguments['opportunity_id']
            stage = arguments['stage']
            
            log_msg = f"[{timestamp}] MOCK SF: Updated {opp_id} stage to {stage}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Updated opportunity stage to {stage}"
                }]
            }


async def main():
    """Run the mock Salesforce MCP server"""
    import asyncio
    
    if not MCP_AVAILABLE:
        print("❌ MCP SDK not installed. Install with: pip install mcp")
        return
    
    print("=" * 60)
    print("Mock Salesforce MCP Server")
    print("=" * 60)
    print("Using SQLite database to simulate Salesforce CRM")
    print("Port: stdio (MCP protocol)")
    print("")
    
    server = MockSalesforceMCPServer(customer_id=1)
    await server.server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

