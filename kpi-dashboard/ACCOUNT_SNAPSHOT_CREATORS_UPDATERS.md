# Account Snapshot - Who Creates and Who Updates

## Summary

**Account Snapshots are IMMUTABLE** - they are **never updated** after creation. They represent point-in-time snapshots of account state.

---

## Who Creates Account Snapshots

| Creator | Location | Trigger | Snapshot Type | Safeguard | Created By |
|---------|----------|---------|---------------|-----------|------------|
| **User (Manual)** | `account_snapshot_api.py` | User calls `POST /api/account-snapshots/create` | `manual` | None (always allowed) | User ID from session |
| **RAG System** | `direct_rag_api.py` | RAG query when snapshot missing | `rag_auto` | 30-minute minimum interval | User ID from session |
| **Event System** | `event_system.py` (AccountSnapshotSubscriber) | `KPI_DATA_UPLOADED` event | `event_driven` | 1-hour minimum interval + 5-minute cooldown | None (system) |
| **Event System** | `event_system.py` (AccountSnapshotSubscriber) | `ACCOUNT_DATA_CHANGED` event | `event_driven` | 1-hour minimum interval + 5-minute cooldown | None (system) |
| **Event System** | `event_system.py` (AccountSnapshotSubscriber) | `HEALTH_SCORES_UPDATED` event | `event_driven` | 1-hour minimum interval + 5-minute cooldown | None (system) |
| **Tests** | `test_account_snapshot.py`, `e2e_test_account_snapshot.py` | Test execution | `manual` | Can bypass with `force_create=True` | Test user ID |

---

## Who Updates Account Snapshots

| Updater | Location | Update Type | Status |
|---------|----------|-------------|--------|
| **NO ONE** | N/A | N/A | **Snapshots are IMMUTABLE** |

**Note:** The `updated_at` field exists in the model but is **only set on creation** (via `onupdate=db.func.now()`). Since snapshots are never modified after creation, `updated_at` will always equal `created_at`.

---

## Detailed Breakdown

### 1. User (Manual Creation)

**File:** `backend/account_snapshot_api.py`  
**Function:** `create_snapshot()` (line 439)  
**Endpoint:** `POST /api/account-snapshots/create`

**Flow:**
```
User → POST /api/account-snapshots/create
  → create_account_snapshot()
  → AccountSnapshot created
  → Returns snapshot data
```

**Characteristics:**
- ✅ **No time restriction** (always allowed)
- ✅ **Can create for single account or all accounts**
- ✅ **Can bypass safeguard** with `force_create=True`
- ✅ **Tracks user ID** in `created_by` field

**Example:**
```python
# User creates snapshot via API
POST /api/account-snapshots/create
{
  "account_id": 123,
  "snapshot_type": "manual",
  "reason": "User requested snapshot"
}
```

---

### 2. RAG System (Auto-Creation)

**File:** `backend/direct_rag_api.py`  
**Function:** `direct_query()` (line 225-235)  
**Trigger:** RAG query when snapshot doesn't exist

**Flow:**
```
RAG Query → Check for snapshot
  → If missing → create_account_snapshot(type='rag_auto')
  → Snapshot created
  → Used in RAG context
```

**Characteristics:**
- ⏱️ **30-minute minimum interval** (safeguard)
- ✅ **Auto-creates** when snapshot missing
- ✅ **Tracks user ID** in `created_by` field
- ✅ **Respects safeguard** (won't create if recent snapshot exists)

**Example:**
```python
# RAG query triggers auto-creation
latest_snapshot = create_account_snapshot(
    account_id=account.account_id,
    customer_id=customer_id,
    snapshot_type='rag_auto',
    trigger_event='rag_query_missing_snapshot',
    created_by=user_id,
    force_create=False
)
```

---

### 3. Event System (Event-Driven Creation)

**File:** `backend/event_system.py`  
**Class:** `AccountSnapshotSubscriber` (line 268)  
**Method:** `handle_event()` (line 275)

**Events That Trigger Snapshots:**

| Event Type | Triggered By | Account(s) Affected |
|------------|---------------|-------------------|
| `KPI_DATA_UPLOADED` | KPI upload completion | Account from upload |
| `ACCOUNT_DATA_CHANGED` | Account profile update, playbook completion | Specific account |
| `HEALTH_SCORES_UPDATED` | Health trend creation/update | Specific account or all accounts |

**Flow:**
```
Event Published → AccountSnapshotSubscriber.handle_event()
  → Check cooldown (5 minutes)
  → create_account_snapshot(type='event_driven')
  → Snapshot created
```

**Characteristics:**
- ⏱️ **1-hour minimum interval** (safeguard)
- ⏱️ **5-minute cooldown** (additional safeguard)
- ✅ **Auto-creates** on data changes
- ❌ **No user ID** (system-initiated, `created_by=None`)
- ✅ **Respects safeguard** (won't create if recent snapshot exists)

**Example:**
```python
# Event triggers snapshot creation
snapshot = create_account_snapshot(
    account_id=account_id,
    customer_id=customer_id,
    snapshot_type='event_driven',
    trigger_event=event.event_type.value,
    force_create=False
)
```

**Event Publishers:**

| Event | Publisher | Location |
|-------|-----------|----------|
| `KPI_DATA_UPLOADED` | `DataIngestionSubscriber` | `event_system.py` |
| `ACCOUNT_DATA_CHANGED` | `customer_profile_api.py` | After account profile upload |
| `ACCOUNT_DATA_CHANGED` | `playbook_execution_api.py` | After playbook completion |
| `HEALTH_SCORES_UPDATED` | `health_trend_api.py` | After health trend creation/update |

---

## Safeguards Summary

| Snapshot Type | Minimum Interval | Additional Safeguard | Can Bypass? |
|--------------|------------------|---------------------|-------------|
| `manual` | None | None | N/A (always allowed) |
| `rag_auto` | 30 minutes | None | Yes (`force_create=True`) |
| `event_driven` | 1 hour | 5-minute cooldown | Yes (`force_create=True`) |
| `scheduled` | 24 hours | None | Yes (`force_create=True`) |

---

## Snapshot Immutability

### Why Snapshots Are Never Updated

1. **Point-in-Time Records**: Snapshots represent account state at a specific moment
2. **Historical Accuracy**: Updating would corrupt historical data
3. **Audit Trail**: Immutability ensures accurate audit trail
4. **Change Tracking**: Changes are tracked by creating new snapshots

### What Happens Instead of Updates

When account data changes:
1. **New snapshot is created** (if safeguards allow)
2. **Previous snapshot remains unchanged**
3. **Change metrics calculated** (e.g., `health_score_change_from_last`, `revenue_change_percent`)
4. **Trend analysis** uses multiple snapshots

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SNAPSHOT CREATION                         │
└─────────────────────────────────────────────────────────────┘

1. USER (Manual)
   └─> POST /api/account-snapshots/create
       └─> create_account_snapshot(type='manual')
           └─> AccountSnapshot created ✅

2. RAG SYSTEM (Auto)
   └─> RAG Query → No snapshot found
       └─> create_account_snapshot(type='rag_auto')
           └─> AccountSnapshot created ✅

3. EVENT SYSTEM (Event-Driven)
   └─> Event Published (KPI_DATA_UPLOADED, etc.)
       └─> AccountSnapshotSubscriber.handle_event()
           └─> create_account_snapshot(type='event_driven')
               └─> AccountSnapshot created ✅

┌─────────────────────────────────────────────────────────────┐
│                    SNAPSHOT UPDATES                         │
└─────────────────────────────────────────────────────────────┘

❌ NO UPDATES - Snapshots are IMMUTABLE
   └─> updated_at = created_at (always)
```

---

## Code References

### Creation Points

1. **Manual API**: `backend/account_snapshot_api.py:439` - `create_snapshot()`
2. **RAG Auto**: `backend/direct_rag_api.py:228` - `create_account_snapshot()`
3. **Event-Driven**: `backend/event_system.py:331` - `create_account_snapshot()`
4. **Core Function**: `backend/account_snapshot_api.py:61` - `create_account_snapshot()`

### Update Points

**NONE** - No update operations exist in the codebase.

---

## Summary Table

| Operation | Who | When | Type | Immutable? |
|-----------|-----|------|------|------------|
| **Create** | User | On-demand | `manual` | ✅ Yes |
| **Create** | RAG System | When missing | `rag_auto` | ✅ Yes |
| **Create** | Event System | On data change | `event_driven` | ✅ Yes |
| **Update** | ❌ No one | ❌ Never | ❌ N/A | ✅ Immutable |

---

**Last Updated**: January 2025  
**Status**: ✅ Complete

