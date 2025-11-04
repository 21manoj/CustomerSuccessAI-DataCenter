# KPI Reference Ranges - Fixed Issue

## Problem Identified

The user reported that for KPIs where "lower is better" (like Support Cost per Ticket), the default values were showing higher values as healthy, which is incorrect.

## Root Cause

The issue was in the `reset_kpi_reference_ranges` function in `/backend/kpi_reference_ranges_api.py`. It was incorrectly mapping ranges for KPIs where `higher_is_better: False`.

### Original Code (INCORRECT):
```python
# This mapped ranges directly without considering higher_is_better
critical_min = ranges['low']['min']  # Wrong: low color = red, not critical
critical_max = ranges['low']['max']
risk_min = ranges['medium']['min']
risk_max = ranges['medium']['max']
healthy_min = ranges['high']['min']  # Wrong: high color = green, but stored as healthy
healthy_max = ranges['high']['max']
```

This caused:
- For "Support Cost per Ticket": 0-25 (low cost, green) was stored as CRITICAL
- And 76-999999 (high cost, red) was stored as HEALTHY

## Solution Implemented

Fixed the mapping logic to handle both cases correctly:

```python
if higher_is_better:
    # Higher is better: low range = red (critical), high range = green (healthy)
    critical_min = ranges['low']['min']
    critical_max = ranges['low']['max']
    risk_min = ranges['medium']['min']
    risk_max = ranges['medium']['max']
    healthy_min = ranges['high']['min']
    healthy_max = ranges['high']['max']
else:
    # Lower is better: low range = green (healthy), high range = red (critical)
    # Need to REVERSE the mapping
    healthy_min = ranges['low']['min']  # Low values are healthy (green)
    healthy_max = ranges['low']['max']
    risk_min = ranges['medium']['min']
    risk_max = ranges['medium']['max']
    critical_min = ranges['high']['min']  # High values are critical (red)
    critical_max = ranges['high']['max']
```

## Verification

After the fix, "Support Cost per Ticket" now shows correct values:

```
✅ critical_range: 76-999999 $ (BAD - high cost = critical)
✅ risk_range: 26-75 $ (MEDIUM)
✅ healthy_range: 0-25 $ (GOOD - low cost = healthy)
```

## Additional Fixes

1. **Added missing columns to database model:**
   - `critical_range` (VARCHAR)
   - `risk_range` (VARCHAR)
   - `healthy_range` (VARCHAR)
   - `description` (TEXT)

2. **Database migration:** Added columns to existing database

## Impact

This fix applies to ALL KPIs where `higher_is_better: False`, ensuring correct mapping for:
- Support Cost per Ticket
- Time to First Value (TTFV)
- First Response Time
- Mean Time to Resolution (MTTR)
- Ticket Volume
- Ticket Backlog
- Escalation Rate
- Process Cycle Time
- Customer Complaints
- Error Rates
- Churn Rate
- Churn by Segment/Persona/Product
- Days Sales Outstanding (DSO)
- Cash Conversion Cycle (CCC)
- Cost per Unit
- Customer Acquisition Cost
- Support Requests During Onboarding
- Churn Risk Flags Triggered

All 18 KPIs with `higher_is_better: False` now have correct ranges stored in the database.

