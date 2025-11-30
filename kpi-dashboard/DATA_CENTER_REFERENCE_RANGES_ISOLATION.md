# Data Center Customer - Reference Ranges Isolation

## ✅ **YES - Completely Separate from Other Customers**

The data center customer's KPI reference ranges are **fully isolated** from other customers' ranges through the multi-tenant architecture.

---

## 🔒 Isolation Mechanism

### 1. **Database Schema**

The `KPIReferenceRange` model uses `customer_id` to isolate ranges:

```python
class KPIReferenceRange(db.Model):
    customer_id = db.Column(db.Integer, 
                           db.ForeignKey('customers.customer_id', ondelete='CASCADE'), 
                           nullable=True)  # NULL = system default
    kpi_name = db.Column(db.String, nullable=False)
    
    # Composite unique constraint: same kpi_name allowed for different customers
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'kpi_name', name='uq_customer_kpi_name'),
        db.Index('idx_ref_range_customer_kpi', 'customer_id', 'kpi_name'),
    )
```

**Key Points:**
- ✅ `customer_id` can be `NULL` (system defaults) or a specific customer ID
- ✅ Unique constraint on `(customer_id, kpi_name)` allows same KPI name for different customers
- ✅ Each customer can have their own ranges for the same KPI

---

### 2. **Seeding Script Isolation**

The `seed_data_center_reference_ranges.py` script **explicitly sets** `customer_id`:

```python
ref_range = KPIReferenceRange(
    customer_id=customer.customer_id,  # ← Data Center customer's ID
    kpi_name=range_data['kpi_name'],
    # ... other fields ...
)
```

**Result:**
- ✅ Data center ranges have `customer_id = <data_center_customer_id>`
- ✅ Other customers' ranges have their own `customer_id`
- ✅ System defaults have `customer_id = NULL`

---

### 3. **API Endpoint Isolation**

The `/api/kpi-reference-ranges` endpoint **filters by customer_id**:

```python
@kpi_reference_ranges_api.route('/api/kpi-reference-ranges', methods=['GET'])
def get_kpi_reference_ranges():
    customer_id = get_current_customer_id()  # From auth middleware
    
    # Get customer-specific ranges
    customer_ranges = KPIReferenceRange.query.filter_by(
        customer_id=customer_id  # ← Only this customer's ranges
    ).all()
    
    # Get system defaults (customer_id = NULL)
    system_ranges = KPIReferenceRange.query.filter_by(
        customer_id=None
    ).all()
```

**Result:**
- ✅ Data center customer only sees their own ranges
- ✅ Other customers only see their own ranges
- ✅ No cross-customer data leakage

---

### 4. **Health Score Engine Isolation**

The `HealthScoreEngine` respects customer isolation:

```python
@staticmethod
def get_kpi_reference_range_from_db(kpi_name: str, customer_id: int = None) -> Optional[Dict]:
    # First try customer-specific range
    if customer_id:
        ref_range = KPIReferenceRange.query.filter_by(
            customer_id=customer_id,
            kpi_name=kpi_name
        ).first()
        if ref_range:
            return format_range(ref_range)
    
    # Fallback to system default
    ref_range = KPIReferenceRange.query.filter_by(
        customer_id=None,
        kpi_name=kpi_name
    ).first()
    
    if ref_range:
        return format_range(ref_range)
    
    # Final fallback to config file
    return get_kpi_reference_range(kpi_name)
```

**Result:**
- ✅ Data center customer uses their own ranges
- ✅ Other customers use their own ranges (or system defaults)
- ✅ No mixing of ranges between customers

---

## 📊 Database Structure Example

### Scenario: 3 Customers

```
kpi_reference_ranges table:

| range_id | customer_id | kpi_name                    | critical_min | ... |
|----------|-------------|-----------------------------|--------------|-----|
| 1        | NULL        | daily_invocations           | 0            | ... | ← System default
| 2        | NULL        | error_rate_pct              | 0            | ... | ← System default
| 3        | 1           | daily_invocations           | 100          | ... | ← Customer 1 custom
| 4        | 1           | error_rate_pct              | 1.0          | ... | ← Customer 1 custom
| 5        | 6           | daily_invocations           | 956          | ... | ← Data Center (customer_id=6)
| 6        | 6           | invocation_velocity_change_pct | -15        | ... | ← Data Center (customer_id=6)
| 7        | 6           | days_since_last_invocation   | 8            | ... | ← Data Center (customer_id=6)
| ...      | ...         | ...                         | ...          | ... |
```

**Isolation:**
- ✅ Customer 1 (ID=1) sees ranges 3, 4, and system defaults (1, 2)
- ✅ Data Center (ID=6) sees ranges 5, 6, 7, and system defaults (1, 2)
- ✅ Customer 2 (ID=2) sees only system defaults (1, 2)
- ✅ **No customer sees another customer's ranges**

---

## 🔍 Verification Queries

### Check Data Center Ranges Only

```sql
SELECT kpi_name, critical_min, critical_max, risk_min, risk_max, healthy_min, healthy_max
FROM kpi_reference_ranges
WHERE customer_id = 6;  -- Data Center customer ID
```

### Check Other Customers' Ranges

```sql
SELECT customer_id, kpi_name, critical_min, critical_max
FROM kpi_reference_ranges
WHERE customer_id IS NOT NULL
ORDER BY customer_id, kpi_name;
```

### Check System Defaults

```sql
SELECT kpi_name, critical_min, critical_max
FROM kpi_reference_ranges
WHERE customer_id IS NULL;
```

---

## 🎯 Data Center Customer Specific Ranges

### What Gets Created

When you run `seed_data_center_reference_ranges.py`, it creates:

**10 KPI Reference Ranges** with `customer_id = <data_center_customer_id>`:

1. `daily_invocations` - Data Center specific ranges
2. `invocations_30d` - Data Center specific ranges
3. `invocation_velocity_change_pct` - Data Center specific ranges
4. `monthly_spend` - Data Center specific ranges
5. `days_since_last_invocation` - Data Center specific ranges
6. `error_rate_pct` - Data Center specific ranges
7. `p95_latency_ms` - Data Center specific ranges
8. `avg_execution_time_sec` - Data Center specific ranges
9. `cold_start_pct` - Data Center specific ranges
10. `health_score` - Data Center specific ranges

**All with:**
- ✅ `customer_id` set to data center customer's ID
- ✅ Unique to data center customer
- ✅ Not visible to other customers
- ✅ Not affecting other customers' calculations

---

## 🚨 Important Notes

### 1. **Health Score Calculation**

**Data Center Customer:**
- Uses **regression formula** (does NOT use reference ranges)
- Formula: `health_score = 52.14 + (velocity_change × 0.416) - ...`

**Other Customers:**
- Use **reference-range-based calculation** (uses reference ranges)
- Calculated via `HealthScoreEngine` with reference ranges

**Result:** Different calculation methods = Complete isolation ✅

---

### 2. **Reference Ranges Usage**

**Data Center Customer:**
- Reference ranges used for:
  - ✅ **Alerts** (playbook triggers)
  - ✅ **Visualization** (color-coding)
  - ✅ **KPI status** (healthy/risk/critical)

**Other Customers:**
- Reference ranges used for:
  - ✅ **Health score calculation**
  - ✅ **Alerts** (playbook triggers)
  - ✅ **Visualization** (color-coding)
  - ✅ **KPI status** (healthy/risk/critical)

**Result:** Same infrastructure, different data = Complete isolation ✅

---

### 3. **API Access**

When data center customer calls `/api/kpi-reference-ranges`:
- ✅ Returns only data center's ranges
- ✅ Falls back to system defaults if KPI not found
- ✅ Never returns other customers' ranges

When other customer calls `/api/kpi-reference-ranges`:
- ✅ Returns only their ranges
- ✅ Falls back to system defaults if KPI not found
- ✅ Never returns data center's ranges

**Result:** API-level isolation ✅

---

## ✅ Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Database Isolation** | ✅ Yes | `customer_id` column with unique constraint |
| **Seeding Script** | ✅ Yes | Sets `customer_id` explicitly |
| **API Endpoints** | ✅ Yes | Filters by `customer_id` from auth |
| **Health Score Engine** | ✅ Yes | Respects `customer_id` parameter |
| **Cross-Customer Access** | ✅ No | Impossible due to constraints |
| **Data Mixing** | ✅ No | Each customer has separate rows |

---

**Conclusion:** The data center customer's reference ranges are **completely separate** from other customers' ranges. The multi-tenant architecture ensures full isolation at the database, API, and application levels.

**Last Updated**: January 2025  
**Status**: ✅ Fully Isolated

