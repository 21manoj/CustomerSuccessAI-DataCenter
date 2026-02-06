# Onboarding Wizard Integration Guide

## Current Status

**❌ NOT YET WIRED:** The onboarding wizard (frontend) and `_template` provisioning system (backend) are separate. Here's how to connect them.

---

## Integration Architecture

```
┌─────────────────────────────────┐
│  Onboarding Wizard (Frontend)   │
│  - Collects all onboarding data │
│  - Validates inputs             │
│  - Calls API on completion      │
└────────────┬────────────────────┘
             │
             │ POST /api/onboarding/complete
             ▼
┌─────────────────────────────────┐
│   Onboarding API (Backend)      │
│   - Creates Customer in DB      │
│   - Creates User account        │
│   - Saves configuration         │
│   - Triggers provisioning       │
└────────────┬────────────────────┘
             │
             │ (if vertical = datacenter)
             ▼
┌─────────────────────────────────┐
│   provision_dc_customer.py      │
│   - Reads _template/            │
│   - Creates customer{N}-dc2_s/  │
│   - Parameterizes all files     │
└─────────────────────────────────┘
```

---

## What Was Created

### 1. **Frontend Wizard Components** ✅
- `OnboardingWizard.main.tsx` - Main orchestrator
- Step components (Step0-Step8)
- Type definitions and configs

### 2. **Backend Provisioning** ✅
- `_template/` directory (Data Center template)
- `provision_dc_customer.py` (provisioner script)
- `create_template.py` (template creator)

### 3. **Integration API** ✅ (NEW)
- `onboarding_api.py` - Connects wizard to provisioning
- `/api/onboarding/complete` - Main endpoint
- `/api/onboarding/validate-domain` - Domain validation
- `/api/onboarding/preview-provisioning` - Preview what will be created

---

## How It Works

### Step-by-Step Flow

1. **User completes wizard** → All data collected in frontend

2. **Wizard calls API**:
   ```typescript
   // In OnboardingWizard.main.tsx - handleComplete()
   const response = await fetch('/api/onboarding/complete', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify(onboardingData)
   });
   ```

3. **API processes request**:
   - Creates `Customer` record in database
   - Creates `User` record (admin)
   - Saves `CustomerConfig` with wizard data
   - Creates `PlaybookTrigger` entries from events

4. **If vertical = "datacenter"**:
   - Calls `provision_datacenter_customer(customer_id)`
   - Which runs `provision_dc_customer.py` script
   - Creates `customer{N}-dc2_s/` directory from `_template/`
   - Parameterizes all files with customer_id

5. **If vertical = "saas"**:
   - Database-only creation (no file system provisioning)
   - Uses shared database tables

6. **Team invitations** (optional):
   - Creates user records for team members
   - Sends invitation emails (if implemented)

---

## Required Changes

### 1. Update Main App to Register API

```python
# In app.py or your main Flask app file
from onboarding_api import onboarding_api

app.register_blueprint(onboarding_api)
```

### 2. Update Wizard to Call API

```typescript
// In OnboardingWizard.main.tsx
const handleComplete = async () => {
  const onboardingData: OnboardingData = {
    account,
    business,
    pillars,
    events,
    criteria,
    sources,
    team,
    skip_training
  };

  try {
    const response = await fetch('/api/onboarding/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(onboardingData)
    });

    if (response.ok) {
      const result = await response.json();
      onComplete(onboardingData);
      // Redirect to dashboard or show success message
    } else {
      const error = await response.json();
      alert(`Onboarding failed: ${error.error}`);
    }
  } catch (error) {
    alert(`Network error: ${error.message}`);
  }
};
```

### 3. Add Wizard Config to CustomerConfig Model

```python
# In models.py - add wizard_config column to CustomerConfig
class CustomerConfig(db.Model):
    # ... existing fields ...
    wizard_config = db.Column(db.JSON, nullable=True)  # Store full wizard data
```

Or use existing JSON column and merge with category_weights.

---

## Testing the Integration

### 1. Test API Endpoint Directly

```bash
curl -X POST http://localhost:5000/api/onboarding/complete \
  -H "Content-Type: application/json" \
  -d '{
    "account": {
      "email": "test@company.com",
      "password": "Test1234!",
      "company_domain": "company",
      "subscription_plan": "professional"
    },
    "business": {
      "company_name": "Test Company",
      "vertical": "datacenter",
      "industry": "SaaS",
      "segments": ["Enterprise"]
    },
    "pillars": [...],
    "events": [...],
    "criteria": {...},
    "sources": [],
    "team": []
  }'
```

### 2. Verify Provisioning

After API call, check:
- Database: `SELECT * FROM customers WHERE customer_name = 'Test Company';`
- File System: `ls -la verticals/customer{N}-dc2_s/`
- Files should have correct `customer_id` parameterized

---

## What Happens for Each Vertical

### Data Center Vertical
1. ✅ Customer created in database
2. ✅ User account created
3. ✅ Configuration saved
4. ✅ **File system provisioned from `_template/`**
   - Creates `customer{N}-dc2_s/` directory
   - All scripts parameterized with customer_id
   - Ready for data loading

### SaaS Vertical
1. ✅ Customer created in database
2. ✅ User account created
3. ✅ Configuration saved
4. ❌ **No file system provisioning** (uses shared tables)
   - All data in database
   - No customer-specific directory structure

---

## Next Steps

1. **Register the API blueprint** in your Flask app
2. **Update CustomerConfig model** to store wizard_config (if needed)
3. **Test the API endpoint** with sample data
4. **Update wizard frontend** to call the API
5. **Test full flow** from wizard → API → provisioning

---

## Files Created for Integration

- ✅ `kpi-dashboard/backend/onboarding_api.py` - Integration API
- ✅ `OnboardingWizard.main.tsx` - Frontend wizard (needs API call added)
- ✅ Documentation (this file)

---

## Summary

The wizard and template are now connected via `onboarding_api.py`. When a user completes the wizard:

1. **Frontend** sends all data to `/api/onboarding/complete`
2. **API** creates database records and configuration
3. **If Data Center:** API calls provisioner to create file system from `_template/`
4. **If SaaS:** Database-only (no file system provisioning)

**Status:** ✅ Integration code ready - needs to be wired into main app
