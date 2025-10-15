# 🎯 How to Use Playbooks - Step-by-Step Guide

## ✅ **Issue Resolution**

### **Problem**: "Zero accounts showing" and "Don't see triggers in Settings"

### **Solutions**:

---

## 🚀 **Part 1: Using Playbooks with Account Selection**

### **Step 1: Navigate to Playbooks Tab**
1. Login to your dashboard
2. Click the **"Playbooks"** tab in the sidebar
3. You should see 5 playbook cards

### **Step 2: Start a Playbook**
1. Click **"Start Playbook"** button on any playbook card (e.g., VoC Sprint 🎤)
2. **Account Selector Modal** will appear
3. You'll see:
   - "All Accounts" option at the top
   - List of your 25 accounts with details:
     - Account name
     - Industry • Region • Revenue
     - Status badge (Active/At Risk)

### **Step 3: Select Account**
1. **Option A**: Click **"All Accounts"** to run playbook for all accounts
2. **Option B**: Click a **specific account** to run playbook for that account only
3. Modal closes automatically
4. Success message appears

### **Step 4: View Active Execution**
1. Scroll down to **"Active Executions"** section
2. You'll see:
   ```
   🎤 VoC Sprint
   TechCorp Industries - Execution a69d1e69
   [Progress: 0/12 steps]
   [Step buttons...]
   ```
3. Account name is displayed prominently

### **Troubleshooting Account List**:

If you see **zero accounts**:

**Check 1**: Verify accounts exist in database
```bash
curl -s http://localhost:5059/api/accounts -H "X-Customer-ID: 1" | python3 -m json.tool
```

**Expected**: Should return array of 25 accounts

**Check 2**: Open browser console (F12)
- Look for message: "Loaded accounts: 25"
- Check for any error messages

**Check 3**: Verify customer ID
- The Playbooks component uses `customerId` from session
- Make sure you're logged in
- Check session.customer_id is set

---

## ⚙️ **Part 2: Configuring Trigger Settings**

### **Step 1: Open Advanced Settings**
1. Navigate to **"Settings"** tab in sidebar
2. Look for button labeled **"Advanced Settings"** (top right)
3. Click **"Advanced Settings"** button
4. Settings Modal opens

### **Step 2: Scroll to Playbook Triggers**
**Important**: You need to **SCROLL DOWN** in the Settings modal!

The Settings modal contains multiple sections:
1. Feature Toggles (top)
2. System Status
3. **KPI Reference Ranges**
4. **🎯 Playbook Triggers** ← **SCROLL HERE**

### **Step 3: View Playbook Documentation**
Once you've scrolled to "🎯 Playbook Triggers", you'll see:

**Documentation Panel**:
```
📚 Available Playbooks & Triggers

🎤 VoC Sprint
   Triggers: NPS < 10, CSAT < 3.6, Churn Risk ≥ 30%, Health Drop ≥ 10 pts
   Purpose: Surface value gaps and convert to executive-backed actions

🚀 Activation Blitz
   Triggers: Adoption < 60, Active Users < 50, DAU/MAU < 25%
   Purpose: Compress time-to-value and drive user engagement

⚡ SLA Stabilizer - Configuration coming soon
🛡️ Renewal Safeguard - Configuration coming soon  
📈 Expansion Timing - Configuration coming soon
```

### **Step 4: Edit VoC Sprint Triggers**
Below the documentation, you'll see:

```
🎤 VoC Sprint Triggers

┌─────────────────────────────────────────┐
│ NPS Threshold: [    10    ]             │ ← Edit this
│ Trigger if NPS below this value         │
│                                          │
│ CSAT Threshold: [   3.6   ]             │ ← Edit this
│ Trigger if CSAT below this value        │
│                                          │
│ Churn Risk Threshold: [  0.30  ]        │ ← Edit this
│ Trigger if churn risk above this value  │
│                                          │
│ Health Score Drop: [    10    ]         │ ← Edit this
│ Trigger if health score drops by this   │
│                                          │
│ Churn Mentions: [     2     ]           │ ← Edit this
│ Trigger if this many churn mentions     │
│                                          │
│ [✓] Auto-Trigger Enabled                │ ← Toggle this
│                                          │
│   [Save VoC Triggers] [Test Triggers]   │
└─────────────────────────────────────────┘
```

### **Step 5: Edit Activation Blitz Triggers**
Scroll down a bit more to see:

```
🚀 Activation Blitz Triggers

┌─────────────────────────────────────────┐
│ Adoption Index: [    60    ]            │ ← Edit this
│ Active Users: [    50    ]              │ ← Edit this
│ DAU/MAU: [   0.25   ]                   │ ← Edit this
│ [✓] Unused Feature Check                │ ← Toggle this
│ Target Features: [Feature X, Feature Y] │ ← Edit this
│ [✓] Auto-Trigger Enabled                │ ← Toggle this
│                                          │
│  [Save Activation Triggers] [Test]      │
└─────────────────────────────────────────┘
```

### **Step 6: Save and Test**

**To Save Changes**:
1. Edit any values you want to change
2. Click **"Save VoC Triggers"** or **"Save Activation Triggers"**
3. Success message appears
4. Settings are persisted to database

**To Test Triggers**:
1. Click **"Test Triggers"** button
2. Backend evaluates triggers against all accounts
3. Returns list of accounts that meet trigger conditions
4. Success message shows: "Trigger test completed: VoC Sprint triggered for 3 account(s)"

---

## 🔍 **Troubleshooting: "I don't see triggers in Settings"**

### **Issue**: Triggers not visible in Settings modal

**Solution Steps**:

**1. Make sure you clicked "Advanced Settings"**:
   - In Settings tab, look for blue button "Advanced Settings" (top right)
   - Click it to open the Settings modal

**2. Scroll down in the modal**:
   - The modal has multiple sections
   - Playbook Triggers are **after** "KPI Reference Ranges"
   - **You must scroll down** to see them

**3. Look for the🎯 icon**:
   - Section title: "🎯 Playbook Triggers"
   - Can't miss the target emoji!

**4. Check modal height**:
   - Modal uses `max-h-[90vh] overflow-y-auto`
   - Should be scrollable
   - Try scrolling with mouse wheel or scrollbar

**5. Verify modal is fully loaded**:
   - Wait for "Loading..." to finish
   - Check browser console for errors
   - Press F12 and look for React errors

---

## 📊 **Visual Location Guide**

### **Settings Tab Layout**:
```
Settings & Configuration
┌────────────────────────────────────┐
│ [Advanced Settings] ← Click this!  │
└────────────────────────────────────┘

Master KPI Framework Configuration
Upload Configuration
```

### **Settings Modal (After clicking Advanced Settings)**:
```
╔═══════════════════════════════════════╗
║ System Settings                  [×]  ║
╠═══════════════════════════════════════╣
║                                        ║
║ 🔧 Feature Toggles                    ║
║ ├─ RAG System: [●] On                ║
║ └─ Advanced Analytics: [●] On         ║
║                                        ║
║ 📊 System Status                      ║
║                                        ║
║ 📊 KPI Reference Ranges               ║
║                                        ║
║ ↓↓↓ SCROLL DOWN ↓↓↓                   ║
║                                        ║
║ 🎯 Playbook Triggers ← HERE!          ║
║                                        ║
║ 📚 Available Playbooks & Triggers     ║
║ 🎤 VoC Sprint                         ║
║ 🚀 Activation Blitz                   ║
║                                        ║
║ 🎤 VoC Sprint Triggers                ║
║ ┌──────────────────────────┐          ║
║ │ NPS Threshold: [10]      │          ║
║ │ CSAT Threshold: [3.6]    │          ║
║ │ ... (more fields)        │          ║
║ │ [Save] [Test]            │          ║
║ └──────────────────────────┘          ║
║                                        ║
║ 🚀 Activation Blitz Triggers          ║
║ ┌──────────────────────────┐          ║
║ │ Adoption Index: [60]     │          ║
║ │ Active Users: [50]       │          ║
║ │ ... (more fields)        │          ║
║ │ [Save] [Test]            │          ║
║ └──────────────────────────┘          ║
║                                        ║
║          [Close]                       ║
╚═══════════════════════════════════════╝
```

---

## 🎯 **Quick Test Checklist**

### **Accounts in Playbooks**:
- [ ] Navigate to Playbooks tab
- [ ] Click "Start Playbook" on any playbook
- [ ] Account selector modal opens
- [ ] See "All Accounts" option
- [ ] See list of 25 accounts
- [ ] Click an account
- [ ] See account name in Active Executions

### **Trigger Settings**:
- [ ] Navigate to Settings tab
- [ ] Click "Advanced Settings" button (top right)
- [ ] Settings modal opens
- [ ] **SCROLL DOWN** past Feature Toggles and KPI Reference Ranges
- [ ] See "🎯 Playbook Triggers" section
- [ ] See documentation panel with all 5 playbooks
- [ ] See "🎤 VoC Sprint Triggers" with 6 input fields
- [ ] See "🚀 Activation Blitz Triggers" with 6 input fields
- [ ] Try editing a value (e.g., change NPS from 10 to 15)
- [ ] Click "Save VoC Triggers"
- [ ] Click "Test Triggers"

---

## 🐛 **If Still Not Working**

### **Clear Browser Cache**:
```
1. Press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Or clear cache completely
3. Reload page
```

### **Check Console for Errors**:
```
1. Press F12
2. Click "Console" tab
3. Look for red errors
4. Share any errors you see
```

### **Verify Backend**:
```bash
# Check backend is running
curl http://localhost:5059/

# Check accounts API
curl http://localhost:5059/api/accounts -H "X-Customer-ID: 1"

# Should return 25 accounts
```

---

**If you still don't see the triggers after scrolling down in the Settings modal, please share a screenshot or let me know what you DO see in the Settings modal!** 🔍
