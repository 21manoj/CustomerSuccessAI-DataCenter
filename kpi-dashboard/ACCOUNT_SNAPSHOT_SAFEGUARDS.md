# Account Snapshot - Safeguards Against Duplicate Creation

## ✅ Safeguards Implemented

The system now includes **coded safeguards** to prevent creating duplicate snapshots unnecessarily. Once a snapshot is created, the system will **skip creation** of new snapshots within defined time intervals, unless explicitly forced.

---

## Safeguard Rules

### 1. **Event-Driven Snapshots** (`snapshot_type='event_driven'`)
- **Minimum Interval**: 1 hour
- **Behavior**: If a snapshot exists that was created < 1 hour ago, skip creation
- **Rationale**: Prevents rapid-fire snapshots from multiple events in short succession

**Example**:
```
10:00 AM - KPI upload → Snapshot created ✅
10:15 AM - Health score update → Snapshot skipped ⏸️ (only 15 min ago)
11:01 AM - Profile update → Snapshot created ✅ (1+ hour passed)
```

### 2. **RAG Auto Snapshots** (`snapshot_type='rag_auto'`)
- **Minimum Interval**: 30 minutes
- **Behavior**: If a snapshot exists that was created < 30 minutes ago, skip creation
- **Rationale**: RAG queries may happen frequently, but snapshots don't need to update that often

**Example**:
```
2:00 PM - RAG query → Snapshot created ✅
2:15 PM - Another RAG query → Snapshot skipped ⏸️ (only 15 min ago)
2:31 PM - Another RAG query → Snapshot created ✅ (30+ min passed)
```

### 3. **Scheduled Snapshots** (`snapshot_type='scheduled'`)
- **Minimum Interval**: 24 hours
- **Behavior**: If a snapshot exists that was created < 24 hours ago, skip creation
- **Rationale**: Scheduled snapshots are meant to be daily/weekly, not hourly

**Example**:
```
Monday 9:00 AM - Scheduled snapshot → Created ✅
Monday 3:00 PM - Scheduled snapshot → Skipped ⏸️ (same day)
Tuesday 9:00 AM - Scheduled snapshot → Created ✅ (24+ hours passed)
```

### 4. **Manual Snapshots** (`snapshot_type='manual'`)
- **Minimum Interval**: None (always allowed)
- **Behavior**: Always create, regardless of existing snapshots
- **Rationale**: User-initiated snapshots should always be honored

**Example**:
```
10:00 AM - User clicks account → Snapshot created ✅
10:05 AM - User clicks account again → Snapshot created ✅ (manual, no restriction)
```

---

## Implementation Details

### Function Signature
```python
def create_account_snapshot(
    account_id, 
    customer_id, 
    snapshot_type='manual', 
    snapshot_reason=None, 
    trigger_event=None, 
    created_by=None, 
    force_create=False  # NEW: Bypass safeguard if True
):
```

### Safeguard Check Logic
```python
# SAFEGUARD: Prevent duplicate snapshot creation (unless forced or manual)
if not force_create and previous_snapshot:
    time_since_last = datetime.now() - previous_snapshot.snapshot_timestamp
    
    if snapshot_type == 'event_driven':
        if time_since_last < timedelta(hours=1):
            return None  # Skip creation (not an error)
    
    elif snapshot_type == 'rag_auto':
        if time_since_last < timedelta(minutes=30):
            return None  # Skip creation (not an error)
    
    elif snapshot_type == 'scheduled':
        if time_since_last < timedelta(hours=24):
            return None  # Skip creation (not an error)
    
    # Manual snapshots: Always allow (no check)
```

### Return Values
- **Snapshot Object**: Snapshot was created successfully
- **None**: Snapshot creation was skipped due to safeguard (not an error)
- **Exception**: Actual error occurred during creation

---

## Bypassing Safeguards

### Force Create Flag
If you need to bypass the safeguard (e.g., for testing or manual override):

```python
snapshot = create_account_snapshot(
    account_id=account_id,
    customer_id=customer_id,
    snapshot_type='event_driven',
    force_create=True  # Bypass safeguard
)
```

### API Endpoint
```json
POST /api/account-snapshots/create
{
  "account_id": 5,
  "snapshot_type": "event_driven",
  "force_create": true  // Bypass safeguard
}
```

---

## Event System Integration

The event system subscriber respects the safeguard:

```python
# In event_system.py - AccountSnapshotSubscriber
snapshot = create_account_snapshot(
    account_id=account_id,
    customer_id=customer_id,
    snapshot_type='event_driven',
    trigger_event=event.event_type.value,
    force_create=False  # Respect safeguard
)

if snapshot:
    logger.info(f"✅ Auto-created snapshot {snapshot.snapshot_id}")
elif snapshot is None:
    logger.debug(f"⏸️  Skipped snapshot creation: Recent snapshot exists")
```

---

## RAG Integration

The RAG system respects the safeguard when auto-creating snapshots:

```python
# In direct_rag_api.py
if not latest_snapshot:
    latest_snapshot = create_account_snapshot(
        account_id=account.account_id,
        customer_id=customer_id,
        snapshot_type='rag_auto',
        trigger_event='rag_query_missing_snapshot',
        force_create=False  # Respect safeguard
    )
    
    if latest_snapshot is None:
        # Safeguard triggered - get existing snapshot instead
        latest_snapshot = AccountSnapshot.query.filter_by(...).first()
```

---

## API Response Handling

### Success Response
```json
{
  "message": "Account snapshot created successfully",
  "snapshot_id": 123,
  "account_id": 5,
  "timestamp": "2025-01-15T10:00:00"
}
```

### Skipped Response (Safeguard Triggered)
```json
{
  "message": "Snapshot creation skipped: A recent snapshot already exists",
  "skipped": true,
  "account_id": 5
}
```

### Error Response
```json
{
  "error": "Failed to create snapshot"
}
```

---

## Benefits

✅ **Prevents Database Bloat**: Avoids creating hundreds of snapshots in short time  
✅ **Performance**: Reduces unnecessary database writes  
✅ **Data Quality**: Ensures snapshots represent meaningful state changes  
✅ **Flexible**: Manual snapshots always allowed (user control)  
✅ **Transparent**: Clear logging when snapshots are skipped  
✅ **Override Available**: `force_create` flag for special cases  

---

## Logging

### When Snapshot is Skipped
```
⏸️  Skipping snapshot creation for account TechCorp Solutions: 
    Snapshot exists from 15.3 minutes ago 
    (event-driven snapshots require 1 hour minimum interval)
```

### When Snapshot is Created
```
✅ Auto-created snapshot 123 for account TechCorp Solutions (trigger: kpi_data_uploaded)
```

### In Event System
```
⏸️  Skipped snapshot creation for account TechCorp Solutions: Recent snapshot exists (safeguard)
```

---

## Testing

### Test 1: Event-Driven Safeguard
```python
# Create first snapshot
snapshot1 = create_account_snapshot(..., snapshot_type='event_driven')
assert snapshot1 is not None

# Try to create second snapshot immediately
snapshot2 = create_account_snapshot(..., snapshot_type='event_driven')
assert snapshot2 is None  # Safeguard triggered

# Wait 1+ hour, then create
# snapshot3 = create_account_snapshot(..., snapshot_type='event_driven')
# assert snapshot3 is not None
```

### Test 2: Manual Always Allowed
```python
# Create first snapshot
snapshot1 = create_account_snapshot(..., snapshot_type='manual')
assert snapshot1 is not None

# Create second snapshot immediately (manual, no restriction)
snapshot2 = create_account_snapshot(..., snapshot_type='manual')
assert snapshot2 is not None  # Manual always allowed
```

### Test 3: Force Create Bypass
```python
# Create first snapshot
snapshot1 = create_account_snapshot(..., snapshot_type='event_driven')
assert snapshot1 is not None

# Force create second snapshot immediately
snapshot2 = create_account_snapshot(..., snapshot_type='event_driven', force_create=True)
assert snapshot2 is not None  # Force bypassed safeguard
```

---

## Configuration

### Adjusting Time Intervals
**Location**: `backend/account_snapshot_api.py` - `create_account_snapshot()` function

```python
# Current intervals
if snapshot_type == 'event_driven':
    if time_since_last < timedelta(hours=1):  # Change this value
        return None

elif snapshot_type == 'rag_auto':
    if time_since_last < timedelta(minutes=30):  # Change this value
        return None

elif snapshot_type == 'scheduled':
    if time_since_last < timedelta(hours=24):  # Change this value
        return None
```

---

**Last Updated**: January 2025  
**Status**: ✅ Fully Implemented and Active


