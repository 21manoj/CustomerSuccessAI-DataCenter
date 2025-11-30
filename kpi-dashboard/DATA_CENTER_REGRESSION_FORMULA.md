# Data Center Customer - Regression Health Score Formula

## ✅ **VERIFIED FORMULA**

This regression formula matches the customer's health scores with **97.1% accuracy** (within 2 points).

---

## Formula

```python
health_score = round(
    52.14 
    + (invocation_velocity_change_pct × 0.416)
    - (days_since_last_invocation × 1.030)
    + (error_rate_pct × 0.440)
    + (monthly_spend × 0.000035)
    - (daily_invocations × 0.00001)
    + (p95_latency_ms × 0.000002),
    0  # Round to nearest integer
)
```

---

## Formula Components

| Component | Coefficient | Impact | Notes |
|-----------|------------|--------|-------|
| **Base** | 52.14 | Constant | Starting point for all accounts |
| **Invocation Velocity Change (%)** | +0.416 | High | Positive change improves score |
| **Days Since Last Invocation** | -1.030 | **Very High** | Strong negative impact (up to -29.87 points) |
| **Error Rate (%)** | +0.440 | Moderate | Higher error rate increases score (counterintuitive) |
| **Monthly Spend ($)** | +0.000035 | Low | Small positive impact |
| **Daily Invocations** | -0.00001 | Very Low | Small negative impact |
| **P95 Latency (ms)** | +0.000002 | Very Low | Minimal impact |

---

## Component Contribution Analysis

### Typical Ranges (from 35 accounts)

| Component | Min Contribution | Max Contribution | Average |
|-----------|-----------------|-----------------|---------|
| Base | 52.14 | 52.14 | 52.14 |
| Velocity | -29.24 | +20.76 | +1.23 |
| Days Since | -29.87 | 0.00 | -6.06 |
| Error Rate | +0.06 | +5.92 | +1.11 |
| Monthly Spend | +0.01 | +1.89 | +0.36 |
| Daily Invocations | -1.78 | 0.00 | -0.26 |
| P95 Latency | +0.17 | +1.18 | +0.56 |

### Most Impactful Factors

1. **Days Since Last Invocation** (-1.030 per day)
   - Can reduce score by up to **29.87 points**
   - Accounts with 29 days since last invocation: -29.87 points
   - Accounts with 0 days: 0 impact

2. **Invocation Velocity Change** (+0.416 per %)
   - Positive changes: up to +20.76 points
   - Negative changes: up to -29.24 points
   - Range: -29.24 to +20.76 points

3. **Error Rate** (+0.440 per %)
   - Range: +0.06 to +5.92 points
   - **Note**: Counterintuitive - higher error rate increases score

---

## Verification Results

### Accuracy Metrics

- **Perfect Matches**: 13/35 (37.1%)
- **Within 1 Point**: 30/35 (85.7%)
- **Within 2 Points**: 34/35 (97.1%)
- **Within 5 Points**: 35/35 (100.0%)
- **Mean Absolute Error**: 0.80 points
- **Max Absolute Error**: 3.00 points
- **RMSE**: 1.10 points

### Score Distribution

| Metric | Calculated | File | Difference |
|--------|-----------|------|------------|
| Range | 1 - 70 | 4 - 71 | Excellent |
| Mean | 49.1 | 49.2 | -0.1 |
| Median | 57.0 | 58.0 | -1.0 |

---

## Example Calculations

### Example 1: Elastic AI Corp (Worst Match: -3 points)

**Inputs**:
- `invocation_velocity_change_pct`: -67.7%
- `days_since_last_invocation`: 29
- `error_rate_pct`: 13.45%
- `monthly_spend`: $19,790.08
- `daily_invocations`: 2,208
- `p95_latency_ms`: 293,412

**Calculation**:
```
health_score = 52.14
    + (-67.7 × 0.416)      = -28.16
    - (29 × 1.030)         = -29.87
    + (13.45 × 0.440)      = +5.92
    + (19790.08 × 0.000035) = +0.69
    - (2208 × 0.00001)     = -0.02
    + (293412 × 0.000002)  = +0.59
    = 1.29 → 1 (rounded)
```

**File's score**: 4  
**Difference**: -3.0 points

---

### Example 2: Async Processing (Perfect Match: 0 points)

**Inputs**:
- `invocation_velocity_change_pct`: -67.0%
- `days_since_last_invocation`: 21
- `error_rate_pct`: 9.30%
- `monthly_spend`: $3,440.61
- `daily_invocations`: 189
- `p95_latency_ms`: 488,944

**Calculation**:
```
health_score = 52.14
    + (-67.0 × 0.416)      = -27.87
    - (21 × 1.030)         = -21.63
    + (9.30 × 0.440)       = +4.09
    + (3440.61 × 0.000035) = +0.12
    - (189 × 0.00001)      = -0.00
    + (488944 × 0.000002)  = +0.98
    = 7.83 → 8 (rounded)
```

**File's score**: 8  
**Difference**: 0.0 points ✅

---

### Example 3: Production ML API (Perfect Match: 0 points)

**Inputs**:
- `invocation_velocity_change_pct`: +30.0%
- `days_since_last_invocation`: 0
- `error_rate_pct`: 0.10%
- `monthly_spend`: $10,000.00
- `daily_invocations`: 50,000
- `p95_latency_ms`: 100,000

**Calculation**:
```
health_score = 52.14
    + (30.0 × 0.416)       = +12.48
    - (0 × 1.030)          = 0.00
    + (0.10 × 0.440)       = +0.04
    + (10000 × 0.000035)   = +0.35
    - (50000 × 0.00001)    = -0.50
    + (100000 × 0.000002)  = +0.20
    = 64.71 → 65 (rounded)
```

**Note**: This is a hypothetical example. Actual account may differ.

---

## Implementation Guide

### Step 1: Map KPIs to Formula Inputs

| Formula Input | KPI Name | Data Type | Source | Historical Data Required? |
|--------------|----------|-----------|--------|---------------------------|
| `invocation_velocity_change_pct` | Invocation Velocity Change | Percentage | Calculated from current vs previous period | ✅ **YES** - Previous period's invocation count |
| `days_since_last_invocation` | Days Since Last Invocation | Integer | Calculated from last invocation timestamp | ✅ **YES** - Last invocation timestamp |
| `error_rate_pct` | Error Rate | Percentage | KPI data (may be period-based) | ⚠️ **MAYBE** - Depends on calculation period |
| `monthly_spend` | Monthly Spend | Currency | Current month's KPI data | ❌ **NO** - Current value only |
| `daily_invocations` | Daily Invocations | Integer | Current day's KPI data | ❌ **NO** - Current value only |
| `p95_latency_ms` | P95 Latency | Milliseconds | Current period's KPI data | ⚠️ **MAYBE** - Depends on calculation period |

**Note**: `invocation_velocity_change_pct` must be calculated as:
```
velocity_change_pct = ((current_invocations - previous_invocations) / previous_invocations) × 100
```

### Step 2: Calculate Health Score

```python
def calculate_data_center_health_score(
    invocation_velocity_change_pct: float,
    days_since_last_invocation: int,
    error_rate_pct: float,
    monthly_spend: float,
    daily_invocations: int,
    p95_latency_ms: float
) -> int:
    """
    Calculate health score using regression formula.
    
    Returns:
        Health score (0-100, rounded to nearest integer)
    """
    score = (
        52.14
        + (invocation_velocity_change_pct * 0.416)
        - (days_since_last_invocation * 1.030)
        + (error_rate_pct * 0.440)
        + (monthly_spend * 0.000035)
        - (daily_invocations * 0.00001)
        + (p95_latency_ms * 0.000002)
    )
    
    # Round to nearest integer and clamp to 0-100
    return max(0, min(100, round(score)))
```

### Step 3: Integration with Our System

1. **KPI Mapping**: Map their KPIs to our KPI structure
2. **Calculation**: Use this formula instead of our reference-range system
3. **Storage**: Store calculated health score in `health_trends` table
4. **Display**: Show in Account Health dashboard

---

## Important Notes

### 1. **No Reference Ranges Needed (But Some Historical Data Required)**
Unlike our standard system, this formula **does not use reference ranges**. It's a direct linear regression.

**However, it DOES require some historical data:**
- **`invocation_velocity_change_pct`**: Requires previous period's invocation count to calculate the change
- **`days_since_last_invocation`**: Requires timestamp of last invocation

**What it DOESN'T need:**
- Reference range definitions (Critical/At Risk/Healthy thresholds)
- 3-month rolling averages (like the weighted component formula)
- Complex historical aggregations

### 2. **Counterintuitive Error Rate**
The error rate coefficient is **positive** (+0.440), meaning higher error rates increase the health score. This is likely a data artifact or the model learned this pattern from their data. **Do not change** - use as provided.

### 3. **Days Since Last Invocation**
This is the **most impactful** factor (-1.030 per day). Accounts with many days since last invocation will have significantly lower scores.

### 4. **Rounding**
Always round the final result to the nearest integer (0 decimal places).

### 5. **Bounds**
The formula can produce values outside 0-100. Consider clamping:
- `min(100, max(0, calculated_score))`

---

## Comparison with Weighted Component Formula

The customer initially provided a **weighted component formula**:
```
health_score = (velocity_score × 0.45) + (spend_score × 0.30) + (latency_score × 0.15) + (error_score × 0.10)
```

However, the **regression formula** (this document) is what actually matches their file. The weighted component formula was likely:
- An intended/planned formula
- A simplified explanation
- Not the actual implementation

**Use the regression formula** for this customer.

---

## Questions for Customer (Optional)

1. **Error Rate Coefficient**: Why is error rate positive? (Higher errors = higher score seems counterintuitive)
2. **Formula Source**: Was this derived from historical data regression?
3. **Updates**: Will this formula change over time as more data is collected?
4. **Bounds**: Should scores be clamped to 0-100, or can they go outside this range?

---

**Last Updated**: January 2025  
**Status**: ✅ Verified and Ready for Implementation

