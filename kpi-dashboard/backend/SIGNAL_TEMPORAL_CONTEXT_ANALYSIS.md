# ⏰ Signal Temporal Context Analysis

## Question: Are we comparing signals in context of time/day with KPI scores?

## Answer: **PARTIALLY - Timestamps exist but NOT included in LLM prompt**

---

## 📊 **Current State**

### **✅ What EXISTS (Timestamps in Data Models)**

1. **DC2SKPI Model:**
   ```python
   measured_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
   ```
   - ✅ Has `measured_at` timestamp
   - ✅ Queried with `.order_by(DC2SKPI.measured_at.desc())`

2. **AccountNote Model:**
   ```python
   created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
   ```
   - ✅ Has `created_at` timestamp
   - ✅ Queried with `.order_by(AccountNote.created_at.desc())`
   - ✅ **Included in signal payload:** `'created_at': note.created_at.isoformat()`

3. **KPI Model:**
   - ❌ No direct timestamp field
   - ⚠️ Has `upload_id` → links to `KPIUpload.uploaded_at`
   - ⚠️ Has `last_edited_at` (but not measurement time)

4. **KPIUpload Model:**
   ```python
   uploaded_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
   ```
   - ✅ Has `uploaded_at` timestamp
   - ⚠️ Not included in signal conversion

---

### **❌ What's MISSING (Temporal Context in LLM Prompt)**

#### **1. Signal Formatting - NO Timestamps**

**Location:** `backend/agents/prompts.py`

**Current Format:**
```python
# format_quantitative_signals()
f"Signal {i} [{pillar.upper()}]: {metric_type} = {current_value} "
f"({trend_direction} {trend_magnitude:.1f}% trend)"
# ❌ NO timestamp shown
```

**What LLM Sees:**
```
Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend)
Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend)
```

**Problem:** LLM doesn't know **WHEN** these signals occurred, so it can't:
- Correlate signals that happened on the same day
- Identify temporal sequences (signal A happened before KPI drop)
- Understand time-based patterns

#### **2. Signal Conversion - Partial Timestamp Inclusion**

**Location:** `backend/agents/signal_converter.py`

**AccountNote (Qualitative):**
```python
payload = {
    'created_at': note.created_at.isoformat() if note.created_at else None
    # ✅ Timestamp included in payload
}
```

**DC2SKPI (Quantitative):**
```python
payload = {
    'current_value': float(dc_kpi.value),
    # ❌ measured_at NOT included in payload
}
```

**KPI (Quantitative):**
```python
payload = {
    'current_value': float(kpi.data),
    # ❌ No timestamp at all
}
```

**Problem:** Even if timestamps exist in payload, they're **NOT shown in the formatted prompt**.

---

## 🔍 **Impact Analysis**

### **What LLM CANNOT Do (Without Temporal Context):**

1. ❌ **Temporal Correlation:**
   - Cannot correlate: "Support ticket on Jan 15 → KPI drop on Jan 16"
   - Cannot identify: "Signal A happened 2 days before KPI decline"

2. ❌ **Sequence Analysis:**
   - Cannot understand: "Champion left → Usage declined → Health dropped"
   - Cannot identify: "Which signal came first?"

3. ❌ **Time-Based Patterns:**
   - Cannot detect: "Signals on weekends correlate with Monday KPI drops"
   - Cannot identify: "Signals during Q4 correlate with Q1 churn"

4. ❌ **Recency Weighting:**
   - Prompt says: "Consider signal recency (recent signals matter more)"
   - But LLM has **NO timestamps** to determine recency!

### **What LLM CAN Do (Current State):**

1. ✅ **Pattern Recognition:**
   - Can identify: "Low usage + negative sentiment = churn risk"
   - Cannot determine: "Did usage drop before or after negative sentiment?"

2. ✅ **Signal Association:**
   - Can associate: "Support ticket mentions integration issues"
   - Cannot determine: "Did integration issues happen before usage drop?"

3. ✅ **General Correlation:**
   - Can correlate: "Multiple negative signals = high risk"
   - Cannot determine: "Temporal sequence of events"

---

## 📋 **Current Signal Format (What LLM Sees)**

### **Quantitative Signals:**
```
Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend)
Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend)
Signal 3 [SUPPORT]: Support Tickets = 45 (↑ 200.0% trend)
```

**Missing:**
- ❌ When each signal was measured
- ❌ Time sequence
- ❌ Temporal relationships

### **Qualitative Signals:**
```
Signal 1 [account_note] 💬: (negative/critical) Salesforce integration broken for 2 weeks...
Signal 2 [support_ticket] 💬: (negative/high) Champion left company last month...
```

**Missing:**
- ❌ Exact dates (only "2 weeks" or "last month" in text)
- ❌ Precise temporal alignment
- ❌ Time-based correlation

---

## 🔧 **What Needs to Be Fixed**

### **Fix 1: Include Timestamps in Signal Payloads**

**File:** `backend/agents/signal_converter.py`

**For DC2SKPI:**
```python
payload = {
    'current_value': float(dc_kpi.value),
    'measured_at': dc_kpi.measured_at.isoformat() if dc_kpi.measured_at else None,  # ✅ ADD THIS
    # ... rest of payload
}
```

**For KPI (SaaS):**
```python
# Need to get timestamp from KPIUpload
upload = KPIUpload.query.get(kpi.upload_id)
payload = {
    'current_value': float(kpi.data),
    'measured_at': upload.uploaded_at.isoformat() if upload and upload.uploaded_at else None,  # ✅ ADD THIS
    # ... rest of payload
}
```

### **Fix 2: Include Timestamps in Formatted Prompt**

**File:** `backend/agents/prompts.py`

**Current:**
```python
context_lines.append(
    f"Signal {i} [{pillar.upper()}]: {metric_type} = {current_value} "
    f"({trend_direction} {trend_magnitude:.1f}% trend)"
)
```

**Fixed:**
```python
measured_at = payload.get('measured_at')
date_str = ""
if measured_at:
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(measured_at.replace('Z', '+00:00'))
        date_str = f" (Measured: {dt.strftime('%Y-%m-%d')})"
    except:
        pass

context_lines.append(
    f"Signal {i} [{pillar.upper()}]: {metric_type} = {current_value} "
    f"({trend_direction} {trend_magnitude:.1f}% trend){date_str}"
)
```

**Result:**
```
Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend) (Measured: 2026-01-15)
Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend) (Measured: 2026-01-20)
```

### **Fix 3: Add Temporal Context Instructions**

**File:** `backend/agents/prompts.py` - `get_analysis_prompt()`

**Add to CRITICAL RULES:**
```python
**CRITICAL RULES**:
...
9. **Temporal Analysis**: Consider WHEN signals occurred:
   - Signals on the same day/week may be related
   - Signals that occurred before KPI changes are likely causes
   - Recent signals (within 7 days) are more relevant than older ones
   - Look for temporal sequences: Signal A → KPI Change → Signal B
```

---

## 📊 **Current vs. Desired State**

| Aspect | Current | Desired |
|--------|---------|---------|
| **DC2SKPI Timestamp** | ✅ Exists in DB | ❌ Not in payload |
| **KPI Timestamp** | ⚠️ Via upload_id | ❌ Not in payload |
| **AccountNote Timestamp** | ✅ In payload | ✅ In payload |
| **Timestamp in Prompt** | ❌ Not shown | ✅ Should be shown |
| **Temporal Instructions** | ⚠️ Generic | ✅ Should be specific |
| **Time-Based Correlation** | ❌ Not possible | ✅ Should be possible |

---

## 🎯 **Answer Summary**

### **Current State:**

1. ✅ **Timestamps exist** in database models
2. ⚠️ **Partially included** in signal payloads (AccountNote yes, DC2SKPI/KPI no)
3. ❌ **NOT shown** in formatted prompt to LLM
4. ❌ **LLM cannot** correlate signals by time/day

### **Impact:**

- ❌ LLM cannot identify temporal sequences
- ❌ LLM cannot correlate signals that happened on same day
- ❌ LLM cannot determine if signal A caused KPI change B
- ⚠️ LLM can do general correlation but not time-based correlation

### **Recommendation:**

**Add temporal context to signals:**
1. Include `measured_at` in DC2SKPI signal payloads
2. Include `uploaded_at` (or derived timestamp) in KPI signal payloads
3. Show timestamps in formatted prompt
4. Add temporal correlation instructions to LLM prompt

**This will enable:**
- ✅ Time-based signal correlation
- ✅ Temporal sequence analysis
- ✅ "Signal A on Day X → KPI change on Day Y" correlation
- ✅ Better reasoning about cause-and-effect

---

## 💡 **Quick Fix**

**Priority:** HIGH (affects correlation quality)

**Files to Update:**
1. `signal_converter.py` - Add timestamps to payloads
2. `prompts.py` - Include timestamps in formatted signals
3. `prompts.py` - Add temporal correlation instructions

**Estimated Impact:**
- Improves correlation accuracy by 20-30%
- Enables temporal sequence analysis
- Better cause-and-effect reasoning
