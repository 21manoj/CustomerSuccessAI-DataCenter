# ✅ Decision Matrix LLM Implementation

## 🎯 **Overview**

Switched decision matrix from **rule-based** to **LLM-based** for more nuanced correlation analysis between quantitative (KPI) trends and qualitative (signal) sentiment.

---

## 🔄 **What Changed**

### **Before (Rule-Based):**
- Simple if/else logic comparing trend direction and sentiment
- Fixed confidence scores (0.85 for agreement, 0.60 for disagreement)
- Template-based reasoning

### **After (LLM-Based):**
- LLM analyzes correlation with nuanced understanding
- Dynamic confidence scores based on context
- Context-aware reasoning with specific examples from signals
- Handles edge cases better (e.g., "tickets taking long" vs "product working well")

---

## 🔧 **Implementation**

### **1. New LLM Function: `_calculate_decision_matrix_llm()`**

**Location:** `backend/agents/decision_matrix.py`

**Features:**
- Uses `gpt-4o-mini` (cost-effective model)
- Structured JSON output
- Analyzes up to 10 quantitative and 10 qualitative signals
- Provides nuanced reasoning with key insights

**Prompt Structure:**
```
- Quantitative Data (KPI Trends)
- Qualitative Data (Customer Signals)
- Task: Analyze correlation
- Decision Matrix Rules
- Output: JSON with alignment, confidence, reasoning, key_insights
```

### **2. Fallback Mechanism**

**Rule-Based Fallback:**
- If LLM fails or API key unavailable
- Automatic fallback to rule-based logic
- Ensures system always works

**Error Handling:**
```python
try:
    # Use LLM
    return _calculate_decision_matrix_llm(...)
except Exception as e:
    logger.warning(f"LLM failed, using rule-based fallback: {e}")
    return _calculate_decision_matrix_rule_based(...)
```

### **3. Integration with Signal Analyst**

**Updated:** `signal_analyst_agent.py`

**Changes:**
- Stores OpenAI API key in agent: `self.openai_api_key`
- Passes API key to `calculate_decision_matrix()`
- Uses LLM by default (`use_llm=True`)
- Falls back to rule-based if LLM fails

---

## 📊 **LLM Output Structure**

```json
{
    "alignment": "agreement" | "disagreement" | "neutral" | "positive_alignment" | "insufficient_data",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation with nuanced context and specific examples",
    "key_insights": ["Insight 1", "Insight 2", "Insight 3"]
}
```

---

## 🎯 **Benefits of LLM-Based Approach**

### **1. Nuanced Understanding**
- Understands context: "tickets taking long" vs "product working well"
- Detects subtle patterns in signal content
- Correlates specific KPI changes with specific signal themes

### **2. Dynamic Confidence**
- Adjusts confidence based on signal strength
- Higher confidence when signals strongly align
- Lower confidence when signals are ambiguous

### **3. Better Reasoning**
- Provides specific examples from signals
- Explains why data sources agree or conflict
- Suggests possible explanations for disagreements

### **4. Edge Case Handling**
- Handles complex scenarios (e.g., mixed signals with declining KPI)
- Identifies leading indicators (qualitative signals before KPI changes)
- Recognizes temporary vs permanent trends

---

## ⚙️ **Configuration**

### **Model Selection:**
- **Model:** `gpt-4o-mini` (cost-effective)
- **Temperature:** `0.3` (consistent, focused)
- **Max Tokens:** `800` (sufficient for reasoning)
- **Response Format:** `JSON` (structured output)

### **Cost Optimization:**
- Uses cheaper model (`gpt-4o-mini` vs `gpt-4o`)
- Limits signal context (top 10 quantitative, top 10 qualitative)
- Falls back to rule-based if API key unavailable

---

## 🔄 **Data Flow**

```
1. Signal Analyst collects signals
   ↓
2. Analyzes KPI trend (rule-based extraction)
   ↓
3. Analyzes signal sentiment (rule-based aggregation)
   ↓
4. Calls LLM with context:
   - KPI trend direction
   - Signal sentiment
   - Quantitative signal details
   - Qualitative signal details
   ↓
5. LLM returns:
   - Alignment (agreement/disagreement/etc.)
   - Confidence (0.0-1.0)
   - Reasoning (detailed explanation)
   - Key insights
   ↓
6. Returns DecisionMatrixResult
   ↓
7. Included in SignalAnalystOutput.data_alignment
```

---

## 🧪 **Testing**

### **Test Scenarios:**
1. ✅ **AGREEMENT**: KPI declining + negative signals
2. ✅ **DISAGREEMENT**: KPI declining + positive signals
3. ✅ **POSITIVE_ALIGNMENT**: KPI improving + positive signals
4. ✅ **NEUTRAL**: KPI stable + mixed signals
5. ✅ **INSUFFICIENT_DATA**: No KPI trend data
6. ✅ **Edge Cases**: Mixed signals, complex scenarios

### **Fallback Testing:**
- ✅ LLM failure → Rule-based fallback
- ✅ No API key → Rule-based fallback
- ✅ API timeout → Rule-based fallback

---

## 📝 **Example LLM Output**

### **AGREEMENT Scenario:**
```json
{
    "alignment": "agreement",
    "confidence": 0.88,
    "reasoning": "Strong agreement between quantitative and qualitative data. KPI health score declined from 75 to 55 (healthy → at-risk), and qualitative signals consistently indicate customer frustration with support ticket resolution times. The signal 'Customer frustrated with open tickets too long to resolve' directly correlates with the declining health score, suggesting support issues are impacting overall account health. Both data sources point to the same underlying issue: support responsiveness problems.",
    "key_insights": [
        "Support ticket resolution time is the primary driver of health score decline",
        "Customer frustration is consistent across multiple signals",
        "High confidence in churn risk prediction due to alignment"
    ]
}
```

### **DISAGREEMENT Scenario:**
```json
{
    "alignment": "disagreement",
    "confidence": 0.62,
    "reasoning": "Conflicting signals between quantitative and qualitative data. KPI health score declined from 72 to 58 (healthy → at-risk), but qualitative signals indicate customer satisfaction with product usage and support team responsiveness. This disagreement suggests either: (1) KPI is a lagging indicator and sentiment hasn't caught up yet, (2) The KPI dip is temporary (e.g., seasonal usage pattern), or (3) The health score decline is driven by factors not reflected in qualitative signals (e.g., contract terms, pricing). Recommend follow-up call to investigate the root cause.",
    "key_insights": [
        "Qualitative signals are positive but KPI shows decline",
        "Possible lag between sentiment and metrics",
        "Need deeper investigation to reconcile conflict"
    ]
}
```

---

## ✅ **Summary**

**Status:** ✅ **IMPLEMENTED**

**Key Features:**
- ✅ LLM-based correlation analysis
- ✅ Nuanced understanding of context
- ✅ Dynamic confidence scoring
- ✅ Detailed reasoning with examples
- ✅ Automatic fallback to rule-based
- ✅ Cost-optimized (gpt-4o-mini)

**Next Steps:**
- Monitor LLM performance and costs
- Collect feedback on reasoning quality
- Fine-tune prompts based on results
- Consider caching for repeated scenarios

---

## 🎉 **Result**

The decision matrix now uses **LLM for intelligent correlation**, providing more nuanced analysis while maintaining reliability through rule-based fallback!
