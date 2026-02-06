# ✅ Decision Matrix Implementation - Signal Analyst

## 🎯 **Overview**

Implemented a decision matrix that compares **quantitative (KPI) trends** with **qualitative (signal) sentiment** to determine **agreement** or **disagreement** between data sources.

---

## 📊 **Decision Matrix Logic**

### **Situation 1: AGREEMENT** ✅
- **KPI Trend**: Declining (e.g., healthy → at-risk)
- **Signal Sentiment**: Negative (e.g., "Customer frustrated with open tickets too long to resolve")
- **Decision**: **AGREEMENT** - Both point to same issue
- **Confidence**: High (0.85)
- **Action**: High confidence in churn risk prediction

### **Situation 2: DISAGREEMENT** ⚠️
- **KPI Trend**: Declining (e.g., healthy → at-risk)
- **Signal Sentiment**: Positive (e.g., "Customer happy with overall product usage and support")
- **Decision**: **DISAGREEMENT** - Conflicting signals
- **Confidence**: Lower (0.60)
- **Action**: Recommend follow-up call to investigate

### **Other Scenarios:**

#### **POSITIVE_ALIGNMENT** ✅
- **KPI Trend**: Improving (e.g., at-risk → healthy)
- **Signal Sentiment**: Positive
- **Decision**: **POSITIVE_ALIGNMENT** - Both improving
- **Action**: Good opportunity for expansion discussions

#### **NEUTRAL**
- **KPI Trend**: Stable
- **Signal Sentiment**: Mixed/Neutral
- **Decision**: **NEUTRAL**
- **Action**: Monitor and maintain engagement

---

## 🔧 **Implementation**

### **1. New File: `decision_matrix.py`**

**Key Functions:**
- `analyze_kpi_health_trend()` - Analyzes KPI health trend from quantitative signals
- `analyze_signal_sentiment()` - Analyzes aggregated sentiment from qualitative signals
- `calculate_decision_matrix()` - Main function that compares trends and sentiment

**Decision Matrix Result:**
```python
{
    "alignment": "agreement" | "disagreement" | "neutral" | "positive_alignment" | "insufficient_data",
    "trend_direction": "improving" | "declining" | "stable" | "unknown",
    "signal_sentiment": "positive" | "negative" | "neutral" | "mixed",
    "kpi_health_trend": "healthy → at-risk",
    "signal_summary": "Customer frustrated with: open tickets too long to resolve",
    "confidence": 0.85,
    "reasoning": "AGREEMENT: KPI data shows declining trend and qualitative signals indicate customer frustration. Both data sources point to the same underlying issue."
}
```

---

### **2. Updated: `models.py`**

**Added to `SignalAnalystOutput`:**
```python
data_alignment: Optional[Dict] = Field(None, description="Alignment between quantitative and qualitative data (agreement/disagreement)")
```

---

### **3. Updated: `signal_analyst_agent.py`**

**Integration:**
- Imports `calculate_decision_matrix` from `decision_matrix.py`
- Calculates decision matrix after parsing LLM response
- Adds `data_alignment` to `SignalAnalystOutput`

---

## 📋 **Decision Matrix Rules**

### **KPI Trend Analysis:**
- **IMPROVING**: critical → at-risk, at-risk → healthy, healthy → healthy (high score)
- **DECLINING**: healthy → at-risk, at-risk → critical, healthy → critical
- **STABLE**: No change in health status
- **UNKNOWN**: Cannot determine from available data

### **Signal Sentiment Analysis:**
- **POSITIVE**: Majority of signals are positive (happy, satisfied, pleased)
- **NEGATIVE**: Majority of signals are negative (frustrated, disappointed, concerned)
- **MIXED**: Both positive and negative signals present
- **NEUTRAL**: No strong sentiment detected

### **Alignment Decision Matrix:**

| KPI Trend | Signal Sentiment | Alignment | Confidence | Action |
|-----------|-----------------|-----------|------------|--------|
| Declining | Negative | **AGREEMENT** | 0.85 | High confidence in churn risk |
| Declining | Positive | **DISAGREEMENT** | 0.60 | Follow-up call needed |
| Declining | Mixed | **DISAGREEMENT** | 0.55 | Investigation needed |
| Declining | Neutral | **NEUTRAL** | 0.50 | Monitor and engage |
| Improving | Positive | **POSITIVE_ALIGNMENT** | 0.80 | Expansion opportunity |
| Improving | Negative | **DISAGREEMENT** | 0.60 | Follow-up call needed |
| Improving | Mixed/Neutral | **NEUTRAL** | 0.65 | Monitor |
| Stable | Negative | **DISAGREEMENT** | 0.55 | Proactive engagement |
| Stable | Positive | **NEUTRAL** | 0.70 | Monitor for expansion |
| Stable | Mixed/Neutral | **NEUTRAL** | 0.60 | Stable account |
| Unknown | Any | **INSUFFICIENT_DATA** | 0.30 | Need more data |

---

## 🎯 **Example Output**

### **Situation 1: AGREEMENT**
```json
{
    "data_alignment": {
        "alignment": "agreement",
        "trend_direction": "declining",
        "signal_sentiment": "negative",
        "kpi_health_trend": "healthy → at-risk",
        "signal_summary": "Customer frustrated with: open tickets too long to resolve, integration challenges",
        "confidence": 0.85,
        "reasoning": "AGREEMENT: KPI data shows declining trend (healthy → at-risk) and qualitative signals indicate customer frustration (open tickets too long to resolve). Both data sources point to the same underlying issue. High confidence in churn risk prediction."
    }
}
```

### **Situation 2: DISAGREEMENT**
```json
{
    "data_alignment": {
        "alignment": "disagreement",
        "trend_direction": "declining",
        "signal_sentiment": "positive",
        "kpi_health_trend": "healthy → at-risk",
        "signal_summary": "Customer happy with: overall product usage, support team responsiveness",
        "confidence": 0.60,
        "reasoning": "DISAGREEMENT: KPI data shows declining trend (healthy → at-risk) but qualitative signals indicate customer satisfaction (overall product usage, support team responsiveness). Conflicting signals suggest either: (1) KPI lagging indicator, (2) Temporary KPI dip, or (3) Need for deeper investigation. Lower confidence in churn risk prediction - recommend follow-up call."
    }
}
```

---

## ✅ **Benefits**

1. **Identifies Data Conflicts**: Detects when quantitative and qualitative data disagree
2. **Adjusts Confidence**: Lowers confidence when signals conflict
3. **Actionable Insights**: Recommends specific actions (follow-up call, investigation, etc.)
4. **Better Decision Making**: Helps CSMs understand when to trust KPIs vs signals
5. **Prevents False Positives**: Reduces false churn predictions when signals are positive

---

## 🔄 **Integration with Signal Analyst**

The decision matrix is automatically calculated for every Signal Analyst analysis:

1. **Signal Analyst API** receives request
2. **Collects** quantitative and qualitative signals
3. **Sends to LLM** for analysis
4. **Calculates Decision Matrix** (compares trends and sentiment)
5. **Returns** `SignalAnalystOutput` with `data_alignment` field

---

## 📝 **Next Steps**

1. ✅ Decision matrix implemented
2. ✅ Integrated into Signal Analyst output
3. ⚠️ **Future**: Use `data_alignment` to influence playbook trigger decisions
4. ⚠️ **Future**: Display `data_alignment` in UI (Executive Dashboard, Signal Analyst results)
5. ⚠️ **Future**: Use `data_alignment` confidence to adjust churn probability

---

## 🎯 **Summary**

**Your Requirement:**
> "KPI data showing down trend + signal saying customer frustrated = AGREEMENT"
> "KPI data showing down trend + customer happy = DISAGREEMENT"

**Implementation:**
- ✅ Decision matrix compares KPI trends with signal sentiment
- ✅ Returns `agreement`, `disagreement`, `neutral`, `positive_alignment`, or `insufficient_data`
- ✅ Includes confidence score and reasoning
- ✅ Integrated into Signal Analyst output

**Result:**
Signal Analyst now makes intelligent decisions about data alignment, helping CSMs understand when to trust quantitative vs qualitative data! 🎉
