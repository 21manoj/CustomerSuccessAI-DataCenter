# Account Snapshot - Automatic Updates Implementation

## ✅ Implementation Complete

Automatic snapshot creation has been implemented as per the design document. Snapshots are now automatically created when relevant data changes occur.

---

## Event-Driven Automatic Snapshot Creation

### Implementation Details

#### 1. **AccountSnapshotSubscriber** (`backend/event_system.py`)
- **Purpose**: Automatically creates account snapshots when data changes
- **Cooldown**: 5 minutes between snapshots for the same account (prevents duplicates)
- **Events Subscribed To**:
  - `KPI_DATA_UPLOADED` - After KPI upload completes
  - `ACCOUNT_DATA_CHANGED` - After account profile update
  - `HEALTH_SCORES_UPDATED` - After health score calculation

#### 2. **Event Publishing Integration**

**A. KPI Upload** (`backend/enhanced_upload_api.py`)
- Already publishes `KPI_DATA_UPLOADED` event
- Snapshot automatically created for the account that received the upload

**B. Health Trend Creation/Update** (`backend/health_trend_api.py`)
- Publishes `HEALTH_SCORES_UPDATED` event when:
  - Health trend is created
  - Health trend is updated
  - Health trends are generated in bulk
- Snapshot automatically created for affected account(s)

**C. Customer Profile Upload** (`backend/customer_profile_api.py`)
- Publishes `ACCOUNT_DATA_CHANGED` event for each updated account
- Snapshot automatically created for each account with updated profile

**D. Playbook Execution Completion** (`backend/playbook_execution_api.py`)
- Publishes `ACCOUNT_DATA_CHANGED` event when playbook execution completes
- Snapshot automatically created for the account that ran the playbook

---

## How It Works

### Event Flow

```
Data Change Occurs
    ↓
Event Published (e.g., KPI_DATA_UPLOADED)
    ↓
AccountSnapshotSubscriber.handle_event()
    ↓
Check Cooldown (5 min per account)
    ↓
Verify Account Ownership (security)
    ↓
Create Snapshot (snapshot_type='event_driven')
    ↓
Log Success/Failure
```

### Cooldown Mechanism

To prevent creating too many snapshots:
- **Cooldown Period**: 5 minutes (300 seconds)
- **Tracking**: `last_snapshot_times` dictionary per account
- **Behavior**: If snapshot was created < 5 minutes ago, skip creation

**Example**:
```
10:00 AM - KPI upload → Snapshot created
10:02 AM - Health score update → Snapshot skipped (cooldown)
10:06 AM - Account profile update → Snapshot created (cooldown expired)
```

---

## Snapshot Types

### 1. **Manual** (`snapshot_type='manual'`)
- Created via API: `POST /api/account-snapshots/create`
- Created when user clicks account in Health tab (if missing)
- Created via RAG query (if missing)

### 2. **Event-Driven** (`snapshot_type='event_driven'`)
- Automatically created by `AccountSnapshotSubscriber`
- `trigger_event` = event type (e.g., `kpi_data_uploaded`, `account_data_changed`)

### 3. **RAG Auto** (`snapshot_type='rag_auto'`)
- Automatically created by RAG system when snapshot missing
- `trigger_event='rag_query_missing_snapshot'`

### 4. **Scheduled** (`snapshot_type='scheduled'`)
- **Not Yet Implemented** - Future enhancement
- Would be triggered by cron job or scheduler

### 5. **Post-Health-Calc** (`snapshot_type='post_health_calc'`)
- **Not Yet Implemented** - Future enhancement
- Would be triggered after health score calculation runs

---

## Event Triggers Summary

| Event Type | Trigger | Accounts Affected | Implementation |
|------------|---------|------------------|----------------|
| `KPI_DATA_UPLOADED` | KPI upload completes | Account from upload | ✅ Implemented |
| `ACCOUNT_DATA_CHANGED` | Profile upload, playbook completion | Specific account(s) | ✅ Implemented |
| `HEALTH_SCORES_UPDATED` | Health trend created/updated | Specific account or all | ✅ Implemented |
| `PLAYBOOK_EXECUTION_COMPLETED` | Playbook finishes | Account that ran playbook | ✅ Implemented (via ACCOUNT_DATA_CHANGED) |

---

## Configuration

### Cooldown Period
**Location**: `backend/event_system.py` - `AccountSnapshotSubscriber.__init__()`

```python
self.snapshot_cooldown = 300  # 5 minutes in seconds
```

**To Change**: Modify this value to adjust cooldown period.

### Event System Startup
**Location**: `backend/app_v3_minimal.py`

The event system automatically starts when the Flask app initializes:
```python
from event_system import event_manager
event_manager.start()
```

---

## Logging

### Success Logs
```
✅ Auto-created snapshot 123 for account TechCorp Solutions (trigger: kpi_data_uploaded)
```

### Cooldown Logs
```
Skipping snapshot for account 5 (cooldown: 180s remaining)
```

### Error Logs
```
⚠️  Failed to create snapshot for account TechCorp Solutions
Error creating snapshot for account TechCorp Solutions: [error details]
```

---

## Testing

### Manual Test
1. Upload KPI data for an account
2. Check logs for: `✅ Auto-created snapshot ... (trigger: kpi_data_uploaded)`
3. Verify snapshot exists: `GET /api/account-snapshots/latest?account_id=X`

### Verify Cooldown
1. Upload KPI data → Snapshot created
2. Immediately update health trend → Snapshot skipped (cooldown)
3. Wait 5+ minutes → Update health trend → Snapshot created

---

## Benefits

✅ **Automatic**: No manual intervention needed  
✅ **Real-Time**: Snapshots created immediately after data changes  
✅ **Efficient**: Cooldown prevents duplicate snapshots  
✅ **Secure**: Verifies account ownership before creating  
✅ **Transparent**: Logs all snapshot creation attempts  
✅ **Flexible**: Can be disabled by not starting event system  

---

## Future Enhancements

1. **Scheduled Snapshots**: Daily/weekly/monthly automatic snapshots
2. **Configurable Cooldown**: Per-customer or per-account cooldown settings
3. **Snapshot Retention Policy**: Automatic cleanup of old snapshots
4. **Batch Snapshot Creation**: Create snapshots for all accounts at once
5. **Snapshot Comparison**: API to compare two snapshots

---

**Last Updated**: January 2025  
**Status**: ✅ Fully Implemented and Active


