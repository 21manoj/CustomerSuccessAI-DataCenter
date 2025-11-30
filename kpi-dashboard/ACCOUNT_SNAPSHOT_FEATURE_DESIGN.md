# Account Snapshot Feature - Complete Design

## Overview
A unified account snapshot system that captures complete account state at specific points in time, enabling historical analysis, trend tracking, and enhanced RAG context.

**Note:** Automatic retention and cleanup policies (12-month retention, archival) are planned for a future release. See `PRODUCT_ROADMAP.md` item #5 for details.

---

## 1. What Will Be Captured

### 1.1 Core Account Information
| Field | Source | Description |
|-------|--------|-------------|
| `account_id` | Account | Account identifier |
| `account_name` | Account | Account name |
| `customer_id` | Account | Tenant identifier |
| `snapshot_timestamp` | System | When snapshot was taken |
| `snapshot_type` | System | `manual`, `scheduled`, `event_driven`, `post_upload`, `post_health_calc` |
| `snapshot_reason` | System | Why snapshot was created (optional) |

### 1.2 Financial Metrics
| Field | Source | Description |
|-------|--------|-------------|
| `revenue` | Account.revenue | Current annual revenue |
| `revenue_change_from_last` | Calculated | Change from previous snapshot |
| `revenue_change_percent` | Calculated | Percentage change |

### 1.3 Health Scores
| Field | Source | Description |
|-------|--------|-------------|
| `overall_health_score` | HealthTrend or calculated | Overall health score (0-100) |
| `product_usage_score` | HealthTrend | Product usage category score |
| `support_score` | HealthTrend | Support category score |
| `customer_sentiment_score` | HealthTrend | Customer sentiment category score |
| `business_outcomes_score` | HealthTrend | Business outcomes category score |
| `relationship_strength_score` | HealthTrend | Relationship strength category score |
| `health_score_change_from_last` | Calculated | Change from previous snapshot |
| `health_score_trend` | Calculated | `improving`, `declining`, `stable` (based on last 3 snapshots) |

### 1.4 Account Status & Metadata
| Field | Source | Description |
|-------|--------|-------------|
| `account_status` | Account.account_status | `active`, `inactive`, `at_risk`, `churn` |
| `industry` | Account.industry | Industry vertical |
| `region` | Account.region | Geographic region |
| `account_tier` | Account.profile_metadata.account_tier | Account tier (if available) |
| `external_account_id` | Account.external_account_id | External system ID |

### 1.5 CSM & Team Assignment
| Field | Source | Description |
|-------|--------|-------------|
| `assigned_csm` | Account.profile_metadata.assigned_csm | CSM name |
| `csm_manager` | Account.profile_metadata.csm_manager | CSM manager name |
| `account_owner` | Account.profile_metadata.account_owner | Account owner (if different from CSM) |

### 1.6 Products & Usage
| Field | Source | Description |
|-------|--------|-------------|
| `products_used` | Account.profile_metadata.products_used or Product table | List of product names |
| `product_count` | Calculated | Number of products |
| `primary_product` | Calculated | Most used/primary product |

### 1.7 Playbook Status
| Field | Source | Description |
|-------|--------|-------------|
| `playbooks_running` | PlaybookExecution (status='in-progress') | List of playbook IDs currently running |
| `playbooks_running_count` | Calculated | Number of active playbooks |
| `playbooks_completed_count` | PlaybookExecution (status='completed') | Total completed playbooks (all time) |
| `playbooks_completed_last_30_days` | PlaybookExecution | Count of playbooks completed in last 30 days |
| `last_playbook_executed` | PlaybookExecution | Most recent playbook execution (playbook_id, date) |
| `playbook_recommendations_active` | PlaybookTrigger | List of playbooks that are recommended/triggered |

### 1.8 KPI Summary
| Field | Source | Description |
|-------|--------|-------------|
| `total_kpis` | KPI.count() | Total number of KPIs for account |
| `account_level_kpis` | KPI.count(product_id=NULL) | Number of account-level KPIs |
| `product_level_kpis` | KPI.count(product_id IS NOT NULL) | Number of product-level KPIs |
| `critical_kpis_count` | KPI (health_status='Critical') | Number of KPIs in critical state |
| `at_risk_kpis_count` | KPI (health_status='Risk') | Number of KPIs in risk state |
| `healthy_kpis_count` | KPI (health_status='Healthy') | Number of KPIs in healthy state |
| `top_critical_kpis` | KPI (top 5 by impact) | List of top 5 critical KPIs with values |

### 1.9 Engagement Metrics (from profile_metadata)
| Field | Source | Description |
|-------|--------|-------------|
| `lifecycle_stage` | Account.profile_metadata.engagement.lifecycle_stage | `onboarding`, `growth`, `mature`, `renewal` |
| `onboarding_status` | Account.profile_metadata.engagement.onboarding_status | Onboarding completion status |
| `last_qbr_date` | Account.profile_metadata.engagement.last_qbr_date | Last QBR date |
| `next_qbr_date` | Account.profile_metadata.engagement.next_qbr_date | Next QBR date |
| `engagement_score` | Account.profile_metadata.engagement.score | Engagement score (if available) |

### 1.10 Champion & Stakeholder Info (from profile_metadata)
| Field | Source | Description |
|-------|--------|-------------|
| `primary_champion` | Account.profile_metadata.champions[0] | Primary champion name |
| `champion_status` | Account.profile_metadata.champions[0].status | Champion status |
| `stakeholder_count` | Account.profile_metadata.champions.length | Number of champions/stakeholders |

### 1.13 CSM Notes & Playbook Reports (References)
| Field | Source | Description |
|-------|--------|-------------|
| `recent_csm_note_ids` | AccountNote (last 5) | JSON array of note IDs - Last 5 CSM notes at snapshot time |
| `recent_playbook_report_ids` | PlaybookReport (last 3) | JSON array of report IDs - Last 3 playbook reports at snapshot time |

**Note:** These are references (IDs only), not full content. Full content is fetched via joins when needed for RAG context.

### 1.11 Calculated Metrics
| Field | Description |
|-------|-------------|
| `days_since_last_snapshot` | Days since previous snapshot |
| `snapshot_sequence_number` | Sequential number for this account (1, 2, 3...) |
| `is_significant_change` | Boolean - true if health score changed >5 points or revenue changed >10% |

### 1.12 Metadata
| Field | Description |
|-------|-------------|
| `created_by` | User who triggered snapshot (if manual) |
| `trigger_event` | Event that triggered snapshot (if event-driven) |
| `snapshot_version` | Version of snapshot schema (for future compatibility) |

---

## 2. Database Schema

### 2.1 AccountSnapshot Table

```python
class AccountSnapshot(db.Model):
    __tablename__ = 'account_snapshots'
    
    # Primary Key
    snapshot_id = db.Column(db.Integer, primary_key=True)
    
    # Account & Customer
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    
    # Snapshot Metadata
    snapshot_timestamp = db.Column(db.DateTime, nullable=False, index=True)
    snapshot_type = db.Column(db.String(50), nullable=False)  # manual, scheduled, event_driven, post_upload, post_health_calc
    snapshot_reason = db.Column(db.String(255))  # Optional reason
    snapshot_version = db.Column(db.Integer, default=1)  # Schema version
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    trigger_event = db.Column(db.String(100))  # Event that triggered snapshot
    
    # Financial
    revenue = db.Column(db.Numeric(15, 2))
    revenue_change_from_last = db.Column(db.Numeric(15, 2))
    revenue_change_percent = db.Column(db.Numeric(5, 2))
    
    # Health Scores
    overall_health_score = db.Column(db.Numeric(5, 2))
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    health_score_change_from_last = db.Column(db.Numeric(5, 2))
    health_score_trend = db.Column(db.String(20))  # improving, declining, stable
    
    # Account Status
    account_status = db.Column(db.String(50))
    industry = db.Column(db.String(100))
    region = db.Column(db.String(100))
    account_tier = db.Column(db.String(50))
    external_account_id = db.Column(db.String(100))
    
    # CSM & Team
    assigned_csm = db.Column(db.String(100))
    csm_manager = db.Column(db.String(100))
    account_owner = db.Column(db.String(100))
    
    # Products
    products_used = db.Column(db.JSON)  # List of product names
    product_count = db.Column(db.Integer, default=0)
    primary_product = db.Column(db.String(100))
    
    # Playbooks
    playbooks_running = db.Column(db.JSON)  # List of playbook IDs
    playbooks_running_count = db.Column(db.Integer, default=0)
    playbooks_completed_count = db.Column(db.Integer, default=0)
    playbooks_completed_last_30_days = db.Column(db.Integer, default=0)
    last_playbook_executed = db.Column(db.JSON)  # {playbook_id, date}
    playbook_recommendations_active = db.Column(db.JSON)  # List of recommended playbooks
    recent_playbook_report_ids = db.Column(db.JSON)  # [report_id1, report_id2, report_id3] - Last 3 reports
    
    # KPI Summary
    total_kpis = db.Column(db.Integer, default=0)
    account_level_kpis = db.Column(db.Integer, default=0)
    product_level_kpis = db.Column(db.Integer, default=0)
    critical_kpis_count = db.Column(db.Integer, default=0)
    at_risk_kpis_count = db.Column(db.Integer, default=0)
    healthy_kpis_count = db.Column(db.Integer, default=0)
    top_critical_kpis = db.Column(db.JSON)  # [{kpi_name, value, health_status}, ...]
    
    # Engagement
    lifecycle_stage = db.Column(db.String(50))
    onboarding_status = db.Column(db.String(50))
    last_qbr_date = db.Column(db.Date)
    next_qbr_date = db.Column(db.Date)
    engagement_score = db.Column(db.Numeric(5, 2))
    
    # Champions
    primary_champion = db.Column(db.String(100))
    champion_status = db.Column(db.String(50))
    stakeholder_count = db.Column(db.Integer, default=0)
    
    # CSM Notes & Playbook Reports (References)
    recent_csm_note_ids = db.Column(db.JSON)  # [note_id1, note_id2, ...] - Last 5 notes
    recent_playbook_report_ids = db.Column(db.JSON)  # [report_id1, report_id2, report_id3] - Last 3 reports
    
    # Calculated
    days_since_last_snapshot = db.Column(db.Integer)
    snapshot_sequence_number = db.Column(db.Integer, default=1)
    is_significant_change = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Indexes
    __table_args__ = (
        db.Index('idx_account_snapshot_timestamp', 'account_id', 'snapshot_timestamp'),
        db.Index('idx_customer_snapshot_timestamp', 'customer_id', 'snapshot_timestamp'),
        db.Index('idx_snapshot_type', 'snapshot_type'),
    )
```

### 2.2 AccountNote Table (New)

**Purpose:** Store CSM notes, meeting notes, QBR notes, and other account-related notes.

```python
class AccountNote(db.Model):
    __tablename__ = 'account_notes'
    
    # Primary Key
    note_id = db.Column(db.Integer, primary_key=True)
    
    # Account & Customer
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    
    # Note Content
    note_type = db.Column(db.String(50), nullable=False)  # 'meeting', 'qbr', 'call', 'email', 'general', 'interaction'
    note_content = db.Column(db.Text, nullable=False)  # Full note text
    note_title = db.Column(db.String(255))  # Optional title/subject
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Optional Fields
    meeting_date = db.Column(db.Date)  # Date of meeting/call (if applicable)
    participants = db.Column(db.JSON)  # List of participant names
    tags = db.Column(db.JSON)  # List of tags for categorization
    is_important = db.Column(db.Boolean, default=False)  # Flag for important notes
    related_playbook_id = db.Column(db.String(50))  # Link to playbook if note is playbook-related
    
    # Indexes
    __table_args__ = (
        db.Index('idx_account_note_timestamp', 'account_id', 'created_at'),
        db.Index('idx_customer_note_timestamp', 'customer_id', 'created_at'),
        db.Index('idx_note_type', 'note_type'),
    )
```

**Example Data:**
```python
note_id=1, account_id=1, customer_id=1,
  note_type='qbr', note_title='Q4 2025 QBR',
  note_content='Discussed NPS improvement plan, committed to 3 feature requests...',
  created_by=1, created_at='2025-01-15 10:30:00',
  meeting_date='2025-01-15', participants=['John Smith (CSM)', 'Jane Doe (Customer)']
```

**Relationships:**
- Many-to-One: accounts, customers, users
- Referenced by: account_snapshots (via recent_csm_note_ids JSON array)

---

## 3. How RAG System Will Be Informed

### 3.1 Integration Points

#### A. Direct RAG API (`direct_rag_api.py`)
**Location:** `backend/direct_rag_api.py`  
**Method:** Enhance context assembly to include snapshot data

**Current Context Assembly:**
```python
context_data.append(f"Account: {account.account_name}, Revenue: ${account.revenue:,.0f}, Health Score: {health_score:.1f}/100")
```

**Enhanced Context Assembly:**
```python
# Get latest snapshot for account
latest_snapshot = AccountSnapshot.query.filter_by(
    account_id=account.account_id,
    customer_id=customer_id
).order_by(AccountSnapshot.snapshot_timestamp.desc()).first()

if latest_snapshot:
    # Build base snapshot context
    snapshot_context = (
        f"Account: {account.account_name} (Snapshot: {latest_snapshot.snapshot_timestamp.strftime('%Y-%m-%d')})\n"
        f"  Revenue: ${latest_snapshot.revenue:,.0f} "
        f"({'↑' if latest_snapshot.revenue_change_percent > 0 else '↓'} {abs(latest_snapshot.revenue_change_percent):.1f}%)\n"
        f"  Health Score: {latest_snapshot.overall_health_score:.1f}/100 "
        f"({latest_snapshot.health_score_trend})\n"
        f"  CSM: {latest_snapshot.assigned_csm or 'Unassigned'}\n"
        f"  Products: {', '.join(latest_snapshot.products_used or [])}\n"
        f"  Playbooks Running: {', '.join(latest_snapshot.playbooks_running or [])}\n"
        f"  Playbooks Completed: {latest_snapshot.playbooks_completed_count}\n"
        f"  Critical KPIs: {latest_snapshot.critical_kpis_count}/{latest_snapshot.total_kpis}\n"
    )
    
    # Fetch and append CSM notes summaries
    if latest_snapshot.recent_csm_note_ids:
        notes = AccountNote.query.filter(
            AccountNote.note_id.in_(latest_snapshot.recent_csm_note_ids)
        ).order_by(AccountNote.created_at.desc()).all()
        
        if notes:
            snapshot_context += "  Recent CSM Notes:\n"
            for note in notes[:3]:  # Limit to 3 most recent
                note_summary = note.note_content[:150] + "..." if len(note.note_content) > 150 else note.note_content
                snapshot_context += f"    - {note.note_type.title()} ({note.created_at.strftime('%Y-%m-%d')}): {note_summary}\n"
    
    # Fetch and append playbook report summaries
    if latest_snapshot.recent_playbook_report_ids:
        reports = PlaybookReport.query.filter(
            PlaybookReport.report_id.in_(latest_snapshot.recent_playbook_report_ids)
        ).order_by(PlaybookReport.report_generated_at.desc()).all()
        
        if reports:
            snapshot_context += "  Recent Playbook Reports:\n"
            for report in reports:
                exec_summary = report.report_data.get('executive_summary', '')
                if exec_summary:
                    summary = exec_summary[:200] + "..." if len(exec_summary) > 200 else exec_summary
                    snapshot_context += f"    - {report.playbook_name} ({report.report_generated_at.strftime('%Y-%m-%d')}): {summary}\n"
    
    context_data.append(snapshot_context)
```

#### B. Historical Context for Queries
**New Function:** `get_account_snapshot_history()`

```python
def get_account_snapshot_history(account_id, customer_id, months=3):
    """Get account snapshot history for RAG context"""
    cutoff_date = datetime.now() - timedelta(days=months*30)
    
    snapshots = AccountSnapshot.query.filter_by(
        account_id=account_id,
        customer_id=customer_id
    ).filter(
        AccountSnapshot.snapshot_timestamp >= cutoff_date
    ).order_by(AccountSnapshot.snapshot_timestamp.desc()).all()
    
    if not snapshots:
        return None
    
    history_context = "=== ACCOUNT SNAPSHOT HISTORY ===\n"
    for snapshot in snapshots:
        history_context += (
            f"Date: {snapshot.snapshot_timestamp.strftime('%Y-%m-%d')}\n"
            f"  Health: {snapshot.overall_health_score:.1f} "
            f"({snapshot.health_score_trend})\n"
            f"  Revenue: ${snapshot.revenue:,.0f}\n"
            f"  Status: {snapshot.account_status}\n"
            f"  Playbooks: {snapshot.playbooks_running_count} running, "
            f"{snapshot.playbooks_completed_count} completed\n"
        )
    
    return history_context
```

#### B.1 Fetching Referenced Content for RAG
**New Function:** `get_snapshot_referenced_content()`

```python
def get_snapshot_referenced_content(snapshot):
    """
    Fetch summaries from CSM notes and playbook reports referenced in snapshot.
    Returns formatted context string for RAG.
    """
    context_parts = []
    
    # Fetch CSM Notes
    if snapshot.recent_csm_note_ids:
        notes = AccountNote.query.filter(
            AccountNote.note_id.in_(snapshot.recent_csm_note_ids),
            AccountNote.customer_id == snapshot.customer_id  # Security check
        ).order_by(AccountNote.created_at.desc()).all()
        
        if notes:
            context_parts.append("=== RECENT CSM NOTES ===")
            for note in notes:
                # Truncate long notes for context
                note_preview = note.note_content[:300] + "..." if len(note.note_content) > 300 else note.note_content
                context_parts.append(
                    f"{note.note_type.title()} - {note.created_at.strftime('%Y-%m-%d')}: {note_preview}"
                )
    
    # Fetch Playbook Reports
    if snapshot.recent_playbook_report_ids:
        reports = PlaybookReport.query.filter(
            PlaybookReport.report_id.in_(snapshot.recent_playbook_report_ids),
            PlaybookReport.customer_id == snapshot.customer_id  # Security check
        ).order_by(PlaybookReport.report_generated_at.desc()).all()
        
        if reports:
            context_parts.append("=== RECENT PLAYBOOK REPORTS ===")
            for report in reports:
                report_data = report.report_data or {}
                exec_summary = report_data.get('executive_summary', '')
                outcomes = report_data.get('outcomes_achieved', {})
                
                # Build report summary
                report_summary = f"{report.playbook_name} ({report.report_generated_at.strftime('%Y-%m-%d')})"
                if exec_summary:
                    summary = exec_summary[:250] + "..." if len(exec_summary) > 250 else exec_summary
                    report_summary += f": {summary}"
                
                # Add key outcomes
                if outcomes:
                    outcome_strs = []
                    for metric, data in list(outcomes.items())[:2]:  # Top 2 outcomes
                        if isinstance(data, dict) and 'improvement' in data:
                            outcome_strs.append(f"{metric}: {data.get('improvement', 'N/A')}")
                    if outcome_strs:
                        report_summary += f" | Outcomes: {', '.join(outcome_strs)}"
                
                context_parts.append(report_summary)
    
    return "\n".join(context_parts) if context_parts else None
```

**Usage in RAG Context Assembly:**
```python
# In direct_rag_api.py, when building context from snapshot:
if latest_snapshot:
    # ... base snapshot context ...
    
    # Add referenced content (notes and reports)
    referenced_content = get_snapshot_referenced_content(latest_snapshot)
    if referenced_content:
        context_data.append(referenced_content)
```

#### C. System Prompt Enhancement
**Location:** `backend/direct_rag_api.py` - System prompt section

**Add to System Prompt:**
```
You have access to account snapshot data that captures complete account state at specific points in time.

Account snapshots include:
- Health scores (overall and by category) with trend indicators
- Revenue with change tracking
- CSM assignments and team information
- Active and completed playbooks
- KPI summaries (total, critical, at-risk counts)
- Engagement metrics (lifecycle stage, QBR dates)
- Product usage information
- Recent CSM notes (meeting notes, QBR notes, interaction logs)
- Recent playbook reports (executive summaries, outcomes, recommendations)

When answering questions about account history or trends:
- Reference specific snapshot dates when discussing changes
- Use trend indicators (improving, declining, stable) to describe health score changes
- Cite playbook execution history when relevant
- Reference CSM notes when discussing customer interactions or meetings
- Include playbook report outcomes when discussing playbook results
- Compare current state to historical snapshots when appropriate
```

#### D. Query-Specific Snapshot Context
**For queries like:**
- "What was TechCorp's state last month?"
- "Show me account changes over the last quarter"
- "Which accounts improved their health score?"

**Add snapshot context:**
```python
# Detect historical queries
if any(keyword in query.lower() for keyword in ['history', 'trend', 'change', 'improve', 'decline', 'last month', 'quarter']):
    snapshot_context = get_account_snapshot_history(account_id, customer_id, months=6)
    if snapshot_context:
        context_data.append(snapshot_context)
```

### 3.2 RAG Query Examples with Snapshots

**Query:** "What was TechCorp's health score last month?"
**RAG Context:**
```
Account: TechCorp Solutions (Snapshot: 2025-01-15)
  Health Score: 68.5/100 (declining)
  Revenue: $1,200,000 (↓ 5.2%)
  CSM: John Smith
  Playbooks Running: voc-sprint
  Critical KPIs: 8/59
```

**Query:** "Which accounts improved their health score?"
**RAG Context:**
```
Account: TechCorp Solutions
  Current: 72.3/100 (improving)
  Last Month: 68.5/100
  Change: +3.8 points

Account: DataCo Inc
  Current: 65.2/100 (stable)
  Last Month: 65.0/100
  Change: +0.2 points
```

---

## 4. Frequency of Updates

### 4.1 Snapshot Triggers

#### A. Scheduled Snapshots (Recommended)
**Frequency Options:**
- **Daily** (recommended for active accounts): Every day at 2 AM
- **Weekly**: Every Monday at 2 AM
- **Monthly**: First day of month at 2 AM

**Configuration:**
```python
# CustomerConfig or new SnapshotConfig table
snapshot_frequency = 'daily'  # daily, weekly, monthly
snapshot_time = '02:00'  # Time of day
snapshot_accounts = 'all'  # all, active_only, health_score_below_70
```

**Implementation:**
- Background job (cron, Celery, or scheduled task)
- Runs for all accounts or filtered subset
- Creates snapshot for each account

#### B. Event-Driven Snapshots
**Triggers:**
1. **Health Score Calculation** (after rollup)
   - When: After `/api/corporate/rollup` completes
   - Scope: All accounts that had health scores calculated
   - Reason: `post_health_calc`

2. **KPI Upload** (after upload)
   - When: After `/api/upload` or `/api/upload/enhanced` completes
   - Scope: Account(s) that received new KPI data
   - Reason: `post_upload`

3. **Significant Health Score Change**
   - When: Health score changes by >5 points
   - Scope: Specific account
   - Reason: `health_score_change`

4. **Significant Revenue Change**
   - When: Revenue changes by >10%
   - Scope: Specific account
   - Reason: `revenue_change`

5. **Playbook Execution Start**
   - When: New playbook execution created (status='in-progress')
   - Scope: Account associated with playbook
   - Reason: `playbook_started`

6. **Playbook Execution Complete**
   - When: Playbook execution completed (status='completed')
   - Scope: Account associated with playbook
   - Reason: `playbook_completed`

7. **Account Status Change**
   - When: Account status changes (e.g., active → at_risk)
   - Scope: Specific account
   - Reason: `status_change`

#### C. Manual Snapshots
**API Endpoint:** `POST /api/account-snapshots/create`
**Parameters:**
- `account_id` (optional - if not provided, creates for all accounts)
- `reason` (optional - user-provided reason)

**Use Cases:**
- Before major account changes
- After important meetings/QBRs
- For audit purposes
- Before/after playbook execution

### 4.2 Snapshot Frequency Recommendations

| Account Type | Recommended Frequency | Rationale |
|--------------|----------------------|-----------|
| **High-Value Accounts** (revenue > $1M) | Daily | Critical accounts need frequent tracking |
| **At-Risk Accounts** (health < 70) | Daily | Monitor deteriorating accounts closely |
| **Active Playbooks** | Daily | Track progress of active playbooks |
| **Standard Accounts** | Weekly | Balance between tracking and storage |
| **Inactive Accounts** | Monthly | Minimal changes, less frequent needed |

### 4.3 Storage Considerations

**Estimated Storage per Snapshot:**
- ~2-3 KB per snapshot (JSON fields + numeric fields)
- 100 accounts × 30 daily snapshots = ~6-9 MB/month
- 100 accounts × 12 monthly snapshots = ~2.4-3.6 MB/year

**Retention Policy:**
- **Keep all snapshots** for last 12 months
- **Monthly snapshots** for 2-5 years
- **Quarterly snapshots** for 5+ years
- **Archive old snapshots** to cold storage after retention period

---

## 5. API Endpoints

### 5.1 Create Snapshot
```
POST /api/account-snapshots/create
Body: {
  "account_id": 123,  // optional, if not provided creates for all accounts
  "snapshot_type": "manual",  // manual, scheduled, event_driven
  "reason": "Pre-QBR snapshot"
}
```

### 5.2 Get Account Snapshots
```
GET /api/account-snapshots?account_id=123&limit=10&start_date=2025-01-01
```

### 5.3 Get Latest Snapshot
```
GET /api/account-snapshots/latest?account_id=123
```

### 5.4 Compare Snapshots
```
GET /api/account-snapshots/compare?account_id=123&snapshot_id_1=10&snapshot_id_2=20
```

### 5.5 Get Snapshot History for RAG
```
GET /api/account-snapshots/history?account_id=123&months=3
```

---

## 6. Implementation Plan

### Phase 1: Database & Model
1. Create `AccountSnapshot` model
2. Create database migration
3. Add indexes

### Phase 2: Snapshot Creation Logic
1. Implement `create_account_snapshot()` function
2. Implement change detection logic
3. Implement trend calculation

### Phase 3: Event-Driven Triggers
1. Add snapshot creation after health score calculation
2. Add snapshot creation after KPI upload
3. Add snapshot creation on playbook events
4. Add snapshot creation on significant changes

### Phase 4: Scheduled Snapshots
1. Implement scheduled job (daily/weekly/monthly)
2. Add configuration for frequency
3. Add filtering logic (all vs. active only)

### Phase 5: RAG Integration
1. Enhance `direct_rag_api.py` context assembly
2. Add snapshot history function
3. Update system prompts
4. Add query detection for historical queries

### Phase 6: API Endpoints
1. Create snapshot API endpoints
2. Add comparison endpoints
3. Add history endpoints

### Phase 7: Frontend Integration (Optional)
1. Add snapshot timeline view
2. Add snapshot comparison UI
3. Add manual snapshot trigger button

---

## 7. Success Metrics

- **Coverage**: 100% of accounts have at least monthly snapshots
- **Timeliness**: Snapshots created within 5 minutes of trigger events
- **RAG Enhancement**: Historical queries show 50% improvement in accuracy
- **Storage**: < 100 MB for 1000 accounts with 12 months of daily snapshots

---

**Last Updated:** 2025-01-XX  
**Status:** Design Phase - Awaiting Approval

