# Data Center Customer - Health Score Calculation

## Context

The data center customer file (`serverless_model_cs_platform.xlsx`) already contains a `health_score` column (0-10 scale), but our system calculates health scores from KPIs using reference ranges. This document explains how we would calculate health scores for this specific customer.

---

## Current State

### Existing Health Scores (from file)
- **Scale**: 0-10 (different from our 0-100 scale)
- **Distribution**: Varies across 35 accounts
- **Source**: Unknown (may be manually calculated or from another system)

### Our System's Approach
- **Scale**: 0-100
- **Method**: Calculated from KPIs using reference ranges
- **Formula**: 3-level hierarchy (KPI → Category → Overall)

---

## Data Center Customer's KPIs

### Available Metrics (13 KPIs):

1. **Product Usage KPIs**:
   - `daily_invocations` (e.g., 2,208)
   - `invocations_30d` (e.g., 66,240)
   - `invocation_velocity_change_pct` (e.g., -67.7%)
   - `days_since_last_invocation` (e.g., 29 days)

2. **Support KPIs**:
   - `avg_execution_time_sec` (e.g., 290.9 seconds)
   - `cold_start_pct` (e.g., 21.0%)
   - `p95_latency_ms` (e.g., 293,412 ms)
   - `error_rate_pct` (e.g., 13.45%)

3. **Business Outcomes KPIs**:
   - `monthly_spend` (e.g., $19,790.08)
   - `contract_value_annual` (e.g., $237,480.95)
   - `expansion_potential` (Low/Medium/High → needs conversion to numeric)

4. **Customer Sentiment KPIs**:
   - `health_score` (0-10 scale → needs conversion to 0-100)
   - `churn_risk` (High/Medium/Low → needs conversion to numeric)

---

## Reference Ranges Needed

### Critical Step: Define Reference Ranges for Each KPI

For the data center customer, we need to define what "Critical", "At Risk", and "Healthy" means for each metric:

#### 1. Daily Invocations
- **Higher is Better**: Yes (more usage = better)
- **Data Range**: 150 - 178,356 (Average: 26,256)
- **Percentiles**: P25=956, P50=3,616, P75=32,551
- **Critical**: < 956 invocations/day (bottom 25%)
- **At Risk**: 956-3,616 invocations/day (25th-50th percentile)
- **Healthy**: > 32,551 invocations/day (top 25%)

#### 2. Monthly Invocations (invocations_30d)
- **Higher is Better**: Yes
- **Data Range**: 4,500 - 5,350,680 (Average: 787,677)
- **Percentiles**: P25=28,680, P50=108,480, P75=976,530
- **Critical**: < 28,680/month (bottom 25%)
- **At Risk**: 28,680-108,480/month (25th-50th percentile)
- **Healthy**: > 976,530/month (top 25%)

#### 3. Average Execution Time
- **Higher is Better**: No (lower is better)
- **Data Range**: 83.3 - 583.8 seconds (Average: 276.6)
- **Percentiles**: P25=152.4, P50=229.3, P75=407.9
- **Critical**: > 407.9 seconds (top 25% = slowest)
- **At Risk**: 229.3-407.9 seconds (50th-75th percentile)
- **Healthy**: < 152.4 seconds (bottom 25% = fastest)

#### 4. Cold Start Percentage
- **Higher is Better**: No (lower is better)
- **Data Range**: 9.5% - 77.6% (Average: 42.2%)
- **Percentiles**: P25=21.5%, P50=47.8%, P75=60.7%
- **Critical**: > 60.7% (top 25% = worst)
- **At Risk**: 47.8%-60.7% (50th-75th percentile)
- **Healthy**: < 21.5% (bottom 25% = best)

#### 5. P95 Latency
- **Higher is Better**: No (lower is better)
- **Data Range**: 86,021 - 589,210 ms (Average: 281,038 ms)
- **Percentiles**: P25=156,138, P50=235,327, P75=414,223
- **Critical**: > 414,223 ms (top 25% = slowest)
- **At Risk**: 235,327-414,223 ms (50th-75th percentile)
- **Healthy**: < 156,138 ms (bottom 25% = fastest)

#### 6. Error Rate
- **Higher is Better**: No (lower is better)
- **Data Range**: 0.13% - 13.45% (Average: 2.52%)
- **Percentiles**: P25=0.64%, P50=1.21%, P75=2.03%
- **Critical**: > 2.03% (top 25% = worst)
- **At Risk**: 1.21%-2.03% (50th-75th percentile)
- **Healthy**: < 0.64% (bottom 25% = best)

#### 7. Monthly Spend
- **Higher is Better**: Yes (more revenue = better)
- **Data Range**: $229 - $54,137 (Average: $10,200)
- **Percentiles**: P25=$1,386, P50=$3,441, P75=$13,046
- **Critical**: < $1,386/month (bottom 25%)
- **At Risk**: $1,386-$3,441/month (25th-50th percentile)
- **Healthy**: > $13,046/month (top 25%)

#### 8. Annual Contract Value
- **Higher is Better**: Yes
- **Data Range**: $2,751 - $649,638 (Average: $122,395)
- **Percentiles**: P25=$16,631, P50=$41,287, P75=$156,551
- **Critical**: < $16,631/year (bottom 25%)
- **At Risk**: $16,631-$41,287/year (25th-50th percentile)
- **Healthy**: > $156,551/year (top 25%)

#### 9. Invocation Velocity Change
- **Higher is Better**: Yes (positive growth = better)
- **Data Range**: -70.3% to +49.9% (Average: +3.0%)
- **Percentiles**: P25=-15.2%, P50=+11.1%, P75=+30.0%
- **Critical**: < -15% (declining, bottom 25%)
- **At Risk**: -15% to +11% (25th-50th percentile)
- **Healthy**: > +30% (growing, top 25%)

#### 10. Days Since Last Invocation
- **Higher is Better**: No (lower is better = more active)
- **Data Range**: 0 - 29 days (Average: 5.9 days)
- **Percentiles**: P25=1 day, P50=3 days, P75=8 days
- **Critical**: > 8 days (top 25% = least active)
- **At Risk**: 3-8 days (50th-75th percentile)
- **Healthy**: < 1 day (bottom 25% = most active)

#### 11. Expansion Potential (Text → Numeric)
- **Conversion**: Low=1, Medium=2, High=3
- **Higher is Better**: Yes
- **Critical**: 1 (Low)
- **At Risk**: 2 (Medium)
- **Healthy**: 3 (High)

#### 12. Churn Risk (Text → Numeric)
- **Conversion**: High=1, Medium=2, Low=3
- **Higher is Better**: No (lower churn risk = better)
- **Critical**: 1 (High churn risk)
- **At Risk**: 2 (Medium churn risk)
- **Healthy**: 3 (Low churn risk)

#### 13. Health Score (0-10 → 0-100)
- **Conversion**: Multiply by 10 (4/10 → 40/100)
- **Higher is Better**: Yes
- **Data Range**: 4-71 (Average: 49.2, Median: 58.0)
- **Note**: File uses 0-10 scale, but values go up to 71 (likely 0-100 scale)
- **Critical**: < 30 (bottom 25% of accounts)
- **At Risk**: 30-60 (middle 50% of accounts)
- **Healthy**: > 60 (top 25% of accounts)

---

## Health Score Calculation Example

### Account: Elastic AI Corp (SRVL-3007)

**Raw Metrics**:
- Error Rate: 13.45%
- Daily Invocations: 2,208
- Monthly Spend: $19,790.08
- Health Score: 4/10
- Churn Risk: High
- Days Since Last Invocation: 29

**Step 1: KPI-Level Scores**

1. **Error Rate: 13.45%**
   - Status: Critical (> 10%)
   - Score: 0-33 range → Calculate: ~15 points
   - Impact: Critical (3x)
   - Weighted: 15 × 3 = 45

2. **Daily Invocations: 2,208**
   - Status: Healthy (> 500)
   - Score: 67-100 range → Calculate: ~85 points
   - Impact: High (2x)
   - Weighted: 85 × 2 = 170

3. **Monthly Spend: $19,790**
   - Status: Healthy (> $10,000)
   - Score: 67-100 range → Calculate: ~90 points
   - Impact: High (2x)
   - Weighted: 90 × 2 = 180

4. **Health Score: 4/10 → 40/100**
   - Status: At Risk (30-60)
   - Score: 34-66 range → Calculate: ~50 points
   - Impact: Critical (3x)
   - Weighted: 50 × 3 = 150

5. **Churn Risk: High → 1**
   - Status: Critical (High risk = 1)
   - Score: 0-33 range → Calculate: ~20 points
   - Impact: Critical (3x)
   - Weighted: 20 × 3 = 60

6. **Days Since Last Invocation: 29**
   - Status: At Risk (7-30 days)
   - Score: 34-66 range → Calculate: ~45 points
   - Impact: High (2x)
   - Weighted: 45 × 2 = 90

**Step 2: Category Scores**

**Product Usage Category**:
- Daily Invocations: 170
- Days Since Last Invocation: 90
- Total Weighted: 260
- Total Impact Weights: 2 + 2 = 4
- **Category Score**: 260 / 4 = **65.0**

**Support Category**:
- Error Rate: 45
- (Other support KPIs...)
- **Category Score**: ~**42.0** (example)

**Business Outcomes Category**:
- Monthly Spend: 180
- (Other business KPIs...)
- **Category Score**: ~**68.5** (example)

**Customer Sentiment Category**:
- Health Score: 150
- Churn Risk: 60
- Total Weighted: 210
- Total Impact Weights: 3 + 3 = 6
- **Category Score**: 210 / 6 = **35.0**

**Step 3: Overall Health Score**

**Category Weights** (from Step 2 of onboarding):
- Product Usage: 35% (0.35)
- Business Outcomes: 25% (0.25)
- Support: 20% (0.20)
- Customer Sentiment: 15% (0.15)
- Relationship Strength: 5% (0.05)

**Weighted Contributions**:
- Product Usage: 65.0 × 0.35 = 22.75
- Business Outcomes: 68.5 × 0.25 = 17.13
- Support: 42.0 × 0.20 = 8.40
- Customer Sentiment: 35.0 × 0.15 = 5.25
- Relationship Strength: 50.0 × 0.05 = 2.50 (example)

**Overall Score**: (22.75 + 17.13 + 8.40 + 5.25 + 2.50) / 1.00 = **56.03**

**Status**: At Risk (34-66 range)

---

## Key Differences

### Existing Health Score (from file)
- **Scale**: 0-10
- **Value**: 4/10
- **Meaning**: "At Risk" (assuming 0-3=Critical, 4-6=At Risk, 7-10=Healthy)

### Our Calculated Health Score
- **Scale**: 0-100
- **Value**: ~56/100
- **Meaning**: "At Risk" (34-66 range)
- **Method**: Calculated from 13 KPIs using reference ranges

### Conversion
- Existing: 4/10 = 40/100 (if we just multiply)
- Calculated: 56/100 (from KPIs)
- **Difference**: Our method gives higher score because:
  - Daily Invocations (2,208) is healthy
  - Monthly Spend ($19,790) is healthy
  - These positive KPIs offset the negative ones (Error Rate, Churn Risk)

---

## Why This Matters for Onboarding

### Step 3: Reference Ranges
**CRITICAL**: We must define reference ranges for all 13 KPIs. Without them:
- Health scores will be **0** or **incorrect**
- System can't calculate scores
- Dashboard won't show meaningful data

### Step 2: Category Weights
**IMPORTANT**: Weights determine which categories matter most:
- Product Usage: 35% (usage metrics are core)
- Business Outcomes: 25% (revenue matters)
- Support: 20% (performance matters)
- Customer Sentiment: 15% (health/churn matter)
- Relationship Strength: 5% (less relevant for platform)

### Step 5: KPI Data Upload
**REQUIRED**: Transform file metrics to KPI records:
- Each metric becomes a KPI
- Assign proper category
- Assign impact level (Critical/High/Medium/Low)
- Store data value

---

## Validation

### Compare Calculated vs. Existing Scores

After onboarding, we can:
1. Calculate health scores using our method
2. Compare with existing `health_score` column
3. Identify discrepancies
4. Adjust reference ranges if needed

### Example Comparison:
```
Account: Elastic AI Corp
Existing Score: 4/10 (40/100)
Calculated Score: 56/100
Difference: +16 points

Reason: Our method considers:
- Positive: High invocations, high spend
- Negative: High error rate, high churn risk
- Net: Slightly positive (56 vs 40)
```

---

## Next Steps

1. **Define Reference Ranges** (Step 3)
   - Use industry benchmarks for data center/serverless
   - Adjust based on customer's actual data distribution
   - Store in `KPIReferenceRange` table

2. **Set Category Weights** (Step 2)
   - Product Usage: 35%
   - Business Outcomes: 25%
   - Support: 20%
   - Customer Sentiment: 15%
   - Relationship Strength: 5%

3. **Transform & Upload Data** (Step 5)
   - Convert 13 metrics to KPI records
   - Assign categories and impact levels
   - Upload 35 accounts × 13 KPIs = 455 records

4. **Calculate & Validate**
   - System calculates health scores
   - Compare with existing scores
   - Adjust reference ranges if needed

---

**Last Updated**: January 2025  
**Status**: Data Center Customer Specific Analysis

