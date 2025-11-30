# Account Snapshot API Signatures

Complete API reference for Account Snapshot endpoints.

---

## Base URL

All endpoints are prefixed with `/api/account-snapshots`

---

## Authentication

All endpoints require:
- **Session-based authentication** (user must be logged in)
- **Customer ID** extracted from session via `get_current_customer_id()`

---

## Endpoints

### 1. Create Account Snapshot

**Endpoint:** `POST /api/account-snapshots/create`

**Description:** Create account snapshot(s) - can create for single account or all accounts

**Request Body:**
```json
{
  "account_id": 123,              // Optional - if not provided, creates for all accounts
  "snapshot_type": "manual",      // Optional - default: "manual"
  "reason": "User requested",     // Optional - reason for snapshot
  "trigger_event": "user_action", // Optional - event that triggered snapshot
  "force_create": false            // Optional - bypass duplicate safeguard (default: false)
}
```

**Snapshot Types:**
- `manual` - User-initiated (no time restriction)
- `scheduled` - Scheduled/automated (24-hour minimum interval)
- `event_driven` - Triggered by events (1-hour minimum interval)
- `post_upload` - After KPI upload
- `post_health_calc` - After health score calculation
- `rag_auto` - Auto-created for RAG queries (30-minute minimum interval)

**Response (Success - Single Account):**
```json
{
  "status": "success",
  "message": "Created 1 snapshot(s)",
  "snapshots": [
    {
      "snapshot_id": 456,
      "account_id": 123,
      "account_name": "TechCorp Solutions",
      "snapshot_timestamp": "2025-01-15T10:30:00",
      "overall_health_score": 72.5
    }
  ]
}
```

**Response (Skipped - Duplicate Prevention):**
```json
{
  "message": "Snapshot creation skipped: A recent snapshot already exists",
  "skipped": true,
  "account_id": 123
}
```

**Response (Success - All Accounts):**
```json
{
  "status": "success",
  "message": "Created 5 snapshot(s)",
  "snapshots": [
    {
      "snapshot_id": 456,
      "account_id": 123,
      "account_name": "TechCorp Solutions",
      "snapshot_timestamp": "2025-01-15T10:30:00",
      "overall_health_score": 72.5
    },
    // ... more snapshots
  ]
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Failed to create snapshot: <error message>"
}
```

**Status Codes:**
- `200` - Success (created or skipped)
- `401` - Authentication required
- `500` - Server error

**Safeguards:**
- **Event-driven**: 1-hour minimum interval
- **RAG auto**: 30-minute minimum interval
- **Scheduled**: 24-hour minimum interval
- **Manual**: No restriction (always allowed)
- **Force create**: Bypasses all safeguards

---

### 2. Get Latest Snapshot

**Endpoint:** `GET /api/account-snapshots/latest`

**Description:** Get latest snapshot for a specific account

**Query Parameters:**
- `account_id` (required, integer) - Account ID

**Example Request:**
```
GET /api/account-snapshots/latest?account_id=123
```

**Response (Success):**
```json
{
  "status": "success",
  "snapshot": {
    "snapshot_id": 456,
    "account_id": 123,
    "account_name": "TechCorp Solutions",
    "snapshot_timestamp": "2025-01-15T10:30:00",
    "snapshot_type": "manual",
    "overall_health_score": 72.5,
    "health_score_trend": "improving",
    "revenue": 1200000.00,
    "revenue_change_percent": 5.2,
    "assigned_csm": "John Doe",
    "products_used": ["Product A", "Product B"],
    "playbooks_running": ["voc-sprint", "activation-blitz"],
    "playbooks_running_count": 2,
    "playbooks_completed_count": 5,
    "critical_kpis_count": 3,
    "total_kpis": 25,
    "recent_csm_note_ids": [101, 102, 103],
    "recent_playbook_report_ids": [201, 202, 203]
  }
}
```

**Response (Not Found):**
```json
{
  "status": "not_found",
  "message": "No snapshot found for this account"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Failed to fetch latest snapshot: <error message>"
}
```

**Status Codes:**
- `200` - Success
- `400` - Missing account_id
- `401` - Authentication required
- `404` - No snapshot found
- `500` - Server error

---

### 3. Get Snapshots (List with Filters)

**Endpoint:** `GET /api/account-snapshots`

**Description:** Get account snapshots with optional filters

**Query Parameters:**
- `account_id` (optional, integer) - Filter by account ID
- `limit` (optional, integer) - Maximum number of results (default: 10)
- `start_date` (optional, string) - Filter by start date (format: YYYY-MM-DD)

**Example Requests:**
```
GET /api/account-snapshots
GET /api/account-snapshots?account_id=123
GET /api/account-snapshots?account_id=123&limit=20
GET /api/account-snapshots?start_date=2025-01-01&limit=50
```

**Response (Success):**
```json
{
  "status": "success",
  "snapshots": [
    {
      "snapshot_id": 456,
      "account_id": 123,
      "account_name": "TechCorp Solutions",
      "snapshot_timestamp": "2025-01-15T10:30:00",
      "snapshot_type": "manual",
      "overall_health_score": 72.5,
      "health_score_trend": "improving",
      "revenue": 1200000.00,
      "revenue_change_percent": 5.2,
      "playbooks_running_count": 2,
      "playbooks_completed_count": 5,
      "critical_kpis_count": 3,
      "is_significant_change": true
    },
    // ... more snapshots
  ],
  "total": 10
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Failed to fetch snapshots: <error message>"
}
```

**Status Codes:**
- `200` - Success
- `401` - Authentication required
- `500` - Server error

---

### 4. Get Snapshot History

**Endpoint:** `GET /api/account-snapshots/history`

**Description:** Get account snapshot history for RAG context (last N months)

**Query Parameters:**
- `account_id` (required, integer) - Account ID
- `months` (optional, integer) - Number of months to look back (default: 3)

**Example Requests:**
```
GET /api/account-snapshots/history?account_id=123
GET /api/account-snapshots/history?account_id=123&months=6
```

**Response (Success):**
```json
{
  "status": "success",
  "history": [
    {
      "snapshot_timestamp": "2025-01-15T10:30:00",
      "overall_health_score": 72.5,
      "health_score_trend": "improving",
      "revenue": 1200000.00,
      "account_status": "active",
      "playbooks_running_count": 2,
      "playbooks_completed_count": 5
    },
    {
      "snapshot_timestamp": "2025-01-01T08:00:00",
      "overall_health_score": 68.0,
      "health_score_trend": "stable",
      "revenue": 1140000.00,
      "account_status": "active",
      "playbooks_running_count": 1,
      "playbooks_completed_count": 4
    }
    // ... more history entries
  ],
  "total": 2
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Failed to fetch snapshot history: <error message>"
}
```

**Status Codes:**
- `200` - Success
- `400` - Missing account_id
- `401` - Authentication required
- `500` - Server error

---

## Internal Function Signature

### `create_account_snapshot()`

**Function:** `create_account_snapshot(account_id, customer_id, snapshot_type='manual', snapshot_reason=None, trigger_event=None, created_by=None, force_create=False)`

**Parameters:**
- `account_id` (int, required) - Account ID to snapshot
- `customer_id` (int, required) - Customer ID (for security)
- `snapshot_type` (str, optional) - Type of snapshot (default: 'manual')
  - Options: `'manual'`, `'scheduled'`, `'event_driven'`, `'post_upload'`, `'post_health_calc'`, `'rag_auto'`
- `snapshot_reason` (str, optional) - Reason for snapshot
- `trigger_event` (str, optional) - Event that triggered snapshot
- `created_by` (int, optional) - User ID who created the snapshot
- `force_create` (bool, optional) - Bypass duplicate check (default: False)

**Returns:**
- `AccountSnapshot` object - If snapshot created successfully
- `None` - If snapshot creation skipped (duplicate prevention) or error occurred

**Usage Example:**
```python
from account_snapshot_api import create_account_snapshot

# Create manual snapshot
snapshot = create_account_snapshot(
    account_id=123,
    customer_id=1,
    snapshot_type='manual',
    snapshot_reason='User requested snapshot',
    created_by=user_id,
    force_create=False
)

if snapshot:
    print(f"Snapshot created: {snapshot.snapshot_id}")
else:
    print("Snapshot creation skipped or failed")
```

---

## Snapshot Data Structure

### Complete Snapshot Object

```python
{
    # Primary Keys
    "snapshot_id": 456,
    "account_id": 123,
    "customer_id": 1,
    
    # Metadata
    "snapshot_timestamp": "2025-01-15T10:30:00",
    "snapshot_type": "manual",
    "snapshot_reason": "User requested",
    "snapshot_version": 1,
    "created_by": 5,
    "trigger_event": "user_action",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00",
    
    # Financial
    "revenue": 1200000.00,
    "revenue_change_from_last": 60000.00,
    "revenue_change_percent": 5.2,
    
    # Health Scores
    "overall_health_score": 72.5,
    "product_usage_score": 75.0,
    "support_score": 70.0,
    "customer_sentiment_score": 68.0,
    "business_outcomes_score": 75.0,
    "relationship_strength_score": 74.0,
    "health_score_change_from_last": 4.5,
    "health_score_trend": "improving",
    
    # Account Status
    "account_status": "active",
    "industry": "Technology",
    "region": "North America",
    "account_tier": "Enterprise",
    "external_account_id": "EXT-123",
    
    # CSM & Team
    "assigned_csm": "John Doe",
    "csm_manager": "Jane Smith",
    "account_owner": "Bob Johnson",
    
    # Products
    "products_used": ["Product A", "Product B"],
    "product_count": 2,
    "primary_product": "Product A",
    
    # Playbooks
    "playbooks_running": ["voc-sprint", "activation-blitz"],
    "playbooks_running_count": 2,
    "playbooks_completed_count": 5,
    "playbooks_completed_last_30_days": 2,
    "last_playbook_executed": {
        "playbook_id": "voc-sprint",
        "date": "2025-01-10T14:00:00"
    },
    "playbook_recommendations_active": ["renewal-safeguard"],
    "recent_playbook_report_ids": [201, 202, 203],
    
    # KPI Summary
    "total_kpis": 25,
    "account_level_kpis": 20,
    "product_level_kpis": 5,
    "critical_kpis_count": 3,
    "at_risk_kpis_count": 5,
    "healthy_kpis_count": 17,
    "top_critical_kpis": [
        {
            "kpi_name": "NPS Score",
            "value": "45",
            "health_status": "Critical",
            "category": "Customer Sentiment"
        }
    ],
    
    # Engagement
    "lifecycle_stage": "Growth",
    "onboarding_status": "Complete",
    "last_qbr_date": "2024-12-15",
    "next_qbr_date": "2025-03-15",
    "engagement_score": 75.0,
    
    # Champions
    "primary_champion": "Alice Williams",
    "champion_status": "Active",
    "stakeholder_count": 3,
    
    # References
    "recent_csm_note_ids": [101, 102, 103, 104, 105],
    
    # Calculated
    "days_since_last_snapshot": 0,
    "snapshot_sequence_number": 5,
    "is_significant_change": true
}
```

---

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "error": "Authentication required"
}
```

**400 Bad Request:**
```json
{
  "error": "account_id is required"
}
```

**404 Not Found:**
```json
{
  "status": "not_found",
  "message": "No snapshot found for this account"
}
```

**500 Internal Server Error:**
```json
{
  "status": "error",
  "error": "Failed to <operation>: <error message>"
}
```

---

## Rate Limiting & Safeguards

### Duplicate Prevention

Snapshots are prevented from being created too frequently based on type:

| Snapshot Type | Minimum Interval | Can Bypass? |
|--------------|------------------|-------------|
| `manual` | None | N/A |
| `event_driven` | 1 hour | Yes (`force_create=True`) |
| `rag_auto` | 30 minutes | Yes (`force_create=True`) |
| `scheduled` | 24 hours | Yes (`force_create=True`) |
| `post_upload` | None | N/A |
| `post_health_calc` | None | N/A |

### Behavior

- If a snapshot exists within the minimum interval, creation is **skipped** (not an error)
- Returns `200 OK` with `skipped: true` message
- Use `force_create=True` to bypass safeguards (use with caution)

---

## Examples

### cURL Examples

**Create snapshot for specific account:**
```bash
curl -X POST http://localhost:5059/api/account-snapshots/create \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<session_cookie>" \
  -d '{
    "account_id": 123,
    "snapshot_type": "manual",
    "reason": "User requested snapshot"
  }'
```

**Get latest snapshot:**
```bash
curl http://localhost:5059/api/account-snapshots/latest?account_id=123 \
  -H "Cookie: session=<session_cookie>"
```

**Get snapshot history:**
```bash
curl "http://localhost:5059/api/account-snapshots/history?account_id=123&months=6" \
  -H "Cookie: session=<session_cookie>"
```

**List snapshots with filters:**
```bash
curl "http://localhost:5059/api/account-snapshots?account_id=123&limit=20" \
  -H "Cookie: session=<session_cookie>"
```

---

**Last Updated**: January 2025  
**API Version**: 1.0

