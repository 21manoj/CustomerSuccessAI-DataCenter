# Data Center Customer - Edge Cases & Code Path Handling

## Overview

This document addresses edge cases and code paths for the data center customer's regression health score formula, specifically:
1. **New accounts** (no historical data)
2. **Missing KPI data** (incomplete inputs)
3. **No reference ranges** (regression formula doesn't use them)

---

## Formula Requirements

```python
health_score = 52.14 
    + (invocation_velocity_change_pct × 0.416)
    - (days_since_last_invocation × 1.030)
    + (error_rate_pct × 0.440)
    + (monthly_spend × 0.000035)
    - (daily_invocations × 0.00001)
    + (p95_latency_ms × 0.000002)
```

### Required Inputs

| Input | Type | Historical Data Required? | Can Be Missing? |
|-------|------|---------------------------|------------------|
| `invocation_velocity_change_pct` | Float | ✅ YES (previous period) | ⚠️ **Critical** |
| `days_since_last_invocation` | Integer | ✅ YES (last invocation timestamp) | ⚠️ **Critical** |
| `error_rate_pct` | Float | ⚠️ Maybe (period-based) | ⚠️ **Important** |
| `monthly_spend` | Float | ❌ NO | ⚠️ **Important** |
| `daily_invocations` | Integer | ❌ NO | ✅ **Optional** |
| `p95_latency_ms` | Float | ⚠️ Maybe (period-based) | ✅ **Optional** |

---

## Edge Case 1: New Account (No Historical Data)

### Scenario
Customer adds a new account. We don't have:
- Previous period's invocation count (can't calculate `velocity_change_pct`)
- Last invocation timestamp (can't calculate `days_since_last_invocation`)

### Code Path Options

#### Option A: Use Default Values (Recommended)
```python
def calculate_data_center_health_score(
    invocation_velocity_change_pct: Optional[float] = None,
    days_since_last_invocation: Optional[int] = None,
    error_rate_pct: Optional[float] = None,
    monthly_spend: Optional[float] = None,
    daily_invocations: Optional[int] = None,
    p95_latency_ms: Optional[float] = None
) -> int:
    """
    Calculate health score with graceful handling of missing data.
    """
    # Default values for missing historical data
    if invocation_velocity_change_pct is None:
        invocation_velocity_change_pct = 0.0  # No change (neutral)
    
    if days_since_last_invocation is None:
        days_since_last_invocation = 0  # Assumes active today
    
    # Default values for optional metrics
    if error_rate_pct is None:
        error_rate_pct = 0.0  # No errors
    
    if monthly_spend is None:
        monthly_spend = 0.0  # No spend
    
    if daily_invocations is None:
        daily_invocations = 0  # No invocations
    
    if p95_latency_ms is None:
        p95_latency_ms = 0.0  # No latency data
    
    # Calculate score
    score = (
        52.14
        + (invocation_velocity_change_pct * 0.416)
        - (days_since_last_invocation * 1.030)
        + (error_rate_pct * 0.440)
        + (monthly_spend * 0.000035)
        - (daily_invocations * 0.00001)
        + (p95_latency_ms * 0.000002)
    )
    
    return max(0, min(100, round(score)))
```

**Result for new account with defaults:**
```
score = 52.14 + 0 - 0 + 0 + 0 - 0 + 0 = 52.14 → 52
```

**Pros:**
- ✅ Always produces a score
- ✅ Neutral starting point (52 = base score)
- ✅ Simple to implement

**Cons:**
- ⚠️ May not reflect actual account state
- ⚠️ Assumes account is active (days_since = 0)

---

#### Option B: Return "Insufficient Data" Status
```python
def calculate_data_center_health_score(...) -> Dict:
    """
    Returns score with data quality indicator.
    """
    missing_critical = []
    
    if invocation_velocity_change_pct is None:
        missing_critical.append('invocation_velocity_change_pct')
    
    if days_since_last_invocation is None:
        missing_critical.append('days_since_last_invocation')
    
    if missing_critical:
        return {
            'score': None,
            'status': 'insufficient_data',
            'missing_fields': missing_critical,
            'message': 'Cannot calculate health score: missing historical data'
        }
    
    # ... calculate score ...
    return {
        'score': calculated_score,
        'status': 'complete',
        'missing_fields': []
    }
```

**Pros:**
- ✅ Explicit about data quality
- ✅ Frontend can show "Data Pending" status

**Cons:**
- ❌ No score displayed until data available
- ❌ More complex UI handling

---

#### Option C: Use Contract Value as Proxy
```python
def calculate_data_center_health_score(
    ...,
    contract_value_annual: Optional[float] = None
) -> int:
    """
    Use contract value to estimate missing values.
    """
    # If no monthly_spend, estimate from contract
    if monthly_spend is None and contract_value_annual:
        monthly_spend = contract_value_annual / 12
    
    # If no velocity_change, assume stable (0%)
    if invocation_velocity_change_pct is None:
        invocation_velocity_change_pct = 0.0
    
    # If no days_since, assume active (0 days)
    if days_since_last_invocation is None:
        days_since_last_invocation = 0
    
    # ... rest of calculation ...
```

**Pros:**
- ✅ Uses available data (contract value)
- ✅ More realistic estimates

**Cons:**
- ⚠️ Still requires assumptions
- ⚠️ More complex logic

---

### **Recommendation: Option A (Default Values)**

**Rationale:**
- Simplest to implement
- Always produces a score
- Neutral starting point (52 = base score)
- Can be refined as data becomes available

---

## Edge Case 2: Missing Individual KPI Values

### Scenario
Account exists, but some KPIs are missing (e.g., no error_rate_pct in current upload).

### Code Path

```python
def calculate_data_center_health_score(...) -> int:
    """
    Handle missing individual KPIs gracefully.
    """
    # Critical fields: Use defaults if missing
    if invocation_velocity_change_pct is None:
        invocation_velocity_change_pct = 0.0  # Assume no change
    
    if days_since_last_invocation is None:
        days_since_last_invocation = 0  # Assume active today
    
    # Important fields: Use defaults if missing
    if error_rate_pct is None:
        error_rate_pct = 0.0  # Assume no errors
    
    if monthly_spend is None:
        monthly_spend = 0.0  # Assume no spend
    
    # Optional fields: Use 0 if missing (minimal impact)
    if daily_invocations is None:
        daily_invocations = 0
    
    if p95_latency_ms is None:
        p95_latency_ms = 0.0
    
    # Calculate score
    score = (
        52.14
        + (invocation_velocity_change_pct * 0.416)
        - (days_since_last_invocation * 1.030)
        + (error_rate_pct * 0.440)
        + (monthly_spend * 0.000035)
        - (daily_invocations * 0.00001)
        + (p95_latency_ms * 0.000002)
    )
    
    return max(0, min(100, round(score)))
```

**Impact of Missing Values:**

| Missing Field | Default | Impact on Score | Severity |
|--------------|---------|-----------------|----------|
| `invocation_velocity_change_pct` | 0.0 | ±0 points | Low (neutral) |
| `days_since_last_invocation` | 0 | +0 points | Low (assumes active) |
| `error_rate_pct` | 0.0 | +0 points | Low (assumes no errors) |
| `monthly_spend` | 0.0 | +0 points | Low (minimal coefficient) |
| `daily_invocations` | 0 | +0 points | Very Low (minimal coefficient) |
| `p95_latency_ms` | 0.0 | +0 points | Very Low (minimal coefficient) |

**Note:** Missing values result in **neutral impact** (0 contribution), so score defaults to base (52.14).

---

## Edge Case 3: Reference Ranges for Alerts (Not for Health Score)

### Scenario
Data center customer uses regression formula for health score calculation, but reference ranges are still needed for alerts and playbooks.

### Important Distinction

**Health Score Calculation**:
- ✅ Uses **regression formula** (does NOT use reference ranges)
- ✅ Direct calculation from KPI values
- ✅ No KPIReferenceRange lookup needed

**Alerts & Playbooks**:
- ✅ **DO use reference ranges** to detect anomalies
- ✅ Trigger playbooks based on threshold breaches
- ✅ Color-code KPIs in dashboards (healthy/risk/critical)

### Code Path

```python
def calculate_health_score_for_account(account_id: int, customer_id: int) -> int:
    """
    Calculate health score using customer-specific formula.
    """
    # Check if customer uses regression formula
    customer_config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if customer_config and customer_config.health_score_formula_type == 'regression':
        # Use regression formula (data center customer)
        # NOTE: This does NOT use reference ranges
        return calculate_data_center_health_score(
            invocation_velocity_change_pct=get_velocity_change(account_id),
            days_since_last_invocation=get_days_since_invocation(account_id),
            error_rate_pct=get_error_rate(account_id),
            monthly_spend=get_monthly_spend(account_id),
            daily_invocations=get_daily_invocations(account_id),
            p95_latency_ms=get_p95_latency(account_id)
        )
    else:
        # Use standard reference-range-based system
        from health_score_engine import HealthScoreEngine
        engine = HealthScoreEngine()
        # ... standard calculation ...
```

### Reference Ranges Still Required

Even though health score calculation doesn't use reference ranges, we still need them for:

1. **Playbook Triggers**:
   - `invocation_velocity_change_pct < -15%` → At-risk alert
   - `days_since_last_invocation > 14` → CSM escalation
   - `error_rate_pct > 5%` → Engineering escalation

2. **Dashboard Visualization**:
   - Color-code KPIs: 🟢 Healthy / 🟡 Risk / 🔴 Critical
   - Show status indicators

3. **KPI Health Status**:
   - Determine if individual KPIs are healthy/at-risk/critical
   - Used for recommendations and insights

**Key Points:**
- ✅ **Health score**: Uses regression formula (no reference ranges)
- ✅ **Alerts/Playbooks**: Use reference ranges (see `DATA_CENTER_KPI_REFERENCE_RANGES.md`)
- ✅ **Visualization**: Use reference ranges for color-coding
- ✅ **Separation of concerns**: Calculation vs. Alerting

---

## Edge Case 4: Historical Data Collection Over Time

### Scenario
New account starts with defaults, but as data accumulates, we can calculate actual values.

### Code Path

```python
def get_velocity_change(account_id: int, period: str = 'monthly') -> Optional[float]:
    """
    Calculate invocation velocity change from historical data.
    """
    # Get current period's invocations
    current_kpi = KPI.query.filter_by(
        account_id=account_id,
        kpi_parameter='invocations_30d'  # or similar
    ).order_by(KPI.upload_id.desc()).first()
    
    if not current_kpi:
        return None  # No current data
    
    # Get previous period's invocations
    previous_kpi = KPI.query.filter_by(
        account_id=account_id,
        kpi_parameter='invocations_30d'
    ).order_by(KPI.upload_id.desc()).offset(1).first()
    
    if not previous_kpi:
        return None  # No historical data yet
    
    # Calculate change
    try:
        current = float(str(current_kpi.data).replace(',', ''))
        previous = float(str(previous_kpi.data).replace(',', ''))
        
        if previous == 0:
            return None  # Division by zero
        
        change_pct = ((current - previous) / previous) * 100
        return change_pct
    except (ValueError, TypeError):
        return None

def get_days_since_invocation(account_id: int) -> Optional[int]:
    """
    Calculate days since last invocation from KPI data.
    """
    # Get most recent invocation timestamp
    last_invocation_kpi = KPI.query.filter_by(
        account_id=account_id,
        kpi_parameter='last_invocation_date'  # or similar
    ).order_by(KPI.upload_id.desc()).first()
    
    if not last_invocation_kpi:
        return None  # No data
    
    try:
        from datetime import datetime
        last_date = datetime.strptime(str(last_invocation_kpi.data), '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        return days_since
    except (ValueError, TypeError):
        return None
```

**Progressive Data Quality:**

| Time Period | Data Available | Score Quality |
|-------------|----------------|---------------|
| **Day 1** | None | Default (52) - "Insufficient Data" |
| **Week 1** | Current KPIs only | Partial (52 + current values) |
| **Month 1** | Current + some historical | Better (velocity change available) |
| **Month 2+** | Full historical | Complete (all components) |

---

## Edge Case 5: Multiple Accounts Added Simultaneously

### Scenario
Customer uploads data for 10 new accounts at once.

### Code Path

```python
def calculate_health_scores_batch(account_ids: List[int], customer_id: int) -> Dict[int, int]:
    """
    Calculate health scores for multiple accounts efficiently.
    """
    results = {}
    
    # Batch fetch all required KPIs
    kpis = KPI.query.filter(
        KPI.account_id.in_(account_ids),
        KPI.customer_id == customer_id
    ).all()
    
    # Group by account
    kpis_by_account = {}
    for kpi in kpis:
        if kpi.account_id not in kpis_by_account:
            kpis_by_account[kpi.account_id] = []
        kpis_by_account[kpi.account_id].append(kpi)
    
    # Calculate scores
    for account_id in account_ids:
        account_kpis = kpis_by_account.get(account_id, [])
        
        # Extract values
        velocity_change = extract_velocity_change(account_kpis)
        days_since = extract_days_since(account_kpis)
        error_rate = extract_error_rate(account_kpis)
        monthly_spend = extract_monthly_spend(account_kpis)
        daily_invocations = extract_daily_invocations(account_kpis)
        p95_latency = extract_p95_latency(account_kpis)
        
        # Calculate score
        score = calculate_data_center_health_score(
            invocation_velocity_change_pct=velocity_change,
            days_since_last_invocation=days_since,
            error_rate_pct=error_rate,
            monthly_spend=monthly_spend,
            daily_invocations=daily_invocations,
            p95_latency_ms=p95_latency
        )
        
        results[account_id] = score
    
    return results
```

**Performance:**
- ✅ Single database query for all KPIs
- ✅ Batch processing
- ✅ Efficient for bulk operations

---

## Implementation Strategy

### 1. **Customer Configuration**

Add to `CustomerConfig` model:
```python
class CustomerConfig(db.Model):
    # ... existing fields ...
    health_score_formula_type = db.Column(db.String(50), default='reference_range')
    # Options: 'reference_range', 'regression', 'custom'
    
    health_score_formula_config = db.Column(db.JSON)
    # For regression: stores coefficients
    # For custom: stores formula definition
```

### 2. **Health Score Calculation Router**

```python
def calculate_health_score(account_id: int, customer_id: int) -> int:
    """
    Route to appropriate health score calculation based on customer config.
    """
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if config and config.health_score_formula_type == 'regression':
        return calculate_data_center_regression_score(account_id, customer_id)
    else:
        return calculate_standard_reference_range_score(account_id, customer_id)
```

### 3. **Data Quality Tracking**

```python
def calculate_data_center_health_score(...) -> Dict:
    """
    Return score with data quality metadata.
    """
    missing_fields = []
    if invocation_velocity_change_pct is None:
        missing_fields.append('invocation_velocity_change_pct')
    if days_since_last_invocation is None:
        missing_fields.append('days_since_last_invocation')
    # ... check other fields ...
    
    # Calculate score with defaults
    score = calculate_with_defaults(...)
    
    return {
        'score': score,
        'data_quality': {
            'completeness': 1.0 - (len(missing_fields) / 6),
            'missing_fields': missing_fields,
            'is_estimated': len(missing_fields) > 0
        }
    }
```

---

## Summary

### Code Path Flow

```
New Account Added
    ↓
Check for Historical Data
    ↓
    ├─ No Historical Data → Use Defaults → Score = 52 (base)
    └─ Has Historical Data → Calculate Actual Values → Score = 52 + components
    ↓
Store Score in health_trends table
    ↓
Check Reference Ranges (for alerts/playbooks)
    ↓
    ├─ KPI in Critical Range → Trigger Playbook Alert
    ├─ KPI in Risk Range → Trigger Warning Alert
    └─ KPI in Healthy Range → No Alert
    ↓
Display in UI (with data quality indicator if estimated)
```

### Key Decisions

1. ✅ **Use default values** for missing historical data (Option A)
2. ✅ **Health score**: Uses regression formula (no reference ranges)
3. ✅ **Alerts/Playbooks**: Use reference ranges (see `DATA_CENTER_KPI_REFERENCE_RANGES.md`)
4. ✅ **Progressive enhancement** as data accumulates
5. ✅ **Data quality tracking** to show estimation status
6. ✅ **Customer-specific routing** based on config

### Related Documents

- **`DATA_CENTER_KPI_REFERENCE_RANGES.md`**: Complete reference ranges and playbook alert configurations
- **`DATA_CENTER_REGRESSION_FORMULA.md`**: Health score regression formula verification
- **`DATA_CENTER_OPTION2_MAPPING_PLAN.md`**: Initial mapping plan (superseded by regression formula)

---

**Last Updated**: January 2025  
**Status**: Ready for Implementation

