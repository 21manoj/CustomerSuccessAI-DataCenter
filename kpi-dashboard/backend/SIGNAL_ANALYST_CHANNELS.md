# 📡 Signal Analyst Channels Overview

## Current Channels: **2 Data Sources**

Signal Analyst collects signals from **2 primary data source channels**:

---

## **Channel 1: Qdrant (Vector Database)**

**Location:** `backend/agents/qdrant_integration.py`

**Collection:** `kpi_dashboard_vectors_customer_{customer_id}`

**Signal Types Provided:**
1. **Quantitative Signals** (top_k=20)
   - Query: `"account {account_id} KPI metrics usage revenue health score quantitative data"`
   - Contains: KPIs, usage metrics, revenue, health scores
   
2. **Qualitative Signals** (top_k=20)
   - Query: `"account {account_id} support tickets emails notes sentiment qualitative data"`
   - Contains: Support tickets, emails, notes, sentiment data
   
3. **Historical Patterns** (top_k=10)
   - Query: `"account {account_id} historical trends patterns time series churn expansion outcomes"`
   - Contains: Historical trends, patterns, time series, churn/expansion outcomes

**Functions:**
- `get_quantitative_signals_from_qdrant()`
- `get_qualitative_signals_from_qdrant()`
- `get_historical_patterns_from_qdrant()`

---

## **Channel 2: PostgreSQL Database**

**Location:** `backend/agents/signal_converter.py`

**Data Models Used:**
1. **Account** → Quantitative signals
   - Revenue, industry, region, account status
   - `signal_source: 'internal'`

2. **KPI** (SaaS) → Quantitative signals
   - KPI metrics, values, trends, categories
   - `signal_source: 'internal'`

3. **DC2SKPI** (Data Center) → Quantitative signals
   - DC2S KPIs, values, targets, pillars, weights
   - `signal_source: 'internal'`

4. **AccountNote** → Qualitative signals
   - Notes, sentiment, severity, note type
   - `signal_source: 'internal'`

**Function:**
- `convert_database_models_to_signals()`

**Returns:**
- `quantitative_signals`: List[SignalData]
- `qualitative_signals`: List[SignalData]
- `historical_patterns`: [] (empty - not populated from DB)

---

## **Signal Source Classification**

Within the signals, there's a `signal_source` field that can be:

1. **`'internal'`** ✅ **ACTIVE**
   - All database signals are marked as `'internal'`
   - Account data, KPIs, notes from your system

2. **`'external'`** ⚠️ **PARTIALLY IMPLEMENTED**
   - Mentioned in code and prompts
   - Currently only in mock/test data
   - Would include: funding events, executive changes, market events
   - **Not yet fully integrated** with real external data sources

---

## **Summary**

| Channel | Data Source | Signal Types | Status |
|---------|-------------|--------------|--------|
| **1. Qdrant** | Vector Database | Quantitative, Qualitative, Historical | ✅ Active |
| **2. PostgreSQL** | Database | Quantitative, Qualitative | ✅ Active |
| **3. External Sources** | (Future) | External events | ⚠️ Planned |

---

## **Current Implementation**

**In `signal_analyst_api.py`:**

```python
# Channel 1: Qdrant
if use_qdrant:
    quantitative_signals.extend(get_quantitative_signals_from_qdrant(...))
    qualitative_signals.extend(get_qualitative_signals_from_qdrant(...))
    historical_patterns.extend(get_historical_patterns_from_qdrant(...))

# Channel 2: Database
if use_database:
    db_signals = convert_database_models_to_signals(
        account=account,
        kpis=kpis,
        dc_kpis=dc_kpis,
        notes=notes
    )
    quantitative_signals.extend(db_signals['quantitative_signals'])
    qualitative_signals.extend(db_signals['qualitative_signals'])
    historical_patterns.extend(db_signals['historical_patterns'])
```

---

## **Answer: 2 Active Channels**

**Signal Analyst currently has 2 active data source channels:**

1. ✅ **Qdrant** (Vector Database) - 3 signal types
2. ✅ **PostgreSQL** (Database) - 2 signal types (quantitative, qualitative)

**Total Signal Types Collected:**
- Quantitative: From both channels
- Qualitative: From both channels  
- Historical: Only from Qdrant (not from database)

**Note:** External signal sources are mentioned in the architecture but not yet fully implemented (only in test/mock data).
