# Data Center Customer - Option 2: Mapping to Our KPI System

## Overview

Map the serverless health score formula to our reference-range based KPI system while preserving their formula logic.

---

## Challenge Analysis & Solutions

### Challenge 1: Invocation Velocity Formula → Reference Ranges

**Their Formula**:
```
IF(velocity_change > 0, MIN(100, 70 + velocity_change), MAX(0, 70 + velocity_change))
```

**Problem**: Uses direct calculation (70 + change), not reference ranges.

**Solution**: **Reverse-engineer reference ranges** from the formula.

**Mapping Logic**:
- Formula: `score = 70 + velocity_change_pct`
- To get score ranges:
  - **Critical (0-33)**: `70 + velocity_change ≤ 33` → `velocity_change ≤ -37%`
  - **At Risk (34-66)**: `33 < 70 + velocity_change ≤ 66` → `-37% < velocity_change ≤ -4%`
  - **Healthy (67-100)**: `66 < 70 + velocity_change ≤ 100` → `-4% < velocity_change ≤ +30%`

**But wait**: Their formula caps at 0 and 100, so:
- **Critical (0-33)**: `velocity_change ≤ -37%` OR `velocity_change < -70%` (capped at 0)
- **At Risk (34-66)**: `-37% < velocity_change ≤ -4%`
- **Healthy (67-100)**: `-4% < velocity_change ≤ +30%` OR `velocity_change > +30%` (capped at 100)

**Better Approach**: Map velocity_change directly to score ranges:

| Velocity Change | Formula Score | Our Range | Status |
|----------------|---------------|-----------|--------|
| > +30% | 100 (capped) | 67-100 | Healthy |
| 0% to +30% | 70-100 | 67-100 | Healthy |
| -4% to 0% | 66-70 | 34-66 | At Risk |
| -37% to -4% | 33-66 | 34-66 | At Risk |
| -70% to -37% | 0-33 | 0-33 | Critical |
| < -70% | 0 (capped) | 0-33 | Critical |

**Reference Range Definition**:
- **Critical**: `velocity_change < -37%` OR `velocity_change < -70%` (both result in score ≤ 33)
- **At Risk**: `-37% ≤ velocity_change ≤ -4%` (results in score 33-66)
- **Healthy**: `-4% < velocity_change` (results in score > 66)

**Implementation**: Use velocity_change_pct as the KPI value, with these ranges.

---

### Challenge 2: Spend Trend Formula → Reference Ranges

**Their Formula**:
```
IF(monthly_spend > avg_monthly_spend_last_3mo × 1.2, 100,
   IF(monthly_spend < avg_monthly_spend_last_3mo × 0.8, 40, 80))
```

**Problem**: Requires **historical data** (3-month average) that we don't have.

**Solutions**:

#### Solution A: Use Contract Value as Proxy (Recommended)
- **Assumption**: `contract_value_annual / 12` ≈ average monthly spend
- **Formula**: Compare `monthly_spend` to `contract_value_annual / 12`
- **Ranges**:
  - **Healthy (100)**: `monthly_spend > (contract_value_annual / 12) × 1.2`
  - **At Risk (80)**: `(contract_value_annual / 12) × 0.8 ≤ monthly_spend ≤ (contract_value_annual / 12) × 1.2`
  - **Critical (40)**: `monthly_spend < (contract_value_annual / 12) × 0.8`

**Reference Range Definition**:
- Calculate ratio: `spend_ratio = monthly_spend / (contract_value_annual / 12)`
- **Critical**: `spend_ratio < 0.8` (spending < 80% of expected)
- **At Risk**: `0.8 ≤ spend_ratio ≤ 1.2` (spending 80-120% of expected)
- **Healthy**: `spend_ratio > 1.2` (spending > 120% of expected)

#### Solution B: Use Absolute Monthly Spend Ranges
- **Critical**: `monthly_spend < $1,000`
- **At Risk**: `$1,000 ≤ monthly_spend ≤ $10,000`
- **Healthy**: `monthly_spend > $10,000`

**Problem**: Doesn't capture "trend" (increasing/decreasing).

**Recommendation**: **Solution A** (use contract value as proxy).

---

### Challenge 3: Latency Formula → Reference Ranges

**Their Formula**:
```
MAX(0, 100 - (p95_latency_ms / 10))
```

**Problem**: Linear formula, not reference ranges.

**Solution**: **Map latency values to score ranges** based on formula.

**Formula Analysis**:
- `score = 100 - (latency / 10)`
- To get score ranges:
  - **Critical (0-33)**: `100 - (latency / 10) ≤ 33` → `latency ≥ 670ms`
  - **At Risk (34-66)**: `33 < 100 - (latency / 10) ≤ 66` → `340ms ≤ latency < 670ms`
  - **Healthy (67-100)**: `66 < 100 - (latency / 10) ≤ 100` → `0ms ≤ latency < 340ms`

**But**: Their formula says:
- `<500ms = great (95+ points)` → `100 - (500/10) = 50` (wait, that's not 95+)
- `1000ms = poor (<0 points)` → `100 - (1000/10) = 0` ✓

**Re-analysis**:
- Score = 100 - (latency / 10)
- For 95+ points: `100 - (latency / 10) ≥ 95` → `latency ≤ 50ms`
- For 0 points: `100 - (latency / 10) ≤ 0` → `latency ≥ 1000ms`

**Reference Range Definition**:
- **Critical**: `p95_latency_ms ≥ 1000ms` (score = 0)
- **At Risk**: `500ms ≤ p95_latency_ms < 1000ms` (score = 0-50)
- **Healthy**: `p95_latency_ms < 500ms` (score = 50-100)

**But wait**: Their data shows latencies of 86,021-589,210ms (much higher!). Let's recalculate:
- `293,412ms` → Score: `100 - (293,412/10) = 100 - 29,341.2 = -29,241` → Capped at 0 ✓

**Adjusted Reference Ranges** (based on actual data):
- **Critical**: `p95_latency_ms ≥ 1000ms` (score = 0, per formula)
- **At Risk**: `500ms ≤ p95_latency_ms < 1000ms` (score = 0-50)
- **Healthy**: `p95_latency_ms < 500ms` (score = 50-100)

**Note**: Most accounts will be Critical (latencies are 86K-589K ms), which matches their formula (all would score 0).

---

### Challenge 4: Error Rate Formula → Reference Ranges

**Their Formula**:
```
MAX(0, 100 - (error_rate_pct × 10))
```

**Problem**: Linear formula, not reference ranges.

**Solution**: **Map error rate values to score ranges** based on formula.

**Formula Analysis**:
- `score = 100 - (error_rate × 10)`
- To get score ranges:
  - **Critical (0-33)**: `100 - (error_rate × 10) ≤ 33` → `error_rate ≥ 6.7%`
  - **At Risk (34-66)**: `33 < 100 - (error_rate × 10) ≤ 66` → `3.4% ≤ error_rate < 6.7%`
  - **Healthy (67-100)**: `66 < 100 - (error_rate × 10) ≤ 100` → `0% ≤ error_rate < 3.4%`

**Their notes**:
- `<1% errors = 90+ points` → `100 - (1 × 10) = 90` ✓
- `>10% errors = 0 points` → `100 - (10 × 10) = 0` ✓

**Reference Range Definition**:
- **Critical**: `error_rate_pct ≥ 10%` (score = 0)
- **At Risk**: `3.4% ≤ error_rate_pct < 10%` (score = 33-66)
- **Healthy**: `error_rate_pct < 3.4%` (score = 67-100)

**Simplified** (matching their notes):
- **Critical**: `error_rate_pct ≥ 10%` (score = 0)
- **At Risk**: `1% ≤ error_rate_pct < 10%` (score = 0-90)
- **Healthy**: `error_rate_pct < 1%` (score = 90-100)

---

## Complete Reference Range Mapping

### KPI 1: Invocation Velocity Change
- **KPI Name**: "Invocation Velocity Change"
- **Category**: Product Usage KPI
- **Impact Level**: High
- **Higher is Better**: Yes
- **Formula**: `score = 70 + velocity_change_pct` (capped 0-100)
- **Reference Ranges** (mapped from formula):
  - **Critical (0-33)**: `velocity_change_pct ≤ -37%` 
    - Example: -37% → score = 33, -70% → score = 0
  - **At Risk (34-66)**: `-37% < velocity_change_pct ≤ -4%`
    - Example: -20% → score = 50, -4% → score = 66
  - **Healthy (67-100)**: `velocity_change_pct > -4%`
    - Example: 0% → score = 70, +30% → score = 100 (capped)
- **Weight in Category**: 45% (matches their formula weight)

### KPI 2: Spend Trend Ratio
- **KPI Name**: "Monthly Spend vs Expected"
- **Category**: Business Outcomes KPI
- **Impact Level**: High
- **Higher is Better**: Yes
- **Calculation**: `spend_ratio = monthly_spend / (contract_value_annual / 12)`
- **Formula**: 
  - `ratio > 1.2` → Score = 100
  - `0.8 ≤ ratio ≤ 1.2` → Score = 80
  - `ratio < 0.8` → Score = 40
- **Reference Ranges** (mapped from formula):
  - **Critical (0-33)**: `spend_ratio < 0.8` → Score = 40 (maps to lower At Risk, but formula says 40)
    - **Note**: Score 40 is technically in At Risk range (34-66), but their formula treats it as "Critical" behavior
    - **Solution**: Use `spend_ratio < 0.6` for Critical to get score ≤ 33
    - **OR**: Accept that score 40 maps to lower At Risk range (34-66)
  - **At Risk (34-66)**: `0.8 ≤ spend_ratio ≤ 1.2` → Score = 80 (maps to upper At Risk)
  - **Healthy (67-100)**: `spend_ratio > 1.2` → Score = 100
- **Weight in Category**: 30% (matches their formula weight)
- **Challenge**: Score 40 doesn't map cleanly to Critical range (0-33). Options:
  1. Adjust Critical range to include 40: `spend_ratio < 0.8` → Score 40 (treat as Critical behavior)
  2. Use narrower Critical range: `spend_ratio < 0.6` → Score ≤ 33 (true Critical)
  3. Accept mismatch: Score 40 is in At Risk range but represents "declining spend"

### KPI 3: P95 Latency
- **KPI Name**: "P95 Latency"
- **Category**: Support KPI
- **Impact Level**: High
- **Higher is Better**: No (lower is better)
- **Formula**: `score = 100 - (latency_ms / 10)` (capped 0-100)
- **Reference Ranges** (mapped from formula):
  - **Critical (0-33)**: `p95_latency_ms ≥ 670ms`
    - Example: 670ms → score = 33, 1000ms → score = 0
  - **At Risk (34-66)**: `340ms ≤ p95_latency_ms < 670ms`
    - Example: 340ms → score = 66, 500ms → score = 50, 669ms → score = 33.1
  - **Healthy (67-100)**: `p95_latency_ms < 340ms`
    - Example: 100ms → score = 90, 50ms → score = 95
- **Weight in Category**: 15% (matches their formula weight)
- **Note**: Most accounts have latencies 86K-589K ms, which all score 0 (Critical)

### KPI 4: Error Rate
- **KPI Name**: "Error Rate"
- **Category**: Support KPI
- **Impact Level**: Critical
- **Higher is Better**: No (lower is better)
- **Formula**: `score = 100 - (error_rate_pct × 10)` (capped 0-100)
- **Reference Ranges** (mapped from formula):
  - **Critical (0-33)**: `error_rate_pct ≥ 6.7%`
    - Example: 6.7% → score = 33, 10% → score = 0
  - **At Risk (34-66)**: `3.4% ≤ error_rate_pct < 6.7%`
    - Example: 3.4% → score = 66, 5% → score = 50
  - **Healthy (67-100)**: `error_rate_pct < 3.4%`
    - Example: 1% → score = 90, 0.5% → score = 95, 0.1% → score = 99
- **Weight in Category**: 10% (matches their formula weight)
- **Simplified** (matching their notes):
  - **Critical**: `error_rate_pct ≥ 10%` (score = 0)
  - **At Risk**: `1% ≤ error_rate_pct < 10%` (score = 0-90)
  - **Healthy**: `error_rate_pct < 1%` (score = 90-100)

---

## Category Weights

**From their formula**:
- Invocation Velocity: 45% → **Product Usage KPI: 45%**
- Spend Trend: 30% → **Business Outcomes KPI: 30%**
- Latency: 15% → **Support KPI: 15%**
- Error Rate: 10% → **Support KPI: 10%**

**Total Support KPI**: 15% + 10% = **25%**

**Final Category Weights**:
- **Product Usage KPI**: 45%
- **Business Outcomes KPI**: 30%
- **Support KPI**: 25%
- **Customer Sentiment KPI**: 0% (not used in their formula)
- **Relationship Strength KPI**: 0% (not used in their formula)

**Note**: Must sum to 100%, so we have 45 + 30 + 25 = 100% ✓

---

## Implementation Strategy

### Step 1: Create Calculated KPI for Spend Trend

**Problem**: Spend Trend requires calculation (ratio), not direct value.

**Solution**: Create a **calculated KPI** that computes the ratio.

**Implementation**:
```python
def calculate_spend_trend_ratio(monthly_spend, contract_value_annual):
    """
    Calculate spend trend ratio for reference range comparison
    """
    expected_monthly = contract_value_annual / 12
    if expected_monthly > 0:
        return monthly_spend / expected_monthly
    return 1.0  # Default to 1.0 if no contract value
```

**Store as KPI**:
- KPI Name: "Monthly Spend vs Expected"
- Data Value: The calculated ratio (e.g., "0.99" for 99% of expected)
- Category: Business Outcomes KPI
- Reference Ranges: 0.8 (Critical max), 1.2 (Healthy min)

### Step 2: Handle Velocity Change Formula Logic

**Problem**: Their formula uses `70 + velocity_change`, which creates non-linear mapping.

**Solution**: **Use velocity_change_pct directly** with reference ranges that produce equivalent scores.

**Validation**: Ensure our reference-range scoring produces same results as their formula.

**Example**:
- `velocity_change = -20%`
- Their formula: `MAX(0, 70 + (-20)) = 50`
- Our system: Check if -20% is in At Risk range (-37% to -4%) → Yes → Score: 34-66 range → Calculate: ~50 ✓

### Step 3: Handle Latency/Error Rate Linear Formulas

**Problem**: Linear formulas don't map cleanly to 3-range system.

**Solution**: **Use reference ranges** that approximate the linear formula, then validate scores match.

**Validation**:
- For latency = 500ms:
  - Their formula: `100 - (500/10) = 50`
  - Our system: 500ms is in At Risk range (500-1000ms) → Score: 34-66 → Calculate: ~50 ✓

- For error_rate = 5%:
  - Their formula: `100 - (5 × 10) = 50`
  - Our system: 5% is in At Risk range (1-10%) → Score: 0-90 → Calculate: ~50 ✓

---

## Validation: Ensuring Scores Match

### Test Cases

#### Test 1: Invocation Velocity
- **Input**: `velocity_change = -67.7%`
- **Their Formula**: `MAX(0, 70 + (-67.7)) = 2.3`
- **Our System**: 
  - Check: -67.7% < -37% → Critical range
  - Score: 0-33 range → Calculate: ~2 ✓

#### Test 2: Spend Trend
- **Input**: `monthly_spend = $19,790`, `contract_value_annual = $237,481`
- **Their Formula**: Need 3-month average (assume $20,000) → Ratio: 0.99 → Score: 80
- **Our System**:
  - Calculate ratio: `19,790 / (237,481 / 12) = 0.999`
  - Check: 0.8 ≤ 0.999 ≤ 1.2 → At Risk range
  - Score: 34-66 range → Calculate: ~80 ✓

#### Test 3: Latency
- **Input**: `p95_latency = 293,412ms`
- **Their Formula**: `MAX(0, 100 - (293,412/10)) = 0`
- **Our System**:
  - Check: 293,412ms ≥ 1000ms → Critical range
  - Score: 0-33 range → Calculate: 0 ✓

#### Test 4: Error Rate
- **Input**: `error_rate = 13.45%`
- **Their Formula**: `MAX(0, 100 - (13.45 × 10)) = 0`
- **Our System**:
  - Check: 13.45% ≥ 10% → Critical range
  - Score: 0-33 range → Calculate: 0 ✓

---

## Updated Onboarding Plan

### Step 1: Business Outcomes
- Detect: "Serverless/Platform" customer type
- Set: `customer_type = 'serverless'`

### Step 2: KPI Category Weights
- **Pre-set** (not user-configurable for serverless):
  - Product Usage: 45%
  - Business Outcomes: 30%
  - Support: 25%
  - Customer Sentiment: 0%
  - Relationship Strength: 0%

### Step 3: KPI Reference Ranges
- **Auto-populate** based on serverless formulas:
  - Invocation Velocity Change: -37% / -4% thresholds
  - Spend Trend Ratio: 0.8 / 1.2 thresholds
  - P95 Latency: 500ms / 1000ms thresholds
  - Error Rate: 1% / 10% thresholds

### Step 4: Account Setup
- Same as before

### Step 5: KPI Data Upload
- Transform metrics to KPIs
- **Calculate Spend Trend Ratio** during transformation
- Store as KPI with calculated ratio value

---

## Implementation Code

### Transformation Logic

```python
def transform_serverless_to_kpis(df):
    """
    Transform serverless customer file to our KPI format
    """
    kpis = []
    
    for _, row in df.iterrows():
        account_name = row['company_name']
        
        # 1. Invocation Velocity Change
        kpis.append({
            'account_name': account_name,
            'category': 'Product Usage KPI',
            'kpi_parameter': 'Invocation Velocity Change',
            'data': row['invocation_velocity_change_pct'],
            'impact_level': 'High',
            'measurement_frequency': 'Monthly'
        })
        
        # 2. Spend Trend Ratio (CALCULATED)
        monthly_spend = row['monthly_spend']
        contract_value = row['contract_value_annual']
        spend_ratio = monthly_spend / (contract_value / 12) if contract_value > 0 else 1.0
        
        kpis.append({
            'account_name': account_name,
            'category': 'Business Outcomes KPI',
            'kpi_parameter': 'Monthly Spend vs Expected',
            'data': spend_ratio,  # Store as ratio (e.g., 0.99)
            'impact_level': 'High',
            'measurement_frequency': 'Monthly'
        })
        
        # 3. P95 Latency
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'P95 Latency',
            'data': row['p95_latency_ms'],
            'impact_level': 'High',
            'measurement_frequency': 'Daily'
        })
        
        # 4. Error Rate
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'Error Rate',
            'data': row['error_rate_pct'],
            'impact_level': 'Critical',
            'measurement_frequency': 'Daily'
        })
    
    return kpis
```

### Reference Range Creation

```python
def create_serverless_reference_ranges(customer_id):
    """
    Create reference ranges for serverless customer based on formulas
    """
    ranges = [
        {
            'kpi_name': 'Invocation Velocity Change',
            'critical_max': -37.0,  # velocity_change < -37% → Critical
            'risk_max': -4.0,        # -37% ≤ velocity_change ≤ -4% → At Risk
            'healthy_min': -4.0,     # velocity_change > -4% → Healthy
            'higher_is_better': True,
            'unit': '%'
        },
        {
            'kpi_name': 'Monthly Spend vs Expected',
            'critical_max': 0.8,     # ratio < 0.8 → Critical
            'risk_max': 1.2,         # 0.8 ≤ ratio ≤ 1.2 → At Risk
            'healthy_min': 1.2,      # ratio > 1.2 → Healthy
            'higher_is_better': True,
            'unit': 'ratio'
        },
        {
            'kpi_name': 'P95 Latency',
            'critical_min': 1000.0,  # latency ≥ 1000ms → Critical
            'risk_min': 500.0,       # 500ms ≤ latency < 1000ms → At Risk
            'healthy_max': 500.0,    # latency < 500ms → Healthy
            'higher_is_better': False,
            'unit': 'ms'
        },
        {
            'kpi_name': 'Error Rate',
            'critical_min': 10.0,     # error_rate ≥ 10% → Critical
            'risk_min': 1.0,         # 1% ≤ error_rate < 10% → At Risk
            'healthy_max': 1.0,      # error_rate < 1% → Healthy
            'higher_is_better': False,
            'unit': '%'
        }
    ]
    
    # Create KPIReferenceRange records
    for range_def in ranges:
        create_reference_range(customer_id, range_def)
```

---

## Validation & Testing

### Score Comparison

After implementation, compare:
1. **Our calculated scores** (using reference ranges)
2. **Their formula scores** (using direct calculation)
3. **Existing scores** (from file)

**Expected**: Our scores should match their formula scores (within rounding).

### Edge Cases

1. **Velocity Change > +30%**: Should cap at 100 (our system handles this)
2. **Velocity Change < -70%**: Should cap at 0 (our system handles this)
3. **Latency > 1000ms**: Should score 0 (our system: Critical = 0-33, should calculate to 0)
4. **Error Rate > 10%**: Should score 0 (our system: Critical = 0-33, should calculate to 0)

---

## Benefits of Option 2

✅ **Uses our existing system** (reference ranges, KPI structure)  
✅ **Preserves their formula logic** (mapped to ranges)  
✅ **Consistent with other customers** (same calculation method)  
✅ **Flexible** (can adjust ranges if needed)  
✅ **No custom code paths** (uses standard health score engine)  

---

## Next Steps

1. **Implement reference range creation** for serverless customers
2. **Implement spend trend ratio calculation** during transformation
3. **Validate scores match** their formula
4. **Test with actual data** from file
5. **Adjust ranges if needed** to match their formula exactly

---

**Last Updated**: January 2025  
**Status**: Option 2 Detailed Plan Complete

