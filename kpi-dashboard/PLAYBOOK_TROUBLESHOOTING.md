# 🔍 Playbook System Troubleshooting Guide

## ✅ Backend Status: WORKING PERFECTLY

All backend APIs tested and confirmed working:
- ✅ Create execution with account name
- ✅ Retrieve executions
- ✅ Complete steps
- ✅ Generate comprehensive reports
- ✅ List all reports
- ✅ Delete executions

**Test Results**:
```
✅ Created execution with account: "TechCorp Solutions"
✅ Report generated with 5 themes and 4 outcomes
✅ Reports API returning data correctly
✅ Delete working
```

---

## 🔍 Frontend Troubleshooting

### **Issue 1: Account Names Not Showing**

**What to Check**:

**Step 1**: Open browser console (F12)
**Step 2**: Go to Playbooks tab
**Step 3**: Start a playbook
**Step 4**: Look for these console messages:
```
Loaded accounts: 25
Started VoC Sprint for TechCorp Solutions (or similar)
```

**Step 5**: Check Network tab in DevTools:
- Look for POST to `/api/playbooks/executions`
- Check the request payload - should include:
  ```json
  {
    "context": {
      "accountName": "TechCorp Solutions",
      "accountId": 1
    }
  }
  ```
- Check the response - should return execution with context

**If account name not showing**:
1. Verify the execution object has `context.accountName`
2. Check if `execution.context?.accountName` exists in the component
3. Try hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

---

### **Issue 2: Reports Not Showing**

**What to Check**:

**Step 1**: Open Reports tab
**Step 2**: Open browser console (F12)
**Step 3**: Look for network requests to `/api/playbooks/reports`
**Step 4**: Check the response

**Manual Test**:
```bash
# In terminal
curl -s http://localhost:5059/api/playbooks/reports -H "X-Customer-ID: 1" | python3 -m json.tool
```

**Expected Response**:
```json
{
  "status": "success",
  "reports": [
    {
      "execution_id": "...",
      "playbook_name": "voc-sprint",
      "account_name": "TechCorp Solutions",
      "status": "in-progress",
      "steps_completed": 1,
      "has_full_report": true
    }
  ],
  "total": 1
}
```

**If empty**:
1. Start a playbook first (creates execution)
2. Wait 5 seconds (auto-refresh interval)
3. Check if PlaybookReports component is mounting
4. Verify no JavaScript errors in console

---

### **Issue 3: Trigger Values Not Visible**

**What to Check**:

**Step 1**: In Active Executions, look for gray box with "Trigger Conditions:"
**Step 2**: Should show tags like: [NPS: 10] [CSAT: 3.6]

**If not showing**:
1. Check if playbook has trigger data in steps
2. Look for step with id containing 'trigger-check'
3. Verify step.data.triggers exists

**Manual Verification**:
```javascript
// In browser console
const playbooks = window.__PLAYBOOKS__; // If available
console.log(playbooks[0].steps[0].data.triggers);
```

---

## 🎯 **Quick Diagnostic**

### **Check 1: Backend Running**
```bash
curl http://localhost:5059/
```
Should return: `{"message": "KPI Dashboard API", ...}`

### **Check 2: Create Test Execution**
```bash
curl -X POST http://localhost:5059/api/playbooks/executions \
  -H "X-Customer-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "playbookId": "voc-sprint",
    "context": {
      "customerId": 1,
      "accountId": 1,
      "accountName": "Test Account",
      "userId": 1,
      "userName": "Test User"
    }
  }' | python3 -m json.tool
```

Should return execution with `context.accountName`.

### **Check 3: Get Reports**
```bash
curl http://localhost:5059/api/playbooks/reports -H "X-Customer-ID: 1" | python3 -m json.tool
```

Should list executions.

### **Check 4: Generate Report**
```bash
# Use execution ID from step 2
curl "http://localhost:5059/api/playbooks/executions/<EXEC_ID>/report" \
  -H "X-Customer-ID: 1" | python3 -m json.tool | head -50
```

Should return comprehensive report.

---

## 🔧 **Common Fixes**

### **Fix 1: Clear Browser Cache**
```
1. Press Cmd+Shift+Delete (Mac) or Ctrl+Shift+Delete (Windows)
2. Clear cached files
3. Reload page
```

### **Fix 2: Hard Refresh**
```
Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

### **Fix 3: Check Console Errors**
```
F12 → Console tab → Look for red errors
```

### **Fix 4: Restart Backend**
```bash
cd backend
lsof -ti:5059 | xargs kill -9
python3 run_server.py
```

---

## 📊 **Expected Behavior**

### **When Starting Playbook**:
1. Click "Start Playbook"
2. Select account
3. Alert: "Started VoC Sprint for {Account Name}" ✅
4. Execution appears at TOP
5. Shows: Account badge + trigger values + delete icon ✅

### **When Viewing Reports**:
1. Go to Reports tab
2. See list of executions immediately
3. Each shows: Playbook name, account name, status, steps completed
4. Click "View Report" → See full report with RACI, outcomes, etc. ✅

### **When Completing Steps**:
1. Click step button
2. Step marked complete
3. Progress bar updates
4. Report regenerates (visible in Reports tab after 5s) ✅

---

## 🆘 **If Still Not Working**

### **Share These Details**:
1. Browser console errors (F12 → Console)
2. Network tab showing API calls
3. What you see vs. what you expect
4. Screenshot of the issue

### **Try This**:
1. Open browser console (F12)
2. Go to Playbooks tab
3. Start a playbook
4. Share any error messages you see

**The backend is confirmed working - issue is likely frontend state or rendering!**
