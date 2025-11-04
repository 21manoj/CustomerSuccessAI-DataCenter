#!/usr/bin/env python3
"""
Analyze all 59 KPIs and identify which ones are impacted by SKU-based product dimension
for: Product Adoption, Support, and Cross-sell/Upsell opportunities
"""

import json
from health_score_config import KPI_REFERENCE_RANGES, CATEGORY_WEIGHTS

# Define all KPIs with their categories
all_kpis = {
    # Product Usage KPIs
    "Product Usage": [
        "Product Activation Rate",
        "Customer Retention Rate",
        "Onboarding Completion Rate",
        "Time to First Value (TTFV)",
        "Customer Onboarding Satisfaction (CSAT)",
        "Training Participation Rate",
        "Feature Adoption Rate",
        "Knowledge Base Usage",
        "Learning Path Completion Rate",
        "Support Requests During Onboarding",
        "Churn Rate (inverse)",
        "Share of Wallet",
        "Employee Productivity (customer usage patterns)",
        "Operational Efficiency (platform utilization)",
    ],
    # Support KPIs
    "Support": [
        "First Response Time",
        "Mean Time to Resolution (MTTR)",
        "Customer Support Satisfaction",
        "Ticket Volume",
        "Ticket Backlog",
        "Escalation Rate",
        "Support Cost per Ticket",
        "Case Deflection Rate",
        "Customer Effort Score (CES)",
        "Process Cycle Time",
        "First Contact Resolution (FCR)",
    ],
    # Customer Sentiment KPIs
    "Customer Sentiment": [
        "Net Promoter Score (NPS)",
        "Customer Complaints",
        "Error Rates (affecting customer experience)",
        "Customer sentiment Trends",
        "Customer Satisfaction (CSAT)",
        "Relationship Health Score",
    ],
    # Business Outcomes KPIs
    "Business Outcomes": [
        "Revenue Growth",
        "Customer Lifetime Value (CLV)",
        "Upsell and Cross-sell Revenue",
        "Cost Savings",
        "Days Sales Outstanding (DSO)",
        "Accounts Receivable Turnover",
        "Cash Conversion Cycle (CCC)",
        "Invoice Accuracy",
        "Payment Terms Compliance",
        "Collection Effectiveness Index (CEI)",
        "Net Revenue Retention (NRR)",
        "Renewal Rate",
        "Expansion Revenue Rate",
        "Churn by Segment/Persona/Product",
        "Key Performance Indicators (KPIs)",
        "Operational Cost Savings",
        "Cost per Unit",
        "Return on Investment (ROI)",
        "Gross Revenue Retention (GRR)",
        "Contract Renewal Rate",
        "Expansion Revenue",
        "Customer Acquisition Cost",
        "Churn Rate",
        "Average Contract Value",
        "Customer ROI",
        "Market Share",
        "Competitive Win Rate",
    ],
    # Relationship Strength KPIs
    "Relationship Strength": [
        "Business Review Frequency",
        "Account Engagement Score",
        "Churn Risk Flags Triggered",
        "Service Level Agreements (SLAs) compliance",
        "On-time Delivery Rates",
        "Benchmarking Results",
        "Regulatory Compliance",
        "Audit Results",
        "Cross-functional Task Completion",
        "Process Improvement Velocity",
    ]
}

# Analyze which KPIs are impacted by product dimension
def analyze_kpi_impact():
    results = {
        "Product Adoption": {
            "high": [],
            "medium": [],
            "low": []
        },
        "Support": {
            "high": [],
            "medium": [],
            "low": []
        },
        "Cross-sell/Upsell": {
            "high": [],
            "medium": [],
            "low": []
        }
    }
    
    # Product Adoption keywords
    adoption_keywords = ["activation", "onboarding", "feature", "adoption", "training", 
                        "knowledge", "learning", "time to first", "productivity", 
                        "efficiency", "utilization", "usage", "retention"]
    
    # Support keywords
    support_keywords = ["support", "ticket", "response", "resolution", "escalation", 
                       "case", "effort", "satisfaction"]
    
    # Cross-sell/Upsell keywords
    revenue_keywords = ["revenue", "upsell", "cross-sell", "expansion", "nrr", "grr", 
                       "share of wallet", "contract", "renewal", "lifetime value", 
                       "acquisition", "market share"]
    
    for category, kpis in all_kpis.items():
        for kpi in kpis:
            kpi_lower = kpi.lower()
            
            # Check Product Adoption impact
            adoption_count = sum(1 for keyword in adoption_keywords if keyword in kpi_lower)
            if adoption_count >= 2 or any(word in kpi_lower for word in ["activation", "feature adoption", "onboarding"]):
                results["Product Adoption"]["high"].append((category, kpi))
            elif adoption_count == 1:
                results["Product Adoption"]["medium"].append((category, kpi))
            else:
                results["Product Adoption"]["low"].append((category, kpi))
            
            # Check Support impact
            support_count = sum(1 for keyword in support_keywords if keyword in kpi_lower)
            if support_count >= 2 or "support" in kpi_lower or "ticket" in kpi_lower:
                results["Support"]["high"].append((category, kpi))
            elif support_count == 1:
                results["Support"]["medium"].append((category, kpi))
            else:
                results["Support"]["low"].append((category, kpi))
            
            # Check Cross-sell/Upsell impact
            revenue_count = sum(1 for keyword in revenue_keywords if keyword in kpi_lower)
            if revenue_count >= 2 or any(word in kpi_lower for word in ["upsell", "cross-sell", "expansion", "nrr", "grr"]):
                results["Cross-sell/Upsell"]["high"].append((category, kpi))
            elif revenue_count == 1:
                results["Cross-sell/Upsell"]["medium"].append((category, kpi))
            else:
                results["Cross-sell/Upsell"]["low"].append((category, kpi))
    
    return results

# Generate Excel data
def generate_excel_data():
    results = analyze_kpi_impact()
    
    excel_data = []
    
    # Header row
    excel_data.append([
        "Category",
        "KPI Name",
        "Unit",
        "Product Adoption Impact",
        "Support Impact",
        "Cross-sell/Upsell Impact",
        "Overall Product Dimension Impact",
        "SKU Tracking Required",
        "Business Value",
        "Example: Product A Value",
        "Example: Product B Value"
    ])
    
    # Get all unique KPIs
    all_unique_kpis = []
    for category, kpis in all_kpis.items():
        for kpi in kpis:
            if not any(k[1] == kpi for k in all_unique_kpis):
                all_unique_kpis.append((category, kpi))
    
    # Sort by category
    category_order = ["Product Usage", "Support", "Customer Sentiment", "Business Outcomes", "Relationship Strength"]
    all_unique_kpis.sort(key=lambda x: (category_order.index(x[0]) if x[0] in category_order else 999, x[1]))
    
    for category, kpi in all_unique_kpis:
        # Get KPI details
        kpi_config = KPI_REFERENCE_RANGES.get(kpi, {})
        unit = kpi_config.get("unit", "N/A")
        
        # Determine impact levels
        adoption_impact = "Low"
        support_impact = "Low"
        revenue_impact = "Low"
        
        kpi_lower = kpi.lower()
        
        # Product Adoption
        if any(word in kpi_lower for word in ["activation", "feature adoption", "onboarding", "training", "knowledge", "learning"]):
            adoption_impact = "High"
        elif any(word in kpi_lower for word in ["usage", "utilization", "productivity", "efficiency"]):
            adoption_impact = "Medium"
        
        # Support
        if "support" in kpi_lower or "ticket" in kpi_lower:
            support_impact = "High"
        elif any(word in kpi_lower for word in ["response", "resolution", "escalation", "case"]):
            support_impact = "Medium"
        
        # Cross-sell/Upsell
        if any(word in kpi_lower for word in ["upsell", "cross-sell", "expansion revenue", "nrr", "grr"]):
            revenue_impact = "High"
        elif any(word in kpi_lower for word in ["revenue", "contract", "renewal", "share of wallet"]):
            revenue_impact = "Medium"
        
        # Overall impact
        impact_scores = {
            "High": 3,
            "Medium": 2,
            "Low": 1
        }
        
        overall = max(adoption_impact, support_impact, revenue_impact, key=lambda x: impact_scores.get(x, 0))
        
        # SKU Tracking Required
        sku_required = "Yes" if overall in ["High", "Medium"] else "Optional"
        
        # Business Value
        business_value = []
        if adoption_impact in ["High", "Medium"]:
            business_value.append("Product Adoption")
        if support_impact in ["High", "Medium"]:
            business_value.append("Support")
        if revenue_impact in ["High", "Medium"]:
            business_value.append("Revenue")
        business_value_str = ", ".join(business_value) if business_value else "Account-level only"
        
        # Example values based on KPI type
        example_a = "N/A"
        example_b = "N/A"
        
        if "activation" in kpi_lower or "adoption" in kpi_lower:
            example_a = "95%"
            example_b = "45%"
        elif "revenue" in kpi_lower or "arr" in kpi_lower:
            example_a = "$500K"
            example_b = "$120K"
        elif "ticket" in kpi_lower or "support" in kpi_lower:
            example_a = "3 tickets/month"
            example_b = "47 tickets/month"
        elif "nrr" in kpi_lower or "grr" in kpi_lower:
            example_a = "115%"
            example_b = "85%"
        elif "nps" in kpi_lower or "csat" in kpi_lower or "satisfaction" in kpi_lower:
            example_a = "75"
            example_b = "35"
        elif "time" in kpi_lower and "resolution" in kpi_lower:
            example_a = "2.1 hours"
            example_b = "12.5 hours"
        elif "retention" in kpi_lower:
            example_a = "98%"
            example_b = "72%"
        elif "churn" in kpi_lower:
            example_a = "2%"
            example_b = "18%"
        
        excel_data.append([
            category,
            kpi,
            unit,
            adoption_impact,
            support_impact,
            revenue_impact,
            overall,
            sku_required,
            business_value_str,
            example_a,
            example_b
        ])
    
    return excel_data

# Write to JSON for Excel generation
def write_json():
    excel_data = generate_excel_data()
    
    # Convert to dictionary format
    result_json = {
        "headers": excel_data[0],
        "rows": excel_data[1:]
    }
    
    with open("product_dimension_kpi_analysis.json", "w") as f:
        json.dump(result_json, f, indent=2)
    
    print(f"✅ Generated JSON with {len(excel_data)-1} KPIs")
    return excel_data

if __name__ == "__main__":
    excel_data = write_json()
    
    # Summary statistics
    print("\n📊 SUMMARY STATISTICS")
    print("=" * 60)
    
    total_kpis = len(excel_data) - 1
    high_impact = sum(1 for row in excel_data[1:] if row[6] == "High")
    medium_impact = sum(1 for row in excel_data[1:] if row[6] == "Medium")
    sku_required = sum(1 for row in excel_data[1:] if row[7] == "Yes")
    
    print(f"Total KPIs Analyzed: {total_kpis}")
    print(f"High Impact (SKU Required): {high_impact}")
    print(f"Medium Impact (SKU Recommended): {medium_impact}")
    print(f"Low Impact (Optional): {total_kpis - high_impact - medium_impact}")
    print(f"\nSKU Tracking Required: {sku_required} KPIs")
    
    # Category breakdown
    print("\n📈 BY CATEGORY:")
    for category in ["Product Usage", "Support", "Customer Sentiment", "Business Outcomes", "Relationship Strength"]:
        category_kpis = [row for row in excel_data[1:] if row[0] == category]
        high_count = sum(1 for row in category_kpis if row[6] == "High")
        print(f"  {category}: {len(category_kpis)} KPIs ({high_count} high impact)")

