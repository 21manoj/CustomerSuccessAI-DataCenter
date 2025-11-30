# Account Snapshot - When Are Snapshots Created?

## Snapshot Creation Triggers

Account snapshots are created automatically or on-demand in the following scenarios:

---

## 1. **Event-Driven (Automatic) - Real-Time**

### A. After KPI Data Upload
**Trigger**: User uploads KPI Excel file  
**Event**: `KPI_DATA_UPLOADED`  
**When**: Immediately after upload completes and KPIs are saved to database  
**Location**: `backend/enhanced_upload_api.py` → `event_manager.publish_kpi_upload()`  
**Snapshot Type**: `event_driven`  
**Trigger Event**: `kpi_data_uploaded`

**Example Flow**:
```
10:00 AM - User uploads KPI file for "TechCorp Solutions"
10:00 AM - Backend processes file, creates KPIs in database
10:00 AM - Event published: KPI_DATA_UPLOADED
10:00 AM - AccountSnapshotSubscriber creates snapshot automatically
10:00 AM - Log: "✅ Auto-created snapshot 123 for account TechCorp Solutions"
```

### B. After Health Score Calculation/Update
**Trigger**: Health trend is created or updated  
**Event**: `HEALTH_SCORES_UPDATED`  
**When**: 
- After creating a new health trend record
- After updating an existing health trend
- After bulk generating health trends for all accounts
**Location**: `backend/health_trend_api.py`  
**Snapshot Type**: `event_driven`  
**Trigger Event**: `health_scores_updated`

**Example Flow**:
```
10:15 AM - User calculates health scores for all accounts
10:15 AM - HealthTrend records created/updated in database
10:15 AM - Event published: HEALTH_SCORES_UPDATED (for each account)
10:15 AM - AccountSnapshotSubscriber creates snapshots automatically
10:15 AM - Log: "✅ Auto-created snapshot 124 for account Acme Corp"
```

### C. After Customer Profile Upload
**Trigger**: User uploads customer profile Excel file  
**Event**: `ACCOUNT_DATA_CHANGED`  
**When**: Immediately after profile metadata is updated for each account  
**Location**: `backend/customer_profile_api.py`  
**Snapshot Type**: `event_driven`  
**Trigger Event**: `account_data_changed`

**Example Flow**:
```
10:30 AM - User uploads customer profile file
10:30 AM - Backend updates Account.profile_metadata for 36 accounts
10:30 AM - Event published: ACCOUNT_DATA_CHANGED (for each account)
10:30 AM - AccountSnapshotSubscriber creates snapshots automatically
10:30 AM - Log: "✅ Auto-created snapshot 125-160 for 36 accounts"
```

### D. After Playbook Execution Completes
**Trigger**: Playbook execution status changes to "completed"  
**Event**: `ACCOUNT_DATA_CHANGED`  
**When**: When playbook execution is saved with status='completed'  
**Location**: `backend/playbook_execution_api.py` → `save_execution_to_db()`  
**Snapshot Type**: `event_driven`  
**Trigger Event**: `account_data_changed`

**Example Flow**:
```
11:00 AM - VoC Sprint playbook completes for "TechCorp Solutions"
11:00 AM - PlaybookExecution.status updated to 'completed'
11:00 AM - Event published: ACCOUNT_DATA_CHANGED
11:00 AM - AccountSnapshotSubscriber creates snapshot automatically
11:00 AM - Log: "✅ Auto-created snapshot 161 for account TechCorp Solutions"
```

---

## 2. **On-Demand (Manual) - User-Initiated**

### A. User Clicks Account in Health Tab
**Trigger**: User clicks on an account name in Account Health Dashboard  
**When**: Immediately when account is selected  
**Location**: `src/components/CSPlatform.tsx` → `fetchAccountSnapshot()`  
**Snapshot Type**: `manual`  
**Trigger Event**: `User clicked account in Health tab`

**Example Flow**:
```
2:00 PM - User navigates to Account Health tab
2:00 PM - User clicks on "TechCorp Solutions" account
2:00 PM - Frontend calls: GET /api/account-snapshots/latest?account_id=5
2:00 PM - No snapshot found → Frontend calls: POST /api/account-snapshots/create
2:00 PM - Snapshot created
2:00 PM - Snapshot context displayed in UI
```

### B. RAG Query (If Snapshot Missing)
**Trigger**: User asks RAG question about an account  
**When**: Before RAG query executes, if snapshot doesn't exist  
**Location**: `backend/direct_rag_api.py`  
**Snapshot Type**: `rag_auto`  
**Trigger Event**: `rag_query_missing_snapshot`

**Example Flow**:
```
3:00 PM - User asks: "What's TechCorp's current status?"
3:00 PM - RAG system checks for snapshot
3:00 PM - No snapshot found → Creates one automatically
3:00 PM - Log: "📸 No snapshot found for TechCorp Solutions, creating one automatically..."
3:00 PM - Snapshot created
3:00 PM - RAG query executes with snapshot context
```

### C. Manual API Call
**Trigger**: Direct API call to create snapshot  
**When**: Anytime via API  
**Location**: `POST /api/account-snapshots/create`  
**Snapshot Type**: `manual` (or specified in request)

**Example Flow**:
```
4:00 PM - Admin calls: POST /api/account-snapshots/create
4:00 PM - Request body: {"account_id": 5, "snapshot_type": "manual"}
4:00 PM - Snapshot created immediately
```

---

## 3. **Cooldown Protection**

**Purpose**: Prevent creating too many snapshots in a short time

**Cooldown Period**: 5 minutes (300 seconds) per account

**Behavior**:
- If snapshot was created < 5 minutes ago for an account, skip creation
- Logs: "Skipping snapshot for account X (cooldown: 180s remaining)"

**Example**:
```
10:00 AM - KPI upload → Snapshot created ✅
10:02 AM - Health score update → Snapshot skipped (cooldown) ⏸️
10:06 AM - Profile update → Snapshot created ✅ (cooldown expired)
```

---

## Summary Table

| Trigger | When | Frequency | Snapshot Type | Cooldown Applied |
|---------|------|-----------|---------------|------------------|
| **KPI Upload** | After upload completes | Every upload | `event_driven` | ✅ Yes (5 min) |
| **Health Score Update** | After trend created/updated | Every calculation | `event_driven` | ✅ Yes (5 min) |
| **Profile Upload** | After profile updated | Every upload | `event_driven` | ✅ Yes (5 min) |
| **Playbook Completion** | When playbook finishes | Every completion | `event_driven` | ✅ Yes (5 min) |
| **User Clicks Account** | When account selected | On-demand | `manual` | ❌ No |
| **RAG Query** | Before query if missing | On-demand | `rag_auto` | ❌ No |
| **Manual API Call** | When API called | On-demand | `manual` | ❌ No |

---

## Timing Examples

### Scenario 1: New Account Setup
```
Day 1, 9:00 AM - Upload KPI file
  → Snapshot #1 created (event_driven, kpi_data_uploaded)

Day 1, 9:30 AM - Upload customer profile
  → Snapshot #2 created (event_driven, account_data_changed)

Day 1, 10:00 AM - Calculate health scores
  → Snapshot #3 created (event_driven, health_scores_updated)

Day 1, 2:00 PM - User clicks account in Health tab
  → Snapshot #4 created (manual, user clicked account)
  → OR uses existing snapshot if created < 5 min ago
```

### Scenario 2: Active Account (Multiple Events)
```
10:00 AM - KPI upload → Snapshot created ✅
10:02 AM - Health score update → Skipped (cooldown) ⏸️
10:05 AM - Playbook completes → Skipped (cooldown) ⏸️
10:06 AM - Profile update → Snapshot created ✅ (cooldown expired)
10:10 AM - User clicks account → Uses existing snapshot (no new creation)
```

### Scenario 3: RAG Query for Account Without Snapshot
```
3:00 PM - User asks: "Show me TechCorp's status"
3:00 PM - RAG checks for snapshot → Not found
3:00 PM - RAG auto-creates snapshot (rag_auto)
3:00 PM - RAG query executes with snapshot context
3:05 PM - User asks another question → Uses existing snapshot
```

---

## Best Practices

### ✅ **Recommended**
- Let automatic event-driven snapshots handle most cases
- Snapshots are created automatically when data changes
- No manual intervention needed for normal operations

### ⚠️ **Manual Creation When Needed**
- Before important meetings (create snapshot for reference)
- After major account changes (manual snapshot for milestone)
- For specific reporting periods (monthly/quarterly snapshots)

### 🔒 **Cooldown Protection**
- Prevents database bloat from rapid-fire events
- 5-minute cooldown is configurable in code
- Manual/RAG snapshots bypass cooldown (on-demand)

---

## Monitoring

### Check Snapshot Creation Logs
```bash
# Backend logs will show:
✅ Auto-created snapshot 123 for account TechCorp Solutions (trigger: kpi_data_uploaded)
Skipping snapshot for account 5 (cooldown: 180s remaining)
📸 No snapshot found for TechCorp Solutions, creating one automatically...
✓ Auto-created snapshot 124 for TechCorp Solutions
```

### Query Snapshots
```bash
# Get latest snapshot for account
GET /api/account-snapshots/latest?account_id=5

# Get all snapshots
GET /api/account-snapshots?account_id=5&limit=10
```

---

**Last Updated**: January 2025  
**Status**: ✅ Fully Operational


