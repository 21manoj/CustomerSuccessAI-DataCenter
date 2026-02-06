# 📋 Config File Creation & Signal Analyst Confidence Analysis

## Question 1: Config File Creation Module

### 🎯 **Primary Module: `onboarding_api_v2_config_aware.py`**

**Location:** `kpi-dashboard/backend/onboarding_api_v2_config_aware.py`

**Purpose:** Complete onboarding flow that creates customers with proper configuration

---

### ✅ **Key Features:**

#### 1. **Config-Aware Customer Creation**
- **Endpoint:** `POST /api/onboarding/complete`
- **Functionality:**
  - Creates `Customer` record
  - Creates `CustomerConfig` with default settings
  - Generates config-aware CSV files
  - Validates uploads against config

**Request:**
```json
{
    "customer_name": "Company Name",
    "email": "user@company.com",
    "password": "password",
    "vertical": "dc2_s",
    "industry": "Technology"
}
```

**Response:**
```json
{
    "success": true,
    "customer_id": 123,
    "config": {
        "enabled_kpis": ["KPI1", "KPI2", ...],
        "pillar_weights": {...},
        "kpi_upload_mode": "account_rollup"
    }
}
```

#### 2. **CSV Validation Against Config**
- **Function:** `validate_csv_against_config(customer_id, csv_file)`
- **Checks:**
  - ✅ Validates CSV columns match required format
  - ✅ Compares KPIs in CSV vs enabled KPIs in config
  - ✅ Identifies disabled KPIs that will be filtered
  - ✅ Provides warnings for config mismatches
  - ✅ Calculates filter statistics

**Returns:**
```python
{
    "valid": bool,
    "enabled_kpis": int,
    "csv_kpis": int,
    "disabled_kpis": list,
    "warnings": list,
    "will_filter": bool,
    "details": {
        "total_records": int,
        "enabled_records": int,
        "filtered_records": int,
        "filter_percentage": str
    }
}
```

#### 3. **Config-Aware CSV Generation**
- Generates CSV files that respect `CustomerConfig`
- Only includes enabled KPIs
- Filters out disabled KPIs automatically

---

### 🔧 **Supporting Modules:**

#### **A. Master File API** (`master_file_api.py`)
**Purpose:** Upload master KPI framework Excel files

**Features:**
- **Endpoint:** `POST /api/master-file/upload`
- Extracts category weights from Excel "Health Score Components" sheet
- Maps component names to category weights:
  - Product Usage → Product Usage KPI
  - Support Engagement → Support KPI
  - Customer Sentiment → Customer Sentiment KPI
  - Business Outcomes → Business Outcomes KPI
  - Relationship Strength → Relationship Strength KPI
- Stores weights in `CustomerConfig.category_weights`
- **Endpoint:** `GET /api/master-file/weights` - Retrieves current weights

**Usage:**
```python
# Upload master file
POST /api/master-file/upload
Content-Type: multipart/form-data
file: <excel_file.xlsx>

# Response
{
    "status": "success",
    "category_weights": {
        "Product Usage KPI": 0.30,
        "Support KPI": 0.20,
        ...
    }
}
```

#### **B. DC2S Config API** (`dc2s_config_api.py`)
**Purpose:** Manage DC2_S specific configuration

**Features:**
- **GET `/api/dc2s/config/`** - Get current config
- **PUT `/api/dc2s/config/`** - Update config
- **GET `/api/dc2s/config/weight-history`** - Get weight change history
- **POST `/api/dc2s/config/validate`** - Validate config before saving

**Config Structure:**
```python
{
    "pillar_weights": {
        "AI": 0.25,
        "CH": 0.20,
        "DV": 0.15,
        "EX": 0.20,
        "OS": 0.20
    },
    "enabled_kpis": ["KPI1", "KPI2", ...],
    "kpi_weights": {
        "KPI1": 0.05,
        "KPI2": 0.03,
        ...
    },
    "kpi_overrides": {
        "KPI1": {
            "target": 85.0,
            "critical_range": [0, 50],
            "risk_range": [50, 70],
            "healthy_range": [70, 100]
        }
    },
    "kpi_definitions": {...}
}
```

#### **C. Config Loader Utility** (`utils/config_loader.py`)
**Purpose:** Load and manage customer configuration

**Features:**
- `ConfigLoader(customer_id)` - Load config for customer
- `get_enabled_kpis()` - Get list of enabled KPIs
- `get_pillar_weights()` - Get pillar weights
- `get_kpi_weights()` - Get KPI-level weights
- `validate_kpi(kpi_code)` - Check if KPI is enabled

#### **D. Config Validator** (`utils/config_validator.py`)
**Purpose:** Validate configuration before saving

**Features:**
- Validates pillar weights sum to 1.0
- Validates KPI weights within pillar
- Checks for duplicate KPIs
- Validates ranges (critical < risk < healthy)
- Returns detailed error messages

---

### 📊 **Config Creation Flow:**

```
1. Customer Registration
   ↓
2. POST /api/onboarding/complete
   ↓
3. Create CustomerConfig (default settings)
   ↓
4. [Optional] Upload Master File
   POST /api/master-file/upload
   ↓
5. Extract Category Weights
   ↓
6. Update CustomerConfig.category_weights
   ↓
7. [Optional] Customize Config
   PUT /api/dc2s/config/
   ↓
8. Validate Config
   POST /api/dc2s/config/validate
   ↓
9. Save Config
   ↓
10. Generate Config-Aware CSVs
```

---

## Question 2: Signal Analyst Tests & Confidence Scoring

### 🎯 **Primary Module: Signal Analyst API**

**Location:** `kpi-dashboard/backend/agents/signal_analyst_api.py`

**Endpoint:** `POST /api/signal-analyst/analyze`

---

### ✅ **Confidence Scoring Model:**

#### **1. PredictionConfidence Model** (`agents/models.py`)

```python
class PredictionConfidence(BaseModel):
    overall_confidence: float  # 0.0 to 1.0
    confidence_level: ConfidenceLevel  # VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW
    confidence_factors: Dict[str, float]  # What contributed to confidence
```

**Confidence Levels:**
- **VERY_HIGH:** 90%+ (`overall_confidence >= 0.90`)
- **HIGH:** 75-90% (`overall_confidence >= 0.75`)
- **MEDIUM:** 60-75% (`overall_confidence >= 0.60`)
- **LOW:** 40-60% (`overall_confidence >= 0.40`)
- **VERY_LOW:** <40% (`overall_confidence < 0.40`)

#### **2. SignalAnalystOutput Model**

**Key Fields for Confidence:**
```python
{
    "predicted_outcome": "churn" | "expansion" | "stable" | ...,
    "churn_probability": 0.0-100.0,
    "expansion_probability": 0.0-100.0,
    "health_score": 0.0-100.0,
    "confidence": {
        "overall_confidence": 0.85,
        "confidence_level": "high",
        "confidence_factors": {
            "signal_count": 0.9,
            "signal_quality": 0.8,
            "historical_match": 0.85,
            "data_completeness": 0.75
        }
    },
    "risk_drivers": [...],
    "growth_drivers": [...],
    "recommended_actions": [...]
}
```

---

### 🧪 **Existing Tests:**

#### **1. Test Run Analysis** (`test_run_analysis.py`)

**Location:** `kpi-dashboard/backend/test_run_analysis.py`

**Purpose:** End-to-end test of Signal Analyst API

**What it tests:**
- ✅ Authentication
- ✅ Account retrieval
- ✅ Signal Analyst API call
- ✅ Response validation
- ✅ Confidence score extraction
- ✅ Health score, churn/expansion probabilities

**Usage:**
```bash
python3 test_run_analysis.py
```

**Output:**
```
✅ Analysis completed successfully!
   Health Score: 72.5
   Churn Probability: 15.3%
   Expansion Probability: 45.2%
   Recommended Actions: 5
```

#### **2. Customer-Specific Tests**

**Location:** `kpi-dashboard/backend/verticals/customer{ID}-dc2_s/journey/scripts/phase5/test_signal_analyst.py`

**Example:** `customer120-dc2_s/journey/scripts/phase5/test_signal_analyst.py`

**What it tests:**
- ✅ Bootstrap weights loading
- ✅ KPI mapping validation
- ✅ Health score calculation
- ✅ Outcome prediction (churn/expansion/stable)
- ✅ Accuracy against actual milestones
- ✅ Confidence scoring

**Key Features:**
```python
class SignalAnalystTester:
    def predict_outcome(self, health_score, kpis):
        """Predict outcome based on health score and KPIs"""
        
        # Churn risk based on health
        if health_score < 40:
            churn_risk = 0.90
            predicted_outcome = 'churn'
        elif health_score < 55:
            churn_risk = 0.70
            predicted_outcome = 'at_risk'
        # ... more logic
        
        return {
            'outcome': predicted_outcome,
            'churn_risk': churn_risk,
            'expansion_prob': expansion_prob,
            'confidence': calculated_confidence
        }
```

**Test Metrics:**
- Baseline accuracy: 55-65% (with bootstrap weights)
- Target accuracy: 75-85% (after learning)
- Confidence correlation with accuracy

#### **3. Version-Specific Tests**

**Locations:**
- `test_signal_analyst_v2.py` - Version 2 schema
- `test_signal_analyst_v3.py` - Version 3 schema
- `test_signal_analyst_v4.py` - Version 4 schema (current)
- `test_signal_analyst_v4_smart_override.py` - Smart override logic

**What they test:**
- ✅ Schema validation
- ✅ Confidence score calculation
- ✅ Signal quality assessment
- ✅ Historical pattern matching
- ✅ Response parsing

---

### 📊 **Confidence Score Components:**

#### **1. Signal Count Factor**
```python
confidence_factors["signal_count"] = min(1.0, total_signals / 50)
# More signals = higher confidence (up to 50 signals)
```

#### **2. Signal Quality Factor**
```python
confidence_factors["signal_quality"] = average_similarity_score
# Higher similarity from Qdrant = higher confidence
```

#### **3. Historical Match Factor**
```python
confidence_factors["historical_match"] = matching_patterns / total_patterns
# More historical patterns match = higher confidence
```

#### **4. Data Completeness Factor**
```python
confidence_factors["data_completeness"] = available_kpis / enabled_kpis
# More KPIs available = higher confidence
```

#### **5. Overall Confidence Calculation**
```python
overall_confidence = (
    signal_count * 0.25 +
    signal_quality * 0.30 +
    historical_match * 0.25 +
    data_completeness * 0.20
)
```

---

### 🎯 **Using Confidence for Playbook Selection:**

#### **Current Implementation:**

**1. Playbook Recommendations API** (`playbook_recommendations_api.py`)

**Endpoint:** `POST /api/playbooks/recommendations/<playbook_id>`

**How it works:**
- Evaluates accounts against playbook triggers
- Calculates urgency score (not directly using Signal Analyst confidence)
- Sorts by urgency

**2. Signal Analyst → Playbook Integration (Recommended)**

**Proposed Flow:**
```python
# 1. Run Signal Analyst
signal_result = POST /api/signal-analyst/analyze
{
    "account_id": 123,
    "analysis_type": "comprehensive"
}

# 2. Extract confidence and predictions
confidence = signal_result["confidence"]["overall_confidence"]
confidence_level = signal_result["confidence"]["confidence_level"]
predicted_outcome = signal_result["predicted_outcome"]
churn_probability = signal_result["churn_probability"]

# 3. Select playbook based on confidence + outcome
if confidence_level in ["VERY_HIGH", "HIGH"]:
    if predicted_outcome == "churn" and churn_probability > 70:
        playbook = "renewal-safeguard"
    elif predicted_outcome == "expansion" and expansion_probability > 60:
        playbook = "expansion-timing"
    elif health_score < 50:
        playbook = "sla-stabilizer"
```

**Confidence Thresholds for Playbook Selection:**
- **VERY_HIGH (90%+):** Use prediction with full confidence
- **HIGH (75-90%):** Use prediction, but add manual review flag
- **MEDIUM (60-75%):** Use prediction with caution, require CSM review
- **LOW (40-60%):** Don't auto-select playbook, show recommendations
- **VERY_LOW (<40%):** Don't use for playbook selection, gather more data

---

### 📝 **CSM Helper Artifacts Generation:**

#### **1. QBR (Quarterly Business Review) Generation**

**Based on Signal Analyst Output:**
```python
def generate_qbr(signal_result):
    return {
        "account_health": signal_result["health_score"],
        "key_insights": signal_result["key_insights"],
        "risk_drivers": signal_result["risk_drivers"],
        "growth_opportunities": signal_result["growth_drivers"],
        "recommended_actions": signal_result["recommended_actions"],
        "confidence": signal_result["confidence"]["confidence_level"],
        "next_steps": generate_next_steps(signal_result)
    }
```

#### **2. Email Generation**

**Templates based on confidence:**
- **HIGH confidence + Churn risk:** Urgent intervention email
- **HIGH confidence + Expansion:** Upsell opportunity email
- **MEDIUM confidence:** Standard check-in email
- **LOW confidence:** Data gathering email

**Example:**
```python
def generate_email(signal_result):
    confidence = signal_result["confidence"]["confidence_level"]
    outcome = signal_result["predicted_outcome"]
    
    if confidence == "VERY_HIGH" and outcome == "churn":
        template = "urgent_churn_prevention"
        urgency = "immediate"
    elif confidence == "HIGH" and outcome == "expansion":
        template = "expansion_opportunity"
        urgency = "high"
    # ... more logic
    
    return {
        "template": template,
        "subject": generate_subject(signal_result),
        "body": generate_body(signal_result),
        "urgency": urgency,
        "recommended_actions": signal_result["recommended_actions"]
    }
```

---

### ✅ **Recommended Test Suite for Confidence Scoring:**

#### **1. Confidence Accuracy Test**
```python
def test_confidence_accuracy():
    """Test that confidence scores correlate with prediction accuracy"""
    # Run predictions on historical data
    # Compare confidence to actual outcomes
    # Verify: HIGH confidence = higher accuracy
```

#### **2. Playbook Selection Test**
```python
def test_playbook_selection_by_confidence():
    """Test playbook selection based on confidence thresholds"""
    # Test VERY_HIGH confidence → auto-select playbook
    # Test MEDIUM confidence → show recommendations
    # Test LOW confidence → don't auto-select
```

#### **3. CSM Artifact Generation Test**
```python
def test_artifact_generation():
    """Test QBR and email generation from Signal Analyst output"""
    # Generate QBR from signal result
    # Generate email from signal result
    # Verify content matches confidence level
```

---

## 📋 **Summary:**

### **Config File Creation:**
- **Primary Module:** `onboarding_api_v2_config_aware.py`
- **Features:** Customer creation, config validation, CSV generation
- **Supporting:** Master file upload, DC2S config API, config loader/validator

### **Signal Analyst Confidence:**
- **Primary Module:** `agents/signal_analyst_api.py`
- **Confidence Model:** `PredictionConfidence` with 5 levels
- **Tests:** `test_run_analysis.py`, customer-specific tests, version tests
- **Use Cases:** Playbook selection, QBR generation, email templates

### **Next Steps:**
1. ✅ Use existing Signal Analyst confidence scores
2. ⚠️ Integrate confidence into playbook selection logic
3. ⚠️ Create CSM artifact generators (QBR, emails)
4. ⚠️ Add confidence-based test suite

---

## 🔗 **Related Files:**

- `backend/onboarding_api_v2_config_aware.py` - Config creation
- `backend/master_file_api.py` - Master file upload
- `backend/dc2s_config_api.py` - DC2S config management
- `backend/agents/signal_analyst_api.py` - Signal Analyst API
- `backend/agents/models.py` - Confidence models
- `backend/test_run_analysis.py` - E2E test
- `backend/playbook_recommendations_api.py` - Playbook selection
- `backend/utils/config_loader.py` - Config utilities
- `backend/utils/config_validator.py` - Config validation
