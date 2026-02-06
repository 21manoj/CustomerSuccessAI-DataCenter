# 📊 Signal Analyst Payload Summary

## ✅ **Your Questions Answered**

### **Q1: What payload goes to Signal Analyst?**

**Answer:** Two primary sources combined into unified payload:

1. **Quantitative Data (KPI-Based):**
   - Account-level health score (Level 3 rollup) - ✅ **NOW INCLUDED**
   - Individual KPI health scores (Level 1) - ✅ **INCLUDED**
   - Associated KPIs with health status - ✅ **INCLUDED**

2. **Signals (from signals.csv format):**
   - Internal signals (AccountNote table) - ✅ **INCLUDED**
   - External signals (QualitativeSignal table) - ✅ **NOW INCLUDED** (loaded from CSV during onboarding/runtime)

---

### **Q2: LLM does correlation and presents results?**

**Answer:** ✅ **YES - Correct**

**Flow:**
```
1. Collect signals from sources
2. Deduplicate signals (✅ NOW IMPLEMENTED)
3. Send to LLM with temporal grouping
4. LLM correlates:
   - Quantitative signals (KPIs, health scores)
   - Qualitative signals (notes, tickets)
   - Temporal context (week/month grouping)
5. LLM returns:
   - predicted_outcome (churn/expansion/stable)
   - churn_probability (0-100%)
   - risk_drivers (list)
   - recommended_actions (list)
```

---

### **Q3: Decision is made which action to take next?**

**Answer:** ⚠️ **PARTIALLY IMPLEMENTED**

**Current State:**
- ✅ Signal Analyst returns predictions and recommendations
- ⚠️ **Decision logic NOT YET IMPLEMENTED** (playbook trigger vs follow-up call)

**What Exists:**
- `playbook_recommendations_api.py` has playbook evaluation functions
- But no integration with Signal Analyst output

**What's Needed:**
- Decision engine that takes Signal Analyst output
- Decides: Playbook trigger OR Follow-up call
- Based on: churn_probability, health_score, risk_drivers

---

### **Q4: Ensure no duplicate data goes to LLM?**

**Answer:** ✅ **NOW IMPLEMENTED**

**Implementation:**
- ✅ Created `signal_deduplicator.py` with deduplication logic
- ✅ Applied deduplication before sending to LLM
- ✅ Uses unique identifiers (`kpi_id`, `note_id`, `signal_id`)
- ✅ Prefers database source (exact data, no embedding loss)

**Deduplication Keys:**
- KPIs: `kpi_id` or `(account_id, kpi_parameter)`
- Notes: `note_id` or `(account_id, created_at, text_hash)`
- Health Score: `(account_id, week_number)` or `(account_id, calculated_at)`
- External Signals: `signal_id` or `(account_id, event_type, date)`

---

## 📋 **Current Payload Structure**

### **Quantitative Signals:**

```python
[
    {
        "signal_type": "account_health_score",  # ✅ From rollup
        "overall_health_score": 75.5,
        "week_number": 4,
        "month_year": "2026-01",
        "source": "health_score_rollup"
    },
    {
        "signal_type": "kpi_metric",  # ✅ From KPIs
        "kpi_id": 456,  # ✅ Unique identifier
        "kpi_parameter": "Daily Active Users",
        "current_value": 1250,
        "health_status": "Critical",
        "health_score": 12.5,
        "week_number": 4,
        "source": "postgresql"
    }
]
```

### **Qualitative Signals:**

```python
[
    {
        "signal_type": "account_note",  # ✅ From AccountNote table
        "note_id": 789,  # ✅ Unique identifier
        "sentiment": "negative",
        "severity": "high",
        "text": "Integration broken...",
        "week_number": 4,
        "source": "postgresql"
    }
]
```

---

## 🔄 **Data Flow (Current Implementation)**

```
1. Signal Analyst API Called
   ↓
2. Get/Calculate Health Score (with weekly recalculation check)
   ↓
3. Collect Signals:
   a. From Qdrant (vector DB) - top_k=20
   b. From PostgreSQL (raw DB) - limit(50)
   ↓
4. ✅ DEDUPLICATE Signals (NEW!)
   - Remove duplicates by kpi_id, note_id, signal_id
   - Prefer database source (exact data)
   ↓
5. Build SignalAnalystInput:
   - quantitative_signals (deduplicated)
   - qualitative_signals (deduplicated)
   - health_score (included)
   ↓
6. Send to LLM
   ↓
7. LLM Correlates & Returns:
   - predicted_outcome
   - churn_probability
   - risk_drivers
   - recommended_actions
   ↓
8. ⚠️ Decision Engine (NOT YET IMPLEMENTED):
   - If churn_prob > 70% AND health < 50:
     → Trigger playbook
   - If churn_prob 40-70%:
     → Follow-up call
   - If expansion_prob > 60%:
     → Trigger expansion playbook
```

---

## ✅ **What's Implemented**

1. ✅ **Health Score Rollup** (on KPI upload)
2. ✅ **Weekly Recalculation** (before Signal Analyst)
3. ✅ **Health Score in Payload** (as quantitative signal)
4. ✅ **Deduplication** (before sending to LLM)
5. ✅ **Temporal Grouping** (week_number, month_year in payloads)

---

## ⚠️ **What's Missing**

1. ✅ **QualitativeSignal Integration** - ✅ **NOW IMPLEMENTED** (using existing DB data)
2. ⚠️ **Decision Engine** (playbook trigger vs follow-up call logic)

---

## 🎯 **Recommendations**

### **Priority 1: Signals.csv Import (HIGH)**

**Need to implement:**
- CSV parser for signals.csv format
- Store in `QualitativeSignal` table or new `ExternalSignal` table
- Convert to SignalData format for Signal Analyst

**CSV Format (from examples):**
```csv
signal_id,account_id,signal_date,signal_type,sentiment,content
1,120001,2024-01-10,escalation,negative,Project milestone delayed...
2,120001,2024-01-27,meeting,negative,Security compliance audit...
```

### **Priority 2: Decision Engine (HIGH)**

**Need to implement:**
- Function that takes Signal Analyst output
- Decides: Playbook trigger OR Follow-up call
- Based on thresholds (churn_prob, health_score, etc.)

### **Priority 3: External Signals Integration (MEDIUM)**

**Need to implement:**
- Import signals.csv files
- Convert to SignalData format
- Include in Signal Analyst payload

---

## ✅ **Summary**

**Your Understanding is CORRECT:**

1. ✅ **Two Primary Sources:**
   - Quantitative data (KPI-based health scores, associated KPIs)
   - Signals (from signals.csv format) - ⚠️ CSV exists but not yet imported

2. ✅ **LLM Does Correlation:**
   - Receives deduplicated signals
   - Correlates quantitative + qualitative
   - Considers temporal grouping
   - Returns predictions and recommendations

3. ⚠️ **Decision Making:**
   - Signal Analyst output exists
   - Decision logic NOT YET IMPLEMENTED
   - Would decide: Playbook trigger OR Follow-up call

4. ✅ **No Duplicate Data:**
   - Deduplication IMPLEMENTED
   - Applied before sending to LLM
   - Uses unique identifiers

---

## 🚀 **Next Steps**

1. ✅ **Deduplication** - DONE
2. ⚠️ **Signals.csv Import** - NEEDS IMPLEMENTATION
3. ⚠️ **Decision Engine** - NEEDS IMPLEMENTATION
