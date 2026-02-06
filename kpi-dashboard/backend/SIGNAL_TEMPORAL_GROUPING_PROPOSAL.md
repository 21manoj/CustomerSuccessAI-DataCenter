# 📅 Signal Temporal Grouping Proposal
## Week/Month-Based Correlation (Not Exact Timestamps)

## Question: How would LLM associate signals, KPIs, and notes in context of week/month (not exact timestamps)?

## Answer: **Group by Week/Month Periods - Not Yet Implemented**

---

## 🎯 **Proposed Approach**

### **Concept: Time-Period Grouping**

Instead of exact timestamps, group signals/KPIs/notes by:
- **Week Number** (1-52) - For journey-based analysis
- **Month/Year** (2026-01) - For monthly trend analysis

This allows LLM to correlate:
- "Signals in Week 5 → KPI changes in Week 6"
- "Notes in January → KPI trends in January"
- "Multiple signals in same week = correlated events"

---

## 📊 **Current Data Available**

### **1. Timestamps in Database:**

**DC2SKPI:**
```python
measured_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
# Example: 2026-01-15 10:30:00
```

**AccountNote:**
```python
created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
# Example: 2026-01-20 14:22:00
```

**KPI (via KPIUpload):**
```python
uploaded_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
# Example: 2026-01-10 09:00:00
```

### **2. Time-Period Models:**

**HealthTrend:**
```python
month = db.Column(db.Integer, nullable=False)  # 1-12
year = db.Column(db.Integer, nullable=False)   # 2026
# Already grouped by month/year!
```

**KPITimeSeries:**
```python
month = db.Column(db.Integer, nullable=False)  # 1-12
year = db.Column(db.Integer, nullable=False)   # 2026
# Already grouped by month/year!
```

**Journey Data:**
```python
week_number = event.get('week_number')  # 1-52
# Already grouped by week!
```

---

## 🔧 **Proposed Implementation**

### **Step 1: Add Time-Period Fields to Signal Payloads**

**File:** `backend/agents/signal_converter.py`

**For DC2SKPI:**
```python
from datetime import datetime

def convert_dc2s_kpi_to_signal_data(dc_kpi: DC2SKPI, similarity: float = 0.85):
    # Convert measured_at to week_number and month/year
    measured_at = dc_kpi.measured_at if dc_kpi.measured_at else datetime.utcnow()
    
    # Calculate week number (ISO week)
    week_number = measured_at.isocalendar()[1]  # Week 1-52/53
    year = measured_at.year
    month = measured_at.month
    month_year = f"{year}-{month:02d}"
    
    payload = {
        'signal_type': 'kpi_metric',
        'current_value': float(dc_kpi.value),
        'measured_at': measured_at.isoformat(),  # Keep exact for reference
        'week_number': week_number,              # ✅ ADD: Week grouping
        'month': month,                          # ✅ ADD: Month grouping
        'year': year,                            # ✅ ADD: Year grouping
        'month_year': month_year,                # ✅ ADD: Month/Year string
        # ... rest of payload
    }
```

**For AccountNote:**
```python
def convert_account_notes_to_signal_data(notes: List[AccountNote], similarity: float = 0.8):
    signals = []
    
    for note in notes:
        created_at = note.created_at if note.created_at else datetime.utcnow()
        
        # Calculate week number and month/year
        week_number = created_at.isocalendar()[1]
        year = created_at.year
        month = created_at.month
        month_year = f"{year}-{month:02d}"
        
        payload = {
            'signal_type': 'account_note',
            'created_at': created_at.isoformat(),
            'week_number': week_number,          # ✅ ADD: Week grouping
            'month': month,                      # ✅ ADD: Month grouping
            'year': year,                        # ✅ ADD: Year grouping
            'month_year': month_year,            # ✅ ADD: Month/Year string
            # ... rest of payload
        }
```

**For KPI (SaaS):**
```python
def convert_kpi_to_signal_data(kpi: KPI, similarity: float = 0.85):
    # Get timestamp from KPIUpload
    upload = KPIUpload.query.get(kpi.upload_id)
    if upload and upload.uploaded_at:
        uploaded_at = upload.uploaded_at
        week_number = uploaded_at.isocalendar()[1]
        year = uploaded_at.year
        month = uploaded_at.month
        month_year = f"{year}-{month:02d}"
    else:
        week_number = None
        month = None
        year = None
        month_year = None
    
    payload = {
        'signal_type': 'kpi_metric',
        'current_value': float(kpi.data),
        'week_number': week_number,              # ✅ ADD: Week grouping
        'month': month,                          # ✅ ADD: Month grouping
        'year': year,                            # ✅ ADD: Year grouping
        'month_year': month_year,                # ✅ ADD: Month/Year string
        # ... rest of payload
    }
```

---

### **Step 2: Group Signals by Time Period**

**File:** `backend/agents/signal_analyst_api.py`

**Add grouping function:**
```python
def group_signals_by_time_period(signals: List[SignalData], period_type: str = 'week'):
    """
    Group signals by time period (week or month)
    
    Args:
        signals: List of SignalData
        period_type: 'week' or 'month'
    
    Returns:
        Dict[period_key, List[SignalData]]
    """
    grouped = defaultdict(list)
    
    for signal in signals:
        payload = signal.payload
        
        if period_type == 'week':
            week_num = payload.get('week_number')
            year = payload.get('year')
            if week_num and year:
                period_key = f"Week {week_num}, {year}"
                grouped[period_key].append(signal)
        elif period_type == 'month':
            month_year = payload.get('month_year')
            if month_year:
                grouped[month_year].append(signal)
    
    return dict(grouped)
```

---

### **Step 3: Format Signals with Time-Period Context**

**File:** `backend/agents/prompts.py`

**Update `format_quantitative_signals()`:**
```python
@staticmethod
def format_quantitative_signals(signals: List[Dict], group_by_period: bool = True) -> str:
    """Format quantitative signals with time-period grouping"""
    if not signals:
        return "No quantitative signals available"
    
    if group_by_period:
        # Group by week_number or month_year
        grouped_by_week = defaultdict(list)
        grouped_by_month = defaultdict(list)
        
        for signal in signals:
            payload = signal.get('payload', {})
            week_num = payload.get('week_number')
            month_year = payload.get('month_year')
            
            if week_num:
                grouped_by_week[f"Week {week_num}"].append(signal)
            if month_year:
                grouped_by_month[month_year].append(signal)
        
        # Format by time period
        context_lines = []
        
        # Group by week (if available)
        if grouped_by_week:
            context_lines.append("**QUANTITATIVE SIGNALS BY WEEK:**")
            for week_label in sorted(grouped_by_week.keys(), key=lambda x: int(x.split()[1])):
                week_signals = grouped_by_week[week_label]
                context_lines.append(f"\n{week_label}:")
                for i, signal in enumerate(week_signals[:5], 1):  # Top 5 per week
                    payload = signal.get('payload', {})
                    pillar = payload.get('pillar', 'unknown')
                    metric_type = payload.get('metric_type', 'unknown')
                    current_value = payload.get('current_value', 0)
                    context_lines.append(
                        f"  Signal {i} [{pillar.upper()}]: {metric_type} = {current_value}"
                    )
        
        # Group by month (if available)
        elif grouped_by_month:
            context_lines.append("**QUANTITATIVE SIGNALS BY MONTH:**")
            for month_year in sorted(grouped_by_month.keys()):
                month_signals = grouped_by_month[month_year]
                context_lines.append(f"\n{month_year}:")
                for i, signal in enumerate(month_signals[:5], 1):
                    payload = signal.get('payload', {})
                    pillar = payload.get('pillar', 'unknown')
                    metric_type = payload.get('metric_type', 'unknown')
                    current_value = payload.get('current_value', 0)
                    context_lines.append(
                        f"  Signal {i} [{pillar.upper()}]: {metric_type} = {current_value}"
                    )
        
        return "\n".join(context_lines)
    
    else:
        # Original format (no grouping)
        # ... existing code ...
```

---

### **Step 4: Add Temporal Correlation Instructions**

**File:** `backend/agents/prompts.py` - `get_analysis_prompt()`

**Add to CRITICAL RULES:**
```python
**CRITICAL RULES**:
...
9. **Temporal Correlation (Week/Month Level)**:
   - Signals grouped by WEEK or MONTH are likely related
   - If Signal A in Week 5 and KPI change in Week 6 → likely cause-and-effect
   - Multiple signals in same week/month → correlated events
   - Look for temporal sequences:
     * Week N: Signal A (support ticket)
     * Week N+1: KPI decline
     * Week N+2: Health score drop
   - Recent weeks (last 4 weeks) are more relevant than older data
   - Group analysis by time period to identify patterns
```

---

## 📋 **Example: How LLM Would See It**

### **Current Format (No Temporal Grouping):**
```
Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250 (↓ 30.0% trend)
Signal 2 [FINANCIAL]: ARR = 120000 (↓ 15.0% trend)
Signal 3 [account_note]: (negative/critical) Integration broken...
```

**Problem:** LLM doesn't know when these happened relative to each other.

---

### **Proposed Format (With Week/Month Grouping):**
```
**QUANTITATIVE SIGNALS BY WEEK:**

Week 5, 2026:
  Signal 1 [PRODUCT_USAGE]: Daily Active Users = 1250
  Signal 2 [FINANCIAL]: ARR = 120000

Week 6, 2026:
  Signal 3 [SUPPORT]: Support Tickets = 45 (↑ 200.0% trend)

Week 7, 2026:
  Signal 4 [PRODUCT_USAGE]: Daily Active Users = 980 (↓ 22% from Week 5)

**QUALITATIVE SIGNALS BY WEEK:**

Week 5, 2026:
  Signal 1 [account_note] 💬: (negative/critical) Salesforce integration broken for 2 weeks...

Week 6, 2026:
  Signal 2 [support_ticket] 💬: (negative/high) Champion left company...
```

**Benefit:** LLM can now see:
- Week 5: Integration issue + Usage drop
- Week 6: Support tickets spike
- Week 7: Continued usage decline
- **Temporal sequence:** Integration issue → Support spike → Usage decline

---

## 🔧 **Implementation Steps**

### **Step 1: Add Time-Period Calculation**

**Create utility function:**
```python
# backend/agents/temporal_utils.py

from datetime import datetime

def get_time_periods(dt: datetime) -> dict:
    """Extract week and month/year from datetime"""
    if not dt:
        return {
            'week_number': None,
            'month': None,
            'year': None,
            'month_year': None
        }
    
    week_number = dt.isocalendar()[1]  # ISO week (1-52/53)
    year = dt.year
    month = dt.month
    month_year = f"{year}-{month:02d}"
    
    return {
        'week_number': week_number,
        'month': month,
        'year': year,
        'month_year': month_year
    }
```

### **Step 2: Update Signal Converters**

**File:** `backend/agents/signal_converter.py`

```python
from .temporal_utils import get_time_periods

def convert_dc2s_kpi_to_signal_data(dc_kpi: DC2SKPI, similarity: float = 0.85):
    measured_at = dc_kpi.measured_at if dc_kpi.measured_at else None
    time_periods = get_time_periods(measured_at)
    
    payload = {
        # ... existing fields ...
        **time_periods,  # ✅ Add week_number, month, year, month_year
    }
```

### **Step 3: Update Prompt Formatting**

**File:** `backend/agents/prompts.py`

```python
def format_quantitative_signals(signals: List[Dict], group_by: str = 'week') -> str:
    """Format with time-period grouping"""
    if group_by == 'week':
        # Group by week_number
        # Format as shown above
    elif group_by == 'month':
        # Group by month_year
        # Format by month
```

---

## 🎯 **Benefits of Week/Month Grouping**

### **1. Practical Correlation:**
- "Signals in Week 5 → KPI changes in Week 6" (clear temporal sequence)
- "Multiple signals in same week = correlated" (grouped analysis)

### **2. Pattern Recognition:**
- LLM can identify: "Week 5-7 pattern: Integration issue → Support spike → Usage decline"
- LLM can correlate: "January signals → February KPI trends"

### **3. Reduced Noise:**
- Exact timestamps (2026-01-15 10:30:00) are too granular
- Week/month grouping is more meaningful for correlation

### **4. Journey Alignment:**
- Journey data uses `week_number` (1-52)
- Signals grouped by week align with journey visualization
- Enables: "Week 5 journey events → Week 5 signals → Week 6 KPI changes"

---

## 📊 **Example Correlation**

### **With Week Grouping:**

**LLM Sees:**
```
Week 5:
  - Signal: Integration broken (account_note)
  - Signal: DAU = 1250 (quantitative)
  - KPI: Support tickets = 12

Week 6:
  - Signal: Support tickets = 45 (↑ 275%)
  - KPI: DAU = 980 (↓ 22%)
  - KPI: Health score = 68 (↓ from 75)

Week 7:
  - Signal: Champion left (account_note)
  - KPI: DAU = 850 (↓ 13%)
  - KPI: Health score = 55 (↓ from 68)
```

**LLM Can Correlate:**
- Week 5: Integration issue + initial usage drop
- Week 6: Support spike + continued usage decline + health drop
- Week 7: Champion departure + further decline
- **Pattern:** Integration issue → Support overload → Champion leaves → Continued decline

---

## ✅ **Recommendation**

**Implement week/month grouping:**

1. ✅ **Add time-period fields** to signal payloads (week_number, month, year, month_year)
2. ✅ **Group signals by time period** before formatting
3. ✅ **Format signals with time-period labels** in prompt
4. ✅ **Add temporal correlation instructions** to LLM prompt

**This enables:**
- Week-based correlation (aligned with journey data)
- Month-based correlation (aligned with HealthTrend/KPITimeSeries)
- Clear temporal sequences for LLM analysis
- Better cause-and-effect reasoning

---

## 🔧 **Quick Implementation**

**Priority:** HIGH (enables proper temporal correlation)

**Files to Update:**
1. `signal_converter.py` - Add time-period calculation
2. `prompts.py` - Add time-period grouping and formatting
3. `signal_analyst_api.py` - Group signals before sending to LLM

**Estimated Impact:**
- Enables explicit temporal correlation
- Aligns with journey week_number structure
- Improves LLM reasoning about cause-and-effect
- Better pattern recognition
