# Account Snapshot - Database Tables & Runtime Updates

## Database Tables Used by Account Snapshot

### Tables READ From (Data Sources)

The Account Snapshot feature reads data from the following tables to build a comprehensive snapshot:

#### 1. **`accounts`** (Primary Source)
- **Purpose**: Core account information
- **Fields Used**:
  - `account_id`, `customer_id`
  - `account_name`, `revenue`, `industry`, `region`, `account_status`
  - `external_account_id`
  - `profile_metadata` (JSON) - Contains:
    - `assigned_csm`, `csm_manager`, `account_owner`
    - `account_tier`
    - `products_used` (fallback if no Product records)
    - `engagement` (lifecycle_stage, onboarding_status, QBR dates, engagement_score)
    - `champions` (primary champion, stakeholder count)
- **Query Location**: `account_snapshot_api.py:77-80`

#### 2. **`products`**
- **Purpose**: Product usage information
- **Fields Used**:
  - `product_name` (to build `products_used` list)
  - `account_id`, `customer_id` (for filtering)
- **Query Location**: `account_snapshot_api.py:141-146`

#### 3. **`kpis`**
- **Purpose**: KPI summary statistics
- **Fields Used**:
  - `kpi_id`, `account_id`, `product_id`
  - `category`, `kpi_parameter`, `data`
  - Used to calculate:
    - Total KPIs count
    - Account-level vs Product-level KPI counts
    - Critical/At-Risk/Healthy KPI counts (via `HealthScoreEngine`)
    - Top 5 critical KPIs
- **Query Location**: `account_snapshot_api.py:197-224`

#### 4. **`health_trends`**
- **Purpose**: Health score data (preferred source)
- **Fields Used**:
  - `overall_health_score`
  - `product_usage_score`, `support_score`, `customer_sentiment_score`
  - `business_outcomes_score`, `relationship_strength_score`
  - `year`, `month` (for getting latest trend)
- **Query Location**: `account_snapshot_api.py:99-118`
- **Fallback**: If no `HealthTrend` exists, calculates on-the-fly using `calculate_health_score_proxy()`

#### 5. **`playbook_executions`**
- **Purpose**: Active and completed playbook data
- **Fields Used**:
  - `playbook_id`, `status` (in-progress, completed)
  - `started_at`, `completed_at`
  - `account_id`, `customer_id` (for filtering)
- **Calculations**:
  - Running playbooks count
  - Completed playbooks count
  - Completed in last 30 days
  - Last playbook executed (most recent)
- **Query Location**: `account_snapshot_api.py:151-180`

#### 6. **`playbook_reports`**
- **Purpose**: Recent playbook execution results
- **Fields Used**:
  - `report_id` (stored as reference in `recent_playbook_report_ids`)
  - `playbook_name`, `report_generated_at`
  - `account_id`, `customer_id` (for filtering)
- **Query Location**: `account_snapshot_api.py:189-194`
- **Note**: Only stores IDs (last 3 reports), full content fetched when needed for RAG

#### 7. **`playbook_triggers`**
- **Purpose**: Active playbook recommendations
- **Fields Used**:
  - `playbook_type`
  - `auto_trigger_enabled` (for filtering active triggers)
- **Query Location**: `account_snapshot_api.py:183-187`

#### 8. **`account_notes`** (NEW TABLE)
- **Purpose**: CSM notes, meeting notes, QBR notes
- **Fields Used**:
  - `note_id` (stored as reference in `recent_csm_note_ids`)
  - `note_type`, `note_content`, `created_at`
  - `account_id`, `customer_id` (for filtering)
- **Query Location**: `account_snapshot_api.py:256-260`
- **Note**: Only stores IDs (last 5 notes), full content fetched when needed for RAG

#### 9. **`account_snapshots`** (Previous Snapshot)
- **Purpose**: Calculate changes and trends
- **Fields Used**:
  - `snapshot_timestamp` (for `days_since_last_snapshot`)
  - `snapshot_sequence_number` (for incrementing sequence)
  - `overall_health_score` (for `health_score_change_from_last`)
  - `revenue` (for `revenue_change_from_last` and `revenue_change_percent`)
- **Query Location**: `account_snapshot_api.py:86-96`

### Tables WRITTEN To

#### 1. **`account_snapshots`** (NEW TABLE)
- **Purpose**: Store the complete snapshot
- **Fields Written**: 50+ fields including:
  - Metadata (snapshot_id, account_id, customer_id, timestamp, type, reason)
  - Financial (revenue, revenue_change_from_last, revenue_change_percent)
  - Health Scores (overall, category scores, trend, change)
  - Account Status (status, industry, region, tier, external_id)
  - CSM & Team (assigned_csm, csm_manager, account_owner)
  - Products (products_used JSON, product_count, primary_product)
  - Playbooks (running, completed counts, last executed, recommendations)
  - KPI Summary (total, account-level, product-level, critical/at-risk/healthy counts)
  - Engagement (lifecycle_stage, onboarding_status, QBR dates, engagement_score)
  - Champions (primary_champion, champion_status, stakeholder_count)
  - References (recent_csm_note_ids JSON, recent_playbook_report_ids JSON)
  - Calculated (days_since_last_snapshot, sequence_number, is_significant_change)
- **Query Location**: `account_snapshot_api.py:313-360`

---

## How Account Snapshot Updates from Runtime Environment

### Current Implementation: **Manual Creation**

Currently, snapshots are created **manually** via API endpoints:

#### 1. **Manual API Call**
```python
POST /api/account-snapshots/create
{
  "account_id": 123,  # Optional - if omitted, creates for all accounts
  "snapshot_type": "manual",
  "reason": "Monthly snapshot",
  "trigger_event": null
}
```

#### 2. **Real-Time Data Fetching**

When a snapshot is created, it **immediately queries** all source tables to get the latest data:

```python
# Example: Snapshot creation process
def create_account_snapshot(account_id, customer_id, ...):
    # 1. Get account (current state)
    account = Account.query.filter_by(account_id=account_id).first()
    
    # 2. Get latest health trend (real-time)
    latest_trend = HealthTrend.query.filter_by(...).order_by(...).first()
    
    # 3. Get current products (real-time)
    products = Product.query.filter_by(account_id=account_id).all()
    
    # 4. Get current KPIs (real-time)
    all_kpis = KPI.query.filter_by(account_id=account_id).all()
    
    # 5. Get current playbook executions (real-time)
    running_executions = PlaybookExecution.query.filter_by(...).all()
    
    # 6. Get recent reports and notes (real-time)
    recent_reports = PlaybookReport.query.filter_by(...).limit(3).all()
    recent_notes = AccountNote.query.filter_by(...).limit(5).all()
    
    # 7. Create snapshot with all current data
    snapshot = AccountSnapshot(...)
    db.session.add(snapshot)
    db.session.commit()
```

**Key Point**: Every snapshot creation is a **point-in-time capture** of the current database state. It does NOT store historical data - it captures what exists **right now**.

---

### Future: Automatic Updates (Design Ready)

The design supports automatic snapshot creation, but it's **not yet implemented**. Here are the planned trigger mechanisms:

#### 1. **Scheduled Snapshots** (Not Implemented)
```python
# Would be triggered by a cron job or scheduler
POST /api/account-snapshots/create
{
  "snapshot_type": "scheduled",
  "trigger_event": "daily_snapshot_job"
}
```

#### 2. **Event-Driven Snapshots** (Not Implemented)
The system has an event system (`backend/event_system.py`) that could trigger snapshots:

**Potential Events**:
- `KPI_DATA_UPLOADED` - After KPI upload completes
- `HEALTH_SCORES_UPDATED` - After health score calculation
- `ACCOUNT_DATA_CHANGED` - After account profile update
- `PLAYBOOK_EXECUTION_COMPLETED` - After playbook finishes

**Example Integration** (Not Yet Implemented):
```python
# In event_system.py or upload_api.py
def on_kpi_upload_complete(customer_id, account_id):
    # Trigger snapshot after upload
    create_account_snapshot(
        account_id=account_id,
        customer_id=customer_id,
        snapshot_type='event_driven',
        trigger_event='kpi_data_uploaded'
    )
```

#### 3. **Post-Health-Calc Snapshots** (Not Implemented)
After health score calculation runs, could automatically create snapshot:
```python
# In health_trend_api.py or health calculation job
def after_health_calculation(account_id, customer_id):
    create_account_snapshot(
        account_id=account_id,
        customer_id=customer_id,
        snapshot_type='post_health_calc',
        trigger_event='health_scores_updated'
    )
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME ENVIRONMENT                      │
│  (Data changes in real-time via uploads, updates, etc.)   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ Real-time queries when snapshot created
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE TABLES (READ)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ accounts │  │ products │  │   kpis   │  │ health_  │   │
│  │          │  │          │  │          │  │ trends   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │playbook_│  │playbook_│  │playbook_│  │account_ │   │
│  │executions│ │reports  │  │triggers  │  │notes     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ Snapshot creation logic
                        │ (create_account_snapshot function)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              DESTINATION TABLE (WRITE)                       │
│                    account_snapshots                         │
│  (Point-in-time snapshot with 50+ fields)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Characteristics

### ✅ **Real-Time Data Capture**
- Snapshots capture the **current state** at the moment of creation
- No historical data stored - only current values
- All queries are executed **at snapshot creation time**

### ✅ **No Automatic Updates**
- Snapshots are **immutable** once created
- They represent a **point-in-time** state
- To get updated data, create a **new snapshot**

### ✅ **References, Not Copies**
- CSM notes and playbook reports are stored as **IDs only** (JSON arrays)
- Full content is fetched when needed (e.g., for RAG context)
- This keeps snapshot size manageable

### ✅ **Change Detection**
- Compares with previous snapshot to calculate:
  - `health_score_change_from_last`
  - `revenue_change_from_last` / `revenue_change_percent`
  - `days_since_last_snapshot`
  - `is_significant_change` (flag)

---

## Summary

**Tables Read From**: 9 tables
- `accounts`, `products`, `kpis`, `health_trends`
- `playbook_executions`, `playbook_reports`, `playbook_triggers`
- `account_notes`, `account_snapshots` (previous)

**Tables Written To**: 1 table
- `account_snapshots`

**Update Mechanism**: 
- **Current**: Manual API calls
- **Future**: Event-driven, scheduled, or post-calculation triggers (design ready, not implemented)

**Data Freshness**: 
- Snapshots are **point-in-time** captures
- Created snapshots are **immutable**
- To get latest data, create a new snapshot

