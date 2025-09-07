#!/usr/bin/env python3
"""
Health Score Configuration
Defines reference ranges and scoring logic for all KPIs
"""

# Reference ranges for all KPIs (like medical lab reports)
KPI_REFERENCE_RANGES = {
    # Product Usage KPIs
    "Product Activation Rate": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Customer Retention Rate": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Onboarding Completion Rate": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Time to First Value (TTFV)": {
        "ranges": {"low": {"min": 31, "max": 999, "color": "red"}, "medium": {"min": 8, "max": 30, "color": "yellow"}, "high": {"min": 0, "max": 7, "color": "green"}},
        "unit": "days",
        "higher_is_better": False
    },
    "Customer Onboarding Satisfaction (CSAT)": {
        "ranges": {"low": {"min": 1.0, "max": 3.0, "color": "red"}, "medium": {"min": 3.1, "max": 4.0, "color": "yellow"}, "high": {"min": 4.1, "max": 5.0, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Training Participation Rate": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Feature Adoption Rate": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Knowledge Base Usage": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Learning Path Completion Rate": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Support Requests During Onboarding": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 999, "color": "red"}},
        "unit": "count",
        "higher_is_better": False
    },
    "Churn Rate (inverse)": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Share of Wallet": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Employee Productivity (customer usage patterns)": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Operational Efficiency (platform utilization)": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },

    # Support KPIs
    "First Response Time": {
        "ranges": {"low": {"min": 8, "max": 999, "color": "red"}, "medium": {"min": 2, "max": 8, "color": "yellow"}, "high": {"min": 0, "max": 2, "color": "green"}},
        "unit": "hours",
        "higher_is_better": False
    },
    "Mean Time to Resolution (MTTR)": {
        "ranges": {"low": {"min": 24, "max": 999, "color": "red"}, "medium": {"min": 4, "max": 24, "color": "yellow"}, "high": {"min": 0, "max": 4, "color": "green"}},
        "unit": "hours",
        "higher_is_better": False
    },
    "Customer Support Satisfaction": {
        "ranges": {"low": {"min": 1.0, "max": 3.0, "color": "red"}, "medium": {"min": 3.1, "max": 4.0, "color": "yellow"}, "high": {"min": 4.1, "max": 5.0, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Ticket Volume": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "green"}, "medium": {"min": 101, "max": 500, "color": "yellow"}, "high": {"min": 501, "max": 9999, "color": "red"}},
        "unit": "count",
        "higher_is_better": False
    },
    "Ticket Backlog": {
        "ranges": {"low": {"min": 0, "max": 10, "color": "green"}, "medium": {"min": 11, "max": 25, "color": "yellow"}, "high": {"min": 26, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Escalation Rate": {
        "ranges": {"low": {"min": 0, "max": 10, "color": "green"}, "medium": {"min": 11, "max": 25, "color": "yellow"}, "high": {"min": 26, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Support Cost per Ticket": {
        "ranges": {"low": {"min": 0, "max": 25, "color": "green"}, "medium": {"min": 26, "max": 75, "color": "yellow"}, "high": {"min": 76, "max": 999999, "color": "red"}},
        "unit": "$",
        "higher_is_better": False
    },
    "Case Deflection Rate": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Customer Effort Score (CES)": {
        "ranges": {"low": {"min": 1.0, "max": 3.0, "color": "red"}, "medium": {"min": 3.1, "max": 4.0, "color": "yellow"}, "high": {"min": 4.1, "max": 5.0, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Process Cycle Time": {
        "ranges": {"low": {"min": 0, "max": 2, "color": "green"}, "medium": {"min": 2.1, "max": 5, "color": "yellow"}, "high": {"min": 5.1, "max": 999, "color": "red"}},
        "unit": "days",
        "higher_is_better": False
    },
    "First Contact Resolution (FCR)": {
        "ranges": {"low": {"min": 0, "max": 60, "color": "red"}, "medium": {"min": 61, "max": 85, "color": "yellow"}, "high": {"min": 86, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },

    # Customer Sentiment KPIs
    "Net Promoter Score (NPS)": {
        "ranges": {"low": {"min": -100, "max": 0, "color": "red"}, "medium": {"min": 1, "max": 50, "color": "yellow"}, "high": {"min": 51, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Customer Complaints": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Error Rates (affecting customer experience)": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Customer sentiment Trends": {
        "ranges": {"low": {"min": -100, "max": 0, "color": "red"}, "medium": {"min": 1, "max": 50, "color": "yellow"}, "high": {"min": 51, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Customer Satisfaction (CSAT)": {
        "ranges": {"low": {"min": 1.0, "max": 3.0, "color": "red"}, "medium": {"min": 3.1, "max": 4.0, "color": "yellow"}, "high": {"min": 4.1, "max": 5.0, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Relationship Health Score": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },

    # Business Outcomes KPIs
    "Revenue Growth": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "red"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Customer Lifetime Value (CLV)": {
        "ranges": {"low": {"min": 0, "max": 10000, "color": "red"}, "medium": {"min": 10001, "max": 50000, "color": "yellow"}, "high": {"min": 50001, "max": 999999, "color": "green"}},
        "unit": "$",
        "higher_is_better": True
    },
    "Upsell and Cross-sell Revenue": {
        "ranges": {"low": {"min": 0, "max": 10, "color": "red"}, "medium": {"min": 11, "max": 25, "color": "yellow"}, "high": {"min": 26, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Cost Savings": {
        "ranges": {"low": {"min": 0, "max": 10000, "color": "red"}, "medium": {"min": 10001, "max": 50000, "color": "yellow"}, "high": {"min": 50001, "max": 999999, "color": "green"}},
        "unit": "$",
        "higher_is_better": True
    },
    "Days Sales Outstanding (DSO)": {
        "ranges": {"low": {"min": 0, "max": 30, "color": "green"}, "medium": {"min": 31, "max": 60, "color": "yellow"}, "high": {"min": 61, "max": 999, "color": "red"}},
        "unit": "days",
        "higher_is_better": False
    },
    "Accounts Receivable Turnover": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "red"}, "medium": {"min": 101, "max": 300, "color": "yellow"}, "high": {"min": 301, "max": 9999, "color": "green"}},
        "unit": "ratio",
        "higher_is_better": True
    },
    "Cash Conversion Cycle (CCC)": {
        "ranges": {"low": {"min": 0, "max": 30, "color": "green"}, "medium": {"min": 31, "max": 60, "color": "yellow"}, "high": {"min": 61, "max": 999, "color": "red"}},
        "unit": "days",
        "higher_is_better": False
    },
    "Invoice Accuracy": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Payment Terms Compliance": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Collection Effectiveness Index (CEI)": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Net Revenue Retention (NRR)": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "red"}, "medium": {"min": 101, "max": 115, "color": "yellow"}, "high": {"min": 116, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Renewal Rate": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Expansion Revenue Rate": {
        "ranges": {"low": {"min": 0, "max": 10, "color": "red"}, "medium": {"min": 11, "max": 25, "color": "yellow"}, "high": {"min": 26, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Churn by Segment/Persona/Product": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Key Performance Indicators (KPIs)": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Operational Cost Savings": {
        "ranges": {"low": {"min": 0, "max": 10000, "color": "red"}, "medium": {"min": 10001, "max": 50000, "color": "yellow"}, "high": {"min": 50001, "max": 999999, "color": "green"}},
        "unit": "$",
        "higher_is_better": True
    },
    "Cost per Unit": {
        "ranges": {"low": {"min": 0, "max": 25, "color": "green"}, "medium": {"min": 26, "max": 75, "color": "yellow"}, "high": {"min": 76, "max": 999999, "color": "red"}},
        "unit": "$",
        "higher_is_better": False
    },
    "Return on Investment (ROI)": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "red"}, "medium": {"min": 101, "max": 200, "color": "yellow"}, "high": {"min": 201, "max": 9999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Gross Revenue Retention (GRR)": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "red"}, "medium": {"min": 101, "max": 115, "color": "yellow"}, "high": {"min": 116, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Contract Renewal Rate": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Expansion Revenue": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "red"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Customer Acquisition Cost": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "green"}, "medium": {"min": 101, "max": 500, "color": "yellow"}, "high": {"min": 501, "max": 999999, "color": "red"}},
        "unit": "$",
        "higher_is_better": False
    },
    "Churn Rate": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 100, "color": "red"}},
        "unit": "%",
        "higher_is_better": False
    },
    "Average Contract Value": {
        "ranges": {"low": {"min": 0, "max": 10000, "color": "red"}, "medium": {"min": 10001, "max": 50000, "color": "yellow"}, "high": {"min": 50001, "max": 999999, "color": "green"}},
        "unit": "$",
        "higher_is_better": True
    },
    "Customer ROI": {
        "ranges": {"low": {"min": 0, "max": 100, "color": "red"}, "medium": {"min": 101, "max": 200, "color": "yellow"}, "high": {"min": 201, "max": 9999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Market Share": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "red"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 999, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Competitive Win Rate": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },

    # Relationship Strength KPIs
    "Business Review Frequency": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Account Engagement Score": {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    },
    "Churn Risk Flags Triggered": {
        "ranges": {"low": {"min": 0, "max": 5, "color": "green"}, "medium": {"min": 6, "max": 15, "color": "yellow"}, "high": {"min": 16, "max": 999, "color": "red"}},
        "unit": "count",
        "higher_is_better": False
    },
    "Service Level Agreements (SLAs) compliance": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "On-time Delivery Rates": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Benchmarking Results": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Regulatory Compliance": {
        "ranges": {"low": {"min": 0, "max": 80, "color": "red"}, "medium": {"min": 81, "max": 95, "color": "yellow"}, "high": {"min": 96, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Audit Results": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Cross-functional Task Completion": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "%",
        "higher_is_better": True
    },
    "Process Improvement Velocity": {
        "ranges": {"low": {"min": 0, "max": 70, "color": "red"}, "medium": {"min": 71, "max": 90, "color": "yellow"}, "high": {"min": 91, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    }
}

# Category weights from the original Excel file
CATEGORY_WEIGHTS = {
    "Product Usage": 0.20,      # 20%
    "Support": 0.20,            # 20%
    "Customer Sentiment": 0.20, # 20%
    "Business Outcomes": 0.25,  # 25%
    "Relationship Strength": 0.15 # 15%
}

# Impact level weights for scoring
IMPACT_WEIGHTS = {
    "High": 3,
    "Medium": 2,
    "Low": 1
}

def get_kpi_reference_range(kpi_name: str) -> dict:
    """Get reference range for a specific KPI"""
    return KPI_REFERENCE_RANGES.get(kpi_name, {
        "ranges": {"low": {"min": 0, "max": 50, "color": "red"}, "medium": {"min": 51, "max": 80, "color": "yellow"}, "high": {"min": 81, "max": 100, "color": "green"}},
        "unit": "score",
        "higher_is_better": True
    })

def get_category_weight(category: str, customer_id: int = None) -> float:
    """Get weight for a specific category, optionally from customer config"""
    # Normalize category name by removing " KPI" suffix if present
    normalized_category = category.replace(" KPI", "")
    
    if customer_id:
        try:
            from models import CustomerConfig
            from extensions import db
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if config and config.category_weights:
                import json
                customer_weights = json.loads(config.category_weights)
                # Try both original and normalized category names
                return customer_weights.get(category, customer_weights.get(normalized_category, CATEGORY_WEIGHTS.get(normalized_category, 0.20)))
        except Exception as e:
            print(f"Error getting customer category weights: {e}")
    
    # Use normalized category name for lookup
    return CATEGORY_WEIGHTS.get(normalized_category, 0.20)

def get_impact_weight(impact_level: str) -> int:
    """Get weight for impact level"""
    return IMPACT_WEIGHTS.get(impact_level, 1) 