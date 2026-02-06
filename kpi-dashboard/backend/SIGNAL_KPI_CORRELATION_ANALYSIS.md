# 🔗 Signal-KPI Correlation Analysis

## Question: Where does signal correlation with KPI scores happen?

## Answer: **INSIDE Signal Analyst (via LLM), NOT before**

---

## 📊 **Current Architecture**

### **Before Signal Analyst (Signal Collection Phase)**

**Location:** `backend/agents/signal_converter.py` and `backend/agents/qdrant_integration.py`

**What Happens:**
1. **KPI → Signal Conversion:**
   ```python
   # From signal_converter.py
   payload = {
       'signal_type': 'kpi_metric',
       'pillar': kpi.category,
       'metric_type': kpi.kpi_parameter,
       'current_value': float(kpi.data),  # Raw KPI value
       'trend': 0.0,  # Default (not calculated)
       'kpi_id': kpi.kpi_id,
       'impact_level': kpi.impact_level
   }
   ```

2. **DC2SKPI → Signal Conversion:**
   ```python
   # Basic status calculation (value vs target)
   if dc_kpi.value >= dc_kpi.target:
       status = 'healthy'
   elif dc_kpi.value >= dc_kpi.target * 0.8:
       status = 'at_risk'
   else:
       status = 'critical'
   
   payload = {
       'current_value': float(dc_kpi.value),
       'target_value': float(dc_kpi.target),
       'status': status,  # Basic status, not correlation
       'weight': float(dc_kpi.weight)
   }
   ```

**Key Finding:** 
- ✅ KPI values are embedded in signals
- ✅ Basic status calculation (healthy/at_risk/critical) for DC2S
- ❌ **NO correlation analysis**
- ❌ **NO statistical correlation**
- ❌ **NO signal-to-KPI score mapping**

---

### **Inside Signal Analyst (Analysis Phase)**

**Location:** `backend/agents/signal_analyst_agent.py` and `backend/agents/prompts.py`

**What Happens:**

1. **Signal Formatting:**
   ```python
   # From prompts.py - format_quantitative_signals()
   f"Signal {i} [{pillar.upper()}]: {metric_type} = {current_value} "
   f"({trend_direction} {trend_magnitude:.1f}% trend)"
   ```

2. **LLM Prompt Instructions:**
   ```python
   # From prompts.py - get_analysis_prompt()
   """
   **CRITICAL RULES**:
   1. Base predictions ONLY on signals provided, not assumptions
   2. If signals conflict, explain the conflict and weight them appropriately
   3. Consider signal recency (recent signals matter more)
   4. Consider signal severity (critical signals override low severity)
   5. Look for patterns across quantitative + qualitative signals  # ← CORRELATION HERE
   6. External signals (funding, exec changes) can override internal signals
   """
   ```

3. **LLM Analysis:**
   - LLM receives formatted signals with KPI values
   - LLM performs correlation/pattern matching internally
   - LLM identifies which signals correlate with which outcomes
   - LLM creates `risk_drivers` and `growth_drivers` with `supporting_signals`

**Key Finding:**
- ✅ **Correlation happens INSIDE Signal Analyst via LLM**
- ✅ LLM identifies patterns and correlations
- ✅ LLM associates signals with outcomes
- ❌ **NO pre-computed correlation scores**
- ❌ **NO statistical correlation before LLM**

---

## 🔍 **Detailed Flow**

### **Step 1: Signal Collection (NO Correlation)**

```python
# signal_analyst_api.py - analyze_account()

# Collect from Qdrant
quantitative_signals = get_quantitative_signals_from_qdrant(...)
# Returns: List[SignalData] with payload containing:
#   - current_value (KPI value)
#   - metric_type (KPI name)
#   - pillar (category)
#   - NO correlation score

# Collect from Database
db_signals = convert_database_models_to_signals(...)
# Returns: Dict with quantitative_signals containing:
#   - current_value (KPI value)
#   - metric_type (KPI name)
#   - pillar (category)
#   - NO correlation score
```

**Status:** Signals have KPI values, but **NO correlation scores**

---

### **Step 2: Signal Formatting (NO Correlation)**

```python
# prompts.py - format_quantitative_signals()

# Formats signals for prompt:
"Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend)"
"Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend)"
```

**Status:** Signals formatted with values, but **NO correlation analysis**

---

### **Step 3: LLM Analysis (CORRELATION HAPPENS HERE)**

```python
# signal_analyst_agent.py - analyze()

# LLM receives:
"""
**QUANTITATIVE SIGNALS** (12 signals)
Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend)
Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend)
...

**QUALITATIVE SIGNALS** (3 signals)
Signal 1 [support_ticket]: (negative/critical) Salesforce integration broken...
Signal 2 [executive_change]: (negative/high) New CTO hired, previously used competitor...
...

**CRITICAL RULES**:
5. Look for patterns across quantitative + qualitative signals  # ← LLM does this
"""

# LLM performs correlation internally:
# - Sees: DAU declining + support ticket about integration
# - Correlates: Integration issues → Usage decline → Churn risk
# - Outputs: risk_drivers with supporting_signals
```

**Status:** **Correlation happens INSIDE LLM**

---

## 📋 **What's Missing (Pre-Correlation)**

### **What DOESN'T Exist:**

1. ❌ **Statistical Correlation Engine**
   - No Pearson correlation calculation
   - No correlation matrix between signals and KPIs
   - No pre-computed correlation scores

2. ❌ **Signal-KPI Mapping Service**
   - No explicit mapping: "Signal X correlates with KPI Y at 0.85"
   - No correlation database/table
   - No historical correlation tracking

3. ❌ **Pre-Analysis Correlation**
   - No correlation calculation before sending to Signal Analyst
   - No correlation scores in SignalData payload
   - No correlation-based signal filtering

### **What DOES Exist:**

1. ✅ **KPI Values in Signals**
   - `current_value` contains KPI data
   - `metric_type` identifies the KPI
   - `pillar` categorizes the KPI

2. ✅ **Basic Status Calculation (DC2S only)**
   - `status: 'healthy' | 'at_risk' | 'critical'`
   - Based on value vs target comparison
   - Not correlation, just threshold check

3. ✅ **LLM-Based Correlation**
   - LLM identifies patterns
   - LLM correlates signals with outcomes
   - LLM creates `supporting_signals` in risk/growth drivers

---

## 🎯 **Answer Summary**

### **Where Correlation Happens:**

| Phase | Location | Correlation Type | Status |
|-------|----------|------------------|--------|
| **Before Signal Analyst** | `signal_converter.py` | ❌ None | No correlation |
| **Before Signal Analyst** | `qdrant_integration.py` | ❌ None | No correlation |
| **Inside Signal Analyst** | `signal_analyst_agent.py` | ✅ LLM-based | **CORRELATION HAPPENS HERE** |
| **Inside Signal Analyst** | `prompts.py` | ✅ Pattern matching | Via LLM instructions |

### **Conclusion:**

**Signal correlation with KPI scores happens INSIDE Signal Analyst via the LLM**, not before.

**Current Flow:**
```
1. Collect Signals (with KPI values) → NO correlation
2. Format Signals → NO correlation  
3. Send to LLM → LLM performs correlation internally
4. LLM outputs risk_drivers with supporting_signals → Correlation results
```

**What This Means:**
- ✅ LLM does intelligent correlation/pattern matching
- ⚠️ No deterministic correlation scores
- ⚠️ No pre-computed correlation metrics
- ⚠️ Correlation is "black box" (LLM reasoning)

---

## 💡 **Implications**

### **Current State:**
- Correlation is **implicit** (done by LLM)
- Correlation is **not deterministic** (varies by LLM reasoning)
- Correlation is **not measurable** (no correlation scores)
- Correlation is **not reusable** (computed fresh each time)

### **If You Want Pre-Correlation:**

You would need to add:
1. **Correlation Engine** - Calculate statistical correlations
2. **Signal-KPI Mapping** - Map signals to KPIs with correlation scores
3. **Pre-Analysis Correlation** - Add correlation scores to SignalData payload
4. **Correlation Database** - Store historical correlations

**Example:**
```python
# Hypothetical pre-correlation
signal.correlation_scores = {
    'kpi_123': 0.85,  # Strong correlation with KPI 123
    'kpi_456': 0.62,  # Moderate correlation with KPI 456
    'health_score': 0.78  # Correlation with overall health
}
```

---

## 🔧 **Recommendation**

**Current Approach (LLM-based):**
- ✅ Flexible and intelligent
- ✅ Handles complex patterns
- ⚠️ Not deterministic
- ⚠️ No correlation scores

**If You Need Deterministic Correlation:**
- Add correlation engine before Signal Analyst
- Calculate statistical correlations
- Add correlation scores to SignalData
- Use correlations for signal filtering/weighting

**Hybrid Approach (Recommended):**
- Keep LLM correlation for complex patterns
- Add deterministic correlation for key signal-KPI pairs
- Use both in Signal Analyst analysis
