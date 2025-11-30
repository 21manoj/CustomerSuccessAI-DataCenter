# Data Center Customer Onboarding Plan

## File Analysis: `serverless_model_cs_platform.xlsx`

### File Structure
- **Sheets**: 2
  - `Dashboard`: Summary metrics (18 rows)
  - `Customers`: Customer/account data (35 rows, 21 columns)

### Data Content

#### Customer/Account Data (35 accounts)
**Columns Available**:
1. **Identifiers**:
   - `customer_id` (e.g., "SRVL-3007")
   - `company_name` (e.g., "Elastic AI Corp")
   - `signup_date`

2. **Business Metrics**:
   - `monthly_spend`
   - `contract_value_annual`
   - `customer_segment` (Production Service, Development/Testing)
   - `csm_assigned`

3. **Usage/Performance KPIs**:
   - `daily_invocations`
   - `invocations_30d`
   - `avg_execution_time_sec`
   - `cold_start_pct`
   - `p95_latency_ms`
   - `error_rate_pct`
   - `invocation_velocity_change_pct`
   - `days_since_last_invocation`

4. **Health Indicators**:
   - `health_score` (0-10 scale)
   - `churn_risk` (High, Medium, Low)
   - `expansion_potential` (High, Medium, Low)

5. **Metadata**:
   - `industry` (Financial Services, E-commerce, etc.)
   - `use_case` (Model Inference, Scientific Computing, etc.)
   - `gpu_type_primary` (L4, L40S, etc.)

---

## Onboarding Approach

### **Step 1: Business Outcomes & Goals** 🎯

**Pre-filled from File Analysis**:
- **Industry**: Technology (Data Center/Cloud Services)
- **Company Size**: Likely Enterprise (based on contract values)
- **Number of Accounts**: 35

**Recommended Business Goals** (based on data available):
- ✅ **Reduce Churn** (churn_risk data available)
- ✅ **Drive Product Adoption** (invocation metrics available)
- ✅ **Improve Customer Satisfaction** (health_score, error_rate available)
- ✅ **Expand Revenue** (expansion_potential data available)
- ✅ **Reduce Support Costs** (error_rate, latency metrics)

**Action**: Customer selects goals, system pre-fills industry/size/account count

---

### **Step 2: KPI Category Weights** ⚖️

**Recommended Weights** (based on data center/serverless focus):

1. **Product Usage KPI**: **35%** (High)
   - *Rationale*: Usage metrics (invocations, execution time) are core to this business
   - *KPIs*: Daily Invocations, Invocation Velocity, Days Since Last Invocation

2. **Business Outcomes KPI**: **25%** (High)
   - *Rationale*: Revenue (monthly_spend, contract_value) is critical
   - *KPIs*: Monthly Spend, Contract Value, Expansion Potential

3. **Support KPI**: **20%** (Medium)
   - *Rationale*: Error rates and latency impact satisfaction
   - *KPIs*: Error Rate, P95 Latency, Cold Start Percentage

4. **Customer Sentiment KPI**: **15%** (Medium)
   - *Rationale*: Health score and churn risk indicate sentiment
   - *KPIs*: Health Score, Churn Risk

5. **Relationship Strength KPI**: **5%** (Low)
   - *Rationale*: Less relevant for serverless/platform model
   - *KPIs*: CSM Assigned (if tracked)

**Action**: Customer adjusts sliders, system suggests these defaults

---

### **Step 3: KPI Reference Ranges** 📊

**KPI Mapping from File to Our System**:

| File Column | Our KPI Name | Category | Critical | At Risk | Healthy |
|-------------|--------------|----------|----------|---------|---------|
| `daily_invocations` | Daily Invocations | Product Usage | < 100 | 100-500 | > 500 |
| `invocations_30d` | Monthly Invocations | Product Usage | < 3,000 | 3,000-15,000 | > 15,000 |
| `avg_execution_time_sec` | Average Execution Time | Support | > 500 | 200-500 | < 200 |
| `cold_start_pct` | Cold Start Percentage | Support | > 50% | 20-50% | < 20% |
| `p95_latency_ms` | P95 Latency | Support | > 500,000 | 100,000-500,000 | < 100,000 |
| `error_rate_pct` | Error Rate | Support | > 10% | 5-10% | < 5% |
| `monthly_spend` | Monthly Spend | Business Outcomes | < $1,000 | $1,000-$10,000 | > $10,000 |
| `contract_value_annual` | Annual Contract Value | Business Outcomes | < $50,000 | $50,000-$200,000 | > $200,000 |
| `health_score` | Health Score | Customer Sentiment | < 3 | 3-6 | > 6 |
| `churn_risk` | Churn Risk | Customer Sentiment | High | Medium | Low |
| `expansion_potential` | Expansion Potential | Business Outcomes | Low | Medium | High |
| `invocation_velocity_change_pct` | Invocation Velocity Change | Product Usage | < -50% | -50% to 0% | > 0% |
| `days_since_last_invocation` | Days Since Last Invocation | Product Usage | > 30 | 7-30 | < 7 |

**Action**: 
- System pre-populates ranges based on data center industry benchmarks
- Customer can adjust if needed
- For calculated fields (churn_risk, expansion_potential), map text values to numeric scores

---

### **Step 4: Account & Profile Setup** 👥

**Data Transformation Required**:

#### A. Extract Account Data
```python
# Map file columns to Account model
accounts = []
for row in df.iterrows():
    account = {
        'account_name': row['company_name'],
        'external_account_id': row['customer_id'],  # SRVL-3007
        'revenue': row['contract_value_annual'],
        'industry': row['industry'],
        'region': 'Unknown',  # Not in file, may need manual entry
        'account_status': 'active',  # Assume active if in file
        'account_tier': row['customer_segment'],  # Production Service, etc.
        'assigned_csm': row['csm_assigned']
    }
    accounts.append(account)
```

#### B. Create Profile Metadata
```python
profile_metadata = {
    'account_id_external': row['customer_id'],
    'industry': row['industry'],
    'use_case': row['use_case'],
    'gpu_type_primary': row['gpu_type_primary'],
    'signup_date': row['signup_date'],
    'customer_segment': row['customer_segment']
}
```

**Action**:
1. **Option 1**: Upload this file directly
   - System detects it's not in standard format
   - Offers to transform it
   - Shows preview of transformed data
   - Customer confirms

2. **Option 2**: Manual transformation
   - Customer downloads template
   - Maps columns manually
   - Uploads transformed file

**Recommended**: **Option 1** - Auto-transform with preview

---

### **Step 5: KPI Data Upload** 📈

**Challenge**: File has **account-level metrics**, not **KPI structure**

**Solution**: Transform to KPI format

#### Transformation Logic:

```python
def transform_to_kpi_format(customer_file):
    """
    Transform data center customer file to KPI format
    """
    kpis = []
    
    for _, row in customer_file.iterrows():
        account_name = row['company_name']
        account_id = row['customer_id']
        
        # Product Usage KPIs
        kpis.append({
            'account_name': account_name,
            'category': 'Product Usage KPI',
            'kpi_parameter': 'Daily Invocations',
            'data': row['daily_invocations'],
            'impact_level': 'High',
            'measurement_frequency': 'Daily'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Product Usage KPI',
            'kpi_parameter': 'Monthly Invocations',
            'data': row['invocations_30d'],
            'impact_level': 'High',
            'measurement_frequency': 'Monthly'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Product Usage KPI',
            'kpi_parameter': 'Invocation Velocity Change',
            'data': row['invocation_velocity_change_pct'],
            'impact_level': 'Medium',
            'measurement_frequency': 'Monthly'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Product Usage KPI',
            'kpi_parameter': 'Days Since Last Invocation',
            'data': row['days_since_last_invocation'],
            'impact_level': 'High',
            'measurement_frequency': 'Daily'
        })
        
        # Support KPIs
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'Average Execution Time',
            'data': row['avg_execution_time_sec'],
            'impact_level': 'High',
            'measurement_frequency': 'Daily'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'Cold Start Percentage',
            'data': row['cold_start_pct'],
            'impact_level': 'Medium',
            'measurement_frequency': 'Daily'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'P95 Latency',
            'data': row['p95_latency_ms'],
            'impact_level': 'High',
            'measurement_frequency': 'Daily'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Support KPI',
            'kpi_parameter': 'Error Rate',
            'data': row['error_rate_pct'],
            'impact_level': 'Critical',
            'measurement_frequency': 'Daily'
        })
        
        # Business Outcomes KPIs
        kpis.append({
            'account_name': account_name,
            'category': 'Business Outcomes KPI',
            'kpi_parameter': 'Monthly Spend',
            'data': row['monthly_spend'],
            'impact_level': 'High',
            'measurement_frequency': 'Monthly'
        })
        
        kpis.append({
            'account_name': account_name,
            'category': 'Business Outcomes KPI',
            'kpi_parameter': 'Annual Contract Value',
            'data': row['contract_value_annual'],
            'impact_level': 'High',
            'measurement_frequency': 'Annual'
        })
        
        # Customer Sentiment KPIs
        kpis.append({
            'account_name': account_name,
            'category': 'Customer Sentiment KPI',
            'kpi_parameter': 'Health Score',
            'data': row['health_score'],
            'impact_level': 'Critical',
            'measurement_frequency': 'Monthly'
        })
        
        # Map churn_risk to numeric (High=1, Medium=2, Low=3)
        churn_score = {'High': 1, 'Medium': 2, 'Low': 3}.get(row['churn_risk'], 2)
        kpis.append({
            'account_name': account_name,
            'category': 'Customer Sentiment KPI',
            'kpi_parameter': 'Churn Risk Score',
            'data': churn_score,
            'impact_level': 'Critical',
            'measurement_frequency': 'Monthly'
        })
        
        # Map expansion_potential to numeric (Low=1, Medium=2, High=3)
        expansion_score = {'Low': 1, 'Medium': 2, 'High': 3}.get(row['expansion_potential'], 2)
        kpis.append({
            'account_name': account_name,
            'category': 'Business Outcomes KPI',
            'kpi_parameter': 'Expansion Potential Score',
            'data': expansion_score,
            'impact_level': 'Medium',
            'measurement_frequency': 'Quarterly'
        })
    
    return kpis
```

**Result**: 
- 35 accounts × ~13 KPIs = **~455 KPI records**
- Organized by category
- Ready for upload

**Action**:
1. Customer uploads `serverless_model_cs_platform.xlsx`
2. System detects non-standard format
3. System offers transformation
4. Shows preview: "Will create 35 accounts and 455 KPIs"
5. Customer confirms
6. System transforms and uploads

---

## Implementation Plan

### Phase 1: File Format Detection & Transformation

**New Endpoint**: `POST /api/onboarding/transform-customer-file`
```python
@onboarding_api.route('/api/onboarding/transform-customer-file', methods=['POST'])
def transform_customer_file():
    """
    Transform non-standard customer file to our format
    """
    file = request.files.get('file')
    
    # Detect file type
    if file.filename.endswith('.xlsx'):
        df = pd.read_excel(file)
    elif file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    
    # Detect format (data center, CRM export, etc.)
    format_type = detect_customer_file_format(df)
    
    # Transform based on format
    if format_type == 'data_center_serverless':
        accounts = extract_accounts_from_data_center(df)
        kpis = transform_to_kpi_format(df)
        profile_metadata = extract_profile_metadata(df)
    
    # Return preview
    return jsonify({
        'format_detected': format_type,
        'accounts_count': len(accounts),
        'kpis_count': len(kpis),
        'preview': {
            'accounts': accounts[:3],  # First 3
            'kpis': kpis[:10]  # First 10
        }
    })
```

### Phase 2: Onboarding Wizard Integration

**Modified Step 4**: Add "Upload Customer File" option
- Option A: Upload standard template
- Option B: Upload customer file (auto-transform)
- Option C: Manual entry

**Modified Step 5**: Auto-populate from transformed data
- If Step 4 used transformation, skip manual upload
- Show: "KPI data ready from Step 4 transformation"
- Option to upload additional files

---

## Data Quality Checks

### Validation Rules:

1. **Account Data**:
   - ✅ `company_name` required
   - ✅ `customer_id` unique
   - ⚠️ `region` missing (may need manual entry)
   - ✅ `industry` present

2. **KPI Data**:
   - ✅ All numeric KPIs have valid values
   - ✅ Text KPIs (churn_risk, expansion_potential) mapped correctly
   - ⚠️ Missing some standard KPIs (can add defaults)

3. **Completeness**:
   - ✅ 35 accounts
   - ✅ ~13 KPIs per account
   - ⚠️ Some accounts may have null values (handle gracefully)

---

## Expected Outcomes

### After Onboarding:

1. **35 Accounts** created
   - With profile metadata (industry, use_case, GPU type)
   - With external_account_id mapping

2. **~455 KPIs** created
   - Organized by 4 categories
   - With reference ranges configured
   - Ready for health score calculation

3. **Health Scores** calculated
   - Based on configured weights
   - Using reference ranges
   - Displayed in dashboard

4. **RAG System** ready
   - Can answer questions about accounts
   - Can provide insights on churn risk
   - Can recommend playbooks

---

## Next Steps

1. **Implement File Format Detector** for data center files
2. **Create Transformation Logic** (as shown above)
3. **Add Preview/Confirm UI** in onboarding wizard
4. **Test with this file** to validate transformation
5. **Handle Edge Cases** (null values, missing fields)

---

**Status**: Design Complete - Ready for Implementation  
**File Analyzed**: `serverless_model_cs_platform.xlsx`  
**Accounts**: 35  
**KPIs to Create**: ~455


