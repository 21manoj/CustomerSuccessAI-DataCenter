# 🔍 Health Status Calculation Analysis
## Where "At-Risk", "Healthy", "Critical" States Come From

## 🎯 **Answer to Your Question**

**Q: Which quantitative data tells me about "at-risk", "healthy", or "critical" state before it gets to LLM with time grouping? Is this all coming from SQL statements/DB? How often is this calculated?**

**A:**
1. ✅ **Source**: Calculated on-demand using **SQL queries** to `kpi_reference_ranges` table
2. ✅ **Method**: Compares KPI values against reference ranges (Critical/Risk/Healthy thresholds)
3. ⚠️ **Frequency**: **On-demand** (not pre-calculated), triggered by:
   - API calls (`/api/health-status/kpis`)
   - Health score calculations (after KPI upload)
   - Health trend generation
4. ⚠️ **Storage**: **NOT persistently stored** for most KPIs (calculated on-the-fly)
   - Exception: `KPITimeSeries` table stores `health_status` when time series records are created

---

## 📊 **Data Flow: How Health Status is Determined**

### **Step 1: Reference Ranges (Stored in DB)**

**Table:** `kpi_reference_ranges`

**SQL Query:**
```sql
SELECT 
    kpi_name,
    critical_min, critical_max,  -- Critical range (red)
    risk_min, risk_max,          -- At-Risk range (yellow)
    healthy_min, healthy_max,    -- Healthy range (green)
    higher_is_better,            -- Direction (↑ or ↓)
    unit                         -- Unit (days, hours, $, %, etc.)
FROM kpi_reference_ranges
WHERE kpi_name = ? 
  AND (customer_id = ? OR customer_id IS NULL)  -- Customer-specific or system default
ORDER BY customer_id DESC  -- Customer-specific takes precedence
LIMIT 1;
```

**Example Data:**
```python
{
    'kpi_name': 'Time to First Value (TTFV)',
    'critical_min': 0,
    'critical_max': 7,      # 0-7 days = Critical (red)
    'risk_min': 7,
    'risk_max': 14,         # 7-14 days = At-Risk (yellow)
    'healthy_min': 14,
    'healthy_max': 999999,  # 14+ days = Healthy (green)
    'higher_is_better': False,  # Lower is better
    'unit': 'days'
}
```

---

### **Step 2: KPI Value Retrieval (From DB)**

**Table:** `kpis` (or `dc2s_kpis` for DC2_S)

**SQL Query:**
```sql
SELECT 
    kpi_id,
    account_id,
    kpi_parameter,  -- KPI name
    data,           -- Raw value (e.g., "21 hours", "$50K", "85%")
    measured_at     -- Timestamp (for DC2S)
FROM kpis
WHERE account_id = ?
  AND kpi_parameter = ?;
```

**Example Data:**
```python
{
    'kpi_id': 12345,
    'account_id': 10001,
    'kpi_parameter': 'Time to First Value (TTFV)',
    'data': '21 hours',  # Raw value
    'measured_at': '2026-01-15 10:30:00'  # For DC2S
}
```

---

### **Step 3: Value Parsing & Normalization**

**Function:** `HealthScoreEngine.parse_kpi_value(data_str, kpi_name)`

**Process:**
1. Parse raw value: `"21 hours"` → `21.0` (float)
2. Unit conversion: If reference range expects `days`, convert `21 hours` → `0.875 days`
3. Handle currency: `"$50K"` → `50000.0`
4. Handle percentages: `"85%"` → `85.0`

**Code Location:** `backend/health_score_engine.py:53-152`

---

### **Step 4: Health Status Calculation**

**Function:** `HealthScoreEngine.calculate_health_status(value, kpi_name)`

**Process:**
1. **Get reference range** from DB (Step 1)
2. **Compare value** against ranges:
   - If `higher_is_better = True`:
     - `value` in `[critical_min, critical_max]` → **'low'** → **'Critical'**
     - `value` in `[risk_min, risk_max]` → **'medium'** → **'At-Risk'**
     - `value` in `[healthy_min, healthy_max]` → **'high'** → **'Healthy'**
   - If `higher_is_better = False` (lower is better):
     - `value` in `[critical_min, critical_max]` → **'high'** → **'Critical'** (reversed!)
     - `value` in `[risk_min, risk_max]` → **'medium'** → **'At-Risk'**
     - `value` in `[healthy_min, healthy_max]` → **'low'** → **'Healthy'** (reversed!)
3. **Calculate score** (0-100) based on position within range
4. **Return status** with color mapping

**Code Location:** `backend/health_score_engine.py:155-249`

**Example:**
```python
# Input: value = 0.875 days, kpi_name = 'Time to First Value (TTFV)'
# Reference range: critical=[0,7], risk=[7,14], healthy=[14,999999]
# higher_is_better = False (lower is better)

# 0.875 is in critical range [0,7]
# Since lower is better, critical = 'high' status
# Result: status = 'high' → mapped to 'Critical' (red)
```

---

### **Step 5: Status Mapping**

**Mapping (in `health_status_api.py`):**
```python
status_mapping = {
    'low': 'Critical',      # 🔴 Red
    'medium': 'Risk',        # 🟡 Yellow (At-Risk)
    'high': 'Healthy',       # 🟢 Green
    'unknown': 'Unknown'     # ⚪ Gray
}
```

**Note:** The mapping is **counter-intuitive** because:
- For "higher is better" KPIs: `low` value = `Critical`
- For "lower is better" KPIs: `high` value = `Critical` (reversed logic)

---

## 🔄 **When is Health Status Calculated?**

### **1. On-Demand API Calls** ⚡

**Endpoint:** `GET /api/health-status/kpis`

**Trigger:** User requests health status for KPIs

**Frequency:** **Every API call** (real-time)

**Code Location:** `backend/health_status_api.py:16-80`

**Flow:**
```
User Request → Query KPIs from DB → Calculate health_status for each → Return JSON
```

**Example:**
```python
# GET /api/health-status/kpis?account_id=10001
# Returns:
[
    {
        "kpi_id": 12345,
        "kpi_parameter": "Time to First Value (TTFV)",
        "data": "21 hours",
        "health_status": "Critical",  # ✅ Calculated on-the-fly
        "health_score": 12.5,
        "health_color": "red",
        "reference_range": "0-999999 days"
    }
]
```

---

### **2. Health Score Calculation** 📊

**Trigger:** After KPI upload or health trend calculation

**Frequency:** **After each KPI upload** or **manual health score calculation**

**Code Location:** `backend/health_score_storage.py:154-218`

**Flow:**
```
KPI Upload → Parse KPIs → Calculate health_status → Calculate category scores → Calculate overall health
```

**Example:**
```python
# In _calculate_account_health_scores():
for kpi in account_kpis:
    parsed_value = self.health_engine.parse_kpi_value(kpi.data, kpi.kpi_parameter)
    health_info = self.health_engine.calculate_health_status(parsed_value, kpi.kpi_parameter)
    # health_info = {'status': 'low', 'score': 12.5, 'color': 'red', ...}
```

---

### **3. Health Trend Generation** 📈

**Trigger:** When creating `HealthTrend` or `KPITimeSeries` records

**Frequency:** **Monthly** (when time series records are created)

**Code Location:** `backend/health_trend_api.py`

**Storage:** `KPITimeSeries.health_status` column (persistently stored)

**SQL:**
```sql
INSERT INTO kpi_time_series (
    kpi_id, account_id, month, year, value,
    health_status,  -- ✅ Stored here!
    health_score
) VALUES (?, ?, ?, ?, ?, ?, ?);
```

**Note:** This is the **ONLY place** where health status is persistently stored.

---

### **4. Signal Analyst (Before LLM)** 🤖

**Trigger:** When Signal Analyst collects signals

**Frequency:** **Every Signal Analyst API call**

**Code Location:** `backend/agents/signal_converter.py`

**Process:**
```python
# When converting KPIs to signals:
dc_kpi = DC2SKPI.query.get(kpi_id)
parsed_value = parse_kpi_value(dc_kpi.value, dc_kpi.kpi_code)
health_info = calculate_health_status(parsed_value, dc_kpi.kpi_code)

# Include in signal payload:
signal_payload = {
    'current_value': parsed_value,
    'health_status': health_info['status'],  # 'low', 'medium', 'high'
    'health_score': health_info['score'],    # 0-100
    'health_color': health_info['color'],    # 'red', 'yellow', 'green'
    # ... time period grouping (week_number, month_year)
}
```

**This is where health status reaches the LLM!**

---

## 💾 **Storage: Where is Health Status Stored?**

### **Persistently Stored:**

1. **`kpi_time_series` table:**
   - Column: `health_status` (VARCHAR(20))
   - Values: `'Healthy'`, `'Risk'`, `'Critical'`
   - **When:** Created when time series records are generated (monthly)
   - **Query:**
     ```sql
     SELECT health_status FROM kpi_time_series 
     WHERE account_id = ? AND month = ? AND year = ?;
     ```

### **NOT Stored (Calculated On-Demand):**

1. **`kpis` table:**
   - ❌ **No `health_status` column**
   - ✅ Calculated on-the-fly when needed

2. **`dc2s_kpis` table:**
   - ❌ **No `health_status` column**
   - ✅ Calculated on-the-fly when needed

3. **`health_trends` table:**
   - ❌ **No `health_status` column** (only overall health score)
   - ✅ Individual KPI statuses calculated on-demand

---

## 🔍 **SQL Queries Used**

### **Query 1: Get Reference Range**

```sql
-- From: health_score_engine.py:17-50
SELECT 
    range_id,
    kpi_name,
    unit,
    higher_is_better,
    critical_min, critical_max,
    risk_min, risk_max,
    healthy_min, healthy_max,
    description
FROM kpi_reference_ranges
WHERE kpi_name = ?
  AND (customer_id = ? OR customer_id IS NULL)
ORDER BY customer_id DESC NULLS LAST  -- Customer-specific first
LIMIT 1;
```

### **Query 2: Get KPI Values**

```sql
-- For SaaS KPIs:
SELECT 
    kpi_id, account_id, kpi_parameter, data,
    upload_id
FROM kpis
WHERE account_id = ?
  AND kpi_parameter = ?;

-- For DC2S KPIs:
SELECT 
    kpi_id, account_id, kpi_code, value,
    measured_at  -- ✅ Has timestamp!
FROM dc2s_kpis
WHERE account_id = ?
  AND kpi_code = ?;
```

### **Query 3: Get Stored Health Status (Time Series Only)**

```sql
-- Only for time series data:
SELECT 
    kpi_id, account_id, month, year,
    value, health_status, health_score
FROM kpi_time_series
WHERE account_id = ?
  AND month = ?
  AND year = ?;
```

---

## ⏱️ **Calculation Frequency Summary**

| **Trigger** | **Frequency** | **Storage** | **Location** |
|------------|---------------|-------------|--------------|
| **API Call** (`/api/health-status/kpis`) | Every request | ❌ Not stored | `health_status_api.py` |
| **KPI Upload** | After each upload | ❌ Not stored | `health_score_storage.py` |
| **Health Score Calculation** | On-demand/manual | ❌ Not stored | `health_score_storage.py` |
| **Time Series Creation** | Monthly | ✅ Stored in `kpi_time_series` | `health_trend_api.py` |
| **Signal Analyst** | Every analysis | ❌ Not stored (in payload only) | `signal_converter.py` |

---

## 🎯 **Key Insights**

### **1. Mostly On-Demand Calculation**

- ✅ Health status is **calculated on-the-fly** using SQL queries
- ❌ **NOT pre-calculated** and stored (except time series)
- ⚡ **Real-time** - always uses latest KPI values and reference ranges

### **2. SQL-Based (Not Python-Only)**

- ✅ Uses **SQL queries** to `kpi_reference_ranges` table
- ✅ Uses **SQL queries** to `kpis` / `dc2s_kpis` tables
- ✅ Calculation logic in Python, but data comes from DB

### **3. Reference Ranges are Customer-Specific**

- ✅ Customer-specific ranges override system defaults
- ✅ Query prioritizes: `customer_id = X` → `customer_id = NULL`
- ✅ Allows customization per customer

### **4. Time Series is Exception**

- ✅ `KPITimeSeries.health_status` is **persistently stored**
- ✅ Created monthly when time series records are generated
- ✅ Can be queried directly: `SELECT health_status FROM kpi_time_series WHERE ...`

---

## 🔧 **For Signal Analyst with Time Grouping**

### **Current Flow:**

```
1. Signal Analyst API called
2. Collect KPIs from DB (with measured_at timestamps)
3. For each KPI:
   a. Parse value (parse_kpi_value)
   b. Calculate health_status (calculate_health_status) ← SQL query to reference_ranges
   c. Add time periods (week_number, month_year)
4. Group signals by week/month
5. Format for LLM with health_status included
```

### **What LLM Sees:**

```
**QUANTITATIVE SIGNALS BY WEEK:**

Week 5, 2026:
  Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250
    Health Status: Critical (red)  ← ✅ From SQL calculation
    Health Score: 12.5/100
    Reference Range: 0-956 (Critical)

Week 6, 2026:
  Signal 2 [SUPPORT]: Support Tickets = 45
    Health Status: At-Risk (yellow)  ← ✅ From SQL calculation
    Health Score: 55.0/100
    Reference Range: 10-30 (At-Risk)
```

---

## ✅ **Summary**

1. **Source**: SQL queries to `kpi_reference_ranges` + `kpis`/`dc2s_kpis` tables
2. **Calculation**: On-demand Python function (`calculate_health_status`)
3. **Frequency**: 
   - ⚡ **Real-time** for API calls
   - 📊 **After KPI uploads**
   - 📈 **Monthly** for time series (stored)
4. **Storage**: Mostly **NOT stored** (calculated on-the-fly), except `kpi_time_series.health_status`
5. **For LLM**: Health status is calculated **before** time grouping, then included in signal payloads

---

## 🚀 **Recommendation**

**For better performance and consistency:**

1. ✅ **Keep on-demand calculation** (ensures latest reference ranges)
2. ✅ **Add caching** for frequently accessed KPIs
3. ✅ **Consider pre-calculating** health_status when KPIs are uploaded (store in `kpis` table)
4. ✅ **Include health_status in signal payloads** (already done in `signal_converter.py`)

**Current implementation is correct** - on-demand calculation ensures:
- Latest reference ranges are used
- Customer-specific overrides are respected
- No stale data issues
