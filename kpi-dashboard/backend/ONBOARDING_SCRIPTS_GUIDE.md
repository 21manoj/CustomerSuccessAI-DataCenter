# Onboarding Scripts Comparison Guide

## 📋 Overview

You now have **3 different onboarding scripts** - choose based on your needs:

| Script | Purpose | Complexity | When to Use |
|--------|---------|------------|-------------|
| **quick_onboard.py** | Ultra-simple, just run it | ⭐ Minimal | Quick demos, testing |
| **simple_onboard_customer.py** | Production onboarding | ⭐⭐ Simple | Real customer setup |
| **test_onboarding_complete_e2e_api_v3.py** | Full testing suite | ⭐⭐⭐⭐ Complex | QA, validation, CI/CD |

---

## 🚀 Script 1: quick_onboard.py (FASTEST)

**Purpose:** Get a customer up and running in 10 seconds

### Usage:
```bash
# Defaults: Auto-generated name, 15 KPIs, 3 accounts, 12 months
python3 quick_onboard.py

# With company name
python3 quick_onboard.py "Acme Corp"

# Custom KPI count
python3 quick_onboard.py "Test Co" --kpis 20
```

### What it does:
✅ Creates customer  
✅ Creates CustomerConfig (N enabled KPIs)  
✅ Creates 3 accounts (Production, Staging, Development)  
✅ Generates 12 months of KPI data (config-aware)  
✅ Calculates health scores  
✅ **DONE!**

### Output:
```
🚀 Onboarding: Acme Corp
   KPIs: 15, Accounts: 3, Months: 12
   ✅ Customer ID: 124
   ✅ Config: 15 KPIs enabled
   ✅ Accounts: 3 created
   ✅ KPI Data: 540 records
   ✅ Scores: Calculated for 3 accounts

✅ DONE! Customer 124 ready to use

Customer ID: 124
Dashboard: http://localhost:3000/customer/124
API: curl http://localhost:5059/api/journey/<account_id>
```

### Best for:
- ✅ Quick demos
- ✅ Testing during development
- ✅ When you just need a customer NOW

---

## 🎯 Script 2: simple_onboard_customer.py (PRODUCTION)

**Purpose:** Full-featured onboarding with all options

### Usage:
```bash
# Basic
python3 simple_onboard_customer.py --name "Acme Corp"

# All options
python3 simple_onboard_customer.py \
  --name "Enterprise Corp" \
  --industry "Healthcare" \
  --accounts 10 \
  --months 24 \
  --enabled-kpis 25

# Skip score calculation (faster)
python3 simple_onboard_customer.py --name "Test Co" --skip-scores
```

### What it does:
✅ Creates customer  
✅ Creates CustomerConfig (configurable KPIs)  
✅ Creates N accounts (configurable)  
✅ Generates M months of KPI data (config-aware)  
✅ Saves to database in batches  
✅ Calculates health scores (optional)  
✅ Detailed logging and statistics  

### Output:
```
======================================================================
SIMPLE CUSTOMER ONBOARDING (CONFIG-AWARE)
======================================================================
Company: Acme Corp
Industry: Technology
Accounts: 10
Months: 24
Enabled KPIs: 25
======================================================================

[14:23:01] Creating customer: Acme Corp
[14:23:01] ✅ Customer created with ID: 125
[14:23:01] Creating CustomerConfig with 25 enabled KPIs...
[14:23:02] ✅ Config created with 25 enabled KPIs
[14:23:02]    Enabled KPIs: AI-KPI1, AI-KPI2, AI-KPI3, CH-KPI1, CH-KPI2...
[14:23:02] Creating 10 accounts...
[14:23:02] ✅ Created 10 accounts
[14:23:02]    • 12501: Acme Corp-Production
[14:23:02]    • 12502: Acme Corp-Staging
           ... (8 more)
[14:23:03] Generating KPI data for 24 months...
[14:23:05] ✅ Generated 6000 KPI measurements (config-aware)
[14:23:05]    Accounts: 10
[14:23:05]    KPIs: 25
[14:23:05]    Months: 24
[14:23:05]    Total: 10 × 25 × 24 = 6000
[14:23:05] Saving 6000 records to database...
[14:23:05]    Saved batch 1: 1000 records
[14:23:06]    Saved batch 2: 1000 records
           ... (4 more)
[14:23:10] ✅ Saved 6000 records to database
[14:23:10] Calculating health scores...
[14:23:10]    Calculating for month: 2025-12-01
[14:23:12] ✅ Calculated scores for 10 accounts
[14:23:12]    • Acme Corp-Production: 88.5 (excellent)
[14:23:12]    • Acme Corp-Staging: 72.3 (good)
           ... (8 more)

======================================================================
✅ ONBOARDING COMPLETE!
======================================================================
Customer ID: 125
Company: Acme Corp
Accounts: 10
Enabled KPIs: 25
KPI Records: 6000

Next steps:
  • View in dashboard: http://localhost:3000/customer/125
  • Test API: curl http://localhost:5059/api/journey/<account_id>
  • Upload more data: POST /api/upload
======================================================================
```

### Best for:
- ✅ Production customer onboarding
- ✅ When you need specific configurations
- ✅ Large-scale data generation
- ✅ Custom scenarios

---

## 🧪 Script 3: test_onboarding_complete_e2e_api_v3.py (TESTING)

**Purpose:** Complete end-to-end testing with validation

### Usage:
```bash
python3 test_onboarding_complete_e2e_api_v3.py
```

### What it does:
✅ Creates customer via API  
✅ Creates CustomerConfig  
✅ Provisions directory structure  
✅ Generates config-aware CSVs  
✅ **Validates everything at each step**  
✅ Comprehensive logging  
✅ Generates JSON test report  
✅ Returns exit code (0 = pass, 1 = fail)  

### Output:
```
======================================================================
E2E ONBOARDING TEST V3 - CONFIG-AWARE CSV GENERATION
======================================================================
Started: 2026-01-24T14:25:00
Log: logs/onboarding_tests/onboarding_e2e_v3_20260124_142500.log

V3 NEW FEATURES:
  🎯 Config-aware CSV generation
  🎯 Dynamic KPI selection from CustomerConfig
  🎯 No hardcoded 35 KPIs

✅ Server running

======================================================================
Starting: 1. Create Customer via API
======================================================================
Creating customer: E2E Test Corp V3 1737738300
✅ Customer created: 126
✅ Completed in 1.23s

======================================================================
Starting: 2. Provision Directory
======================================================================
✅ Directory: /tmp/test_customer_126
✅ Completed in 0.05s

======================================================================
Starting: 3. Generate Config-Aware CSV Files
======================================================================
Generating CONFIG-AWARE CSV files...
🎯 V3: Only generating enabled KPIs from CustomerConfig
🎯 V3: Generating config-aware KPI measurements
   Found 15 enabled KPIs in config
   Sample KPIs: AI-KPI1, AI-KPI2, AI-KPI3, CH-KPI1, CH-KPI2...
   Generated 1800 config-aware measurements
✅ Generated 5 CSV files
   KPI measurements: 1800
   🎯 Config-aware: Only enabled KPIs generated
✅ Completed in 2.45s

======================================================================
✅ TEST PASSED!
======================================================================
Customer ID: 126
CSVs: /tmp/test_customer_126

V3 Features Validated:
  ✅ Config-aware CSV generation
  ✅ Only enabled KPIs generated
  ✅ Dynamic from database config

Report: logs/onboarding_tests/report_customer_126_20260124_142500.json
======================================================================
```

### Best for:
- ✅ Automated testing (CI/CD)
- ✅ Validating changes
- ✅ QA processes
- ✅ When you need test reports

---

## 📊 Comparison Table

| Feature | quick_onboard.py | simple_onboard_customer.py | test_v3.py |
|---------|------------------|----------------------------|------------|
| **Speed** | ⚡⚡⚡ Fastest (~5s) | ⚡⚡ Fast (~15s) | ⚡ Slower (~30s) |
| **Customization** | Minimal | Full | None |
| **Logging** | Basic | Detailed | Comprehensive |
| **Validation** | None | Basic | Full |
| **Test Reports** | ❌ No | ❌ No | ✅ Yes (JSON) |
| **Exit Codes** | ❌ No | ✅ Yes | ✅ Yes |
| **Config-Aware** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Production Ready** | ⚠️ Demo only | ✅ Yes | ⚠️ Testing only |

---

## 🎯 Decision Tree

```
Need onboarding?
│
├─ Just testing/demo?
│  └─ Use: quick_onboard.py ⚡
│
├─ Real customer setup?
│  │
│  ├─ Default settings OK?
│  │  └─ Use: quick_onboard.py ⚡
│  │
│  └─ Need custom config?
│     └─ Use: simple_onboard_customer.py 🎯
│
└─ Need validation/testing?
   └─ Use: test_onboarding_complete_e2e_api_v3.py 🧪
```

---

## 💡 Examples

### Example 1: Quick Demo
```bash
# Just show someone the system
python3 quick_onboard.py "Demo Corp"
# → Customer ready in 5 seconds
```

### Example 2: Production Customer
```bash
# Proper customer onboarding
python3 simple_onboard_customer.py \
  --name "Acme Corporation" \
  --industry "Manufacturing" \
  --accounts 20 \
  --months 24 \
  --enabled-kpis 30
# → Full setup with logging
```

### Example 3: CI/CD Pipeline
```bash
# In your CI/CD script
python3 test_onboarding_complete_e2e_api_v3.py
if [ $? -eq 0 ]; then
  echo "Tests passed"
else
  echo "Tests failed"
  exit 1
fi
```

---

## 🔑 Key Differences

### Configuration:
- **quick_onboard.py**: Hardcoded defaults, minimal options
- **simple_onboard_customer.py**: Full command-line control
- **test_v3.py**: Auto-generated test names/IDs

### Output:
- **quick_onboard.py**: Minimal (5 lines)
- **simple_onboard_customer.py**: Detailed (30+ lines)
- **test_v3.py**: Comprehensive (100+ lines + JSON report)

### Error Handling:
- **quick_onboard.py**: Basic try-catch
- **simple_onboard_customer.py**: Detailed error messages
- **test_v3.py**: Full validation + rollback

### Database Operations:
- **quick_onboard.py**: Single commit
- **simple_onboard_customer.py**: Batched commits
- **test_v3.py**: Transactional with validation

---

## ✅ Recommendations

**For Development:**
```bash
python3 quick_onboard.py "DevTest"
```

**For Production:**
```bash
python3 simple_onboard_customer.py --name "Real Customer" --accounts 10
```

**For CI/CD:**
```bash
python3 test_onboarding_complete_e2e_api_v3.py
```

**For Load Testing:**
```bash
# Create 100 customers quickly
for i in {1..100}; do
  python3 quick_onboard.py "LoadTest-$i"
done
```

---

## 📝 Summary

You have **3 tools for 3 different needs**:

1. **quick_onboard.py** - When you need it NOW (⚡ 5 seconds)
2. **simple_onboard_customer.py** - When you need it RIGHT (🎯 production)
3. **test_v3.py** - When you need it VALIDATED (🧪 testing)

**All three are config-aware and generate only enabled KPIs!** ✅

Choose based on your use case! 🚀
