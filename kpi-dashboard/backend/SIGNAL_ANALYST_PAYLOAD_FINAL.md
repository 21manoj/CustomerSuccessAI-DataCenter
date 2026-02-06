# ✅ Signal Analyst Payload - Final Implementation

## 🎯 **Corrected Understanding**

You're absolutely right! Signals from CSV are **already uploaded** during onboarding/runtime and stored in the `QualitativeSignal` table. We should **use what's already in the database**, not import from CSV again.

---

## ✅ **What's Implemented**

### **1. Two Primary Sources (As You Described):**

#### **Source 1: Quantitative Data (KPI-Based)**
- ✅ Account-level health score (Level 3 rollup)
- ✅ Individual KPI health scores (Level 1)
- ✅ Associated KPIs with health status
- **Source:** PostgreSQL (`kpis`, `dc2s_kpis`, `health_trends` tables)

#### **Source 2: Signals (from signals.csv format)**
- ✅ Internal signals (AccountNote table)
- ✅ **External signals (QualitativeSignal table)** - ✅ **NOW INCLUDED**
- **Source:** `AccountNote` table + `QualitativeSignal` table (loaded from CSV during onboarding)

---

### **2. Signal Collection (Updated)**

**File:** `backend/agents/signal_analyst_api.py`

**Now Collects:**
```python
# 1. Account Notes (from AccountNote table)
notes = AccountNote.query.filter_by(...).limit(20).all()

# 2. Qualitative Signals (from QualitativeSignal table - loaded from CSV)
qual_signals_from_db = QualitativeSignal.query.filter_by(
    account_id=account_id_int
).order_by(QualitativeSignal.signal_date.desc()).limit(30).all()

# 3. Convert to SignalData
qual_signal_data = convert_qualitative_signals_to_signal_data(qual_signals_from_db)

# 4. Combine with other signals
db_signals['qualitative_signals'].extend(qual_signal_data)
```

---

### **3. Deduplication**

**File:** `backend/agents/signal_deduplicator.py`

**Deduplication Keys:**
- KPIs: `kpi_id` or `(account_id, kpi_parameter)`
- Account Notes: `note_id` or `(account_id, created_at, text_hash)`
- **Qualitative Signals: `signal_id` or `(account_id, signal_type, signal_date)`** ✅ **ADDED**
- Health Score: `(account_id, week_number)`
- External Signals: `signal_id`

---

### **4. Payload Structure**

**Quantitative Signals:**
```python
[
    {
        "signal_type": "account_health_score",  # From rollup
        "overall_health_score": 75.5,
        "week_number": 4,
        "month_year": "2026-01"
    },
    {
        "signal_type": "kpi_metric",  # From KPIs
        "kpi_id": 456,
        "kpi_parameter": "Daily Active Users",
        "health_status": "Critical",
        "health_score": 12.5
    }
]
```

**Qualitative Signals:**
```python
[
    {
        "signal_type": "account_note",  # From AccountNote table
        "note_id": 789,
        "sentiment": "negative",
        "text": "Integration broken..."
    },
    {
        "signal_type": "escalation",  # From QualitativeSignal table (CSV)
        "signal_id": "1",  # ✅ Unique identifier
        "signal_source": "internal",
        "sentiment": "negative",
        "content": "Project milestone delayed...",
        "week_number": 4,
        "month_year": "2026-01"
    },
    {
        "signal_type": "meeting",  # From QualitativeSignal table (CSV)
        "signal_id": "2",
        "signal_source": "internal",
        "sentiment": "negative",
        "content": "Security compliance audit findings...",
        "week_number": 4
    }
]
```

---

## 🔄 **Data Flow (Corrected)**

```
1. Onboarding/Runtime:
   - Customer uploads signals.csv file
   - Script loads into QualitativeSignal table
   - ✅ Already in database!

2. Signal Analyst API Called:
   ↓
3. Collect Signals:
   a. From Qdrant (vector DB) - top_k=20
   b. From PostgreSQL:
      - KPIs (kpis, dc2s_kpis tables)
      - Account Notes (AccountNote table)
      - ✅ Qualitative Signals (QualitativeSignal table) - NEW!
   ↓
4. ✅ DEDUPLICATE Signals
   - Remove duplicates by kpi_id, note_id, signal_id
   - Prefer database source
   ↓
5. Build SignalAnalystInput:
   - quantitative_signals (deduplicated)
   - qualitative_signals (deduplicated, includes QualitativeSignal)
   - health_score (included)
   ↓
6. Send to LLM
   ↓
7. LLM Correlates & Returns:
   - predicted_outcome
   - churn_probability
   - risk_drivers
   - recommended_actions
```

---

## ✅ **Implementation Status**

1. ✅ **Health Score Rollup** (on KPI upload)
2. ✅ **Weekly Recalculation** (before Signal Analyst)
3. ✅ **Health Score in Payload** (as quantitative signal)
4. ✅ **Deduplication** (before sending to LLM)
5. ✅ **Temporal Grouping** (week_number, month_year in payloads)
6. ✅ **QualitativeSignal Integration** - ✅ **NOW IMPLEMENTED**

---

## 📋 **Files Modified**

1. ✅ `backend/agents/qualitative_signal_converter.py` (NEW)
2. ✅ `backend/agents/signal_analyst_api.py` (UPDATED - queries QualitativeSignal table)
3. ✅ `backend/agents/signal_deduplicator.py` (UPDATED - handles QualitativeSignal deduplication)
4. ✅ `backend/agents/signal_converter.py` (UPDATED - imports QualitativeSignal)

---

## ✅ **Summary**

**Your Understanding is CORRECT:**

1. ✅ **Two Primary Sources:**
   - Quantitative data (KPI-based health scores, associated KPIs)
   - Signals (from signals.csv format) - ✅ **NOW USING QualitativeSignal TABLE**

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
   - Uses unique identifiers (including `signal_id` from QualitativeSignal)

---

## 🎯 **Key Correction**

**Before:** Thought signals.csv needed to be imported
**After:** ✅ Signals are already in `QualitativeSignal` table (loaded during onboarding/runtime)
**Action:** ✅ Now querying `QualitativeSignal` table and including in Signal Analyst payload

**No CSV import needed - using existing database data!** ✅
