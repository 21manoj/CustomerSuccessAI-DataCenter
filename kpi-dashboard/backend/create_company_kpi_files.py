#!/usr/bin/env python3
"""
Create individual KPI files for each of the 25 companies with 59 KPIs each.
"""

import pandas as pd
import json
import random
import os

def create_company_kpi_files():
    """Create individual KPI files for each company"""
    
    # Load corporate metadata
    with open("corporate_metadata.json", "r") as f:
        metadata = json.load(f)
    
    # Define the exact 59 KPIs from the original Excel file
    kpi_structure = {
        "Product Usage KPI": [
            {"kpi_parameter": "Time to First Value (TTFV)", "impact_level": "High", "measurement_frequency": "Weekly"},
            {"kpi_parameter": "Onboarding Completion Rate", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Product Activation Rate", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Customer Onboarding Satisfaction (CSAT)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Support Requests During Onboarding", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Customer Retention Rate", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Churn Rate (inverse)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Share of Wallet", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Employee Productivity (customer usage patterns)", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Operational Efficiency (platform utilization)", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Feature Adoption Rate", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Training Participation Rate", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Knowledge Base Usage", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Learning Path Completion Rate", "impact_level": "Medium", "measurement_frequency": "Monthly"}
        ],
        "Support KPI": [
            {"kpi_parameter": "First Response Time", "impact_level": "High", "measurement_frequency": "Daily"},
            {"kpi_parameter": "Mean Time to Resolution (MTTR)", "impact_level": "High", "measurement_frequency": "Daily"},
            {"kpi_parameter": "Customer Support Satisfaction", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Ticket Volume", "impact_level": "Medium", "measurement_frequency": "Daily"},
            {"kpi_parameter": "Ticket Backlog", "impact_level": "Medium", "measurement_frequency": "Daily"},
            {"kpi_parameter": "First Contact Resolution (FCR)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Escalation Rate", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Support Cost per Ticket", "impact_level": "Low", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Case Deflection Rate", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Customer Effort Score (CES)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Process Cycle Time", "impact_level": "Medium", "measurement_frequency": "Monthly"}
        ],
        "Customer Sentiment KPI": [
            {"kpi_parameter": "Net Promoter Score (NPS)", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Customer Satisfaction (CSAT)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Customer Complaints", "impact_level": "High", "measurement_frequency": "Daily"},
            {"kpi_parameter": "Error Rates (affecting customer experience)", "impact_level": "Medium", "measurement_frequency": "Daily"},
            {"kpi_parameter": "Customer sentiment Trends", "impact_level": "High", "measurement_frequency": "Monthly"}
        ],
        "Business Outcomes KPI": [
            {"kpi_parameter": "Revenue Growth", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Customer Lifetime Value (CLV)", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Upsell and Cross-sell Revenue", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Cost Savings", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Return on Investment (ROI)", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Days Sales Outstanding (DSO)", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Accounts Receivable Turnover", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Cash Conversion Cycle (CCC)", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Invoice Accuracy", "impact_level": "Low", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Payment Terms Compliance", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Collection Effectiveness Index (CEI)", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Gross Revenue Retention (GRR)", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Net Revenue Retention (NRR)", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Renewal Rate", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Expansion Revenue Rate", "impact_level": "High", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Churn by Segment/Persona/Product", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Key Performance Indicators (KPIs)", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Operational Cost Savings", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Cost per Unit", "impact_level": "Medium", "measurement_frequency": "Monthly"}
        ],
        "Relationship Strength KPI": [
            {"kpi_parameter": "Business Review Frequency", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Account Engagement Score", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Churn Risk Flags Triggered", "impact_level": "High", "measurement_frequency": "Weekly"},
            {"kpi_parameter": "Service Level Agreements (SLAs) compliance", "impact_level": "High", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "On-time Delivery Rates", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Benchmarking Results", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Regulatory Compliance", "impact_level": "Medium", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Audit Results", "impact_level": "Low", "measurement_frequency": "Quarterly"},
            {"kpi_parameter": "Cross-functional Task Completion", "impact_level": "Medium", "measurement_frequency": "Monthly"},
            {"kpi_parameter": "Process Improvement Velocity", "impact_level": "Low", "measurement_frequency": "Quarterly"}
        ]
    }
    
    def generate_realistic_data(kpi_info, company_industry):
        """Generate realistic data based on KPI type and company industry"""
        kpi_name = kpi_info["kpi_parameter"].lower()
        
        # Industry-specific adjustments
        if "technology" in company_industry.lower():
            base_multiplier = 1.2
        elif "healthcare" in company_industry.lower():
            base_multiplier = 0.9
        elif "financial" in company_industry.lower():
            base_multiplier = 1.1
        else:
            base_multiplier = 1.0
        
        if "time" in kpi_name or "response" in kpi_name or "resolution" in kpi_name:
            # Time-based metrics
            hours = random.randint(1, 24) * base_multiplier
            return f"{int(hours)} hours"
        elif "rate" in kpi_name or "percentage" in kpi_name or "completion" in kpi_name:
            # Percentage metrics
            percentage = random.randint(65, 98) * base_multiplier
            return f"{min(100, int(percentage))}%"
        elif "satisfaction" in kpi_name or "csat" in kpi_name or "nps" in kpi_name:
            # Satisfaction scores
            score = (random.randint(3, 5) + random.random()) * base_multiplier
            return f"{min(5, round(score, 1))}"
        elif "revenue" in kpi_name or "growth" in kpi_name:
            # Revenue metrics
            growth = random.randint(5, 25) * base_multiplier
            return f"{int(growth)}%"
        elif "cost" in kpi_name or "savings" in kpi_name:
            # Cost metrics
            savings = random.randint(10, 100) * base_multiplier
            return f"${int(savings)}K"
        elif "retention" in kpi_name or "churn" in kpi_name:
            # Retention metrics
            retention = random.randint(85, 98) * base_multiplier
            return f"{min(100, int(retention))}%"
        elif "volume" in kpi_name or "count" in kpi_name:
            # Volume metrics
            volume = random.randint(50, 500) * base_multiplier
            return f"{int(volume)}"
        else:
            # Default
            percentage = random.randint(70, 95) * base_multiplier
            return f"{min(100, int(percentage))}%"
    
    def generate_source_review():
        """Generate realistic source review"""
        sources = ["CSR", "OBR", "System", "Survey", "Analytics"]
        return random.choice(sources)
    
    # Create directory for company files
    os.makedirs("company_kpi_files", exist_ok=True)
    
    created_files = []
    
    # Create KPI file for each company
    for company in metadata["companies"]:
        company_name = company["company_name"]
        company_industry = company["industry"]
        
        # Create Excel file for this company
        filename = f"company_kpi_files/{company_name.lower().replace(' ', '_').replace('&', 'and')}_kpis.xlsx"
        
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            # Add company summary sheet first (will be skipped)
            summary_data = [
                ["Company Summary"],
                ["Company", company_name],
                ["Industry", company_industry],
                ["Revenue", f"${company['revenue']:,}"],
                ["Employees", company["employee_count"]],
                ["Contract Value", f"${company['contract_value']:,}"]
            ]
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False, header=False)
            
            # Group KPIs by category
            categories = {}
            for category, kpis in kpi_structure.items():
                categories[category] = []
                for kpi in kpis:
                    company_kpi = {
                        "category": category,
                        "health_score_component": category.replace(" KPI", ""),
                        "kpi_parameter": kpi["kpi_parameter"],
                        "impact_level": kpi["impact_level"],
                        "measurement_frequency": kpi["measurement_frequency"],
                        "weight": round(random.uniform(0.05, 0.25), 2),
                        "data": generate_realistic_data(kpi, company_industry),
                        "source_review": generate_source_review(),
                        "row_index": len(categories[category]) + 1
                    }
                    categories[category].append(company_kpi)
            
            # Add KPI sheets
            for category, kpis in categories.items():
                sheet_data = []
                # Add header
                sheet_data.append([
                    "Health Score Component", "Weight (%)", "Data", "Source Review", 
                    "KPI/Parameter", "Impact Level", "Measurement Frequency"
                ])
                # Add KPI rows
                for kpi in kpis:
                    sheet_data.append([
                        kpi["health_score_component"],
                        kpi["weight"],
                        kpi["data"],
                        kpi["source_review"],
                        kpi["kpi_parameter"],
                        kpi["impact_level"],
                        kpi["measurement_frequency"]
                    ])
                
                df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
                df.to_excel(writer, sheet_name=category, index=False)
            
            # Add rollup sheet last (will be skipped)
            rollup_data = [
                ["Company Rollup"],
                ["Company", company_name],
                ["Revenue", f"${company['revenue']:,}"],
                ["KPIs", "59"]
            ]
            rollup_df = pd.DataFrame(rollup_data)
            rollup_df.to_excel(writer, sheet_name="Rollup", index=False, header=False)
        
        created_files.append({
            "company_name": company_name,
            "filename": filename,
            "kpi_count": 59
        })
        
        print(f"   ✅ Created: {company_name} ({filename})")
    
    print(f"\n✅ Created {len(created_files)} company KPI files:")
    print(f"   - Directory: company_kpi_files/")
    print(f"   - Files: {len(created_files)}")
    print(f"   - Total KPIs: {len(created_files) * 59}")
    print(f"   - Each file contains exactly 59 KPIs")
    
    return created_files

if __name__ == "__main__":
    create_company_kpi_files() 