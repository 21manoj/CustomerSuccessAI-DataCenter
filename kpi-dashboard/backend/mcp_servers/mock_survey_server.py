"""
Mock Survey/Interview MCP Server
Provides qualitative data: NPS, CSAT, VoC interviews, CSM assessments
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


class MockSurveyMCPServer:
    """
    Mock Survey/Interview System
    Provides qualitative KPIs that come from:
    - NPS/CSAT surveys
    - Voice of Customer interviews
    - CSM manual assessments
    """
    
    def __init__(self, customer_id=1):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed")
            
        self.server = Server("mock-surveys")
        self.customer_id = customer_id
        
        # Register handlers
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        
        print(f"Mock Survey MCP Server initialized for customer {customer_id}")
    
    async def list_resources(self):
        """List available survey/interview resources"""
        return [
            Resource(
                uri="surveys://nps_scores",
                name="NPS Survey Results",
                description="Net Promoter Score from customer surveys",
                mimeType="application/json"
            ),
            Resource(
                uri="surveys://csat_scores",
                name="CSAT Survey Results",
                description="Customer Satisfaction scores",
                mimeType="application/json"
            ),
            Resource(
                uri="surveys://interview_notes",
                name="Voice of Customer Interviews",
                description="Qualitative feedback from customer interviews",
                mimeType="application/json"
            ),
            Resource(
                uri="surveys://csm_assessments",
                name="CSM Relationship Assessments",
                description="Manual CSM evaluations and relationship strength",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str):
        """Generate mock survey data from your database"""
        from app import app, db
        from models import Account, KPI, HealthTrend
        
        with app.app_context():
            if uri == "surveys://nps_scores":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                nps_data = []
                for acc in accounts:
                    # Check if account has NPS KPI
                    nps_kpi = KPI.query.filter_by(
                        account_id=acc.account_id
                    ).filter(
                        KPI.kpi_parameter.like('%NPS%')
                    ).first()
                    
                    if nps_kpi and nps_kpi.data:
                        # Use actual NPS from your database
                        try:
                            nps_score = float(nps_kpi.data)
                        except:
                            nps_score = random.randint(-50, 80)
                    else:
                        # Generate realistic NPS
                        nps_score = random.randint(-50, 80)
                    
                    nps_data.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "NPS_Score": nps_score,
                        "Survey_Date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                        "Response_Rate": round(random.uniform(30, 80), 1),
                        "Respondents": random.randint(10, 100),
                        "Promoters": random.randint(5, 40),
                        "Passives": random.randint(5, 30),
                        "Detractors": random.randint(2, 25),
                        "Trend": random.choice(["Improving", "Stable", "Declining"])
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(nps_data, indent=2)
                    }]
                }
            
            elif uri == "surveys://csat_scores":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                csat_data = []
                for acc in accounts:
                    # Check for CSAT KPI
                    csat_kpi = KPI.query.filter_by(
                        account_id=acc.account_id
                    ).filter(
                        KPI.kpi_parameter.like('%CSAT%')
                    ).first()
                    
                    if csat_kpi and csat_kpi.data:
                        try:
                            csat_score = float(csat_kpi.data)
                        except:
                            csat_score = round(random.uniform(1, 5), 1)
                    else:
                        csat_score = round(random.uniform(1, 5), 1)
                    
                    csat_data.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "CSAT_Score": csat_score,
                        "Survey_Date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                        "Response_Rate": round(random.uniform(30, 80), 1),
                        "Very_Satisfied": random.randint(10, 40),
                        "Satisfied": random.randint(15, 35),
                        "Neutral": random.randint(5, 20),
                        "Dissatisfied": random.randint(2, 15),
                        "Very_Dissatisfied": random.randint(0, 10)
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(csat_data, indent=2)
                    }]
                }
            
            elif uri == "surveys://interview_notes":
                accounts = Account.query.filter_by(customer_id=self.customer_id).limit(10).all()
                
                interview_data = []
                for acc in accounts:
                    interview_data.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "Interview_Date": (datetime.now() - timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d"),
                        "Interviewer": random.choice(["CSM Team", "Product Manager", "VP Customer Success"]),
                        
                        # Qualitative insights
                        "Executive_Sentiment": random.choice(["Very Positive", "Positive", "Neutral", "Concerned", "Negative"]),
                        "Perceived_Value": random.choice(["Exceptional", "High", "Medium", "Low"]),
                        "Renewal_Intent": random.choice(["Definite Renewal", "Likely Renewal", "Uncertain", "At Risk"]),
                        
                        # Interview quotes (would be actual transcripts)
                        "Key_Quote": random.choice([
                            "The product saves us 10 hours per week",
                            "Our team is much more productive now",
                            "We're seeing ROI within 3 months",
                            "Missing some key features we need",
                            "Support response time needs improvement"
                        ]),
                        "Main_Concern": random.choice([
                            "Cost justification for renewal",
                            "Need more training resources",
                            "Missing integrations with our systems",
                            "None - very satisfied with the product"
                        ]),
                        
                        # Relationship indicators
                        "Champion_Identified": random.choice([True, False]),
                        "Executive_Sponsor": random.choice([True, False]),
                        "Internal_Advocate": random.choice([True, False]),
                        "Expansion_Interest": random.choice(["High", "Medium", "Low", "None"])
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(interview_data, indent=2)
                    }]
                }
            
            elif uri == "surveys://csm_assessments":
                accounts = Account.query.filter_by(customer_id=self.customer_id).all()
                
                csm_data = []
                for acc in accounts:
                    # Get health trend to inform assessment
                    health = HealthTrend.query.filter_by(
                        account_id=acc.account_id
                    ).order_by(
                        HealthTrend.year.desc(),
                        HealthTrend.month.desc()
                    ).first()
                    
                    health_score = float(health.overall_health_score) if health else 70
                    
                    csm_data.append({
                        "AccountId": f"SF_{acc.account_id}",
                        "AccountName": acc.account_name,
                        "Assessment_Date": (datetime.now() - timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d"),
                        "CSM_Name": random.choice(["Jane Smith", "John Doe", "Sarah Wilson"]),
                        
                        # CSM subjective ratings (1-5 scale)
                        "Relationship_Strength": min(5, max(1, int(health_score / 20))),
                        "Business_Alignment": random.randint(2, 5),
                        "Product_Fit": random.randint(2, 5),
                        "Communication_Quality": random.randint(2, 5),
                        
                        # CSM assessment
                        "Expansion_Potential": random.choice(["High", "Medium", "Low", "None"]),
                        "Churn_Risk": "High" if health_score < 60 else ("Medium" if health_score < 75 else "Low"),
                        
                        # CSM notes (free text)
                        "Notes": random.choice([
                            "Strong relationship with CTO. Looking to expand to new department in Q1.",
                            "Recent executive turnover. Need to rebuild relationships.",
                            "Very satisfied. Using product across entire organization.",
                            "Concerned about pricing for renewal. Need to demonstrate ROI."
                        ]),
                        "Risk_Factors": random.choice([
                            "Budget cuts announced",
                            "Champion leaving company",
                            "Competitor evaluation in progress",
                            "None identified"
                        ]),
                        
                        # Action items
                        "Recommended_Actions": random.choice([
                            "Schedule executive business review",
                            "Provide additional training",
                            "Start VoC Sprint",
                            "Continue current engagement strategy"
                        ])
                    })
                
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(csm_data, indent=2)
                    }]
                }
    
    async def list_tools(self):
        """Available survey/interview actions"""
        return [
            Tool(
                name="send_nps_survey",
                description="Send NPS survey to account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "email_list": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["account_id"]
                }
            ),
            Tool(
                name="schedule_interview",
                description="Schedule VoC interview",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "date": {"type": "string"},
                        "participants": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["account_id", "date"]
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict):
        """Execute survey/interview actions (mock)"""
        timestamp = datetime.now().isoformat()
        
        if name == "send_nps_survey":
            account_id = arguments['account_id']
            log_msg = f"[{timestamp}] MOCK SURVEY: Sent NPS survey to {account_id}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ NPS survey sent to account {account_id}"
                }]
            }
        
        elif name == "schedule_interview":
            account_id = arguments['account_id']
            date = arguments['date']
            
            log_msg = f"[{timestamp}] MOCK SURVEY: Scheduled interview for {account_id} on {date}"
            print(log_msg)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Interview scheduled for {date}"
                }]
            }


async def main():
    """Run the mock Survey MCP server"""
    import asyncio
    
    if not MCP_AVAILABLE:
        print("❌ MCP SDK not installed. Install with: pip install mcp")
        return
    
    print("=" * 60)
    print("Mock Survey/Interview MCP Server")
    print("=" * 60)
    print("Providing NPS, CSAT, VoC, and CSM assessment data")
    print("Port: stdio (MCP protocol)")
    print("")
    
    server = MockSurveyMCPServer(customer_id=1)
    await server.server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

