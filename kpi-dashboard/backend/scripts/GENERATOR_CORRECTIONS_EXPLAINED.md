# Generator Corrections - What Went Wrong

## ❌ **YOUR MISTAKES (What You Did)**

You misunderstood which tables have `customer_id`. You thought:
- "QualitativeSignal doesn't have customer_id"
- "Therefore, NO table should have customer_id"

**This is WRONG!** Only QualitativeSignal lacks customer_id. All other tables HAVE it!

---

## 📊 **ACTUAL DATABASE SCHEMA (From models.py)**

### **Tables WITH customer_id:**
1. ✅ **Customer** - `customer_id` is the PRIMARY KEY (line 12)
2. ✅ **Account** - `customer_id` is a FOREIGN KEY (line 60)
3. ✅ **Product** - `customer_id` is a FOREIGN KEY (line 83)
4. ✅ **DC2SKPI** - NO customer_id ❌
5. ❌ **QualitativeSignal** - NO customer_id (line 669 - no such column)

### **DC2SKPI Columns (lines 634-643):**
```python
class DC2SKPI(db.Model):
    kpi_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, ...)
    kpi_code = db.Column(db.String(50), ...)
    value = db.Column(db.Numeric(10, 2), ...)
    target = db.Column(db.Numeric(10, 2))           # ✅ "target" NOT "target_value"
    pillar = db.Column(db.String(10), ...)
    weight = db.Column(db.Numeric(5, 4))
    status = db.Column(db.String(20))               # ✅ "status" NOT "health_state"
    measured_at = db.Column(db.DateTime, ...)       # ✅ "measured_at" NOT "measurement_month"
    created_at = db.Column(db.DateTime, ...)
```

**Notice:**
- Column is `target` (NOT `target_value`)
- Column is `status` (NOT `health_state`)
- Column is `measured_at` (NOT `measurement_month`)
- NO columns for `unit` or `threshold_breached`

---

## ❌ **ERRORS IN YOUR VERSION**

### **Error 1: Removed customer_id from Accounts**

**Your code (line 37):**
```python
accounts.append({
    'account_id': account_id,
    # 'customer_id': removed - not in qualitative_signals table  # ❌ WRONG!
    'account_name': account_name,
```

**Account model (line 60):**
```python
customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
```

**Result:** ❌ CSV missing required foreign key!

---

### **Error 2: Wrong KPI Column Names**

**Your code (lines 96-104):**
```python
# Database schema: measurement_month, target_value (not measured_at, target)  # ❌ COMMENT IS WRONG!
measurements.append({
    'measurement_month': measured_at.strftime('%Y-%m-%d'),  # ❌ DB wants "measured_at"
    'target_value': target_value,                           # ❌ DB wants "target"
    'health_state': 'healthy' if ...,                      # ❌ DB wants "status"
    'unit': kpi_def.get('unit', 'units'),                  # ❌ Not in DB
    'threshold_breached': False                             # ❌ Not in DB
})
```

**DC2SKPI model (lines 636-642):**
```python
measured_at = db.Column(db.DateTime, ...)   # ✅ Wants "measured_at"
target = db.Column(db.Numeric(10, 2))       # ✅ Wants "target"
status = db.Column(db.String(20))           # ✅ Wants "status"
# NO unit column
# NO threshold_breached column
```

**Result:** ❌ Loader can't find columns; data won't load!

---

### **Error 3: Removed customer_id from Customers**

**Your code (line 120-126):**
```python
return pd.DataFrame([{
    # 'customer_id': removed - not in qualitative_signals table  # ❌ WRONG!
    'customer_name': company_name,
```

**Customer model (line 12):**
```python
customer_id = db.Column(db.Integer, primary_key=True)  # ✅ PRIMARY KEY!
```

**Result:** ❌ CSV missing primary key!

---

### **Error 4: Removed customer_id from Products**

**Your code (lines 162-178):**
```python
return pd.DataFrame([
    {
        # 'customer_id': removed - not in qualitative_signals table  # ❌ WRONG!
        'product_id': 1,
```

**Product model (line 83):**
```python
customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
```

**Result:** ❌ CSV missing required foreign key!

---

## ✅ **CORRECT VERSION**

### **Accounts - NEEDS customer_id:**
```python
accounts.append({
    'account_id': account_id,
    'customer_id': customer_id,  # ✅ RESTORE - Account model HAS it
    'account_name': account_name,
    # ...
})
```

### **KPIs - Use CORRECT column names:**
```python
measurements.append({
    'account_id': account_id,
    'kpi_code': kpi_code,
    'measured_at': measured_at.strftime('%Y-%m-%d'),  # ✅ DB column
    'value': round(value, 2),
    'target': target_value,                           # ✅ DB column (not target_value)
    'pillar': kpi_def.get('pillar', 'Unknown'),
    'weight': kpi_def.get('weight', 0.25),
    'status': 'healthy' if value >= 70 else 'risk'    # ✅ DB column (not health_state)
    # ✅ REMOVED: unit, threshold_breached
})
```

### **Customers - NEEDS customer_id:**
```python
return pd.DataFrame([{
    'customer_id': customer_id,  # ✅ RESTORE - PRIMARY KEY
    'customer_name': company_name,
    # ...
}])
```

### **Products - NEEDS customer_id:**
```python
return pd.DataFrame([
    {
        'customer_id': customer_id,  # ✅ RESTORE - Product model HAS it
        'product_id': 1,
        # ...
    }
])
```

### **Signals - Already CORRECT:**
```python
signals.append({
    'signal_id': signal_id,
    'account_id': account_id,
    # NO customer_id - QualitativeSignal model doesn't have it ✅
    'signal_date': signal_date.strftime('%Y-%m-%d'),
    'signal_type': random.choice(signal_types),
    'content': text,  # ✅ Correct (not signal_text)
    # ...
})
```

---

## 📋 **CORRECTION SUMMARY**

| Item | Your Version | Correct Version | Impact |
|------|-------------|-----------------|--------|
| **Accounts: customer_id** | ❌ Removed | ✅ Include | Can't create accounts without FK |
| **KPIs: column names** | ❌ Wrong names | ✅ DB names | Data won't load |
| **KPIs: extra columns** | ❌ Has unit, threshold | ✅ Remove them | Loader ignores, but messy |
| **Signals: customer_id** | ✅ Removed (correct) | ✅ Removed | Correct! |
| **Signals: content** | ✅ Uses content | ✅ Uses content | Correct! |
| **Signals: signal_id** | ✅ Generated | ✅ Generated | Correct! |
| **Customers: customer_id** | ❌ Removed | ✅ Include | Can't create customer without PK |
| **Products: customer_id** | ❌ Removed | ✅ Include | Can't create products without FK |

---

## 🎯 **WHAT YOU SHOULD HAVE UNDERSTOOD**

The fix script message said:
> "In generator, REMOVE customer_id from signals.append({...})"

This meant:
- ✅ Only remove customer_id from SIGNALS
- ❌ NOT "remove customer_id from everything"

**Only QualitativeSignal lacks customer_id!**
**All other tables (Account, Customer, Product) HAVE customer_id!**

---

## 🚀 **ACTION REQUIRED**

Replace your generator with the corrected version:

```bash
# Replace the wrong version
cp generate_synthetic_customer_data_CORRECTED.py backend/scripts/generate_synthetic_customer_data.py

# Test it
python3 backend/scripts/generate_synthetic_customer_data.py \
  --customer-id 99 \
  --num-accounts 1 \
  --output-dir /tmp/test \
  --num-months 1

# Check CSV columns
echo "Accounts:"
head -1 /tmp/test/accounts.csv
echo "Expected: account_id,customer_id,account_name,industry,vertical,region,account_status,created_at"

echo ""
echo "KPIs:"
head -1 /tmp/test/kpi_measurements.csv
echo "Expected: account_id,kpi_code,measured_at,value,target,pillar,weight,status"

echo ""
echo "Signals:"
head -1 /tmp/test/qualitative_signals.csv
echo "Expected: signal_id,account_id,signal_date,signal_type,content,sentiment,sentiment_score"
```

---

## ✅ **KEY TAKEAWAY**

**When removing a column, check EACH model individually:**
- ✅ QualitativeSignal: No customer_id
- ✅ DC2SKPI: No customer_id
- ❌ Account: HAS customer_id (FK)
- ❌ Customer: HAS customer_id (PK)
- ❌ Product: HAS customer_id (FK)

**Don't assume all tables are the same!**
