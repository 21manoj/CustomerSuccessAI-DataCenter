#!/usr/bin/env python3
"""
Seed customer-specific KPIReferenceRange overrides for a tenant from a hardcoded 59-KPI catalog.
Use when you need an exact per-tenant catalog and ranges that differ from system defaults.

Safety:
- Only affects the specified customer's overrides (customer_id = tenant id)
- Does NOT change system defaults (customer_id = NULL)
"""
from app_v3_minimal import app
from extensions import db
from models import KPIReferenceRange, Customer
import argparse

# Hardcoded 59 KPI ranges (from user's Test tenant spec)
# Each entry: kpi_name, unit, critical_min, critical_max, risk_min, risk_max, healthy_min, healthy_max, higher_is_better
CATALOG = [
    ("Account Engagement Score", "score", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Accounts Receivable Turnover", "ratio", 0.0, 100.0, 101.0, 300.0, 301.0, 9999.0, True),
    ("Audit Results", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Average Contract Value", "$", 0.0, 10000.0, 10001.0, 50000.0, 50001.0, 999999.0, True),
    ("Benchmarking Results", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Business Review Frequency", "score", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Case Deflection Rate", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Cash Conversion Cycle (CCC)", "days", 0.0, 30.0, 31.0, 60.0, 61.0, 999.0, False),
    ("Churn Rate", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 100.0, False),
    ("Churn Rate (inverse)", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Churn Risk Flags Triggered", "count", 0.0, 5.0, 6.0, 15.0, 16.0, 999.0, False),
    ("Churn by Segment/Persona/Product", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 100.0, False),
    ("Collection Effectiveness Index (CEI)", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Competitive Win Rate", "%", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Contract Renewal Rate", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Cost Savings", "$", 0.0, 10000.0, 10001.0, 50000.0, 50001.0, 999999.0, True),
    ("Cost per Unit", "$", 0.0, 25.0, 26.0, 75.0, 76.0, 999999.0, False),
    ("Cross-functional Task Completion", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Customer Acquisition Cost", "$", 0.0, 100.0, 101.0, 500.0, 501.0, 999999.0, False),
    ("Customer Complaints", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 100.0, False),
    ("Customer Effort Score (CES)", "score", 1.0, 3.0, 3.1, 4.0, 4.1, 5.0, True),
    ("Customer Lifetime Value (CLV)", "$", 0.0, 10000.0, 10001.0, 50000.0, 50001.0, 999999.0, True),
    ("Customer Onboarding Satisfaction (CSAT)", "score", 1.0, 3.0, 3.1, 4.0, 4.1, 5.0, True),
    ("Customer ROI", "%", 0.0, 100.0, 101.0, 200.0, 201.0, 9999.0, True),
    ("Customer Retention Rate", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Customer Satisfaction (CSAT)", "score", 1.0, 3.0, 3.1, 4.0, 4.1, 5.0, True),
    ("Customer Support Satisfaction", "score", 1.0, 3.0, 3.1, 4.0, 4.1, 5.0, True),
    ("Customer sentiment Trends", "score", -100.0, 0.0, 1.0, 50.0, 51.0, 100.0, True),
    ("Days Sales Outstanding (DSO)", "days", 0.0, 30.0, 31.0, 60.0, 61.0, 999.0, False),
    ("Employee Productivity (customer usage patterns)", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Error Rates (affecting customer experience)", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 100.0, False),
    ("Escalation Rate", "%", 0.0, 10.0, 11.0, 25.0, 26.0, 100.0, False),
    ("Expansion Revenue", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 999.0, True),
    ("Expansion Revenue Rate", "%", 0.0, 10.0, 11.0, 25.0, 26.0, 999.0, True),
    ("Feature Adoption Rate", "%", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("First Contact Resolution (FCR)", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("First Response Time", "hours", 8.0, 999.0, 2.0, 8.0, 0.0, 2.0, False),
    ("Gross Revenue Retention (GRR)", "%", 0.0, 100.0, 101.0, 115.0, 116.0, 999.0, True),
    ("Invoice Accuracy", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Key Performance Indicators (KPIs)", "%", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Knowledge Base Usage", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Learning Path Completion Rate", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Market Share", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 999.0, True),
    ("Mean Time to Resolution (MTTR)", "hours", 24.0, 999.0, 4.0, 24.0, 0.0, 4.0, False),
    ("Net Promoter Score (NPS)", "score", -100.0, 0.0, 1.0, 50.0, 51.0, 100.0, True),
    ("Net Revenue Retention (NRR)", "%", 0.0, 100.0, 101.0, 115.0, 116.0, 999.0, True),
    ("On-time Delivery Rates", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Onboarding Completion Rate", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Operational Cost Savings", "$", 0.0, 10000.0, 10001.0, 50000.0, 50001.0, 999999.0, True),
    ("Operational Efficiency (platform utilization)", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Payment Terms Compliance", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Process Cycle Time", "days", 0.0, 2.0, 2.1, 5.0, 5.1, 999.0, False),
    ("Process Improvement Velocity", "score", 0.0, 70.0, 71.0, 90.0, 91.0, 100.0, True),
    ("Product Activation Rate", "%", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Regulatory Compliance", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Relationship Health Score", "%", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Renewal Rate", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Return on Investment (ROI)", "%", 0.0, 100.0, 101.0, 200.0, 201.0, 9999.0, True),
    ("Revenue Growth", "%", 0.0, 5.0, 6.0, 15.0, 16.0, 999.0, True),
    ("Service Level Agreements (SLAs) compliance", "%", 0.0, 80.0, 81.0, 95.0, 96.0, 100.0, True),
    ("Share of Wallet", "%", 0.0, 50.0, 51.0, 80.0, 81.0, 100.0, True),
    ("Support Cost per Ticket", "$", 0.0, 25.0, 26.0, 75.0, 76.0, 999999.0, False),
    ("Support Requests During Onboarding", "count", 0.0, 5.0, 6.0, 15.0, 16.0, 999.0, False),
    ("Ticket Backlog", "%", 0.0, 10.0, 11.0, 25.0, 26.0, 100.0, False),
    ("Ticket Volume", "count", 0.0, 100.0, 101.0, 500.0, 501.0, 9999.0, False),
    ("Time to First Value (TTFV)", "days", 31.0, 999.0, 8.0, 30.0, 0.0, 7.0, False),
    ("Training Participation Rate", "%", 0.0, 60.0, 61.0, 85.0, 86.0, 100.0, True),
    ("Upsell and Cross-sell Revenue", "%", 0.0, 10.0, 11.0, 25.0, 26.0, 999.0, True),
]


def seed_customer(customer_name: str):
    cust = Customer.query.filter(Customer.customer_name == customer_name).first()
    if not cust:
        print(f"❌ Customer '{customer_name}' not found")
        return
    customer_id = cust.customer_id
    # Remove existing overrides
    deleted = KPIReferenceRange.query.filter_by(customer_id=customer_id).delete()
    print(f"Cleared {deleted} existing overrides for customer_id={customer_id}")
    # Upsert all entries
    for (name, unit, cmin, cmax, rmin, rmax, hmin, hmax, hib) in CATALOG:
        rr = KPIReferenceRange(
            customer_id=customer_id,
            kpi_name=name,
            unit=unit,
            higher_is_better=bool(hib),
            critical_min=float(cmin),
            critical_max=float(cmax),
            risk_min=float(rmin),
            risk_max=float(rmax),
            healthy_min=float(hmin),
            healthy_max=float(hmax),
            critical_range=f"{cmin}-{cmax} {unit}",
            risk_range=f"{rmin}-{rmax} {unit}",
            healthy_range=f"{hmin}-{hmax} {unit}",
            description=f"Tenant override for {name}"
        )
        db.session.add(rr)
    db.session.commit()
    total = KPIReferenceRange.query.filter_by(customer_id=customer_id).count()
    print(f"✅ Seeded {total} KPI overrides for '{customer_name}' (id={customer_id})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", required=True, help="Exact customer name to seed (tenant)")
    args = parser.parse_args()
    with app.app_context():
        seed_customer(args.customer)


if __name__ == "__main__":
    main()










