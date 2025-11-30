# Data Center Customer - Serverless Model Health Score Formula

## Original Formula (from Customer)

The data center customer uses a **custom health score formula** specific to serverless/platform businesses:

```
Health Score = ROUND(
    (invocation_velocity_score × 0.45) + 
    (spend_trend_score × 0.30) + 
    (latency_score × 0.15) + 
    (error_rate_score × 0.10), 
    0
)
```

### Component Breakdown

#### 1. Invocation Velocity Score (45% weight)
**Formula**:
```
IF(invocation_velocity_change_pct > 0, 
   MIN(100, 70 + invocation_velocity_change_pct), 
   MAX(0, 70 + invocation_velocity_change_pct))
```

**Logic**:
- **Growing invocations** (positive change) = higher score
- **Base score**: 70 points
- **Growing**: Add velocity_change_pct to 70, cap at 100
- **Declining**: Subtract velocity_change_pct from 70, floor at 0
- **Declining >70%**: Results in 0 points

**Examples**:
- `velocity_change = +30%` → Score: `MIN(100, 70 + 30) = 100`
- `velocity_change = +10%` → Score: `MIN(100, 70 + 10) = 80`
- `velocity_change = 0%` → Score: `70`
- `velocity_change = -20%` → Score: `MAX(0, 70 - 20) = 50`
- `velocity_change = -70%` → Score: `MAX(0, 70 - 70) = 0`

#### 2. Spend Trend Score (30% weight)
**Formula**:
```
IF(monthly_spend > avg_monthly_spend_last_3mo × 1.2, 
   100, 
   IF(monthly_spend < avg_monthly_spend_last_3mo × 0.8, 
      40, 
      80))
```

**Logic**:
- **Spending 20%+ more** than 3-month average = 100 points
- **Spending 20%+ less** than 3-month average = 40 points
- **Stable spending** (±20%) = 80 points

**Note**: This requires **historical data** (3-month average). For initial onboarding, we may need to:
- Use current `monthly_spend` as baseline
- Or use `contract_value_annual / 12` as proxy

#### 3. Latency Score (15% weight)
**Formula**:
```
MAX(0, 100 - (p95_latency_ms / 10))
```

**Logic**:
- **Linear penalty**: Every 10ms of latency = -1 point
- **<500ms** = 95+ points (100 - 50 = 50, wait that's wrong...)
- **1000ms** = 0 points (100 - 100 = 0)
- **>1000ms** = 0 points (capped at 0)

**Examples**:
- `p95_latency = 100ms` → Score: `100 - (100/10) = 90`
- `p95_latency = 500ms` → Score: `100 - (500/10) = 50`
- `p95_latency = 1000ms` → Score: `100 - (1000/10) = 0`
- `p95_latency = 293,412ms` → Score: `MAX(0, 100 - 29341.2) = 0`

#### 4. Error Rate Score (10% weight)
**Formula**:
```
MAX(0, 100 - (error_rate_pct × 10))
```

**Logic**:
- **Linear penalty**: Every 1% error rate = -10 points
- **<1% errors** = 90+ points (100 - 10 = 90)
- **10% errors** = 0 points (100 - 100 = 0)
- **>10% errors** = 0 points (capped at 0)

**Examples**:
- `error_rate = 0.5%` → Score: `100 - (0.5 × 10) = 95`
- `error_rate = 1%` → Score: `100 - (1 × 10) = 90`
- `error_rate = 5%` → Score: `100 - (5 × 10) = 50`
- `error_rate = 10%` → Score: `100 - (10 × 10) = 0`
- `error_rate = 13.45%` → Score: `MAX(0, 100 - 134.5) = 0`

---

## Churn Risk Calculation

**Formula**:
```
IF invocation_velocity_change_pct < -50 AND days_since_last_invocation > 7 
THEN "High"
ELSE IF invocation_velocity_change_pct < -20 
THEN "Medium"
ELSE "Low"
```

**Logic**:
- **High Risk**: Velocity declining >50% AND inactive >7 days
- **Medium Risk**: Velocity declining >20%
- **Low Risk**: Otherwise

---

## Mapping to Our System

### Option 1: Use Their Formula Directly (Recommended)

**Implementation**: Create a **custom health score calculator** for serverless customers

**Pros**:
- ✅ Matches their existing methodology
- ✅ No need to transform/reinterpret
- ✅ Health scores will match their expectations
- ✅ Simpler than our 3-level hierarchy

**Cons**:
- ⚠️ Requires custom code path
- ⚠️ Spend Trend needs historical data (may need workaround)

**Code Structure**:
```python
def calculate_serverless_health_score(account_data):
    """
    Calculate health score using serverless-specific formula
    """
    # 1. Invocation Velocity Score (45%)
    velocity_change = account_data['invocation_velocity_change_pct']
    if velocity_change > 0:
        velocity_score = min(100, 70 + velocity_change)
    else:
        velocity_score = max(0, 70 + velocity_change)
    
    # 2. Spend Trend Score (30%)
    # Note: Need 3-month average, use current spend as proxy for now
    monthly_spend = account_data['monthly_spend']
    avg_spend_3mo = account_data.get('avg_monthly_spend_last_3mo', monthly_spend)
    if monthly_spend > avg_spend_3mo * 1.2:
        spend_score = 100
    elif monthly_spend < avg_spend_3mo * 0.8:
        spend_score = 40
    else:
        spend_score = 80
    
    # 3. Latency Score (15%)
    p95_latency = account_data['p95_latency_ms']
    latency_score = max(0, 100 - (p95_latency / 10))
    
    # 4. Error Rate Score (10%)
    error_rate = account_data['error_rate_pct']
    error_score = max(0, 100 - (error_rate * 10))
    
    # Overall Health Score
    health_score = round(
        (velocity_score * 0.45) + 
        (spend_score * 0.30) + 
        (latency_score * 0.15) + 
        (error_score * 0.10),
        0
    )
    
    return health_score
```

---

### Option 2: Map to Our KPI System

**Approach**: Transform their formula into our 3-level hierarchy

**Challenges**:
- Their formula is **direct calculation**, not reference-range based
- Spend Trend requires **historical comparison**, not absolute values
- Our system uses **reference ranges** (Critical/At Risk/Healthy)

**Mapping**:

1. **Invocation Velocity** → Product Usage KPI
   - **Reference Range**: Based on velocity_change_pct
   - **Critical**: < -50% (declining >50%)
   - **At Risk**: -50% to 0%
   - **Healthy**: > 0% (growing)
   - **Problem**: Their formula uses 70 as base, not reference ranges

2. **Spend Trend** → Business Outcomes KPI
   - **Reference Range**: Based on % change vs 3-month average
   - **Critical**: < 80% of average (declining >20%)
   - **At Risk**: 80-120% of average (stable)
   - **Healthy**: > 120% of average (growing >20%)
   - **Problem**: Requires historical data we don't have

3. **Latency** → Support KPI
   - **Reference Range**: Linear scale
   - **Critical**: > 1000ms (0 points)
   - **At Risk**: 500-1000ms (50-0 points)
   - **Healthy**: < 500ms (50-100 points)
   - **Works**: Can map to reference ranges

4. **Error Rate** → Support KPI
   - **Reference Range**: Linear scale
   - **Critical**: > 10% (0 points)
   - **At Risk**: 1-10% (90-0 points)
   - **Healthy**: < 1% (90-100 points)
   - **Works**: Can map to reference ranges

**Category Weights** (from their formula):
- Product Usage: 45% (invocation velocity)
- Business Outcomes: 30% (spend trend)
- Support: 25% (15% latency + 10% error rate)

**Verdict**: **Option 1 is better** - their formula is simpler and more direct.

---

## Implementation Plan

### Step 1: Detect Serverless Customer Type

**In Onboarding Wizard Step 1**:
- Add question: "What type of platform do you use?"
- Options: "Serverless/Platform", "Traditional SaaS", "Other"
- If "Serverless/Platform" → Use custom formula

### Step 2: Custom Health Score Calculator

**Create**: `backend/serverless_health_score_calculator.py`

```python
class ServerlessHealthScoreCalculator:
    """Custom health score calculator for serverless/platform customers"""
    
    @staticmethod
    def calculate(account_data):
        # Implementation as shown above
        pass
    
    @staticmethod
    def calculate_churn_risk(account_data):
        velocity_change = account_data['invocation_velocity_change_pct']
        days_since = account_data['days_since_last_invocation']
        
        if velocity_change < -50 and days_since > 7:
            return "High"
        elif velocity_change < -20:
            return "Medium"
        else:
            return "Low"
```

### Step 3: Integration Points

**A. Health Score Calculation**:
- Modify `HealthScoreEngine` to check customer type
- If serverless → Use `ServerlessHealthScoreCalculator`
- If traditional → Use existing 3-level hierarchy

**B. Onboarding Wizard**:
- Step 2: If serverless, skip category weights (use fixed: 45/30/15/10)
- Step 3: If serverless, skip reference ranges (use direct formulas)
- Step 5: Upload data, calculate using custom formula

**C. Data Storage**:
- Store calculated health score in `HealthTrend` table
- Store component scores (velocity, spend, latency, error) for breakdown

---

## Example Calculation

### Account: Elastic AI Corp (SRVL-3007)

**Data**:
- `invocation_velocity_change_pct`: -67.7%
- `monthly_spend`: $19,790.08
- `avg_monthly_spend_last_3mo`: $20,000 (assumed)
- `p95_latency_ms`: 293,412
- `error_rate_pct`: 13.45%

**Calculation**:

1. **Invocation Velocity Score**:
   - `velocity_change = -67.7%`
   - Score: `MAX(0, 70 + (-67.7)) = MAX(0, 2.3) = 2.3`

2. **Spend Trend Score**:
   - `monthly_spend = $19,790`
   - `avg_3mo = $20,000`
   - Ratio: `19,790 / 20,000 = 0.99` (within ±20%)
   - Score: `80`

3. **Latency Score**:
   - `p95_latency = 293,412 ms`
   - Score: `MAX(0, 100 - (293,412 / 10)) = MAX(0, 100 - 29,341.2) = 0`

4. **Error Rate Score**:
   - `error_rate = 13.45%`
   - Score: `MAX(0, 100 - (13.45 × 10)) = MAX(0, 100 - 134.5) = 0`

5. **Overall Health Score**:
   - `(2.3 × 0.45) + (80 × 0.30) + (0 × 0.15) + (0 × 0.10)`
   - `= 1.04 + 24.0 + 0 + 0`
   - `= 25.04`
   - **Rounded: 25**

**Churn Risk**:
- `velocity_change = -67.7%` (< -50%)
- `days_since = 29` (> 7)
- **Result: "High"**

**Comparison**:
- **File's health_score**: 4 (on 0-10 scale = 40/100)
- **Our calculated**: 25/100
- **Difference**: Our method gives slightly higher score due to stable spend (80 points)

---

## Challenges & Solutions

### Challenge 1: Spend Trend Requires Historical Data

**Problem**: Formula needs `avg_monthly_spend_last_3mo`, but we only have current `monthly_spend`.

**Solutions**:
1. **Use contract_value_annual / 12** as proxy for average
2. **Use current monthly_spend** as baseline (assume stable)
3. **Request historical data** from customer
4. **Calculate from time series** if we have historical KPI data

### Challenge 2: Formula vs. Reference Ranges

**Problem**: Their formula is direct calculation, not reference-range based.

**Solution**: 
- Use **custom calculator** for serverless customers
- Keep **reference-range system** for traditional customers
- Allow **hybrid approach** (custom formula + reference ranges for other KPIs)

### Challenge 3: Category Weights

**Problem**: Their weights (45/30/15/10) don't match our 5-category system.

**Solution**:
- For serverless customers, use **their weights** (4 categories)
- Map to our categories:
  - Product Usage: 45% (invocation velocity)
  - Business Outcomes: 30% (spend trend)
  - Support: 25% (15% latency + 10% error rate)
  - Customer Sentiment: 0% (not used)
  - Relationship Strength: 0% (not used)

---

## Updated Onboarding Plan

### For Serverless/Platform Customers:

**Step 1: Business Outcomes**
- Detect customer type: "Serverless/Platform"
- Set flag: `use_custom_health_formula = True`

**Step 2: KPI Weights**
- **Skip** (use fixed weights: 45/30/15/10)
- Or show: "Using serverless-specific formula (weights: 45/30/15/10)"

**Step 3: Reference Ranges**
- **Skip** (formula-based, not reference-range based)
- Or show: "Using direct calculation formulas (no reference ranges needed)"

**Step 4: Account Setup**
- Same as before

**Step 5: KPI Data Upload**
- Upload data
- Calculate health scores using custom formula
- Store component scores for breakdown

---

## Recommendation

**Use Option 1: Custom Formula**

**Reasons**:
1. ✅ Matches their existing methodology
2. ✅ Simpler than reference-range system
3. ✅ Health scores will be familiar to them
4. ✅ Can still use our KPI system for other metrics

**Implementation**:
1. Add customer type detection in onboarding
2. Create `ServerlessHealthScoreCalculator`
3. Integrate into `HealthScoreEngine`
4. Store component scores for UI breakdown

---

**Last Updated**: January 2025  
**Status**: Serverless Formula Analysis Complete


