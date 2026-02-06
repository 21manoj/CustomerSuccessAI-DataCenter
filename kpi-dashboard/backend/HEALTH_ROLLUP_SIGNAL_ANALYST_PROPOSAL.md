# 🎯 Health Score Rollup & Signal Analyst Integration Proposal

## Question: Should we execute Level 1/2/3 rollups periodically BEFORE calling Signal Analyst?

---

## 📊 **Current Reality**

### **Level 1, 2, 3 Rollup Hierarchy**

**Level 1: KPI-Level Health Scores**
- Individual KPI values → Health status (Critical/At-Risk/Healthy)
- Score: 0-100 based on reference ranges
- Impact weight: High (3x), Medium (2x), Low (1x)

**Level 2: Category-Level Health Scores**
- Groups of KPIs by category (Product Usage, Support, etc.)
- Normalized average: `sum(weighted_scores) / sum(impact_weights)`
- Ensures categories with more KPIs don't get inflated scores

**Level 3: Overall Account Health Score**
- Weighted average of normalized category scores
- Category weights: Product Usage (30%), Support (20%), etc.
- Final score: 0-100 representing overall account health

**Code Location:**
- `health_score_engine.py`: `calculate_kpi_health_score()`, `calculate_category_health_score()`, `calculate_overall_health_score()`
- `corporate_api.py`: `/api/corporate/rollup` endpoint

---

### **Current Calculation Frequency**

| **Trigger** | **Frequency** | **Stored?** | **Location** |
|------------|---------------|-------------|--------------|
| **API Call** (`/api/corporate/rollup`) | On-demand | ✅ Yes (in `health_trends` table) | `corporate_api.py:178` |
| **After KPI Upload** | After each upload | ⚠️ Not automatically | Manual trigger needed |
| **Health Trend API** | On-demand/manual | ✅ Yes (in `health_trends` table) | `health_trend_api.py` |
| **Signal Analyst** | Every analysis | ❌ **NOT calculated** | Missing! |

---

### **Current Signal Analyst Behavior**

**What Signal Analyst Currently Collects:**

1. ✅ **Quantitative Signals** (from Qdrant/DB):
   - Individual KPI values
   - KPI health status (Critical/At-Risk/Healthy)
   - KPI health scores (0-100)

2. ✅ **Qualitative Signals** (from Qdrant/DB):
   - Account notes
   - Support tickets
   - Sentiment analysis

3. ❌ **Missing: Account-Level Health Score**
   - **NOT included** as a signal
   - **NOT calculated** before Signal Analyst runs
   - LLM doesn't see overall account health context

**Code Evidence:**
- `signal_analyst_api.py:129-200`: Collects KPIs and notes, but **no health score**
- `signal_converter.py`: Converts KPIs to signals, but **no overall health score**
- `models.py:SignalAnalystInput`: Has `health_score` field, but it's **not populated**

---

## 🎯 **Proposal: Pre-Calculate Rollups Before Signal Analyst**

### **Why This Matters**

1. **Account Health Score is a Critical Signal**
   - Represents aggregated view of all KPIs
   - Shows overall account trajectory
   - Better aligned with customer's view of account health

2. **Temporal Context**
   - Health score changes over time (week/month)
   - LLM can correlate: "Health score dropped from 75 → 55 in Week 5"
   - Enables pattern recognition: "Health decline → Support spike → Churn risk"

3. **Consistency**
   - Pre-calculated scores ensure consistency across analyses
   - Avoids recalculating on every Signal Analyst call
   - Uses same methodology as dashboard/rollup

---

## ✅ **Recommended Implementation**

### **Option 1: Pre-Calculate on KPI Upload (Recommended)**

**Trigger:** After KPI upload completes

**Flow:**
```
1. KPI Upload → KPIs saved to DB
2. Event: KPI_DATA_UPLOADED published
3. Health Score Rollup Subscriber:
   a. Calculate Level 1 (KPI health scores)
   b. Calculate Level 2 (Category health scores)
   c. Calculate Level 3 (Overall account health score)
   d. Store in health_trends table
4. Event: HEALTH_SCORES_UPDATED published
5. Signal Analyst can now use pre-calculated health scores
```

**Code Location:** `backend/event_system.py` → New subscriber

**Benefits:**
- ✅ Health scores always up-to-date
- ✅ No delay when Signal Analyst runs
- ✅ Consistent with dashboard calculations

---

### **Option 2: Pre-Calculate Before Signal Analyst (Fallback)**

**Trigger:** Before Signal Analyst API call

**Flow:**
```
1. Signal Analyst API called
2. Check if health_trends has recent health score
3. If missing or stale (> 1 hour old):
   a. Calculate rollup on-the-fly
   b. Store in health_trends
4. Include health score in SignalAnalystInput
5. Continue with analysis
```

**Code Location:** `backend/agents/signal_analyst_api.py:32-130`

**Benefits:**
- ✅ Ensures health score exists when needed
- ✅ No separate background job required
- ⚠️ Adds latency to Signal Analyst API call

---

### **Option 3: Scheduled Periodic Calculation**

**Trigger:** Scheduled job (daily/weekly)

**Flow:**
```
1. Cron job runs daily at 2 AM
2. For each account:
   a. Calculate health score rollup
   b. Store in health_trends
3. Signal Analyst uses pre-calculated scores
```

**Code Location:** New scheduled job script

**Benefits:**
- ✅ Predictable calculation schedule
- ✅ Can run during low-traffic hours
- ⚠️ May be stale if KPIs updated between runs

---

## 🔧 **Implementation Details**

### **Step 1: Add Health Score to Signal Analyst Input**

**File:** `backend/agents/signal_analyst_api.py`

**Current Code:**
```python
# Collect signals
quantitative_signals = []
qualitative_signals = []
historical_patterns = []

# ... collect KPIs and notes ...

# Build SignalAnalystInput
input_data = SignalAnalystInput(
    account_id=account_id,
    account_name=account.account_name,
    quantitative_signals=quantitative_signals,
    qualitative_signals=qualitative_signals,
    historical_patterns=historical_patterns,
    # ❌ health_score is missing!
)
```

**Proposed Code:**
```python
# Get or calculate health score
from models import HealthTrend
from health_score_storage import HealthScoreStorageService

# Check if recent health score exists
health_trend = HealthTrend.query.filter_by(
    account_id=account_id_int,
    customer_id=customer_id
).order_by(HealthTrend.created_at.desc()).first()

if health_trend and health_trend.overall_health_score:
    overall_health_score = float(health_trend.overall_health_score)
    health_score_age_hours = (datetime.utcnow() - health_trend.created_at).total_seconds() / 3600
    
    # Use existing if < 1 hour old
    if health_score_age_hours < 1:
        logger.info(f"Using existing health score: {overall_health_score} (age: {health_score_age_hours:.1f}h)")
    else:
        # Recalculate if stale
        logger.info(f"Health score stale ({health_score_age_hours:.1f}h), recalculating...")
        storage_service = HealthScoreStorageService()
        health_scores = storage_service._calculate_account_health_scores(account, customer_id)
        overall_health_score = health_scores.get('overall', 0)
        
        # Store updated health score
        # ... (store in health_trends)
else:
    # Calculate if missing
    logger.info("No health score found, calculating...")
    storage_service = HealthScoreStorageService()
    health_scores = storage_service._calculate_account_health_scores(account, customer_id)
    overall_health_score = health_scores.get('overall', 0)

# Build SignalAnalystInput
input_data = SignalAnalystInput(
    account_id=account_id,
    account_name=account.account_name,
    health_score=overall_health_score,  # ✅ Now included!
    quantitative_signals=quantitative_signals,
    qualitative_signals=qualitative_signals,
    historical_patterns=historical_patterns,
)
```

---

### **Step 2: Include Health Score in Signal Payload**

**File:** `backend/agents/signal_converter.py`

**Add health score context to signals:**
```python
def convert_database_models_to_signals(
    kpis=None, 
    dc_kpis=None, 
    notes=None,
    account_health_score=None  # ✅ New parameter
):
    """Convert database models to SignalData objects"""
    signals = []
    
    # ... existing KPI conversion ...
    
    # Add account health score as a quantitative signal
    if account_health_score is not None:
        health_signal = SignalData(
            signal_id=f"health_score_{account_id}",
            signal_type="account_health",
            source="health_score_rollup",
            payload={
                'signal_type': 'account_health_score',
                'overall_health_score': account_health_score,
                'health_status': get_health_status_from_score(account_health_score),
                'health_color': get_health_color_from_score(account_health_score),
                'calculated_at': datetime.utcnow().isoformat(),
                # ... time period grouping (week_number, month_year)
            },
            similarity=1.0  # Always include
        )
        signals.append(health_signal)
    
    return signals
```

---

### **Step 3: Add Health Score to Prompt**

**File:** `backend/agents/prompts.py`

**Update prompt to include health score:**
```python
def get_analysis_prompt(input_data: SignalAnalystInput) -> str:
    """Generate analysis prompt with health score context"""
    
    prompt = f"""
## Account Context

**Account:** {input_data.account_name} (ID: {input_data.account_id})
**Overall Health Score:** {input_data.health_score}/100 ({get_health_status(input_data.health_score)})
**Analysis Type:** {input_data.analysis_type}
**Time Horizon:** {input_data.time_horizon_days} days

## Signals Analysis

{format_quantitative_signals(input_data.quantitative_signals)}
{format_qualitative_signals(input_data.qualitative_signals)}

## CRITICAL RULES

1. **Account Health Context:**
   - Overall health score: {input_data.health_score}/100
   - Health status: {get_health_status(input_data.health_score)}
   - Use this as primary context for all predictions
   - Health score < 50 = High churn risk
   - Health score 50-70 = At-risk, monitor closely
   - Health score > 70 = Healthy, focus on expansion

2. **Temporal Correlation:**
   - Correlate health score changes with signal timing
   - If health score dropped in Week 5, look for signals in Week 4-5
   - Multiple signals in same week/month are likely correlated

...
```

---

## 📊 **Comparison: Current vs. Proposed**

### **Current Flow:**
```
Signal Analyst API Called
  ↓
Collect KPIs from DB
  ↓
Collect Notes from DB
  ↓
Convert to signals (individual KPIs only)
  ↓
Send to LLM (no overall health context)
  ↓
LLM infers account health from individual KPIs
```

**Problem:** LLM must infer overall health from individual KPIs (inconsistent, error-prone)

---

### **Proposed Flow:**
```
KPI Upload
  ↓
Calculate Level 1/2/3 Rollup
  ↓
Store in health_trends table
  ↓
Signal Analyst API Called
  ↓
Get pre-calculated health score
  ↓
Collect KPIs + Notes
  ↓
Include health score as signal
  ↓
Send to LLM (with overall health context)
  ↓
LLM uses health score + individual KPIs for analysis
```

**Benefit:** LLM has explicit account health context (consistent, accurate)

---

## 🎯 **Recommendation**

### **✅ Implement Option 1 + Option 2 (Hybrid)**

1. **Primary:** Pre-calculate on KPI upload (Option 1)
   - Health scores always up-to-date
   - No delay for Signal Analyst

2. **Fallback:** Calculate if missing (Option 2)
   - Ensures health score exists even if upload didn't trigger calculation
   - Handles edge cases

3. **Include in Signal Analyst:**
   - Add health score to `SignalAnalystInput`
   - Include in signal payloads
   - Update prompt to use health score context

---

## 📋 **Implementation Checklist**

- [ ] **Step 1:** Create `HealthScoreRollupSubscriber` in `event_system.py`
  - Subscribe to `KPI_DATA_UPLOADED` event
  - Calculate Level 1/2/3 rollup
  - Store in `health_trends` table
  - Publish `HEALTH_SCORES_UPDATED` event

- [ ] **Step 2:** Update `signal_analyst_api.py`
  - Get or calculate health score before analysis
  - Include in `SignalAnalystInput`

- [ ] **Step 3:** Update `signal_converter.py`
  - Add health score as quantitative signal
  - Include time period grouping (week_number, month_year)

- [ ] **Step 4:** Update `prompts.py`
  - Include health score in prompt context
  - Add health score correlation instructions

- [ ] **Step 5:** Test
  - Verify health score calculated on KPI upload
  - Verify health score included in Signal Analyst
  - Verify LLM uses health score in analysis

---

## ⏱️ **Timeline Estimate**

- **Step 1:** 2-3 hours (Event subscriber)
- **Step 2:** 1-2 hours (Signal Analyst integration)
- **Step 3:** 1 hour (Signal converter)
- **Step 4:** 1 hour (Prompt update)
- **Step 5:** 2-3 hours (Testing)

**Total:** ~8-10 hours

---

## 🎯 **Expected Benefits**

1. ✅ **Better Signal Alignment**
   - Account health score is a "signal from customer" (aggregated view)
   - LLM sees overall health context, not just individual KPIs

2. ✅ **Improved Predictions**
   - Health score provides primary context for churn/expansion predictions
   - LLM can correlate: "Health 75 → 55 = High churn risk"

3. ✅ **Temporal Correlation**
   - Health score changes over time (week/month)
   - LLM can correlate health trends with signals

4. ✅ **Consistency**
   - Same health score used in dashboard and Signal Analyst
   - No discrepancies between views

---

## ✅ **Conclusion**

**YES, we should execute Level 1/2/3 rollups periodically BEFORE calling Signal Analyst.**

**Account-level health score SHOULD be a "signal from customer"** because:
- It represents the customer's aggregated view of account health
- It's better aligned than individual KPIs
- It provides temporal context (health trends over time)
- It enables better correlation and pattern recognition

**Recommended Approach:**
- Pre-calculate on KPI upload (primary)
- Calculate if missing before Signal Analyst (fallback)
- Include health score in Signal Analyst input and prompts
