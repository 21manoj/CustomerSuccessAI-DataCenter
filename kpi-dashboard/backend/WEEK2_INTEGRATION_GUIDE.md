# DC2_S Week 2: Google Sheets Integration
## Complete Implementation Guide

**Status:** Ready to implement  
**Estimated Time:** 2-3 hours  
**Prerequisites:** Week 1 complete (DC2_S vertical installed)

---

## 📦 **What's Included**

### **Files Created:**
1. `sample_accounts.py` - 10 realistic DC2_S pilot accounts with KPI data
2. `google_sheets_generator.py` - Creates master Google Sheet
3. `sync_pipeline.py` - Bidirectional sync (Sheets ↔ Postgres)
4. `SETUP_GOOGLE_AUTH.md` - Google API authentication guide

### **What You'll Build:**
- ✅ Master Google Sheet with 10 pilot accounts
- ✅ 51 total tabs (1 index + 5 tabs × 10 accounts)
- ✅ Automated sync every 15 minutes
- ✅ Partner-based access control
- ✅ Real-time KPI updates
- ✅ Automated health score calculations

---

## 🚀 **Quick Start (30 minutes)**

### **Step 1: Set Up Google Authentication** (15 min)

Follow the detailed guide:
```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend
cat SETUP_GOOGLE_AUTH.md
```

**Summary:**
1. Enable Google Sheets API
2. Create service account
3. Download credentials JSON
4. Test authentication

**Result:** You should have `integrations/google-credentials.json`

---

### **Step 2: Copy Week 2 Files** (5 min)

```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend

# Create integrations directory
mkdir -p integrations

# Copy the 4 files you downloaded to integrations/
cp ~/Downloads/sample_accounts.py integrations/
cp ~/Downloads/google_sheets_generator.py integrations/
cp ~/Downloads/sync_pipeline.py integrations/
cp ~/Downloads/SETUP_GOOGLE_AUTH.md integrations/

# Verify
ls -la integrations/
```

**Should show:**
```
sample_accounts.py
google_sheets_generator.py
sync_pipeline.py
google-credentials.json
SETUP_GOOGLE_AUTH.md
```

---

### **Step 3: Install Dependencies** (2 min)

```bash
cd backend
pip3 install gspread oauth2client
```

---

### **Step 4: Generate Master Sheet** (5 min)

```bash
cd backend/integrations

# Generate the master sheet
python3 google_sheets_generator.py google-credentials.json

# Or with custom name:
python3 google_sheets_generator.py google-credentials.json --name "DC2_S Pilot - Q1 2026"
```

**What happens:**
1. Creates new Google Sheet
2. Generates Index tab with 10 accounts
3. Creates 5 tabs for each account:
   - `{id}_KPIs` - Current KPI values
   - `{id}_Health` - Health score breakdown
   - `{id}_Communications` - Communication log
   - `{id}_Actions` - Recommended actions
   - `{id}_Profile` - Account details

**Output:**
```
DC2_S GOOGLE SHEETS GENERATOR
============================================================
Accounts to create: 10
Tabs per account: 5
Total tabs: 51 (including index)
============================================================

✅ Authenticated with Google Sheets API
✅ Created master sheet: DC2_S Master - Pilot Accounts
   URL: https://docs.google.com/spreadsheets/d/ABC123.../edit

✅ Created Index tab

📊 Creating tabs for account 1/10: CloudScale AI Labs
   ✅ Created tab: 1_KPIs
   ✅ Created tab: 1_Health
   ✅ Created tab: 1_Communications
   ✅ Created tab: 1_Actions
   ✅ Created tab: 1_Profile

[... 9 more accounts ...]

✅ Master sheet created successfully!
   URL: https://docs.google.com/spreadsheets/d/ABC123.../edit
   Total tabs: 51

🎉 Sheet generation complete!
```

---

### **Step 5: Share Sheet with Service Account** (1 min)

1. **Copy the sheet URL** from the output
2. **Open it in browser**
3. **Click "Share"** (top right)
4. **Add service account email:**
   - Get from: `cat google-credentials.json | grep client_email`
   - Should be: `dc2s-sync-bot@....iam.gserviceaccount.com`
5. **Set to "Editor"**
6. **Uncheck "Notify people"**
7. **Click "Share"**

---

### **Step 6: Test the Sheet** (2 min)

Open the sheet and verify:
- ✅ Index tab shows all 10 accounts
- ✅ Each account has 5 tabs
- ✅ KPIs tab has values populated
- ✅ Health tab shows scores
- ✅ Profile tab shows account details

---

## 🔄 **Set Up Sync Pipeline** (15 minutes)

### **Option A: Run Sync Once (Test)**

```bash
cd backend/integrations

# Get your sheet URL from Step 4 output
SHEET_URL="https://docs.google.com/spreadsheets/d/ABC123.../edit"

# Run one-time sync
python3 sync_pipeline.py google-credentials.json "$SHEET_URL" --once
```

**What it does:**
1. Reads KPI values from sheet
2. Updates database
3. Recalculates health scores
4. Writes back to sheet

---

### **Option B: Run Continuous Sync**

```bash
cd backend/integrations

SHEET_URL="https://docs.google.com/spreadsheets/d/ABC123.../edit"

# Run continuous sync (every 15 minutes)
python3 sync_pipeline.py google-credentials.json "$SHEET_URL" --interval 15
```

**Output:**
```
DC2_S CONTINUOUS SYNC PIPELINE
============================================================
Sync interval: 15 minutes
Started: 2026-01-01 10:00:00
============================================================

🔄 Starting sync for 10 accounts...
   Direction: both
   Time: 2026-01-01 10:00:00

📊 Syncing account 1...
   ✅ Synced 12 KPIs from sheet to DB for account 1
   ✅ Synced 12 KPIs to sheet for account 1
   ✅ Synced health score (88.5) to sheet for account 1
   ✅ Synced 3 actions to sheet for account 1

[... 9 more accounts ...]

✅ Sync complete!

⏰ Next sync at: 10:15:00
   Sleeping for 15 minutes...
```

**To stop:** Press `Ctrl+C`

---

### **Option C: Run as Background Service**

```bash
cd backend/integrations

SHEET_URL="https://docs.google.com/spreadsheets/d/ABC123.../edit"

# Run in background
nohup python3 sync_pipeline.py google-credentials.json "$SHEET_URL" --interval 15 > sync.log 2>&1 &

# Get process ID
echo $! > sync.pid

# Check logs
tail -f sync.log

# Stop sync
kill $(cat sync.pid)
```

---

## 📊 **Understanding the 10 Pilot Accounts**

### **Account Distribution:**

**By Health Status:**
- 🟢 **Healthy (3):** CloudScale AI Labs, Nexus Research, Quantum Computing
- 🟡 **Risk (4):** DataVision Analytics, ML Solutions, IntelliTech, Neural Networks
- 🔴 **Critical (3):** StartupAI Ventures, Legacy Systems, Budget AI Labs

**By Phase:**
- **Deployment (3):** IntelliTech, Neural Networks, StartupAI, Budget AI
- **Performance (4):** DataVision, ML Solutions, Legacy Systems, Nexus
- **Excellence (3):** CloudScale, Quantum Computing, Nexus

**By Partner Tier:**
- **Direct (3):** Nexus, IntelliTech, StartupAI
- **Tier 1 (3):** CloudScale, Quantum, Neural Networks
- **Tier 2 (4):** DataVision, ML Solutions, Legacy, Budget AI

---

## 🔍 **Testing the Integration**

### **Test 1: Manual KPI Update**

1. **Open the sheet**
2. **Go to account 1 (CloudScale AI Labs) → KPIs tab**
3. **Change GPU utilization** (cell C4) from `78.0` to `82.0`
4. **Wait for next sync** (max 15 minutes)
5. **Check Health tab** - score should update automatically

---

### **Test 2: Database Update**

If you have your database connected:

```python
from verticals.dc2_s import calculate_overall_health

# Update a KPI in your database
# (Your existing KPI update code here)

# Wait for sync
# Check sheet - should reflect new value and recalculated health
```

---

### **Test 3: Partner Access Control**

**Tier 1 Partner View:**
- Can see: CloudScale, Quantum, Neural Networks
- Cannot see: Direct or Tier 2 accounts

**Tier 2 VAR View:**
- Can see: Only their assigned accounts
- Example: VAR-005 sees only DataVision Analytics

**Implementation:**
- Filter by `var_partner_id` in sheet
- Or create separate sheets per partner tier

---

## 🎯 **Sync Pipeline Architecture**

### **Bidirectional Flow:**

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Google Sheets  │ ◄────── │  Sync Pipeline   │ ◄────── │   Postgres DB   │
│                 │         │                  │         │                 │
│  - User edits   │ ──────► │  - Reads both    │ ──────► │  - App writes   │
│  - KPI values   │         │  - Resolves      │         │  - KPI updates  │
│  - Manual data  │         │  - Calculates    │         │  - Auto-calc    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │                            │
        │                            ▼                            │
        │                   Every 15 minutes                      │
        │                   Last-write-wins                       │
        └────────────────────────────────────────────────────────┘
```

### **What Gets Synced:**

**Sheets → Database:**
- ✅ KPI values (manual edits)
- ✅ Communication logs
- ✅ Action status updates

**Database → Sheets:**
- ✅ KPI values (from app)
- ✅ Health scores (recalculated)
- ✅ Pillar scores
- ✅ Recommended actions (auto-generated)

**Calculated in Sync:**
- ✅ Overall health
- ✅ Pillar scores
- ✅ Alert triggers
- ✅ Status (healthy/risk/critical)

---

## 🔐 **Partner Access Implementation**

### **Method 1: Filtered Sheets**

Create separate sheets per partner tier:
```bash
python3 google_sheets_generator.py google-credentials.json \
    --name "DC2_S - Tier 1 Partners" \
    --filter partner_tier=tier_1
```

### **Method 2: Protected Ranges**

In Google Sheets:
1. **Data → Protected sheets and ranges**
2. **Set range** (e.g., accounts 1-3 for Tier 1)
3. **Restrict who can edit**

### **Method 3: Share Individual Tabs**

For VARs - share only their account tabs:
- VAR-005 gets access to tab `4_*` only

---

## 📈 **Sample Data Overview**

### **Account 1: CloudScale AI Labs** (Flagship)
- **Status:** 🟢 Healthy (88.5/100)
- **GPUs:** 64 × H100
- **Value:** $15M
- **Phase:** Excellence
- **Key Metrics:**
  - GPU Utilization: 78% ✅
  - RMA Rate: 0.8% ✅
  - Expansion Probability: 85% ✅

### **Account 8: StartupAI Ventures** (At-Risk)
- **Status:** 🔴 Critical (42.0/100)
- **GPUs:** 8 × A100
- **Value:** $2M
- **Phase:** Deployment
- **Key Metrics:**
  - Time-to-First-Workload: 28 days ❌
  - RMA Rate: 3.2% ❌
  - GPU Utilization: 42% ❌

---

## 🐛 **Troubleshooting**

### **Sync Not Working**

```bash
# Check if service account has access
cat google-credentials.json | grep client_email

# Test authentication
python3 -c "import gspread; from oauth2client.service_account import ServiceAccountCredentials; creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', ['https://spreadsheets.google.com/feeds']); print('✅ Auth OK')"
```

### **Sheet URL Issues**

Make sure URL format is:
```
https://docs.google.com/spreadsheets/d/SHEET_ID/edit
```

NOT:
```
https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0
```

### **Permission Denied**

1. Check sheet is shared with service account
2. Service account has "Editor" permissions
3. Google Sheets API is enabled

---

## ✅ **Week 2 Checklist**

- [ ] Google Sheets API enabled
- [ ] Service account created
- [ ] Credentials downloaded
- [ ] Dependencies installed (`gspread`, `oauth2client`)
- [ ] Master sheet generated (51 tabs)
- [ ] Sheet shared with service account
- [ ] Sync tested (one-time)
- [ ] Continuous sync running
- [ ] All 10 accounts visible
- [ ] Health scores calculating
- [ ] Partner access configured

---

## 🎉 **Success Criteria**

You've successfully completed Week 2 when:

1. ✅ Master sheet is created with all 10 accounts
2. ✅ Each account has 5 tabs (KPIs, Health, Communications, Actions, Profile)
3. ✅ Sync pipeline runs without errors
4. ✅ Manual KPI edits sync to database
5. ✅ Health scores update automatically
6. ✅ Recommended actions appear in Actions tab
7. ✅ Partner access is configured

---

## 📊 **Next Steps: Week 3+**

Now that you have Google Sheets working, you can:

### **Week 3-6: Build Missing Agents**
- Playbook Planner Agent
- Expansion Opportunity Agent
- Portfolio Triage Agent
- Narrative Generator Agent

### **Week 7-8: Learning Loop**
- Feedback collection from sheets
- Weight adjustment based on outcomes
- Convergence tracking

### **Week 9-10: Playbooks**
- Automated playbook execution
- Human approval workflows

---

## 💡 **Pro Tips**

1. **Start with read-only sync** to test safely
2. **Use `--once` flag** for testing before continuous sync
3. **Monitor API quotas** in Google Cloud Console
4. **Back up your sheet** before enabling write sync
5. **Test with 1-2 accounts first** before all 10
6. **Use named ranges** in sheets for easier sync

---

## 🆘 **Getting Help**

If stuck:
1. Check `sync.log` for error details
2. Verify Google API quotas
3. Test authentication separately
4. Start with `--once` sync to debug

---

**Week 2 Complete!** 🎊

You now have:
- ✅ 10 pilot accounts in Google Sheets
- ✅ Real-time bidirectional sync
- ✅ Automated health calculations
- ✅ Partner access control ready

**Ready for Week 3?** 🚀
