# 📊 Signal Analyst Payload Architecture & Deduplication Strategy

## 🎯 **Your Questions Answered**

### **Q1: What payload goes to Signal Analyst?**

**Answer:** Two primary data sources are combined into a unified payload:

1. **Quantitative Data:**
   - KPI-based health scores (individual KPIs with health status)
   - Account-level health score (Level 3 rollup)
   - Associated KPIs (from `kpis` or `dc2s_kpis` tables)

2. **Signals (from signals.csv format):**
   - External signals (funding, exec changes, market events)
   - Internal signals (support tickets, account notes, sentiment)
   - Qualitative signals (notes, emails, conversations)

---

## 📋 **Current Payload Structure**

### **SignalAnalystInput Model:**

```python
{
    "account_id": "123",
    "customer_id": 120,
    "vertical_type": "saas_customer_success",
    "account_name": "Acme Corp",
    "account_arr": 500000.0,
    "health_score": 75.5,  # ✅ Overall account health (Level 3 rollup)
    
    "quantitative_signals": [
        {
            "similarity": 0.95,
            "payload": {
                "signal_type": "account_health_score",  # ✅ From rollup
                "overall_health_score": 75.5,
                "health_status": "high",
                "week_number": 4,
                "month_year": "2026-01",
                ...
            }
        },
        {
            "similarity": 0.85,
            "payload": {
                "signal_type": "kpi_metric",  # ✅ From KPIs
                "kpi_id": 456,
                "kpi_parameter": "Daily Active Users",
                "current_value": 1250,
                "health_status": "Critical",
                "health_score": 12.5,
                ...
            }
        },
        {
            "similarity": 0.90,
            "payload": {
                "signal_type": "external_signal",  # ✅ From signals.csv
                "signal_source": "external",
                "signal_id": "funding_round_2026_01",
                "event_type": "funding_raised",
                "amount": 5000000,
                ...
            }
        }
    ],
    
    "qualitative_signals": [
        {
            "similarity": 0.80,
            "payload": {
                "signal_type": "account_note",  # ✅ From AccountNote table
                "note_id": 789,
                "sentiment": "negative",
                "severity": "high",
                "text": "Integration broken for 2 weeks...",
                ...
            }
        },
        {
            "similarity": 0.85,
            "payload": {
                "signal_type": "support_ticket",  # ✅ From signals.csv
                "signal_source": "external",
                "ticket_id": "TICK-12345",
                "severity": "critical",
                ...
            }
        }
    ],
    
    "historical_patterns": [
        {
            "similarity": 0.75,
            "payload": {
                "signal_type": "historical_pattern",
                "pattern_type": "churn_precedent",
                "similar_accounts": 5,
                "outcome": "churned",
                ...
            }
        }
    ]
}
```

---

## 🔄 **Data Flow: How Payload is Built**

### **Step 1: Collect from Multiple Sources**

**Current Implementation (`signal_analyst_api.py`):**

```python
# Source 1: Qdrant (Vector Database)
if use_qdrant:
    quant_signals = get_quantitative_signals_from_qdrant(...)  # top_k=20
    qual_signals = get_qualitative_signals_from_qdrant(...)    # top_k=20
    hist_patterns = get_historical_patterns_from_qdrant(...)    # top_k=10
    quantitative_signals.extend(quant_signals)  # ⚠️ NO DEDUPLICATION
    qualitative_signals.extend(qual_signals)    # ⚠️ NO DEDUPLICATION

# Source 2: PostgreSQL (Raw Database)
if use_database:
    db_signals = convert_database_models_to_signals(
        account=account,
        kpis=kpis,           # limit(50)
        dc_kpis=dc_kpis,     # limit(50)
        notes=notes,          # limit(20)
        account_health_score=overall_health_score  # ✅ From rollup
    )
    quantitative_signals.extend(db_signals['quantitative_signals'])  # ⚠️ NO DEDUPLICATION
    qualitative_signals.extend(db_signals['qualitative_signals'])    # ⚠️ NO DEDUPLICATION

# Source 3: signals.csv (External Signals) - ⚠️ NOT YET IMPLEMENTED
# Would need: import_signals_from_csv() function
```

---

## ⚠️ **Current Duplication Issues**

### **Problem 1: Qdrant + PostgreSQL Duplication**

**Scenario:**
- Qdrant contains embedded versions of PostgreSQL data
- Signal Analyst collects from BOTH sources
- Same KPI appears twice (once from Qdrant, once from PostgreSQL)

**Example:**
```
Quantitative Signals:
  Signal 1 (from Qdrant): KPI ID 456, "Daily Active Users" = 1250
  Signal 2 (from DB): KPI ID 456, "Daily Active Users" = 1250  ← DUPLICATE!
```

**Impact:**
- Wastes tokens (sending duplicate data to LLM)
- Biases analysis (same signal counted twice)
- Increases cost
- Slower processing

---

### **Problem 2: Account Health Score Duplication**

**Scenario:**
- Account health score added as signal in `signal_converter.py`
- May also appear in Qdrant if embedded
- Could be duplicated

---

## ✅ **Recommended Payload Architecture**

### **Two Primary Sources (As You Described):**

#### **Source 1: Quantitative Data (KPI-Based)**

**Includes:**
1. **Account-Level Health Score** (Level 3 rollup)
   - Overall health score (0-100)
   - Category scores (Product Usage, Support, etc.)
   - Temporal grouping (week_number, month_year)

2. **Individual KPI Health Scores** (Level 1)
   - Each KPI with health status (Critical/At-Risk/Healthy)
   - Health score (0-100)
   - Reference range context
   - Temporal grouping (week_number, month_year)

**Source:** PostgreSQL (`kpis`, `dc2s_kpis`, `health_trends` tables)

**Deduplication Key:** `kpi_id` or `(account_id, kpi_code, measured_at)`

---

#### **Source 2: Signals (from signals.csv format)**

**Includes:**
1. **External Signals:**
   - Funding events
   - Executive changes
   - Market events
   - Competitor mentions

2. **Internal Signals:**
   - Support tickets
   - Account notes (from `AccountNote` table)
   - Email interactions
   - Meeting notes

**Source:** 
- `AccountNote` table (internal)
- signals.csv files (external) - ⚠️ **NOT YET IMPLEMENTED**
- Qdrant (if embedded)

**Deduplication Key:** `signal_id` or `(account_id, signal_type, timestamp)`

---

## 🔧 **Deduplication Strategy**

### **Option 1: Deduplicate by ID (Recommended)**

**Implementation:**
```python
def deduplicate_signals(signals: List[SignalData]) -> List[SignalData]:
    """Remove duplicate signals based on unique identifiers"""
    seen_ids = set()
    unique_signals = []
    
    for signal in signals:
        payload = signal.payload
        
        # Create unique key based on signal type
        if payload.get('signal_type') == 'kpi_metric':
            # Use kpi_id for KPIs
            key = f"kpi_{payload.get('kpi_id')}"
        elif payload.get('signal_type') == 'account_note':
            # Use note_id for notes
            key = f"note_{payload.get('note_id')}"
        elif payload.get('signal_type') == 'account_health_score':
            # Use account_id + timestamp for health score
            key = f"health_{payload.get('account_id')}_{payload.get('calculated_at')}"
        elif payload.get('signal_type') == 'external_signal':
            # Use signal_id for external signals
            key = f"signal_{payload.get('signal_id')}"
        else:
            # Fallback: use text hash for unknown types
            text = payload.get('text', '')
            key = f"text_{hash(text)}"
        
        if key and key not in seen_ids:
            seen_ids.add(key)
            unique_signals.append(signal)
        elif not key:
            # Signals without key - keep all (e.g., account metadata)
            unique_signals.append(signal)
    
    return unique_signals
```

**Usage:**
```python
# After collecting from all sources
quantitative_signals = deduplicate_signals(quantitative_signals)
qualitative_signals = deduplicate_signals(qualitative_signals)
```

---

### **Option 2: Prioritize Source (Qdrant vs DB)**

**Strategy:**
- If signal exists in both Qdrant and DB, keep only one
- Prefer Qdrant (has similarity scores, better for semantic search)
- Or prefer DB (has exact data, no embedding loss)

**Implementation:**
```python
def merge_signals_with_priority(qdrant_signals: List[SignalData], 
                                 db_signals: List[SignalData],
                                 prefer_qdrant: bool = True) -> List[SignalData]:
    """Merge signals, preferring one source over another"""
    # Create lookup by ID
    signal_map = {}
    
    # Add signals from preferred source first
    preferred = qdrant_signals if prefer_qdrant else db_signals
    fallback = db_signals if prefer_qdrant else qdrant_signals
    
    for signal in preferred:
        key = get_signal_key(signal)
        if key:
            signal_map[key] = signal
    
    # Add signals from fallback source (only if not already present)
    for signal in fallback:
        key = get_signal_key(signal)
        if key and key not in signal_map:
            signal_map[key] = signal
    
    return list(signal_map.values())
```

---

## 📊 **Proposed Payload Structure (Deduplicated)**

### **Quantitative Signals:**

```python
quantitative_signals = [
    # 1. Account Health Score (ONE signal, from rollup)
    {
        "signal_type": "account_health_score",
        "overall_health_score": 75.5,
        "week_number": 4,
        "month_year": "2026-01",
        "source": "health_score_rollup"  # ✅ Single source
    },
    
    # 2. Individual KPIs (deduplicated by kpi_id)
    {
        "signal_type": "kpi_metric",
        "kpi_id": 456,  # ✅ Unique identifier
        "kpi_parameter": "Daily Active Users",
        "current_value": 1250,
        "health_status": "Critical",
        "health_score": 12.5,
        "week_number": 4,
        "source": "postgresql"  # ✅ Single source (prefer DB over Qdrant)
    },
    
    # 3. External Signals (from signals.csv)
    {
        "signal_type": "external_signal",
        "signal_id": "funding_round_2026_01",  # ✅ Unique identifier
        "event_type": "funding_raised",
        "amount": 5000000,
        "source": "signals_csv"
    }
]
```

---

### **Qualitative Signals:**

```python
qualitative_signals = [
    # 1. Account Notes (from AccountNote table)
    {
        "signal_type": "account_note",
        "note_id": 789,  # ✅ Unique identifier
        "sentiment": "negative",
        "severity": "high",
        "text": "Integration broken...",
        "week_number": 4,
        "source": "postgresql"
    },
    
    # 2. Support Tickets (from signals.csv)
    {
        "signal_type": "support_ticket",
        "signal_id": "TICK-12345",  # ✅ Unique identifier
        "severity": "critical",
        "source": "signals_csv"
    }
]
```

---

## 🎯 **Decision Flow: Playbook vs Follow-Up Call**

### **Current Flow:**

```
Signal Analyst Analysis
  ↓
LLM Returns:
  - predicted_outcome (churn/expansion/stable)
  - churn_probability (0-100%)
  - risk_drivers (list)
  - recommended_actions (list)
  ↓
Decision Logic (NOT YET IMPLEMENTED):
  - If churn_probability > 70% AND health_score < 50:
    → Trigger playbook (e.g., "voc-sprint")
  - If churn_probability 40-70%:
    → Follow-up call recommended
  - If expansion_probability > 60%:
    → Trigger playbook (e.g., "expansion-blitz")
  - If health_score > 80%:
    → No action needed (healthy account)
```

**Code Location:** Would be in `playbook_recommendations_api.py` or new decision engine

---

## ✅ **Implementation Plan**

### **Step 1: Add Deduplication Function**

**File:** `backend/agents/signal_analyst_api.py`

```python
def deduplicate_signals(signals: List[SignalData]) -> List[SignalData]:
    """Remove duplicate signals based on unique identifiers"""
    seen_keys = set()
    unique_signals = []
    
    for signal in signals:
        payload = signal.payload
        signal_type = payload.get('signal_type')
        
        # Create unique key based on signal type
        if signal_type == 'kpi_metric':
            key = f"kpi_{payload.get('kpi_id')}"
        elif signal_type == 'account_note':
            key = f"note_{payload.get('note_id')}"
        elif signal_type == 'account_health_score':
            # Health score is unique per account per calculation
            key = f"health_{payload.get('account_id')}_{payload.get('calculated_at', 'latest')}"
        elif signal_type == 'external_signal':
            key = f"signal_{payload.get('signal_id')}"
        elif signal_type == 'dc2s_kpi':
            # For DC2S KPIs, use account_id + kpi_code + measured_at
            key = f"dc2s_{payload.get('account_id')}_{payload.get('kpi_code')}_{payload.get('measured_at', '')}"
        else:
            # Fallback: use text hash
            text = payload.get('text', '')
            key = f"text_{hash(text)}"
        
        if key and key not in seen_keys:
            seen_keys.add(key)
            unique_signals.append(signal)
        elif not key:
            # Signals without key - keep all
            unique_signals.append(signal)
    
    logger.info(f"Deduplicated signals: {len(signals)} → {len(unique_signals)} (removed {len(signals) - len(unique_signals)} duplicates)")
    return unique_signals
```

---

### **Step 2: Apply Deduplication Before LLM**

**File:** `backend/agents/signal_analyst_api.py`

```python
# After collecting from all sources
quantitative_signals.extend(quant_signals)  # From Qdrant
quantitative_signals.extend(db_signals['quantitative_signals'])  # From DB

# ✅ DEDUPLICATE before sending to LLM
quantitative_signals = deduplicate_signals(quantitative_signals)
qualitative_signals = deduplicate_signals(qualitative_signals)
historical_patterns = deduplicate_signals(historical_patterns)

logger.info(f"Final signal counts: {len(quantitative_signals)} quantitative, {len(qualitative_signals)} qualitative")
```

---

### **Step 3: Use QualitativeSignal Table (Already Exists)** ✅

**File:** `backend/agents/signal_analyst_api.py` (UPDATED)

**Status:** ✅ **IMPLEMENTED** - Signals from CSV are already loaded into `QualitativeSignal` table during onboarding/runtime.

**Implementation:**
- ✅ Query `QualitativeSignal` table for account signals
- ✅ Convert to SignalData format
- ✅ Include in qualitative_signals payload
- ✅ Deduplicate with other signals

**Note:** Signals.csv files are loaded into `QualitativeSignal` table during customer data loading (see `02_load_customer_data_SMART_V2_CONFIG_AWARE.py`).

---

## 📋 **Summary: Payload Architecture**

### **Two Primary Sources:**

1. **Quantitative Data (KPI-Based):**
   - ✅ Account health score (Level 3 rollup)
   - ✅ Individual KPI health scores (Level 1)
   - ✅ Associated KPIs with health status
   - **Source:** PostgreSQL (`kpis`, `dc2s_kpis`, `health_trends`)

2. **Signals (from signals.csv format):**
   - ✅ External signals (funding, exec changes)
   - ✅ Internal signals (notes, tickets)
   - **Source:** `AccountNote` table + signals.csv files (future)

### **LLM Correlation:**
- ✅ LLM receives deduplicated signals
- ✅ LLM correlates quantitative + qualitative signals
- ✅ LLM considers temporal grouping (week/month)
- ✅ LLM returns predictions and recommendations

### **Decision Making:**
- ✅ Signal Analyst output → Decision engine
- ✅ Decision: Playbook trigger OR Follow-up call
- ⚠️ **Decision logic NOT YET IMPLEMENTED** (would be in `playbook_recommendations_api.py`)

### **Deduplication:**
- ✅ **MUST implement** before sending to LLM
- ✅ Use unique identifiers (`kpi_id`, `note_id`, `signal_id`)
- ✅ Prefer one source over another (DB vs Qdrant)

---

## 🚀 **Implementation Status**

1. ✅ **Deduplication function created** (`signal_deduplicator.py`)
2. ✅ **Deduplication applied** before LLM (in `signal_analyst_api.py`)
3. ⚠️ **Signals.csv import** (Step 3 - future, needs implementation)
4. ⚠️ **Decision engine** (playbook vs follow-up call - needs implementation)

---

## 📊 **Decision Flow: Playbook vs Follow-Up Call**

### **Current State:**

**Signal Analyst Output:**
```python
{
    "predicted_outcome": "churn",
    "churn_probability": 75.0,
    "health_score": 45.0,
    "risk_drivers": [...],
    "recommended_actions": [...]
}
```

**Decision Logic (NOT YET IMPLEMENTED):**

Would need to be added to `playbook_recommendations_api.py`:

```python
def decide_action_from_signal_analyst_output(output: SignalAnalystOutput) -> Dict:
    """
    Decide next action based on Signal Analyst output
    
    Returns:
        {
            "action_type": "playbook" | "follow_up_call" | "no_action",
            "playbook_id": "voc-sprint" | None,
            "priority": "immediate" | "high" | "medium" | "low",
            "reason": "Explanation"
        }
    """
    churn_prob = output.churn_probability
    health_score = output.health_score
    predicted_outcome = output.predicted_outcome
    
    # Decision Logic:
    if churn_prob > 70 and health_score < 50:
        # High churn risk + low health = Trigger playbook
        return {
            "action_type": "playbook",
            "playbook_id": "voc-sprint",  # or "renewal-safeguard"
            "priority": "immediate",
            "reason": f"High churn risk ({churn_prob}%) with low health ({health_score}/100)"
        }
    
    elif churn_prob > 50 and health_score < 60:
        # Medium churn risk = Follow-up call
        return {
            "action_type": "follow_up_call",
            "playbook_id": None,
            "priority": "high",
            "reason": f"Moderate churn risk ({churn_prob}%) - proactive engagement needed"
        }
    
    elif output.expansion_probability and output.expansion_probability > 60:
        # High expansion potential = Trigger expansion playbook
        return {
            "action_type": "playbook",
            "playbook_id": "expansion-blitz",
            "priority": "high",
            "reason": f"High expansion potential ({output.expansion_probability}%)"
        }
    
    elif health_score > 80:
        # Healthy account = No action needed
        return {
            "action_type": "no_action",
            "playbook_id": None,
            "priority": "low",
            "reason": f"Account is healthy ({health_score}/100) - no intervention needed"
        }
    
    else:
        # Default: Follow-up call for monitoring
        return {
            "action_type": "follow_up_call",
            "playbook_id": None,
            "priority": "medium",
            "reason": "Routine monitoring recommended"
        }
```

---

## ✅ **Summary: Payload Architecture**

### **Two Primary Sources (As You Described):**

1. **Quantitative Data (KPI-Based):**
   - ✅ Account health score (Level 3 rollup)
   - ✅ Individual KPI health scores (Level 1)
   - ✅ Associated KPIs with health status
   - **Source:** PostgreSQL (`kpis`, `dc2s_kpis`, `health_trends`)

2. **Signals (from signals.csv format):**
   - ✅ Internal signals (AccountNote table)
   - ⚠️ External signals (signals.csv - **NOT YET IMPLEMENTED**)
   - **Source:** `AccountNote` table + signals.csv files (future)

### **LLM Correlation:**
- ✅ LLM receives **deduplicated** signals
- ✅ LLM correlates quantitative + qualitative signals
- ✅ LLM considers temporal grouping (week/month)
- ✅ LLM returns predictions and recommendations

### **Decision Making:**
- ✅ Signal Analyst output → Decision engine
- ✅ Decision: Playbook trigger OR Follow-up call
- ⚠️ **Decision logic NOT YET IMPLEMENTED** (would be in `playbook_recommendations_api.py`)

### **Deduplication:**
- ✅ **IMPLEMENTED** - Deduplication function created
- ✅ **IMPLEMENTED** - Applied before sending to LLM
- ✅ Uses unique identifiers (`kpi_id`, `note_id`, `signal_id`)
- ✅ Prefers database source (exact data, no embedding loss)
