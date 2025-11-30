# Data Center Customer - KPI Reference Ranges & Alerts

**Purpose**: These reference ranges define healthy, at-risk, and critical thresholds for each KPI to detect anomalous data and trigger appropriate alerts.

**Methodology**: Ranges are calculated from 35 production-quality customer records using percentile analysis:
- **Healthy Range**: P75 - Max (top 25% performers)
- **Risk Range**: P25 - P75 (middle 50%)
- **Critical Range**: Min - P25 (bottom 25%)

**Note**: While the health score uses a regression formula (not reference ranges), these ranges are critical for:
1. **Alerting**: Detecting anomalies and triggering playbooks
2. **Visualization**: Color-coding KPIs in dashboards
3. **Playbook Triggers**: Automatic action recommendations

---

## 📊 COMPLETE KPI REFERENCE RANGES

### 1. Daily Invocations

**KPI Name**: `daily_invocations`  
**Unit**: count  
**Direction**: ↑ Higher is Better  
**Correlation with Health**: 0.223

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 32,551 | 267,534 | High-volume production workload |
| 🟡 **RISK** | 956 | 32,551 | Moderate usage, watch for decline |
| 🔴 **CRITICAL** | 0 | 956 | Very low usage, likely churning |

**Data Distribution**:
- Min: 150 | P25: 956 | Median: 3,616 | P75: 32,551 | Max: 178,356

---

### 2. Invocations (30-day)

**KPI Name**: `invocations_30d`  
**Unit**: count  
**Direction**: ↑ Higher is Better  
**Correlation with Health**: 0.223

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 976,530 | 8,026,020 | Enterprise-scale usage |
| 🟡 **RISK** | 28,680 | 976,530 | Growing but not yet scaled |
| 🔴 **CRITICAL** | 0 | 28,680 | Minimal usage, trial phase |

**Data Distribution**:
- Min: 4,500 | P25: 28,680 | Median: 108,480 | P75: 976,530 | Max: 5,350,680

---

### 3. Invocation Velocity Change (%)

**KPI Name**: `invocation_velocity_change_pct`  
**Unit**: %  
**Direction**: ↑ Higher is Better  
**Correlation with Health**: **0.985** ⭐ **STRONGEST PREDICTOR**

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 30% | 75% | Rapid growth, high expansion potential |
| 🟡 **RISK** | -15% | 30% | Slow growth or stabilizing |
| 🔴 **CRITICAL** | -100% | -15% | Declining usage, churn risk |

**Data Distribution**:
- Min: -70.3% | P25: -15.2% | Median: 11.1% | P75: 30.0% | Max: 49.9%

**⚠️ CRITICAL THRESHOLD**: < -15% MoM decline = High churn risk

**Playbook Alerts**:
- 🔴 **Alert**: Velocity < -15% for 2 weeks → At-risk alert
- 🔴 **Alert**: Error rate > 2% + Velocity < 0% → Churn risk alert

---

### 4. Monthly Spend

**KPI Name**: `monthly_spend`  
**Unit**: USD  
**Direction**: ↑ Higher is Better  
**Correlation with Health**: 0.060

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | $13,046 | $81,205 | High-value customer |
| 🟡 **RISK** | $1,386 | $13,046 | Mid-tier spend |
| 🔴 **CRITICAL** | $0 | $1,386 | Low spend, trial or churning |

**Data Distribution**:
- Min: $229 | P25: $1,386 | Median: $3,441 | P75: $13,046 | Max: $54,137

---

### 5. Days Since Last Invocation

**KPI Name**: `days_since_last_invocation`  
**Unit**: days  
**Direction**: ↓ Lower is Better  
**Correlation with Health**: **-0.924** ⭐ **STRONG CHURN SIGNAL**

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 0 | 1 | Active daily usage |
| 🟡 **RISK** | 1 | 8 | Occasional usage, needs re-engagement |
| 🔴 **CRITICAL** | 8 | 44 | Inactive, high churn probability |

**Data Distribution**:
- Min: 0 | P25: 1 | Median: 3 | P75: 8 | Max: 29

**⚠️ CRITICAL THRESHOLD**: > 14 days inactive = Trigger immediate CSM outreach

**Playbook Alerts**:
- 🟡 **Alert**: Days inactive > 7 → Re-engagement alert
- 🔴 **Alert**: Days inactive > 14 → CSM escalation

---

### 6. Error Rate (%)

**KPI Name**: `error_rate_pct`  
**Unit**: %  
**Direction**: ↓ Lower is Better  
**Correlation with Health**: **-0.868** ⭐ **STRONG QUALITY SIGNAL**

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 0% | 0.64% | Excellent reliability |
| 🟡 **RISK** | 0.64% | 2.03% | Moderate errors, needs investigation |
| 🔴 **CRITICAL** | 2.03% | 20.17% | Poor quality, high support burden |

**Data Distribution**:
- Min: 0.13% | P25: 0.64% | Median: 1.21% | P75: 2.03% | Max: 13.45%

**⚠️ CRITICAL THRESHOLD**: > 5% error rate = Infrastructure issue, escalate to engineering

**Playbook Alerts**:
- 🟡 **Alert**: Error rate > 2% → Investigation needed
- 🔴 **Alert**: Error rate > 5% → Engineering escalation
- 🔴 **Alert**: Error rate > 2% + Velocity < 0% → Churn risk alert

---

### 7. P95 Latency

**KPI Name**: `p95_latency_ms`  
**Unit**: milliseconds  
**Direction**: ↑ Higher is Better (Note: This seems inverted - review)  
**Correlation with Health**: 0.062

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 414,223 | 883,815 | Complex workloads |
| 🟡 **RISK** | 156,138 | 414,223 | Standard latency |
| 🔴 **CRITICAL** | 0 | 156,138 | Fast but possibly shallow usage |

**Data Distribution**:
- Min: 86,021ms | P25: 156,138ms | Median: 235,327ms | P75: 414,223ms | Max: 589,210ms

**⚠️ NOTE**: Low correlation suggests latency alone doesn't predict health. Consider removing or inverting direction.

---

### 8. Average Execution Time

**KPI Name**: `avg_execution_time_sec`  
**Unit**: seconds  
**Direction**: ↑ Higher is Better (Note: Review this - longer execution may indicate inefficiency)  
**Correlation with Health**: 0.063

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 407.9 | 875.7 | Long-running compute tasks |
| 🟡 **RISK** | 152.4 | 407.9 | Medium execution time |
| 🔴 **CRITICAL** | 0 | 152.4 | Short/simple tasks |

**Data Distribution**:
- Min: 83.3s | P25: 152.4s | Median: 229.3s | P75: 407.9s | Max: 583.8s

**⚠️ NOTE**: Weak correlation. This metric may not be useful for health scoring.

---

### 9. Cold Start Percentage

**KPI Name**: `cold_start_pct`  
**Unit**: %  
**Direction**: ↓ Lower is Better  
**Correlation with Health**: -0.059

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 0% | 21.5% | Warm containers, frequent usage |
| 🟡 **RISK** | 21.5% | 60.65% | Moderate cold starts |
| 🔴 **CRITICAL** | 60.65% | 116.4% | High cold starts, infrequent use |

**Data Distribution**:
- Min: 9.5% | P25: 21.5% | Median: 47.8% | P75: 60.65% | Max: 77.6%

---

### 10. Health Score

**KPI Name**: `health_score`  
**Unit**: score (0-100)  
**Direction**: ↑ Higher is Better  
**Correlation with Health**: 1.000 (by definition)

| Range | Min | Max | Description |
|-------|-----|-----|-------------|
| 🟢 **HEALTHY** | 65 | 107 | Low churn risk, expansion opportunity |
| 🟡 **RISK** | 39 | 65 | Needs CSM intervention |
| 🔴 **CRITICAL** | 0 | 39 | High churn probability, urgent action |

**Data Distribution**:
- Min: 4 | P25: 39 | Median: 58 | P75: 65 | Max: 71

**Alignment with Churn Risk**:
- Health < 20 → High Churn Risk (5 customers)
- Health 20-49 → Medium Churn Risk (4 customers)
- Health ≥ 50 → Low Churn Risk (26 customers)

---

## 🎯 KEY INSIGHTS

### Most Important KPIs for Health Prediction

1. **Invocation Velocity Change** (r=0.985) - Primary growth indicator
2. **Days Since Last Invocation** (r=-0.924) - Primary churn signal
3. **Error Rate** (r=-0.868) - Quality/satisfaction indicator

### Weak Predictors (Consider De-emphasizing)

- P95 Latency (r=0.062)
- Avg Execution Time (r=0.063)
- Cold Start % (r=-0.059)
- Monthly Spend (r=0.060)

---

## 🚨 RECOMMENDED ALERT THRESHOLDS (For Playbook Creation)

### Critical Alerts (Immediate Action Required)

1. **Velocity Decline Alert**
   - **Trigger**: `invocation_velocity_change_pct < -15%` for 2 weeks
   - **Action**: At-risk alert → CSM outreach
   - **Priority**: High

2. **Inactivity Alert**
   - **Trigger**: `days_since_last_invocation > 7`
   - **Action**: Re-engagement alert → CSM outreach
   - **Priority**: Medium

3. **Inactivity Escalation**
   - **Trigger**: `days_since_last_invocation > 14`
   - **Action**: CSM escalation → Manager notification
   - **Priority**: Critical

4. **Error Rate Escalation**
   - **Trigger**: `error_rate_pct > 5%`
   - **Action**: Engineering escalation → Technical support
   - **Priority**: Critical

5. **Combined Churn Risk Alert**
   - **Trigger**: `error_rate_pct > 2%` AND `invocation_velocity_change_pct < 0%`
   - **Action**: Churn risk alert → Executive review
   - **Priority**: Critical

### Warning Alerts (Monitor & Investigate)

6. **Error Rate Warning**
   - **Trigger**: `error_rate_pct > 2%` AND `error_rate_pct <= 5%`
   - **Action**: Investigation needed → CSM review
   - **Priority**: Medium

7. **Low Usage Alert**
   - **Trigger**: `daily_invocations < 956` for 1 week
   - **Action**: Usage decline alert → CSM outreach
   - **Priority**: Medium

8. **Health Score Decline**
   - **Trigger**: `health_score < 39` (Critical range)
   - **Action**: Health intervention → CSM action plan
   - **Priority**: High

---

## 📋 PLAYBOOK TRIGGER CONFIGURATION

### Playbook 1: Velocity Decline Response
```yaml
name: "Velocity Decline Response"
trigger:
  condition: "invocation_velocity_change_pct < -15%"
  duration: "14 days"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "csm"
    message: "Account showing declining velocity for 2 weeks"
  - type: "recommendation"
    category: "re-engagement"
    priority: "high"
```

### Playbook 2: Inactivity Re-engagement
```yaml
name: "Inactivity Re-engagement"
trigger:
  condition: "days_since_last_invocation > 7"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "csm"
    message: "Account inactive for 7+ days"
  - type: "recommendation"
    category: "re-engagement"
    priority: "medium"
```

### Playbook 3: Inactivity Escalation
```yaml
name: "Inactivity Escalation"
trigger:
  condition: "days_since_last_invocation > 14"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "csm_manager"
    message: "Account inactive for 14+ days - urgent action required"
  - type: "recommendation"
    category: "churn_prevention"
    priority: "critical"
```

### Playbook 4: Error Rate Investigation
```yaml
name: "Error Rate Investigation"
trigger:
  condition: "error_rate_pct > 2%"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "csm"
    message: "Error rate above threshold - investigation needed"
  - type: "recommendation"
    category: "technical_support"
    priority: "medium"
```

### Playbook 5: Error Rate Escalation
```yaml
name: "Error Rate Escalation"
trigger:
  condition: "error_rate_pct > 5%"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "engineering"
    message: "Error rate critical - infrastructure issue suspected"
  - type: "recommendation"
    category: "technical_escalation"
    priority: "critical"
```

### Playbook 6: Combined Churn Risk
```yaml
name: "Combined Churn Risk"
trigger:
  condition: "error_rate_pct > 2% AND invocation_velocity_change_pct < 0%"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "executive"
    message: "Multiple risk factors detected - high churn probability"
  - type: "recommendation"
    category: "executive_review"
    priority: "critical"
```

### Playbook 7: Health Score Intervention
```yaml
name: "Health Score Intervention"
trigger:
  condition: "health_score < 39"
  duration: "immediate"
  frequency: "daily"
actions:
  - type: "alert"
    recipient: "csm"
    message: "Health score in critical range - intervention required"
  - type: "recommendation"
    category: "health_intervention"
    priority: "high"
```

---

## 🔄 INTEGRATION WITH HEALTH SCORE CALCULATION

**Important Note**: 
- The **health score calculation** uses the **regression formula** (does not use reference ranges)
- The **reference ranges** are used for:
  1. **Alerting** (playbook triggers)
  2. **Visualization** (color-coding in dashboards)
  3. **KPI status** (healthy/risk/critical indicators)

This separation allows:
- ✅ Accurate health scores via regression formula
- ✅ Actionable alerts via reference ranges
- ✅ Clear visual indicators for CSMs

---

## 📊 DATABASE SCHEMA REQUIREMENTS

### KPIReferenceRange Table (for Data Center Customer)

```sql
INSERT INTO kpi_reference_ranges (
    customer_id,
    kpi_name,
    unit,
    higher_is_better,
    critical_min,
    critical_max,
    risk_min,
    risk_max,
    healthy_min,
    healthy_max,
    description
) VALUES
-- Daily Invocations
(6, 'daily_invocations', 'count', true, 0, 956, 956, 32551, 32551, 267534, 'Daily invocation count'),
-- Invocations 30-day
(6, 'invocations_30d', 'count', true, 0, 28680, 28680, 976530, 976530, 8026020, '30-day invocation count'),
-- Invocation Velocity Change
(6, 'invocation_velocity_change_pct', '%', true, -100, -15, -15, 30, 30, 75, 'Month-over-month velocity change'),
-- Monthly Spend
(6, 'monthly_spend', 'USD', true, 0, 1386, 1386, 13046, 13046, 81205, 'Monthly spend in USD'),
-- Days Since Last Invocation
(6, 'days_since_last_invocation', 'days', false, 8, 44, 1, 8, 0, 1, 'Days since last invocation'),
-- Error Rate
(6, 'error_rate_pct', '%', false, 2.03, 20.17, 0.64, 2.03, 0, 0.64, 'Error rate percentage'),
-- P95 Latency
(6, 'p95_latency_ms', 'milliseconds', true, 0, 156138, 156138, 414223, 414223, 883815, 'P95 latency in milliseconds'),
-- Average Execution Time
(6, 'avg_execution_time_sec', 'seconds', true, 0, 152.4, 152.4, 407.9, 407.9, 875.7, 'Average execution time in seconds'),
-- Cold Start Percentage
(6, 'cold_start_pct', '%', false, 60.65, 116.4, 21.5, 60.65, 0, 21.5, 'Cold start percentage'),
-- Health Score
(6, 'health_score', 'score', true, 0, 39, 39, 65, 65, 107, 'Overall health score (0-100)');
```

---

**Last Updated**: January 2025  
**Status**: Ready for Playbook Implementation

